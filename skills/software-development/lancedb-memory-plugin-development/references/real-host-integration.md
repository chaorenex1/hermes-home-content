# Real-Host Integration: deployment, agent-toolset seam, store-lock & review-storm diagnostics

Depth for deploying the plugin to the real Hermes home and diagnosing why a lane
"works in tests" yet fails on the real host. Commands assume HERMES_HOME =
`%LOCALAPPDATA%\hermes` on this machine.

## Deploy chain (verified, in order)

1. Confirm repo state (`git status`, `git log -1`); deploy the current working tree — only on the user's explicit request.
2. `python scripts/install_dev_plugin.py --target-hermes-home "<HERMES_HOME>" --replace`
   - Backs up `<HERMES_HOME>/backups/lancedb.backup-<UTC>` (copytree), then rmtree + clean copy
     (ignores `__pycache__`, `.pytest_cache`, `*.py[cod]`).
   - `--dry-run --replace` prints the action without writing (plain `--dry-run` refuses on an existing target).
3. Verify equality: walk repo `plugin/lancedb` vs deployed tree, sha256 each non-cache file; expect
   zero only-in-src / only-in-dst / differing (a full deploy is ~63 files) and no `__pycache__` in the deployed tree.
   The skill's `scripts/tree_parity_check.py <src> <dst…>` runs exactly this walk; extra targets cover
   profile copies (`profiles/<name>/plugins/lancedb`).
