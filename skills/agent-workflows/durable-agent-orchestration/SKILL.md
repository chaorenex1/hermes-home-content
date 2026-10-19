---
name: durable-agent-orchestration
description: "Build and verify durable AI planning-to-execution workflows with structured manifests, delegation, reviews, and bounded retries."
version: 1.1.0
author: Masia
created_by: agent
---

# Durable Agent Orchestration

Use for systems that turn an approved AI plan into multi-agent execution across turns or process restarts.

## Outcome

Implement a durable workflow:

```text
AI task classification → template history → approved plan + manifest
→ step dispatch → evidence → step review → global review → outcome history
```

Do not treat natural-language status claims as workflow completion.

## Ralph / planning requirements

1. **Classify with AI, not local keyword routing.** Require a schema-validated result containing task kind, execution profile, suggested template, confidence, and reason. Persist the result with the plan.
2. **Fallback safely.** If classification is unavailable or invalid, use a conservative general/manual template. Do not silently revive a keyword map.
3. **Retrieve template history before plan generation.** Match by task kind and execution profile. Reuse only successful, quality-backed templates.
4. **Optimize from failure history.** When matching history has review failures but no proven reusable template, inject those findings into the planning prompt as explicit improvement criteria. Preserve old template versions; do not mutate history in place.
5. **Approve a stable artifact.** Store plan path, template/version/source, classification, approval state, manifest, and a content digest. Execution must reject missing, unapproved, or digest-changed plans.

## Manifest contract

A Markdown plan is for people; a manifest is for execution. Require each executable step to contain:

```json
{
  "id": "S01",
  "title": "...",
  "agent": "coder|general|explore",
  "instructions": "...",
  "depends_on": [],
  "acceptance_criteria": ["..."],
  "evidence_required": ["..."],
  "max_attempts": 2
}
```

Validate unique IDs, known dependencies, non-empty acceptance/evidence fields, supported agents, and bounded retry values before creating execution state.

### Hierarchical execution routes and just-in-time task refinement

Do not reduce a rich Ralph plan to a flat checklist or force a one-Task-to-one-step mapping. A compiled execution artifact has three layers:

```text
immutable Ralph plan (human-readable source of truth)
→ route manifest (frozen top-level execution path)
→ task execution manifest (generated when a route task is activated)
```

1. **Route nodes preserve task identity.** A route may add explicit `preflight` and `global_review` nodes, and may semantically group or split work, but every plan task remains a traceable `task_ref` along the route. Keep a many-to-many source coverage map rather than relying on matching node counts.
2. **Refine at activation time.** When dependencies make a task ready, generate its child execution graph from the frozen task section, relevant global architecture/invariants, approved upstream handoffs, current repository/environment facts, and outstanding risks. The child graph supplies the current goal, background, concrete actions, verification, stop/recovery condition, and handoff requirements.
3. **Keep immutable and mutable state separate.** `StepDefinition` / source refs / plan digest are frozen. `StepState` records live evidence, artifacts, failures, choices, and approved handoffs. The next worker prompt is a projection of both, not a cold task title or a copy of the full plan.
4. **Require provenance for generated detail.** Every synthesized child step must cite its parent task and relevant plan sections. Mark runtime-derived checks separately from source requirements. Missing or ambiguous plan detail is a refinement blocker or a proposal for Ralph review, never a silently invented requirement.
5. **Do not let refinement change plan intent.** A child planner may split, order, or skip already-proven work inside its parent task, but cannot remove acceptance criteria, weaken safety constraints, expand into future tasks, or change the overall goal. Such a need returns to Ralph for plan revision and a new digest.
6. **Task closure is a real gate.** A parent task completes only after its child graph's raw evidence and an independent semantic Judge establish the task acceptance criteria. Persist a concise handoff: completed capability, artifacts/commit, verification evidence, unresolved limits, and invalidated assumptions. Downstream task refinement receives this handoff.
7. **Validate coverage semantically.** Before approval, independently compare the route plus all currently materialized task contracts against the full plan: important intent, invariants, verification, risks, and completion evidence must be represented or explicitly deferred to a named task-ref. Reject summary-only manifests that cannot tell a worker why, how, and how to verify the current work.
8. **Do not turn the human plan into a mechanical contract-writing exercise.** The planner—not the user—extracts and synthesizes route background, actions, verification, and recovery from rich Markdown. Do not require one-task/one-static-step mappings or hand-authored YAML for every task. Task identity remains a route anchor; concrete child steps are generated when that anchor becomes ready and must carry source provenance.

### Task-refiner contract, provenance, and failure observability

A route task may correctly resolve its source packet yet fail before any child step is inserted because the auxiliary refiner returned a structurally invalid `TaskExecutionManifest`. Preserve that distinction without making the LLM responsible for fields the runtime already knows.

1. **Separate semantic fields from deterministic fields.** Validate model-authored semantics—`id`, `title`, `agent`, `goal`, `background`, actions, verification, stop/recovery, acceptance criteria, evidence, and bounded retries. Derive mechanical provenance such as each child’s `source_refs` canonically from the frozen parent `RouteNode.source_refs`, and normalize the persisted child manifest before storage. A model-provided source label must never expand the parent’s provenance, but a non-canonical label must not block otherwise valid work.
2. **Use an explicit JSON shape plus local validation.** Prompt for one JSON object with a non-empty `steps` array, then enforce the complete runtime schema locally. Prompt text alone is not a schema guarantee.
3. **Report field-level diagnostics.** Carry child index plus missing/invalid scalar fields, required-array failures, frozen-agent mismatches, invalid retry values, and JSON parse errors in a structured refinement error. Do not retain only a generic exception such as “incomplete child step.”
4. **Persist safe, bounded evidence.** On failure record route/task identity, refiner model, raw-output character count, SHA-256, normalized validation details, and attempt history. Store a redacted bounded excerpt only when policy permits; do not persist arbitrary raw model output by default.
5. **Repair once with changed input.** After a schema or parse failure, issue at most one repair request that includes the validator findings and the parent’s allowed provenance. If it still fails, set the route/workflow to `blocked` with zero child steps; never loop or silently fabricate missing semantic fields.
6. **Distinguish failure classes.** The event trail must distinguish source-slice failure, refiner unavailability, malformed JSON, semantic schema failure, and blocked repair without log scraping.

**Required regressions:** prove that a malformed semantic field is diagnosed, a single diagnostic repair can produce a valid child manifest, two invalid attempts leave no partial child step, and malformed/non-canonical model `source_refs` are normalized to the frozen parent source set. Also retain the multi-stage route test: task activation only after dependencies, source-backed context plus upstream handoff, failed-child parent blocking, and successor contextualization without the prior transcript.

**Kanban child-graph persistence:** Store validated child steps separately from parent route state with a compound identity `(run_id, route_key, child_key)`. Persist the complete normalized manifest atomically before any child is dispatchable; a duplicate materialization must fail rather than overwrite evidence. Claim one pending child through a compare-and-set transition (`pending → running`) and append a route-child claim event. Do not reuse a parent-level `(route_key, attempt, stage)` uniqueness key for multiple child steps: child execution attempts need their own namespaced identity. Only after every child’s Dev → functional QA → CTO QA evidence is accepted may the parent route write its handoff and release successors.

### Dependency-safe parallel dispatch

Parallelism is a property of the frozen DAG, never permission to bypass it. At both route and child levels, enumerate every pending node whose declared dependencies are accepted and dispatch the whole ready set in one controller turn. Keep a legacy single-item dispatch helper only for compatibility; expose a batch-ready dispatch surface for normal operation so independent work is not accidentally serialized.

