# SkyrimSE Junction (space-free dataPath)

Created 2026-07-01 to work around MO2 CLI space-in-path bug.

```powershell
New-Item -ItemType Junction `
  -Path "<PATH_TO_STEAM_LIBRARY>\steamapps\common\SSEData" `
  -Target "<PATH_TO_STEAM_LIBRARY>\steamapps\common\Skyrim Special Edition" `
  -Force
```

## Usage

```js
xedit_start({
  dataPath: "<PATH_TO_STEAM_LIBRARY>\\steamapps\\common\\SSEData\\Data",
  // ... other params
})
```

## Paths resolved

| Junction | Target |
|---|---|
| `H:\...\common\SSEData` | `H:\...\common\Skyrim Special Edition` |
| `H:\...\common\SSEData\Data\` | `H:\...\common\Skyrim Special Edition\Data\` |

## Removal

```powershell
Remove-Item "<PATH_TO_STEAM_LIBRARY>\steamapps\common\SSEData"
```
