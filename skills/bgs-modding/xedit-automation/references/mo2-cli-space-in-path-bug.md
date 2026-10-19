# MO2 CLI Space-in-Path Bug

## Symptom

`xedit_start` with `dataPath` containing spaces (e.g. `Skyrim Special Edition`)
produces wrong Data path in xEdit log:

```text
# Expected
Using Skyrim Special Edition Data Path: <PATH_TO_STEAM_LIBRARY>\steamapps\common\Skyrim Special Edition\Data\

# Actual
Using Skyrim Special Edition Data Path: <PATH_TO_STEAM_LIBRARY>\steamapps\common\Skyrim
```

The path is truncated at the first space. xEdit then falls back to the wrong
game (Skyrim LE) and fails with registry/INI errors.

## Root cause

When `mo2-launch-backend: mo2-cli`, the MO2 control plane routes the launch
through MO2's own CLI. The `-D:<path>` argument contains spaces, and the
Windows command-line parser has a classic trap: a **trailing backslash inside a
quoted token escapes the closing quote**. The PowerShell client was appending a
trailing `\` to the data path, so the final command-line token looked like:

```text
"-D:H:\...\Skyrim Special Edition\Data\\"
```

The trailing `\` escapes the closing `"`, causing the token to be mis-parsed and
truncated at the first space.

## Fix: quote-safe path construction without bypassing MO2 CLI

Do **not** switch to `organizer.startApplication` unless the user explicitly
asks for it. The request in this session was to stay on the MO2 CLI path and fix
quoting instead.

### 1. `xedit-client.launch.ps1` — stop appending a trailing backslash

Change the `--data-path` handling (around line 423) so the `-D:` argument does
not end with `\`:

```powershell
# --data-path (optional) translates to xEdit's -D:<path> flag.
# We deliberately do NOT append a trailing backslash. On Windows a trailing
# backslash inside a quoted token escapes the closing quote, which causes
# MO2 CLI / xEdit to mis-parse paths containing spaces.
if ($options.ContainsKey('--data-path')) {
    $dataPathArg = (ConvertTo-XeditClientNativeWindowsPath -Path ([string]$options['--data-path'])).TrimEnd('\')
    if (-not [string]::IsNullOrWhiteSpace($dataPathArg)) {
        $normalizedLauncherCommand.ArgumentList = @($normalizedLauncherCommand.ArgumentList + @('-D:' + $dataPathArg))
        $nativeTargetArgumentList = @(ConvertTo-XeditClientFlatStringArray -Values @($nativeTargetArgumentList + @('-D:' + $dataPathArg)))
    }
}
```

### 2. `mo2_agent_control.py` — controlled command-line quoting

Add a helper that strips trailing backslashes before quoting, then pass the whole
command line as a single string to `subprocess.Popen` so `list2cmdline` cannot
re-escape the token:

```python
def _quote_mo2_cli_arg(arg: str) -> str:
    """Quote a single argument for the MO2 CLI command line.

    Windows command-line parsing has a classic trap: a trailing backslash
    inside a quoted token escapes the closing quote, which makes a value like
    '-D:H:\\Skyrim Special Edition\\Data\\' mis-parse. We strip the trailing
    backslash before quoting so the path is passed as a single token.
    """
    if not any(c in arg for c in ' \t"'):
        return arg
    arg = arg.rstrip("\\")
    arg = arg.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{arg}"'


def start_mo2_cli_launch(payload: dict[str, object], organizer=None) -> subprocess.Popen:
    """Launch through MO2 CLI 'run -e' to get VFS context with proper arg forwarding."""
    target_path = str(payload["target_path"])
    args = list(payload.get("args", []))

    mo2_exe = _find_mo2_exe(organizer) if organizer else None
    if not mo2_exe:
        return start_subprocess_launch(payload)

    profile_name = "pbr"
    exe_title = "xEdit Fork"
    cli_args = [
        mo2_exe,
        "-p", profile_name,
        "-e", exe_title,
        "--",
        *args,
    ]

    # Pass the command line as a single string so we control quoting exactly.
    cmd_line = " ".join(_quote_mo2_cli_arg(a) for a in cli_args)

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(
        cmd_line,
        cwd=str(Path(mo2_exe).parent),
        creationflags=creation_flags,
    )
```

Result: the `-D:` token is emitted as:

```text
"-D:H:\...\Skyrim Special Edition\Data"
```

No trailing backslash, no escaped closing quote, single intact token.

## Verification

Check `SSEEdit_log.txt` in `<moRoot>/Tools/xEdit/` after launch. The "Using ...
Data Path:" line should point to the correct game directory, not the truncated
path.

## Alternative: omit `-D:` entirely

When MO2 is running, its VFS should resolve the game path correctly via registry
redirection. If `mo2_status.detection.process_running` is true and the control
plane bootstrap is fresh, try launching **without** `dataPath`:

```js
xedit_start({
  moRoot: "<PATH_TO_MO2_INSTALL>",
  launcherPath: "...",
  gameMode: "SkyrimSE",
  moProfile: "pbr",
  pluginsFile: "<PATH_TO_MO2_INSTANCE>\\profiles\\pbr\\plugins.txt",
})
```

This avoids the space-in-path issue entirely, as only `-SSE -automation-serve -P:...`
args are passed (no spaces).
