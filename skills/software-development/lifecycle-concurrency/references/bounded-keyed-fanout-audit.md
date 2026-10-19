# Bounded Keyed Fan-Out Audit

Use this reference when one lifecycle stage performs independent remote/model work for a finite set of keys and then combines durable receipts.

## Audit matrix

| Layer | Required evidence | Failure signal |
|---|---|---|
| Host facade | `run()` uses per-call locals; runner creates a fresh execution/session object; `ContextVar` state is isolated; resources close in `finally`; async/thread sibling exists or a production characterization passes | Shared mutable session/agent object, process-global context mutation, or no cleanup |
| Bound | Explicit constant or validated effective setting read by the executor | Default executor size, thread-per-key, or a removed config knob accepted but ignored |
| Key ownership | Canonical key enum; each key scheduled once; per-worker host metadata binds key and exact paths | Duplicate key work, model-visible authority claims, or unrestricted shared tool access |
| Reads/writes | Disjoint expected paths; atomic per-file writes; lock scope does not include remote work; pair/multi-file atomicity stated explicitly | Same target reachable by siblings, lock held during inference, or implied transaction that does not exist |
| Aggregation | Workers return immutable outcomes; caller orders by canonical keys; multi-error selection is deterministic | Shared list append, raw `as_completed()` order, or last-writer-wins receipt fields |
| Failure/shutdown | Every started worker is drained before method exit; queued work cancellation policy is explicit | A worker can write after the caller has raised/returned |
| Tests | Event/Condition gates prove overlap, cap, reverse completion, drain-before-raise, and cross-key denial | Sleep-only tests or assertions that merely count final calls |

## Reentrant host-facade decision

A shared facade instance is usually safe when it stores only immutable identity and a runner callable, while each invocation constructs a fresh agent, session key, persistence handle, and isolated context. Verify the real runner, not just the public signature. A fake-runner barrier probe proves wrapper reentrancy; add one host characterization that monkeypatches the real runner boundary and checks simultaneous calls see distinct session keys and tool contexts.

Caller safety remains separate: a reentrant facade does not impose a rate or resource bound. The fan-out owner must provide the semaphore/executor cap.

## Write-conflict reasoning

Separate these claims:

1. **Expected-path disjointness:** well-behaved workers target different files.
2. **Physical authority:** the dispatcher rejects a worker that attempts another key's target.
3. **Atomicity:** each file replacement is atomic.
4. **Transactionality:** all outputs for one key commit together.

A profile-wide writer lock often proves only item 3. It may serialize individual writes from otherwise concurrent workers while allowing `A-short, B-short, A-detail, B-detail`. That is safe for disjoint targets but not an atomic output pair. Receipt validation after writes detects mistakes but cannot undo an unauthorized or partial write.

Carry an internal, host-owned envelope such as:

```json
{
  "purpose": "stage.summary",
  "tool_context": {
    "key": "experiences",
    "allowed_read_prefix": "/experiences/",
    "allowed_write_targets": [
      "/experiences/summary.md",
      "/experiences/detailed-summary.md"
    ]
  }
}
```

Enforce the envelope in the shared tool dispatcher before filesystem mutation. Do not trust the model to echo or select authorization-bearing paths.

## Deterministic implementation shape

```python
keys = canonical_affected_keys(receipt)
with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(keys))) as pool:
    outcomes = list(pool.map(run_one_key, keys))  # preserves input order

for key, outcome in zip(keys, outcomes, strict=True):
    aggregate_observed.extend(outcome.observed_paths)
    aggregate_touched.extend(outcome.touched_paths)
```

If using `submit`, retain `future_by_key` and call `result()` in canonical key order. Use `as_completed()` only for progress telemetry or re-sort before semantic aggregation. Decide whether multiple failures surface by canonical key, submission order, or an aggregate error; test the selected rule.

## Exact event-gated RED recipes

### 1. Overlap and cap

- Force `MAX_WORKERS = 2` with at least three affected keys.
- In the fake worker, increment `active` under a lock and set `two_started` when it reaches two.
- Block on `release` in `try/finally`; decrement `active` in `finally`.
- Run the lifecycle method in an outer thread.
- Assert `two_started.wait(timeout=...)`, release, join, then assert `peak == 2`, every key ran once, and no worker remains active.
- A serial implementation fails because only one worker reaches the gate; an unbounded implementation fails because peak exceeds two.

### 2. Reverse completion, canonical receipt

- Use two canonical keys where the first worker waits for an event set by the second.
- Record completion order and force it to be `[second, first]`.
- Assert the returned affected keys, observed paths, and touched paths remain `[first..., second...]`, including fixed within-key output order.

### 3. Drain before raise

- Start two workers and signal `both_started`.
- Let the first raise while the second remains blocked.
- Assert the outer lifecycle call has not returned or raised yet.
- Release the sibling, join, assert the chosen error propagates, and assert no worker can mutate after exit.

### 4. Physical cross-key denial

- Give a worker host-owned authority for key A.
- Attempt a validly shaped write to key B through the real dispatcher.
- Assert a typed denial and that key B's target does not exist or remains byte-identical.
- Separately assert the two exact key-A targets still work.

## Reporting

Report independently:

- facade reentrancy: pass / partial / fail;
- caller-side concurrency bound;
- expected-path disjointness;
- physical write fence;
- per-file atomicity versus multi-file transactionality;
- canonical aggregation and failure order;
- passing characterization tests versus still-RED contract tests.