For every ready item, perform its own compare-and-set claim (`pending → running`) before creating the employee task. A lost claim means another controller won and must be skipped; it must not abort dispatch of the remaining ready items. Nodes whose dependencies are running, blocked, or merely completed-but-not-accepted remain pending. Add regressions proving: two independent top-level routes start together; two dependency-free child steps start together; a dependent child remains pending; and a replay does not duplicate a child task.

When adding parallelism to a mature controller, keep unrelated lifecycle domains out of scope. In particular, do not alter authorization, evidence, worktree, review, or invalidation rules for a separate post-acceptance/Ops phase unless the request explicitly includes that phase. Verify its existing focused regressions alongside the new concurrency tests.

### Compact artifacts and global-acceptance capability gate

A Ralph Judge may receive a bounded artifact window rather than an unlimited plan file. Keep the designated executable artifact compact enough to be judged as one complete document: retain scope, architecture, every executable Task heading, exact verification commands, stop/recovery rules, risks, and final evidence; move verbose source-plan provenance to a cited read-only source file. Never accept a head/tail-truncated artifact as proof that middle tasks or rollback clauses were reviewed.

Before approval, validate the manifest actually produced by the installed runtime, not merely a prose claim that it will be RouteManifest v2. Confirm `execution_manifest.version == 2`, the route is non-empty, no legacy static `steps` payload remains, each visible Task has exactly one `task_ref`, dependencies are ordered, and the final global acceptance gate is executable. If a plan requires a named global gate such as `R99`, make its source section explicitly state: required route id/kind, dependency on the final implementation task, source refs, acceptance criteria, evidence artifacts, pass/block behavior, and non-mutation scope.

Then perform an isolated runtime smoke test: creating a v2 workflow must persist route nodes (first running, successors pending) **without eagerly created child steps**; `next_prompt()` must materialize only the active task using its source-backed context; after the normal evidence/review gate, a handoff event must be stored and supplied to the dependency-unblocked successor. A successfully created v1 workflow is not evidence that v2 parsed or ran. Manual approval/database overrides can retain a v1 manifest despite current source supporting automatic v2 compilation.

Route compilation is an auxiliary-model operation with a finite timeout. Regression-test the actual request timeout. Do not silently character-truncate a frozen plan, source section, or Judge artifact: preserve complete Markdown and use heading-safe segmentation when a full compile times out, provider request-size limits reject it, or the returned route fails structural validation. Validate the full-model result **before** recording the full attempt as successful. Prompts must enumerate every required v2 node field (`id`, `kind`, `title`, `source_refs`, `background`, `depends_on`, `agent`, acceptance/evidence arrays, retries, and `task_ref` where applicable): models may return a plausible route skeleton with missing fields. It is safe to normalize only an omitted outer `version` when a valid `route` envelope is otherwise present; never fabricate missing node fields. First attempt the complete plan; on recoverable failure, compile complete `### Task N:` sections independently, validate each segment, deterministically reassemble dependency IDs, then validate the merged v2 route against the full source. Persist mode (`full|segmented`), attempt outcomes, timeout/error reasons, plan character count, and `truncated=false`; surface those diagnostics in the initiating transcript/Desktop event. On unavailable compiler, invalid JSON, invalid merged manifest, or an indivisible segment failure, leave Ralph at `awaiting_next_round` with no digest/manifest. Never silently substitute a generic fallback route.

The v2 validator must enforce multiplicity, not set membership: every source Task has exactly one `task_ref`. Treat `preflight` and `global_review` as executable route semantics, not merely accepted JSON kinds: preflight is read-only (`explore`) work that can create a handoff; global review transitions the workflow to its independent review gate and records pass/rework/block on the terminal route node. Add end-to-end regressions for duplicate task refs, explicit preflight/global nodes, full→segmented compilation, and no-truncation artifact transport.

### Emergency approval-state override

Direct edits to durable Ralph state are an emergency-only escape hatch, never a substitute for normal independent approval. Perform them only with explicit user authorization. First make a timestamped backup of the active `harness.db`; then inspect the exact `state_meta` record, preserve an append-only override event with the authorization and manifest digest, and read back status, digest, manifest version, and step count. Do not silently downgrade a route manifest to a flat manifest: disclose any semantic mismatch, especially named global-review behavior. Before claiming dispatch, call the normal Ultrawork creation path and report its real workflow ID and current phase; retain the backup path for rollback.

### Evidence semantics and one-shot recovery

`evidence_required` names the **artifacts to collect** (for example, exact command, raw stdout, raw stderr, exit status, artifact path); it is not a list of state-machine phase names. Never reject an `execute`/`red`/`green` report merely because the literal phase name is absent from `evidence_required`.

For semantic or factual acceptance, do **not** pass a step because evidence is non-empty or because a model copied acceptance-criterion prose into a dictionary. Exact natural-language criterion-key matching is brittle across punctuation, wording, localization, and formatting. Instead, persist raw evidence and send a bounded fact packet to an independent auxiliary Judge (for example, `get_text_auxiliary_client("ultrawork_judge")`).

The Judge input must contain workflow/step IDs, stable criterion IDs such as `S02:C01`, the criterion text, raw delegated evidence, relevant dependency evidence, and the current phase. For a Ralph-origin v2 route step, it must also contain the **complete digest-verified frozen Markdown** and the Route’s original `source_refs`; a path, line number, worker claim, or preselected regex excerpt is not sufficient evidence. The independent Judge—not an exact heading parser—semantically resolves every `(step_key, source_ref)` as `resolved`, `ambiguous`, or `unresolved`, records its selected heading/reason/evidence references, and may interpret headings, task labels, aliases, and natural-language descriptions. A `pass` requires every source ref to be `resolved`; ambiguity or absence must yield `rework` or `blocked`. Deterministic code still owns artifact readability, SHA-256 digest equality, state identity, and strict Judge-output shape; it must never silently rewrite the frozen Route. Preserve legacy non-route workflows’ existing evidence-only contract when they have no route-source identity. Require strict JSON with `pass|rework|blocked`, confidence, per-criterion assessments keyed by stable IDs, source assessments, cited evidence references, findings, and required action. Persist the raw evidence, normalized Judge report, model/task identity, and evidence-packet hash before a state transition. Fail closed to `rework` or `blocked` on unavailable Judge, invalid JSON, unsupported verdict, insufficient evidence, or an uncited criterion.

Keep structural state-machine safety—current workflow/step identity, dependency order, delegated-handle completion, phase validity, idempotency, and bounded retries—but make the **Judge verdict**, not rule-based evidence-content checks, determine semantic acceptance. Test paraphrased criteria, missing/contradictory raw evidence, Judge failures, dependency release, and global coverage of all stable criterion IDs.

### Global Judge evidence packet

This section is the default for Ralph-backed and other independently gated workflows. A Native CTO Swarm governed by `references/native-cto-swarm-lifecycle.md` deliberately combines Global QA, Global Judge, and synthesis into one evidence-complete `cto_final` card; do not re-expand that Native finalization into three cards.

A Global QA report is not a Global Judge decision. Before synthesis or completion, construct a separate digest-bound Global Judge packet containing the immutable global contract and persisted raw Dev plus independent QA evidence for **every** non-global route. Reject the transition if any route is missing either evidence class. Invoke the same fail-closed auxiliary Judge boundary, persist its normalized `judge_decision` and packet digest before transition, and require cited coverage of every global criterion. Regression-test that a single-route run invokes the Judge twice (route and global), the global packet exposes per-route raw evidence, and synthesis cannot start without the persisted global decision.

