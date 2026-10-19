---
name: hermes-plugin-development
description: "Use when building or extending a Hermes plugin."
version: 1.0.0
author: Masia
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, plugins, register, llm, subagents, hooks, middleware, validation]
    related_skills: [hermes-agent, hermes-web-provider-plugin, hermes-secret-source-plugins, lancedb-memory-plugin-development, safe-extension-deployment]
---

# Hermes Plugin Development

Cross-type knowledge for `plugin.yaml` + `register(ctx)` plugins under `$HERMES_HOME/plugins/<category>/<dir>/`: giving a plugin AI capability (LLM calls, child agent sessions), participating in the main agent loop, and the validation loop that proves a registration actually works.

## When to Use

- Building or extending any Hermes plugin: tools, hooks, commands, LLM calls (`ctx.llm`), child agent sessions (`ctx.subagent_lifecycle`), or answering "how do I do X in a plugin".
- Debugging a plugin registration, hook, or LLM/subagent call that does not behave as documented.
- Type-specific plugin kinds load their own skill instead: web-search/extract provider → `hermes-web-provider-plugin`; secret-source backend → `hermes-secret-source-plugins`; LanceDB memory → `lancedb-memory-plugin-development`. Finished-plugin deployment (atomic swap, rollback, runtime verification) → `safe-extension-deployment`. Recovering another agent's adviser/reviewer mechanism to port into a plugin → `agent-internals-forensics`.

## Answer from the live install, not memory

Plugin contracts move between releases. Before answering or writing plugin code:

1. `hermes --version` — prints the live Install directory (`.../installs/<hash>/environments/<hash>/workspace`).
2. Read the contract in the live tree: `hermes_cli/plugins.py` (PluginContext registrars + `VALID_HOOKS`), `agent/subagent_lifecycle.py`, `agent/plugin_llm.py`.
3. Read the in-tree docs — do not guess: `website/docs/developer-guide/plugins/index.md` (registrars, hook table, middleware table), `plugin-llm-access.md`, `subagent-lifecycle-api.md`; public hook reference in `website/docs/user-guide/features/hooks.md`.
4. A second source checkout may exist (`$HERMES_HOME/hermes-agent/`); confirm parity (`diff -q <a> <b>`) before citing either tree — the running install is the one that counts.

## Pick the AI surface (decision table)

| Need | Surface | Owns an agent loop? |
|---|---|---|
| One LLM call (summarize / classify / rewrite / extract) | `ctx.llm.complete()` / `complete_structured()` (+ async variants) | No — single bounded call, no tool loops |
| Full child agent (LLM + tools, own loop) | `ctx.subagent_lifecycle.launch(SubagentLaunchRequest(...))` | Yes — same host path as `delegate_task` |
| Observe/steer the user's running turn | `ctx.register_hook(...)` / `ctx.register_middleware(...)` | No — participates in the main loop |
| Direct in-process `AIAgent` | `from run_agent import AIAgent` | Bundled-plugin escape hatch only — private core import |

Exhaustive request fields, limits, states, methods, routing rules, and pitfalls: `references/llm-and-agent-loops.md`
(which also carries the working script-probe recipe: import `run_agent` BEFORE any `hermes_cli.*` module).

## Escalate to async without duplicating the loop

`AIAgent`'s loop is synchronous — there is no `async def` in `run_agent` or
`agent.conversation_loop` — so an async surface offloads the *whole* run; it never wraps a single
call in a coroutine. Ship both entries from one implementation:

```python
def run(message, *, context="", model="", provider="", toolsets=None) -> AgentRun:
    ...                                   # sync; import run_agent FIRST inside it
async def run_async(message, **kw) -> AgentRun:
    return await asyncio.to_thread(run, message, **kw)
```

- Register the coroutine function together with `is_async=True`
  (`ctx.register_tool(..., handler=handle_async, is_async=True)`); `tools.registry.dispatch`
  bridges it for sync callers through `_run_async()` and is safe inside a running loop.
- The pairing is strict and fails at dispatch, not at registration: async handler +
  `is_async=False` hands a coroutine to the result normaliser, sync handler + `is_async=True`
  hands a string to `await`. `validate` compares names, not callable shapes — only an execution
  probe catches the swap.
- Keep the route owner thin: the loop lives in its own module (`run` / `run_async` + a small
  result dataclass), while the aux-task plugin keeps only config, framing, schema and the two
  handlers. Two copies of the constructor drift the moment one gains `reasoning_config` or a
  new guard.
- Keep the loop's EXTERNAL surface to what a caller can actually know — message, context, system
  message, model, provider, toolsets — and resolve model + credentials + reasoning + budget inside the
  runner with the gateway helpers (`gateway.run._load_gateway_config` / `_resolve_gateway_model` /
  `_resolve_runtime_agent_kwargs`, `hermes_constants.resolve_reasoning_config`), the way
  `feishu_comment.py::_resolve_model_and_runtime` does. A caller forced to assemble
  `api_key`/`base_url`/`api_mode`/`credential_pool` is a design error: every call site repeats the
  plumbing and one of them forgets `reasoning_config`. A pinned `provider` re-resolves that
  provider's credentials — never send another provider's model with the main route's key.
- A system message belongs to the TURN (`run_conversation(prompt, system_message=...)`), not to the
  constructor and never merged into the user message. Persona/rubric text prepended to the message
  pollutes the evidence the peer is asked to judge; `ephemeral_system_prompt=` at construction binds
  it for the agent's whole life and hides it from callers who only supply one.
- Isolation of a peer run is explicit: `skip_context_files=True`, `skip_memory=True`,
  `skip_background_review=True`, and a deliberate decision on `load_soul_identity` — that flag LOADS
  the operator's SOUL identity (it is not an isolation switch), so "all four True" means isolated
  from project/memory/review but speaking in the configured voice.
- `asyncio.to_thread` copies the contextvars, which is what the gateway's per-profile secret
  scope needs; `close()` then runs in the worker thread that built the agent.

## Run an agent loop: ctx.subagent_lifecycle

```python
from agent.subagent_lifecycle import SubagentLaunchRequest   # public allowlisted import

def run_review(args, **kwargs):          # _ctx captured in register(ctx)
    svc = _ctx.subagent_lifecycle
    handle = svc.launch(SubagentLaunchRequest(
        goal="Review this change for regressions.",
        context="Only inspect the supplied repository.",
        role="leaf",
        allowed_toolsets=("file",),      # registered names; subset of parent's
    ))
    term = svc.wait(handle, timeout_seconds=120)
    if term.timed_out:
        return json.dumps({"success": True, "data": {"state": term.state.value,
                                                     "handle": handle.to_dict()}})
    r = svc.result(handle)               # .summary / .terminal_state / .result_hash
    return json.dumps({"success": True, "data": {"state": r.terminal_state.value,
                                                 "summary": r.summary}})
```

Rules that cause first-try failures (full list in the reference):

- Callable only inside an active agent turn — a plugin tool handler or a hook callback. Outside one it raises `SubagentLifecycleError` ("No active Hermes parent session is available."). Works in CLI, gateway, non-interactive, kanban-worker sessions.
- `allowed_toolsets` must be registered names and a subset of the parent's toolsets — it narrows, never broadens.
- `timeout_seconds`, `working_directory`, `blocked_tools` are rejected by launch validation — do not pass them (per-launch timeouts are not supported, children get isolated workdirs, per-tool blocking must be expressed as `allowed_toolsets`). They DO exist as fields on the frozen dataclass, so `dataclasses.fields()` and autocomplete suggest they work; the rejection fires inside `launch()`.
- `provider=` must already be a configured Hermes provider; routing precedence is request.provider > delegation config > parent.
- `agent.subagent_lifecycle` is on the public import allowlist; `run_agent` is not (see the escape hatch in the reference).
- Copy-ready pair that already passed `validate` + `doctor`: `templates/agentloop_plugin_init.py` + `templates/agentloop_plugin.yaml`. Register the tool under the plugin's own toolset namespace, not a core one.

## Mid-turn seams: what a hook or middleware can actually change

Hooks and middleware are not interchangeable; pick by when the effect must land.

- `pre_llm_call` runs ONCE per turn in the prologue, and its context is stamped into the turn's user
  message and replayed byte-for-byte for every provider attempt that turn. It cannot inject per
  tool-loop iteration.
- `llm_request` middleware runs per provider attempt, returns `{"request": {...}}` to replace the
  provider kwargs, and is synchronous with no timeout wrapper: ledger reads only, never a model call.
- A `pre_tool_call` block is visible: the message becomes that tool call's result, so the model may
  retry. Cap it per turn and reserve it for mutating tools.
- `pre_verify` keeps a turn going only when the turn edited files, and only up to
  `agent.verify_hooks.max_verify_nudges` — it is not a general continuation channel.
- `on_interim_message` carries visible assistant text only. `post_auxiliary_call` carries usage per
  auxiliary attempt and is the meter for a plugin's own LLM calls.
- Hooks are bounded by `plugins.hook_callback_timeout` (default 30s; a slow callback is abandoned and
  suppressed for 60s). Model work belongs on a worker thread.
- The system prompt is built once per session and replayed; no plugin rewrites it mid-session.
- `VALID_HOOKS` in the live `hermes_cli/plugins.py` is the authority; the public hooks page lags.

Urgency-to-seam mapping, the exact return contracts, and the two-attempt probe that proves which
seam fired: `references/hook-and-middleware-seams.md`.

## One ledger, one producer

A layered plugin that writes the same review table from two places (a cadence-based deeper
reviewer and a per-turn injector) ends up with duplicate advice that dedupe can only hide. Merge
the production path, not just the output: the deeper layer keeps its own artifact (a correction
note on the artifact it owns) and the live reviewer is the only writer of advice rows.

- **Retire a producer in one change.** Grep the removed contract key across the plugin *and*
the tests before running anything: prompt contract, parser/normalizer, store write, artifact
section heading, the consumer's candidate block, the store's consume/promotion branch, and every
fixture helper that builds the old reply. A shared per-file fixture (`_dialectic_json(...)`) makes
this one edit; hand-rolled payloads scattered per test make it a sweep.
- **Give retired rows an explicit fate.** Pending rows of a source nobody writes any more are a
silent leak: expire them through the existing TTL path, ignore them on read, or migrate them, and
say which in the code. Never leave a consumer still reading a source that has no producer.
- **Republish on no-op, or the old artifact stays live.** If the deeper layer's artifact only ships
when it changes something, the last advice-bearing artifact survives as the "latest" one forever.
Publish a truthful no-change note (`- no change this window`) so the stale text is replaced.
- **Section headings are a contract.** The `## Heading` set is duplicated in the artifact
validator, the store's section→conclusion map, and the prefetch/digest readers. Rename it in all
of them in the same change; a half-renamed heading silently stops indexing the new artifact while
the old rows keep serving as current.
- When the layer's only product is a correction of a specific row (a base refresh, a job window),
  skip the model call entirely if that row is absent. A review with nowhere to write its result burns
  tokens and produces nothing.
- **A downstream review validates against its source row, not a blanket non-empty rule.** An
  upstream pass can legitimately publish sparse cards (a window with no identity or summary
  evidence); a review that echoes those empty fields is faithful, not broken. Reject only content
  the source row carried and the reply dropped, plus listed explicit clears. A validator that
  demands every field be non-empty fails every review of a sparse window, retries twice, and keeps
  the content watermark stuck. The artifact docs must state the same rule in every section, or one
  will promise "empty arrays are valid" while the validator refuses them.
- **Deliver after the turn ends.** A plugin has no send API of its own: when advice arrives after the
  final answer and must reach a gateway chat, call the host tool in-process —
  `send_message_tool({"target": platform, "action": "send", "message": text})` — and treat
  `json.loads(result)["success"]` as the receipt, so a rejected send leaves the row pending instead of
  claiming delivery. Guard on platform (never CLI/TUI) and keep a notified-id set so a retry does not
  repeat the message.
- **Sweep at the terminal hook, not only at publish.** A background review can finish before
  `post_llm_call` marks the turn terminal, so a notify-on-publish check alone misses it. Do both: the
  publish path notifies when the session is already terminal, and the terminal hook sweeps rows nobody
  has sent. The notified-id set makes the double path idempotent.

## Validation loop (before claiming anything works)

- `hermes plugins validate <plugin_dir>` — runs `register(ctx)` with a real context: undeclared tools (`provides_tools`), collisions, import errors; warns on private core imports (catalog rule 9).
- `hermes plugins doctor <plugin_dir>` — full discovery + import in a temp `HERMES_HOME`; prints the registration count (`registrations: 1 tool(s), 0 hook(s)`) — that line is the cheap proof a handler/toolset mismatch did not silently drop the tool.
- Local dev install is a copy, not `hermes plugins install`: that subcommand takes a catalog entry name, a Git URL, or `owner/repo` shorthand — never a local directory. Place the dir under `$HERMES_HOME/plugins/<name>/`, then `hermes plugins enable <name>` (writes `plugins.entries`; never hand-edit config.yaml).
- Repo vs install: when the plugin is developed in a git checkout while a copy also sits under `$HERMES_HOME/plugins`, make and verify the change in the repo, then deploy it — the user treats the installed copy as this plugin's deployment target and expects replacement + gateway restart + live verification in the same task, not a fix that only lives in the checkout. Back up the installed tree first and report the path, and put the backup outside `$HERMES_HOME/plugins/`: that root is the provider discovery root, so a sibling copy left inside it is a candidate second provider. On Windows the running gateway can hold the installed directory: `hermes gateway stop`, replace the tree (`rm -rf` then `cp -a`, which preserves mtimes), `diff -rq --exclude=__pycache__` against the repo, then start the gateway. Replacing under a live process fails or leaves a half-copied tree. After `hermes gateway restart`, prove the new code loaded from `logs/agent.log` (the manifest parse line names the install path, then the plugin's own hook lines appear); a "port still accepting connections" warning during restart is the old process draining, not a failure. A new default in the provider's config defaults applies to every live config that omits the key, so read the deployed config block before shipping a risky default and state the behavior change in the deploy report. Before overwriting, diff it: content the repo lacks is either an older generation (git log shows the removal) or a hand edit that exists nowhere else — a backup alone is not a decision. The ask-first exception is a different plugin owning the same aux key or tool name; report that conflict instead of retiring the other plugin by deleting it.
- Tool handlers must return a JSON **string** (the registry rejects plain dicts; only the multimodal envelope passes).
- Contract-mode test runs: point the suite at the host (`HERMES_WORKSPACE=<install workspace>` + the host venv's python). A bare local interpreter can lack host deps and produce false failures that look like your change; a suite that boots the real `agent.*` / `tools.registry` modules is the only run whose pass means anything. Two `-q` flags (a `pytest.ini` `addopts = -q` plus `-q` on the command line) also suppress the final `N passed` line — read the exit code, and take counts from `--co` (it prints `file.py: N` rows) instead of re-running to find out whether it passed.
- Prove hook **dispatch**, not just registration: `validate` and `doctor` check declared names and that `register(ctx)` runs, but only the agent's own dispatch proves a callback's return value is consumed. Stage the plugin into a temp `HERMES_HOME`, run the host venv python with the workspace on `sys.path`, call `hermes_cli.plugins.discover_plugins()`, then dispatch exactly as the loop does: `invoke_hook("pre_tool_call", tool_name=..., session_id=...)`, `get_pre_verify_continue_message(session_id=..., changed_paths=[...])`, or `invoke_hook("pre_llm_call", user_message=..., parent_session_id="")`. Seed the provider state (a pending row, a bound session) first, and assert the second call no longer fires — one-shot semantics are part of the contract.
- **A plugin scheduler fires in tests too.** With `cadence: 1` the background worker reviews on the first recorded event, so a test that then calls the worker method directly runs it twice and the call counter doubles (N becomes 2N, one per roster member). Give the test config a high cadence and drive the method explicitly, or `wait_idle()` before asserting call counts; assert the *prompt* content rather than the call count when both paths must run.
- Registration metadata (tool/skill descriptions) is snapshotted at load; a running Gateway needs a plugin reload for changed registration metadata to land — re-`enable` of an already-enabled plugin is a no-op.

## Diagnose from the host's logs, before touching code

A "check the logs and fix the plugin" request is evidence work: the installed copy can be commits
behind the repo, so part of what the log shows may already be fixed.

1. Read `$HERMES_HOME/logs/`: `agent.log` (plugin lifecycle, per-turn hooks, model calls),
   `errors.log` (WARNING+), `gateway-stdio.log` (the one-line `[gateway-crash] thread <name> raised ...`),
   `tui_gateway_crash.log` (the full traceback behind that line), `gateway.log` (host startup). Group
   matches by normalized message — one repeating warning is one bug, not N.
2. Prove each candidate is live before patching: grep the source for the exact method/attribute named
   in the traceback, and `diff -rq --exclude=__pycache__` the installed copy against the repo. A
   stale install replays already-fixed errors; deploying is the whole fix and no code change is owed.
3. Reproduce at the narrowest layer (call the failing store/worker method directly, or drive the
   tracker with an injected clock), then keep that reproduction as a regression test that fails on
   the old predicate. Prove the test is red on the old code with a path-scoped stash:
   `git stash push -- <file>`, run that single test, `git stash pop`; unrelated uncommitted work
   stays put. A test that only asserts "does not raise" is vacuous when the old code already
   swallowed the exception — assert on the log record or the returned status instead.
4. Separate model-quality failures from code defects before patching. "returned invalid JSON",
   "empty cards" and "no usable JSON after 2 passes" are not one bug: an "empty cards"
   rejection can be a validator contradicting an upstream pass that legitimately emitted empty
   fields (compare the reply with the source row it reviews), while a malformed reply from a small
   aux route is model behaviour (check `auxiliary.<key>.model`). Read `agent.log`'s
   `API call #N ... out=<tokens>` and `Turn ended ... api_calls=N/M response_len=<chars>` lines: a
   run that spends its tool budget on `tool_search`/`tool_describe` and ends with a long text
   answer is tool-thrash, not JSON incapability. Cap that budget and give it one no-tools repair
   pass; only truncated or invalid JSON with no tool calls is a reason to raise the aux model.
5. Fix, run the full suite, run the repo's host-verification script (often
   `scripts/verify_against_host.py --host-python <host venv>/python.exe --workspace <install>`;
   auto-detect fails on a non-standard install), deploy, restart the gateway, then re-grep the logs
   for zero new warnings from the plugin. Swap/rollback mechanics: `safe-extension-deployment`.

## One directory, several surfaces (provider + tools + hooks + aux route)

A memory-provider plugin is not limited to `register_memory_provider`: the memory loader builds a real
`PluginContext` (`plugins/memory/__init__.py`), so `ctx.register_hook`, `ctx.register_tool` and
`ctx.register_auxiliary_task` all work from the same `register()` — one repo can ship the provider, its hooks,
a tool and its own `auxiliary.<key>` model route.

- **Aux tasks need no manifest field; ctx-registered tools and hooks do.** List every tool passed to `ctx.register_tool`
  under `provides_tools:`, and every hook passed to `ctx.register_hook` under `provides_hooks:`. `hermes plugins validate`
  FAILS on an undeclared tool ("undeclared tools registered") and only warns about a declared-but-unregistered one; the
  manifest-contract test also compares `provides_hooks` against the registered hook set, so adding a hook is a three-file
  change (registration, manifest, that test). Tools a provider returns from `get_tool_schemas()` do
  NOT belong there — they never touch the plugin registry.
- **Collisions are asymmetric, and both are process-wide.** A foreign `auxiliary` key raises `ValueError`
  ("already registered by plugin X"); a duplicate tool name is refused with a warning and `register_tool`
  returns `None` instead of raising. So put the optional surface in its own `try/except` inside `register()` and
  keep the primary registration outside it: a refused adviser route must never cost the memory provider.
- **Moving a surface between plugins means retiring the old owner first** (uninstall/disable, or the new
  registration is refused/ignored). Keep the toolset name stable when you do — per-platform `toolsets:` lists
  select the toolset, not the plugin.
- Probing the registered surface end-to-end: assert `get_plugin_auxiliary_tasks()` contains the key and
  `tools.registry.registry.get_entry(<tool>)` returns an entry with the expected `.toolset` and `.is_async`,
  inside a host probe (temp `HERMES_HOME`, repo staged as `plugins/<name>`). That catches "registered but not
  callable" and a handler/flag mismatch, neither of which manifest validation can see.

## Memory-provider plugins (`plugins/memory/` contract)

Bundled examples to copy from: `plugins/memory/byterover` (CLI-backed) and
`plugins/memory/retaindb` (cloud + write queue) in the live install tree.

- `register(ctx)` calls `ctx.register_memory_provider(instance)` — one instance per plugin. Discovery order:
  bundled `plugins/memory/<name>/` → `$HERMES_HOME/plugins/<name>/` → `./.hermes/plugins/<name>/`
  (`HERMES_ENABLE_PROJECT_PLUGINS`) → pip entry points `hermes_agent.memory_providers`. The cheap scan
  reads the first 8 KB of `__init__.py` for `register_memory_provider`/`MemoryProvider`; `doctor` then
  auto-detects `kind: exclusive` from the same markers (no `kind:` field needed in plugin.yaml).
- **The INSTALLED DIRECTORY name is the provider name** `memory.provider` selects (`find_provider_dir(name)`
  → `<plugins>/<name>`). The `name:` field and the `name` property are labels — a hyphenated repo cloned
  as-is only activates if `memory.provider` equals that directory name; otherwise clone into
  `plugins/<provider-name>`. Rename all three together.
- ABC lives at `agent/memory_provider.py` (read it live): abstract = `name`, `is_available`, `initialize`,
  `get_tool_schemas`; everything else has no-op defaults. `initialize(session_id, **kwargs)` always carries
  `hermes_home` (profile-scoped — never hardcode) and `agent_context`; subagent/cron/flush contexts must not
  write memory. `handle_tool_call` must return a JSON **string** (`tool_error()` from tools.registry).
- Threading model: `sync_turn` and `queue_prefetch` run on the MemoryManager's background worker,
  `prefetch` runs on the critical path under a timeout (a still-running previous prefetch skips the
  provider that turn). So: do I/O in `queue_prefetch`, consume the cached block in `prefetch`, and let
  unexpected failures propagate only from `prefetch` (it is re-raised there); swallow errors in hooks.
- **Every background thread must inherit the caller's contextvars.** Spawn with
  `agent.memory_provider.spawn_context_thread(target, name=...)` (or
  `contextvars.copy_context().run`), never a bare `threading.Thread`. Profile isolation is a
  ContextVar-scoped HERMES_HOME override plus a per-turn secret scope; a bare thread starts empty and
  therefore reads the default profile's secrets or fails closed with `UnscopedSecretError: Hermes
  could not read this profile's <ENV_VAR>`, which kills the review/job on every run. This covers
  every helper thread, including a run-with-timeout wrapper that calls an LLM and any reviewer
  worker that must not steal the main loop. Probe it: set a ContextVar in the caller and have the
  spawned thread report it back — a bare thread returns the default.
- **A long-lived worker must carry the context per job, not once at thread start.** Capture
  `contextvars.copy_context()` where the job is enqueued (that turn's profile/secret scope) and run
  the review inside it. A context captured at thread creation pins whichever profile happened to
  schedule first, and a multiplexed gateway then resolves the wrong profile's scope. Drop the stored
  context on session reset and stop.
- **A bounded `join()` does not make a shared store safe to close.** An LLM-backed job outlives a
  5 s join; its error handler then writes to a closed sqlite connection
  (`AttributeError: 'NoneType' object has no attribute 'execute'`, dumped to
  `logs/tui_gateway_crash.log`) and the drain thread dies with the row left `running`. Pick one
  invariant-preserving shape: `stop(timeout)` returns whether the thread ended and `shutdown()`
  skips `store.close()` while a drain is in flight; or shutdown closes unconditionally and the
  drain-path store methods (`claim_jobs`, `complete_job`, `fail_job`, the job counts) treat
  `self._conn is None` as gone (`[]` / no-op / `"closed"`), with the failure-recording call itself
  wrapped. Nothing may raise into the drain thread; letting one connection die with the process
  beats crashing the handler.
- **Never key job-window uniqueness on an exact wall-clock timestamp.** Windows' `time.time()` has
  ~15 ms granularity on the Python 3.11 host, so two dispatches inside one tick produce the same
  `to_ts`; a store that dedupes `(session, from_ts, to_ts)` then collapses the second job into the
  first and the layer silently misses a window. Make the edge strictly increasing
  (`max(now, last_edge + 1e-6)`) and keep windows edge-to-edge, then test with a fixed clock and
  assert two distinct windows. Same trap for rate-limit buckets and "new since" cursors.
- Installed plugins under `$HERMES_HOME/plugins/<name>/` are not git repos. When you hand-edit one,
  leave a timestamped backup plus an apply-verified patch under `$HERMES_HOME/local-patches/`,
  generated from the pre-change files (`git -c core.autocrlf=false apply` onto a pristine copy must
  reproduce the live bytes). Otherwise the next install/update silently reverts the fix.
- `recall_status()` must reflect only the LAST `prefetch`; count==0 means "content, no discrete count".
- Verification ladder (all real, no mocks): `hermes plugins validate <dir>` (runs `register()` under the
  real contracts) → `hermes plugins doctor <dir>` (temp-HERMES_HOME discovery+import; prints
  `manifest: <name> <ver> (exclusive)`) → end-to-end loader probe: copy the plugin to
  `<tmp>/plugins/<name>`, run the host venv python with `HERMES_HOME=<tmp>` and
  `PYTHONPATH=<workspace>`, then `plugins.memory.discover_memory_providers()` /
  `load_memory_provider(<name>)` + `initialize/sync_turn/prefetch` round-trip.
- **pytest pitfall**: the plugin repo root IS the package (`__init__.py`). Pytest treats any ancestor dir
  containing `__init__.py` as a collectable package and imports the plugin module as a test module
  (`CollectError ... ImportError while importing test module '<repo>/__init__.py'`, relative import
  "no known parent package"). `--import-mode=importlib` does NOT fix it. Fix: put the pytest config inside
  `tests/pytest.ini` so rootdir=tests and the ancestor walk stops before the repo root.
- Test bootstrap that works everywhere: try importing the real host modules per module
  (`agent.memory_provider`, `tools.registry`) and shim only what fails; a shim parent module needs
  `__path__ = []` or `from agent.memory_provider import X` fails with "'agent' is not a package".
  Also load the plugin as a synthetic package (`spec_from_file_location(name, root/'__init__.py',
  submodule_search_locations=[root])`) — that mirrors the loader and makes relative imports work.
  An editable host install exposes `agent`/`hermes_cli` through a finder but not the host's
  root-level modules (`hermes_yaml`), so a host-mode test dies mid-run with `ModuleNotFoundError`
  even though `agent` imported. After importing `agent.memory_provider`, insert
  `Path(agent.__file__).resolve().parents[1]` into `sys.path` when that root holds the host's
  top-level modules.