4. Mirror to named profiles: `cd $HERMES_HOME/scripts && python sync_default_profile_extensions.py`
   (dry-run → apply → dry-run). While the Gateway is down the 5-minute cron never fires — the direct
   run IS the named-profile deploy path (its SYNC_ROOTS cover `skills` AND `plugins`). Expect
   `plugins=replaced` for every profile. A skills-side `post-mirror verification failed` on several
   profiles is usually a FALSE ALARM: the mirror verifies by (size, mtime_ns) while running sessions
   rewrite `skills/.usage.json` and `skills/.bundled_manifest` mid-run. Confirm with content sha
   (`tree_parity_check.py` on the failing root; ignore those two live files' mtime/usage drift) before
   treating it as real drift — do not loop re-runs to "fix" it.
5. `hermes gateway restart` → `hermes gateway status` (expect `✓ Gateway process running (PID: …)`).
   Gateway lifecycle (start / clean-exit with PIDs) is recorded as JSON lines in
   `logs/gateway-exit-diag.log` — use it to attribute which process and code generation was live at a given time.
6. Smoke: `hermes chat -q "Reply with exactly: PROBE_OK" --oneshot`, then read
   `$HERMES_HOME/logs/agent.log` and `errors.log` (below).

## What "provider alive" looks like on a real smoke

- No new `Memory provider 'lancedb' initialize failed` in `errors.log` for the probe session.
- `agent.log`: `provider.turn_started turn=1` for that session.
- `session-context.db::session_layer_counters` gains a row for the probe session
  (`base_turns`/`dialectic_turns` advanced; `counting=0` and `stopped_at` set after session end).
- `provider.dynamic_turn_job_gated turn=1 … base_cadence=5` is SUCCESS, not failure: with the real
  config cadence=5 a turn-1 session must NOT enqueue a dynamic job — an empty `dynamic_turn_jobs`
  table at turn 1 is correct gating.
- First successful init on an old store migrates the schema in place, leaving per-step
  `memory.schema-<N>.backup.db` files next to `memory.db`, and creates `session-context.db`.

## The agent-toolset seam (bind `tools=` vs `toolsets=`)

The Host facade (`hermes_cli/plugin_runtime.py` in the host tree) exposes TWO channels:

- `bind(tools=(...))` — PRIVATE tool names only, resolved against the plugin's registered private
  tools; any other name raises `KeyError: "unknown private tools for '<plugin-id>': <name>"`.
- `bind(toolsets=(...))` — HOST-owned toolset names, validated against the host allowlist
  (`_ALLOWED_HOST_TOOLSETS`). `session_search` and `skills` are host toolsets; the `skill_view`
  TOOL is granted through the `skills` toolset (a bare `skill_view` toolset name does not exist).

Rules:
- Split lane requests before bind: private toolset names expand to private tool names (`tools=`);
  every other name is a Host toolset (`toolsets=`). Keep a small alias map for legacy names
  (e.g. `skill_view` → host toolset `skills`).
- Treat the host allowlist as part of the contract: when a lane legitimately needs another host
  toolset, extend it there (minimal edit) and add a host-side accept test beside the reject test.
- **Mocked-host trap**: every repo test fakes the ctx.agent facade, so a wrong-channel bind passes
  the whole suite and fails at the first lane run on the real host. When touching lanes' toolsets,
  read the real host tree first (`hermes_cli/plugin_runtime.py`, `agent/plugin_agent.py`
  `_host_tool_names_for_toolsets`) before trusting fixtures, and run one real lane afterwards.
- Diagnostic signature: `provider.turn_job_failed … error_type=KeyError` with a traceback ending at
  `hermes_cli/plugin_runtime.py` `resolve` = this seam. In-flight sessions loaded from older code
  may log `SchemaVerificationError: database schema is newer than this provider` — an expected
  transient after a store migration; restart the session, do not "fix" it.
- Host WIP files are untracked/edited in place; record every host edit under
  `$HERMES_HOME\patches\hermes-agent\` (patched file copy + a change note) so Hermes updates cannot
  silently erase it.

## Plugin-Agent context seam (kb_* refusals)

- Signature: in plugin-agent lanes (summary/dialectic/extraction/profile-review), kb_* read calls all
  return `invalid_arguments` `"plugin Agent context belongs to another plugin"` (retryable=false);
  memory maintenance jobs fail closed and the refusals recur in every fresh process — a restart does
  NOT clear them (unlike the stale-generation class in SKILL.md §1; a post-deploy process
  reproducing a signature rules stale code OUT). `kb_mode` failing with `permission_denied: internal
  Agent workflows cannot switch another session's mode` is a different, expected guard.
- Mechanism: `register_context_run` (plugin `agent_context_runtime.py`) keys the run by the plugin id
  the plugin derives from the facade — `getattr(agent_facade, "_plugin_id", "lancedb")` in
  `plugin/lancedb/__init__.py` and every lane registration in `agent_pipeline.py`. The host envelope
  carries `identity.plugin_id`, built by the memory loader as `f"memory/{name}"`
  (`<hermes-agent>/plugins/memory/__init__.py`). The real `PluginAgentFacade`
  (`hermes_cli/plugin_runtime.py`) holds only `_identity`/`_registry`/`_runner` — no `_plugin_id` —
  so the plugin side falls back to `"lancedb"` while the envelope says `"memory/lancedb"` and
  `resolve_context_run` rejects the mismatch.
- The suite stays green because repo fixtures fake the facade WITH `_plugin_id="memory/lancedb"`
  (see `tests/test_ctx_agent_private_registration.py`, `tests/test_profile_agent_runtime.py::
  test_runtime_preserves_host_plugin_identity`). Probe the REAL classes instead: run
  `python <skill>/scripts/host_facade_probe.py <hermes-agent tree> [<HERMES_HOME>]` with the host
  venv python; it prints the facade class, `_plugin_id` presence, the value the plugin would read,
  and `identity.plugin_id`.
- Fix direction (host-side, minimal; record under `$HERMES_HOME\patches\hermes-agent\`): expose
  `_plugin_id = identity.plugin_id` on `PluginAgentFacade` so registration and envelope agree. Verify
  afterwards with one real kb_* call from a plugin-agent lane plus an `errors.log` count that stops
  growing.

## Real-store writer.lock: stale-lock diagnosis

- The store lock is a create-exclusive file `$HERMES_HOME/lancedb-memory/writer.lock` containing
  `pid=<N>`, removed on release, with NO stale recovery. A holder that crashes or is killed wedges
  EVERY later writer (`WriterLockTimeout: writer lock is already held`) — real sessions keep
  answering while the provider silently degrades (visible only in logs).
- Detect: `stat` `writer.lock` and `memory.db` — both frozen at the same old mtime = the crash time;
  read the lock file's pid; confirm it is dead (`tasklist | grep -w <pid>` AND `ps -W | grep -w <pid>`).
- Remediate only when the pid is dead: back up `memory.db` + `manifest.json` to
  `backups/lancedb-memory-store-<UTC>/` and `cmp`-verify, delete the lock, re-run the smoke; expect
  the schema migration and lock-free operation afterwards.
- A leak can recur the same day: any process that dies mid-hold (including parallel pytest runs
  whose stray threads touch the real store) leaves a fresh lock — re-run the detection recipe
after any unexpected `initialize failed` line rather than assuming the first fix holds.
- Durable fix direction: WriterLock should detect and reclaim a dead-pid lock; record it as a
  finding rather than hot-patching it mid-deploy.

## Profile-review retry storm (poisoned job) — reset recipe

- Signature: `provider.profile_review_failed mode=normal error_type=RuntimeError duration_ms≈450…`
  repeating about once per second in `agent.log`, with NO traceback — the handler logs a single
  debug line. Count `profile_review_failed` against `profile_review_completed` across the log:
  a repeating failure with zero completions is a stuck job, not a crash to debug.
- State lives in real `memory.db`: `profile_review_jobs` (`attempt_count` in the tens of thousands =
  the storm), `profile_review_kind_jobs`, `profile_review_phase_runs`, `profile_review_leases`
  (usually empty while idle), and `profile_review_state` (3-day cadence cursor — never touch it).
- Mechanism: the coordinator retries one job per ~30 s tick and re-enters the same terminal state
  forever when the durable phase job is non-resumable — an interrupted kind job (`InterruptedProcess`
  from a host that exited mid-review) or a durable `agent_jobs` phase row left failed by an older
  seam bug. `fail()` no-ops on an already-failed row, so the loop never progresses.
- Reset (only after the DB/journal shows the job is poison, not in-flight work):
  1. Back up `memory.db` (`cmp`-verify) to `backups/lancedb-memory-store-<UTC>-pre-review-reset/`.
  2. Targeted DELETE of that job family: `profile_review_kind_jobs WHERE job_id LIKE '<job_id>:%'`,
     `profile_review_phase_runs WHERE job_id='<job_id>'`, `profile_review_jobs WHERE job_id='<job_id>'`;
     leave `profile_review_state` and the lease tables alone.
  3. The next tick on a long-lived provider host recreates a fresh job for the due window; confirm
     zero new `profile_review_failed` lines afterwards.
- Host-lifetime rule: reviews run inside a provider-hosted process; a one-shot `hermes chat
  --oneshot` probe exits mid-review and poisons the in-flight job. Use probes ONLY for the
  init/counter smoke; verify reviews through the gateway (or another long-lived session) by waiting
  for `profile_review_completed`, or leave verification to the user's next long session.
- Durable fix direction (record as a finding, don't hot-patch): make interrupted kind jobs
  resumable/reconcilable (fail-forward) so a short-lived host cannot wedge the review loop.

## Memory boundary outbox (boundary-delivery failure signatures)

- `agent.memory_boundary_outbox: memory boundary delivery failed for <event>: session_id does not
  match the active Provider session` in `agent.log` = the durable outbox replaying a boundary event
  whose session is no longer the one the provider instance is bound to: the plugin guard
  (`_bound_session` inside `on_session_end`/`on_session_switch`) raises, the host marks the event
  failed and retries with ≤60 s backoff (publishing + inline attempt in
  `run_agent.py::_publish_memory_boundary`; worker loop in `agent/memory_boundary_outbox.py`;
  re-verify line numbers).
- For an already-ended session this backlog NEVER drains: every fresh process binds to its own new
  session, so the retry "waits" for a provider binding that will never exist again. Quantify in
  `state.db::memory_boundary_outbox` (read-only sqlite3): undelivered rows whose `attempts` climb
  into the hundreds/thousands for weeks, `next_attempt_at` rolling every ≤60 s. Requirement impact:
  `on_session_end` semantics for those sessions (stop both turn counters, fire the dialectic
  trigger, expire the working set) never run. Do not delete outbox rows or hand-patch the store to
  silence it; the repair is a plugin-side contract change (below), not a store edit.
- Repair contract (landed in the dev-repo working tree — re-verify against live code before
  extending it): `on_session_end`/`on_session_switch` treat the EVENT's session as authoritative —
  `_boundary_session()` (falls back to the live binding only for empty/None) and
  `_boundary_turn_number()` (expiry watermark from that session's own counters row); the dialectic
  trigger is recorded against the stopped session's scope/mode via
  `_enqueue_dialectic_reasoning(counters=...)`; a deferred `on_session_switch` (parent ≠ bound) only
  expires the old scope and records the event id and must NEVER rebind the live session, while the
  inline path (parent == bound) keeps the original rebind. `_bound_session`'s strict check stays for
  the live surfaces (`working_scope`, `set_session_mode`, `on_turn_start`, `compress_context`).
  Regression: `tests/test_boundary_deferred_delivery.py`; host-seam probe (real host delivery
  functions driven against the plugin): `scripts/boundary_outbox_probe.py`. Deploying the repair
  drains the backlog once; old sessions without a counters row make `stop_session` return None →
  clean no-op. Residual: no event-id dedupe on the end path — a crash between processing and
  `delivered_at` marking replays one boundary (one extra dialectic trigger).
- The DB `last_error` is redacted (`ValueError: memory boundary delivery failed`); the true message
  and traceback live only in `agent.log` (DEBUG). `delivered_at` is NOT proof the provider
  processed anything: a non-primary provider instance early-returns from `on_session_end` without
  raising, so the host can mark an event delivered as a silent no-op.
- If delivery stops outright: `logs/tui_gateway_crash.log` groups thread exceptions by
  `thread=memory-boundary-outbox`. `OverflowError: int too large to convert to float` from
  `_backoff_seconds` (`agent/memory_boundary_outbox.py`) means a long-retried event's `2 ** attempts`
  overflowed and killed the worker; the clamp fix (`exponent = min(attempts, 32)`) is recorded under
  `$HERMES_HOME\patches\hermes-agent\` — after a Hermes update, verify the clamp is still present
  (`grep "min(attempts, 32)" agent/memory_boundary_outbox.py`) before re-diagnosing.
- `Hook '<name>' callback <fn> skipped after previous timeout or while still running`
  (`hermes_cli.plugins`) means the callback's bounded worker (30 s budget, ~60 s post-timeout
  suppression, per `hermes_cli/plugins_dispatch.py`) is still running or recently timed out; the
  callback `__name__` identifies the registrant (a bare `callback` = an anonymous registration
  closure/wrapper) but is NOT unique across plugins — `post_tool_call` is registered by lancedb's
  lifecycle hooks (bound method), by the system-browser plugin, and (named `_on_post_tool_call`) by
  disk-cleanup; enumerate candidates with `grep -rn 'register_hook("post_tool_call"'` over
  `$HERMES_HOME/plugins` and `<hermes-agent>/plugins/` (skip `__pycache__`). Exclude a candidate by
  its own downstream evidence: a skip line same-millisecond with that plugin's persisted-result
  line (e.g. `provider.tool_metric … persisted=True`) means that plugin's callback DID run — a
  skipped callback never executes — so the wedged callback is another registrant. A stuck worker
  suppresses that callback for the life of the process (only a restart clears it); plain suppression
  self-expires, so skips can be sporadic. Do not equate skips with total loss: downstream evidence
  decides (skipped invocations can coexist with persisted results).

## Stuck turn-job backlog (reclaim loop over ancient jobs)

- Signature: a freshly started process logs `provider.turn_job_started … phase=summary attempt=36`
  within seconds of init (any fresh smoke/CLI/gateway process re-claims ancient jobs via
  `recover_incomplete`); the attempt ends `provider.turn_job_failed … error_type=AgentRunFailure` with
  `agent_runtime.AgentRunFailure: Plugin LLM structured output did not match schema: 'session_id' is a
  required property` (summary lane model omits `session_id` in the receipt). The SAME lane's
  kb_tree/kb_read calls succeed — this is NOT the kb envelope seam; `attempt_count` grows by ~1 per
  process start and the job re-enters the queue.
- A one-shot smoke in a fresh process burns ±1 attempt per stuck job — expected, not a regression.
  Do not delete/reset the rows to silence it; the fix belongs in the summary lane's receipt contract
  (model/schema alignment for legacy job payloads) — record as a finding.

## Deploy-adjacent home hygiene

- Drop stale `plugins.enabled` entries by byte-preserving `config.yaml` edits: remove exactly the one
  line (including its EOL), `yaml.safe_load` old and new and assert the only structural difference is
  that list item, keep a `config.yaml.bak-<UTC>` — the patch tool refuses config.yaml. `hermes plugins
  disable <name>` errors "not installed or bundled" for plugins that were removed outright; editing
  the enabled list is the fix (each process boot logs the stale entry by name until then).
- Compat shims from the host's plugin decomposition: `hermes plugins compat` lists ENABLED PLUGINS
  importing soon-removed paths, but host files can hold the same stale import lazily (invisible to
  that scan) — grep the host tree for the retired symbol and switch to the new module path; verify
  with the owning host test file afterwards.
