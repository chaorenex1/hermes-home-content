# Per-turn extraction audit: Hermes memory providers

Use this reference when a Hermes memory provider is being changed from idle/session-end extraction to extraction after every completed turn.

## Authoritative lifecycle route

- `MemoryProvider.sync_turn(user_content, assistant_content, session_id=..., messages=...)` is the completed-turn provider boundary. The host contract says it is called after each turn and should be non-blocking.
- `MemoryManager.sync_all(...)` dispatches provider sync on one serialized background worker, preserving turn order.
- `AIAgent._sync_external_memory_for_turn(...)` excludes interrupted turns before calling `sync_all`; retain that upstream exclusion.
- `on_session_end(messages)` is a real session-boundary hook (exit, reset, expiry), not a per-turn hook.
- `on_turn_start(...)` occurs before prefetch and sees only new user activity; it is the wrong place to build a completed-turn extraction window.

## Audit findings that generalize

1. A scheduler key such as `idle-extraction:{session_id}` or a pipeline checkpoint such as `extraction:{session_id}` has session cardinality. Per-turn cadence requires event/job cardinality, e.g. a digest of session ID, stable end-message watermark, and extractor version.
2. Do not implement per-turn behavior by setting an idle delay to zero. Session-keyed jobs still overwrite each other, and new-turn cancellation still destroys completed-turn work.
3. The `messages` argument may contain the full transcript. Slice from the current turn's final user boundary through tool calls/results and the final assistant response; do not repeatedly submit a trailing-N window.
4. Avoid reading a mutable provider turn counter inside delayed `sync_turn` work. The host may have started the next turn before the background callback executes. Use a stable message/event watermark captured with the completed turn.
5. Search the real loader for callback construction. Test-only initialization kwargs such as classifier/planner/judge callbacks do not prove production reachability.
6. Inspect persistence order. If evidence rows are immutable and all messages are written before signal detection, per-turn cadence silently creates a durable transcript archive. Prefer ephemeral redaction and classification, then persist only cited evidence and candidate mutations atomically.
7. Preserve quarantine semantics. Extraction cadence and accepted-memory promotion are separate policy changes.

## Recommended state machine

```text
completed non-interrupted turn
  -> serialized host sync
  -> current-turn delta + stable watermark
  -> ephemeral redaction/signal gate
  -> durable job keyed by event identity
  -> bounded background worker
  -> classifier/planner/judge
  -> cited evidence + quarantined candidate transaction
  -> extracted | empty | rejected | backoff | failed_terminal
```

A later user turn does not cancel a completed-turn job. Session end becomes a flush/fallback boundary. Retry timers may remain, but idle-eligibility timers should not.

## Provider-owned workers and automatic candidate review

When the host already dispatches `sync_turn` on a serialized worker, a provider-owned worker is still a distinct lifecycle boundary. Audit both layers:

1. The host must snapshot mutable message input before submitting its closure; copying inside the delayed provider callback is too late if the host mutates the list first.
2. `sync_turn` should make one immutable, event-keyed handoff and return. The provider worker owns a bounded FIFO and a single drain loop; session switch/new input must not clear completed-turn work.
3. Host shutdown must first deliver queued callbacks, then provider shutdown must either drain or durably checkpoint accepted work. A short join on a daemon thread is not recovery: already-running side effects may continue after shutdown while queued work disappears.
4. Keep the signal gate ephemeral. Persisting all messages and then checking for a signal turns no-signal turns into a transcript archive. If pre-signal crash recovery is required, the host must provide stable transcript references or an explicit durable event source; do not solve it by persisting bodies before classification.
5. If extraction is followed by automatic AI Candidate Review, model it as a separate stage and invocation: `signal -> extraction -> candidate review -> promote|reject`. An extraction completeness judge is not a candidate reviewer.
6. "No human fallback" requires durable review-stage ownership. A crash after candidate creation must resume automatic review; it must not silently leave an ordinary quarantined candidate that an operator is expected to discover. Malformed or unavailable review output should enter bounded retry/backoff or terminal automation failure, never fabricate approval or rejection.
7. Reuse version-fenced atomic promotion/rejection primitives, but persist reviewer identity, rationale, candidate version, and evidence linkage. Review every touched candidate independently; one failed review must not corrupt sibling decisions.
8. Test-only callback kwargs are not production AI wiring. Trace the real loader. If production reuses a general agent/curator helper, verify strict duplicate-key JSON parsing, bounded input/output/iterations, recursive-memory exclusion, and a no-tools execution surface before granting automatic promotion authority.

Recommended class-level API shapes are immutable `TurnExtractionWork`, strict `SignalVerdict`, version-bound `CandidateReviewRequest`, and `CandidateReviewVerdict(decision: approve|reject, rationale, reviewer provider/model)`. Prefer one production inference protocol with separate methods over unrelated ad-hoc kwargs, while preserving callback injection for deterministic tests.

## Minimum regression matrix

- Two rapid completed turns create two durable jobs and neither is overwritten.
- Duplicate delivery of one completed turn is idempotent.
- Interrupted turns create no job.
- New-turn start does not cancel prior completed-turn work.
- Full transcript input is reduced to the current-turn delta.
- No-signal turns do not persist message bodies.
- Tool provenance and source spans survive extraction.
- Pending/backoff jobs recover after restart.
- Production startup provides the inference dependency without test-only injection.
- Candidate extraction never directly writes accepted memory or Skills.
- A positive signal runs extraction before a separate Candidate Review invocation; approve promotes atomically and reject never creates accepted visibility.
- A crash after candidate creation resumes automatic review instead of exposing a human-fallback queue.
- Malformed reviewer output retries or fails terminally without fabricating a decision.
- Session switch preserves already-completed turn jobs, and shutdown remains bounded while retaining durable accepted work.
- Blocking the first turn with an event while enqueueing a second proves FIFO order and one-worker ownership without timing-only sleeps.

## Configuration migration

When replacing idle cadence, migrate or tolerate legacy delay fields instead of making existing profile files invalid. Verify queue depth, retries, maximum rounds/candidates, and concurrency are read by runtime code; declarations alone are not evidence.
