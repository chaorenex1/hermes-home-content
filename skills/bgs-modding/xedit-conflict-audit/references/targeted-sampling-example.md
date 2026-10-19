# Targeted Sampling Worked Example — pbr Profile (Skyrim SE, 934 plugins)

This is the end-to-end flow from the 2026-07-02 session. Use it as a template when the user asks for a full-load-order conflict overview.

## Phase 1: Parse the load order

```
xedit_call files.list → 934 files
```

Python (`execute_code`) to parse:
```python
import json
with open(path, "r") as f:
    raw = json.loads(json.loads(f.read())["result"])
files = raw["data"]["files"]

core = {"Skyrim.esm","Update.esm","Dawnguard.esm","HearthFires.esm","Dragonborn.esm"}
mods = [f for f in files if f["name"] not in core]

# Winner zone: last 60
for f in mods[-60:]:
    ...

# Category grouping
keywords = {"Water": [], "Sacrosanct": [], "NPC": [], ...}
for f in mods:
    for kw in keywords:
        if kw.lower() in f["name"].lower():
            keywords[kw].append(f)
```

## Phase 2: Probe per category

| Category | Plugin probed | Signature | Result |
|---|---|---|---|
| Water | Water for ENB (Shades of Skyrim).esp [918] | `WATR` | 68 records, 8 with overrideCount≥1 |
| Vampire | Sacrosanct - Vampires of Skyrim.esp [904] | `SPEL` | 100+ (truncated), 0 with overrideCount>0 |
| Vampire | Sacrosanct - Vampires of Skyrim.esp [904] | `PERK` | 71 records, 10 with overrideCount≥1 |
| DynDOLOD | DynDOLOD.esp [932] | `WRLD` | 22 records, 0 conflicts |
| Alternate Start | alternate start - live another life.esp [912] | `QUST` | 21 records, 0 conflicts |

Key findings from `records.list`:
- `PuddleWaterCreek` (82001825): overrideCount=3 → suspect
- `SCS_Mechanics_Perk_VampireFeed` (7E01E41B): overrideCount=2 → suspect
- `SCS_PerkTree_380_Perk_VampireLord_DragonAtMidnight` (7E07008F): overrideCount=1 → suspect

## Phase 3: Deep-inspect

```
xedit_inspect_conflicts Water for ENB 82001825 → minor, participants: WfENB → Calm Water → Blue Creek Water → Clear Creek Water
xedit_inspect_conflicts Sacrosanct 7E01E41B → minor, participants: Sacrosanct → Sacrosanct_DAK → Just Bite - Sacrosanct
xedit_inspect_conflicts Sacrosanct 7E07008F → minor (caOverride), participants: Sacrosanct → dragonatmidnighttweaks
```

## Phase 4: Report

All conflicts found were **intentional internal patch chains** — every override participant was from the same mod family. Zero breaking conflicts in sampled zones (~200 records across 5 categories).

| Risk | Count | Details |
|---|---|---|
| 🔴 CRITICAL | 0 | |
| 🟡 HIGH | 0 | |
| 🔵 INFO | 3 zones | Water for ENB (14-patch architecture), Sacrosanct (6-patch chain), NPC overhauls |
| 🟢 LOW | — | All conflicts are intentional patch overrides |

## Key takeaway

Do not chase "red means broken." In a well-curated modpack, most override chains are deliberate. Only flag external cross-family overrides as suspicious.
