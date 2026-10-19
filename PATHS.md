# Path placeholders

This snapshot was captured on one Windows machine. Paths that pointed into a
specific user profile or a specific disk layout are replaced with placeholders.
They are literal text: Hermes does not expand them. Substitute real paths, or
set the matching environment variable, before using `config.yaml` or `mcp-configs/`.

| Placeholder | Meaning | Typical value |
|---|---|---|
| `<HERMES_HOME>` | Hermes home: config, skills, plugins, sessions, `.env` | `%LOCALAPPDATA%\hermes`, `~/.hermes` |
| `<USER_HOME>` | OS user profile | `C:\Users\<you>`, `$HOME` |
| `<PATH_TO_MO2_INSTALL>` | Mod Organizer 2 installation directory, contains `ModOrganizer.exe` | `D:\ModOrganizer2` |
| `<PATH_TO_MO2_INSTANCE>` | MO2 instance root, contains `profiles/` and `mods/` | `...\MO2\instances\<name>` |
| `<PATH_TO_MO2_SECONDARY>` | Second MO2 install referenced by the BGS fetch and Papyrus scripts | `D:\ModOrganizer2` |
| `<PATH_TO_MO2_ALT>` | Alternate MO2 root used by the BGS MCP test fixtures | any MO2 root |
| `<PATH_TO_STEAM_LIBRARY>` | Steam library root, contains `steamapps/common` | `D:\SteamLibrary` |
| `<PATH_TO_STEAM>` | Steam installation root | `C:\Program Files (x86)\Steam` |
| `<PATH_TO_STARFIELD>` | Starfield installation | `...\steamapps\common\Starfield` |
| `<PATH_TO_XEDIT>` | Directory containing `xEdit.exe` | `...\xEdit` |
| `<PATH_TO_BROWSER_PROFILE>` | Edge/Chromium user-data directory used for CDP automation | `%LOCALAPPDATA%\Microsoft\Edge\User Data` |
| `<PATH_TO_BGS_FIXTURE>` | Writable fixture root for the BGS MCP acceptance tests | any temporary directory |
| `<PATH_TO_PAPYRUS_WORK>` | Papyrus source, compile, and decompile workspace | any working directory |

Notes:

- `<HERMES_HOME>` is the only placeholder with a native environment variable.
  Set `HERMES_HOME` and use `$HERMES_HOME` / `%HERMES_HOME%` in scripts where
  the shell supports it.
- `config.yaml` and `mcp-configs/mcp-servers.json` will not run until the
  placeholders are replaced.
- The BGS MCP test fixtures assert on some absolute paths. If you run those
  tests, point the placeholders at a real MO2 layout.
- No operator name or user-profile path remains in the tree. Prose references
  were changed to "the operator".
