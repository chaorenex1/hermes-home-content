# xEdit Launch Code-Change Deploy Cycle

When you patch `xedit-client.*.ps1`, `mo2_agent_control.py`, or any control-plane
Python code, the changed file must reach the runtime MO2 plugin directory before
it is exercised. Hermes skills live in `%LOCALAPPDATA%/hermes/skills/bgs-modding/`,
but MO2 loads the Python plugin from its own `plugins/` directory and caches
bytecode in `plugins/__pycache__/`. A code change that is only in the skill
tree is silently ignored.

## Deploy steps

1. **Identify the runtime destination**.
   - `mo2_agent_control.py` → `<moRoot>/plugins/mo2_agent_control.py`
   - `xedit-client.launch.ps1` and `xedit-client.*.ps1` → `<moRoot>/plugins/Mo2AgentControl/bootstrap/runtime/`

2. **Copy the changed file** from the skill tree to the runtime destination.

   ```bash
   cp "<USER_HOME>/AppData/Local/hermes/skills/bgs-modding/tools/mo2-control-plane/live-bridge/mo2_agent_control.py" \
      "/h/JueLun V5/Mod Organizer 2/plugins/mo2_agent_control.py"

   cp "<USER_HOME>/AppData/Local/hermes/skills/bgs-modding/tools/mo2-vfs-launcher/lib/xedit-client.launch.ps1" \
      "/h/JueLun V5/Mod Organizer 2/plugins/Mo2AgentControl/bootstrap/runtime/xedit-client.launch.ps1"
   ```

3. **Delete the Python bytecode cache** so MO2 does not load the old `.pyc`.

   ```bash
   rm -rf "/h/JueLun V5/Mod Organizer 2/plugins/__pycache__"
   ```

4. **Verify MO2 is running** with the expected profile.

   ```js
   mo2_status({})
   // detection.process_running must be true
   // profile must match the one used in xedit_start
   ```

5. **Launch xEdit** and read the evidence.

   ```js
   xedit_start({ moRoot, mo2InstanceRoot, gameMode, dataPath, moProfile })
   xedit_status()  // poll until ready or failed
   ```

6. **Check the log**. If the bug was path-related, read `*Edit_log.txt` in
   `<moRoot>/Tools/xEdit/` for the "Using ... Data Path:" line.

## Common failures before reaching the actual test

| Failure | Cause | Fix |
|---|---|---|
| `Stale live bootstrap file: status.json` | MO2 is not running | Start MO2 manually; verify `mo2_status.detection.process_running` |
| `CEILING001` from `mo2_run_tool` | Permission ceiling at `metadata-editable` | Set `BGS_MO2_PERMISSION_CEILING=full-control` or start MO2 manually |
| `ENOENT: no such file or directory, open '.../ModOrganizer.ini'` | `mo2_session` bound to the wrong root (split layout) | Use `mo2InstanceRoot` for the instance path, `moRoot` for the base install |
| Changes silently ignored | `__pycache__` still contains old `.pyc` | Delete `plugins/__pycache__` |

## This session's concrete example

The user asked to fix MO2 CLI path truncation without bypassing the CLI.
The patch was made in the skill tree, but the end-to-end test could not
complete because MO2 was not running at test time. The deploy steps above are
required to validate it.
