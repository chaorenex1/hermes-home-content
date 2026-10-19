# xEdit Launch Pitfalls & Debug Guide

Session reference: 2026-07-01, tri-split MO2 layout.

## Transport modes in mo2-vfs-launcher.ps1

Two code paths determine whether xEdit runs inside MO2 VFS:

| Mode | Transport | VFS? | xEdit flag behavior |
|---|---|---|---|
| `broker` | MO2 CLI `launch.start` | Yes | `-SSE`/`-FO4` flags honored |
| `direct-child` | `[System.Diagnostics.Process]::Start()` | **No** | Flags ignored; uses compiled game mode |

The `direct-child` path (lines 494-495) spawns xEdit.exe as a bare process
— no MO2 VFS hooks. xEdit then falls back to registry detection and its
compiled game target (e.g. FO4Edit looks for Fallout4 in registry).

## Full parameter trace

```
xedit_start({ moRoot, mo2InstanceRoot, launcherPath, gameMode, moProfile, dataPath, pluginsFile })
  → resolveLaunchOpts()
    → LaunchOptions { clientScript, launcherPath, gameMode, moProfile, moRoot, instanceRoot, dataPath, pluginsFile }
  → launchDaemon(opts)
    → pwsh -File <clientScript> process launch
      --launcher-path <launcherPath>
      --game-mode <gameMode>        → maps to -SSE / -FO4 / -TES5 / -SF1
      --mo-profile <moProfile>
      --mo2-root <moRoot>
      --mo2-instance-root <instanceRoot>   (if set)
      --data-path <dataPath>
      --plugins-file <pluginsFile>         (if set)
    → xedit-client.launch.ps1 :: Invoke-XeditClientProcessLaunch
      → resolves plugins.txt from instance root or mo2-root
      → creates session plugins file under %TEMP%/xedit-client-sessions/<guid>/plugins.txt
      → builds normalized command: xEdit.exe -SSE -automation-serve -P:<session-plugins> -D:<dataPath>\
      → if mo-profile: New-XeditClientMo2LaunchRequest → MO2 control plane
      → MO2 control plane → mo2-vfs-launcher.ps1 → spawn xEdit
```

## Debug command line

To see the actual xEdit argv, add debug writes:

**xedit-client.launch.ps1** (before MO2 launch request):
```powershell
$exeLeaf = Split-Path -Path $normalizedLauncherCommand.DetectionPath -Leaf
Write-Host "[DEBUG] $exeLeaf $($nativeTargetArgumentList -join ' ')"
```

**mo2-vfs-launcher.ps1** (before Process.Start):
```powershell
$exeName = Split-Path -Path $startInfo.FileName -Leaf
Write-Host "[DEBUG] $exeName $($startInfo.Arguments)"
```

## Test command

```
pwsh -NoProfile -ExecutionPolicy Bypass -File "<HERMES_HOME>/skills/bgs-modding/tools/mo2-vfs-launcher/xedit-client.ps1" process launch --launcher-path "<PATH_TO_MO2_INSTALL>\Tools\xEdit\xEdit.exe" --game-mode "SkyrimSE" --mo-profile "pbr" --mo2-root "<PATH_TO_MO2_INSTALL>" --data-path "<PATH_TO_STEAM_LIBRARY>\steamapps\common\Skyrim Special Edition\Data" --plugins-file "<PATH_TO_MO2_INSTANCE>\profiles\pbr\plugins.txt"
```

## FO4Edit binary pitfall

Even when version info reports `ProductName: xEdit`, the binary at
`Tools\xEdit\xEdit.exe` may be a compiled FO4Edit. Check the log:
```
SSEEdit 4.1.6r6 Lite ... starting session   ← Skyrim SE
FO4Edit 4.1.6r6 Lite ... starting session   ← Fallout 4
```
Run `[System.Diagnostics.FileVersionInfo]::GetVersionInfo(...)` —
`OriginalFilename` and `InternalName` are empty for game-specific builds.

## MCP env var handling (hermes mcp add strips env)

Every `hermes mcp add` call removes the `env:` block from the MCP config.
Restore env vars separately after add:
```bash
hermes config set mcp_servers.bgs-xedit-mcp.env.BGS_MO2_ROOT "..."
hermes config set mcp_servers.bgs-xedit-mcp.env.BGS_XEDIT_GAME_MODE "SkyrimSE"
# ... etc
```

