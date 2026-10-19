# Memory-Profile Recommendation Systems

Use this reference when an agent memory provider, user model, or knowledge base will personalize recommendations over Skills, tools, workflows, documents, products, or other catalog items.

## 1. Establish the two-sided contract

A recommender needs both:

1. **User/profile evidence** — current instructions, session state, accepted preferences/identity/projects, evidence-linked dynamic insights, and verified prior outcomes.
2. **A versioned candidate catalog** — stable item ID/version, availability, requirements, risks, cost, descriptive fields, and catalog snapshot version.

Do not store catalog inventory as accepted user memory. Catalog content changes independently and belongs in a rebuildable catalog projection. Do not let quarantined memory influence ranking.

## 2. Build a side-effect-free profile snapshot

Create one immutable `RecommendationProfileSnapshot` per request. It should bind:

- profile/agent/session/workspace scope;
- current goal/query hash;
- working-set version;
- accepted document IDs and versions;
- active dynamic insight IDs, confidence, and lifecycle state;
- current explicit positive/negative constraints;
- catalog snapshot and ranking policy version;
- final snapshot hash.

Authority order:

```text
current explicit instruction/correction
> current session state
> accepted identity/preference/project memory
> active evidence-linked dynamic insight
> verified recommendation outcomes
> generic defaults
```

Do not reuse a method that records model-context injection or increments adoption counters. Read state through a dedicated assembler and issue a recommendation-specific receipt.

## 3. Pipeline

```text
goal + catalog snapshot
→ profile snapshot
→ hard availability/safety/constraint filters
→ lexical/structured or vector candidate recall
→ deterministic feature score
→ optional schema-bound AI rerank of supplied IDs only
→ diversity/cooldown pass
→ result artifact + impression receipt
→ explicit or verified outcome events
→ rebuildable statistics/projections
```

Hard filters precede every score. An explicit contradiction or unavailable item is excluded, not merely penalized. AI can reorder only an authorized candidate subset and cite only evidence contained in the profile snapshot. Unknown item IDs, unknown evidence refs, duplicate IDs, or constraint violations fail closed.

## 4. Ranking baseline

A reasonable cold-start feature mix is:

| Feature | Weight |
|---|---:|
| Current-goal relevance | 0.30 |
| Accepted-preference fit | 0.25 |
| Current-project/task fit | 0.15 |
| Verified success prior | 0.15 |
| Novelty/diversity | 0.10 |
| Evidence confidence | 0.05 |

The positive weights sum to 1.0. Apply explicit penalties separately for repeated exposure, cost/risk mismatch, and unresolved prior failure. Use a neutral prior when no verified outcomes exist. Never infer success from the assistant mentioning or choosing its own recommendation.

Return `personalized` and `degraded` truthfully. Common degraded reasons include no accepted profile evidence, unavailable semantic/vector backend, AI reranker failure, or insufficient verified outcome history. Lexical fallback is valid but must not be described as semantic retrieval.

## 5. Persistence boundary

For file-canonical systems, write the full request/profile/catalog/ranking/evidence package to a versioned artifact such as:

```text
history/recommendations/<request-id>.json
```

Keep SQLite/control storage limited to IDs, scope hashes, artifact hashes/paths, snapshot versions, status, ranks/scores, timestamps, and append-only events.

Recommended logical records:

- `recommendation_requests` — scope, goal hash, profile/catalog/policy hashes, lifecycle status;
- `recommendation_impressions` — item ID/version, displayed rank, score, exposure time;
- `recommendation_outcomes` — append-only outcome event and authorized evidence reference;
- optional rebuildable `recommendation_item_stats` projection.

Do not overload memory-injection feedback. Memory feedback answers whether context influenced an answer; recommendation feedback answers whether an item was selected, attempted, useful, or harmful.

## 6. Outcome semantics

Use explicit states such as:

```text
selected | dismissed | attempted | succeeded | failed | corrected | no_opportunity
```

Accept evidence only from declared sources such as explicit user feedback, a bound tool result, verification output, or an operator event. `no_opportunity` is neutral. A failure may lower the item only for the same applicable environment/constraint state; do not turn one contextual failure into a global negative preference.

## 7. API shape

A safe recommendation request names a catalog adapter rather than allowing an AI to invent inventory:

```json
{
  "goal": "Choose a workflow for the current task",
  "catalogs": ["skills", "tools"],
  "constraints": {},
  "limit": 5
}
```

A response should include request ID, profile/catalog snapshot hashes, `personalized`, `degraded`, bounded item recommendations, evidence refs, cautions, and missing information. Returning a recommendation never authorizes installation, execution, purchase, download, or another side effect.

## 8. Integration audit

Trace:

```text
host catalog owner
→ catalog snapshot/version
→ profile snapshot assembler
→ hard filters
→ candidate recall
→ deterministic score
→ AI subset/evidence validator
→ result artifact and impression
→ surfaced recommendation
→ bound outcome event
→ future ranking read
```

Verify whether the provider receives a real host catalog/registry. A memory-provider ABC that guarantees only `hermes_home` does not prove the plugin can enumerate all live host tools or Skills; automatic host catalogs may require an injected host service. A plugin-only MVP can instead use a bounded versioned local catalog or caller-supplied candidates treated as untrusted data.

## 9. Acceptance tests

1. Current explicit correction suppresses stale profile state.
2. Accepted preference overrides an overlapping dynamic insight.
3. Quarantined, revoked, expired, stale, cross-profile, and unavailable inputs never rank.
4. The same profile/catalog/policy snapshots replay deterministically before optional exploration.
5. AI output cannot introduce an item or citation absent from its request.
6. Context snapshot assembly does not create ordinary injection/adoption records.
7. `no_opportunity` leaves ranking unchanged.
8. A verified success can affect later ranking without rewriting memory.
9. A correction or contextual failure does not become an unrestricted global preference.
10. Vector-unavailable operation degrades truthfully to lexical/structured ranking.
11. Catalog projections rebuild from catalog authority without touching accepted memory.
12. Recommendation output cannot trigger side effects without the normal host approval/tool boundary.
