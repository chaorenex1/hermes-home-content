# Hermes Kanban platform operations

Operations layer for running Hermes Kanban as the durable execution backend. The orchestration contracts live in SKILL.md; blocked-work decisions live in `references/kanban-recovery-controller.md`.

## Responsibility split

- **Kanban** is the durable source of truth: status, dependencies, comments, runs, summaries, metadata.
- **Dispatcher** claims ready tasks, starts Workers, handles heartbeats, stale claims, crashes, timeouts, retries, and circuit breaking.
- **Orchestrator Profile** decomposes work, reads child results, validates acceptance criteria, and decides transitions; it does not do ordinary implementation work.
- **Worker Profiles** execute concrete work and must end with `kanban_complete` or `kanban_block`.
- **Skills** carry process rules and domain knowledge; they never replace durable state.
- **Plugins/tools** expose missing queries, validators, escalation actions, or integrations.
- **Gateway/notifications** deliver terminal events. Delivery is not orchestration.

Never rely on model memory or a one-time `create` call. For long-lived workflows use a persistent Orchestrator task, or an event-subscribed originating session that can resume.

## Configuration baseline

Inspect the live CLI and official docs before assuming command or config names; verify flags with `hermes kanban <verb> --help`.

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

Create explicit Profiles whose descriptions state capabilities, not role names (`developer`: implements code, runs tests, reports changed files and risks; `reviewer`: validates results and residual risks; `researcher`: gathers evidence and records sources). The decomposer routes on those descriptions, so always configure a safe `default_assignee`; a child must never land without one.

Useful verbs: `init`, `create`, `list`, `show`, `assign`/`reassign`, `comment`, `complete`, `block`/`unblock`, `archive`, `tail`, `runs`, `watch`, `stats --json`, `notify-subscribe`/`notify-list`, `dispatch --dry-run --json`, plus `link`/`unlink` for dependencies. Merge configuration instead of overwriting it, then restart the Gateway and verify status.

## Task lifecycle

### Create

Capture title, body, acceptance criteria, assignee, priority, workspace, runtime limit, retry limit, and parent dependencies. Use `--idempotency-key` for webhook or repeated automation input; `--triage` for ambiguous work; explicit parent links for deterministic pipelines; `--goal` only for open-ended multi-turn work, and still enforce runtime and turn budgets.

### Decompose

Split work into independently verifiable stages and use parent-child links so downstream tasks stay `todo` until prerequisites complete. Parallelize only independent tasks.

### Execute

A Worker calls `kanban_show` first, reads parent handoffs and prior attempts, performs the work with normal tools, emits `kanban_heartbeat` during long operations, records durable comments for material intermediate decisions, and ends with `kanban_complete(summary=..., metadata=...)` or `kanban_block(reason=..., kind=...)`. Completion metadata should carry `changed_files`, `tests_run`, `tests_passed`, `tests_failed`, and `remaining_risks` — downstream QA and synthesis read it.

### Observe and decide

After `completed`, `blocked`, `crashed`, `timed_out`, `gave_up`, or `protocol_violation`, re-read the task and its latest run. Never infer state from an old event or cached conversation. For successful children, validate acceptance criteria before unlocking follow-up work: `done` is not acceptance. Incomplete results get a focused rework task, not a silently completed parent.

### Recover

| Evidence | Action |
|---|---|
| `dependency` | wait; allow dependency promotion |
| `transient` | bounded retry |
| `needs_input` | block and notify the user |
| `capability` | reassign to a capable Profile |
| `crashed` | inspect run/log; retry only within the limit |
| `timed_out` | reduce scope or adjust the runtime cap |
| `gave_up` | stop automatic retries and escalate |
| `protocol_violation` | treat as failure — the Worker exited without a lifecycle call |

Never auto-unblock every blocked task. Repeated same-kind blocking must escalate to triage or a human to prevent loops.

**Review handoff is not a failure.** When a Dev task has a direct independent QA child and its latest durable comment/run carries an immutable SHA, clean status, raw test evidence, changed files, and risks, treat `review-required` as a malformed handoff: call `kanban_complete` with normalized `handoff_state=awaiting_review` metadata and dispatch QA — do not generic-unblock it.

**Real QA gate failure** preserves the failed criterion and evidence, then creates exactly one new chain: Dev rework → independent Functional QA → CTO QA. The rework uses a materially changed strategy and retains previously passed criteria as regressions.

