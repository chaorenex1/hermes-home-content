---
name: hermes-web-provider-plugin
version: 1.1.0
description: "Use when building a Hermes web-search provider plugin."
author: Masia
license: MIT
metadata:
  hermes:
    tags: [hermes, plugins, web-search, camofox, provider]
    related_skills: [hermes-agent, authoring-hermes-skills, safe-extension-deployment]
---

# Building a Hermes web-search provider plugin

## When to Use

- Building or extending a Hermes plugin that services `web_search` / `web_extract`
  (a new backend provider, or changes to camofox-search / ai-search).
- Debugging why a configured web provider is not registered, not selected, or not loading.
- Needing plugin-side LLM calls (`ctx.llm`) or a child agent session (`ctx.subagent_lifecycle`) — see the `hermes-plugin-development` skill.

Reference implementations on this machine: `~/projects/camofox-search` (Camofox browser backend),
`~/projects/ai-search` (Crawl4AI backend). Full docs: hermes-agent repo
`website/docs/developer-guide/web-search-provider-plugin.md` + `.../plugins/index.md`.

## Repo layout that works

```
<repo>/
  plugin/<pkg>/                    # __init__.py (register), plugin.yaml, provider.py,
                                   # client.py, engines.py, settings.py
  scripts/install_dev_plugin.py    # copy installer -> $HERMES_HOME/plugins/web/<pkg>
  scripts/smoke_live.py            # live daemon smoke (run with Hermes venv python)
  tests/                           # offline pytest (conftest stubs agent.* outside Hermes)
  pyproject.toml                   # [project.entry-points."hermes_agent.plugins"]
```

## Contracts (verified against hermes-agent source)

- ABC: `agent.web_search_provider.WebSearchProvider` — implement `name`,
  `is_available()` (cheap, NO network — runs on every `hermes tools` paint),
  `supports_search()`/`supports_extract()`, `search()`/`extract()`, `get_setup_schema()`.
- Return shapes, and they are NOT the same. `search()` returns the legacy envelope
  `{"success": True, "data": {"web": [{title,url,description,position}]}}`, or
  `{"success": False, "error": str}` on failure. `extract()` returns a bare **list**
  `[{url,title,content,raw_content,metadata}, ...]` with `error` on a per-URL failure — never an
  envelope. `tools/web_tools_extract.py::_dispatch_extract` iterates the value directly, so an
  envelope makes it iterate the dict's KEYS and the whole call dies with `'str' object has no
  attribute 'get'`. `search`/`extract` may be `async def`.
- `agent/web_search_provider.py`'s MODULE docstring still describes the envelope for extract; that
  line is stale. The truth is the `extract()` method docstring, the bundled providers
  (`plugins/web/{tavily,exa,firecrawl,parallel,keenable,perplexity}` all annotate `-> list[dict]`),
  and the dispatcher that consumes the value.
- `plugin.yaml`: `kind: backend` + `provides_web_providers: [<provider-name>]`; manifest `name`
  like `web-<slug>`; `requires_env` drives `hermes plugins install` prompts.
- User plugin dirs: `$HERMES_HOME/plugins/<category>/<dir>/` → loader key `<category>/<dir>`, module
  namespace `hermes_plugins.<cat>__<dir>` (`/`→`__`, `-`→`_`). USE RELATIVE IMPORTS in the package.
- User plugins are opt-in: `hermes plugins enable web/<dir>`; bundled backends auto-load.
- Install: copy to `$HERMES_HOME/plugins/web/<dir>` → `hermes plugins enable web/<dir>`. The enable
  soft-reloads a running Gateway (tools/skills land in the NEXT session) but re-imports no provider
  code — a changed `provider.py` takes effect only after a gateway restart (deploy sequence below).
  Validate with `hermes plugins validate <plugin_dir>` (runs register() in isolation).
- Config/env: resolve via `hermes_cli.config.get_env_value` (secret-scope aware) then
  `os.environ`; re-raise `UnscopedSecretError` instead of falling back across profiles.
- Live smoke needs the Hermes venv python (that python can import `agent.*`).

## camofox REST (live-verified camofox-browser 2.4.8, engine camoufox)

- Auth: `Authorization: Bearer <CAMOFOX_API_KEY>` (Hermes `.env`); base `CAMOFOX_URL`,
  default `http://localhost:9377`. Container: `docker start camofox-browser`.