For one-shot or non-repeatable commands, never run the command outside its workflow-bound delegated execution path. If that contract is violated, do not fabricate a delegation handle or replay evidence as though a child produced it. Persist an explicit invalidation/cancellation event with the reason, and begin a separately audited fresh attempt only with user authorization.

## Agent profiles and state machine

| Agent | Allowed work | Required phase flow |
|---|---|---|
| `coder` | Code changes | RED → GREEN → step review |
| `general` | Documents, config, research handoff, non-code artifacts | execute → step review |
| `explore` | Read-only repository discovery | execute/read-only evidence → step review |

Persist workflow, steps, attempts, evidence, reviews, and append-only events in relational state. A retry must have a concrete review finding and a finite cap. Exhaustion is `failed` or `blocked`, never an infinite loop.

## Dispatch is evidence-bound

A generated prompt saying “call delegate_task” is not evidence that delegation occurred.

1. At the real dispatch call site, capture the returned delegation handle.
2. Bind it atomically to the active workflow step and agent identity.
3. On asynchronous completion, write the result to that exact step’s evidence.
4. Reject phase evidence for approved workflow steps until the assigned handle completed.
5. Keep a lightweight registry of workflow-bound handle IDs so ordinary delegations do not import or touch workflow state.

## Delegating code work to external CLI agents and parallel workers

Delegation to coding-agent CLIs, parallel delegated workers, and controller plugins is the dispatch arm of this class. The former standalone playbook is archived at `.archive/delegated-code-work-orchestration/`; provider-specific CLI recipes (Claude Code, Codex, OpenCode) are archived at `.archive/coding-agent-cli-orchestration/references/` — read the matching file before invoking that CLI.

- **Dispatch contract (every worker, every provider):** before dispatch confirm repository/workdir, a clean `git status --short`, tool version, and auth readiness; write acceptance criteria, allowed write scope, prohibited files/operations, required tests, and the stop-with-a-blocker failure path; prefer the provider's non-interactive one-shot command; give every concurrent writer its own worktree; use the narrowest permission mode that can finish the task and never authorize an unrequested commit, push, or deploy.
- **Worker prose is not verification.** Re-read changed source, inventory files, and run the focused test command yourself — a worker's report can describe tests or patches that exist only in its isolated worktree.
- **Parallelize independent mutation surfaces only.** A shared schema/migration/registry/entrypoint/fixture is a serialized ownership boundary: one worker per such surface, or a staged dependency order with the earlier migration verified first.
- **"Read only" is an instruction, not a filesystem boundary.** If an allegedly read-only lane coincides with unexpected changes, stop parent writes until it is terminal, re-read live task/run evidence, and re-read every file before editing — never overwrite an externally changed file from a stale read.
- **Parent-owned integration:** combined focused suite once non-conflicting workers finish → full suite → smoke/build → `git diff --check` and final diff review. Treat deletion of a pre-existing test as a regression unless the worker supplies a contract-level reason plus a parent-visible replacement. Recover isolated uncommitted work into a clean sibling checkout with source/target hash verification — never the user's dirty checkout.
- **Controller plugins** (the automation arm) keep observer and controller roles separate: hooks record immutable observations; a state transition requires an explicit, replay-resistant authorization artifact referencing the observation. Generate run-owned branches from the durable run ID; keep PR opening idempotent; snapshot Ops governance files (ID + digest) before creating run worktrees.
- **Notifications are a durable projection, not workflow truth.** Persist the originating gateway routing descriptor at creation, write the controller event plus an idempotent outbox row in controller state, publish to the board only after the controller transaction commits, and never let delivery failure accept, unblock, or mutate execution state.
- **Replace a local plugin without leaving a shadow copy.** Stage the new tree outside the active plugin directory; move the old tree to a backup root **outside** `$HERMES_HOME/plugins/` (a renamed backup inside `plugins/` is rediscovered as a duplicate manifest); restart once; then verify the canonical manifest hash, `hermes plugins list --plain --no-bundled`, and one installed-code smoke run — a source test suite never proves the installed manifest is enabled.
- Browser-provider plugins are a different class: follow `cdp-browser-automation` — takeover consent comes from the human in the browser's own permission UI, never a chat confirmation.

## Async completion → workflow progression bridge

An asynchronous child completion is **not** a completed workflow step. Preserve this explicit durable path:

```text
child completion event
→ bind handle to its exact step
→ persist the full structured child result as delegation evidence
→ enqueue a workflow-specific continuation for the parent
→ parent submits phase evidence
→ evidence validation
→ independent step review
→ mark completed and activate dependency-unblocked successor
```

1. A completion handler may record `agent_completed`, but must never auto-pass a phase or review merely because the child returned `completed`.
2. Require child contracts to return the step's evidence fields structurally (e.g. command, raw stdout, raw stderr, exit status, artifact paths, verification output), not solely a free-form or nullable summary.
3. The completion re-injection must name the workflow ID, step ID, active phase, and required report schema. A generic “subagent finished; act on it” notification is not a deterministic workflow bridge.
4. The normal post-turn handler must parse a strict phase report and transition only after the assigned handle completed. It then schedules a distinct review phase; only a passing review may mark the step completed and release dependent steps.
5. Keep this report-driven gate even for trivial work: direct completion → completed bypasses acceptance criteria and makes the event log untrustworthy.

**Required end-to-end regression:** exercise `next_prompt → real async delegate_task → completion queue → exact-session parent continuation → phase report → review report → successor activation`. Assert that empty structured evidence remains `awaiting_evidence`, no successor starts early, and a valid pass activates exactly the eligible dependency successor.

### Concrete completion-queue seam

When the shared async queue carries generic delegation events, attach workflow metadata only after confirming the handle belongs to Ultrawork:

1. In the async finalizer, consume the workflow-bound delegation ID and persist `agent_completed` first.
2. Resolve the still-active workflow step by `dispatch_id`; reject a stale, completed, blocked, or non-current step.
3. Add bounded metadata to the event — `workflow_id`, `step_id`, `step_key`, active `phase`, and a parent-only instruction — then enqueue normally.
4. The notification formatter must append this instruction **after** the child result. It must say: do not dispatch another child for this phase; extract only returned evidence; do not invent missing facts; end with the exact `ULTRAWORK_REPORT` schema.
5. Do not call `record_phase` or `record_review` from the finalizer. The normal parent post-turn hook owns those transitions and will schedule the distinct review prompt.
6. Normalize completion envelopes before persisting delegation evidence. A top-level background `delegate_task` may use a batch transport even for one child; its usable evidence can live in `results[0]` rather than root-level `summary`/`error`. Persist the selected child result plus its summary/error so the phase-report continuation receives real evidence rather than null placeholders.
7. If the completion-injected parent turn omits the required strict report, schedule one bounded repair continuation containing the exact report schema. Do not auto-pass a phase/review and do not retry indefinitely: persist the reprompt count/event, then leave a second malformed response as `awaiting_evidence` for explicit handling.

This preserves the durable audit trail while turning a generic async notification into a deterministic, phase-aware parent continuation. Cover both single and batch async finalizers if both can bind Ultrawork handles.

## Review gates

