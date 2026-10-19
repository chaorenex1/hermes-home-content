---
name: lifecycle-concurrency
description: "Safely move lifecycle callbacks from synchronous work to bounded background execution with durable-state tests."
version: 1.1.0
author: Masía
created_by: agent
---

# Lifecycle Concurrency

Use when a request moves work out of an application lifecycle callback (turn hook, request hook, shutdown hook, event handler) so the host remains responsive while durable work continues safely.

## Goals

- The host callback returns promptly.
- At most one equivalent background worker runs per owning lifecycle object.
- Durable work retains its own transaction/idempotency semantics.
- Shutdown is bounded and does not wait indefinitely.
- Tests prove behavior without timing-only sleeps.

## Workflow

1. **Trace ownership first.** Identify callback entry point, durable scheduler/job state, cancellation path, and shutdown path. Do not make a callback asynchronous if it relies on mutable request/session data after return; capture immutable inputs first.
2. **Write a red regression test.** Use `threading.Event` to block the worker callback. Assert the lifecycle hook returns within a small bounded interval, wait for a deterministic worker-start signal, and always release the event in `finally`.
3. **Dispatch minimally.** Store one worker/thread/future reference on the lifecycle owner. Refuse a new dispatch while that worker is alive; do not create an unbounded executor per turn.
4. **Separate the durable handoff from slow work.** Before backgrounding a callback, identify whether it must synchronously create a durable checkpoint that downstream cancellation/recovery reads immediately. Keep that small checkpoint atomic in the callback when required; move only the slow retrieval/classification/remote work behind it. If the existing API combines both and no durable queue exists, do not pretend the whole callback can become nonblocking—report that design boundary rather than breaking checkpoint visibility.
5. **Preserve durable boundaries.** The background worker should call the existing persisted scheduler/service rather than duplicate its transactions, retries, or idempotency logic. Coalesce queued work to a latest immutable input only when dropping superseded work is part of the contract; otherwise retain a bounded durable queue. A non-blocking callback cannot safely enforce a hard queue limit by catching overflow and returning: that silently loses accepted lifecycle events. Persist overflow in the durable queue/outbox or require an explicit Host retry contract; treat configured limits as soft observability thresholds when no retry channel exists. Identify events by stable owner/session sequence, not timestamp plus hash-derived IDs, and persist any scope-generation fence needed to reject work queued before rewind/reset.
5a. **Fence snapshots by durable identity, never projection cardinality.** Raw storage, model replay, UI display, protocol-repaired history, and compacted context are different projections and may legitimately have different lengths. Capture a durable row watermark or session generation before repair/sanitization, compare that same fence after acquiring the lease, and return a typed `stale_snapshot`/defer state only when the durable fence advanced. A no-op caused by drift must reload/refund retry budget; it must not be misreported as exhaustion. See `references/projection-safe-concurrency-fences.md` for the failure pattern and deterministic regression matrix.
6. **Guard shutdown.** Set the shutdown/cancellation flag before a worker starts new work. Join only with a short timeout; never block process exit waiting for an untrusted or remote callback. Capability revocation must be monotonic within one lifecycle epoch: getters/resolvers must check shutdown both before and inside their ownership lock, a waiter must re-check after acquiring a permit, and a closed gate must never be recreated until an explicit new `initialize()` epoch.
7. **Reconcile legacy tests deliberately.** Tests that assert a true durable checkpoint immediately after a callback are contract evidence, not automatically obsolete. Only update synchronous-result tests when the new contract explicitly changes their visibility semantics; use event/deadline assertions for genuinely background work. Never replace assertions with arbitrary sleeps.
8. **Verify source provenance and behavior.** In package/plugin workspaces, prove the test runner imports the working-tree module rather than an installed distribution before trusting RED/GREEN. Run the new regression test, relevant lifecycle/scheduler suite, and then the full project test suite.

## Process and Resource Lifecycle Branches

Lifecycle correctness also includes resources and child processes outside callback concurrency:

- **Process launching:** resolve executables in the effective child environment, preserve argv boundaries, model foreground/background ownership explicitly, and verify resource ownership plus health. Load `references/process-launching-workflows.md`; its re-homed details and probe use the `process-launching-workflows-*` names in `references/` and `scripts/`.
- **Python resource lifetime:** separate transaction scope from concrete resource closure, reproduce lock-sensitive cleanup, and fix shared ownership boundaries rather than hiding leaks with GC or retries. Load `references/python-resource-lifecycle.md` and `references/python-resource-lifecycle-windows-sqlite-temp-cleanup.md`.

These branches share the class invariant: identify the lifecycle owner, establish deterministic acquisition/start and cleanup/stop evidence, bound shutdown, and verify no work or handle outlives its authority.

## Nested Host/Provider Workers

A host may already dispatch `sync_turn` or an equivalent lifecycle callback on a background worker. That does **not** make slow provider AI/network work safe to run inline: a single host worker often serializes all provider writes and prefetch requests. In that shape:

1. Let the host worker call the provider callback in order.
2. Make the provider callback perform only a bounded enqueue and return.
3. Let one provider-owned worker run slow signal checks, extraction, review, and persistence.
4. Keep unrelated queues independent. Failure or overflow of hash-only lifecycle metadata must not drop the authoritative extraction job.

When one durable completed-turn row feeds separate extraction and context lanes, treat identity, insertion ordering, lane terminal states, rewind fences, wakeup ownership, queue overflow, and shared-Agent concurrency as one contract. Never use `created_at + hash ID` as FIFO, never mark a typed substage error completed, and never silently catch durable-queue overflow when no-loss is required. See `references/durable-dual-lane-turn-workers.md` for the implementation and deterministic test matrix.

If the host already passes the completed current-turn user and assistant values, use those values directly. Do not reconstruct a turn by rescanning the cumulative transcript. If tool evidence is required, extend the host contract to pass a current-turn message delta rather than infer it inside the provider.

## Bounded Parallel Fan-Out by Independent Key

Use this when one lifecycle phase fans out over disjoint keys such as memory types, tenants, shards, or artifact classes.

1. **Audit the host facade before parallelizing.** Read the facade and its real runner. Look for per-call local state, fresh execution/session objects, isolated `ContextVar` scope, independent persistence handles, explicit async/thread support, and complete cleanup. A stateless facade with a fresh runner per call is generally reentrant; a passing fake-runner overlap probe is supporting evidence, not a substitute for one production-path characterization test.
2. **Define one visible bound for the whole call path.** Use an explicit module constant or validated setting even when the current key enum is itself finite. If the fan-out executor calls through a second semaphore/gate, both layers must derive from the same bound; independent constants (for example executor `5` versus Agent gate `2`) create misleading tests, unnecessary queued work, and cancellation races. Test with the shared bound forced below the number of keys so an accidental unbounded executor is observable. Do not revive a removed public concurrency setting without restoring its full config contract.
3. **Fence each worker's authority.** Disjoint expected paths are not a security boundary. Carry host-owned per-worker metadata—key, allowed read scope, and exact write targets—through an internal tool context, then enforce it in the shared dispatcher. Prompt instructions and post-hoc receipt validation cannot prevent a mistaken worker from writing another worker's target.
4. **Keep workers isolated.** Each worker returns an immutable per-key outcome. Workers must not append to a shared receipt, mutate shared lists, or hold a common lock across remote/model work.
5. **Aggregate canonically, never by completion order.** Submit in canonical key order and assemble receipts in that same order (`executor.map` or a key→future map followed by ordered reads). `as_completed()` is suitable for telemetry only unless results are re-sorted. Define deterministic multi-failure selection as well.
6. **Understand the write transaction.** A global file lock can make each write atomic while a two-file output pair remains non-transactional. Concurrent workers may interleave distinct writes, and a failure may leave successful sibling output. State whether that is accepted durable behavior or requires a staged transaction.
7. **Drain before exit.** On any worker failure, wait for every started worker or cancel not-yet-started work, then close the executor before returning or raising. No worker may continue writing after the lifecycle method exits. `ThreadPoolExecutor` context-manager shutdown waits but does not cancel queued futures; use a cooperative sibling-failure flag checked immediately before each queued task's first side effect, cancel futures where possible, and RED-test that a third queued key never starts after an earlier sibling fails.
8. **Use event-gated RED tests.** Prove overlap and the cap, force reverse completion and verify canonical aggregation, block a sibling while another fails to prove drain-before-raise, and test physical cross-key write denial. Avoid guessed sleeps except short bounded negative waits.

