---
name: kanban-orchestrator
description: Durable Kanban task orchestration, acceptance, health monitoring, and failure handling for Hermes multi-profile workers.
version: 1.1.4
---

# Kanban Orchestrator

Use this skill when work needs cross-session execution, multiple Workers, dependencies, retries, human input, or final acceptance.

## Before creating a task
1. Classify the work: `general`, `code`, `research`, `review`, or `deploy`.
2. Call `kanban_get_strategy` when available, otherwise use `references/strategy-templates.md`.
3. Set workspace, max runtime, max retries, assignee, and explicit acceptance criteria.
4. Use idempotency keys for webhook or scheduled creation.
5. **Default creation mode: Swarm.** Unless the user explicitly requests a single card, or the work is clearly unsuitable for fan-out, create a Swarm graph with parallel Workers, a Verifier, and a Synthesizer. Do not merely create a normal card and describe a Swarm as a future option.
6. Resolve Worker/Verifier/Synthesizer profiles from configured defaults or current profile capabilities. If defaults are missing, make the smallest reasonable assignment and state the assumption rather than silently falling back to a single card.
7. Subscribe the Swarm root/Blackboard to the creator's original Gateway session before returning the graph. Never hard-code Feishu, Telegram, a group, or a recipient; preserve platform, chat, thread, user, and notifier profile from Gateway session context.
8. For complex work, create a root task and explicit child dependencies; keep independent children parallel.
9. Treat an explicit request to “create a new task” as a creation request, not a request to locate or report an existing task. Create a fresh card or Swarm even if a prior test task already exists; return its new root/task ID and verify its initial status. Do not substitute a completed historical task or merely explain how to create one.

### Default Swarm versus single-card exception
The default is a real fan-out/fan-in graph: Worker cards run in parallel, Verifier depends on every Worker, and Synthesizer depends on the Verifier. A single card is appropriate only for atomic reads, trivial one-tool operations, tightly sequential work, or when the user explicitly asks for one task. Record the exception briefly in the task summary when it is not user-requested.

### Creation-vs-status pitfall
When the user asks where a task is, first determine whether they are asking for the location/status of an existing card or correcting the agent to create a new card. If they explicitly clarify “I want to create a new task,” act immediately with the create operation, then read back the created card and board health. A successful create response plus `status=ready` and a board count increase is the minimum evidence; do not claim execution has started until a dispatcher/Worker event confirms it.

### Delegation is not a Kanban task
`delegate_task` is ephemeral child-agent work, not a durable or user-queryable task card. Never call a delegation ID a created task, worker card, or trackable work item. For multi-step repairs that require status, retries, verification, or handoff, create and verify the Kanban Swarm **before** dispatching work. If ephemeral delegation was already launched, report it as non-durable and create a real Kanban graph before claiming persistent tracking.

### Native Kanban Swarm versus Ralph-Kanban dispatch

Treat these as separate execution backends:

- A request for the **default/native Kanban Swarm** means `hermes kanban swarm` (or the equivalent native board API), not `ralph_kanban_dispatch`.
- `ralph_kanban_dispatch` is only for an approved, digest-frozen Ralph plan with a durable Ralph plan ID. A Markdown path alone is not dispatchable through that backend.
- If the user explicitly corrects this distinction, stop Ralph-dispatch attempts. Create the native Swarm and anchor the plan path and frozen goals on the root Blackboard.

Before creating a native swarm, inspect `hermes kanban swarm --help`: its worker grammar is `PROFILE:TITLE[:SKILL,SKILL]`. **Never put a colon in `TITLE`** unless intentionally starting the optional skills segment; shell quoting does not change this parser rule. Use em dashes, commas, or parentheses in worker titles instead.

After creation, capture and verify root, worker, verifier, and synthesizer IDs. A Swarm root can be immediately `done` by design while remaining the Blackboard; do not mistake that for workflow completion. Verify actual dispatch from child `show` output (`claimed`/`spawned`/heartbeat or terminal run) and board health. A manual `hermes kanban dispatch` result of `Spawned: 0` can coexist with already-running children when the gateway dispatcher claimed them concurrently; task/run state is authoritative.

### Runtime-context consistency