- **Step review:** verify acceptance criteria, required evidence, bounded scope, and TDD evidence for coder steps.
- **Normalize review verdict placement at the parser boundary.** Prompted agents commonly return either `{"phase":"review","verdict":"pass","evidence":{...}}` or `{"phase":"review","evidence":{"verdict":"pass",...}}`. Derive `verdict` from the top-level field first and then `evidence.verdict`; otherwise valid review evidence can remain `awaiting_evidence` and block dependent steps. Add a two-step regression proving nested `pass` completes S01 and activates S02.
- **Preserve criterion text exactly in review evidence.** When coverage is a criterion-keyed map, copy every manifest acceptance criterion verbatim—including terminal punctuation, capitalization, and whitespace—into `evidence.criteria`. Semantic paraphrases (for example, omitting a final period) can fail coverage, leave the step at `review`, and prevent successor activation. On rejection, surface the unmatched criterion in the continuation/status response; diagnose this with the append-only events (`phase_*_recorded` without `step_approved` means the review gate rejected the report, not that the dependency DAG stalled).
- **Do not re-delegate during a review phase.** The continuation for `review` must instruct the parent to independently assess already-recorded evidence and submit `ULTRAWORK_REPORT` with `pass`, `rework`, or `blocked`; a blanket "call delegate_task" instruction on every phase can cause duplicate work and violates one-shot command plans.
- **Enforce review-prompt parity.** `next_prompt()` must branch before emitting the generic delegation instruction: execute/RED/GREEN prompts may require a bound child dispatch, but a review prompt must require only a top-level `verdict` plus evidence. Add a regression that asserts the review prompt contains no mandatory `delegate_task` action and that a completed child is reviewed without a second dispatch.
- **Global review:** after all steps pass, independently inspect final changes, cross-step integration, plan acceptance criteria, and regression evidence.
- Global review may reopen explicit step IDs with findings; preserve previous evidence and enforce retry limits.

## Native workflow observability

When users ask to query **Hermes Ralph or Ultrawork data**, do not assume an external Ralph/OMX implementation. Hermes-native state is profile-scoped under `get_hermes_home()/harness.db`:

- Ralph plans are stored as `state_meta` entries keyed `ralph:<session_id>`; access them through `hermes_cli.ralph.list_plans()`, `get_rounds()`, and `list_template_history()`.
- Ultrawork owns `ultrawork_workflows`, `ultrawork_steps`, and append-only `ultrawork_events`; expose public read APIs such as `list_workflows()` and `list_events()` rather than duplicating SQL in callers.
- Keep model-facing lookup tools separated by state owner: `ralph_search` for plans/rounds/template history and `ultrawork_search` for workflows/steps/events. Require `plan_id` or `workflow_id` for drill-down; accept bounded `session_id`, `status`, and `limit` filters. Cap list sizes and long evidence strings before serializing output.
- Make each tool discoverable in both `toolsets.py` and `hermes_cli/tools_config.py`; otherwise it can register successfully yet remain unknown to `hermes tools enable <toolset>`.

## Direct Kanban Swarms vs Ralph→Kanban Route Controller

Do not infer `ralph_kanban_dispatch` merely because a Markdown plan contains Ralph terminology or a plan ID. First identify the requested execution backend:

- **Native Kanban Swarm:** `hermes kanban swarm` does not require Ralph. In automatic mode, Root/Intake starts CTO Planning, freezes a minimal task graph, and executes paired Dev → QA → CTO Route Judge routes.
- **Ralph→Kanban controller:** use `ralph_kanban_dispatch` only when explicitly requested with a real approved, digest-stable Ralph plan.

For a Native Swarm, inspect the board before duplicating work and preserve creator routing on the Root. `ceo == cto` is a direct naming correction for this lifecycle: new Native tasks and reports use `cto`, with no extra logical-role mapping. The exact Root Goal and any referenced plan are frozen and supplied with each task-specific Goal to Dev and QA. Fixed post-route stages are `opsconfig`, automatic `opsdocs` when the Root has run longer than three days, one combined `cto_final`, main-checkout merge, and unconditional registered-worktree cleanup. Do not create `opsprotocol`, a separate Global-QA/Judge/Synthesis chain, or a user-approval gate for Opsdocs.

See `references/native-cto-swarm-lifecycle.md` for the canonical schema, path contract, merge/cleanup ordering, and required regressions. Root queue status alone is never proof of completion; read the source-aware run state and finalization events.

## Hermes Kanban platform operations

Configuring Hermes Kanban itself (gateway dispatcher, profiles, task lifecycle, notifications, custom tools) is the platform layer beneath the orchestration contracts above. See `references/hermes-kanban-operations.md` for the configuration baseline, profile design, lifecycle and failure decision tables, creator-awareness patterns, extension/migration rules, and verification checklist. See `references/kanban-recovery-controller.md` for the single-board recovery decision table, safe dependency replacement, and dedupe key.

Keep the layers separate: Kanban is durable truth, the dispatcher owns readiness/crashes/retries, an Orchestrator Profile owns acceptance decisions, Workers own execution, and notifications are delivery — never orchestration.

## Ralph planning-only handoff to Kanban

When a user asks for a Kanban-autonomous implementation plan, separate **plan authoring** from **Kanban dispatch**:

1. Start or import the Ralph plan, then obey its planning-only guard: inspect read-only sources and write **only** the designated plan Markdown.
2. Make every execution unit a `### Task N:` section with source coverage, dependencies, TDD/verification, stop/recovery conditions, and a durable handoff. For a requested fixed route count, keep exactly that many top-level tasks; let Kanban materialize Dev → Functional QA → CTO QA children at route activation rather than expanding static cards in the plan.
3. Do not hand-author a legacy `ULTRAWORK_MANIFEST` for new Ralph plans. Ralph compiles the digest-frozen Markdown into RouteManifest v2 at approval.
4. In the planning-only phase, verify the written artifact read-only (task-heading count, source coverage, and absence of a manual legacy manifest). Do not try to advance Ralph lifecycle state, create Kanban cards, or dispatch code work from the planning guard.
5. Report the plan ID/path and its waiting-for-independent-review status. Only after approval, readable digest equality, validated RouteManifest v2, and a clean target base may the controller invoke `ralph_kanban_dispatch` exactly once.

## Ralph → Kanban Route Controller

When an approved Ralph plan must execute through durable named Kanban Profiles rather than ephemeral `delegate_task`, treat Kanban as an **execution backend** for the existing Ralph/Ultrawork contract, not as a second plan parser or an unrelated checklist system.

1. **Require explicit dispatch.** Never auto-start every `status="done"` Ralph plan discovered in durable storage; historical, test, or unrelated plans may be present. Require a user/controller dispatch request naming the approved plan, target board, and repository/workspace.
2. **Verify once, then freeze.** Before creating a Kanban root, require the plan to be approved, executable, readable, digest-equal to its approved bytes, and backed by a validated RouteManifest v2. Reject absent/changed manifests or source task coverage gaps before any child task is created.
3. **Preserve a single execution owner.** Do not call native `create_from_ralph_plan()` and separately create Kanban work for the same plan: that starts competing execution engines. Enforce an atomic one-active-run constraint keyed by `ralph_plan_id` across the chosen backend; record board/root/task mappings durably.
4. **Reuse execution semantics through a stable contract.** A plugin must not depend indefinitely on private Ralph/Ultrawork helpers. Prefer a narrow public, read-only contract such as `load_verified_execution_plan`, `refine_route_task`, and `judge_route_evidence`; native Ultrawork and the Kanban controller consume the same verified plan/route/refinement/Judge semantics.
5. **Materialize route tasks just in time.** Keep the top-level RouteManifest immutable. When a dependency-ready route node activates, create a task context from the frozen source refs, relevant architecture/invariants, verified upstream handoffs, repository snapshot, branch/worktree ownership, and previous QA findings. Do not pre-expand the full plan into static cards.
6. **Use a controller service for cross-task transitions.** A dispatcher-spawned CTO Worker is task-scoped and cannot be the sole authority for completing, unblocking, or promoting sibling cards. A durable controller/plugin owns atomic dependency transitions, idempotency, retries, and recovery; the CTO Profile supplies bounded technical decisions, task refinement, fault analysis, and global review evidence.
7. **Map every implementation attempt to independent QA.** Create a developer card first, then an independently assigned QA card only after complete developer evidence. QA pass goes to the semantic Judge with the complete digest-verified Ralph Markdown and raw evidence. QA rework creates a new bounded attempt carrying only failed criteria, exact findings, passed criteria that must not regress, and a changed recovery strategy.
8. **Persist controller state separately from comments.** Record run, route node, attempt, Kanban task ID, handoff, Judge report, evidence-packet digest, and append-only events. Comments remain human-readable context; they are not sufficient for recovery or idempotency.
9. **Finish with integration and global review.** A developer/QA card being `done` is a handoff, not plan acceptance. Only a global integration check plus independent coverage of every Ralph acceptance criterion can set the Kanban run/root workflow to completed.