- `POST /tabs {userId, sessionKey, url}` → `{tabId}` — `sessionKey` is REQUIRED here
  (core `tools/browser_camofox.py` sends `listItemId`; the daemon version rejects less).
- `POST /tabs/{id}/evaluate {userId, expression}` → `{ok, result, resultType, truncated}`;
  normalize `result` (decoded JSON on 2.4.8, JSON string on other versions).
- `DELETE /sessions/{userId}` closes the browser context and clears the daemon's in-memory
  per-user state; the on-disk profile dir (and its cookies) PERSISTS — it is not a wipe.
- Bing SERP (cn.bing verified): `#b_results > li.b_algo`, `h2 a`, `.b_caption p`.
- Tab creation rejects non-http(s) URLs (`Blocked URL scheme: about:`); blank tabs must OMIT `url`.

## Plugin-owned profile + cookies (verified on camofox-browser 2.4.8 / Edge 155)

- Browse with ONE stable userId (`CAMOFOX_SEARCH_USER_ID`, default `camofox_search`): a cookie
  import only reaches sessions of the SAME userId, so per-call random userIds silently discard
  every import. Per call: open a work tab → do the work → close only that tab.
- Camoufox destroys its browser WINDOW when a context's last tab closes; every later
  `Browser.newPage` then fails (500, `delayedStartupPromise, window is null`). Keep one idle
  blank HOLDER tab in the profile, and heal a broken context once: close session → ensure
  holder → retry the tab create. A live smoke that opens/closes tabs repeatedly is the probe
  for this — a single-tab check will not catch it.
- Cookie endpoints: `POST /sessions/{userId}/cookies {cookies, tabId?}` (Playwright format;
  each cookie needs name+value+domain; max 500 per request; needs a live tab — passing `tabId`
  skips the canonical-profile checks) and `GET /tabs/{tabId}/cookies?userId=` for round-trip
  verification. Tool output carries counts only — never cookie values.
- Reading the USER's own browser cookies (Windows): a running Chromium-family browser holds its
  Cookies DB locked (persistent WinError 32, retries do not help). Fall back to a CDP export
  from a browser started with `--remote-debugging-port` (probe a configurable port list), and
  report what to close/restart — never kill the user's browser. Chromium values: DPAPI key from
  `Local State` + AES-GCM, and modern builds prepend a 32-byte binding prefix to the plaintext
  (strip it); app-bound `v20` is undecryptable — skip. Firefox `cookies.sqlite` is plaintext.
- Depth — session/profile model, exact decrypt formats, CDP recipe, scheduled-job pattern,
  testing recipe: `references/camofox-profile-and-cookies.md`.

## Provider plugin + agent tool + bundled skill (one plugin, three surfaces)

A web-provider plugin can also register agent tools and a bundled skill (proven in camofox-search v0.2):

- `ctx.register_tool(name, toolset, schema, handler, emoji=...)`: handler signature `handler(args, **kwargs)`
  must return a JSON **string** (the registry rejects plain dicts; only the multimodal envelope passes).
- The manifest must declare the tool: `provides_tools: [<name>]` — otherwise
  `hermes plugins validate` fails with "undeclared tools registered (not in provides_tools)".
- `ctx.register_skill(<name>, Path(SKILL.md), description=..., frontmatter=...)`: read-only, resolvable
  as `<manifest name>:<skill>` (load with `skill_view`), listed in `<available_skills>` while enabled;
  no manifest field needed. **Pass the parsed frontmatter explicitly**: the `<available_skills>` row
  comes from register-time metadata (`list_plugin_skill_metadata`), NOT from re-reading the file — a
  skill registered bare shows an empty description and no future agent can see its triggers. Parse
  SKILL.md in `register()` with a small self-contained `key: value` + block-scalar parser; do NOT
  import `agent.skill_utils` or other agent internals for it (`hermes plugins validate` flags private
  core imports, and those seams move between releases).