Before creating or reporting a Kanban ID from an agent shell, verify that the shell is using the same Hermes home/profile/board context the user will query. A sandboxed `HERMES_HOME` can create a valid-looking but invisible parallel board. Run the target-context equivalent of `hermes config path`, `hermes kanban boards list`, and `hermes kanban show <new-id> --json` before returning an ID. If the execution environment differs, invoke Kanban with the user's intended Hermes home/profile explicitly; do not report IDs from a temporary board.

## State and execution truth
Kanban state and `kanban_*` tools are authoritative. Save every task ID. After an event or session restart, reread the task, runs, summaries, metadata, and comments instead of relying on model memory.

Workers must:
- call `kanban_show()` first;
- call `kanban_heartbeat()` during long work;
- call `kanban_complete(summary, metadata)` on success;
- call `kanban_block(reason, kind)` when unable to continue.

## Acceptance
Use `kanban_check_acceptance` after a Worker reports completion. Do not accept a task only because its status is `done`. Verify summary, metadata, test evidence, changed files, and remaining risks. If acceptance fails, create a rework task describing the failed criterion; do not overwrite the original run evidence.

`kanban_check_acceptance` is a convenience heuristic, not a semantic gate. It can return `passed=true` for a blocked task when the criteria merely match a non-empty failure summary. Always read the authoritative `task.status`, latest `run.outcome`, structured `metadata.gate`, comments, and actual artifact/test evidence. A blocked run, missing gate packet, or `gate=fail` cannot become accepted because the helper returned true.

For Swarm graphs, separate model judgment from deterministic acceptance. A controller must enforce: complete topology, every Worker done with non-empty summary and JSON metadata, Verifier `metadata.gate == "pass"`, and Synthesizer outcome `completed` with non-empty summary and JSON metadata. If any hard condition fails, block or hold downstream work and emit a gate-failure event; never send a success notification based only on a model's claim.

## Failure decisions
- `transient`: bounded retry;
- `crashed`: inspect `runs` and the Worker log before retrying or reassigning;
- `timed_out`: reduce scope or adjust runtime, then retry within the limit;
- `capability`: reassign to a suitable Profile;
- `needs_input`: block and notify the user; do not auto-unblock;
- `gave_up` / `protocol_violation`: stop the loop, preserve evidence, and escalate.

Never retry indefinitely. Keep failure monitoring separate from automatic remediation so human-required failures are not silently unblocked.

### Recovery-controller exception
A durable **recovery-controller** is not an ordinary Worker or a read-only Ops observer. Its job is to resolve board anomalies that have a concrete, evidence-backed repair path. Do not let it self-block merely because one dependent task is blocked: record that anomaly on its own card, repair independent anomalies, and continue scanning. If it reaches a turn budget, persist a handoff and create/activate a successor controller rather than treating the controller's own block as the resolution.

The controller may safely repair a malformed task graph only after reading current task state, runs, logs, and dependency edges. Use this order: create a scoped replacement card; link the replacement as the downstream prerequisite; verify the new edge; then unlink the failed prerequisite. Preserve the failed task and its evidence. Do not use this exception to bypass genuine `needs_input`, security, base-drift, or exhausted semantic-review blocks.

### Dependency-edge capability check
Before escalating a graph repair as a missing `unlink`/edge-replacement capability, inspect the live CLI help for `hermes kanban unlink` in the target board context. A prior Worker report that only `link` is available is not authoritative. When `unlink parent_id child_id` exists and the replacement QA gate has independently passed, use the bounded safe sequence: link the replacement gate to **every** downstream child; read each child back and confirm both prerequisites; unlink the legacy parent from every child; read all affected children and the legacy card back; archive the superseded gate only after its child list is empty; append a structured root Blackboard recovery record; then run exactly one dispatcher pass. Never complete the legacy gate merely to release its children.

### Native Swarm worker-spec and completion-contract pitfalls
`hermes kanban swarm --worker` parses `PROFILE:TITLE[:SKILL,SKILL]`. A colon inside a human task title begins the optional skills segment and can silently turn title text into forced skill names, causing worker startup crashes. Keep worker titles colon-free; put detailed requirements in the root goal or task body. After creating a Swarm, inspect every worker's `show` output for the intended title and `skills` array before dispatching. If malformed, replace and rewire the card using the recovery-controller order above; do not retry the malformed card unchanged.