A local Controller plugin is preferable to a broad Core fork for user-specific swarm policy. If a small Core addition is necessary, keep it to the neutral verified-plan/refinement/Judge contract; preserve the controller itself as a versioned plugin with a migration and restart-safe test suite.

### Swarm profile topology configuration

For a Ralph→Kanban controller that uses named lead gateway profiles and employee workers, keep the hierarchy in one explicit, versioned config surface rather than hard-coding a flat profile list. A suitable shape is `kanban.swarm.agents`:

```yaml
cto:     {gateway_service: cto,     employees: [cto]}
devlead: {gateway_service: devlead, employees: [dev1, dev2, dev3, dev4]}
qalead: {gateway_service: qalead,   employees: [qa1, qa2, qa3, qa4]}
opslead:{gateway_service: opslead,  employees: [opsconfig, opsdocs, opsprotocol]}
```

1. Validate the complete topology before controller state or Kanban cards are created: non-empty service/profile names, non-empty unique employee lists, CTO membership, and disjoint Dev/QA worker sets.
2. Derive controller lanes from employee lists (`dev`, `qa`, and each read-only Ops lane). Lead gateway identities are orchestration metadata; do not silently assign implementation or independent QA cards to a lead merely because it owns the service name.
3. Keep a backward-compatible default topology in the plugin, but let the controller entrypoint read the persisted config on every fresh controller construction. Reject malformed user topology rather than falling back to a different hidden routing map.
4. Add a focused regression proving config parsing and that lead services remain distinct from assigned employee lanes; retain the existing full controller suite.
5. Persist Lead-to-employee dispatch as controller state, not a conversational request: create a durable assignment keyed by lead task, route, and attempt; allow exactly one compare-and-set transition from `awaiting_dispatch` to `dispatched` with the concrete employee task ID. Reject wrong-lead and replayed dispatch.
6. For lead-enabled routes, enforce `DevLead → Dev employee → CTO dev admission → QALead → independent QA employee → CTO semantic Judge`. CTO admission uses an explicit verdict such as `admit_for_independent_review`; QALead cannot dispatch QA before it.
7. Expose dedicated DevLead and QALead dispatch handlers that bind the actor server-side rather than accepting an arbitrary caller-supplied role. If either lead lane is configured, require both; retain direct Dev→QA flow only for an explicitly leadless compatibility topology.
8. Apply config through `hermes config set` when possible. If a running gateway holds the config file and atomic replacement is denied, cleanly stop the gateway, finish the idempotent config writes, run the parser/tests, then restart once and verify gateway status. Never start separate per-profile gateways sharing one platform credential; use one multiplexed inbound gateway only when that routing mode is deliberately configured.

### Kanban plugin process-boundary rules

A Kanban lifecycle hook is not a central controller daemon. `kanban_task_claimed` runs in the dispatcher before worker spawn; `kanban_task_completed` and most `kanban_task_blocked` calls run in the worker/caller process after the task transition. Therefore install and enable the controller plugin in the dispatcher profile **and every CTO/Dev/QA worker profile**, and resolve state through the dispatcher-pinned Kanban DB path rather than a profile-local board path.

- Hook callbacks are synchronous, best-effort observers. Rehydrate task/run/evidence from durable storage and make each controller transition idempotent; never trust hook return values or a worker's prose summary alone.
- A completion hook may create the next QA/Judge task only after verifying its own board transaction has committed.
- Do not create or mutate Kanban cards from a blocked-hook path until the specific `block_task` call site is known post-commit. Dependency blocks can fire while the board write transaction is still open; controller code may record a separate controller-state marker there, but a second board write risks lock contention.
- Test user-plugin discovery/enablement, controller imports in every Profile, completion-hook rehydration, cross-profile visibility via `HERMES_KANBAN_DB`, and the unsafe dependency-block path. Restart the Gateway after plugin updates; a live process does not reload plugin code.

### Shared-runtime adapter parity for plugin entrypoints

When a plugin dispatches a Ralph-backed run into a shared core runtime, every continuation surface must target that same runtime identity. Do not leave child refinement, child dispatch, completion/block hooks, observations, or recovery tools routed to a legacy controller DB merely because public tool names were retained.

1. Add an integration test that dispatches a shared `uwk_*` run through the public Ralph entrypoint, then invokes every public continuation tool against it. Assert state remains in shared runtime tables and no legacy controller row is written.
2. Derive child provenance from the frozen route definition in the shared runtime; never trust caller-provided parent source refs for a shared run.
3. Test real post-commit `kanban_db.complete_task()` and `kanban_db.block_task()` paths. Calling an outbox helper directly does not prove the lifecycle bridge is wired.
4. A global reconciler may run from the normal dispatcher tick, but it must drain one replay-safe durable outbox across active boards/runs. Never add a scheduler per swarm.
5. If legacy records stay readable, reject or explicitly adapt legacy-only write operations for shared run IDs; never silently create divergent state.

### Source-of-truth deployment and profile parity

When a local controller exists both as a Git working tree and installed plugin copies, the Git working tree is the editable source of truth. Do not patch only the installed default copy and mistake a passing local import for a deployable change.

1. Identify the actual source repository and compare it with the installed default copy, excluding VCS and cache directories. Preserve pre-existing source changes; do not overwrite source with the installed copy.
2. Run focused source tests with the intended core checkout on `PYTHONPATH`, then run the complete plugin suite before deployment.
3. Stop the Gateway. Make a timestamped backup of the installed plugin and controller/Kanban state before replacement.
4. Deploy the tested source excluding VCS and caches. Where worker profiles have isolated plugin directories, deploy the same source to every configured controller, Dev, and QA profile so hooks remain version-aligned.
5. Verify installed manifest identity/version plus the source-vs-installed manifest hash, restart the Gateway once, then verify enabled plugin version and Gateway PID/status.
6. Run at least one installed-copy test or import after restart. Source tests alone never prove the Gateway loaded the intended revision.

### Local plugin identity, replacement, and activation

When renaming or replacing a local Hermes controller plugin, treat the manifest identity, installed directory, active project workspace, and Gateway process as one deployment unit.

