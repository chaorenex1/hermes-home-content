# Diagnosing Missing Memory Candidates

Use this playbook when a conversation appears to contain durable knowledge but no expected memory is visible. Diagnose the first broken stage before changing prompts or lowering review standards.

## 1. Establish the runtime source of truth

Configuration saying a provider is enabled is not proof that it initialized successfully.

Verify together:

- the module path actually imported by the running Hermes environment;
- the installed package build/version or source revision;
- the provider schema contract versus the live store schema;
- an end-to-end provider health/init check;
- whether provider-owned tools are bound to an initialized instance.

Compare the deployed artifact with the working checkout. If they differ, repair deployment first. Do not tune extraction prompts against code that is not running.

## 2. Follow one session through the pipeline

Use session IDs and immutable message/turn identifiers to check each stage:

| Observed state | Meaning | Investigate next |
|---|---|---|
| No turn job and no evidence | The turn never entered provider extraction | provider initialization, primary-provider selection, lifecycle hook, session binding |
| Job exists but no route | Signal/type router skipped it | router input, empty-signal decision, type limits |
| `completed_empty` | Extraction ran and deliberately produced no candidate | evidence sufficiency, novelty, type boundary, prompt input window |
| `rejected` / `output_rejected` | Model output failed a contract | exact schema error, field validation, candidate rendering |
| `failed` | Runtime/storage stage failed | phase, exception message/stack, transaction state, recovery |
| Candidate quarantined without lifecycle progress | Extraction succeeded but review/promotion stalled | rendered candidate version, evidence binding, reviewer output, staged plan |
| Candidate promoted | It was extracted; the symptom is retrieval, indexing, path, or duplicate perception | accepted document path, projection state, retrieval filters |

Never report “nothing was extracted” until every candidate related to the topic has been checked; a sibling project document may already have been promoted while its event or trajectory representation was rejected.

## 3. Inspect the actual evidence window

Trace the DTO passed to routing, extraction, review, and promotion—not merely the host method signature.

Check whether extraction receives:

- only the current user/assistant pair;
- bounded multi-turn messages;
- tool calls and actual tool results;
- user corrections from later turns;
- artifact/test evidence;
- source authority and version metadata.

A current-turn-only extractor cannot reliably produce multi-turn trajectories, problem-resolution experiences, or tool lessons whose verification appears in later tool results. Keep the evidence rule strict; widen the evidence window instead of promoting assistant summaries as user facts.

## 4. Separate semantic absence from pipeline absence

Classify the failure before proposing a fix:

- **Pipeline absence:** no durable job/evidence. Repair runtime initialization or lifecycle delivery.
- **Evidence absence:** job ran but the required direct evidence was not in its input. Add bounded session/tool evidence or a session-end replay path.
- **Semantic rejection:** evidence was present but the candidate violated type, novelty, or schema contracts. Fix the router/template/schema mismatch.
- **Already represented:** a related accepted document exists. Merge/update it rather than creating a duplicate.

## 5. Recovery rules

- Deploy the intended provider artifact into the environment that actually runs Hermes, then restart the owning process and verify initialization.
- A restored post-turn worker does not automatically recover turns that were never persisted. Provide an explicit bounded backfill/replay path from the canonical session store.
- Preserve complete phase and validation diagnostics; storing only an exception class is insufficient for repair.
- Backfill must retain original session/message evidence, redact secrets, deduplicate by turn/type key, and route through the normal independent review and promotion gates.

## Verification

A repair is complete only when all of these pass:

1. Runtime import path/build and store schema are compatible.
2. Provider health/init succeeds in the actual Hermes environment.
3. One new controlled turn creates a durable turn/type record.
4. Its evidence resolves to the original user/tool content.
5. A supported fixture reaches quarantine and independent review.
6. A no-candidate fixture reaches `completed_empty` without an error.
7. A missed-session replay is idempotent and does not duplicate accepted documents.
