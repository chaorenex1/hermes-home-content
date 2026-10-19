# xEdit `-SSE` vs `-tSSE` parameter (immediate exit)

## Session context

- Date: 2026-07-02
- xEdit version: SSEEdit 4.1.6r6 (at `<PATH_TO_MO2_INSTALL>\Tools\xEdit\xEdit.exe`, 45 MB)

## Symptom

xEdit exits immediately (within seconds) when launched with `-SSE` argument.
No log file is written, no window appears, exit code 0.

## Test results

| Args | Result | Notes |
|---|---|---|
| (none) | ✅ stays running, window appears | PID 12992, 31 MB RAM |
| `-tSSE` | ✅ stays running, window appears | PID 8296, 31 MB RAM |
| `-SSE` | ❌ exits immediately | No process after 8s |
| `-SSE -automation-serve -P:...` | ❌ exits immediately | (the args used by xedit-client.launch.ps1) |

## Root cause

The `-SSE` flag is interpreted by xEdit as **game mode selector** in some
builds, but in the SSEEdit 4.1.6r6 build, the correct flag is `-tSSE`
(or no flag at all, since the binary is already compiled for Skyrim SE).

The `-SSE` flag may cause xEdit to enter a batch/CLI mode that completes
immediately and exits, rather than entering the interactive GUI mode.

## Impact on the xedit-client launch chain

`xedit-client.launch.ps1` `Invoke-XeditClientProcessLaunch` builds the game
mode argument via `Get-XeditClientValidatedGameModeArgument`:

```powershell
$gameModeArgument = Get-XeditClientValidatedGameModeArgument -GameMode $options['--game-mode']
# Returns "-SSE" for SkyrimSE
```

This `-SSE` is then passed as the first xEdit argument, followed by
`-automation-serve -P:...`. If `-SSE` causes immediate exit, the daemon
never starts and the MCP `xedit_status` stays `starting` forever.

## Potential fix

Option A: Change `Get-XeditClientValidatedGameModeArgument` to return
`-tSSE` instead of `-SSE` for SkyrimSE:

```powershell
# In xedit-client.common.ps1 or wherever the mapping is defined
$GameModeMap = @{
    'SkyrimSE'  = '-tSSE'
    'Fallout4'  = '-tFO4'
    # etc.
}
```

Option B: Omit the game-mode flag entirely when the xEdit binary is already
compiled for the target game (SSEEdit for Skyrim SE). The binary knows its
game target from compilation, not from the CLI flag.

Option C: When launching through MO2 VFS (MO2 CLI or organizer backend),
the game mode is determined by MO2's game plugin, so the `-SSE` flag may be
redundant. Test with the flag omitted in MO2-backed launches.

## Verification

```bash
# Test with no args (should stay running):
"<PATH_TO_MO2_INSTALL>/Tools/xEdit/xEdit.exe" &
sleep 8 && tasklist //FI "IMAGENAME eq xEdit.exe"

# Test with -tSSE (should stay running):
"<PATH_TO_MO2_INSTALL>/Tools/xEdit/xEdit.exe" -tSSE &
sleep 8 && tasklist //FI "IMAGENAME eq xEdit.exe"

# Test with -SSE (will exit immediately):
"<PATH_TO_MO2_INSTALL>/Tools/xEdit/xEdit.exe" -SSE &
sleep 8 && tasklist //FI "IMAGENAME eq xEdit.exe"
```

## Related

- `references/xedit-launch-pitfalls.md` — broader launch issues
- `references/invoke-xeditclientprocesslaunch-execution-diagnosis.md` —
  full call chain and the "function ran but xEdit exited" follow-up
