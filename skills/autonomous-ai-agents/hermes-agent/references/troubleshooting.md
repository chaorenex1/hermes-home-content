# Troubleshooting

### Voice not working
1. Check `stt.enabled: true` in config.yaml
2. Verify provider: `pip install faster-whisper` or set API key
3. In gateway: `/restart`. In CLI: exit and relaunch.

### Tool not available
1. `hermes tools` — check if toolset is enabled for your platform
2. Some tools need env vars (check `.env`)
3. `/reset` after enabling tools

### Model/provider issues
1. `hermes doctor` — check config and dependencies
2. `hermes auth` — re-authenticate OAuth providers (or `hermes auth add <provider>`)
3. Check `.env` has the right API key
4. **Copilot 403**: `gh auth login` tokens do NOT work for Copilot API. You must use the Copilot-specific OAuth device code flow via `hermes model` → GitHub Copilot.

### Changes not taking effect
- **Tools/skills:** `/reset` starts a new session with updated toolset
- **Config changes:** In gateway: `/restart`. In CLI: exit and relaunch.
- **Code changes:** Restart the CLI or gateway process
- **Gateway self-restart guard:** `hermes gateway stop/restart` is intentionally blocked when issued through the gateway's own terminal tool, because the command would kill its controlling process. Run the lifecycle command from an external OS shell and verify that `hermes gateway status` reports a new PID. For unattended Windows automation, use a temporary current-user Scheduled Task that runs the absolute `hermes.exe` path, then delete the task and script after the new PID is healthy; do not bypass the guard by killing the gateway PID directly.

