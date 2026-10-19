# AI Candidate Review and Automatic Promotion — Reference Pattern

Use this as a concrete source-map/checklist when auditing a persisted memory-candidate system.

## Canonical lifecycle

```text
producer/classifier
  → quarantined candidate
  → immutable rendered candidate version
  → immutable evidence references + claim spans
  → independent AI reviewer rereads persisted state
  → validated approve/reject verdict
  → expected-version terminal transaction
  → accepted-only projection (approve) or terminal rejection (reject)
```

## Minimal reviewer request

Include only durable, redacted, bounded state:

- stable `candidate_id`
- latest `candidate_version`
- original candidate content
- immutable rendered content
- all linked evidence records
- claim-to-source spans

Do not pass only the producer's in-memory proposal. Do not let the model choose the actor, candidate ID, or version used for mutation.

## Minimal closed verdict

```json
{
  "decision": "approve",
  "rationale": "Evidence supports the rendered claim.",
  "evidence_id": "one ID from the request"
}
```

Allow only `approve` or `reject`; require a bounded non-empty rationale; require the cited evidence ID to belong to the candidate or rendered claims; reject unknown fields. Apply the request's ID/version under an optimistic transaction.

## Schema decision

A new migration is usually **not required** when the existing schema already has:

- quarantined/promoted/rejected candidate lifecycle states
- immutable candidate versions
- accepted versions linked to candidate/version
- append-only decision events with evidence, actor, rationale, and timestamp

A migration becomes necessary when acceptance requires durable review-attempt state, model/prompt/version provenance, retry/backoff accounting, malformed-response audit, or multiple cited evidence IDs per verdict.

## Common integration gaps

1. Promotion validates candidate-linked evidence but rejection validates only global evidence existence.
2. A config flag exists but no runtime reads it.
3. Provider tests inject a reviewer callback, but normal installed-host initialization never supplies one.
4. The extraction scheduler returns candidate IDs, but the provider discards the result.
5. Tool/CLI/manual review remains exposed despite a “no human fallback” requirement.
6. Some creation paths produce bare candidates without a rendered version, making automatic promotion impossible.
7. Callback failure leaves candidates permanently quarantined because no bounded startup/tick rescan exists.

## Focused test matrix

- reviewer sees the persisted version/evidence, not producer output
- approve creates exactly one accepted version/event and accepted retrieval visibility
- reject creates no accepted state and marks candidate rejected
- unrelated evidence rejected on both branches
- stale version fails closed
- malformed/exception verdict leaves quarantine and invokes no operator path
- replay/startup recovery is idempotent
- all candidate creation paths become reviewable or are removed
- production host wiring works without test-only injection
- manual review tool/CLI surfaces are absent or explicitly disabled