## timeout: 300s+ for 800+ plugins

861 plugins needed ~4 minutes to load. MCP default `readyTimeoutMs: 180000`
is insufficient. Extend via per-call override or env var.

## `-D:` space-in-path bug (MO2 CLI)

When `mo2-launch-backend: mo2-cli`, the `-D:` dataPath argument with spaces
gets mangled:

```
[DEBUG] xEdit.exe ... -D:H:\...\Skyrim Special Edition\Data\
# xEdit log shows:
Using ... Data Path: <PATH_TO_STEAM_LIBRARY>\steamapps\common\Skyrim\
```

MO2 CLI truncates at the space. xEdit falls back to wrong game.

**Fix — junction** (most reliable):
```powershell
New-Item -ItemType Junction -Path "H:\...\common\SSEData" -Target "H:\...\common\Skyrim Special Edition" -Force
```
Then pass `dataPath: "H:\\...\\SSEData\\Data"` (no spaces).

**Fix — omit `-D:`**: when MO2 is running, its VFS handles game path via
registry redirection. Launch without `dataPath` to avoid the issue:
```js
xedit_start({ launcherPath, gameMode, moProfile, moRoot, pluginsFile })
```

See `references/mo2-cli-space-in-path-bug.md` for full details.

## mo2-vfs-launcher.ps1 ArgumentList vs Arguments

The `Invoke-Mo2VfsLauncherDirectChildTransport` function originally built
a flat `$startInfo.Arguments` string with manual quoting that broke on
paths containing spaces. Fix: use `$startInfo.ArgumentList` array instead:

```powershell
foreach ($arg in $TargetArguments) {
    $startInfo.ArgumentList.Add($arg)
}
```

Each `--target-arg` value is added individually, so the child process
receives exact tokens without shell parsing. This only affects the
`direct-child` transport; the `broker`/MO2-CLI path has its own argument
handling which can still mangle spaced paths.

## mo2_agent_control.py: hardcoded exe_title + transport fix

`start_mo2_cli_launch` (line 2668) hardcodes `exe_title = "xEdit Fork"` which
does NOT exist in typical MO2 customExecutables. MO2's `-e` mode looks up
registered executables by title; when the title doesn't match, the launch
fails or falls through to a bare `subprocess.Popen` without VFS context.

### Attempt 1: transport (REVERTED — lacks VFS)

`handle_launch_start` was modified to prefer `payload.transport` (pwsh +
wrapper.ps1 → mo2-vfs-launcher.ps1) over mo2-cli. A new `_launch_transport()`
function spawned pwsh via `subprocess.Popen`. This correctly passed all args
(no space mangling), but **xEdit launched outside MO2 VFS** — no VFS hooks
meant the FO4Edit-compiled binary checked the registry and showed the
Fallout4 error dialog. **Reverted.** Transport DOES preserve args but DOES
NOT provide VFS; MO2 CLI DOES provide VFS but mangled spaced args.

### Attempt 2: change exe_title to "xEdit64" → renamed to "xEdit-fork" (2026-07-02)

Originally changed `exe_title = "xEdit64"` in `start_mo2_cli_launch`. The registered
executable entry for `xEdit64` has:
```
binary: <PATH_TO_MO2_INSTALL>/Tools/xEdit/xEdit64.exe
args:   -sse -l:chinese -cp:utf-8
```

MO2 CLI then runs: `xEdit64.exe -sse -l:chinese -cp:utf-8 -SSE -automation-serve -P:...`
The registered `-sse -l:chinese` args conflict with our explicit `-SSE`.
Duplicate SSE flags work (last wins), but `-l:chinese -cp:utf-8` may interfere
with automation-serve mode.

**Current state (2026-07-02)**: `registration_title` changed from `"xEdit64"` to
`"xEdit-fork"` to avoid collisions with the pre-existing `xEdit64` MO2 custom
executable entry that carries `-sse -l:chinese -cp:utf-8` built-in args. The
`start_mo2_cli_launch` function now registers a **new** MO2 executable called
`xEdit-fork` with `base_arguments = "-SSE -l:chinese -cp:utf-8"` and the correct
binary path. This avoids arg conflicts because the registered args match what
the launcher needs.

### Attempt 3: organizer.startApplication API (CONFIRMED ACTIVE — 2026-07-02)