Before a large repository-backed fan-out, verify the installed completion transport with a one-route smoke. Some Native runtimes parse the Kanban completion `summary` itself as a strict `ULTRAWORK_REPORT_V1` JSON envelope while the generic Worker system prompt asks for a short human-readable summary and places machine facts in `metadata`. In that runtime, a normal-looking `done` task can fail closed and block the composite run because the completion hook forwards only `summary`. Freeze the exact report placement and bound identity in the root/Worker contract; do not assume `metadata` or a Blackboard comment reaches the runtime parser.

Repository-backed Native execution also needs an immutable clean candidate SHA. Obtain user authorization for isolated route-branch commits before selecting that backend, explicitly require the Worker to commit and report a clean status, and verify the worktree after completion. If commits are not authorized, choose a non-committing execution path rather than letting every route finish dirty and become non-integrable.

If one malformed completion blocks the run while sibling Workers still heartbeat, preserve them and their worktrees, record the transport mismatch, run one public reconcile pass, and avoid generic unblock or direct database edits. After all active Workers terminate, use a bounded replacement integration plus independent-QA path that resolves overlapping implementations and supplies the corrected report/commit contract. See `references/native-swarm-completion-contract.md` for the failure signature, prevention checklist, and recovery sequence.

### Shared-directory recovery when commits are not authorized

When useful Worker edits exist but Native integration is impossible because reports were malformed or worktrees are dirty and isolated commits were not authorized, do not keep retrying the same runtime contract. Preserve every Worker artifact, resolve overlapping diffs in a separate checkout, verify the integrated baseline, then switch to a **sequential shared-directory Dev → independent QA chain**. Allow only one writer at a time; each next Dev stage depends on the prior QA gate. Dev cards must complete normally with structured evidence and `Do not commit`; they must not self-block merely because review is required.

If a no-commit Dev still self-blocks only for review, do not invent an immutable SHA or mark the card done. Re-parent the independent verifier to a valid completed prior-stage/audit anchor first, verify both edges, unlink and archive the blocked handoff only after it has no children, and require the verifier to inspect the actual shared worktree. The exact sequence is in `references/sequential-shared-worktree-recovery.md`.

If a QA gate fails semantically, create a materially changed Dev rework plus fresh QA. Link and read back the replacement QA on every downstream child before unlinking the failed gate; archive the failed gate only after its child set is empty. Never let a lightweight acceptance helper's `passed=true` override a live `blocked` status, failed run outcome, or raw QA probe—the helper may only keyword-match criteria.

Monitoring is graph-versioned. A controller must watch the exact current chain IDs and stop on the first active block or final synthesis. After graph rewiring, terminate or supersede monitors that still reference removed/archived gates. A delayed notification from an old monitor is historical evidence, not a failure of the replacement chain; verify the monitor session ID and live dependency graph before reporting.

Detailed recovery recipe and pitfalls: `references/sequential-shared-worktree-recovery.md`.

### Controller scope and review-handoff recovery

A dispatcher-spawned Worker is task-scoped: it may report on sibling/child state but cannot safely complete, unblock, or promote another task. Do **not** make such a Worker the sole controller for a multi-stage graph; it can block on a cross-task mutation it cannot perform.

- Put the implementation → verifier → synthesizer dependencies directly in the board graph. The native dispatcher owns ordinary promotion.
- Reserve a root/controller Worker for observation or final synthesis, or run recovery from an external orchestrator/cron context with board-wide CLI authority.
- If the root controller is retained as part of the final Swarm topology, keep it pending behind the final child Synthesizer rather than running it concurrently with child stages.
- An implementation Worker that has finished work but needs review must **complete its own card** with structured evidence: `handoff_state="awaiting_review"`, branch, immutable commit SHA, exact test commands/results, changed files, and risks. `done` here means its handoff is complete—not that the feature is accepted, merged, or globally complete. The independent Verifier owns `gate=pass` or rework.
- Never use `kanban_block(reason="review-required: ...")` when a direct review/verify/QA child depends on the implementation card. Dependency promotion requires the parent to be `done` or `archived`; a sticky review block deadlocks that reviewer. Reserve `kanban_block` for genuine missing input, unavailable capability, or unresolved safety/semantic ambiguity.
- If a legacy implementation Worker incorrectly blocks itself solely for review despite a complete structured handoff and a direct independent Verifier child, an external recovery controller may normalize it to `done`, preserve the original block/comment evidence, append an explicit recovery audit entry, and dispatch the Verifier. Do not generic-`unblock` it: that can rerun already-completed work. Refuse normalization when the handoff lacks an immutable SHA or a reviewer dependency; create a bounded commit/rework card instead.
- For recurring long-running Swarms, use a bounded external recovery tick (for example, every five minutes) to run one dispatcher pass, inspect runs/logs/comments, repair only the safe state faults above, and leave semantic, authority, or exhausted-retry blocks intact.