### Skills not showing
1. `hermes skills list` — verify installed
2. `hermes skills config` — check platform enablement
3. Load explicitly: `hermes -s name` (or the skill's own `/<name>` slash command)

### Gateway issues
Check logs first:
```bash
grep -i "failed to send\|error" ~/.hermes/logs/gateway.log | tail -20
```

Common gateway problems:
- **Gateway dies on SSH logout**: Enable linger: `sudo loginctl enable-linger $USER`
- **Gateway dies on WSL2 close**: WSL2 requires `systemd=true` in `/etc/wsl.conf` for systemd services to work. Without it, gateway falls back to `nohup` (dies when session closes).
- **Gateway crash loop**: Reset the failed state: `systemctl --user reset-failed hermes-gateway`

#### Windows gateway health audit (messaging platforms)

Run in this order; each step answers a different question, and none of them alone proves the gateway works.

1. **Liveness:** `hermes gateway status --deep` — six probes must PASS (pid file, lock held by a live process, `get_running_pid()`, process exists, `gateway_state.json state='running'`, last lifecycle event `gateway.start`). Use `--deep`: the bare summary hides which signal is wrong. Then re-read `gateway.pid` after the command; `status` and `list` are read-only, but prove it rather than assuming.
2. **Event-loop liveness (catches a wedged process):** `$HERMES_HOME/state/gateway.heartbeat` is written off-loop every ~30s and carries `loop_tick_socket` / `loop_tick_tcp_port`. A heartbeat older than ~90s means the loop is frozen even though the PID is alive.
3. **Platform connectivity:** `grep "✓ .* connected" $HERMES_HOME/logs/gateway.log | tail`, then confirm sockets with `netstat -ano | grep <gateway-pid>`. Look for ESTABLISHED to foreign addresses (behind a TUN proxy the peer reads as `198.18.x.x`). Print the whole netstat slice — `head -10` cuts off the external sockets and makes a healthy gateway look silent.
4. **api_server:** unauthenticated `curl -s http://127.0.0.1:8642/health` returns `{"status":"ok"}`; `/v1/models` without `API_SERVER_KEY` returns 401 and logs a warning. That 401 is auth working, not a fault.
5. **End-to-end truth:** query `state.db` per source (`select id,title,last_activity_at,message_count from sessions where source='feishu' order by last_activity_at desc limit 3`). If the newest inbound session is weeks old, report "connected, not proven" — a live inbound message is the only end-to-end test, and sending one spams a real chat, so ask first.
6. **Restart forensics:** `Received UNKNOWN as a planned gateway stop — exiting cleanly` in gateway.log means deliberate stop (a `.gateway-planned-stop.json` marker names the target PID, TTL 60s), never a crash. Correlate `logs/gateway-exit-diag.log` (`gateway.exit_clean`) with `$HERMES_HOME/gateway-starts.log`; a ~20s stop→start gap is the `hermes gateway restart()` path (`restart()` waits for the old gateway and the port to clear). The stop marker does not record who asked: when the initiator is unidentifiable, state the mechanism and say the cause is unknown — do not invent one.
7. **Autostart audit:** `hermes gateway status --deep` prints Task script and Startup entry; `schtasks /Query /TN Hermes_Gateway /V /FO LIST` shows state. Last Result `267011` (SCHED_S_TASK_HAS_NOT_RUN) plus a Startup-folder `Hermes_Gateway.vbs` means the login item is the live path and the task is a redundant second registration — the singleton lock makes the loser exit, so the duplicate is harmless but worth reporting.
8. **State hygiene:** `gateway_state.json` can keep `"connected"` entries for platforms later disabled (discord/weixin) with months-old `updated_at`. Ignore them for health; they still mislead dashboards and the desktop UI.
9. **Expected noise:** Feishu logs `✗ feishu disconnect error after 0.00s: Event loop is closed` with a `ConnectionClosedOK` traceback on every stop, and `Clean EOF` warnings can appear mid-stream. Both are shutdown/stream noise; only a missing `✓ feishu connected` at startup means the adapter failed.

Process inspection on current Windows (no `wmic`):
```bash
powershell.exe -NoProfile -Command 'Get-CimInstance Win32_Process -Filter "ProcessId=<pid>" | ForEach-Object { "{0} ppid={1}" -f $_.ProcessId, $_.ParentProcessId }'
```
A gateway whose parent PID no longer exists is normal (detached launcher) — not a fault. Read `gateway_state.json` with `encoding='utf-8-sig'`; the BOM breaks plain `json.load`.

### Platform-specific issues
- **Discord bot silent**: Must enable **Message Content Intent** in Bot → Privileged Gateway Intents.
- **Slack bot only works in DMs**: Must subscribe to `message.channels` event. Without it, the bot ignores public channels.
- **Feishu `unexpected keyword argument 'extra_ua_tags'`**: the adapter is newer than the installed `lark-oapi` SDK. Check with `python -c "import inspect,lark_oapi.ws as ws; print(inspect.signature(ws.Client.__init__))"`. If the parameter is absent, install the source-declared pin (`python -m pip install --upgrade "lark-oapi==1.6.8"`) and run `hermes gateway restart`; verify the gateway log contains `✓ feishu connected`. Do not remove the argument as the first choice—Hermes uses the `channel` UA tag for group-event delivery.
- **Windows-specific issues** (`Alt+Enter` newline, WinError 10106, UTF-8 BOM config, line endings): see `references/windows-quirks.md`.

### Bug hunt from logs (separate code bugs from noise)

`$HERMES_HOME/logs/` holds `errors.log` (WARNING+ from every subsystem — look here first),
`gateway-stdio.log`, `mcp-stderr.log`, `tui_gateway_crash.log` (unhandled *thread* exceptions; these
never reach errors.log), `scratch-prune.log`, `gateway-starts.log`.

1. **Group, then read.** Run `python <skill dir>/scripts/triage_errors_log.py --day <YYYY-MM-DD>`.
   It splits `errors.log` into timestamp-delimited blocks, normalizes ids/hashes/counts into
   signatures, and prints per-day counts, the top signatures with first/last occurrence, and
   distinct traceback endings. Reading `tail` shows the loudest noise, not the recurring bug.
2. **Classify every hit before touching code**: code bug (reproduces with the process's real env),
   environment (missing optional module/binary, credentials), or provider noise (rate limits, clean
   EOF, adapter disconnect during shutdown). Only the first is yours to fix; report the other two as
   a class, don't silently drop them.
3. **Reproduce with the environment the code actually builds.** For checkpoints that means
   `GIT_DIR`/`GIT_WORK_TREE`/`GIT_INDEX_FILE` pointing at the shadow store; identical rc/stderr is
   the proof that you found the call site, not just a similar-looking line.
4. **Fix at the owning layer and pin it with a test** that fails before the fix. Then run the
   subsystem's existing suite — that is the regression net.
5. **Prove pre-existing failures are pre-existing**: clone the pristine checkout
   (`git clone --shared <checkout> <scratch>/baseline`) and run the same tests there. Never report an
   untouched test as a regression you caused; never wave away one you did.

Known signatures and what they mean:

- `tools.checkpoint_manager: Git command failed ... git add -A (rc=128) stderr=fatal: '<path>/.git'
  not recognized as a git repository` — the work tree contains a directory whose `.git` is not a
  usable repository (empty dir, dead gitfile); git aborts the whole stage, so every snapshot of that
  project fails silently and `/rollback` freezes. Stage with an exclusion
  (`git add -A -- . ':(exclude,literal)<path>'`), remember the path for the process, and delete the
  debris. `--ignore-errors` does not help.
- `<plugin logger>: ... UnscopedSecretError: Hermes could not read this profile's <VAR>` — a plugin
  spawned a bare `threading.Thread`; the thread starts with empty contextvars and loses the
  profile's HERMES_HOME override + secret scope. Spawn with
  `agent.memory_provider.spawn_context_thread` (details in `hermes-plugin-development`).
- `AttributeError: 'NoneType' object has no attribute 'execute'` from a plugin store during shutdown
  — `close()` ran while a worker thread was mid-job. Make `stop()` report whether the thread ended
  and skip the close while one is in flight.
- `model.context_length pins <model> at <N> but the provider advertises <M>; the pin wins` — config
  pin, not a bug; remove the pin to use the advertised window.
- `Error extracting content: 'str' object has no attribute 'get'` from `web_extract` — the provider
  serving `web.extract_backend` returned an envelope dict (`{"success", "data"}`) where
  `WebSearchProvider.extract()` must return a bare **list**; the dispatcher iterates the dict's keys.
  Fix the provider, not the tool (contract detail: `hermes-web-provider-plugin`). Confirm which
  backend is live from `web.extract_backend` in config.yaml before editing any provider.
- Isolating a plugin's own log lines: the loader names plugin packages
  `hermes_plugins.<category>__<dir>`, so `logging.getLogger(__name__)` inside the package logs under
  that prefix. Grep it to get the plugin's real warnings (rule-DB init, cookie-export fallbacks)
  without the `agent.tool_executor` envelopes that merely mention the plugin name — and remember a
  tool error there names the TOOL, which may belong to a different plugin than the one you are
  fixing (e.g. `camofox_backend_status` is the human-auth plugin, not camofox-search).

### Auxiliary models not working
If `auxiliary` tasks (vision, compression, session_search) fail silently, the `auto` provider can't find a backend. Either set `OPENROUTER_API_KEY` or `GOOGLE_API_KEY`, or explicitly configure each auxiliary task's provider:
```bash
hermes config set auxiliary.vision.provider <your_provider>
hermes config set auxiliary.vision.model <model_name>
```

### "Reset permissions" / auto-approving everything
See `references/security-privacy.md` — wipe the "Always allow" stores, don't touch yolo mode.

