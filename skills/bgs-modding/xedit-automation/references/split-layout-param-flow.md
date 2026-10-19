# Split-Layout Parameter Flow: xedit_start → xEdit.exe

## Live example (Windows 10, 2026-07-01)

### Environment
```
MO2 base (exe + plugins):    <PATH_TO_MO2_INSTALL>
MO2 instance (profiles/mods): <PATH_TO_MO2_INSTANCE>
Profile:                      pbr
Game:                         Skyrim Special Edition
Game Data:                    <PATH_TO_STEAM_LIBRARY>\steamapps\common\Skyrim Special Edition\Data
xEdit:                        <PATH_TO_MO2_INSTALL>\Tools\xEdit\xEdit.exe (FO4Edit 4.1.6r6, runs as SSEEdit via -SSE flag)
Plugins.txt:                  <PATH_TO_MO2_INSTANCE>\profiles\pbr\plugins.txt (861 plugins)
```

### MCP invocation
```js
xedit_start({
  moRoot:           "<PATH_TO_MO2_INSTALL>",
  mo2InstanceRoot:  "<PATH_TO_MO2_INSTANCE>",
  launcherPath:     "<PATH_TO_MO2_INSTALL>\\Tools\\xEdit\\xEdit.exe",
  gameMode:         "SkyrimSE",
  moProfile:        "pbr",
  dataPath:         "<PATH_TO_STEAM_LIBRARY>\\steamapps\\common\\Skyrim Special Edition\\Data",
})
```

### Parameter trace

```
xedit_start(args)
  │
  ├─ resolveLaunchOpts()
  │   moRoot          → args.moRoot
  │   mo2InstanceRoot → args.mo2InstanceRoot  (newly added)
  │   launcherPath    → args.launcherPath
  │   gameMode        → args.gameMode
  │   moProfile       → args.moProfile
  │   dataPath        → args.dataPath
  │
  ├─ launchDaemon(opts) — launch.ts:116
  │   pwsh xedit-client.ps1 process launch \
  │     --launcher-path <path> \
  │     --game-mode SkyrimSE     → maps to -SSE \
  │     --mo-profile pbr \
  │     --mo2-root <base>        → used for control-plane bridge \
  │     --mo2-instance-root <instance> → used for profile lookup \
  │     --data-path <data>       → maps to -D:<data>\
  │
  ├─ xedit-client.ps1 → Invoke-XeditClientProcessLaunch
  │   $gameModeArgument          = '-SSE'
  │   $resolvedSandboxRoot       = --mo2-root value (control plane)
  │   $resolvedInstanceRoot      = --mo2-instance-root || $resolvedSandboxRoot
  │   $pluginSource              = Get-XeditClientResolvedPluginSource(..., $resolvedInstanceRoot)
  │   → reads $resolvedInstanceRoot/profiles/pbr/plugins.txt  ✓
  │
  ├─ New-XeditClientMo2LaunchRequest($resolvedSandboxRoot)
  │   runtimeRoot = $resolvedSandboxRoot/plugins/Mo2AgentControl/bootstrap/runtime
  │   → checks status.json for live MO2
  │
  └─ MO2 VFS launch (mo2-vfs-launcher.ps1)
      xEdit.exe -SSE -automation-serve \
        -P:<session>/plugins.txt \
        -D:<PATH_TO_STEAM_LIBRARY>\...\Skyrim Special Edition\Data\
```

### Phase A/B timeout

`launchDaemon` default `readyTimeoutMs` = 180s. For 861 plugins, this is too short.
Set `BGS_XEDIT_READY_TIMEOUT_SECONDS=300` on the MCP server env to extend.

### xEdit.exe identity note

The `xEdit.exe` at this path is FO4Edit 4.1.6r6 (identifies as "xEdit" in version
info but compiled for Fallout4). When launched INSIDE the MO2 VFS, the `-SSE`
flag switches it to SSEEdit mode. When launched OUTSIDE the MO2 VFS (direct
command line), it defaults to FO4Edit and looks for Fallout4 registry keys.