### Global recovery-controller scope

Run **one generic controller per Kanban installation**, not one scheduled job per plan. On each tick, enumerate boards and inspect only active Swarm roots (`title` beginning `Swarm:` with `swarm_state=running`) plus their reachable task graphs; leave standalone cards and completed/archived Swarms untouched.

For each eligible blocked task, first read the task, run, log, comments, and dependency edges:

1. Normalize a `review-required` block to a completed handoff only when a non-empty evidence packet, immutable commit SHA, raw verification evidence, and direct independent QA/reviewer child exist. Complete with `handoff_state=awaiting_review`; never generic-unblock, which can replay completed work.
2. For a real Functional/CTO `gate: fail`, create exactly one bounded Dev rework with the failed criterion and a materially changed strategy, then independent Functional QA and CTO QA. Link the replacement QA chain to every downstream gate **before** unlinking the failed prerequisite; preserve passed criteria as regressions and archive the superseded failed card only after reading replacement edges back.
3. Keep authority/security/credential ambiguity, missing immutable evidence, base drift/conflicts, absent changed strategy, and exhausted retries blocked. Append the exact required human input to the Swarm root Blackboard.

### Bounded graph traversal and rework wiring

Native CLI `list` output alone is not a dependency graph. For a generic cron pass, first enumerate active roots on every board, then traverse each root with repeated `show --json`, following its `children` set with a visited-ID set and an explicit node cap. Treat the current `task.status` as authoritative: an archived card whose final run says `blocked` is preserved evidence, not an active blocked task requiring another repair.

For an eligible QA gate failure, do not stop after creating a Dev rework. In one bounded recovery transaction, construct and verify the complete chain:

1. Create the Dev rework containing the exact failed criterion, immutable candidate/base evidence, and the materially changed strategy. Keep its source evidence in the body/comment; **do not make the superseded failed gate its parent** when the legacy gate is to be archived, because that leaves the legacy card with a child.
2. Create an independent Functional-QA child of that Dev card, explicitly requiring the prior passed criteria as regressions and structured `metadata.gate` evidence.
3. Create an independent CTO-QA child of Functional QA with the same immutable-SHA and regression requirements.
4. If a downstream task is actively retrying a semantically failed gate because queue dependencies see only `status=done`, first contain the loop with an explicit hold/block and preserve the repeated run evidence. Do not let a generic dispatcher repeatedly respawn a no-op dependency-wait worker while rewiring.
5. Link the replacement CTO-QA card to **every** downstream gate still parented by the failed QA; read each downstream card back to verify the new parent edge.
6. Only then unlink the failed QA edges, re-read the affected downstream parents and the legacy gate, archive the superseded QA only after its child list is empty, and record the chain IDs plus edge evidence on the active root Blackboard.

A `task.status=running` does not prove useful progress: inspect its latest run outcome, recent `dependency_wait` events, and gate metadata. A terminal QA `metadata.gate=fail` can require recovery even though its queue status is `done`; downstream cards may otherwise be promoted because native dependency scheduling does not interpret gate metadata. Do not archive a failed gate merely because a Dev replacement has started: missing Functional/CTO descendants leaves an unverified path and can silently bypass the gate. After any mutation, run exactly one dispatcher pass and read the new chain plus every rewired downstream card back. Never infer a plan-specific recovery policy from a job name or hard-code a root ID into the controller.

### Recovered terminal gate and fresh semantic review

When a failed **terminal** QA gate was already consumed by a completed semantic/global review with `verdict=rework`, a passing replacement CTO gate does not retroactively turn that historical review into a pass. Preserve the historical review and create a **fresh independent semantic review** instead.

