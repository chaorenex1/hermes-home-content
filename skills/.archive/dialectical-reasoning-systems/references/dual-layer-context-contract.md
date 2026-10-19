# Dual-Layer Context Contract

Use this reference when designing or auditing a post-turn memory reasoner that separates stable context assembly from dynamic dialectical synthesis.

## Model-visible layers

Only two blocks may be injected:

```text
Base Context
Dialectical Context
```

Working Set, RetrievalIntent, Accepted Materialization, tool telemetry, and round artifacts remain internal evidence/state. They must not become additional model-visible layers.

## Base Context

| Field | Meaning | Authoritative source |
|---|---|---|
| `session_summary` | Current conversation progress and unresolved work | Current-session messages and structured tool results |
| `user_representation` | What the user is currently attending to | Current/recent user messages plus verified session/runtime evidence |
| `user_peer_card` | Stable facts and collaboration defaults | Accepted `identity` + `preference`, with document/version/citation |
| `ai_self_representation` | How the AI should currently express itself and respond to the user's focus | User representation + session summary + AI identity card |
| `ai_identity_card` | Stable identity and behavioral boundaries of the active profile | Current profile `SOUL.md`, hash-bound |

Keep dynamic representations distinct from stable cards. Assistant text alone cannot establish the user's focus. Dynamic dialogue inference cannot rewrite Accepted memory or `SOUL.md`.

## Dialectical Context

The dialectical layer models the user's current state and needs. Automatic long-term retrieval is limited to:

```text
entities
trajectories
experiences
tools
projects
```

`identity` and `preference` belong to the base layer.

## Orthogonal controls

- `contextCadence`: minimum turn interval between successful base-layer refreshes.
- `dialecticCadence`: minimum turn interval between successful dialectical refreshes.
- `dialecticDepth`: enabled depth, strictly 1–3.

Depth semantics:

```text
d1: choose cold/warm prompt and produce the initial assessment
d2: self-audit d1 and synthesize evidence from recent conversation
d3: reconcile contradictions across prior passes and emit the final synthesis
```

Depth 1 executes d1; depth 2 executes d1+d2; depth 3 executes d1+d2+d3. Do not skip configured d2/d3 via a generic `sufficient` flag or output-length heuristic.

Cold/warm selection is made by the dialectical layer:

```text
no valid BaseContextSnapshot -> cold
valid BaseContextSnapshot    -> warm
```

The existence of source files alone does not prove that a valid base snapshot was assembled.

## Refresh and failure semantics

- Only a validated, persisted refresh advances its cadence watermark.
- Empty output, schema failure, source read failure, version conflict, timeout, or artifact commit failure leaves the previous valid snapshot and watermark unchanged.
- If both layers are due, refresh Base first, then run dialectical reasoning against the latest valid Base snapshot.
- Base and dialectical blocks need independent budgets, versions, receipts, and feedback.

## Audit checklist

- Exactly two model-visible context tags are production-reachable.
- User representation is session-dynamic; user peer card is Accepted-backed.
- AI self-representation is a response stance; AI identity card is SOUL-backed.
- The five dialectical memory types are host-whitelisted.
- Working Set and materializations are evidence, not third-layer text.
- Each round binds prior output hashes and real evidence refs.
- Candidate promotion and SOUL modification remain separate reviewed paths.
- Restart recovery is idempotent and never synthesizes success.

## Common wrong turns

- Mapping `identity` directly to user representation instead of the stable peer card.
- Mapping `preference` alone to the peer card and omitting identity.
- Deriving AI identity from current Assistant output.
- Treating all three rounds as mandatory when configured depth is 1 or 2.
- Extending beyond depth 3 after the contract fixes a 1–3 range.
- Exposing Working Set or Accepted retrieval as a third model-visible layer.
