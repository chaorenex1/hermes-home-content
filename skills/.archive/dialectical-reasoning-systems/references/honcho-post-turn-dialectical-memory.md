# Honcho and Post-Turn Dialectical Memory Loops

## Scope

Condensed July 2026 comparison between Hermes' Honcho provider and a local evidence-driven memory provider. Use this when deciding whether a proposed “dialectical” mechanism is online decision review or post-turn memory maintenance.

Authoritative Honcho documentation: <https://hermes-agent.nousresearch.com/docs/zh-Hans/user-guide/features/honcho>

## Honcho Reference Model

Honcho is a post-turn, next-turn-effect user-modeling backend:

```text
turn completes
  → persist user/assistant messages
  → refresh base peer context on contextCadence
  → run dialectic on dialecticCadence
  → execute up to dialecticDepth passes
  → cache representation/card/session context + dialectic supplement
next query
  → prefetch injects the ready context
```

Its passes are semantically:

1. cold user assessment or warm session positioning;
2. self-audit and evidence-grounded gap filling;
3. reconciliation and contradiction synthesis.

`dialecticCadence` decides whether a dialectic call fires; `dialecticDepth` bounds one to three passes. Later passes can stop early. This is different from both an opportunity-gated pre-action critic and an every-pass-mandatory fixed-round controller.

Honcho injects two layers:

- base context: representation, peer card, session summary/recent context;
- dialectic supplement: synthesized `peer.chat()` result.

It supports session prewarm, per-pass reasoning levels, query-length reasoning heuristics, `hybrid|context|tools` recall modes, and peer observation controls (`observeMe` / `observeOthers`). Its service owns raw messages, conclusions, cards, representations, and semantic search.

## Stronger Local Control-Plane Pattern

A file-canonical local provider may reuse Honcho's pass semantics while adding:

- a typed Session Working Set for goals, tasks, plans, decisions, artifacts, and runtime state;
- typed accepted memory (`identity`, `preference`, `projects`, `trajectories`, `experiences`, `tools`, etc.);
- persisted `RetrievalIntent(goal, memory_types, query_hash, budgets)` records;
- accepted-document/version/citation materializations;
- quarantine candidate, independent review, promotion, supersession, and revocation lifecycles;
- exact injection receipts and `used|helpful|contradicted|no_opportunity` feedback;
- reviewable, base-hash-fenced profile/SOUL improvement proposals.

The intended orchestration is:

```text
completed turn transcript + structured tool evidence
  → normalize runtime working state
  → pass 1: profile/session/project grounding
  → validated retrieval intent for identity/preference/projects
  → accepted-only retrieval + citation materialization
  → pass 2: gaps, prior trajectories, experiences, tool lessons
  → optional second validated retrieval intent
  → pass 3: reconcile without widening topic or memory types
  → atomically commit dynamic model and working-state operations
  → persist a model snapshot, not final injection text
next query
  → query-filter model snapshot + working state + current accepted memory
  → create exact injection offer and receipt
```

## Evidence Boundaries

- Complete Hermes messages may include assistant tool calls and tool results. If the host passes them, normalize and freeze them before reasoning; do not reduce the evidence to only the final user/assistant strings.
- A provider LLM callback cannot be assumed to call `session_search` or arbitrary agent tools. Cross-session raw history requires an explicit bounded host interface.
- `kb_search` over accepted memory is not raw-session-history search. Keep current-session transcript evidence, historical session retrieval, and accepted long-term knowledge distinct.
- Long-term memory becoming “short-term context” means a citation-bound session materialization, not copying the body into conversation-authority working state.
- Newly extracted quarantine candidates cannot feed the same run's retrieval. Only accepted, currently visible versions may be recalled.
- Assistant text may update a session summary, but must not alone establish stable user preferences, habits, goals, or profile policy.
- Dynamic observations cannot directly edit `SOUL.md`; they may only support an independently reviewed improvement proposal.

## Coverage Metrics

For an R1-always, R2/R3-adaptive post-turn system, report:

- grounding coverage over all completed turns;
- continuation recall for cases independently labeled as requiring R2 or R3;
- evidence coverage and state-revision correctness;
- query-specific injection opportunity and adoption;
- latency/cost per actual depth.

Do not count a valid R1-only routine turn as missing coverage. Do not call invocation on every turn effective dialectical coverage.

## Implementation Audit Questions

1. Does the host call happen before or after the answer?
2. Does the callback receive full messages or only the final pair?
3. Are pass roles enforced by schema/state, or only described in prose?
4. Can pass output create a validated retrieval intent between passes?
5. Does retrieval search accepted memory, raw history, or both?
6. Is next-turn injection query-filtered after the next query arrives?
7. Are accepted memory, dynamic profile, and working state kept at distinct authority levels?
8. Is feedback bound to the exact injected snapshot?
9. Can assistant-only output pollute stable user modeling?
10. Are profile-policy changes proposals rather than direct writes?