1. Require a valid replacement Dev → Functional QA → CTO QA chain, with both fresh QA runs carrying `metadata.gate="pass"` on the same immutable candidate SHA.
2. Create the fresh semantic-review card with two parents: the active Swarm root (so graph traversal and Blackboard ownership remain intact) and the replacement CTO gate. Use an idempotency key keyed by the recovery lineage/candidate SHA.
3. Link that fresh review to the contained terminal verifier before dispatching. Read the verifier back and confirm it temporarily has both the historical review and fresh review as parents. Keep the legacy edge and verifier block until the fresh review produces a durable `verdict=pass` packet; do not generic-unblock it.
4. If the original recovery-controller's stated scope ends at producing the replacement QA chain, complete its own card with `handoff_state="awaiting_global_semantic_review"`, SHA/gate/test evidence, and residual risks. Do not leave it indefinitely `running` merely to await an independent review.
5. After a fresh semantic pass, link/read-back the replacement review on every downstream gate, unlink the historical failed-review edge, then re-read all affected cards. If the contained terminal verifier remains `blocked` from the superseded semantic failure, it is sticky: do **not** generic-unblock or reuse it. Create a fresh independent verifier with the completed non-semantic prerequisites plus the replacement review; link it to the synthesizer, read back the synthesizer with both old and new verifier parents, unlink the legacy verifier, re-read both cards, then archive the legacy verifier only after its child list is empty. The new verifier must independently emit structured `metadata.gate=pass` before synthesis may start.

A `dispatch` result of `spawned: []` is expected when the Gateway already claimed the fresh review or replacement verifier. Its live `show`/run state—not the dispatch count—is the completion evidence.

### Concurrent dispatcher reconciliation

A Gateway dispatcher or another controller can claim, normalize, complete, or promote a card between a recovery controller's inspection and verification. Post-mutation `show` output is authoritative even when it contradicts a just-written Blackboard comment. Before reporting, reread every changed card and its immediate edges. If another actor validly normalizes a review handoff or claims a replacement QA card, append a concise correction to the root Blackboard with the observed state and attribution when available; do not repeat the normalization or dispatch pass. Never leave a root comment claiming a task is blocked or held after live state proves it is done or running.

### Semantic-gate retry containment

A failed QA gate is not necessarily represented by the current task status or last-run metadata: it may be preserved in a prior blocked run and a detailed task comment while native dependency handling has already promoted and re-claimed the same QA card. Treat a `dependency_wait` retry after a semantic `gate: fail` as a loop hazard, not a transient retry.

1. Read the task's runs, comments, and downstream children; extract the immutable SHA, failed criterion, passed regressions, and materially changed strategy from the durable evidence packet.
2. Explicitly hold/block the live legacy QA card to stop another re-claim, then immediately reread it. Blocking a running card can race with its active worker; the post-block run/status is authoritative.
3. Create the complete replacement Dev → Functional QA → CTO QA chain with idempotency keys. The replacement Dev card must not use the legacy failed gate as a parent when that gate will later be archived.
4. Link the replacement CTO gate to every downstream child, read back the child with both old and new parents, unlink the legacy edge, then reread the child and legacy card. Archive the legacy gate only after its child list is empty.
5. Append one concise root Blackboard record containing failure evidence, containment, all replacement IDs, edge read-back, and forbidden operations. Run exactly one dispatcher pass; `spawned: []` is valid when the Gateway concurrently claimed the newly-ready Dev card—verify the actual task run instead of retrying dispatch.

### Worker provider quota failure — fleet reroute

When every spawned worker crashes instantly, read one worker log under `$HERMES_HOME/kanban/logs/<task>.log` first: an HTTP 403/quota error on the profile's provider is an infrastructure fault, not a task fault. Recover with task-level overrides, never profile config edits unless the user asks:

1. Probe candidate providers with a direct minimal API call (both `/chat/completions` and `/responses` for codex-style providers) before rerouting.
2. `hermes kanban set-model <task_id> <model> --provider <provider>` on every card of the graph (workers, verifier, synthesizer), then `hermes kanban unblock <id> --reason ...` for auto-blocked cards, then one `hermes kanban dispatch` pass.
3. A stop-condition watcher that exits on `blocked` can exit during the crash window before the reroute lands — restart it after the reroute completes.

With `dispatch_in_gateway: true` but no gateway process running, nothing spawns: run `hermes kanban dispatch` manually per promotion (or via a bounded polling loop). A dispatch result of `Spawned: 0` while a card is already `running` is normal.

### Root completion readback

After `hermes kanban complete <root>` finish by reading the root back (`show --json`): confirm `status=done` and the acceptance summary/metadata are stored; declared totals in the summary must match the raw run evidence.