1. Inspect `hermes plugins list --plain --no-bundled` before removal; delete the actual installed plugin directory/name, not a source-repository nickname inferred from conversation.
2. If the source project directory must be renamed, switch the active Desktop Project away first, rename the Git root, verify `git rev-parse --show-toplevel` and working-tree status, then create/switch to a Project anchored at the new path. Do not lose uncommitted work.
3. Stop the Gateway before replacing a loaded plugin. Remove the old plugin through `hermes plugins remove <installed-name>` when possible; if removal is blocked by local file attributes, resolve permissions only on that exact stopped-plugin directory, then verify it no longer exists.
4. For a local working-tree deployment, copy the complete working tree into `$HERMES_HOME/plugins/<new-manifest-name>/` while excluding `.git`, interpreter caches, and test caches. Verify the installed `plugin.yaml` parses, its `name` equals the target identity, and its manifest hash matches the source.
5. Enable the new plugin, restart/start the Gateway once, then verify both `hermes plugins list --plain --no-bundled` and `hermes gateway status`. Treat a request for built-in tool override as a separate privileged authorization; do not grant it merely to finish installation.
6. Keep source, installed copy, and runtime verification separate in the report. A successful source test suite is not proof that the installed manifest is enabled or that the Gateway restarted.
7. When consolidating a local auxiliary plugin into a controller plugin, preserve every public tool name, schema, handler behavior, and toolset label. Add the absorbed tools to the destination manifest's `provides_tools`, add registration and at least one behavior regression, deploy the verified destination copy first, then disable/remove the old plugin and restart the Gateway. Do not delete the source plugin merely because a similar tool name exists in another extension.

### Windows physical lead gateways without platform or dispatcher conflicts

When running dedicated physical Gateway processes for CTO/lead profiles alongside a default Gateway:

1. Keep the default Gateway as the only `kanban.dispatch_in_gateway: true` process. Set it to `false` in every secondary lead profile before starting those processes, so they cannot become concurrent dispatchers on the shared Kanban DB.
2. Verify the *effective* enabled adapter set for each profile, not only YAML `platforms.*.enabled` fields. Environment credentials can activate platform adapters at runtime. Either provide distinct credentials per physical Gateway or disable all platform credential inputs for the secondary profile.
3. To temporarily disable secondary profile messaging without deleting secrets, comment its platform-specific `.env` entries in place using a stable marker such as `# disabled-messaging-platform `. Do not copy credentials into backups, logs, or agent output. Re-enable by removing only that marker.
4. Start each profile Gateway, then verify both `hermes -p <profile> gateway status` and an effective-config probe show the expected process and no enabled messaging adapters. On Windows, Scheduled Task creation can require UAC; Hermes may fall back to a Startup-folder entry, which must be reported as the actual persistence mechanism.
5. If a process exits at startup, read its profile-local `logs/gateway-stdio.log` before retrying. Shared API ports and duplicate platform sessions are configuration conflicts; fix the conflicting adapter inputs rather than repeatedly restarting.

### Cron recovery for physical lead gateways

When the requested recovery mechanism is **Cron**, do not substitute a Windows Scheduled Task:

1. Remove any superseded OS-level recovery task and script.
2. Put a deterministic Python watchdog under `$HERMES_HOME/scripts/`. It must call `hermes -p <profile> gateway status` and `hermes -p <profile> gateway start` directly—do not hard-code a Hermes executable path.
3. Create it as a script-only Hermes Cron job: `no_agent=true`, `schedule="every 5m"` (not bare `5m`, which is one-shot), `deliver="local"`, and a relative script filename.
4. Keep healthy runs silent; emit only recovered or failed profile names. Verify a manual Cron run and a controlled stop → Cron run → restart recovery, then confirm all four physical Gateway statuses.
5. The Cron scheduler depends on its host Gateway process; state that dependency plainly in the final report.

### Controller-owned worktree lifecycle and safe automatic reclamation

The rules below are the conservative default. For a Native CTO Swarm whose accepted contract explicitly requires cleanup after the main-merge attempt with no clean/HEAD/active-attempt business preconditions, use the bounded exception in `references/native-cto-swarm-lifecycle.md`: force-remove only Run-registered paths beneath the owner `HERMES_HOME/worktree` root, even when merge fails. Path ownership remains mandatory.

A route controller that creates Git worktrees must own their lifecycle durably; never rely on workers, task comments, or a generic filesystem cleaner to remove them.

1. Register every Feature, Ops, and Delta-QA worktree immediately after creation: run ID, kind, absolute path, branch (if any), expected SHA, state, cleanup attempts/error, and timestamps.
2. On terminal run states (`completed`, `blocked`, `failed`), mark registered worktrees `pending_cleanup` only after all controller Dev/QA/child/Ops attempts are inactive. Execute deletion after the enclosing state transaction commits.
3. Before removal, verify the registered path is a clean Git worktree and both its recorded SHA and current HEAD remain readable from the base repository. Use `git worktree remove <path>` followed by `git worktree prune`; never use `--force` automatically.
4. Dirty worktrees are `quarantined`, not deleted. Missing, unreadable, or removal-failed worktrees become `cleanup_failed`; retain their path/error and append an auditable event. Worktree removal must not delete Feature/Ops branches by default.
5. Claim cleanup with CAS (`pending_cleanup → cleaning`) so concurrent controllers cannot delete the same worktree. On startup, reconcile only terminal runs with `pending_cleanup` or interrupted `cleaning`; never discover-and-delete unregistered worktrees.
6. Candidate Ops worktrees remain through Delta QA. Reclaim Feature, Ops, and Delta-QA worktrees only after final terminal state and retained commit readability.
7. Regression-test clean Feature cleanup with branch retained; dirty quarantine; maintenance Ops cleanup; candidate Ops plus Delta-QA final cleanup; restart reconciliation; active-attempt refusal; and post-removal `git worktree list --porcelain` verification.

### Controller-owned worktree lifecycle: TDD controller seams

For worktree lifecycle changes, helper-only unit tests are insufficient. Add vertical, real-Git temporary-repository regressions that prove the controller seam:

1. Create a run through the real dispatch/worktree path and assert each created Feature/route and integration worktree is immediately represented in durable state with run, route, attempt, path, branch, frozen base, candidate SHA, integration/cleanup state, and reason fields.
2. Drive the actual Dev → QA → Judge completion path and assert route acceptance occurs only after the candidate has been merged into the run-owned integration branch; assert the base branch remains unchanged.
3. Force a frozen-base ancestry failure, current-base drift, or merge conflict. Assert a durable reason/event, blocked route/run state, no rebase/reset, and retained branch.
4. Set a terminal run plus an interrupted `cleaning` claim, then invoke the normal reconciliation entrypoint. Assert CAS removes only clean registered worktrees, preserves branches, quarantines dirty trees, and records missing/removal failures.

Use real Git commands in a temporary repository. Validate database state and `git worktree list --porcelain`/branch reachability together; mocks can hide unsafe deletion or accidental base mutation.

### Feature branch, PR, and governance observer backend

See `references/feature-branch-governance-swarm.md` for the compact operational contract and checklist.

For code delivery through Kanban, use run-owned Git hierarchy: `base → feat/ralph-<plan> → route/<route>-<attempt>`. Explicit dispatch must persist repository root, base ref/SHA, integration branch/worktree and PR identity; reject non-Git, dirty, or drifting bases. Dev handoffs require exact branch, commit SHA, clean status, diff, and test evidence. Functional QA verifies the exact candidate revision and behavior; CTO QA separately verifies process coverage, scope, static/style conformance, and merge eligibility. Only both gates permit deterministic dependency-ordered integration; block conflicts/base drift and never silently rebase or merge to base.

PR lifecycle is idempotent and non-destructive: reconcile an existing PR by exact head branch, create at most one draft PR, persist its identity/head SHA, and never auto-merge, close, force-push, or delete branches without a separate explicit policy.

Operations in this Ralph/feature-governance backend are read-only observer lanes (`opsdocs`, `opsconfig`, `opsprotocol`): snapshot docs/config/protocol digests at dispatch and emit versioned proposals only. This is not the Native CTO contract; Native runs use only `opsconfig` and autonomous `opsdocs` as defined in `references/native-cto-swarm-lifecycle.md`. AGENTS/CLAUDE/SOUL, gitignore, lint/CI, and communication-protocol changes require separate maintenance branches plus CTO QA; never alter active worker context. Project terminal hooks into an append-only ledger keyed by immutable board/event identity. A separate CAS-authorized controller decision, bound to snapshot ID, frozen digest and expected revision, is the sole authority that may create successor/rework tasks. Do not write to the Kanban board from an unsafe block-hook path.

