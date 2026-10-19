---
name: self-improving-agent-systems
description: Design agent memory, dialectical and self-improvement systems.
version: 1.1.0
metadata:
  hermes:
    tags: [memory, skills, curator, evaluation, safety]
---
# Self-Improving Agent Systems

## When to Use
Use when designing, reviewing, or extending an agent's persistent memory, skills, background reflection, knowledge base, or learning loop.

## Core Model
Treat self-improvement as controlled promotion of evidence-backed learnings, not model-weight training and not unrestricted automatic writing:

```text
trajectory/evidence → candidate → verification/review → accepted artifact → retrieval → outcome evaluation → retain, supersede, expire, or revoke
```

Separate storage by purpose:
- **Memory:** compact, high-frequency preferences, constraints, and pointers.
- **Knowledge base:** on-demand declarative domain facts and decisions.
- **Skills:** reusable procedural workflows with verification and recovery steps.
- **Trajectory/evidence ledger:** append-only task actions, tool results, tests, sources, and decisions.

## Establish the Source of Truth First

Never infer content authority from the current implementation or from the presence of a database. Read the user/architecture contract first and classify every store as **canonical content**, **metadata/control state**, **quarantine/staging**, or **rebuildable projection**.

For file-canonical memory systems:

- accepted Markdown/files are the durable content authority;
- SQLite may store only paths, hashes, versions, lifecycle/task state, audit links, and projection status;
- candidate and reviewed-plan bodies belong in versioned staging files when database bodies are outside the contract;
- summaries, FTS, vectors, and caches must rebuild from canonical files;
- recovery reconciles metadata from files and must never overwrite canonical files from stale database content.

Review the actual staged bytes and complete before/after target state. Execute only the reviewed candidate/plan hashes. Multi-file writes require a durable pending/committed/failed journal, base-hash fences, backups, read-back verification, and startup recovery because several atomic renames do not form one atomic transaction. Review retry exhaustion is `rejected`, `blocked`, or `exhausted`—never automatic approval.

See `references/file-canonical-memory-control-plane.md` for the transaction, recovery, summary, and verification pattern.

## Memory Content Template Layer
Keep editable memory-type prompts separate from the extraction transport and lifecycle contract.

- A memory content template defines only the semantic body: which facts belong to the type, section meanings, omission rules, examples, and boundaries against sibling types.
- The outer extraction prompt owns untrusted-input handling, JSON/schema shape, evidence IDs and spans, candidate operations, review, and persistence. Do not duplicate these into every content template.
- Default to ordinary content-generation prompts. Use replacement variables only when the caller explicitly requires them **and** the runtime has a declared substitution contract; never infer variable replacement from a template filename or section skeleton.
- Omit unsupported optional sections instead of emitting empty headings, `Unknown`, `N/A`, placeholders, or invented facts.
- Derive titles from supported body content rather than treating the title as an independent source of truth.
- Inspect the live loader before claiming an editable prompt file is active. A storage helper that creates or edits prompt files is not proof that provider initialization or extraction reads them.
- Keep type boundaries explicit: entities are stable named facts; events are time-anchored occurrences; experiences are reusable problem-solving processes; tools are tool-centered usage experience; trajectories are one user requirement's analysis→implementation→verification execution record; projects are durable project state and decisions.

When authoring or reviewing these prompts, use `references/memory-content-template-design.md` for type-specific contracts and correction-driven pitfalls.

## Finite Planning Loops
Treat every AI-driven self-improvement cycle as a durable, bounded planning run—not an unbounded agent recursion:

```text
frozen state snapshot → plan → validate → execute allowlisted actions → judge
                         ↑                                      ↓
                     continue only with a new state/gap   done|blocked|exhausted
```

Persist each run, round, validated plan, and event. A finite plan must include its context version, allowed actions, expected state changes, success criteria, stop conditions, and hard budgets. Enforce a common state machine:

```text
queued → planning → plan_validated → executing → judging
  → completed | continue | blocked | retryable | failed_terminal | exhausted | cancelled
```

Rules:
- A retry increments an attempt for the same round; it never consumes a new logical round or widens scope.
- `continue` requires a persisted new state/gap and an unvisited target. Identical plans over an unchanged snapshot terminate as no-progress.
- Planner output is JSON only; the executor maps validated actions to deterministic services. Do not give the planner direct database, filesystem, tool-policy, Skill-write, or budget-expansion authority.
- Separate recurring scheduling from a loop run: an active-session observer tick should be a fresh one-round run keyed by a dedupe hash, not an immortal run.
- Use rule planners for deterministic maintenance and bootstrap retrieval; use AI/hybrid planners only where semantic selection is needed.
- Define per-loop round caps explicitly (for example: extraction 5, retrieval 3, observation 1, evaluation 2, projection 1) and cancel session-bound runs when a newer user message invalidates the snapshot.

