# Durable Dual-Lane Completed-Turn Workers

Use this reference when one completed-turn callback must durably hand off both authoritative extraction and next-turn context generation without waiting for AI/network work.

## Minimal architecture

Persist one immutable completed-turn envelope synchronously, then wake two bounded resident lanes only when their work is truly independent:

```text
sync_turn
  -> validate/freeze/redact current turn
  -> atomic insert(turn identity, immutable turn number, bounded messages,
                   extraction_status=pending, context_status=pending)
  -> wake extraction lane
  -> wake context lane
  -> return
```

The database row is the durable queue. Never create an in-memory-only context queue beside it.

## Identity and ordering

- Identify the event by stable host identity such as `(session_id, immutable_turn)`, not content alone. Repeated identical text on two turns must create two jobs.
- Add a partial unique constraint for real host turns. On duplicate delivery, return the existing row only if the frozen payload matches; a changed payload for the same event is a conflict.
- FIFO must use a monotonic insertion sequence allocated in the insert transaction. `ORDER BY created_at, hash_job_id` is not FIFO: equal timestamps can reorder turns by hash. A deterministic test should freeze all timestamps and assert claim order remains `[1, 2, 3]`.
- If multiple processes may own workers, a process-local thread singleton is insufficient. Use a durable lane lease/heartbeat or make claim refuse a second running item. Startup recovery must not reset another live process's claim.

## Wakeup protocol

Use one resident worker plus `Event`/`Condition` per lane. A safe Event loop clears before its final recheck:

1. enqueue and commit;
2. set wake event;
3. worker drains claims;
4. when empty, clear event;
5. recheck the durable queue;
6. wait only if still empty.

This prevents the one-shot-worker race where enqueue observes an alive worker just as that worker exits. On shutdown, set the shutdown flag, set every wake event, and join only for a short bound.

## Terminal-state correctness

A typed substage error is not a successful context receipt. If base succeeds and dynamic fails (or vice versa), mark the parent context lane retryable/failed. Replay may skip the already-active layer by cadence and rerun only the missing layer. Never persist `{status: completed, *_error_type: ...}` and then exclude it from recovery.

Link each context generation/job to the durable completed-turn job ID. Persist enough state to reject queued work after a rewind: capture the scope generation at enqueue, then require `begin_job` to atomically match it. Otherwise a turn queued before rewind can start afterward and republish into the new generation.

Start recovered context workers only after scope/session initialization finishes. Starting recovery first races completed-turn processing against dialectical/session initialization.

## Queue-overflow contract

Non-blocking callback + hard queue limit + no dropped events is a three-way constraint. A callback that catches `OverflowError`, logs, and returns silently loses both lanes.

Choose explicitly:

- persist all rows and bound execution concurrency, using SQLite as backlog; or
- persist overflow/deferred rows in another durable state; or
- surface a retryable failure to a host that is proven to replay.

A hard in-memory-style limit without durable overflow cannot satisfy no-loss.

## Independent lanes and shared Agent safety

Separate lanes preserve context freshness when extraction is slow, but they may call the same Agent facade concurrently. Before enabling this, prove the facade and its session/tool-context machinery are concurrency-safe. Otherwise use a provider-owned arbiter or lock. If context freshness has priority, a plain mutex may starve context behind extraction; define lane priority deliberately.

Strict guarantee that turn N context is available at the first prefetch of turn N+1 conflicts with a fully non-blocking handoff. The safe default contract is **latest completed past context**. Exact previous-turn freshness needs a bounded prefetch barrier or a Host-owned completion handoff.

## Read-only audit probes for live concurrency work

When another actor may still be editing the implementation, fingerprint every scoped production file and test before the audit, then fingerprint again after focused probes. If hashes change, discard mixed-snapshot conclusions, reread only the changed ownership paths, and rerun the affected probes. Label superseded test output explicitly rather than presenting it as final-source evidence.

Use three deterministic fail-closed probes in addition to ordinary tests:

1. **Complete-envelope duplicate probe.** Deliver the same durable event identity twice while changing one frozen field at a time: bounded messages, owner/agent identity, platform, scope generation, and redacted turn payload. Every mismatch must conflict. Comparing only a content-derived key is insufficient even when the database keeps the first row.
2. **Monotonic shutdown probe.** Close the provider/concurrency gate, then invoke the real resolver/getter and a stale post-shutdown route. Neither may manufacture a replacement capability or begin another model call. Gate recreation belongs only to an explicit new initialization epoch. Also test a waiter blocked on the concurrency permit during close.
3. **Physical migration verification probe.** Keep the latest migration ledger row but remove one newly required column or index in a disposable database. The schema verifier must fail before a runtime scheduler reads the row. Migration-number continuity and table presence alone do not verify a new concurrency schema.

For parallel fan-out tests, do not assert worker start order: start order is intentionally nondeterministic. Assert canonical semantic aggregation separately. If failure handling claims queued sibling cancellation, test that contract directly; `ThreadPoolExecutor` context-manager shutdown waits but does not cancel pending futures by default.

## Deterministic test matrix

- Callback returns while a context worker is blocked on an Event; durable row exists before release.
- Equal timestamps still claim turns in insertion order.
- Same event/same payload is idempotent; same event/different payload conflicts; same text/different turns stays distinct.
- Both lane workers remain resident and wake after becoming idle.
- Failure of one job does not strand later jobs.
- Typed base/dynamic failure remains recoverable, not completed.
- Restart requeues running/failed work but not completed work.
- Rewind prevents pending and in-flight old-generation work from publishing.
- Queue saturation follows the declared no-loss/backpressure policy.
- Dynamic context is never injected into its own source turn; after completion it is available only to later turns.
- Shutdown wakes idle workers and remains bounded.

Avoid timing-only assertions such as `elapsed < 0.1` as the primary proof. Run the callback in a thread, gate the worker with Events, and prove callback completion before releasing the worker. Polling a durable terminal state with a deadline is acceptable when no event seam exists.
