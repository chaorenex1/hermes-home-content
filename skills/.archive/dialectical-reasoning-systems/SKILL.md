---
name: dialectical-reasoning-systems
description: Use when evaluating dialectical reasoning coverage.
version: 1.0.0
created_by: agent
metadata:
  hermes:
    tags: [dialectical-reasoning, evaluation, memory, evidence, critique]
---
# Dialectical Reasoning Systems

## When to Use

Use when designing, reviewing, debugging, or measuring an agent mechanism that should:

- detect contradictions, corrections, competing requirements, or counterevidence;
- challenge a proposed answer or action before commitment;
- revise working memory or a user model after evidence changes;
- run thesis/critique/synthesis loops;
- measure reasoning coverage, opposition quality, or memory reconciliation.

Support four explicit operating contracts and never conflate them:

- **Opportunity-gated online review:** Before the current answer or side effect, run critique only for genuine corrections, conflicts, ambiguity, or risk. Optimize for recall over real opportunities, not raw invocation count.
- **Post-turn adaptive memory maintenance:** Every completed turn enters a background grounding pass, but later self-audit and reconciliation passes run only when grounding exposes a material gap or contradiction. There is no entry trigger, yet depth remains adaptive from one to three passes. This mode prepares state and context for a future turn; it cannot improve the answer that already finished.
- **Fixed-round online review:** Only when the host or user explicitly requires every turn to execute every named round should the controller forbid early termination. Eligibility may still be labeled offline for quality measurement, but must not gate execution.
- **Lagged single Dynamic Context:** When the host explicitly requires turn N to generate exactly one context for turn N+1, run all AI/retrieval work after the completed turn, publish only the final synthesis, and keep next-turn `prefetch()` as an O(1) read-only delivery adapter. A new session may synchronously attempt one bootstrap call for `source_turn=0`; later turns publish `source_turn=N`. This contract intentionally rejects query-time generation, layered context injection, exact injection feedback, stage checkpoints, and hash-based context consistency.

A user saying “no trigger judgment” may mean “every completed turn runs the first post-turn pass,” not “all three passes are mandatory.” Resolve the system purpose, timing, and selected injection contract before deciding whether depth is adaptive, fixed, query-aware, or strictly previous-turn.

## Core Separation

Treat online decision quality and post-turn memory reconciliation as different systems:

```text
user turn
  → semantic opportunity detector
  → optional pre-decision thesis / independent critique / judge
  → answer or action
  → post-turn state reconciliation
  → query-relevant future injection
```

A post-turn memory updater cannot improve the answer already sent. It may revise future state, retire stale claims, or preserve unresolved conflicts, but it is not evidence of current-turn reasoning coverage.

Keep the turn boundary explicit:

```text
turn N answer/tools
  → completed-turn transcript and runtime evidence
  → post-turn grounding / optional audit / optional reconciliation
  → versioned model and working-state snapshot
turn N+1 query
  → query-filter that snapshot and current accepted memory
  → create an exact injection offer and receipt
  → answer/tools
```

Under a **query-aware offer** contract, do not finalize next-turn injection text before the next query exists: persist a candidate snapshot after turn N, produce a query-specific offer at turn N+1, and bind feedback to that exact offer. Under an explicitly selected **lagged single Dynamic Context** contract, the opposite timing is intentional: `sync_turn(N)` finalizes the only result, `prefetch(N+1)` merely reads it, no query-time generation occurs, and exact injection feedback may be deleted. Do not mix the two contracts.

## Runtime-Fit and Evidence Acquisition

Before designing rounds or evidence flow, trace the actual lifecycle hook and callback capabilities. Do not redesign a post-turn provider callback as a pre-action agent controller unless the host integration is explicitly being changed.

