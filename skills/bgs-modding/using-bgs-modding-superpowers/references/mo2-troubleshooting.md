# MO2 + xEdit Environment Troubleshooting

Common environment failures encountered during BGS modding sessions and their fixes.

## Split-Layout MO2 Binding

**Symptom**: `mo2_session({ mo2Root })` fails with `ENOENT: no such file or directory, open '<path>\ModOrganizer.ini'`

**Root cause**: MO2 global instance stores `ModOrganizer.ini` in `%LOCALAPPDATA%\ModOrganizer\<instance_name>\` while `base_directory` (where profiles/mods/downloads live) is elsewhere.

**Diagnosis**:
```bash
find "C:/Users/<user>/AppData/Local/ModOrganizer" -name "ModOrganizer.ini"
```
Look for the instance name matching your setup. Read the ini to find `base_directory` under `[Settings]`.

**Fix**: Copy `ModOrganizer.ini` from the global instance directory to the `base_directory`:
```bash
cp "C:/Users/<user>/AppData/Local/ModOrganizer/<instance>/ModOrganizer.ini" "<base_directory>/ModOrganizer.ini"
```
Then bind with `mo2Root` set to the `base_directory` path.

## Dual Control Plane Plugin Conflict

**Symptom**: MO2 broker shows `pipeConnected: false` but MO2 process is running. Named-pipe endpoint returns empty responses. Old trigger-file IPC (`bgs_mo2_control.py` v1.3.0) shows dialog boxes with "ignored" result in `blocker-events.jsonl`.

**Root cause**: Both `bgs_mo2_control.py` (v1.3.0, trigger-file IPC, shows blocking dialogs) and `mo2_agent_control.py` (newer, named-pipe IPC) are loaded as MO2 plugins. The old plugin's dialogs or polling interfere with the new plugin's named-pipe endpoint.

**Diagnosis**:
1. Check MO2 plugins directory: `ls <MO2_Root>/plugins/ | grep -E 'bgs_mo2|mo2_agent'`
2. Check blocker events: `cat <MO2_Root>/plugins/Mo2AgentControl/bootstrap/runtime/blocker-events.jsonl`
3. If you see `"type": "ignored"` entries with `"title": "BGS MO2 Control"`, the old plugin is interfering.

**Fix**: Disable the old plugin by renaming:
```bash
mv "<MO2_Root>/plugins/bgs_mo2_control.py" "<MO2_Root>/plugins/bgs_mo2_control.py.disabled"
```
Restart MO2. If the new plugin alone fails to provide the broker, restore the old plugin and accept that only trigger-file IPC (with 3s polling) is available.

## xEdit Client Launch Timeout

**Symptom**: `xedit_status` returns `failed` with `"Timed out waiting for MO2 launch artifact"`. The `mo2-launch-state.json` is never written at the expected session path. The `xedit-client.ps1 process launch` command exits with code 1 after 15s.

**Root cause — two-tier (2026-07-02 verified)**:

1. **MO2 control plane uses `organizer` backend for `launch.start`**. When `xedit-client.ps1` sends a `launch.start` request via named pipe to `mo2-control-plane-<PID>`, MO2's control plane plugin (`mo2_agent_control.py`) responds with `ok: true` and launches xEdit via `organizer.startApplication()`, but returns `"artifacts": {"state_file": null, "backend": "organizer"}`. The custom `mo2-launch-state.json` path specified in the request is ignored — only the `mo2-cli` backend writes to the custom path. The `xedit-client.ps1` script then polls the expected path for 15s and times out.

2. **Named pipe name is PID-scoped**. The pipe name (`mo2-control-plane-<PID>`) changes every time MO2 restarts. If the bootstrap runtime files were read before a restart, the cached pipe name is stale.

**Diagnosis**:

1. **Verify MO2 is running**: check `<mo2Root>/plugins/Mo2AgentControl/bootstrap/runtime/status.json` for `{"state": "ok", "mo2Pid": <N>}` and that the PID matches a running `ModOrganizer.exe` process.
2. **Read the current endpoint**: `<mo2Root>/plugins/Mo2AgentControl/bootstrap/runtime/endpoint.json` gives the current named-pipe name.
3. **Test named pipe IPC directly** — send a `system.ping` to confirm the pipe is responsive:
   ```powershell
   $pipe = [System.IO.Pipes.NamedPipeClientStream]::new(".", "mo2-control-plane-<PID>", [System.IO.Pipes.PipeDirection]::InOut, [System.IO.Pipes.PipeOptions]::None)
   $pipe.Connect(5000)
   # Send: {"protocol_version":"1","request_id":"ping-1","session_id":"test","method":"system.ping","payload":{}}
   # Expect: {"ok":true,"result":{"status":"ok"}}
   ```
4. **Check the session temp dir**: `ls %TEMP%/xedit-client-sessions/<guid>/` — if only `mo2-launch-request.json`, `mo2-launch-wrapper.ps1`, and `plugins.txt` exist (no `mo2-launch-response.json`, no `mo2-launch-state.json`), the request was sent but MO2's response didn't include a state file.
5. **Read `mo2-launch-response.json`** (if it exists) — check `result.artifacts.backend`. If it's `"organizer"` with `"state_file": null`, this is the organizer-backend path. If it's `"mo2-cli"`, the state file should have been written.
6. **Check capabilities**: `<mo2Root>/plugins/Mo2AgentControl/bootstrap/runtime/capabilities.json` lists supported methods. If `launch.start` is listed, the control plane is fully initialized.

**Manual workaround — run wrapper directly** (xEdit launches WITHOUT MO2 VFS):
```bash
pwsh -NoProfile -ExecutionPolicy Bypass -File "<session_path>/mo2-launch-wrapper.ps1"
```
This spawns xEdit via `direct-child` transport (no VFS), which means xEdit uses registry-based game detection and may target the wrong game. The MCP state machine will NOT detect this externally-launched xEdit. Use only for debugging.

**Recommended fix**: Use the `xedit` MCP tools (`xedit_start`, `xedit_restart`) which handle the full lifecycle, or use `mo2_run_tool` MCP to launch xEdit through MO2's VFS properly. The direct `xedit-client.ps1` path is for MCP internal use; agents should route through the MCP surface.

## MO2 Process Detection Mismatch

**Symptom**: `mo2_status` reports `process_running: false` but `Get-Process ModOrganizer` shows the process is running.

**Root cause**: The MO2 MCP sidecar's process detection uses a specific mechanism (shared memory or profile lock) that may not match all MO2 startup modes. This is a sidecar detection gap, not a MO2 failure.

**Workaround**: Verify MO2 is running via PowerShell:
```powershell
Get-Process -Name 'ModOrganizer' -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, Responding
```
If `Responding: True`, MO2 is functional. The sidecar's `broker_connected` is the authoritative indicator of actual IPC connectivity, not `process_running`.
