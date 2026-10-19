---
name: cdp-browser-automation
description: "CDP browser automation, cookie import, Windows lifecycle."
version: 1.0.0
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [cdp, browser, automation, windows, anti-detection, profiles]
---

# CDP Browser Automation

## Overview

Class-level workflow for Chrome DevTools Protocol automation: choose the right browser/profile mode, establish a verified CDP connection, operate through bounded DOM and input actions, preserve login state when authorized, simulate realistic timing when a site requires it, and manage browser processes safely on Windows/MSYS.

Prefer static fetch/search tools for public non-interactive pages. Use CDP for JavaScript-rendered content, authenticated sessions, live UI inspection, or interactions that require a real browser.

## Hermes Current-Browser Route

For this user's browser tasks, default to the `system-browser` route when the requested target is the user's current browser window:

- Call `browser_tabs(action="list")` first to discover the bound session, stable tab IDs, and original active tab.
- Use `browser_eval` with an explicit `tab_id` for target-scoped CDP reads or page actions.
- Do not infer that `browser_navigate`, `browser_snapshot`, `browser_click`, or similarly named generic browser tools are isolated. Their ownership must be proved independently; a shared or different `browser` prefix, launch metadata, and a success flag are not sufficient. Use the ownership canary in `references/browser-toolset-smoke-tests.md` before treating them as disposable.
- For smoke tests, validate `list`, target-scoped evaluation, and reversible `open`/`switch`/`close`; close only the temporary test tab and switch back to the original active tab before returning.
- Never close borrowed or user-owned tabs. Preserve the user's original tabs and active-tab state unless the task explicitly requires changing them.

Verification evidence should include the returned `session_id`, exact `tab_id`, `method: target_cdp` from evaluation, and a final tab listing showing that the temporary tab is gone and the original active tab is restored.

If the Hermes extension action shows `ON` but `browser_tabs` reports that the native extension is not connected, inspect the profile-local rendezvous port and native-host process lineage before reloading the extension. A native host left alive after its previous broker disappeared can keep the MV3 service worker's `nativePort` non-null and prevent reconnection. Confirm the stale chain has no TCP connection to the current rendezvous listener, terminate only that native-host launcher chain, and verify Edge spawns a new host with an `ESTABLISHED` loopback connection to the current broker. Do not kill Edge or Gateway merely to clear the stale host. If takeover then reports `Current browser window has no claimable web tabs`, connection is healthy; the active window contains only protected/internal pages, so use a normal `http:`, `https:`, or `about:blank` tab before retrying.

If the claim instead fails with `Current browser window contains a tab owned by another Hermes task`, another task owns the window: do not retry the system-browser tools. Start an isolated CDP instance (dedicated `--user-data-dir`, e.g. `<PATH_TO_BROWSER_PROFILE>`, port 9222 — see `scripts/start-cdp-edge.py`), verify `http://127.0.0.1:9222/json/version`, and drive it with a self-contained Node CDP script.

If the claim fails with `Current browser window has too many claimable tabs`, the window has more http(s) tabs than `browser.system_browser.max_tabs_per_session` (default 20): raise that config key (≤100) and restart the shared-runtime daemon. Never kill the shared-runtime daemon while the gateway is up — the gateway client cannot reconnect (see the Shared Runtime Failures section).

## Mode Selection

| Need | Mode |
|---|---|
| Anonymous repeatable test | isolated `--user-data-dir`, optionally headless |
| Existing login state | visible browser with the authorized real profile |
| Strong anti-automation controls | visible browser, realistic viewport/UA, bounded randomized timing and input |
| Hermes/Electron UI inspection | attach to the app's declared dev CDP port; never relaunch the user's app merely to obtain a port |

Using a real profile can interfere with the user's daily browser. Confirm scope, avoid broad process termination, and prefer an isolated profile unless login state is genuinely required.

**Debug-port launches against real profiles (Edge/Chrome ≥136) are not viable and not safe**: the browser refuses `--remote-debugging-port` on the default user-data-dir (`DevTools remote debugging requires a non-default data directory`), and a junction/copy workaround silently disables App-Bound Encryption, after which the browser purges the profile's app-bound (`v20`) cookies because it can no longer decrypt them — irreversible without a prior copy of the Cookies DB. Use an isolated profile and log in there; if a real profile's cookie store must power automation, back it up first (full mechanism + recovery recipe: `references/chromium-app-bound-cookie-encryption.md`; import and login-verification procedure: `references/cookie-import-and-login-verification.md`).

## Core Workflow

1. Identify browser executable, profile mode, CDP port, target site, and whether login state is authorized.
2. Check whether the port is already owned before launch.
3. Start the browser through the host process tool, not shell `&`; use explicit arguments and a separate profile when isolation matters.
4. Verify `http://127.0.0.1:<port>/json/version`, discover the intended page target, and attach to that target rather than the first target returned.
5. Enable only required CDP domains, navigate, wait for a real load/DOM condition with a timeout, and project page data into small JSON values instead of dumping the DOM.
6. For interaction, prefer stable selectors and element geometry. Add curved mouse movement, realistic press duration, incremental scrolling, and randomized pauses only when needed; randomness is not a substitute for correct selectors or load conditions.
7. Verify the intended page state after every consequential action.
8. Close only targets/processes proven to belong to this run. Treat `TIME_WAIT` as normal and do not kill unrelated browser trees.

## Human-Like Interaction

Realistic automation should preserve variability without becoming nondeterministic: use the browser's genuine viewport and user agent; move through intermediate coordinates; pause briefly around clicks; scroll in bounded increments; wait on semantic conditions, then add small jitter; bound retries and runtime; and never claim these patterns guarantee bypass of anti-bot controls.

## Robust CSS Selector Generation

When a dynamic SPA uses generated CSS-in-JS classes, treat those classes as current-page evidence, not a durable selector contract. Prefer stable root IDs, landmark tags, direct-child structure, and semantic attributes. Generate the narrowest selector that both matches exactly once and resolves to the already-identified target node; uniqueness without identity verification is insufficient. For selectors expected to work across content shapes, validate at least two representative routes or queries. Use structural `:has(...)` selectors where supported and DOM filtering where they are not; do not silently downgrade to volatile hashes or positional `nth-of-type()` selectors. Clean up any temporary validation tabs and restore the original active tab.

See `references/robust-css-selector-generation.md` for the verified generation algorithm, compatibility fallback, pitfalls, and a WolframAlpha example.

## Bulk Capture Behind Anti-Bot Gates

Cloudflare-style interstitials (`Just a moment...` / `请稍候…`, HTTP 403 for plain fetchers) need a real visible browser and usually clear in 5–20 s. Wait by polling `document.title` plus `readyState !== 'loading'` until the title no longer matches the challenge — never a fixed sleep, and never a retry loop of plain HTTP fetches.

After clearance, capture same-origin sub-pages with `fetch(url, {credentials:'include'})` inside that already-cleared page context: batch many URLs per CDP call (≈4 workers), return small result arrays, and write files in Node; resume by skipping files that already exist. Raise the WebSocket `maxPayload` for multi-hundred-KB pages, and abort a batch loop when a round produces no new files. Discover sub-page URL schemes from the site's own navigation code (`loadfile('...')`, routers, `querySelectorAll('a')`) instead of guessing; when content renders in an iframe, fetch the fragment URL directly — fragments are usually complete HTML documents.

Recipe and runnable script: `references/bulk-page-capture.md`, `scripts/cdp-batch-fetch.js`.

## Windows/MSYS Branch

- Invoke Windows utilities through `cmd.exe //c` when slash-prefixed flags would be path-converted.
- Use MSYS paths or carefully quoted native paths for executables containing spaces.
- Launch long-lived browser processes with `terminal(background=true)`; never append `&`.
- Prefer direct commands or ASCII-only `.bat` files; UTF-8 batch files can be misparsed by `cmd.exe`.
- Use `sleep` in bash; avoid confusing GNU `timeout` with Windows `timeout /t`.
- Identify a port-owning PID and command line before termination. Ignore `TIME_WAIT`.

## Login-State Safety

Treat cookies and sessions as credentials: do not export or print them, navigate to unrelated private pages, or modify the user's profile unnecessarily. Login detection needs site-specific positive evidence; generic selectors are too weak for security-sensitive conclusions.

## Authenticated Search Profile and Cookie Import (camofox-search)

When `web_search`/`web_extract`/camofox queries stop carrying the user's logins, or an import reports 0 cookies or all-undecryptable rows, use this branch. Recipe: `references/cookie-import-and-login-verification.md`; encryption mechanics and store recovery: `references/chromium-app-bound-cookie-encryption.md`; read-only probe: `scripts/camofox-login-state-check.py`.

