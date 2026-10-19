# Split Layout MO2 + BGS-MO2 CLI Recipe

Session reference: 2026-07-01, the operator on Windows 10.

## Observed layout

- **Instance INI / profiles:** `<USER_HOME>\AppData\Local\ModOrganizer\mod make`
- **Base directory / mods / profiles data:** `<PATH_TO_MO2_INSTANCE>`
- **MO2 executable + plugins/:** `<PATH_TO_MO2_INSTALL>` (registered in `nxmhandler.ini`)
- **Active profile:** `pbr`
- **Game:** `Skyrim Special Edition`

This is a "split layout" where the MO2 program tree is separate from the
instance/profile tree. The `bgs-mo2` installer found only one `plugins/`
directory: the main install at `<PATH_TO_MO2_INSTALL>\plugins`, not
`<PATH_TO_MO2_INSTANCE>\plugins` (which does not exist). The control plane works as long as
`bgs_mo2_control.py` is deployed into the plugins directory that the running
MO2 executable actually loads.

## Working CLI commands

### Discover instances
```powershell
python "$HERMES_HOME/skills/bgs-modding/bgs-mo2/scripts/mo2_manager.py" list
```

### Read instance details
```powershell
python "$HERMES_HOME/skills/bgs-modding/bgs-mo2/scripts/mo2_manager.py" info "mod make"
```

### List launchable MO2 options
```powershell
python "$HERMES_HOME/skills/bgs-modding/bgs-mo2/scripts/mo2_manager.py" launch --list
```

Output will look like:
```
[0] 主安装 (nxmhandler) v2.5.2 (cyberpunk2077, skyrimse, skyrim)
      <PATH_TO_MO2_INSTALL>\ModOrganizer.exe
  [1] 实例 'juelunv5' v2.5.2
      ...
```

### Launch MO2 by index
```powershell
python "$HERMES_HOME/skills/bgs-modding/bgs-mo2/scripts/mo2_manager.py" launch 0
```

`launch` takes an **index**, not an instance name or profile name.

### Install control-plane plugins
```powershell
python "$HERMES_HOME/skills/bgs-modding/bgs-mo2/scripts/mo2_install.py" --all
```

Expected output for a split layout:
```
✓ <PATH_TO_MO2_INSTALL>\plugins (1/3 files)
   ✓ bgs_mo2_control.py (backup: ...)
   ✗ bgs_nexus_modpage.py
   ✗ bgs_preview.py
```

The two failures are expected when those optional plugin sources are not
present in the `bgs-mo2` skill tree. Only `bgs_mo2_control.py` is required for
the control plane.

### Verify runtime state
After MO2 is visible and loaded:
```powershell
python "$HERMES_HOME/skills/bgs-modding/bgs-mo2/scripts/mo2_control.py" state
```

Expected:
```json
{
  "ok": true,
  "state": {
    "profileName": "pbr",
    "profilePath": "<PATH_TO_MO2_INSTANCE>/profiles/pbr",
    "gameName": "Skyrim Special Edition",
    "basePath": "<PATH_TO_MO2_INSTANCE>",
    "modCount": 1721,
    "pluginCount": 940
  }
}
```

Also check the plugin bootstrap file:
```powershell
cat "<PATH_TO_MO2_INSTALL>\plugins\Mo2AgentControl\bootstrap\runtime\status.json"
```

Expected: `{"schemaVersion": 1, "state": "ok", "mo2Pid": <pid>}`

### Fallback: trigger-file IPC when mo2_manager.py auto fails

When auto-detection returns the wrong instance or fails entirely, query the
running MO2 directly through trigger files. This is the most reliable method
when the running MO2 exe location does not match any instance INI.

```python
import json, time
from pathlib import Path
from datetime import datetime

TRIGGER_DIR = Path.home() / "AppData" / "Local" / "Temp" / "mo2_control"

# Clean stale files
for f in ["command.json", "command.lock", "result.json"]:
    (TRIGGER_DIR / f).unlink(missing_ok=True)

# Write command
cmd = {"command": "get_state", "timestamp": datetime.now().isoformat()}
(TRIGGER_DIR / "command.json").write_text(json.dumps(cmd), encoding="utf-8")

# Poll (plugin polls every 3s)
for i in range(20):
    time.sleep(0.5)
    rf = TRIGGER_DIR / "result.json"
    if rf.exists():
        result = json.loads(rf.read_text(encoding="utf-8"))
        print(json.dumps(result, indent=2, ensure_ascii=False))
        break
```

### basePath is NOT the game directory

The plugin's `get_state` returns `basePath` which is MO2's internal data
directory (e.g., `<PATH_TO_MO2_INSTANCE>` where mods/ and profiles/ live). For
`BGS_XEDIT_DATA_PATH`, read the actual game path from the instance's
`ModOrganizer.ini`:

```
gamePath=@ByteArray(<PATH_TO_STEAM_LIBRARY>\\steamapps\\common\\Skyrim Special Edition)
```

Strip the `@ByteArray(...)` wrapper — that is your `BGS_XEDIT_DATA_PATH`.

## MCP tool invocation note

The BGS MCP tools (`bgs_kb_status`, `bgs_kb_query`, `xedit_start`, etc.) are
exposed through the MCP servers listed in `hermes mcp list`. They are **not**
directly invocable via `hermes tools call`. If you need to call them outside the
Hermes chat loop, start the MCP server manually over stdio and send the proper
MCP JSON-RPC messages.