## Dialectical Maintenance and Contradiction Handling

Online decision quality and post-turn memory reconciliation are different systems: a post-turn updater cannot improve the answer already sent, and running critique on every turn proves nothing about coverage.

- **Detect opportunities semantically; measure coverage over eligible opportunities.** Trigger classes include explicit user corrections, instructions conflicting with plan/scope, verified tool evidence contradicting a premise, runtime behavior contradicting docs/config, reviewer counterexamples, invalidated completion claims, and directions conflicting with safety invariants. Never report invocation rate, keyword hits, or max-round usage as coverage — report the funnel (trigger recall/precision, execution completion, opposition quality, evidence coverage, state-revision recall, synthesis quality, cost) separately.
- **Scale reasoning depth to risk.** Routine turns: skip or one state-update round. Explicit correction or evidence conflict: thesis plus a materially distinct critic (the critic cannot write persistent state). Irreversible, security-sensitive, or multi-source conflicts: add an independent judge that compares authority and evidence, resolves or defers, names residual uncertainty, and emits deterministic state operations. High-severity rounds cannot self-declare completion — the next round must add a materially new artifact or terminate as no-progress.
- **Make conflict a first-class object, not prose:** claims (with authority class + evidence refs), challenges (materially distinct), and resolutions using explicit operations (`retain|revise|narrow|contest|retire|supersede|defer|escalate`) with residual uncertainty and a revisit trigger. Unresolved conflicts stay in working state; they are never flattened into a confident profile fact.
- **Evidence authority order:** system/safety invariants > current explicit user correction > verified tool output and artifacts > frozen plan/project contract > accepted knowledge > evidence-bound dynamic state > prior assistant claims. Assistant-only text cannot establish a profile-level user fact; completion claims stay session claims until a real artifact verifies them.
- **Runtime-fit before redesign:** trace the actual lifecycle hook/callback capability first. A structured LLM callback usually sees only its prompt and supplied JSON context — do not assume it can call tools, browse the session database, or invoke `session_search`; work from the bounded completed-turn transcript the host already provides.
- **Persist exact failure stages** (`opportunity_detection → json_parse → schema_validation → evidence_reference_validation → opposition_quality → state_version_fence → state_operation → synthesis_judge`); allow one structured repair with the exact invalid field; on repeated failure leave an unresolved working-state item, avoid unverified profile writes, and mark partial/blocked/exhausted. Raising `max_rounds` without minimum-round or role separation does not create a dialectic.
- **Audit deployments by copy, not by tree:** enumerate every live-capable copy (dev checkout, installed plugin, host core, worktrees, dirty working trees); a source read describes the repository, not the runtime; verify each audit claim against the copy it describes.
- **Replay evaluation:** build a frozen-hash corpus with positive and negative examples (corrections, counterexamples, unsafe requests that must keep safety constraints, routine turns that must NOT debate); use two independent reviewers plus an adjudicator receiving actual message/artifact content — never paths or summaries alone.

Depth retained in the archived package: `.archive/dialectical-reasoning-systems/` (dual-layer context contract, lagged single-Dynamic-Context lifecycle, Honcho comparison, coverage-audit baseline, LanceDB implementation map).

### Advisory side channels

A per-turn reviewer that tries to change the current action is a separate system from post-turn
reconciliation: read-only reviewer, own model and context, delta-only perception, a structured note
tool, an emission guard, and severity-tiered delivery. Choose the delivery channel from what the host
can actually do (interrupt, boundary injection, visible card, continuation) before writing prompts;
most hosts have only one or two, and claiming the weaker channel is equivalent hides the loss.
Parameters, content rules, workarounds for a binary-only reference implementation, and pitfalls:
`references/adviser-side-channels.md`.

## Review Procedure
1. Map existing write paths and identify whether each writes direct-to-live state or candidate state.
2. Require a candidate quarantine: unapproved content must not affect default retrieval, directory summaries, embeddings, or prompt prefetch.
3. Preserve per-artifact provenance: source kind/reference, content hash, timestamp, trust level, verification state, scope, validity window, and supersession link.
4. Keep **importance** (value) distinct from **confidence** (correctness) and **trust** (source authority).
5. Define explicit, version-checked promotion, rejection, revocation, expiry, and supersession operations. Preserve evidence and audit records; avoid silent deletion.
6. Convert verified trajectories into experience or failure-pattern candidates. Do not promote a one-off observation into a global rule.
7. Let the knowledge layer propose skill changes, but route actual skill edits through the normal staged approval/diff mechanism.
8. Define outcome metrics before enabling automation: first-pass success, repeated-failure rate, user-correction rate, verification pass rate, tool calls, and token/latency cost.
9. Add replay and adversarial tests for retrieval, candidate leakage, provenance, rollback, cross-profile isolation, and prompt-injection resistance.

## Diagnosing Missing Memory Candidates

