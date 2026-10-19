---
name: hermes-kanban-orchestration
description: "Design and configure Hermes Kanban workflows where an orchestrator AI creates, monitors, validates, and recovers durable tasks across Worker Profiles."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [hermes, kanban, orchestration, dispatcher, task-lifecycle, notifications, plugins, profiles]
---

# Hermes Kanban Orchestration

Use this skill when configuring Hermes for durable task management, multi-profile execution, automatic status awareness, retries, blocking, result validation, or task notifications.

## Core architecture

Keep responsibilities separate:

- **Kanban** is the durable source of truth: task status, dependencies, comments, runs, summaries, and metadata.
- **Dispatcher** claims ready tasks, starts Workers, handles heartbeats, stale claims, crashes, timeouts, retries, and circuit breaking.
- **Orchestrator Profile** creates and decomposes work, reads child results, validates acceptance criteria, and decides the next transition.
- **Worker Profiles** execute concrete work and must end with `kanban_complete` or `kanban_block`.
- **Skills** provide process rules and domain knowledge; they do not replace durable state.
- **Plugins/tools** expose missing queries, validators, escalation actions, or integrations.
- **Gateway/notifications** deliver terminal events to users or the originating conversation.

Do not make the creator AI rely on model memory or a one-time `create` call. For long-lived workflows, make it a persistent Orchestrator task or ensure the originating session is event-subscribed and can resume.

## Configuration workflow

1. Inspect the live CLI and official docs before assuming command or config names.
2. Create explicit Profiles with descriptions that state capabilities, not just role names.
3. Configure the gateway-embedded dispatcher:

```yaml
kanban:
  dispatch_in_gateway: true
  dispatch_interval_seconds: 60
  auto_decompose: true
  auto_decompose_per_tick: 3
  orchestrator_profile: orchestrator
  default_assignee: developer
  failure_limit: 2
  auto_subscribe_on_create: true
```

4. Restart the gateway after config/plugin changes.
5. Create a dedicated `kanban-orchestrator` Skill for lifecycle rules and acceptance criteria.
6. Enable only trusted custom plugins; prefer plugins over editing Hermes core.
7. Run a small end-to-end test and inspect events, runs, summaries, and notifications.

Use the `references/configuration-and-workflows.md` reference for the detailed setup matrix and verification recipe.

## Profile design

Create an Orchestrator Profile with a description such as:

> Responsible for task decomposition, dependency tracking, result acceptance, retry/block decisions, and user escalation; does not perform ordinary implementation work.

Create Worker Profiles with capability descriptions, for example:

- `developer`: implements code, runs tests, reports changed files and risks.
- `reviewer`: validates results, checks tests, identifies residual risks.
- `researcher`: gathers evidence and records sources.

The decomposer uses Profile descriptions for routing. Unknown assignments need a safe `default_assignee`; never allow a child task to land without an assignee.

## Task lifecycle

### Create

Capture title, body, acceptance criteria, assignee, priority, workspace, runtime limit, retry limit, and parent dependencies. Use `--idempotency-key` for webhook or repeated automation input.

Use `--triage` for ambiguous work. Use explicit parent links for deterministic pipelines. Use `--goal` only for open-ended tasks that need multiple turns; still enforce a runtime and turn budget.

### Decompose

Split complex work into independently verifiable stages. Use parent-child links so downstream tasks remain `todo` until prerequisites complete. Parallelize only independent tasks.

### Execute

A Worker should:

1. Call `kanban_show` first.
2. Read parent handoffs and prior attempts.
3. Perform the work using its normal tools.
4. Call `kanban_heartbeat` during long operations.
5. Record durable comments for important intermediate decisions.
6. Call `kanban_complete(summary=..., metadata=...)` on success, or `kanban_block(reason=..., kind=...)` when it cannot continue.

Require structured completion metadata, preferably including `changed_files`, `tests_run`, `tests_passed`, `tests_failed`, and `remaining_risks`.

### Observe and decide

