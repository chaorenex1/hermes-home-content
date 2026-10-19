# Memory Retrieval Pipeline Audit

Use this reference when a memory provider combines cached prefetch, explicit search tools, directory summaries, lexical indexes, optional vector search, and canonical body reads.

## Audit the timing contract first

Trace two independent routes end to end:

1. **Automatic recall**: completed turn → queued prefetch query → background worker → cache publication → next turn `prefetch()` → request-only context injection.
2. **Explicit recall**: model tool call or CLI → query parser → retriever → result serialization → optional body-read tool.

Do not assume `prefetch(current_query)` searches the current query. Some providers intentionally return a cache generated from the previous turn. Record:

- which turn supplies the search query;
- which turn consumes the result;
- whether the current query is ignored;
- first-turn behavior;
- topic-switch behavior;
- stale-result fencing and session-switch invalidation;
- whether injected context is persisted as clean transcript content or only as API-bound sidecar data.

## Projection-to-result reachability

For every configured projection mode, prove a hit can reach the public result, not merely an internal sufficiency flag.

Trace:

```text
accepted canonical source
  → metadata/status filter
  → lexical/vector candidate selection
  → canonical body read
  → result object construction
  → prefetch/tool serialization
  → model-visible context
```

A common defect is: body selection and reading succeed, evidence IDs are recorded, and `sufficient=true`, but result construction requires a directory summary. When summaries are disabled or unavailable, `results` stays empty and automatic prefetch injects nothing. Add a focused probe that asserts both `body_read_document_ids` and non-empty public results.

## Scope every round independently

Check `path`, `recursive`, `memory_types`, tenant/profile/session, and accepted/current status at every retrieval stage:

- summary lexical search;
- summary vector search;
- hybrid merge;
- body-gap selection;
- fallback traversal;
- result serialization.

A Round 2 filter does not repair a Round 1 leak. Test a query whose only matching summary is outside the requested type/path and require no hit. Telemetry such as `searched_memory_types` must describe actual executed scope, not requested intent.

## Name the real algorithm

Verify implementation rather than trusting audit labels such as `summary-fts` or `hybrid`:

- `MATCH`/BM25 means FTS; loading all rows and applying substring `all(...)` is a deterministic scan.
- Concatenating vector hits before lexical hits is not score fusion or reciprocal-rank fusion.
- A local hash bag-of-words embedding is lexical hashing, not semantic embedding.
- `1/rank` is positional scoring, not relevance scoring.

Report requested mode, actual mode, fallback reason, and whether `degraded` has a precise operational meaning.

## Sufficiency and evidence semantics

Determine whether completion is judged by an AI, a lexical coverage predicate, or a state-machine rule. For lexical coverage, inspect tokenization for punctuation, phrases, CJK text, case folding, and cross-document concatenation. A query term appearing anywhere in the combined corpus is not proof that one result answers the request.

Verify that returned evidence IDs identify documents actually read or represented by the returned result. Do not treat all documents under a directory summary as query evidence by default.

## Configuration and runtime adoption

Check the live selected profile, deployed provider, and repository source separately:

1. provider is selected and initialized;
2. deployed retrieval code matches the analyzed source;
3. profile config parses under the deployed schema;
4. configured mode is actually reachable (backend, dimension, dependency);
5. summary generation is enabled when result construction depends on summaries;
6. every advertised limit is read by runtime code;
7. per-round deadlines are reset per round rather than once per request;
8. disabled-loop or projection settings actually alter execution.

Tool schemas may remain visible even when provider initialization failed, so a schema list is not proof of a working backend. Verify with one status/search call or a direct config-load probe.

## Minimal deterministic probes

Use disposable profile state and redacted output.

### No-summary reachability

- Disable summaries.
- Add one accepted document containing the query.
- Search with lexical mode.
- Assert canonical body read occurred.
- Assert the public result is non-empty and contains a stable document/directory handle.

### Round-scope isolation

- Enable summaries.
- Add a matching document only under an excluded memory type/path.
- Search with a different requested type/path and `max_rounds=1`.
- Assert no result and truthful scope telemetry.

### Runtime readiness

- Load the active profile config through the deployed provider parser.
- Check selected provider name.
- Invoke bounded provider status/search.
- Distinguish `schema advertised` from `provider initialized`.

## Goal-driven AI loop contract

When the target design is `search(goal, memory_types?)`, audit it as a bounded state machine rather than a renamed query function:

1. **Type routing:** explicit types bypass AI; omitted, null, or empty types invoke an AI router. Validate the router's closed output against the host-owned type enum and never let the model invent types or paths.
2. **Summary round:** actual FTS over `summary` plus `detailed_summary` is restricted to the selected type roots. An AI Judge receives the real candidate text and bound document IDs/paths.
3. **Tree escalation:** if summaries are insufficient, expose a bounded accepted-only tree containing stable document ID, logical path, and title/filename, but no body or host path.
4. **Body rounds:** an AI selector may choose at most the configured global candidate cap (for example ten) from supplied, in-scope, unvisited IDs. Read bodies through the canonical accepted store with current status/hash validation.
5. **Retry meaning:** “two Judge retries” should produce new evidence on each retry. Persist visited IDs and stop on repeated selection, exhausted tree, timeout, or no progress; never re-judge identical evidence as a new round.
6. **Terminal synthesis:** return `answered`, `partial`, `no_match`, or `failed` with bounded evidence and truthful missing/truncation state. Exhaustion preserves useful partial information.

Test each transition directly: explicit-type bypass, empty-type routing, summary-only stop with zero body reads, out-of-scope summary rejection, candidate-cap enforcement, canonical-body read, two-retry ceiling, no-progress stop, and grounded partial output.

## External prompt-template authority

When AI semantics are profile-editable templates, verify four distinct states for every prompt: **stored, loadable, enforced, frozen for one run**.

- Keep templates under the declared profile-local root (for example `HERMES_HOME/<provider>/prompts/`) and identify every required template ID: type router, summary Judge, tree selector, body Judge, result synthesizer, and directory-summary generation.
- Templates own natural-language semantics. Runtime code owns exact JSON request/response schemas, allowed types, accepted-only checks, path/ID authorization, candidate caps, evidence binding, budgets, and terminal transitions.
- Prefer `template text + a host-serialized bounded JSON payload`; do not allow template expressions to execute code or construct arbitrary filesystem paths.
- Load regular UTF-8 non-symlink files with size and non-empty checks. If external templates are authoritative, missing/invalid templates fail closed; a hidden hardcoded semantic fallback violates the contract.
- Snapshot template bytes/hashes once at search start and persist those hashes with the loop run. Mid-run edits affect later searches, not later rounds of the current search.
- A template storage class is not production adoption. Trace every AI callsite and use a unique sentinel test to prove the selected external template reaches the real router/Judge/selector/synthesizer prompt.
- Avoid conflating memory-content templates with control templates: content templates define one memory type's document body; retrieval templates define routing/judging/selection/synthesis semantics.

## Evidence report format

Report:

1. **live readiness** — selected provider, config parse, initialization, actual mode;
2. **automatic route** — query turn → worker/cache → consumption turn → injection;
3. **explicit route** — tool/CLI → retriever → body-read escalation;
4. **round table** — source, filter, ranking, body access, stop condition;
5. **projection reachability** — summary enabled/disabled and vector available/unavailable;
6. **verified defects** — reproduction output plus exact function/line;
7. **test evidence** — passing existing tests separately from missing regression coverage.
