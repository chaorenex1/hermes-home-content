# Windows hidden xEdit window bug

## Symptom

- `xedit_status` reports `not_started` or the daemon never becomes ready.
- Task Manager shows multiple `xEdit.exe` processes, but none have a visible window.
- The xEdit GUI never appears; automation-call polling eventually times out.

## Root cause

On Windows, `subprocess.Popen(..., creationflags=CREATE_NO_WINDOW)` starts a
console-less process. For xEdit — a GUI program — suppressing the console also
suppresses the main window and any modal error dialogs. If xEdit cannot start
cleanly (wrong game mode, missing VFS, plugin load error, etc.), it stalls on a
hidden dialog and the daemon never answers `system.describe`.

The `xedit-client.call.ps1` `Invoke-XeditClientAutomationCall` helper already
sets `CreateNoWindow = $true` and `WindowStyle = Hidden`. That is correct for
the short-lived IPC call helper, but wrong for the long-lived daemon. When the
control-plane plugin (`mo2_agent_control.py`) also uses `CREATE_NO_WINDOW` for
the real daemon launch, the GUI is hidden and any error stalls the process.

Additionally, `Wait-XeditClientAutomationReady` polls every 500ms and starts a
new hidden xEdit instance on each retry. If the daemon is stuck, these
instances accumulate in the background.

## Affected code locations

| File | Function / line pattern | Wrong flag |
|---|---|---|
| `mo2_agent_control.py` | `_launch_transport` | `creationflags=CREATE_NO_WINDOW` |
| `mo2_agent_control.py` | `start_mo2_cli_launch` | `creationflags=CREATE_NO_WINDOW` |
| `mo2_agent_control.py` | `start_subprocess_launch` | `creationflags=CREATE_NO_WINDOW` |
| `mo2-vfs-launcher.ps1` | `Invoke-Mo2VfsLauncherDirectChildTransport` | `UseShellExecute=$false` + redirect stdout/stderr (hides window) |
| `xedit-client.call.ps1` | `Invoke-XeditClientAutomationCall` | `CreateNoWindow = $true` + `WindowStyle = Hidden` (acceptable for the IPC call helper only) |
| `xedit-client.launch.ps1` | `Wait-XeditClientAutomationReady` | Calls `Invoke-XeditClientAutomationCall` every 500ms (spawns hidden xEdit instances that pile up) |

**Note (2026-07-02)**: The `Wait-XeditClientAutomationReady` call in
`Invoke-XeditClientProcessLaunch` has been **removed** and replaced with
logging. The polling loop is now disabled by default. See
`references/xedit-launch-pitfalls.md` § "Disabling the automation-call
polling loop" for details.

**Note (2026-07-02)**: The `registration_title` in
`start_mo2_cli_launch` has been changed from `"xEdit64"` to `"xEdit-fork"`
to avoid conflicts with pre-existing MO2 custom executable entries. See
`references/xedit-launch-pitfalls.md` § "Attempt 2" for the rationale.

**Note (2026-07-02)**: The `-SSE` flag passed to xEdit causes SSEEdit 4.1.6r6
to exit immediately. Testing showed that `-tSSE` and no-flag launches work
correctly, but `-SSE` causes the process to terminate within seconds. This
is a separate issue from the hidden window bug but compounds the diagnosis.
See `references/xedit-sse-vs-tsse-arg.md` for test results.

**Note (2026-07-02)**: The `qt_ini.py` `upsert_custom_executable` function
corrupted `ModOrganizer.ini` by writing double-backslash prefixes
(`1\\title=` instead of `1\title=`). This caused MO2 CLI to silently fail
to find registered executables. Fixed by changing `prefix = f"{index}\\\\"`
to `prefix = f"{index}\\"`. See `references/qt-ini-backslash-bug.md`.

## Fix (Python control-plane plugin)

Replace `CREATE_NO_WINDOW` with an explicit `STARTUPINFO` that clears
`STARTF_USESHOWWINDOW`:

```python
import subprocess
import sys

startupinfo = subprocess.STARTUPINFO() if sys.platform == "win32" else None
if startupinfo is not None:
    startupinfo.dwFlags &= ~subprocess.STARTF_USESHOWWINDOW

subprocess.Popen(
    args,
    cwd=cwd,
    env=env,
    startupinfo=startupinfo,
)
```

Apply this in all three xEdit launch paths in `mo2_agent_control.py`:
- `_launch_transport`
- `start_mo2_cli_launch`
- `start_subprocess_launch`

## Fix (PowerShell transport wrapper)

For `Invoke-Mo2VfsLauncherDirectChildTransport`, default to a visible window
by using `UseShellExecute = $true` and only redirect output when the caller
explicitly asks for capture:

```powershell
$startInfo = New-Object System.Diagnostics.ProcessStartInfo
$startInfo.UseShellExecute = $true
$startInfo.WorkingDirectory = Split-Path -Path $TargetPath -Parent

$captureOutput = -not [string]::IsNullOrWhiteSpace($StdoutFile) -or
                  -not [string]::IsNullOrWhiteSpace($StderrFile)
if ($captureOutput) {
    $startInfo.RedirectStandardOutput = -not [string]::IsNullOrWhiteSpace($StdoutFile)
    $startInfo.RedirectStandardError = -not [string]::IsNullOrWhiteSpace($StderrFile)
}

if ($captureOutput) {
    foreach ($arg in $TargetArguments) {
        $startInfo.ArgumentList.Add($arg)
    }
}
else {
    $startInfo.Arguments = ($TargetArguments | ForEach-Object {
        if ($_ -match ' ') { '"' + $_ + '"' } else { $_ }
    }) -join ' '
}
```

Note: when `UseShellExecute = $true` you cannot use `ArgumentList`; use a
quoted argument string instead.

## Deploy cycle

1. Edit the file in the MO2 plugin directory the user actually loads:
   `<PATH_TO_MO2_INSTALL>\plugins\mo2_agent_control.py`.
2. Delete the plugin `__pycache__` so Python recompiles:
   `<PATH_TO_MO2_INSTALL>\plugins\__pycache__\mo2_agent_control*.pyc`
3. Restart MO2 (the control-plane plugin is loaded at startup).
4. Trigger `xedit_start` (or `xedit_restart`) from Hermes.
5. Verify:
   - xEdit window appears within 30-60 seconds.
   - `xedit_status` returns `ready`.
   - Task Manager shows one visible xEdit daemon, not a growing pile of hidden
     processes.

## Verification command

After launch, run:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.Name -like '*xEdit*' } |
    Select-Object Name, ProcessId, CommandLine
```

A healthy launch shows one xEdit process with `-automation-serve` and its GUI
visible. Multiple hidden processes indicate the daemon is still stuck and the
automation-call retry loop is spawning clients.

## Related

- `references/xedit-launch-pitfalls.md` — broader transport/MO2-CLI/organizer
  launch issues.
- `references/split-layout-param-flow.md` — parameter flow for split-layout
  MO2 installs.
