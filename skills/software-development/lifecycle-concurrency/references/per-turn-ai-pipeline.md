# Per-Turn AI Pipeline Reference

Use this recipe when replacing an idle/session-end extractor with processing after every completed, non-interrupted turn.

## Ownership

```text
host turn finalizer
  -> host memory manager background worker (ordered fan-out)
  -> provider sync_turn (enqueue only)
  -> provider-owned bounded FIFO worker
  -> AI signal judge
  -> formal extractor
  -> independent AI candidate reviewer
  -> deterministic promote/reject service
```

The provider worker is still necessary when the host has a background worker: running AI inline would monopolize the host's serialized memory worker and delay unrelated sync/prefetch work.

## Minimal work item

Capture immutable current-turn inputs supplied by the host:

```python
@dataclass(frozen=True)
class TurnWork:
    job_id: str
    session_id: str
    user_content: str
    assistant_content: str
    agent_identity: str
    platform: str
```

Do not rescan the cumulative transcript when these values already represent the current completed turn. Add an explicit host-provided `turn_messages` delta if tool results are required.

## Signal contract

Require a strict object such as:

```json
{"schema":"memory-signal/v1","has_signal":true,"reason":"stable user preference"}
```

A false verdict terminates without formal extraction or candidate/evidence writes. Invalid JSON/schema is a technical failure, not `has_signal=false`.

## Review contract

Give the reviewer:

- complete rendered candidate content;
- candidate ID, immutable version, and content hash;
- actual redacted evidence content and provenance;
- relevant citations/source spans when available.

Require a version-bound result:

```json
{
  "schema": "candidate-review/v1",
  "candidate_id": "...",
  "candidate_version": 2,
  "candidate_content_hash": "...",
  "verdict": "approve",
  "rationale": "directly supported durable fact",
  "evidence_id": "..."
}
```

Validate every binding before calling the deterministic lifecycle service. `approve` invokes promotion; `reject` invokes rejection. The AI callback never mutates accepted storage itself.

## Event-gated tests

1. Block the signal callback with `threading.Event` and assert `sync_turn` returns promptly.
2. Release in `finally`; join the provider worker with a bounded timeout.
3. Assert a false signal did not call extraction and left evidence/candidate counts at zero.
4. Assert a true signal invokes extraction even when the turn contains no legacy keyword marker.
5. Block the reviewer and inspect its context to prove complete candidate/evidence delivery.
6. Assert AI approve produces accepted visibility and AI reject does not.
7. Assert session end creates no old idle checkpoint/timer.
8. Replace the unrelated lifecycle queue with an overflow stub and prove extraction still runs.
9. Assert no manual candidate-review tool, CLI command, or shared operation facade remains when review is AI-only.
10. Assert both AI approve and AI reject refuse evidence unrelated to the candidate.
11. Simulate a crash after candidate creation and prove startup recovery resumes AI review without duplicate promotion.
12. Run focused lifecycle tests, full suite, syntax compilation, and diff whitespace checks.

## AI-only closure checklist

- Every candidate producer either creates a rendered, reviewable version or is removed/disabled.
- Review requests contain actual candidate/evidence artifacts and are bound to ID/version/hash.
- Approve and reject use symmetric linked-evidence checks under the writer/version lease.
- Manual approve/reject surfaces are absent, not merely unused by the happy path.
- Failed/malformed reviews remain quarantined and enter bounded automatic retry/recovery.
- The AI runtime is isolated (`skip_memory`) and preferably no-tools with bounded iterations/output.
- Successful and failed review attempts retain enough model/prompt provenance for audit when required.

## Common failure modes

- Returning early after an unrelated metadata queue overflow drops authoritative work.
- Running the signal judge inside the host memory worker serializes all provider activity behind an LLM call.
- Keeping a local keyword filter after a positive AI verdict creates a hidden second semantic gate.
- Passing only candidate IDs or summaries lets the reviewer approve unverifiable claims.
- Treating malformed AI output as reject hides infrastructure failures and destroys valid candidates.
- Updating session-end tests without adding per-turn replacement coverage erases the lifecycle contract instead of changing it.
