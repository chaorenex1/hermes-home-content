# Dynamic User-Profile Modeling Audit Reference

Use this reference to audit LLM-maintained user profiles, preference stores, identity documents, session summaries, and post-answer adoption loops.

## 1. Layer and authority map

Build this table before judging implementation quality:

| Layer | Typical fields | Scope | Expected authority | Required lifecycle |
|---|---|---|---|---|
| Current turn | explicit instruction/correction | turn | highest for current answer | immutable evidence |
| Session working state | goal, task, plan, decision, focus | profile + agent + session + workspace | temporary operational context | active/blocked/completed/superseded/stale |
| Dynamic profile | user representation, profile card, observations, conclusions | profile/agent, sometimes workspace | contextual hypothesis unless independently verified | versioned update, contradiction, supersession, decay |
| Accepted user memory | preference, identity, durable project facts | profile | evidence-reviewed long-term knowledge | candidate/review/accept/revoke/supersede |
| Agent policy | SOUL/system behavior | agent profile | host policy, not user memory | separately authorized change path |

A system is unsafe or semantically confused when these layers share one write path or when a lower-authority summary silently overrides a current user correction.

## 2. Field/provenance matrix

For every field that reaches model context, record:

| Question | Evidence to locate |
|---|---|
| Who produces it? | prompt/callback and production wiring |
| What exact input is visible? | current turn, full transcript, prior profile, accepted memory, tool data |
| Is it source-linked? | evidence IDs, source spans, session/message IDs |
| Is confidence stored? | host-validated numeric field, not prose alone |
| Is it reviewed independently? | persisted artifact reread by a distinct reviewer |
| Can it be corrected? | revise/contradict/supersede operations with expected version |
| Can it expire? | TTL, stale transition, session-end transition, decay |
| Is it query-fenced? | topic/query hash or semantic selection before injection |
| Is use measured? | exact injection receipt plus conservative attribution |
| Can it affect policy? | must be no unless routed through a separate policy gate |

A common asymmetry is strict evidence validation for individual insight objects while free-form `user_representation` or `profile_card` fields are validated only for type and length. Treat the free-form fields as the higher-risk surface if they are always injected.

## 3. Deterministic correction probe

Use a disposable profile and a deterministic reasoner callback. The probe should:

1. Infer session A with a preference such as “prefers concise answers.”
2. Open session B under the same profile and confirm profile warmth is available while session warmth remains cold.
3. Infer an explicit correction such as “actually prefers detailed answers.”
4. Read the final profile and rendered next-turn injection.
5. Assert that the old preference no longer has behavioral effect.

Pseudo-contract:

```text
infer(profile=P, session=A, representation=old, observations=[old])
assert snapshot(profile=P, session=B).representation == old
infer(profile=P, session=B, representation=new, observations=[])
final = snapshot(profile=P, session=B)
assert final.representation == new
assert old not in active(final.observations + final.conclusions)
assert old not in prepare_injection(profile=P, session=B)
```

If the final representation changes but the old structured insight remains active or injectable, the system has summary replacement but not profile correction.

Add companion probes for:

- paraphrase duplicates producing separate content-hash IDs;
- contradictory accepted preference versus dynamic profile;
- topic switch before the post-turn model has refreshed focus;
- two writers reasoning from the same base version;
- restart during queued or running profile inference;
- repeated “revise” reviewer verdicts reaching the configured quota.

## 4. Authority-order checklist

Require one explicit, tested order. A conservative default is:

```text
current explicit instruction
> current explicit correction
> current verified tool/operator state
> latest accepted user memory
> active evidence-linked profile observation
> calibrated profile conclusion
> old free-form profile card or session summary
```

The order must be implemented by selection, suppression, or conflict annotation before context reaches the answer model. Merely placing two contradictory tagged blocks next to each other is not conflict resolution.

## 5. Adoption and usefulness feedback

An adoption Judge should receive:

- exact injection ID and content hash;
- current user query;
- assistant response;
- exact subject IDs/versions offered;
- a rubric that rejects topical overlap, direct user requirements, and generic best practice as adoption.

Audit coverage, not only Judge quality. If the receipt tracks insight IDs but always-injected summary/profile-card fields have no IDs, those fields are outside the feedback loop. `no_opportunity` should not count as negative evidence. Contradiction should create a lifecycle or review signal, not just lower rank.

## 6. Authoring reachability

Do not infer a capability from an enum, template, renderer, path validator, search filter, or tool schema alone. For every declared memory type—especially explicit-only identity—trace:

```text
public/host action
→ evidence capture
→ renderer call
→ versioned candidate artifact
→ independent review
→ accepted write
→ retrieval visibility
→ revision/revocation
```

A renderer with zero callers means the type is representable but not authorable. A search enum means retrieval accepts the type, not that production can create it.

## 7. Review exhaustion and failure semantics

Every candidate-review branch must terminate symmetrically:

- approve → promote exact reviewed hash/version;
- reject → terminal rejected;
- revise → bounded new version and fresh review;
- invalid callback → fail closed;
- stale version → fail closed;
- quota exhausted → rejected/blocked/exhausted, never approved.

Search explicitly for promotion calls inside quota-exhaustion branches. Labels such as `approved_by_policy`, `review_quota`, or `fallback_accept` are high-risk even when ordinary reviewer failures reject correctly.

## 8. Concurrency and durability

Reasoning commonly occurs outside a lock, so the commit needs a base version or hash. Re-reading latest state and then selecting `new_value or latest_value` is not conflict resolution: a stale non-empty value can overwrite a newer one. Prefer:

- expected profile/session artifact version;
- compare-and-swap commit;
- deterministic field-level merge for independent keys;
- conflict state and bounded retry for overlapping free-form fields.

A “durable job” that stores only scope and input hashes may be auditable but not replayable. Report audit durability separately from execution recovery. Privacy-preserving non-replayability can be an intentional trade-off, but lost turns must be named accurately.

## 9. Test evidence standard

Separate:

1. schema/storage tests;
2. callback-injected unit tests;
3. production-loader wiring tests;
4. semantic profile-behavior probes;
5. concurrency/restart tests.

Tests that always return empty `user_representation` and `profile_card` do not validate user-profile modeling even if queues, prompts, and tables pass. Report the full suite result, then list missing semantic invariants separately.

## 10. Common false-positive claims

- “Evidence-grounded profile” when only insight arrays carry evidence but the injected profile card does not.
- “Corrects stale preferences” when the summary changes but old insights remain active.
- “Adoption-aware” when only one subset of injected fields has trackable IDs.
- “Identity supported” when identity can be searched but not authored.
- “Independent AI review” when revision exhaustion promotes without an approve verdict.
- “Durable inference” when restart marks work failed but cannot replay the frozen input.
- “Profile isolated” when agent/session hashes exist but one shared free-form artifact ignores workspace or tenant boundaries without an explicit contract.