## Notification contract
When a task is created from a Gateway session, preserve the creator's exact routing descriptor: platform, chat ID, chat type, thread ID, user ID, notifier profile, and resolved session key. Read these through `gateway.session_context.get_session_env(...)` first; plain `os.environ` is only a fallback because Gateway context is carried by ContextVars. Never infer `chat_type` from a thread or platform, and never default a new subscription to `group`. Persist `chat_type`, `session_key`, and `notifier_profile` with the subscription. For Feishu, preserve inbound `chat_type` and `user_id`; if a group/forum task must notify privately, use the creator's `user_id` rather than the group `chat_id`; DM-origin tasks keep their DM chat ID.

Separate delivery backends. Gateway rows use `delivery_kind="gateway"` and are handled by the Gateway notifier. Local CLI is not a fake DM/group: it has no Gateway adapter. For local CLI use `hermes kanban watch --task <root_id>` / `tail` over persisted `task_events`, or mark an explicitly local subscription `delivery_kind="cli"` and make the Gateway notifier skip it. Non-interactive CLI, cron, and JSON/scripted creation cannot promise continued stdout or chat delivery; return the root ID plus a reproducible watch/show command. For wake-up, use the persisted session descriptor and session key; only reconstruct keys for legacy rows.

Notify lifecycle milestones (`created`, `decomposed`, Worker start/completion, verifier start/gate result, synthesizer start, final success/failure/block). Aggregate heartbeats rather than sending every heartbeat. Verify notification in layers: exact subscription fields, event row, cursor advancement, Gateway adapter/profile selection, wake-up session key, Gateway log, and actual target chat. A local cron job with `deliver: local` proves only that the script ran, not chat delivery. If a Gateway source change is made, restart Gateway from an external shell—never from inside its own process.

Use `kanban_board_health` or `hermes kanban stats --json` before large fan-out and after failures. Inspect stale running tasks, blocked tasks, and failure events; do not edit the SQLite database directly.

Failure events may be monitored by a local cron script every five minutes. Local cron delivery is not the same as Gateway delivery: use an explicit Gateway platform target when alerts must reach Telegram, Discord, or Slack.

## Profile and skill readiness
Before dispatching a task with `--skill NAME`, verify that NAME exists in the target assignee's profile-local skills directory, not only in the active/global profile. A missing profile-local skill causes the Worker to exit during startup with `Unknown skill(s)` while the Dispatcher records only `crashed`. After adding or editing a skill, sync it to every target Profile and run a minimal Worker smoke test: `kanban_show` → `kanban_heartbeat` → `kanban_complete`.

## Layered implementation
Prefer native Kanban tools and this skill first. Add a small user plugin only for durable gaps such as acceptance checks, strategy templates, or Board health; do not modify Hermes core for these. Plugin handlers must return JSON strings and catch exceptions.

## Verification sequence
Test the smallest closed loop before testing decomposition:
1. direct Worker startup with the requested Skill;
2. state, heartbeat, and structured completion;
3. one parent-child dependency;
4. Orchestrator acceptance;
5. original-chat notification.

For complex task-graph or Swarm tests, use a real fan-out/fan-in graph rather than independent cards: create a root, at least two parallel workers, a verifier depending on every worker, and a synthesizer depending on the verifier. Before dispatch, record the returned root/worker/verifier/synthesizer IDs and run a health baseline. Dispatch, then verify each dependency transition with `kanban_show`, `kanban_runs`, and `kanban_board_health`; do not assume creation means execution. If an assigned profile is a terminal/non-spawnable lane, do not treat the skipped spawn as a system failure: preserve the skipped-spawn evidence, reassign to a spawn-capable profile with a recorded reason, and dispatch again. The `swarm` command accepts topology-level options only; apply per-task runtime/retry settings when creating individual cards, not by passing unsupported per-task flags to `swarm`. Acceptance must inspect every worker's non-empty summary/structured metadata, the verifier's structured metadata (especially `gate=pass`), and the synthesizer's final handoff, not merely task status. If the verifier reports `needs_input` because notification evidence is missing, preserve the worker evidence, leave the synthesizer held by dependency, and report a partial/blocked result rather than claiming success. Run the deterministic Swarm controller on a schedule (for example every five minutes) and emit root-level progress/gate/completion events so the creator subscription receives workflow updates. Keep the root Blackboard distinct from workflow completion if the root is marked done immediately by the topology helper.

