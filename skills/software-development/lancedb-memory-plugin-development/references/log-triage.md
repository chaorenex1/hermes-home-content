# Runtime log triage ("检查Hermes日志/报错")

When the user asks to check Hermes logs for plugin errors, run this pass and produce a
severity-ordered report — do not page through `agent.log` line by line.

## Pass order

1. `read_file` `$HERMES_HOME/logs/errors.log` end-to-end (small, WARNING+ only; DEBUG lines never
   land there). `mcp-stderr.log`, `desktop.log`, `gui.log` are short — read them too; usually noise.
2. Sweep `$HERMES_HOME/logs/agent.log` with Python and print aggregates:
   - level × logger counts for WARNING/ERROR/CRITICAL (the short list worth reading);
   - per-pattern counts with digits normalized, to find floods;
   - count FAILURES by the unique failure line, not by phrase hits: one exception contributes ~3
     matching lines (the `raise …` frame, the exception line, the log line) — grep counts overstate
     the incident by ~3x; state the inferred distinct-failure count.
   - the file is appended by EVERY live process (desktop backend, CLI, plugin agents) and can be
     re-created per process start: read first/last timestamps before quoting a window.
3. Attribute a line to a process before reasoning about it: session-tagged lines carry
   `[YYYYMMDD_HHMMSS_hash]`; plugin DEBUG lines are untagged, so pair them by same-millisecond
   timestamps with tagged `agent.tool_executor` lines (same-ms pairing proves same process).
   `hermes_cli.plugins` hook lines carry no tag at all.
4. Prove current-generation code before blaming it: `sha256sum` the repo
   `plugin/lancedb/__init__.py` against `$HERMES_HOME/plugins/lancedb/__init__.py` — equal hashes =
   live current-tree defect, not a stale host (stale-host signatures: SKILL.md §1).
5. Quantify anything durable in the stores, not in the log window (logs only show the window):
   `state.db::memory_boundary_outbox` (undelivered rows, `attempts`, `next_attempt_at` cadence),
   plugin stores under `$HERMES_HOME/lancedb-memory/` (see `references/architecture-anchors.md`).
   Python `sqlite3` with `file:...?mode=ro` URI — read-only, never write during triage.
6. `profiles/<name>/logs/` are usually OLD generations: check the plugin logger digest
   (`_hermes_user_memory.lancedb__source_<digest>`) and the error vocabulary (e.g.
   `context_scheduler` = retired name) before including them; report history as history.

## Report shape (user's standard)

Severity-ordered findings; each with the exact signature line, raw counts, `file:line` anchors
(plugin + host), requirement impact (which hook/provider behavior is actually lost), and a fix
direction. Benign observations grouped last. Close with open items and, when a fix would change a
runtime contract, one explicit question for the ruling — an inspection request does not license
implementing the contract change.

## Signature table

- `ValueError: session_id does not match the active Provider session` + `memory boundary worker
  delivery failed` → outbox wedge vs the plugin session gate; see `references/real-host-integration.md`
  §memory boundary outbox (permanent backlog; quantify in the DB).
- `Hook 'post_tool_call' callback post_tool_call skipped after previous timeout or while still
  running` → live wedged/slow callback, NOT a stale-generation artifact when the name is a real
  callback; the name is shared across plugins — see the skips entry in `references/real-host-integration.md`.
- `agent.title_generator: Instant title failed` + `ValueError: Title '<t>' is already in use by
  session <id>` → host title-uniqueness conflict: every plugin-agent session titles itself
  `Plugin-requested goal: <goal>`, so repeated goals collide. Falls back to LLM title generation —
  report as a host-side nuisance, not a plugin defect.
- `plugins.memory: register() failed for lancedb: private tool 'kb_*' is already registered for
  'memory/lancedb'` → the SECOND in-process provider registration for another agent: the plugin's
  `register(ctx)` raises against the process-local private-tool registry, the host loader
  (`<hermes-agent>/plugins/memory/__init__.py`) swallows it and falls back to
  `_instantiate_subclass` — its own comment calls this a "silent downgrade"; that agent's provider
  is a bare subclass instance, not the registered one.
- `provider.agent_job_failed … error_type=AgentPipelineError` / `provider.profile_review_failed …
  error_type=ContextAgentError` → plugin-agent lane failures; first check the same window for
  upstream provider faults (e.g. `Non-streaming API call stale for 90s` + `Retrying API call`)
  before diagnosing lane logic.
- Benign noise — do not report as defects: `tools.registry check_fn … returned False` (per-turn
  availability probes), skill slash-command collisions, `credential pool: no available entries`,
  platform-disabled-by-config warnings, "not logged into Nous Portal" (skills sync inert), and
  plugin-agent tool refusals that are designed self-scope (`session_search … not found in this
  profile`, `kb_read … memory file does not exist`, `kb_tree … permission_denied: independent
  profile review uses only its frozen read manifest`).