When a conversation appears to contain durable knowledge but no expected memory is visible, diagnose the pipeline before changing semantic prompts or relaxing review:

1. Verify the provider build actually imported by the running Hermes environment and compare its schema contract with the live store.
2. Trace one session through durable jobs, evidence, routing, extraction, quarantine, review, promotion, and retrieval.
3. Distinguish `no job`, `completed_empty`, `rejected`, `failed`, `quarantined`, and `promoted`; each proves a different failure boundary.
4. Inspect the real extraction DTO. A host may receive complete messages while the candidate worker sees only the current user/assistant pair.
5. Keep user-fact evidence strict. Widen the bounded evidence window or add replay rather than treating assistant summaries as user identity or preference.
6. Check for an already-promoted sibling representation before claiming the topic was never extracted.
7. After repairing runtime delivery, explicitly backfill missed sessions; post-turn workers cannot recover turns that were never persisted.

Use `references/extraction-pipeline-failure-diagnosis.md` for the stage matrix, recovery rules, and end-to-end verification checklist.

## Memory-Profile Recommendation Systems
When persistent memory is used to personalize recommendations, treat the recommender as a separate evidence consumer—not as another memory retrieval mode.

- Separate the **user side** (current instruction, session state, accepted preferences/identity/projects, evidence-linked dynamic insights) from the **item side** (a versioned external catalog). A user profile alone cannot recommend anything.
- Build one versioned, hash-bound recommendation-profile snapshot with this authority order: current explicit instruction/correction > current session state > accepted memory > active dynamic insight > verified historical outcomes > generic defaults.
- Do not call a context-injection method merely to obtain profile data if it records injection or changes adoption counters. Add a read-only snapshot assembler and a recommendation-specific receipt.
- Keep catalog items out of accepted memory and accepted-memory projections. Catalog indexes are rebuildable projections owned by the catalog; memory remains user knowledge.
- Use hard constraint filtering before ranking. AI may rerank only host-supplied candidate IDs and must cite only snapshot-authorized evidence; it may not invent items, bypass constraints, or trigger side effects.
- Keep memory-use feedback distinct from recommendation outcomes. "This memory influenced the answer" is not the same as "the user selected, attempted, or succeeded with this item." Record impressions and append-only outcome events separately; `no_opportunity` is neutral.
- Cold-start readiness must be reported truthfully. Quarantined candidates are excluded, dynamic profile text is lower authority than accepted memory, unavailable vectors degrade to lexical/structured ranking, and absent verified outcomes use a neutral prior.
- Persist full recommendation evidence packages in the declared file-canonical artifact store; keep SQLite limited to scope/version/hash/status/ranking/event metadata when that is the host storage contract.

See `references/memory-profile-recommendation-systems.md` for the architecture, schema, ranking, feedback, and acceptance checklist.

## Learning-Sample Yield

When evaluating whether a memory or user-profile system can support reinforcement or preference learning, count samples by the target learner's complete contract rather than summing stored rows:

- Source user→assistant turns are the default ceiling on independent interaction units.
- Memory candidates and inferred labels are weak semantic supervision, not rewards.
- Profile documents, summaries, context generations, and dynamic leaves are correlated state snapshots, not independent examples.
- A contextual-bandit sample requires a context snapshot, action identity, action probability/propensity, outcome, reward, and reward evidence.
- A DPO-style sample requires chosen and rejected alternatives bound to the same prompt/context plus a defensible preference source.
- Missing feedback is missing data; a profile write or successful extraction is not a positive outcome.

Report the current persisted corpus, per-turn theoretical amplification, usable learner-specific yield, and effective independence ceiling separately. Use `references/profile-learning-sample-yield.md` for the read-only live-store procedure, worked interpretation, and report format.

## Pitfalls
- A `candidate` record is unsafe if its text or derived summary enters normal search/prefetch before approval.
- A model tool call is not equivalent to operator confirmation; agent, subagent, web, file, and MCP-derived content needs lower default trust.
- Do not use a memory provider as a tool-policy enforcement layer. It may surface risk signals; blocking dangerous actions belongs in an approval/policy layer.
- Do not use write count as the learning metric. Measure future task outcomes.
- Keep raw evidence separate from concise reusable conclusions so the latter can be revised without losing auditability.

## Planning Integration
For implementation plans, keep the minimal provider/storage MVP separate from self-improvement automation. Add a dedicated later phase that covers candidate isolation, provenance, promotion lifecycle, trajectory-to-learning extraction, skill-proposal handoff, and outcome evaluation.

See `references/self-improvement-control-plane.md` for a concrete schema and acceptance checklist.

## Verification
- Candidate data is absent from default retrieval and prefetch until promotion.
- Every accepted artifact resolves to evidence, an actor/trust classification, and a lifecycle decision.
- A revoked, expired, or superseded artifact no longer affects default context.
- A replay suite demonstrates an improved outcome or rejects the proposed learning.