- A structured LLM callback normally has only the prompt and supplied JSON context; do not assume it can call agent tools, browse the session database, or invoke `session_search`.
- Prefer the bounded completed-turn transcript already supplied by the host, including tool calls and tool results. Let the audit round select and relate evidence from that frozen transcript instead of inventing a separate retrieval service.
- Treat `session_search` as an agent/research capability, not a provider-runtime capability, unless the host exposes an explicit bounded history interface.
- Cross-session raw-history retrieval requires a deliberate host contract. Accepted memory, dynamic profile state, and current-session transcript are not interchangeable with arbitrary historical messages.
- Do not repurpose a candidate-review evidence ledger for dialectical audit evidence unless both workflows intentionally share persistence, redaction, provenance, and authorization semantics. Ephemeral message references may be sufficient for within-run audit, while durable candidate evidence remains a separate trust boundary.

## Opportunity Detection

Use this section for opportunity-gated online review, offline labeling, or deciding whether a post-turn grounding pass must continue into audit/reconciliation. Do not use it as an entry gate when the post-turn contract requires every completed turn to run grounding.

Use a semantic classifier or independent judge, not exact keywords. Relevant trigger classes include:

- explicit user correction of prior interpretation;
- current instruction conflicting with a plan, scope, or prior requirement;
- verified tool/artifact evidence contradicting a premise or completion claim;
- runtime behavior conflicting with documentation, configuration, or inferred role boundaries;
- an independent reviewer producing a material counterexample;
- a claimed completion later invalidated by newer evidence;
- current user direction conflicting with safety or irreversible-operation invariants;
- dynamic profile state conflicting with accepted memory or current explicit user evidence.

The detector should emit a versioned record with eligibility, trigger type, severity, challenged state references, and required minimum review depth.

## Bounded Reasoning Protocol

### Routine, low-risk turns

Skip the full loop or allow one state-update round.

### Explicit correction or evidence conflict

Require at least two roles:

1. **Thesis:** proposed interpretation/action, assumptions, and supporting evidence.
2. **Critic:** strongest materially distinct counterclaim or counterexample. The critic cannot write persistent state.

### Irreversible, security-sensitive, or multi-source conflicts

Require an independent third role:

3. **Judge/Synthesizer:** compare authority and evidence, resolve or defer, identify residual uncertainty, and emit deterministic state operations.

For high-severity opportunities, do not allow the first round to self-declare completion. A later round must add a materially new artifact; repeated restatement terminates as no progress.

## First-Class Conflict Model

Do not bury conflict only in prose summaries. Use explicit objects:

```json
{
  "claims": [
    {
      "claim_id": "...",
      "text": "...",
      "authority": "current_user|verified_tool|frozen_contract|accepted|dynamic|assistant",
      "evidence_refs": []
    }
  ],
  "challenges": [
    {
      "target_claim_id": "...",
      "counterclaim": "...",
      "evidence_refs": [],
      "materially_distinct": true
    }
  ],
  "resolutions": [
    {
      "target_claim_id": "...",
      "operation": "retain|revise|narrow|contest|retire|supersede|defer|escalate",
      "synthesis": "...",
      "residual_uncertainty": [],
      "revisit_trigger": "..."
    }
  ]
}
```

Unresolved conflicts belong in session working memory with their competing claims, evidence, missing proof, revisit trigger, and prohibited premature actions. They should not be flattened into a confident profile fact.

## Evidence Authority

Use this default order, while preserving explicit host policy:

```text
system and safety invariants
> current explicit user correction or requirement
> verified tool output and actual artifacts
> frozen plan, project contract, and authoritative runtime state
> accepted knowledge
> evidence-bound dynamic state
> prior assistant summaries or claims
```

Important boundaries:

- Newer explicit user definitions supersede older assistant interpretations.
- Safety invariants are not silently discarded because a newer request simplifies a destructive operation.
- Assistant-only text cannot establish a profile-level user fact.
- Tool output may establish environment/project facts, not user preferences.
- Completion claims remain session claims until verified by real artifacts or tests.
- Persistent profile changes require explicit user evidence or repeated cross-session evidence followed by the normal review lifecycle.

## Measuring Coverage

Do not call invocation rate, keyword hit rate, or maximum-round usage coverage. Define the primary metric over independently labeled eligible opportunities:

```text
Effective coverage =
  eligible opportunities that completed valid challenge,
  evidence judgment, required state revision, and accepted synthesis
  / all eligible opportunities
```

For post-turn adaptive memory maintenance, add two separate denominators:

```text
Grounding coverage = completed turns with a valid first pass / all completed turns
Continuation recall = labeled runs that required audit or reconciliation and actually reached the required later pass / all labeled runs requiring that depth
```

A routine turn that validly ends after grounding is not a coverage miss. Conversely, invocation on every turn does not prove that required challenge or reconciliation happened.

Report the funnel separately:

- **Trigger recall:** detected eligible opportunities / all eligible opportunities.
- **Trigger precision:** true eligible opportunities / all triggered cases.
- **Execution completion:** valid completed runs / triggered cases.
- **Opposition quality:** non-duplicate, non-strawman counterclaims / eligible completed cases.
- **Evidence coverage:** severity-weighted supported atomic claims / all severity-weighted claims.
- **State-revision recall:** correctly revised/retired/superseded states / states that required revision.
- **Synthesis quality:** independent-judge passes without hidden critical conflicts / generated syntheses.
- **Opportunity-aware adoption:** adopted injections / injections with a real opportunity to affect behavior.
- **Cost/latency:** calls, tokens, and P50/P95 duration per eligible case.

Do not multiply all stages into a single vanity score that hides the failing stage.

## Dual-Layer Context Contract

When the target architecture distinguishes a stable base layer from a dialectical supplement, do not fold every field into one reasoning loop.

- **Base layer:** session summary; user representation derived from what the user currently attends to; user peer card derived from accepted `identity` plus `preference`; AI self-representation describing its current response stance toward the user's focus; and AI identity card derived from the current profile's `SOUL.md`. Refresh and budget it independently; `contextCadence` is the minimum turn interval between base-layer refreshes. Keep the stable cards source-bound while allowing the two representations to track the current conversation.
- **Dialectical layer:** inference about the user's current state and needs, with retrieval limited to `entities`, `trajectories`, `experiences`, `tools`, and `projects`. `dialecticCadence` is the minimum turn interval between dialectical refreshes. `dialecticDepth` is 1–3: depth 1 selects a cold prompt when base context is absent or a warm prompt when base context exists; depth 2 self-audits the initial assessment and synthesizes recent-session evidence; depth 3 reconciles contradictions across prior passes and produces the final synthesis.
- Persist, inject, budget, receipt, and evaluate the two layers separately. Never let AI self-observation become user-profile evidence, and never let dynamic self-representation directly rewrite stable agent identity/SOUL policy.

## Auditing an Existing Implementation

Before judging or changing a dual-layer implementation, map the deployment — do not read conclusions from a single tree:

- Enumerate every live-capable copy: the dev checkout, the installed runtime plugin directory, the host core checkout, and feature branches checked out as git worktrees or task workspaces — plus uncommitted working-tree changes (`git status` in each checkout). An installed copy can lag the checkout by whole modules, and feature host code may exist only in a worktree or as a dirty working-tree edit — absence from committed `main` is not absence of the feature.
- Verify each audit claim (plan row, correction note, spec line) against the copy it describes before classifying a symbol missing, present, or done — audit documents silently mix code generations, and a mixed baseline replans finished work or deletes still-load-bearing code.
- Establish which copy and process actually serve the current session before making any runtime-behavior claim; a source-tree read describes the repository, not the runtime.
- Confirm persisted contracts against live state read-only (open the store with a read-only URI; enumerate tables and rows). A missing table is authoritative for what the host writes today.
- Trace every environment binding end to end: host ContextVar → task-scoped binding → a setter at the feature runtime's dispatch site → provider read. A provider-referenced variable that nothing sets is not a working contract.
- Check both sides of each cross-boundary contract: static metadata written by the host versus dynamic content owned by the file layer, and provider push APIs versus host pull reads. Report which side exists before proposing the other.