For notification tests, verify the layers separately and capture them before cleanup: (a) create or inspect a subscription targeting the intended platform/chat/thread/profile; (b) confirm a terminal task event exists; (c) inspect `notify-list`/SQLite to confirm the subscription cursor advances to the terminal event; (d) inspect the Gateway log for notifier delivery or send-failure evidence; and (e) verify the actual target chat received the message. A completed task alone does not prove notification delivery. The notifier may automatically remove a subscription after a task reaches `done`, so a later `notify-list` showing no row is expected only after you have recorded the advanced cursor and delivery evidence. The CLI `notify-subscribe` command alone proves registration, not delivery. If the task completes but the cursor remains `0`/unchanged, inspect whether the dispatch-owning Gateway has the notifier watcher running and restart the Gateway from an external shell; a Gateway process must not restart itself from inside its own process.

Use `--max-retries 2` or higher during diagnostics. `--max-retries 1` converts a single startup fault into immediate `gave_up`, hiding retry behavior. Archive failed diagnostic cards after preserving their run evidence.

## Root completion
Complete the root only when all required children are done, acceptance criteria pass, tests/evidence are recorded, and no required task remains triage, todo, ready, running, or blocked. The final summary must include completed work, child results, verification evidence, unresolved risks, and next steps.

### Separate queue status from composite workflow state
A Swarm root is a dependency anchor and shared Blackboard, not an ordinary worker card. Do not use `tasks.status=done` as proof that the whole Swarm finished if the topology helper completes the root immediately. Composite workflows must expose a separate workflow-level state (for example `swarm_state=running|completed|blocked`) while preserving queue status for dependency compatibility. Set the state to `running` at topology creation, `completed` only after every Worker handoff is valid, the Verifier has `metadata.gate=pass`, and the Synthesizer has a valid terminal handoff, and `blocked` on a hard gate/failure. CLI, tool, dashboard, notifier, and controller outputs should surface both fields. Tests must assert both: root queue status remains compatible with dependency scheduling, while workflow state tracks actual Swarm completion.

A standalone recovery chain can validly finish the implementation, replacement Global QA, Synthesizer, and root queue card while the original Native runtime remains historically blocked and `swarm_state` stays stale at `running`. If the public CLI exposes no composite-state repair command, do not mutate the Kanban database directly. Append a root audit comment, report **recovered delivery accepted** separately from **Native composite runtime state**, and preserve the stale field as transport/runtime evidence. Never claim the original Native runtime completed merely because the recovery chain did.

Before user-facing completion, the orchestrator—not only a Worker—must independently read the final QA and Synthesizer packets and perform one sufficient direct verification against the integrated artifact (for example the full relevant test suite plus smoke/artifact inspection). Record that evidence on the root before presenting the final result.

See `references/sequential-shared-worktree-recovery.md` for stale composite-state handling after a non-committing recovery.

### Final-result handoff is mandatory
A completed Swarm is not user-facing completion until the Synthesizer's actual deliverable has been read and surfaced. The root card's initial `latest_summary` may remain the topology placeholder (`Swarm topology planned`) even after `swarm_completed`; do not report that placeholder as the result. After the Verifier and Synthesizer finish, read the root with full comments/events and read the Synthesizer task/runs. Extract the `[swarm:synthesis]` blackboard entry or Synthesizer summary, then present the substantive conclusion directly in chat, along with the root ID and a reproducible lookup command. If the Synthesizer claims it wrote to the blackboard but no handoff is present, treat delivery as incomplete and investigate before claiming success.

### Assignment changes must be followed through
If a user reassigns a Swarm role after creation, verify the reassigned card with `show` and then re-check the full dependency graph. Do not assume the change has executed the task; dispatch/claim evidence and terminal run output still determine completion.

### Completion-summary delivery invariant
The terminal `swarm_completed` event must carry the Synthesizer's actual summary in a bounded payload field such as `synthesis_summary`. The Gateway notifier must render that field in the creator-facing completion message; a generic `Swarm completed` status is not a valid final handoff for newly generated events. Preserve a generic fallback for legacy events that lack the field. Add a notifier regression test that creates a root subscription, emits `swarm_completed` with a known summary, runs one notifier tick, and asserts the delivered text contains that summary. Verify the controller, notifier, and test together before claiming the bug fixed.

See `references/health-check.md`, `references/strategy-templates.md`, and `references/swarm-protocol.md` for reusable checks, task policies, deterministic Swarm gates, and creator-notification rules.
