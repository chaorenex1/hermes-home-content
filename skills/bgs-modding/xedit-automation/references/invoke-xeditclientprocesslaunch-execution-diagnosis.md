# Diagnosis: "Invoke-XeditClientProcessLaunch did not execute"

## Session context

- Date: 2026-07-02
- User symptom: xEdit processes visible in Task Manager but no window; user suspected `Invoke-XeditClientProcessLaunch` in `xedit-client.launch.ps1` was not running.
- Environment: tri-split MO2 — exe/plugins at `<PATH_TO_MO2_INSTALL>`, instance/profiles at `<PATH_TO_MO2_INSTANCE>`, game at `<PATH_TO_STEAM_LIBRARY>\steamapps\common\Skyrim Special Edition`.
- Profile: `pbr` (≈ 850 enabled plugins).

## Call chain (verified)

```
xedit_start (MCP tool)
  └─ xedit-mcp/dist/launch.js: kickoffLaunch() → launchDaemon()
      └─ spawn(pwsh, ["-File", "xedit-client.ps1", "process", "launch", ...])
          └─ xedit-client.ps1 switch 'process launch'
              └─ Invoke-XeditClientProcessLaunch
                  └─ builds runner='OpenCodeVfsLauncher' payload
                      └─ Invoke-XeditClientMo2LaunchStart
                          └─ MO2 control-plane launch.start
                              └─ mo2_agent_control.py: handle_launch_start
                                  └─ start_mo2_cli_launch
                                      └─ ModOrganizer.exe -p pbr -e xEdit64 -- <args>
```

## Evidence that it DID execute

1. Manual run of `xedit-client.ps1 process launch ...` printed:
   ```text
   [DEBUG] xEdit.exe -SSE -automation-serve -P:...plugins.txt
   ```
   This line is emitted from `Invoke-XeditClientProcessLaunch` line 452.
2. The function constructed the payload with `runner = 'OpenCodeVfsLauncher'` (source `xedit-client.launch.ps1:121`).
3. Control-plane bootstrap files existed under the expected path:
   ```text
   <PATH_TO_MO2_INSTALL>\plugins\Mo2AgentControl\bootstrap\runtime\{status,capabilities,endpoint}.json
   ```

## Why the user thought it did not execute

- xEdit appeared in Task Manager but had no visible window.
- The MCP `xedit_status` remained `starting` or returned `not_started`.
- Multiple `xEdit.exe` processes accumulated; those with `-automation-call-pid:` and `-automation-call-request:` are the **polling helper** (`Invoke-XeditClientAutomationCall`), not the daemon.

## Root cause of no window

`start_mo2_cli_launch` launches:

```text
ModOrganizer.exe -p pbr -e xEdit64 -- -SSE -automation-serve -P:...plugins.txt
```

Python's `subprocess.STARTUPINFO` only affects the `ModOrganizer.exe` window, not the xEdit child that MO2 CLI creates. If the registered `xEdit64` custom executable in MO2 has a hidden wrapper, batch launcher, or MO2 CLI itself suppresses the window, xEdit remains invisible.

## How to verify

Inspect session artifacts:

```text
%TEMP%\xedit-client-sessions\<guid>\
  mo2-launch-request.json   ← payload with runner, target, profile
  mo2-launch-response.json  ← control-plane response
  mo2-launch-state.json     ← spawned / running / failed
  mo2-launch-wrapper.ps1    ← only present for transport/direct-child path
  ready.request.json        ← automation-call polling evidence
```

## User constraint

User explicitly said: **"没有执行，不要触发轮询了"** ("It did not execute, do not trigger the polling"). This means:

- Do not repeatedly call `Invoke-XeditClientAutomationCall` / `automation call` to poll for readiness.
- The hidden 500ms polling process is the source of the perceived "xEdit pile-up".
- When diagnosing launch issues, prefer static inspection of the artifacts above and one manual `xedit-client.ps1 process launch` invocation over enabling the MCP polling loop.

## Resolution (2026-07-02)

After three fixes were applied, a manual `xedit-client.ps1 process launch`
test succeeded with full `[LAUNCH-LOG]` output:

```
[LAUNCH-LOG] calling Invoke-XeditClientMo2LaunchStart...
[LAUNCH-LOG] Invoke-XeditClientMo2LaunchStart returned. ok=True status=spawned pid=15308
[LAUNCH-LOG] skipping Wait-XeditClientAutomationReady (polling disabled by user request)
[LAUNCH-LOG] processId=15308 — xEdit should be visible now if launch succeeded
process launch
status: ok
mo2-launch-backend: mo2-cli
xedit-pid: 15308
```

Three fixes applied:
1. **Registration title** changed from `"xEdit64"` to `"xEdit-fork"` in
   `start_mo2_cli_launch` (both global source and MO2 plugin copy).
2. **Polling disabled**: `Wait-XeditClientAutomationReady` call removed
   from `Invoke-XeditClientProcessLaunch`, replaced with logging.
3. **`[LAUNCH-LOG]` instrumentation** added at every key step in
   `Invoke-XeditClientProcessLaunch` for future diagnosis.

**Remaining issue**: xEdit process exits immediately after launch (PID
no longer in tasklist). Root cause identified: the `-SSE` flag causes
SSEEdit 4.1.6r6 to exit immediately. Testing showed:
- No args → xEdit stays running ✅
- `-tSSE` → xEdit stays running ✅
- `-SSE` → xEdit exits immediately ❌

The `Get-XeditClientValidatedGameModeArgument` function maps `SkyrimSE` to
`-SSE`, which is passed as the first xEdit argument. This needs to be changed
to `-tSSE` or omitted for SSEEdit builds. See
`references/xedit-sse-vs-tsse-arg.md` for full test results.

## Related references

- `xedit-launch-pitfalls.md` — transport vs MO2 CLI vs organizer backend comparison.
- `windows-hidden-xedit-window-bug.md` — `CREATE_NO_WINDOW` and PowerShell `UseShellExecute` fixes.
- `split-layout-param-flow.md` — `--mo2-root` vs `--mo2-instance-root` divergence.