**Required regressions:** fixed-base worktrees and QA SHA pinning; Functional QA → CTO QA → integration; merge conflict/base drift; duplicate dispatch/restart PR reuse; observer replay/non-mutation; stale decision refusal; and proof that Ops proposals cannot mutate a running task.

## Ralph import and execution triggers

Treat Hermes-native workflow control as session-bound state transitions, not as a generic shell command or an external orchestration integration.

- Runtime registry dispatch supplies `session_id`, not `parent_agent`. Every model-facing workflow control handler must accept and prefer that runtime session ID, with `parent_agent.session_id` only as a direct-Python-call fallback. Regression-test the exact seam with `registry.dispatch(tool_name, args, session_id="...")`; otherwise a correctly registered tool will fail with a misleading "requires an active parent session" error.
- `ralph_execute` starts/resumes/adds criteria/clears only the calling agent's session and returns `ralph.continuation(state)` as the next agent instruction. It starts planning only; never offer model-facing self-approval.
- `ultrawork_execute` accepts only an approved Ralph `plan_id`, preserves the manifest digest gate, creates the workflow in the calling session, and returns `ultrawork.next_prompt(workflow.id)` so the normal real-delegation binding supplies evidence.
- `ralph_import_plan` converts exactly one external Markdown source into an **active, unapproved** Ralph plan. Accept one of inline `markdown` or a bounded UTF-8 `source_path`; derive the objective from an explicit field or first H1; copy the original text to the designated Ralph plan path with exclusive creation. Do not overwrite existing plans.
- Make import failure atomic from the user's perspective: if plan-file creation fails after provisional Ralph state is created, restore the prior state (or clear the provisional one). Preserve the standard Ralph refinement/review gate before any Ultrawork handoff.
- Test inline and path imports, exclusive-source validation, destination collision behavior, current-session enforcement, returned next instructions, and an isolated real import that reads the persisted file back.

### Ralph plan-repair workflow

When an imported implementation plan is awaiting review or needs correction, create a fresh Ralph import in the current session if the prior plan cannot be resumed by ID; do not claim that an inaccessible historical plan has been approved.

1. During an active Ralph planning turn, treat the designated plan file as the only writable artifact. Use its **relative path** for edits; an absolute path can be rejected by the planning guard even when it resolves to the same file.
2. Validate source/docs read-only before editing. If the planning guard blocks shell, status, or clarify calls, record the unresolved source contract in the plan and make the first execution step an explicit gate rather than inventing runtime facts.
3. Correct verified integration contracts before approval. Hermes memory providers use `$HERMES_HOME/plugins/memory/<name>/`, subclass `MemoryProvider`, expose `register(ctx)`, and activate through `memory.provider`; do not use the generic plugin root as their install target.
4. After edits, verify obsolete-contract searches return zero hits, the Ultrawork manifest marker occurs exactly once, and the first execution task reflects the corrected contract.
5. Do not self-approve from a planning turn. Complete the turn so Ralph can enter independent review; only a digest-stable approved plan may enter Ultrawork.

## Approved-plan follow-on goals and Ralph review semantics

When a user reviews a Ralph plan, distinguish **current-round feedback** from **new follow-on goals**; never infer one from the other.

1. Review actions should keep lifecycle controls (`pause`, `clear`) separate from a free-text route. Free text during review is a current-round revision request: preserve the round number, persist the comment, and reanalyze that same round.
2. `adopt Judge recommendation` is conditional on the Judge verdict. If the verdict is `approve`, it may approve/freeze the current plan. If it is `revise` or `blocked`, convert the Judge findings into same-round feedback; never force approval of a plan the Judge found incomplete or unassessable.
3. Do not mutate or reopen a `done` plan merely because the user later supplies new objectives. An approved plan may already be executable by Ultrawork and its plan digest/manifest must remain stable.
4. Collect post-approval objectives through an explicit next-round intake contract (typed action/request ID), not ordinary chat-message inference. Parse multiline/bulleted input into bounded, ordered, de-duplicated goals.
5. Create a successor Ralph plan for the intake: new plan ID/path, immutable `parent_plan_id` linkage, copied/readable parent artifact as the starting reference, and a fresh active round seeded with the new goals. The parent remains `done` and independently eligible for Ultrawork.
6. Make successor creation atomic and idempotent per intake interaction. On artifact-copy failure, remove provisional successor state and leave the parent intact. Enforce normal single-live-owner/session rules.
7. Test both branches across the domain, tool, CLI/Gateway/TUI, and Desktop clarify surfaces: Judge-approved → skip/finalize parent; Judge-approved → multiple goals → successor continuation; Judge-revise/blocked → same-round revision; free-text feedback → same-round revision; parent Ultrawork handoff still validates after successor creation.

### Approved-round finalization and accidental-next-round recovery

Treat **finish current plan** and **accept new goals** as mutually exclusive, explicit lifecycle actions:

1. A recognized finish action finalizes the approved current plan; it must not be parsed as goal text or create a successor/next round. Only actual accepted goal text may set the plan active for the next round.
2. Do not submit execution commands such as “dispatch Ultrawork” through next-round free-text intake. Finish the current plan first so the normal approval path freezes the digest and compiles the manifest; dispatch only afterward.
3. If a stale or accidental next-round goal was consumed, do not repair the resulting plan by injecting a v1 manifest or marking it done directly in storage. First make a backup, then assert the exact session, plan ID, active round, trailing history event, and accidental goal before withdrawing only that event. Restore `awaiting_next_round` with no pending goal, then invoke the normal finish path.
4. The normal finish path is authoritative because it recomputes the digest and compiles RouteManifest v2. If compilation fails, leave the state at `awaiting_next_round` with no execution manifest; preserve the error and require a bounded retry or a separately reviewed compiler fix. Never substitute a hand-written static v1 manifest to unblock dispatch.
5. Regression coverage must prove: exact finish input reaches `done` without adding subgoals; valid goal input alone opens Round 2; an accidental-goal recovery preserves the approved artifact and returns to intake; and post-finish execution receives a v2 route (including required global-review nodes) rather than eager v1 steps.
6. **Do not hijack ordinary chat while intake is pending.** Gateway/TUI code must route only the active clarify request's response into next-round handling. A normal user message (status check, dispatch request, or unrelated discussion) must remain a normal turn; it must neither become a goal nor be silently dropped. Test this at the prompt-submit boundary, not only in the Ralph state function.

## Lossless workflow archiving

Expose Ralph and Ultrawork archival as separate built-in, session-gated control tools rather than deleting durable records.

- `ralph_archive(plan_id)` must preserve plan Markdown, rounds, template metadata, and approval history; model archive state explicitly (`status="archived"`, timestamp/metadata) and prevent archived plans from resuming.
- Refuse Ralph archival for `active` and `awaiting_review` plans. Require the workflow to be paused, completed, or cleared first so planning is not silently interrupted.
- `ultrawork_archive(workflow_id)` must preserve steps, phase/delegation evidence, and append-only events. Add a `workflow_archived` event carrying the prior terminal status.
- Refuse Ultrawork archival while `running` or in `global_review`; never orphan live subagent handles or skip required evidence/review gates.
- Treat archival as logical/lossless by default: leave source plan files and database rows intact, expose archived status through search tools, and add restoration only as a distinct, explicitly designed operation.
- Test active-work rejection, terminal workflow archival, event preservation, non-resumability, and toolset registration.