After `completed`, `blocked`, `crashed`, `timed_out`, `gave_up`, or `protocol_violation`, re-read the task and its latest run. Never infer current state from an old event or cached conversation.

For successful children, validate acceptance criteria before unlocking follow-up work. A `done` status alone is not sufficient evidence. If the result is incomplete, create a focused rework task instead of silently marking the parent complete.

### Recover

Classify failures before acting:

- `dependency`: wait; allow dependency promotion.
- `transient`: bounded retry.
- `needs_input`: block and notify the user.
- `capability`: reassign to a capable Profile.
- `crashed`: inspect run/log; retry only within the limit.
- `timed_out`: reduce scope or adjust the runtime cap.
- `gave_up`: stop automatic retries and escalate.
- `protocol_violation`: treat as failure because the Worker exited without a lifecycle call.

Never automatically unblock every blocked task. Repeated same-kind blocking must escalate to triage or a human to prevent loops.

### Recover review handoffs and QA failures

Use exactly one board-wide Recovery Controller for all active Swarm roots. Do not create one controller or cron job per plan. On each pass, discover active roots across boards, inspect the live task/run/comment evidence, and make at most one bounded recovery decision per failed route. Use `references/recovery-controller.md` for the evidence packet, decision table, safe edge-replacement sequence, and dedupe key.

1. **Review handoff, not a failure:** when a Dev task has a direct independent QA child and its latest durable comment/run records an immutable SHA, clean status, raw test evidence, changed files, and risks, treat `review-required` as a malformed handoff. Call `kanban_complete` with normalized `handoff_state=awaiting_review` metadata, then dispatch. Do not generic-unblock it.
2. **Real QA gate failure:** preserve the failed criterion and evidence, then create exactly one new chain: Dev rework → independent Functional QA → CTO QA. The rework must use a materially changed strategy and retain previously passed criteria as regressions.
3. **Dependency rewiring:** before removing an obsolete parent, link the replacement parent, read every downstream task back, unlink the obsolete edge, and read back again. A controller may use the trusted `hermes kanban link` / `unlink` CLI when a task-scoped Worker lacks one of those tools. Never edit the board SQLite database directly.
4. **Duplicate prevention:** derive a deterministic idempotency key from the failed route, failing SHA, failed criterion, and recovery strategy. Before creating a rework chain, search for an active equivalent. If a concurrent duplicate already exists, archive the duplicate subtree first, then archive the blocked duplicate parent while retaining comments and run history.
5. **Worktree routing guard:** before editing, verify that the assigned worktree is clean, on the expected branch, descended from the required immutable base, and contains the named target files. A wrong-base worktree is routing evidence, not permission to reset or modify it; stop that duplicate and let the valid chain continue.
6. **Integration conflict:** only resolve a branch conflict automatically after explicit user authorization. Resolve inside the isolated integration worktree, preserve the independently accepted semantics from each route, run focused cross-route tests plus the full suite, create an immutable integration commit, and record its SHA before releasing downstream work.

### Complete and archive

Complete the root task only when required children are done, acceptance criteria pass, tests are evidenced, and no unresolved blocking task remains. Archive rather than hard-delete when audit history matters; garbage-collect old workspaces/logs separately.

## Creator-AI awareness

Use one of two patterns:

1. **Originating-session pattern**: enable `auto_subscribe_on_create`; the originating Gateway/TUI channel receives terminal events. On each event, the AI must re-read task state and continue with an explicit decision.
2. **Persistent Orchestrator pattern**: assign a root task to the Orchestrator Profile, which creates children, waits for event/state changes, validates handoffs, and completes or blocks the root task. This is preferred for multi-stage or restart-resistant workflows.

Notifications alone are not orchestration. A Telegram/Discord message proves delivery, not that the creator AI resumed its decision loop.

## Extension strategy

Add a user plugin under `~/.hermes/plugins/<name>/` rather than modifying core. Prioritize small tools that close a real gap:

- `kanban_get_children`: summarize child statuses and latest handoffs.
- `kanban_check_acceptance`: compare structured evidence against criteria.
- `kanban_escalate`: comment, block, and route a human alert atomically.

Plugin handlers must accept `(args, **kwargs)` and always return a JSON string, including errors. Tool schemas must say when the model should use the tool. Enable trusted plugins explicitly and restart Hermes/Gateway.

### Toolset identity migration

A plugin name, its toolset name, and its individual tool names are separate contracts. If Desktop lists an obsolete toolset, first inspect every registration in the plugin and the live `/api/tools/toolsets` handler output. Do **not** delete working tool implementations merely to remove an obsolete toolset row. Instead, migrate every affected registration to the intended surviving toolset, preserve the handlers/schemas/tests and manifest metadata, migrate the relevant `platform_toolsets` / `known_plugin_toolsets` configuration names, then restart the process that actually owns the Desktop HTTP port. Dashboard and Gateway are separate processes; restarting Gateway alone does not refresh a Dashboard-owned registry. Do not edit a Kanban SQLite database for toolset display state: that endpoint is derived from configuration plus the in-memory plugin registry.

Use Gateway hooks for logging, external alerts, or startup checks; do not assume ordinary Gateway hook events are equivalent to Kanban task events. For task terminal notifications use Kanban subscriptions/watch or a supported event bridge.

### Legacy controller → shared-runtime state migration

When a plugin replaces a legacy controller state database with projections in a shared Kanban runtime, implement the adapter in plugin source rather than modifying core. Make it a one-way, explicit operation unless the deployment contract already provides a safe startup migration hook.

1. Read the legacy SQLite database read-only and accept only terminal runs.
2. Before writing destination schema/data, create a non-overwriting backup beside the legacy DB.
3. Refuse every active or mutating related record: not only runs and attempts, but child work, Ops operations/authorizations, worktree cleanup, pending QA, and non-passive route state.
4. Leave the old database untouched and retain it as the detailed audit/readability source; import only the run/route/attempt/event projection needed by shared runtime status APIs.
5. Record an explicit destination-side migration ledger keyed by stable legacy DB identity plus legacy run ID. Do not rely on an active-run uniqueness index to prevent duplicate terminal imports.
6. Prove the safety boundary with focused tests: terminal import creates a backup, leaves source bytes unchanged, is idempotent, and is visible through a real shared-runtime status/read function; active state fails before either a backup or destination runtime write occurs.

## Verification checklist

- `hermes profile describe` shows capability descriptions.
- `hermes gateway status` shows the gateway running.
- `hermes tools list` exposes required toolsets.
- `hermes plugins list` shows trusted plugins enabled.
- A test task reaches `ready`, is spawned, and produces a run.
- Worker calls `kanban_show` and ends with `kanban_complete` or `kanban_block`.
- Long work emits heartbeats.
- A forced transient failure retries only within the configured limit.
- A needs-input block notifies and remains blocked.
- Completion metadata is visible through `show`/`runs` and downstream context.
- The originating subscriber or configured notifier receives terminal events.

## Pitfalls

- In `hermes kanban swarm --worker`, the field grammar is `PROFILE:TITLE[:SKILL,SKILL]`. Do not put an additional colon in the title/instruction text: everything after the second colon is parsed as forced skill names, causing deterministic `Unknown skill(s)` worker crashes. Put detailed instructions in a separately created task body, or use only one profile/title colon in Swarm worker entries.
- Do not confuse `delegate_task` with durable Kanban orchestration.
- Do not run the deprecated standalone daemon alongside the gateway dispatcher; claim races can occur.
- Do not use a shared SQLite board across hosts; the model is host-local and crash detection depends on local PIDs.
- Do not let Workers exit successfully without a lifecycle tool call.
- Do not add many tools before proving the native Kanban loop.
- Do not claim automatic creator-AI awareness solely because notifications are enabled.

For the detailed session-derived setup, configuration examples, and test matrix, see `references/configuration-and-workflows.md`.