1. Back up the source `Cookies` DB (+ `-wal`/`-shm`) before any experiment; it is the only path back if the store is purged.
2. Never debug-launch the real profile — a non-default data dir kills App-Bound Encryption and purges `v20` cookies.
3. Diagnose by value prefix (`substr(encrypted_value,1,3)`): `v10`/`v11` decrypt in user mode; all-`v20` means ABE, so use the rookie-cookies injection export with the browser closed or a Firefox source — do not retry the file export.
4. Require `verified: true`, then independently probe login state; an auth cookie absent on a domain that has other rows means the SOURCE was logged out there, not that the import failed.
5. Keep import batches under 500 cookies AND 64 KiB of wire bytes — the daemon rejects larger JSON bodies.
6. A `403 Check CAMOFOX_API_KEY` from a hand-run sync usually means `PYTHONPATH=<HERMES_HOME>/hermes-agent` was missing (the key silently resolved empty), not a bad key.

## Camofox Browser Server Container Lifecycle

The self-hosted Camofox server (`camofox-browser`, API on 9377) is the backend camofox-search's `web_search`/`web_extract` call. It has a built-in idle-exit lifecycle: idle cleanup closes tabs after `CAMOFOX_IDLE_TIMEOUT_MS` (default 30 min), then the process calls `gracefulShutdown('IDLE_TIMEOUT')` once another `CAMOFOX_IDLE_EXIT_TIMEOUT_MS` (defaults to the same value) passes with no activity. An unused server therefore exits cleanly after about 60 min: exit code 0, `RestartPolicy: no`, `docker logs` ending in `idle exit started` / `shutting down signal=IDLE_TIMEOUT`. Compare `.State.StartedAt` / `.FinishedAt` before suspecting a crash, and read the shipped compiled source (`docker run --rm --entrypoint sh IMG -c "grep -rn IDLE /app/dist"`) when the exit reason is not in the logs.

Rules for keeping it resident:

- `CAMOFOX_IDLE_EXIT_TIMEOUT_MS` must be a large positive value (e.g. `31536000000`). `0` and negative values do not disable the exit: the parser falls back to the default.
- Environment is fixed when the container is created, so `docker update` cannot add it. Clone every run parameter from `docker inspect` (entrypoint, cmd, user, workdir, port bindings, mounts, existing env) into a new container, using `scripts/recreate-docker-container.py` so the API key is copied in memory and never printed or written to a file.
- Add `--restart unless-stopped`: the service then survives Docker restarts, while an explicit `docker stop` still stops it.
- Rename the old container to `<name>.bak` and keep it until the replacement is verified; that is the rollback. Remove it once verified.
- Idle cleanup still runs with the exit disabled: tabs and empty sessions close after `CAMOFOX_IDLE_TIMEOUT_MS`, so raise `CAMOFOX_SESSION_TIMEOUT` / `CAMOFOX_IDLE_TIMEOUT_MS` when sessions must outlive that.

Verification, all three required:

1. Inside the new container, `docker exec <name> node -e "console.log(require('./dist/src/utils/config').loadConfig().idleExitTimeoutMs)"` (workdir `/app`) reports the new value.
2. `GET http://127.0.0.1:9377/health` with `Authorization: Bearer <CAMOFOX_API_KEY>` returns `{"ok":true,...}`.
3. One real `web_search` reaches the server: `docker logs` shows `/tabs/.../evaluate` with `userId=camofox_search`.

`camofox_backend_status` reports the human-auth plugin's own endpoint (the VNC deployment, 9378/6089 by default), which is separate from this server. `ready: false` there says nothing about the 9377 search backend. `camofox_auth_open` drives that human-auth deployment under its own `user_id=hermes` profile, so a login completed there does not authenticate a `browser_navigate` session — log in through the page in the browsing profile (`browser_vault` save_login/fill) or pin that profile's `user_id` instead.

## Built-in browser_* Route (remote camofox page)

When the job is site automation rather than "drive the user's current tab", the generic `browser_navigate` / `browser_snapshot` / `browser_click` / `browser_type` / `browser_console` family drives the camofox browser (container API on 9377). Treat it as a remote, normally headless browser: state lives under `~/.camofox/profiles/<userId>`, and without a pinned `browser.camofox.user_id` a new session gets a new `hermes_<hash>` profile, so login does not survive session boundaries. State that plainly instead of promising a remembered login.

Pin the profile when logins must persist: `hermes config set browser.camofox.user_id <id>`, read back with `hermes config get browser.camofox.user_id`; every session then reuses `~/.camofox/profiles/<id>`. Verify the identity actually in use instead of trusting the file — `docker logs <container> | grep -o '"userId": *"[^"]*"'` shows the userId of the requests being served. Choose an id deliberately: the camofox-search backend runs its own tabs under `camofox_search`, so pinning to it inherits that profile's logins for free, at the cost that a camofox-search restart closes your tabs (recover by re-navigating, the profile itself survives).

- **Extract, don't scrape.** `browser_console` returns one JSON-serializable value from a self-contained IIFE. Use it for data; use `browser_snapshot` only to find refs and understand structure. Snapshot text loses fields and burns context.
- **Wait inside the page.** `browser_console` awaits a returned Promise, so poll in-page (`setTimeout`, ~300 ms) until the target container exists; cap at ~25 s against the 30 s `browser.command_timeout`. A shell sleep either fires before hydration or wastes a fixed block of time on every page.
- **Click by ref, re-snapshot each time.** Navigation, AJAX refresh, and accordion toggles rebuild the DOM and invalidate refs. Refs resolve through shadow roots, which is the only reliable way to hit a web-component control page JS cannot `querySelector`; `el.click()` on such a control silently does nothing.
- **Scope selectors to the region.** Hidden login modals and cookie banners put decoy `h1` / `input` / `button` nodes first in the document; anchor on the page container (e.g. `#pagetitle h1`) or a `data-*` / `data-e2eid` attribute.
- **Prove auth with a request, not with chrome.** `fetch('/<account-endpoint>', {redirect:'manual', credentials:'include'})` then read `status` (401 anonymous / 200 authenticated). Guest shells often render the account menu, an avatar, and even a hidden "please log in" heading, so selector checks report logged-in for anonymous sessions.
- **Verify writes by reloading.** A click's success flag means a pointer event was delivered, nothing more: navigate back to the same URL and re-run the state expression before claiming the action landed.
- **Downloads land on a mounted host dir, not inside the container.** Camofox's `downloadsDir` is `$CAMOFOX_DOWNLOADS_DIR` or `~/.camofox/downloads`, and `~/.camofox` is bind-mounted into the container, so a finished download appears directly in the host's `~/.camofox/downloads` — `docker cp` is not needed. `/home/node/Downloads` is the browser's default dir on the container overlay and stays empty; do not look there. Confirm with `ls -lt "$HOME/.camofox/downloads"` or `GET http://127.0.0.1:9377/users/<userId>/downloads`. Sites rewrite filenames, so read the actual on-disk name.

Before trusting this route with the user's session, prove it is not driving their window — use the ownership canary below.

## Browser Toolset Smoke Tests

Prove browser ownership before exercising capabilities; tool-name families and apparent launch metadata are not ownership evidence:

- If the request refers to the user's current browser window, use the `system-browser` route. Prove the binding with `browser_tabs`, evaluate exact stable tab IDs with `browser_eval`, and perform only reversible temporary-tab operations. Restore the original active tab.
- If the request explicitly calls for an anonymous or disposable browser, require positive isolation evidence before navigation or input. Record current system-browser target IDs, URLs, and the original active tab; then use the ownership canary in `references/browser-toolset-smoke-tests.md`. A generic browser snapshot whose top `frame_id` equals a borrowed system-browser `target_id`, or a navigation that changes any borrowed tab, proves shared-target operation rather than isolation.
- When isolation is not proven, classify capability behavior separately from ownership: `navigate/type/click/vision` may function correctly while the isolation contract fails. Stop using borrowed pages as fixtures, restore any changed URL with the least destructive reversible action, close only run-owned tabs, restore the original active tab, and report the ownership mismatch without turning it into a permanent claim that the tool family is broken.

Follow `references/browser-toolset-smoke-tests.md` for both route-specific matrices, the ownership canary, and cleanup evidence. Always verify state directly rather than trusting success flags. Retry a failing capability once only with a materially different fixture, input, or verification method; if the same deterministic internal error remains, report that capability as isolated and stop without generalizing it to the whole toolset.

## System-Browser Shared Runtime Failures (Windows/Hermes plugin)

All browser tools in this setup (browser_tabs/browser_eval AND generic browser_navigate/snapshot/click via the plugin's pre_tool_call hook) route through ONE gateway-side plugin client to a shared-runtime daemon (line-JSON over 127.0.0.1; state in `<hermes>/system-browser/shared-runtime/runtime.json`).

- The daemon exits when its last client releases. The gateway client stays attached for the gateway's lifetime, so a normal gateway restart re-spawns/re-attaches cleanly.
- CRITICAL: the client has NO reconnect-on-error. If the daemon dies while the gateway client still holds its socket, every subsequent browser tool call fails deterministically with ConnectionResetError ([WinError 10054]) and no new daemon spawns. Recovery = restart the gateway (a fresh client); the gateway hosts the live agent turn, so never kill it mid-turn.
- Daemon config read: `_read_active_config` imports hermes_cli + ruamel.yaml. The tools-python used by the gateway service LACKS ruamel, so a daemon spawned with it silently falls back to DEFAULTS (max_tabs_per_session=20). Spawn the daemon with the install venv python (`…\hermes\installs\<id>\environments\<id>\venv\Scripts\python.exe`) which reads config.yaml correctly.
- Tab claim cap: `Target.claimCurrentWindow` maxTabs = min(max_tabs_per_session (default 20), max_total_tabs - tabs in existing session manifests). A window with more claimable http(s) tabs fails with "too many claimable tabs"; raise `browser.system_browser.max_tabs_per_session` in config.yaml (max 100) and restart the daemon. Dead session manifests under `system-browser/sessions/` consume the budget — back them up, then delete.
- Edge extension reconnect: the extension retries connectNative via chrome.alarms `delayInMinutes: 1`, so after a broker restart it can take up to ~60s to reconnect; a 30s startup wait is too short. Keep the daemon+broker alive (an attached keeper client) for 1–2+ min.
- Borrowed tabs are always released (Target.releaseTarget), never closed — claiming the user's window is non-destructive; only Hermes-created tabs are closed on session end.
- Recovery choreography that works: (1) start a daemon via venv python and hold it with a keeper client attached; (2) wait ≥1–2 min for the extension alarm to reconnect; (3) verify a claim (ensure_session→list_tabs) directly via the same shared_runtime classes; (4) restart ONLY the gateway — schedule it OS-side (schtasks one-shot .cmd) so it survives the dying gateway process tree; the fresh gateway client attaches to the live daemon; (5) keeper releases after seeing a second client (`runtime_client_attached clients=2` in runtime.log).

## Verification Checklist

- [ ] Correct browser, profile, port, and page target identified.
- [ ] CDP endpoint answered and intended target was selected.
- [ ] Navigation and interaction used bounded waits/retries.
- [ ] Consequential actions were verified from resulting state.
- [ ] No cookies, tokens, or private DOM dumps were exposed.
- [ ] Cleanup affected only run-owned targets/processes.

## Support Files

- `references/browser-toolset-smoke-tests.md` — capability matrix, deterministic fixtures, and direct verification evidence for browser toolset checks.
- `references/cdp-browser-windows.md` — comprehensive Windows/profile/lifecycle guide.
- `references/human-behavior.md` and `references/human-like-automation.md` — interaction and anti-detection recipes.
- `references/windows-workarounds.md` — MSYS, encoding, and process pitfalls.
- `references/bulk-page-capture.md` — Cloudflare-gated bulk capture: challenge polling, in-page `fetch` batching, resumable runs.
- `references/cookie-import-and-login-verification.md` — camofox-search cookie import, ABE handling, batched import, and login-state verification.
- `references/chromium-app-bound-cookie-encryption.md` — `v10`/`v20` formats, debug-port walls, fork test, and store-purge recovery.
- `scripts/cdp-batch-fetch.js` — resumable bulk fetcher for a URL list over CDP (same-origin `fetch`).
- `scripts/camofox-login-state-check.py` — read-only store-summary plus live login probes for the camofox-search profile.
- `scripts/recreate-docker-container.py` — clone a container's run config with extra env (e.g. keep the Camofox server from idle-exiting) and a restart policy; secrets never printed.