See `references/bounded-keyed-fanout-audit.md` for a detailed audit matrix and deterministic RED-test recipes.

## Subagent Lifecycle Replacement Boundary

Do not replace a method merely because it is named `infer`. First classify whether it is an actual model transport or a host-owned orchestrator that performs bounded rounds, validates reasoner output, enforces evidence/version fences, and commits durable state. Preserve the latter and replace only its semantic reasoner/judge callback.

For background stages that need one bounded JSON result and no tools, prefer the host-owned plugin LLM lane (`ctx.llm.complete_structured`) over SubagentLifecycle. Give every stage a registered purpose and purpose-specific JSON Schema, use an explicit per-call timeout, fail closed on missing/invalid parsed output, and retain all domain/state-fence checks in deterministic code. A direct plugin completion needs no active parent turn and avoids accidental tool inheritance. See `references/subagent-lifecycle-boundary-audit.md` for the decision gate and structured-output verification contract.

Before requiring lifecycle-only background execution, prove all six contracts:

1. `launch`, `wait`, `result`, and `cancel` remain authorized in the worker's execution context; a turn-local `ContextVar` normally does not cross into a new thread.
2. The lifecycle has an explicit zero-tool mode. Prompt text such as “do not call tools” is not capability enforcement, and an empty toolset may mean “inherit parent tools.”
3. Fully rendered goal, context, and expected result fit the lifecycle's independent size limits.
4. `wait` has a bounded timeout followed by cooperative `cancel` and one short terminal wait.
5. In-process handles reconcile with durable jobs after shutdown or process restart; startup recovery often has no active parent turn.
6. Child construction side effects—memory notification, completion hooks, inherited context, resource cleanup, and cost rollup—are understood and tested.

Keep strict parsing, citations/evidence binding, retry quotas, promotion/rejection, version fences, and persistence in deterministic host code. Use stage-and-round-specific purpose/correlation identifiers so retries do not duplicate a launch or conflate separate logical rounds.

See `references/subagent-lifecycle-boundary-audit.md` for the full callsite audit, background-parent, tool-isolation, bounds, durability, and verification matrix.

## Context-Isolated Capability Registries

When a Host clears caller `ContextVar` state but explicitly carries a provider run capability across that isolation, review it as both an authorization lease and a concurrency lifecycle:

- Bound the **entire serialized envelope**, including plugin identity and purpose. A byte limit on only the nested token/tool context is insufficient.
- Inject metadata through an internal dispatch channel, not model-visible tool arguments, and trace sequential, concurrent, and registry routes separately.
- Bind token resolution to plugin identity, purpose, run/owner, workflow, and persistence binding; reject malformed, inactive, stale, foreign, and mismatched envelopes fail-closed.
- Do not confuse an `RLock`-protected mapping with hard revocation. Lookup/removal may be race-free while an already-resolved capability continues executing after cleanup; choose and test explicit in-flight lease semantics.
- Require one production-path test that crosses the actual Host facade, empty-context runner, real dispatcher, registered provider handler, resolver, and persistence boundary. Synthetic handlers and fake agents prove components, not composition.

See `references/context-isolated-capability-registry.md` for the audit checklist and verification matrix.

## AI-Gated Durable Processing

For background memory/learning pipelines, split semantic decisions from deterministic state transitions:

```text
completed turn -> provider queue -> AI signal judge
  no signal -> terminal no-op
  signal -> formal extractor -> candidate
  candidate -> independent AI reviewer -> approve/reject
  approve/reject -> deterministic version-bound transition service
```