Modified `handle_launch_start` to try `organizer.startApplication()` via
`_launch_via_organizer_api()`. Uses MO2's VFS + correct args. Requires
`psutil` to wrap the returned PID. **This is now the confirmed active backend**
in the current MO2 control plane — `launch.start` responses show
`"artifacts": {"state_file": null, "backend": "organizer"}`.

**Critical side-effect**: the `organizer` backend does NOT write the custom
`mo2-launch-state.json` path specified in the request payload. It returns
`state_file: null`. The `xedit-client.ps1` script's `Wait-XeditClientMo2ArtifactFile`
(15s timeout) depends on this file, so direct `xedit-client.ps1 process launch`
calls will always time out with the organizer backend. Agents should use
the `xedit` MCP tools (`xedit_start`, `xedit_restart`) or `mo2_run_tool`
instead of calling `xedit-client.ps1` directly.

**IPC flow (verified 2026-07-02)**:
1. `xedit-client.ps1` → named pipe `mo2-control-plane-<PID>` → `launch.start` request
2. MO2 responds: `{"ok": true, "result": {"pid": <N>, "artifacts": {"backend": "organizer", "state_file": null}}}`
3. xEdit is running (pid verified via `tasklist`) but `xedit-client.ps1` times out waiting for state file
4. Named pipe `system.ping` works as a health check independent of launch

### Correct fix path

The cleanest solution: **add a new executable registration in MO2** with no
built-in args:

1. In MO2 GUI: Executables → Add → Title: `"xEdit Fork"`, Binary: `xEdit64.exe`, Arguments: (empty)
2. OR: modify the existing `xEdit64` registration to remove `-sse -l:chinese -cp:utf-8`
3. Keep `exe_title = "xEdit64"` (or the new title) in `start_mo2_cli_launch`
4. Clear `plugins/__pycache__/mo2_agent_control*` and restart MO2

This way MO2 CLI launches xEdit with VFS context and no conflicting args,
while our `-SSE -automation-serve -P:... -D:...` after `--` are forwarded
cleanly. The `-D:` space-in-path bug persists with mo2-cli — use a junction
or omit `-D:` and rely on MO2 VFS.

### Deploy cycle for mo2_agent_control.py changes

```bash
# 1. Edit the plugin file
# 2. Clear cache
rm -rf "<moRoot>/plugins/__pycache__/mo2_agent_control*"
# 3. Restart MO2
powershell -Command "Stop-Process -Name ModOrganizer -Force"
powershell -Command "Start-Process '<moRoot>/ModOrganizer.exe' -ArgumentList '-p','<profile>'"
# 4. Wait for control plane
sleep 10
cat "<moRoot>/plugins/Mo2AgentControl/bootstrap/runtime/status.json"
# Should show: {"state":"ok","mo2Pid":<pid>}
```

## Dual-plugin conflict (mo2_agent_control + bgs_mo2_control)

If both `mo2_agent_control.py` and `bgs_mo2_control.py` exist in `<moRoot>/plugins/`,
they compete for the same named-pipe endpoint and produce "Named-pipe endpoint
returned an empty response" errors. Disable the old one:

```bash
mv "<moRoot>/plugins/bgs_mo2_control.py" "<moRoot>/plugins/bgs_mo2_control.py.disabled"
rm -rf "<moRoot>/plugins/__pycache__/bgs_mo2_control*"
```

## MCP env var caching

Changes to `config.yaml` `mcp_servers.*.env.*` entries do NOT take effect until
the MCP server process restarts (Hermes restart). The running MCP process caches
env vars from spawn time. When removing `BGS_XEDIT_DATA_PATH` to stop the `-D:`
flag generation, the old value persists until restart. Pass `dataPath` explicitly
as a workaround, or restart Hermes.

## Automation-call instance runs outside VFS

`Wait-XeditClientAutomationReady` polls xEdit daemon readiness by spawning
a **second** bare xEdit process via `Invoke-XeditClientAutomationCall`:

```powershell
Start-Process xEdit.exe -automation-call-pid:<pid> -automation-call-request:<req> -automation-call-response:<resp>
```

This second xEdit connects to the daemon's named pipe to send
`system.describe`. **It runs outside MO2 VFS** and will hit the registry
for game detection, showing the wrong-game error dialog (e.g. FO4Edit
looking for Fallout4 registry keys on a Skyrim SE profile).