- Bundled skill conventions (user preference): write SKILL.md in ENGLISH — committed artifacts are
  English-first even when the session language is Chinese — and put the trigger conditions in the
  frontmatter `description`, since that text is all a future agent sees in the skills index before
  deciding to load it.
- Per-plugin SQLite store: resolve data dir from `hermes_constants.get_hermes_home()` (profile-aware;
  fall back to `HERMES_HOME` env → platform default for standalone/tests), open connections with
  `PRAGMA journal_mode=WAL` + `busy_timeout`, and catch store errors in the provider so search/extract
  degrade to built-ins instead of failing.
- Verify Hermes-side without pytest: `hermes plugins validate <plugin_dir>` (runs `register()` with a real
  ctx — catches undeclared tools, collisions, import errors) and `hermes plugins doctor <plugin_dir>`
  (discovery + import + registration in a temp HERMES_HOME). The Hermes venv ships no pytest: run the
  repo suite under the repo venv (`PYTHONPATH=<hermes-agent repo>` to exercise the real ABC), and run a
  small probe script with the Hermes venv python for runtime checks.

## Deploy to the live Hermes home and prove it (verified sequence)

Treat "deploy the plugin" as full activation, not a file copy: install, enable, live smoke,
backend switch, evidence, revert path.

1. Install the copy from the repo venv python:
   `scripts/install_dev_plugin.py --target-hermes-home "$HERMES_HOME"` (dry-run first; `--replace`
   when a copy exists — it backs up and hash-verifies).
2. `hermes plugins enable web/<dir>` — output confirms enablement plus
   `Gateway reloaded plugins — deferred: tools (next session)`. The first enable's soft reload
   re-registers tools/skills metadata; it does NOT re-import provider code, so a changed
   `provider.py` reaches the live gateway only after a restart.
   - `hermes gateway restart` WORKS from an external CLI session: it drains, starts a new PID and
     the platforms reconnect. Verify `hermes gateway status` reports the new PID and `gateway.log`
     shows `✓ <platform> connected`; a transient `127.0.0.1:8642 still accepting connections`
     warning is the old socket draining, not a fault.
   - It is refused only when the shell IS inside the gateway's own process tree (a gateway-hosted
     session driving the terminal tool) — there, use the control-socket reload (step 8).
   - Ship the fix with a `plugin.yaml` + `pyproject.toml` version bump in the same commit, so the
     installed copy is identifiable against a later `--replace`.
3. Prove the LIVE gateway loaded it:
   `grep -i "<plugin-dir>" "$HERMES_HOME/logs/agent.log"` — expect
   `Registered web provider '<name>'`, `registered tool: ...`, `registered skill: ...` lines.
4. Live smoke with the Hermes venv python against the real daemon — this is also what creates the
   real data dir / rule DB for the first time.
5. Point the profile at the provider: `hermes config set web.search_backend <name>` and
   `web.extract_backend <name>`. Selection re-reads config per call, so no restart is needed.
6. Prove selection with a probe under the Hermes venv python:
   `discover_plugins()` → `agent.web_search_registry._configured_backend("search")` →
   `_resolve(configured, capability="search").name` (same for `"extract"`).
7. A configured backend may be DANGLING: `web.search_backend` can name a plugin installed only in
   a different profile and resolution falls back silently. Check `hermes plugins list --plain`
   before believing a configured value is active; switch it only when it is broken or the user asked.