See `references/hermes-lancedb-implementation-map.md` for the concrete Hermes memory-provider file map, env chain, live-state locations, and verification commands.

## Replay Evaluation

Build a versioned replay corpus from real session windows. Include both positive and negative examples:

- user correction and scope-boundary cases;
- tool evidence overturning a premise;
- reviewer-found counterexamples;
- unsafe requests that must retain safety constraints;
- routine factual turns that should not trigger a debate.

Use two independent semantic reviewers and a third adjudicator. Reviewers must receive the actual message and artifact content, not only paths, line numbers, summaries, or worker claims. Freeze message-window hashes, prompt/schema versions, expected authority ranking, expected state operations, and forbidden actions.

## Reliability and Observability

Persist exact failure stages rather than one generic reasoning error:

```text
opportunity_detection
json_parse
schema_validation
evidence_reference_validation
opposition_quality
state_version_fence
state_operation
artifact_commit
synthesis_judge
```

Allow at most one structured repair attempt using the exact invalid field or failed invariant. On repeated failure:

- preserve an unresolved working-state item;
- avoid unverified profile writes;
- mark the run partial/blocked/exhausted explicitly;
- retain enough evidence for replay and diagnosis.

## Query-Relevant Injection

Use this section only when the selected contract creates an offer from the current query. It does **not** apply to the lagged single Dynamic Context contract, where `prefetch()` must return the strict previous-turn result without generation or feedback.

Filter future context by the current query, active constraints, relevant decisions, and unresolved conflicts. Prefer a few high-value items over a large profile dump. Distinguish feedback states:

```text
adopted | not_adopted | no_opportunity | contradicted | stale
```

`no_opportunity` is neutral, not negative evidence. Do not optimize adoption toward 100%; irrelevant injection should be removed, while relevant but correctly unused safety/context items may remain valid.

## Rollout Order

1. Add eligibility and failure-stage events in shadow mode.
2. Build and adjudicate a replay corpus.
3. Fix structured-output and state-commit reliability.
4. Shadow the semantic opportunity detector.
5. Canary the independent critic with state writes disabled.
6. Enable judge-approved working-state revision.
7. Enable profile retirement/narrowing only after replay evidence passes.
8. Shadow then canary query-aware injection.
9. Increase rollout only when coverage, correction rate, safety, cost, and latency all pass.

## Pitfalls

- Increasing `max_rounds` without minimum-round or role separation does not create dialectic.
- Reusing one model prompt for thesis, critique, and judgment encourages self-agreement.
- Latest-user-instruction-wins is not a safe universal authority rule.
- Schema validity and matching strings do not prove semantic correctness.
- Post-turn memory success is not current-turn reasoning success.
- High injection adoption can reflect overfitting or excessive context, not better reasoning.
- Storing one-off assistant implementation claims in a stable user profile makes later contradictions harder to repair.

## Verification Checklist

- High-risk opportunities cannot terminate before an independent critique.
- Every critical claim resolves to actual evidence content.
- Counterclaims are materially distinct and not strawmen.
- Required state operations use version fences and are read back.
- Assistant-only claims do not become stable user facts.
- Unresolved conflicts survive safely without blocking unrelated work.
- Routine negative examples do not trigger unnecessary debate.
- Replay results report every funnel stage, not only an aggregate score.

## Session-Specific References

- See `references/single-dynamic-context-post-turn-contract.md` for the strict previous-turn Dynamic Context lifecycle, at-most-once session bootstrap, hash-free publication boundary, destructive legacy cleanup, and required tests.
- See `references/recent-session-coverage-audit.md` for the July 2026 Hermes/LanceDB baseline, representative failure patterns, and replay anchors.
- See `references/honcho-post-turn-dialectical-memory.md` for the Honcho comparison, post-turn adaptive-depth contract, turn-boundary data flow, and accepted/working/profile authority boundaries.
- See `references/hermes-lancedb-implementation-map.md` for where the Hermes file/LanceDB memory provider actually runs from (dev repo vs installed copy vs worktrees), its env chain, provider module map, live-state locations, and verification commands.