**Fix**: pass the game-mode flag to automation-call instances.

`xedit-client.call.ps1` — add `-ExtraArguments` param to `Invoke-XeditClientAutomationCall`:
```powershell
param(..., [string[]]$ExtraArguments = @())
# in ArgumentList:
) + $ExtraArguments
```

`xedit-client.call.ps1` — add `-GameArgs` param to `Wait-XeditClientAutomationReady`:
```powershell
param(..., [string[]]$GameArgs = @())
# in the call:
$response = Invoke-XeditClientAutomationCall ... -ExtraArguments $GameArgs
```

`xedit-client.launch.ps1` — pass `$gameModeArgument` (`-SSE`) to wait:
```powershell
$null = Wait-XeditClientAutomationReady ... -GameArgs @($gameModeArgument)
```

This ensures every xEdit instance (daemon + automation-call) receives
the game-mode flag, preventing registry-based detection.

## Pitfall: xEdit process exists but no visible window appears

Symptom: `tasklist` / Task Manager shows one or more `xEdit.exe` processes, but
no xEdit window is visible. New `xEdit.exe` processes appear every few seconds
and the daemon never reports `ready`.

Diagnosis: `Wait-XeditClientAutomationReady` in `xedit-client.call.ps1` creates a
short-lived automation-call helper every 500 ms to poll the daemon's named pipe.
The helper is started with:

```powershell
$psi.CreateNoWindow = $true
$psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
```

If the daemon is slow to start or has stalled on a hidden error dialog, these
hidden helpers accumulate. The real daemon window may also be suppressed when
the MO2 control plane launches xEdit via `subprocess.Popen(creationflags=CREATE_NO_WINDOW)`
(used in `start_subprocess_launch` and `start_mo2_cli_launch` in `mo2_agent_control.py`),
so the GUI never appears and the process seems to be "repeatedly created in the
background."

Fix:

1. **Verify whether the daemon actually started.** Check `xedit_session` and
   `xedit_health`. If they return `not_started`, the daemon never reached
   readiness; the visible processes are the hidden automation-call helpers.
2. **Kill stale hidden helpers.** Stop all `xEdit.exe` processes, then restart
   through the MCP (`xedit_start`) rather than calling `xedit-client.ps1` directly.
3. **Check the real daemon log.** Read `*Edit_log.txt` in the xEdit `Tools/`
   directory for the actual startup error (wrong game registry, missing masters,
   large load-order timeout, etc.).
4. **For temporary debugging**, make the automation-call helper visible by setting
   `CreateNoWindow = $false` and `WindowStyle = Normal` in `xedit-client.call.ps1`;
   any error dialog from the helper will then be visible. Revert after debugging.
5. **Do not mistake helper PIDs for the daemon PID.** The daemon PID is the one
   returned by `xedit_session.data.daemonPid`; the 500 ms polling helpers are
   transient clients.

## Disabling the automation-call polling loop (user-requested)

**Context**: User said "没有执行，不要触发轮询了" — the 500ms hidden
`Invoke-XeditClientAutomationCall` polling loop in
`Wait-XeditClientAutomationReady` was spawning hidden xEdit processes
that accumulated and caused confusion with the real daemon process.

**Fix**: In `xedit-client.launch.ps1`, replace the
`Wait-XeditClientAutomationReady` call with logging-only:

```powershell
# Original (spawns hidden xEdit every 500ms):
$null = Wait-XeditClientAutomationReady -XeditExecutablePath $normalizedLauncherCommand.DetectionPath -XeditPid $processId -SessionPath $session.SessionPath -TimeoutSeconds $readyTimeoutSeconds -GameArgs @($gameModeArgument)

# Replacement (no polling):
Write-Host "[LAUNCH-LOG] skipping Wait-XeditClientAutomationReady (polling disabled by user request)"
Write-Host "[LAUNCH-LOG] processId=$processId — xEdit should be visible now if launch succeeded"
```

