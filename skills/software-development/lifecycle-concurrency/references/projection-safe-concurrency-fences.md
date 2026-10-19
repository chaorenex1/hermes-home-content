# Projection-Safe Concurrency Fences

Use this when one durable transcript/job/event stream has multiple legitimate projections: raw storage, model replay, UI display, normalized protocol history, compacted context, or filtered active rows.

## Failure pattern

A caller reads durable rows, then legally transforms its working projection by merging adjacent roles, dropping orphan protocol rows, sanitizing replay tails, pruning large results, or replacing provisional events. A later writer/compactor acquires a lease and tries to detect intervening writes with:

```python
if len(reloaded_raw_rows) > len(working_projection):
    abort_as_stale()
```

This is invalid even in a single thread. Cardinality differs because the two lists are different projections, not because durable state advanced. Returning the unchanged projection can become a permanent no-progress loop when the caller interprets it as “nothing compressible” or “retries exhausted.”

## Correct fence

1. Capture a durable watermark **before** projection repair: maximum durable row ID, session generation, append sequence, or an equivalent transaction-owned version.
2. Carry that watermark alongside the working projection; do not infer it later from message count, object identity, timestamps, or normalized content.
3. Acquire the owner/session lease.
4. Re-read the durable watermark under the lease.
5. Abort only when the watermark advanced or another explicit version fence changed.
6. On true advancement, return a typed `stale_snapshot`/`defer` result. The caller reloads/reconciles authoritative state and refunds any retry budget; it must not classify unchanged content as compression exhaustion.
7. Let legal projection transforms change list length freely.

If append, rewind, compaction, or activation can alter visibility without increasing the maximum row ID, use a persisted session generation incremented by every visibility-changing transaction rather than only `MAX(id)`.

## Minimal deterministic regression matrix

### Repair-only shrink must proceed

- Persist two consecutive user rows.
- Read the snapshot and its durable watermark.
- Normalize the model projection so the two rows merge into one.
- Perform no durable write.
- Acquire the lease and compact/process.
- Assert the worker runs and commits; raw count > projected count is not a conflict.

### Real post-snapshot append must abort safely

- Persist the baseline rows and capture the watermark.
- Commit another row before lease acquisition.
- Acquire the lease.
- Assert the worker does not publish from the stale snapshot and the new row survives.

### Caller progress contract

- Force a provider/worker overflow that enters recovery.
- Return typed `stale_snapshot` once.
- Assert the caller reloads and retries without consuming the permanent exhaustion budget.
- Assert a lock contender and a stale durable snapshot remain distinguishable states.

### Composition test

Cross the real path: durable read → replay repair/sanitization → live working projection → lease acquisition → durable fence → publication. Component tests for repair and for late-append protection are insufficient if no test composes them.

## Mitigations are not fixes

An in-place, non-destructive transaction may avoid a session-rotation race because raw rows are archived rather than replaced, but it does not make cardinality a valid version. Lowering an automatic compaction threshold can reduce exposure to overflow, but it also does not repair the concurrency contract.

## Diagnostic evidence to collect

Record only privacy-safe metadata:

- session/owner ID;
- raw durable count and projected working count;
- captured and current durable watermark/generation;
- lease holder and acquisition result;
- typed abort reason;
- whether the caller reloaded, deferred, or consumed retry budget.

A log that only says “changed before lease acquisition” is incomplete unless it includes the two watermarks that proved the change.