8. Updating an already-enabled plugin: `hermes plugins enable web/<dir>` on an enabled plugin is a
   NO-OP — it does not reload the gateway, so changed skill registration metadata (name/description)
   stays stale in the running process. Force the reload over the gateway control socket (Hermes venv
   python): `from gateway.control_socket import reload_gateway_plugins;
   reload_gateway_plugins(Path("<hermes home>"))` → `{reloaded: True, plugins: [...],
   adapters_rewired: N}`. Skill FILE content is path-served (a deployed SKILL.md edit is live on the
   next `skill_view`) — only registration metadata needs the reload.
9. Verifying a just-deployed tool: a `hermes chat -q` spawned from the agent shell routes through the
   RUNNING gateway (platform=local) and reflects its IN-MEMORY plugin state — before the reload
   lands it reports "'<tool>' is not a known tool name" even though the disk copy is new. Verify the
   on-disk copy in a fresh python instead: `discover_plugins()` then
   `model_tools.get_tool_definitions(skip_tool_search_assembly=True)` and check the tool names; then
   reload over the control socket and re-run `hermes chat -q` to prove the live path.
10. After installing a provider fix, prove the INSTALLED copy, not the repo: load it as a synthetic
    package (`spec_from_file_location(name, <installed>/__init__.py, submodule_search_locations=[<installed>])`)
    and run the host dispatcher against it with a stubbed client. Then run the installer's backup
    copy through the same probe — the old tree must reproduce the logged failure and the new one
    must return entries. That A/B is the only causal proof that the deployed bytes changed behaviour.

## Pitfalls

- Parallel work from a provider MUST run worker threads inside a copy of the caller's context:
  the gateway's per-turn secret scope (`agent.secret_scope._SECRET_SCOPE`) is a `ContextVar` that
  fresh threads do NOT inherit, and `get_env_value` on a multiplexed gateway FAILS CLOSED for any
  env read in an unscoped thread (`UnscopedSecretError` — "could not read this profile's
  <VAR> ... Run `hermes gateway restart`"). The web_search call then errors and Hermes silently
  rescues it with a keyless fallback (`served_by`/`rescued_from` in the response) — broken, but
  it looks like a result. Pattern: `context = contextvars.copy_context()` once, then
  `pool.submit(context.copy().run, fn, ...)` per task — each task needs its OWN copy (a shared
  Context cannot be entered concurrently). Regression-test by setting a probe ContextVar before
  `search()` and asserting it inside the worker.
- A provider's own test suite asserts whatever shape its author assumed, so it cannot catch a
  contract mismatch — a green suite says nothing about the host. Verify every provider return value
  against the real dispatcher with a stubbed client:
  `asyncio.run(_dispatch_extract(Provider(), ["https://example.com/"], None))` must return a list
  of entries and must not raise; do the same for `_memoized_search`'s envelope expectations.
- After deploying/reloading a provider plugin, verify the LIVE gateway path with a real
  `web_search` call and read the envelope: a `served_by`/`rescued_from`/`backend_error` rescue is
  a FAILED call even though results come back. Direct probe scripts (Hermes venv python, no
  gateway) never exercise the multiplex scope, so scope bugs surface only through the gateway.
- Write `.gitignore` FIRST. For any full-file rewrite go straight to `rm` + `write_file`: the
  stale-read guard blocks `write_file` on an existing file even after a fresh full read (a single
  earlier paginated read poisons it) and re-reading does not reliably clear it.
- Tests must pass outside Hermes: conftest installs a stub `agent.web_search_provider`
  when the real runtime isn't importable. Run `compileall` under BOTH pythons
  (Hermes venv 3.14 + repo venv).
- Clamp `limit` with try/except `max(1, min(int(limit), 20))`; `limit or 5` turns 0 into 5.
- Repo venv: `uv venv && uv pip install -p .venv/Scripts/python.exe pytest requests`;
  tests: `.venv/Scripts/python.exe -m pytest`.
- After a live smoke, check tabs PER USER: `GET /tabs?userId=<user>` — the unfiltered
  `GET /tabs` misleadingly returns `[]` and hides everything. The plugin's stable profile
  should show exactly one idle blank holder tab and no leftover work tabs.