**Trade-off**: The daemon will NOT be confirmed ready via `system.describe`
when polling is disabled. The MCP `xedit_status` will remain `starting`
because `launchDaemon()` in `launch.js` also calls `process wait` which
polls via `xedit-client.ps1 process wait`. The `process wait` command
calls `Get-XeditClientValidatedLiveProcess` which does NOT spawn a new
xEdit — it just checks if the PID is alive. So `process wait` is safe
and does not create hidden processes. However, the Phase B polling in
`launchDaemon()` (line 121-137) calls `adapter.call({ command: "files.list" })`
which DOES use `Invoke-XeditClientAutomationCall` and will spawn hidden
xEdit instances. To fully disable polling, the MCP `launchDaemon` function
in `launch.js` would need to skip Phase B as well.

## [LAUNCH-LOG] debug instrumentation pattern

Adding `[LAUNCH-LOG]` prefixed `Write-Host` lines at each key step of
`Invoke-XeditClientProcessLaunch` in `xedit-client.launch.ps1` makes the
call chain visible and helps diagnose where execution stops.

Key instrumentation points (added 2026-07-02):

```powershell
Write-Host "[LAUNCH-LOG] options parsed: $($options.Keys -join ', ')"
Write-Host "[LAUNCH-LOG] launcher-path: $launcherPath"
Write-Host "[LAUNCH-LOG] game-mode-arg: $gameModeArgument"
Write-Host "[LAUNCH-LOG] mo-profile: $moProfile"
Write-Host "[LAUNCH-LOG] sandbox-root: $resolvedSandboxRoot"
Write-Host "[LAUNCH-LOG] instance-root: $resolvedInstanceRoot"
Write-Host "[LAUNCH-LOG] plugin-source resolved: $($null -ne $pluginSource)"
Write-Host "[LAUNCH-LOG] preparing MO2 launch for $exeLeaf with args: $($nativeTargetArgumentList -join ' ')"
Write-Host "[LAUNCH-LOG] MO2 launch request artifact written"
Write-Host "[LAUNCH-LOG] calling Invoke-XeditClientMo2LaunchStart..."
Write-Host "[LAUNCH-LOG] Invoke-XeditClientMo2LaunchStart returned. ok=$($mo2LaunchResult.Response.ok) status=$($mo2LaunchResult.State.status) pid=$($mo2LaunchResult.State.pid)"
Write-Host "[LAUNCH-LOG] response artifact written"
Write-Host "[LAUNCH-LOG] processId from launch result: $processId"
Write-Host "[LAUNCH-LOG] skipping Wait-XeditClientAutomationReady (polling disabled by user request)"
Write-Host "[LAUNCH-LOG] processId=$processId — xEdit should be visible now if launch succeeded"
```

## Stale bootstrap file: status.json

After MO2 is restarted, the `status.json` under
`<moRoot>/plugins/Mo2AgentControl/bootstrap/runtime/status.json` is
updated with the new MO2 PID. But if MO2 was killed and NOT restarted
(or is still initializing), the old PID in `status.json` is stale.

The MO2 control-plane client in `xedit-client.launch.ps1` checks
`status.json` and rejects it if the PID doesn't match a running
`ModOrganizer.exe` process. Error message:

```
MO2 control-plane launch.start failed: Stale live bootstrap file: status.json
```

Fix: ensure MO2 is running and fully initialized (wait ~15-20s after
launch) before calling `xedit-client.ps1 process launch`. Verify:

```bash
tasklist //FI "IMAGENAME eq ModOrganizer.exe"
cat "<moRoot>/plugins/Mo2AgentControl/bootstrap/runtime/status.json"
# mo2Pid in status.json must match the running ModOrganizer.exe PID
```

## MO2 INI editing pitfalls

