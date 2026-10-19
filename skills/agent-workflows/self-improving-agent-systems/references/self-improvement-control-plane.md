# Self-improvement control plane

## Artifact states

```text
candidate | quarantined
  -> approved -> accepted
  -> rejected
accepted -> review_required -> expired | superseded | revoked
```

Candidates are stored and reviewed separately. They must not update default retrieval indexes, summaries, embeddings, or prefetched context.

## Minimal records

### Evidence

```yaml
evidence_id: uuid
source_kind: user_confirmed|local_tool_result|test_result|session_message|subagent_output|web_content|imported_file
source_ref: opaque audit reference
content_hash: sha256
captured_at: ISO-8601
trust_level: operator_confirmed|local_verified|agent_inferred|external_untrusted
redaction_state: clean|redacted|rejected
```

### Learning candidate

```yaml
candidate_id: uuid
artifact_kind: memory|knowledge_document|experience|failure_pattern|skill_proposal
status: candidate
scope: user|profile|project|session
importance: 0.0
confidence: 0.0
verification_state: unverified|verified|contradicted
valid_from: optional
valid_until: optional
evidence_ids: []
extraction_version: version
supersedes: optional
```

## Promotion policy

- User-confirmed content may be promoted after schema and provenance validation.
- Agent/subagent/web/file-derived content starts as candidate; it requires review or deterministic verification before promotion.
- Promotion checks the expected version, records the actor and rationale, then atomically exposes the accepted artifact to normal retrieval.
- Rejection, revocation, and expiry retain audit evidence but remove the artifact from default retrieval.

## Plan acceptance checklist

- Candidate material cannot leak through summary/index generation before promotion.
- Importance, confidence, and trust are separate fields.
- All automatic writes have a provenance record and a bounded scope.
- Failed or corrected trajectories can become reviewable failure-pattern candidates.
- Knowledge-layer skill proposals use the skill approval/diff path, not direct skill mutation.
- Future outcomes link to the learning artifacts used and feed retention/review decisions.
- Tests cover rollback, profile isolation, candidate leakage, conflicting evidence, and hostile retrieved content.