- A positive AI signal verdict is authoritative for entering formal extraction; do not silently apply an older keyword heuristic afterward.
- The independent reviewer must receive the actual candidate artifact and actual cited evidence content, not only IDs, paths, line numbers, or extractor summaries.
- Bind review output to candidate ID, immutable version, and content hash. Validate citations against evidence available to the reviewer before applying a transition.
- The reviewer returns semantic `approve` or `reject`; deterministic code performs promotion/rejection under the existing writer/version lease. AI code never writes accepted state directly.
- When the contract is fully AI-reviewed, uncertainty is resolved by bounded independent AI retry/arbitration or fails closed in quarantine. A malformed/failed AI call is a technical failure, not an implicit reject and not a human-review fallback.
- If the semantic gate returns no signal, avoid creating evidence/candidates. If it returns signal, preserve the existing evidence redaction and hostile-content checks at the persistence boundary.

## AI-Only Review Surface and Recovery

“Fully AI-reviewed” is a cross-surface contract, not merely an internal callback:

1. Remove or disable operator approve/reject routes from model tools, CLI commands, and shared operation facades. Leaving one reachable manual route is still a human fallback.
2. Apply the same evidence-link rule to both terminal decisions. Promotion and rejection must each cite evidence linked to the reviewed candidate/version; do not let rejection accept any profile-global evidence merely because it exists.
3. Audit every candidate producer. Bare candidates without an immutable rendered version cannot enter AI review; either add an AI rendering stage for them or remove/disable that producer rather than leave permanently quarantined records.
4. Persist enough review-stage state to recover candidates created just before a crash. On startup, rescan eligible quarantined rendered candidates or replay durable review jobs; never rely on a human to rescue orphans.
5. Use a bounded, no-tools JSON judge when available. If reusing a general agent/curator fork, require `skip_memory`, strict duplicate-key JSON parsing, bounded iterations/output, and fail-closed behavior; document tool access as a residual risk.
6. Store reviewer model/prompt provenance and retry attempts when auditability or crash recovery is part of acceptance. Existing promotion events prove successful terminal transitions, not failed or malformed review attempts.

Tests should prove the manual tool/CLI routes are absent, unrelated evidence cannot authorize either approve or reject, malformed reviews leave candidates quarantined, and restart recovery reaches an AI terminal decision without duplicate accepted versions.

## Contract-Replacement Tests

When replacing idle/session-end processing with per-completed-turn processing, update the entire lifecycle contract deliberately:

- RED: provider callback returns before a blocked signal judge finishes.
- RED: no-signal verdict never calls formal extraction and writes no evidence/candidate.
- RED: positive AI signal reaches extraction even without legacy signal keywords.
- RED: independent AI approval receives full artifacts and auto-promotes; rejection leaves accepted visibility empty.
- RED: session-end no longer creates the superseded idle checkpoint/timer.
- RED: unrelated metadata-queue overflow does not suppress provider-owned work.
- GREEN: remove stale tests that require the old timer/cancellation behavior only after replacement tests prove the new boundary.

See `references/per-turn-ai-pipeline.md` for a compact implementation and verification recipe.

## Pitfalls

- Starting a worker while holding a lock is acceptable only if the worker obtains that lock after startup; never wait for it while still holding the lock.
- Avoid the one-shot-worker lost-wakeup race: if a worker exits when the queue appears empty while enqueue refuses to start another worker because the old thread is still alive, a newly persisted job can be stranded. Prefer a resident worker plus `Event`/`Condition`; otherwise clear ownership and re-check the durable queue atomically before exit.
- A daemon thread avoids blocking interpreter shutdown but does not cancel already-running side effects. Keep worker actions idempotent and use persisted cancellation/state checks.
- Do not claim a multi-round durable workflow is fixed by writing synthetic completion events. Persist and execute the actual round boundaries.
- Avoid test races: wait for an event or terminal database state, not a guessed delay.

## Reference

See `references/event-gated-regression.md` for a reusable test shape.