ModOrganizer.ini uses `\` as section/key separator: `20\title=xEdit64`.
Paths use `\\` for literal backslash: `workingDirectory=<PATH_TO_STEAM_LIBRARY>\\...`.

When editing via `patch` tool, double-check the resulting bytes — the
tool may double-escape backslashes. Verify with Python raw byte read:

```python
with open(path, 'rb') as f: raw = f.read()
with open(path, 'r') as f: lines = f.readlines()
# Correct: line shows '20\title=xEdit64' (one backslash)
# Broken: line shows '20\\\\title=xEdit64' (four backslashes in repr)
```

Fix: use `re.sub(r'(\d+)\\\\(?=[a-zA-Z])', r'\1\\', text)` to repair
section-key separators, and `text.replace('\\\\\\\\', '\\\\')` to repair
path backslashes.

### qt_ini.py `upsert_custom_executable` backslash bug

`qt_ini.py` `_write_custom_executables_section` used
`prefix = f"{index}\\\\"` (produces 2 backslash chars) instead of
`prefix = f"{index}\\"` (1 backslash char). This wrote `1\\title=` instead
of `1\title=` to the INI, corrupting the `[customExecutables]` section.
Binary paths lost all backslashes (e.g.
`H:ueLun V5od Organizer 2oolsíitíit.exe`).

**Fix applied (2026-07-02)**: Changed to `prefix = f"{index}\\"` in both
the MO2 plugin copy and the global skills source.

See `references/qt-ini-backslash-bug.md` for full diagnosis, INI recovery
procedure, and verification commands.

### INI `\title=` matching: `endswith` fails with numeric index prefix

MO2 INI lines are `22\title=xEdit` (index-backslash-key=value). Using
`endswith("\\title=xEdit")` fails because the line ends with
`2\title=xEdit`, not `\title=xEdit`. Use `in` with extra guards:

```python
title_suffix = f"\\title={title}"
if title_suffix in stripped and stripped.endswith(title_suffix.split("\\")[-1]):
    if "\\arguments=" not in stripped and "\\binary=" not in stripped:
        # Found the title line
```

### INI binary path slash mismatch (`/` vs `\`)

`organizer.basePath()` returns paths with `\`, but MO2's INI stores paths
with `/`. Normalize both before comparison:

```python
normalized_exe = exe_path.lower().replace("\\", "/")
entry_bin = entry.get("binary", "").lower().replace("\\", "/")
if entry_bin == normalized_exe:
    return entry.get("title")
```

### INI line endings: `\r\n` (Windows CRLF)

MO2 INI uses CRLF line endings. `read_text()` with universal newlines
converts them. When patching and writing back via `write_text()`, Python
writes `\n` — MO2 tolerates this, but `configparser` on re-read also
works. No special handling needed for read-back verification.

## IOrganizer.startApplication args-stripping behavior

**Critical discovery (2026-07-02 session).** `IOrganizer.startApplication()` has
two distinct behaviors depending on whether the first argument is a path or a
configured executable TITLE:

| Call form | Args passed to child? | VFS? |
|---|---|---|
| `startApplication("path/xEdit.exe", args, ...)` | **NO** — args stripped | Yes |
| `startApplication("xEdit64", [], ...)` (title) | Uses INI-stored args only | Yes |

When a title is passed, MO2 resolves it against `[customExecutables]` in
`ModOrganizer.ini` and uses the stored `binary` + `arguments`. Any args
passed as the second parameter are **ignored**.

### Workaround: dynamic INI patching before `startApplication`

The `handle_launch_start` in `mo2_agent_control.py` now uses this flow:

1. `_resolve_executable_title(organizer, target_path)` — auto-registers
   xEdit if not already in INI, returns title string (e.g. "xEdit")
2. `_patch_ini_executable_args(ini_path, title, extra_args)` — appends
   requested args (`-automation-serve`, `-P:`, `-D:`) to the INI entry
3. `organizer.startApplication(title, [], ...)` — MO2 picks up patched INI args
4. `_restore_ini_executable_args(...)` — restores original INI args

This gives: **VFS from MO2 + correct args from patched INI + visible GUI**.

### `CREATE_NO_WINDOW` removal

`start_subprocess_launch` in `mo2_agent_control.py` originally set
`creationflags=CREATE_NO_WINDOW`, which suppressed xEdit's GUI. **Removed**
— subprocess children now show visible windows. Backend `subprocess` is
the fallback when `organizer` title-based launch fails.

### Backend detection

`mo2-launch-response.json` `artifacts.backend` field tells which path was used:
- `"organizer"` — title-based, VFS + correct args ✓
- `"subprocess"` — direct subprocess, VFS inheritance from MO2 process (incomplete)
- `"mo2-cli"` — legacy, no longer used

### Deploy cycle (same as above)

```bash
rm -rf "<moRoot>/plugins/__pycache__/mo2_agent_control*"
powershell -Command "Stop-Process -Name ModOrganizer -Force"
powershell -Command "Start-Process '<moRoot>/ModOrganizer.exe'"
sleep 15 && cat "<moRoot>/plugins/Mo2AgentControl/bootstrap/runtime/status.json"
```
