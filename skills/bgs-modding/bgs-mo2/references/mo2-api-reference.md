# MO2 Plugin API — Consolidated Reference

## PluginState Enum

| Value | Name | Meaning |
|-------|------|---------|
| 0 | INACTIVE | Plugin disabled |
| 1 | ACTIVE | Plugin enabled (regular) |
| 2 | (ALWAYS_ACTIVE) | Master/required plugin — cannot be fully disabled via `setState()`; degrades to 1 at most |

> **Pitfall**: `setState(name, PluginState.INACTIVE)` on a state=2 plugin returns `ok:True` but only changes state to 1, not 0. MO2's dependency protection prevents full disable.

## IOrganizer

| Method | Returns | Notes |
|--------|---------|-------|
| `refresh(save_changes=True)` | None | F5 equivalent; **blocks UI** — use `QTimer.singleShot(500, ...)` to defer |
| `startApplication(executable, args, cwd, profile...)` | int (handle) | Launch with VFS; 0 = failed |
| `createMod(name)` | IModInterface\|None | Creates mod directory + entry |
| `modList()` | IModList | |
| `pluginList()` | IPluginList | |
| `managedGame()` | IPluginGame | |
| `profile()` / `profileName()` / `profilePath()` | IProfile / str / str | |
| `basePath()` / `modsPath()` / `downloadsPath()` | str | |
| `appVersion()` | VersionInfo | |
| `pluginSetting(name, key)` / `setPluginSetting(...)` | MoVariant / None | |
| `persistent(name, key, default)` / `setPersistent(...)` | MoVariant / None | |

## IModList

| Method | Returns | Notes |
|--------|---------|-------|
| `allMods()` | Sequence[str] | Internal names |
| `getMod(name)` | IModInterface\|None | |
| `setActive(name, bool)` | bool | Enable/disable mod |
| `setPriority(name, int)` | bool | Reorder mod (0-based) |
| `removeMod(mod)` | bool | Delete from disk + UI |
| `onModInstalled/onModMoved/onModRemoved/onModStateChanged` | bool | Event callbacks |

## IPluginList

| Method | Returns | Notes |
|--------|---------|-------|
| `pluginNames()` | Sequence[str] | |
| `state(name)` | PluginState | 0=INACTIVE, 1=ACTIVE, 2=ALWAYS_ACTIVE |
| `setState(name, PluginState)` | None | |
| `priority(name)` | int | -1 if inactive |
| `setPriority(name, int)` | bool | Only works on ACTIVE plugins |
| `loadOrder(name)` | int | Game load order (-1 if inactive) |
| `setLoadOrder(list)` | None | Full order; unlisted plugins placed at end |
| `origin(name)` | str | Mod name that provides this plugin |
| `masters(name)` | Sequence[str] | Required masters |
| `isMasterFlagged/isLightFlagged(name)` | bool | |
| `hasMasterExtension/hasLightExtension(name)` | bool | |
| `hasNoRecords(name)` | bool | |
| `onPluginMoved/onPluginStateChanged/onRefreshed` | bool | Event callbacks |

## IModInterface

| Method | Returns |
|--------|---------|
| `name()` | str |
| `nexusId()` | int |
| `version()` / `newestVersion()` | VersionInfo |
| `url()` | str |
| `repository()` | str |
| `installationFile()` | str |
| `primaryCategory()` | int |
| `gameName()` | str |
| `fileTree()` | IFileTree |
| `endorsedState()` | EndorsedState |
| `trackedState()` | TrackedState |
| `comments()` / `notes()` | str |
| `isSeparator()` / `isBackup()` / `isForeign()` / `isOverwrite()` | bool |
| `converted()` / `validated()` | bool |

## IPlugin (base class)

| Method | Required | Returns |
|--------|:--:|--------|
| `name()` | ✅ | str (internal, non-localized) |
| `author()` | ✅ | str |
| `description()` | ✅ | str |
| `version()` | ✅ | VersionInfo |
| `init(organizer)` | ✅ | bool |
| `settings()` | ✅ | list[PluginSetting] |
| `localizedName()` | — | str (defaults to name()) |
| `requirements()` | — | list[IPluginRequirement] |
| `enabledByDefault()` | — | bool (default True) |
| `master()` | — | str |

> **Pitfall**: MO2 loads plugins successfully even without `name()`/`author()`/`description()`/`version()` — these are abstract in the API but MO2 appears to handle their absence gracefully. Not recommended but observed behavior.

## IPluginTool

| Method | Returns |
|--------|---------|
| `displayName()` | str |
| `tooltip()` | str |
| `icon()` | QIcon |
| `display()` | None |

## IPluginModPage

| Method | Returns |
|--------|---------|
| `displayName()` | str |
| `icon()` | QIcon |
| `pageURL()` | QUrl |
| `useIntegratedBrowser()` | bool |
| `handlesDownload(page_url, download_url, fileinfo)` | bool |

## IPluginPreview

| Method | Returns |
|--------|---------|
| `supportedExtensions()` | set[str] |
| `supportsArchives()` | bool |
| `genFilePreview(filename, max_size)` | QWidget |
| `genDataPreview(file_data, filename, max_size)` | QWidget |

## IPluginRequirement

Inner class `Problem(short_description, long_description)`.
Method `check(organizer)` → Problem|None.

## PluginRequirementFactory

- `gameDependency(name)` → IPluginRequirement

## SortMechanism Enum

NONE / LOOT / BOSS / MLOX — no direct sort API. Use `IPluginList.setLoadOrder()` with pre-sorted order.

## VersionInfo

`VersionInfo(major, minor, patch, ReleaseType)`. ReleaseType: PRE_ALPHA / ALPHA / BETA / CANDIDATE / FINAL.

## PluginSetting

`PluginSetting(key, description, tooltip, default_value)`.

## MO2 Instance Structure

```
~/AppData/Local/ModOrganizer/
├── nxmhandler.ini       # Handler mappings (MO2 exe paths)
├── cache/               # Global cache (NOT an instance)
├── <InstanceName>/
│   ├── ModOrganizer.ini  # [General]/[Settings]/[customExecutables]/[Plugins]/...
│   ├── Mod.Organizer-<version>.exe  # Portable copy
│   └── logs/
└── ...
```

- `base_directory` in `[Settings]` redirects mods/profiles/overwrite to external path
- Profile files: `modlist.txt` (+enabled/-disabled), `plugins.txt` (*enabled), `loadorder.txt`, `archives.txt`, `lockedorder.txt`, `initweaks.ini`, `settings.ini`
