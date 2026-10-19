# Durable & Background Systems

Four systems run alongside the main conversation loop. Quick reference
here; full developer notes live in `AGENTS.md`, user-facing docs under
`website/docs/user-guide/features/`.

### Delegation (`delegate_task`)

Spawn a subagent with an isolated context + terminal session. Only the
child's final summary enters the parent's context.

- **Single / batch:** `delegate_task(goal, context)` or
  `delegate_task(tasks=[...])`; batch children run in parallel, capped by
  `delegation.max_concurrent_children` (default 3), results ordered by
  task index. Over the cap is a tool error, never silent truncation.
- **Background by default:** a top-level call returns a handle at once and
  the result re-enters the conversation as a new turn; an orchestrator
  child instead waits inside its own turn to synthesize. `/stop` or
  closing the owning session cancels children; an ordinary follow-up
  message does not.
- **Context:** children get only `goal` + `context`. When the parent has a
  resolved workspace, the child system prompt also embeds that workspace's
  project context files (`.hermes.md` > `AGENTS.md` > `CLAUDE.md` >
  `.cursorrules`), never SOUL. Pass paths, verbatim errors, versions and
  acceptance commands explicitly; do not rely on parent history.
- **Blocked even if the parent has them:** `clarify`, `memory`,
  `send_message`, `execute_code`, and (for `leaf`) `delegate_task`.
  Children inherit the parent's enabled toolsets and cannot widen them per
  call.
- **Process ownership:** a child's background terminal processes die with
  the child. Bounded builds and tests must finish inside the child (await
  them before returning); a server or CI watcher that must outlive the
  child has to be started by the parent. Returning a PID transfers
  nothing.
- **No wall-clock timeout:** a child ends on completion, error, or its
  iteration budget (`delegation.max_iterations`, default 50). Only zero
  progress trips stale-heartbeat handling; a long but advancing run is
  left alone, so do not use timeouts as a scheduling lever.
- **Cost:** `delegation.model` / `delegation.provider` pin every child
  (frontier parent plans, cheap model executes). The pin is global;
  per-task model override exists only on the Kanban path.
- **Roles / depth:** `leaf` (default) cannot re-delegate; `orchestrator`
  keeps `delegate_task` but only works once `delegation.max_spawn_depth`
  is raised above the default 1 (max 3). Depth multiplies cost: depth 3 at
  concurrency 3 is up to 27 leaves.
- **Not durable:** completion events that already fired survive a restart
  and are re-delivered; a child still running becomes `unknown` and is not
  resumed. For work that must outlive the process use `cronjob` or a
  parent-owned `terminal(background=True, notify_on_complete=True)`.

Config: `delegation.*` in `config.yaml`. Docs:
https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation

### Cron (scheduled jobs)

Durable scheduler — `cron/jobs.py` + `cron/scheduler.py`. Drive it via
the `cronjob` tool, the `hermes cron` CLI (`list`, `add`, `edit`,
`pause`, `resume`, `run`, `remove`), or the `/cron` slash command.

- **Schedules:** duration (`"30m"`, `"2h"`), "every" phrase
  (`"every monday 9am"`), 5-field cron (`"0 9 * * *"`), or ISO timestamp.
- **Per-job knobs:** `skills`, `model`/`provider` override, `script`
  (pre-run data collection; `no_agent=True` makes the script the whole
  job), `context_from` (chain job A's output into job B), `workdir`
  (run in a specific dir with its `AGENTS.md` / `CLAUDE.md` loaded),
  multi-platform delivery.
- **Invariants:** 3-minute hard interrupt per run, `.tick.lock` file
  prevents duplicate ticks across processes, cron sessions pass
  `skip_memory=True` by default, and cron deliveries are framed with a
  header/footer instead of being mirrored into the target gateway
  session (keeps role alternation intact).

User docs: https://hermes-agent.nousresearch.com/docs/user-guide/features/cron

### Curator (skill lifecycle)

Background maintenance for agent-created skills. Tracks usage, marks
idle skills stale, archives stale ones, keeps a pre-run tar.gz backup
so nothing is lost.

- **CLI:** `hermes curator <verb>` — `status`, `usage`, `run`, `pause`,
  `resume`, `pin`, `unpin`, `archive`, `restore`, `list-archived`, `prune`,
  `backup`, `rollback`.
- **Slash:** `/curator <subcommand>` mirrors the CLI.
- **Scope:** only touches skills with `created_by: "agent"` provenance.
  Bundled + hub-installed skills are off-limits. **Never deletes** —
  max destructive action is archive. Pinned skills are exempt from
  every auto-transition and every LLM review pass.
- **Cost:** the deterministic inactivity/prune sweep runs for free. The
  aux-model "consolidate overlapping skills into umbrellas" pass is
  **off by default** — opt in with `curator.consolidate: true` or
  `hermes curator run --consolidate`. Routine background curation costs
  zero tokens.
- **Telemetry:** sidecar at `~/.hermes/skills/.usage.json` holds
  per-skill `use_count`, `view_count`, `patch_count`,
  `last_activity_at`, `state`, `pinned`.

Config: `curator.*` (`enabled`, `interval_hours`, `min_idle_hours`,
`stale_after_days`, `archive_after_days`, `backup.*`).
User docs: https://hermes-agent.nousresearch.com/docs/user-guide/features/curator

### Kanban (multi-agent work queue)

Durable SQLite board for multi-profile / multi-worker collaboration.
Users drive it via `hermes kanban <verb>`; dispatcher-spawned workers
see a focused `kanban_*` toolset gated by `HERMES_KANBAN_TASK`, and
orchestrator profiles can opt into the broader `kanban` toolset. Normal
sessions still have zero `kanban_*` schema footprint unless configured.

- **CLI verbs (common):** `init`, `create`, `list` (alias `ls`),
  `show`, `assign`, `link`, `unlink`, `comment`, `complete`, `block`,
  `unblock`, `archive`, `tail`. Less common: `watch`, `stats`, `runs`,
  `log`, `dispatch`, `daemon`, `gc`.
- **Worker/orchestrator toolset:** `kanban_show`, `kanban_complete`,
  `kanban_block`, `kanban_heartbeat`, `kanban_comment`, `kanban_create`,
  `kanban_link`; profiles that explicitly enable the `kanban` toolset
  outside a dispatcher-spawned task also get `kanban_list` and
  `kanban_unblock` for board routing.
- **Dispatcher** runs inside the gateway by default
  (`kanban.dispatch_in_gateway: true`) — reclaims stale claims,
  promotes ready tasks, atomically claims, spawns assigned profiles.
  Auto-blocks a task after `failure_limit` consecutive spawn failures
  (default 2; configurable via `kanban.failure_limit` or per-task
  `max_retries`).
- **Isolation:** board is the hard boundary (workers get
  `HERMES_KANBAN_BOARD` pinned in env); tenant is a soft namespace
  within a board for workspace-path + memory-key isolation.

User docs: https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban
