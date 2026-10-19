# LLM calls and child agent sessions from plugins

## ctx.llm — one bounded call at a time

- `complete(messages=[...], provider=, model=, temperature=, max_tokens=, timeout=, purpose=, task=)` → result with `.text`, `.provider`, `.model`, `.usage`, `.audit`.
- `complete_structured(instructions=, input=[{type: "text"|"image", ...}], json_schema=, schema_name=)` → adds `.parsed` (a Python object matching the schema) and `.content_type` ("json"/"text"). On parse/validation failure `.parsed` is None and `.text` carries the raw response.
- Async twins `acomplete()` / `acomplete_structured()` — use from gateway adapters or async hooks.
- Trust gate is fail-closed: `provider=`, `model=`, `agent_id=`, `profile=` raise `PluginLlmTrustError` until the operator opts in under `plugins.entries.<id>.llm.*` (independent per-override gates + allowlists). `task=` works only for an auxiliary task the plugin registered via `ctx.register_auxiliary_task()`.
- Boundary: one sync/async call — no streaming, no tool loops, no conversation state. A tool-calling loop is `ctx.subagent_lifecycle`.

## ctx.subagent_lifecycle — a full child agent session

Runs a fresh Hermes child session (its own LLM + tool loop) built through the same host-owned path as `delegate_task`: parent tool-resolution restoration, memory notification, serialized `subagent_stop` hooks, resource cleanup, child-cost rollup. Same safety posture as delegation; it does not replace `delegate_task`.

The imports a plugin uses are public:

```python
from agent.subagent_lifecycle import SubagentLaunchRequest
```

### Launch request fields — exact limits (fail-closed)

- `goal` — required, non-empty, ≤ 16000 characters.
- `context` — optional, ≤ 32000 characters.
- `metadata` — JSON-serializable mapping, ≤ 8192 bytes.
- `role` — `"leaf"` (default) or `"orchestrator"`.
- `allowed_toolsets` — tuple of registered toolset names; when the parent has explicit `enabled_toolsets` it must be a subset (requests that would broaden permissions are rejected). Unknown names rejected; plugin-registered toolsets count as known.
- `model`, `provider` — optional routing overrides; precedence request.provider > `delegation` config > parent. Request `model` overrides the configured model. An unresolvable provider raises before launch.
- `parent_session_id` — if given, must match the active session.
- `correlation_id` — must be unique per parent session (duplicates raise); good for deduping re-launches.
- `timeout_seconds`, `working_directory`, `blocked_tools` — rejected by launch validation; do not pass. The fields exist on the frozen dataclass (so introspection, reprs, and IDE autocomplete present them as usable), but `launch()` runs a rejection table first and raises: `"Per-launch timeout is not supported; configure delegation timeout explicitly."`, `working_directory is not supported because Hermes delegates use isolated task environments.`, `"Per-tool blocking is not supported; use allowed_toolsets."` Waiting is expressed per call (`wait(..., timeout_seconds=)`), never per launch.

### Service methods and states

- `launch(request)` → `SubagentHandle`; serializable via `.to_dict()`. Carries a versioned opaque capability: malformed or forged handles read as UNKNOWN / UNKNOWN_HANDLE and cannot access a child. Launch is asynchronous (background pool) — multiple launches run concurrently.
- `status(handle)` → `.state`; `wait(handle, timeout_seconds=...)` → `.completed`, `.timed_out`, `.state`. The timeout is keyword-only (signature `wait(handle, *, timeout_seconds=None)`) — passing it positionally is a TypeError.
- `result(handle)` → `.terminal_state`, `.summary`, `.structured_payload`, `.result_hash`; before ready: `error_classification="NOT_READY"`.
- `steer(handle, text)` → bool: queues text for the child's next iteration boundary; False once the child finished, stopped accepting, or the handle is foreign.
- `cancel(handle, reason=...)` — cooperative; the terminal state is observed via `wait`/`result`, never claimed by cancel itself.
- `reconnect(handle)` — after a process restart returns `RECONNECT_UNAVAILABLE`; it never relaunches a child.
- States: PENDING, STARTING, RUNNING, SUCCEEDED, FAILED, INTERRUPTED, CANCEL_REQUESTED, CANCELLED, UNKNOWN.
- Terminal results: immutable, idempotent, ≤ 32k chars, omit transcripts/hidden reasoning, carry a result hash; retained in-process for a bounded period (~1 hour). Threads and handles do not survive process exit — treat them as interrupted.

### Where it may be called

Only while an agent turn is active — a plugin tool handler or a hook callback. Otherwise: `SubagentLifecycleError` ("No active Hermes parent session is available."). Works from CLI, gateway, non-interactive, and kanban-worker sessions; code that runs outside a turn (background threads, cron body) cannot launch.

### Threading pitfall (gateway multiplex)

Child construction and credential resolution read the per-profile secret scope, a ContextVar that fresh worker threads do not inherit. If you launch or await children on a new thread inside the gateway, carry the context: `contextvars.copy_context().run(fn, ...)` — one fresh copy per submitted task (a shared Context cannot be entered concurrently). Symptom when missed: `UnscopedSecretError` for the profile's env vars.

### Plugin-side wiring for a loop tool

- Register the tool under the plugin's OWN toolset namespace (`toolset="<plugin_name>"`), the way bundled plugins do (`google_meet`). Plugin toolset keys are persisted and enabled with the plugin, so an own name just appears; reusing a core toolset name (`file`, `terminal`) only muddles discovery.
- Never conclude a toolset name is invalid from a bare probe: `registry.get_registered_toolset_names()` returns `[]` outside an agent/plugin load, because registrations happen at init rather than at import of `tools.registry`. Grep `toolset="..."` in `tools/*.py` or read the config instead.
- A hook callback is a legal launch site, but it runs inline inside the user's turn — waiting there delays that turn. From a hook, launch and return the handle; do the `wait()` in a tool handler.

## Participating in the main loop (observe/steer, don't own)

`ctx.register_hook(name, callback)` — callbacks accept their declared fields; accept `**kwargs` for forward compatibility; a crashing callback is logged and skipped:

- `pre_llm_call` — once per turn, before the tool-calling loop. Return `{"context": ...}` (or a plain string) to inject text into the current user message; anything else / None = observer. The only hook whose return value injects context.
- `post_llm_call` — once per turn after the tool-calling loop (successful turns).
- `pre_api_request` / `post_api_request` / `api_request_error` — per physical provider request (several per turn once tools run); one level below the per-turn pair.
- `pre_tool_call` — may return a directive to block/deny a call; `post_tool_call` — observer with result and duration.
- `transform_llm_output` (return a replacement string; first non-None wins), `pre_verify`, `on_stream_start` / `on_stream_delta` / `on_stream_end`, `agent_loop_stopped`, `subagent_start` / `subagent_stop`, session lifecycle (`on_session_start/end/reset/finalize`).

`ctx.register_middleware(kind, callback)` — behavior-changing, unlike observer hooks:

- `tool_request` / `llm_request`: return `{"args": ...}` / `{"request": ...}` to rewrite the effective payload before anything downstream sees it; `None` = unchanged. `original_args` / `original_request` always carries the pre-middleware copy.
- `tool_execution` / `llm_execution`: wrap the call with `next_call` — call it exactly once (single-use) to run the chain, or skip it to short-circuit.

There is no public API for a plugin to start a turn on the user's main session — turns are user/platform-driven. To get agentic work going from a plugin, launch a child session instead.

## Escape hatch: direct AIAgent (bundled-plugin pattern)

Bundled plugins run in-process agents directly (e.g. the Feishu comment agent):

```python
from run_agent import AIAgent
agent = AIAgent(model=..., base_url=..., api_key=..., provider=..., api_mode=...,
                quiet_mode=True, skip_context_files=True, skip_memory=True,
                max_iterations=15, enabled_toolsets=["feishu_doc", "feishu_drive"])
result = agent.run_conversation(prompt, conversation_history=history or None)
# dict: final_response, messages, api_calls  — or agent.chat(prompt) -> str
agent.close()   # in a finally — releases tool subprocesses and HTTP clients
```

- For third-party plugins `run_agent` is a private core import — `hermes plugins validate` warns (catalog rule 9) and it can break on any release. Prefer `ctx.subagent_lifecycle`.
- Same contextvars rule as above when run on worker threads under the gateway.
- One agent per run; `close()` (in `finally`) or each run leaks subprocesses/clients in a long-lived process.
- `run_conversation(user_message, system_message=None, conversation_history=None, task_id=...)`; `chat(text)` returns just the final response string.

### Sync and async entry points from one implementation

The agent loop is synchronous (no `async def` in `run_agent` / `agent.conversation_loop`), so an async
surface offloads the entire run rather than wrapping one request:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class AgentRun:
    answer: str; api_calls: int; model: str; provider: str; toolsets: tuple[str, ...]
    def as_dict(self): return {...}          # toolsets back to a list for the JSON envelope

def run(message, *, context="", model="", provider="", toolsets=None) -> AgentRun:
    from run_agent import AIAgent            # FIRST — it swaps sys.path and re-execs
    resolved_model, runtime = _resolve_model_and_runtime()   # gateway helpers, see below
    final_model = model or resolved_model
    final_provider = provider or runtime["provider"]
    agent = AIAgent(model=final_model, **_agent_kwargs(final_provider, final_model, runtime),
                    enabled_toolsets=list(toolsets or []) or None, max_iterations=15,
                    quiet_mode=True, skip_context_files=True, skip_memory=True)
    try:
        result = agent.run_conversation(_prompt(message, context))
        return AgentRun(...)
    finally:
        with contextlib.suppress(Exception):
            agent.close()

async def run_async(message, **kwargs) -> AgentRun:
    return await asyncio.to_thread(run, message, **kwargs)
```

- `asyncio.to_thread` propagates contextvars (the gateway's secret scope depends on it) and keeps
  the blocking HTTP calls plus tool subprocesses off the event loop; `close()` therefore runs on
  the same worker thread that created the agent.
- Tool handler pairing: `ctx.register_tool(..., handler=handle_async, is_async=True)`. With
  `is_async=True` the registry calls `_run_async(handler(...))`, which is safe even inside a running
  loop; with `is_async=False` a coroutine reaches `_normalize_handler_result` and is rejected as an
  unsupported type. The reverse swap fails too (the registry awaits a string).
- Keep the sync entry public even when the registered tool is the async one: direct callers
  (workers, probes, `_run_async` bridges) then have one obvious function instead of constructing
  their own event loop.
- The external surface stays small: message, context, model, provider, toolsets. A `cfg=`/`history=`/
  `system_prompt=` parameter on the shared runner forces every caller to know the host's route
  plumbing. Framing (an adviser persona, a review rubric) belongs at the head of the message when
  the loop takes no system prompt; a caller that truly needs one passes `ephemeral_system_prompt=`
  at its own construction site, not by widening the shared runner.

### Binding the escape-hatch agent to an `auxiliary.<task>` route

The pattern the curator's review fork and the Feishu comment agent share (validated end-to-end):

1. `ctx.register_auxiliary_task(key, display_name=, description=, defaults={...})` — no manifest field exists for
   aux tasks; the entry IS the declaration. `key` must be `[A-Za-z0-9_]` only and must not be a built-in key
   (`hermes_cli/main_provider_setup._AUX_TASKS`); re-registration by the same owner is allowed, a foreign key raises.
   `defaults` is where plugin-owned non-routing keys (`max_iterations`, custom strings) ride along —
   `build_auxiliary_task_entry` keeps unknown keys verbatim. `inherit_from=` makes the task track a base task's route
   at read time. User config wins at `auxiliary.<key>`.
2. Read the block back with `load_config_readonly()["auxiliary"][key]` — but only for the knobs the CALLER owns
   (`provider`, `model`, `toolsets`; add your own defaults for anything plugin-specific). Do not hand the whole
   block to the runner as `cfg=`: that pushes route resolution into every call site.
3. Resolve model + credentials INSIDE the runner with the gateway's own helpers — the Feishu comment agent's
   `_resolve_model_and_runtime` is the reference implementation: `from gateway.run import _load_gateway_config,
   _resolve_gateway_model, _resolve_runtime_agent_kwargs`; `model = _resolve_gateway_model(_load_gateway_config())`
   with `hermes_cli.models.get_default_model_for_provider(runtime["provider"])` as the fallback;
   `runtime = _resolve_runtime_agent_kwargs()` for `api_key`/`base_url`/`provider`/`api_mode`/`credential_pool`
   (including the gateway's fallback chain); `resolve_reasoning_config(config, FINAL_model)` after overrides.
   `runtime` also carries `_fallback_notice`, `model`, `capabilities`, `requested_provider`, `command`, `args`,
   `request_overrides`. `AIAgent.__init__` takes 86 keyword params and is only a forwarder to
   `agent.agent_init.init_agent` (no `*args/**kwargs`; `tool_delay` is deprecated and not forwarded), and the
   gateway's own `_runtime_agent_kwargs()` returns exactly the subset it declares — so forward
   `api_key, base_url, provider, api_mode, credential_pool, request_overrides, requested_provider, capabilities,
   command, args` plus `reasoning_config`, and strip only `_fallback_notice` (internal notice) and `model`
   (resolved separately). `AIAgent(**runtime)` still dies on `_fallback_notice`, while dropping the rest teaches
   the agent a different provider contract: no request body overrides, no fallback identity, no ACP command routing.
4. A pinned `provider` that differs from the gateway route must be re-resolved AS a provider:
   `hermes_cli.runtime_provider.resolve_runtime_provider(requested=provider, target_model=model)` → its own
   `api_key`/`base_url`/`api_mode`/`credential_pool`. Reusing the main route's key for another provider's model
   is the failure that surfaces as a 401 from the wrong vendor. Same provider name (or `auto`/`main`/empty) →
   keep the gateway route untouched.
5. `AIAgent(model=, provider=, api_key=, base_url=, api_mode=, credential_pool=, reasoning_config=,
   enabled_toolsets=[...] or None, max_iterations=15, quiet_mode=True, skip_context_files=True, skip_memory=True)`,
   then `run_conversation(prompt)` and `close()` in `finally`.   `reasoning_config` is mandatory: without it
   `reasoning_effort` never reaches the adapter. `max_iterations` is the runner's own constant (the Feishu
   comment agent's 15), not a caller knob — a per-call budget is how two callers end up with different limits.
6. Pin the constructor surface in a test: `assert set(agent.kwargs) == {...}` against a fake `AIAgent`. A peer
   run must stay off `session_id` / `parent_session_id` / `platform` / `user_*` / `chat_*` / `session_db`, the ~24
   `*_callback` params, the checkpoint block and `run_budget_seconds`; set equality is the assertion that catches
   the next helpful-looking addition quietly binding the side agent to the user's session or trajectory.

`ctx.llm.complete(task=<key>)` is the single-call surface on the same route, but the task trust gate only accepts a
key the calling plugin registered ITSELF — another plugin asking for `adviser` is denied, not silently downgraded.

### Verifying an in-process agent plugin for real

`hermes plugins validate`/`doctor` prove registration, not execution. Two paths prove execution:

1. **A script probe — with the agent import FIRST.** `run_agent` bootstraps the managed runtime: it swaps
   `sys.path` to the pinned install environment and re-execs the process (the body runs twice and prints
   `gopass folder: applied N secrets`). A `hermes_cli.*` module imported before that survives the swap, but its
   own lazy imports do not — the signature is `ModuleNotFoundError: No module named 'ruamel'` raised by
   `hermes_yaml` moments after the same import succeeded. Order the imports `run_agent` → `hermes_cli.config` →
   `hermes_cli.runtime_provider` / `hermes_constants` inside the runner function, and do not "warm up" by reading
   config before calling the agent. With that order a plain venv script reaches a real consult: load the plugin
   package by spec, call the tool handler, and argue from its own payload (`api_calls: 1` = one model call;
   `api_calls: 2` with `toolsets: ["file"]` = a real tool iteration).
2. **A real turn**, when you want the host's own wiring: `hermes plugins enable <name>` →
   `hermes chat -q "Call <tool> … and print its raw JSON"`.
3. **A registration assertion inside the host probe** — `validate` proves the tool exists, not how it
   dispatches. Assert `tools.registry.registry.get_entry(<tool>).toolset` and `.is_async` against the
   real registry (plus `get_plugin_auxiliary_tasks()` for an aux key): an async handler registered
   with the wrong flag passes every manifest check and only fails when the model calls it.