## Reusable Ultrawork delegation templates

Make the Ultrawork `coder`, `general`, and `explore` roles reusable built-in delegation templates, not inline prompt fragments in the workflow engine.

1. Define stable named templates in a lightweight module (for example `tools/delegation_templates.py`) and expose them via `delegate_task.template` for single tasks and per-task batch entries.
2. Validate template names at the delegate boundary and render the selected contract into the child system context. Thread the field through the registry handler and `run_agent._dispatch_delegate_task`; adding only a schema field is not functional.
3. Let Ultrawork map each step agent to one template and pass only workflow-specific facts — workflow/step IDs, phase, objective, acceptance criteria, and required evidence — as task context.
4. Template contracts must be evidence-oriented: coder requires genuine RED/GREEN commands and exit codes plus minimal scope; general requires artifact verification and rollback/risk; explore is strictly read-only and reports paths/symbols, observations, confidence, and a recommended next step.
5. Test template rendering, `delegate_task` schema exposure, role-to-template mapping in Ultrawork prompts, and the normal workflow phase/state regressions.
- Verify three paths: focused state/tool tests, fresh registry discovery plus dispatch, and `hermes tools list` after enabling. Toolset changes require a new session (`/reset`) before the active model receives the schema.

## Finite Planning Loops Inside a Durable Workflow

When a workflow contains iterative AI reasoning (retrieval expansion, candidate extraction, context-validity checks, or outcome review), implement it as a persisted finite planning loop rather than an implicit `while` loop or free-form recursive delegation:

```text
freeze/redact state snapshot
→ Plan (rule, AI, or hybrid)
→ Validate plan against a LoopSpec
→ Execute only allowlisted actions
→ Judge evidence and state change
→ completed | continue | blocked | retryable | failed_terminal | exhausted | cancelled
```

Persist a run, round, immutable validated plan, and append-only events. A plan must carry its input/context version, action allowlist, budgets, expected state changes, success criteria, and stop conditions. The executor must never receive unrestricted LLM-authored tool calls.

Rules:

- Separate **logical rounds** from **transport retries**; a retry reruns the same round idempotently and never consumes a round.
- Permit `continue` only when the previous round produced a declared new state/gap and the next plan has an unvisited target. Duplicate plans over an unchanged snapshot terminate as no-progress.
- Make a periodic scheduler tick its own finite run, rather than leaving a single run active forever.
- Use a rule planner for deterministic maintenance; restrict AI/hybrid planners to semantic choices inside server-provided candidate sets.
- Require per-loop action allowlists and hard caps for rounds, attempts, target count, characters, tokens, and wall-clock time.
- Cancel or terminalize session-bound runs when newer user input supersedes their snapshot. Terminal or stale runs cannot resume.
- Persist idempotency and review-deduplication keys for repeated events; update the existing review/run rather than spawning an unbounded follow-up chain.
- Keep extraction/review loops quarantined: they cannot directly promote accepted knowledge, update production indexes, or mutate skills without their own explicit review gate.

## Verification

Write tests first for:

- AI classification overrides misleading task wording;
- successful template history is reused;
- failed history is injected as optimization feedback;
- invalid/missing manifest and changed digest are rejected;
- coder vs general phase transitions;
- delegation-handle binding and completion recording;
- evidence rejection before a required subagent completes;
- bounded rework exhaustion;
- global review pass, block, and reopen behavior;
- persistence/reload of all workflow fields.

Run focused workflow tests plus the existing delegation/async-delegation suite. Compile every CLI, gateway, TUI, and runtime integration file touched. If a broader suite is blocked by an interpreter dependency mismatch, report the exact environment blocker separately from feature-test evidence.

## Audit checklist: execution handoff integrity

When reviewing an approved-plan → durable-execution handoff, test state transitions with direct repros, not only happy-path unit mocks:

1. **Dependency semantics** — validate a DAG (reject self-dependencies and cycles) and activate only pending steps whose declared dependencies are completed. Checking that dependencies merely name existing steps is insufficient.
2. **Evidence semantics** — make `evidence_required` and acceptance criteria executable gates. Verify a workflow cannot pass RED, GREEN, step review, or global review with empty evidence; coder evidence must contain actual command/exit-code facts.
3. **Single-consumption and ownership** — explicitly decide whether an approved plan can launch more than one workflow. If not, atomically bind it to the first workflow. For mutating lifecycle tools such as archive, verify the target belongs to the caller's session or document an intentional profile-global administrator model.
4. **Outcome feedback** — execute the real global-review completion branch and assert it writes success/failure to planning/template history. Lifecycle code after a terminal return is not reachable.
5. **Surface prompt parity** — each CLI, gateway, TUI, and desktop start route must submit the canonical continuation, including manifest instructions. Test `slash.exec → command.dispatch → typed send` as well as direct dispatch.
6. **Real delegation binding** — test `next_prompt` → real `delegate_task` handle → async completion → durable evidence → permitted phase report. Schema/template-rendering tests alone do not prove the binding.

## Reliability audit of Ralph → Ultrawork

When asked whether plans can *reliably* execute code or general work, distinguish structural eligibility from demonstrated delivery reliability.

1. Inventory plans through `ralph_search(resource="plans")`, then inspect every `done` plan independently. For each, verify: artifact readable, frozen digest equals current bytes, execution manifest exists, and the installed validator accepts it. `status="done"` alone is never sufficient: path reuse or later edits can leave an approved record stale.
2. Inspect `ultrawork_search(resource="workflows")`, then drill into representative completed, blocked, and running workflows with `steps` and `events`. Treat a completed arithmetic/read-only workflow as evidence only for that class of work—not for configuration, document delivery, or code changes.
3. For real code reliability, require at least one end-to-end, persisted success in a real repository: approved immutable plan → actual bound delegate → RED → GREEN → independent step review → dependency handoff → global review → completed. Passing unit tests or a RED-only workflow proves control-plane behavior, not delivery reliability.
4. Verify role fidelity. Code-changing route/child steps must use `coder`; `general` only proves bounded non-code work. A dynamic refiner may choose a child role, but do not treat that possibility as a frozen guarantee unless the materialized child manifest proves it.
5. Compare source-level prompt behavior with the state machine. A generic dispatch instruction leaking into `review` is a duplicate-work/one-shot-risk even if validation prevents automatic approval. Report it as an execution reliability gap, not a parser failure.
6. Report separately: (a) can parse/dispatch, (b) fails safely, (c) has successful empirical evidence for the requested work class, and (d) remaining blockers. Do not start a workflow merely to answer an analysis request; creation is persistent and side-effectful.

## Pitfalls

- Do not parse arbitrary task headings as the durable execution contract.
- Do not make execution re-classify a previously approved plan.
- Do not mark a workflow complete when the last step passes; require global review.
- Do not auto-retry without a changed finding, input, or strategy.
- Do not make a producer-side async completion path import heavy workflow modules for every normal subagent completion.
- Do not mistake a green happy-path suite for handoff coverage: include invalid dependency order, empty evidence, replay, ownership, and post-global-review outcome tests.
- For Kanban-driven runtime transitions, test real post-commit `complete_task()` and `block_task()` calls, not only a direct event-queue helper. Assert queued completion and block receipts are consumed exactly once.
- A QA/Judge `rework` must materialize a bounded fresh Dev attempt with failed criteria, raw findings, non-regression criteria, and changed recovery strategy; blocking immediately is a semantic regression. Freeze per-route worker profiles in the execution spec and verify a retry uses that profile rather than a default fallback.