**Dependency rewiring:** link the replacement parent, read every downstream task back, unlink the obsolete edge, read back again. A controller may use the trusted `hermes kanban link`/`unlink` CLI when a task-scoped Worker lacks those tools. Never edit the board SQLite database directly.

**Duplicate prevention:** derive a deterministic idempotency key from failed route, failing SHA, failed criterion, and recovery strategy. Search for an active equivalent before creating; if a concurrent duplicate exists, archive the duplicate subtree first, then the blocked duplicate parent, retaining comments and run history. Before editing, verify the assigned worktree is clean, on the expected branch, descended from the required base, and contains the named files — a wrong-base worktree is routing evidence, not permission to reset it.

**Integration conflicts** are resolved automatically only after explicit user authorization, inside the isolated integration worktree, preserving each route's accepted semantics and recording an immutable integration commit before releasing downstream work.

### Complete and archive

Complete the root only when required children are done, acceptance criteria pass, tests are evidenced, and no unresolved blocking task remains. Archive rather than hard-delete when audit history matters; garbage-collect workspaces/logs separately.

## Creator-AI awareness

Use one of two patterns:

1. **Originating-session:** `auto_subscribe_on_create`; the originating Gateway/TUI channel receives terminal events and the AI re-reads task state before each decision.
2. **Persistent Orchestrator:** a root task assigned to the Orchestrator Profile creates children, waits for state changes, validates handoffs, and completes or blocks the root. Preferred for multi-stage or restart-resistant workflows.

A notification proves delivery, not that the creator AI resumed its decision loop.

## Extension strategy

Add a user plugin under `~/.hermes/plugins/<name>/` rather than modifying core. Small tools that close real gaps: `kanban_get_children`, `kanban_check_acceptance`, `kanban_escalate`. Handlers must accept `(args, **kwargs)` and always return a JSON string, including errors; schemas must say when to use the tool. Enable trusted plugins explicitly and restart Hermes/Gateway.

**Toolset identity migration:** a plugin name, toolset name, and tool names are separate contracts. Inspect every registration and the live `/api/tools/toolsets` output before deleting anything to remove an obsolete toolset row. Migrate registrations to the surviving toolset, migrate `platform_toolsets`/`known_plugin_toolsets`, then restart the process that owns the Desktop HTTP port — Dashboard and Gateway are separate; restarting Gateway alone does not refresh a Dashboard-owned registry. Never edit the Kanban SQLite database for display state.

**Legacy controller → shared runtime:** keep the adapter in plugin source. Read the legacy DB read-only, accept only terminal runs, back up beside it before writing, refuse active/mutating records (runs, attempts, child work, Ops authorizations, worktree cleanup, pending QA, non-passive routes), leave the old DB untouched, import only the run/route/attempt/event projection, and record a destination-side ledger keyed by legacy DB identity + run ID. Test terminal import, source-byte immutability, idempotency, and rejection of active state.

## Verification checklist

- [ ] `hermes profile describe` shows capability descriptions.
- [ ] `hermes gateway status` shows the Gateway running.
- [ ] `hermes tools list` exposes the required toolsets.
- [ ] `hermes plugins list` shows trusted plugins enabled.
- [ ] A test task reaches `ready`, spawns, and produces a run.
- [ ] The Worker calls `kanban_show` and ends with `kanban_complete` or `kanban_block`.
- [ ] Long work emits heartbeats; a forced transient failure retries only within the limit.
- [ ] A needs-input block notifies and stays blocked.
- [ ] Completion metadata is visible through `show`/`runs` and downstream context.
- [ ] The originating subscriber or configured notifier receives terminal events.

## Pitfalls

- In `hermes kanban swarm --worker`, the grammar is `PROFILE:TITLE[:SKILL,SKILL]`. An extra colon in the title makes everything after it parse as skill names, causing deterministic `Unknown skill(s)` worker crashes. Put detail in a separately created task body, or keep a single colon.
- `delegate_task` is not durable Kanban orchestration.
- Do not run the deprecated standalone daemon alongside the Gateway dispatcher; claim races follow.
- Do not share one SQLite board across hosts; crash detection depends on local PIDs.
- Do not let Workers exit successfully without a lifecycle tool call.
- Do not add many tools before proving the native loop.
- Do not claim creator-AI awareness just because notifications are enabled.
