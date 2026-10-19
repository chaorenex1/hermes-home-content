# Multi-Type ESP Conflict Audit — Proven Pattern

Derived from a 934-plugin SkyrimSE pbr profile audit (2026-07-02).

## The progressive-layered approach

DO NOT start with a full WRLD `conflict_status` — it will crash the MCP on large load orders.
Instead, use this 4-phase progressive approach:

### Phase 1: Signature-targeted sampling (SPEL/PERK)
Pick the most conflict-prone record types for the mods you know are loaded.
- Query `records.list` on specific plugins + specific signatures
- Look for `overrideCount > 0` as conflict indicators
- Use `xedit_inspect_conflicts` on records with non-zero overrideCount
- Most will be `minor` — internal patch chains are normal

### Phase 2: WRLD summary only
- Use `records.conflict_status` on the worldspace FormID (e.g. Tamriel `0000003C`)
- Read ONLY the `childGroup.signatures` block — do NOT expand `conflictingHits`
- This gives per-signature totals: CELL 5710/11187, REFR 37792/284482, etc.
- 95%+ of these are `caOverride` (different mods touching different cells) — normal

### Phase 3: Targeted CELL/REFR inspection
- Use `records.list` on specific plugins by signature (e.g. Water for ENB CELL records)
- Inspect conflicts for records with non-zero overrideCount
- Check WINNER is the intended mod

### Phase 4: Other record types (LVLI/KYWD/NPC_)
- Same pattern: `records.list` on key plugins → inspect non-winning records
- LVLI: check if leveled list overrides are intended (e.g. LotDB book system)
- KYWD: most keyword distribution mods create NEW records — zero conflicts
- NPC_: NPC overhaul conflicts are typically just appearance precedence

## Verdict framework

| Verdict | Criteria | Action |
|---|---|---|
| `no_conflict` | Single mod touches record | Accept |
| `minor` / `caOverride` | Internal patch chain or intentional ordering | Accept |
| `minor` / `caConflict` | Two mods fight; patch is the right winner | Accept if patch is correct |
| `breaking` | Two mods carry needed split data | PATCH needed |

## When to make a patch

Only when: multiple plugins carry NEEDED data for the same FormID AND sorting
would lose required behavior either way. Do NOT patch:
- Internal patch chains (e.g. Water for ENB → 14 regional patches)
- Intentional precedence (e.g. USSEP → LotDB leveled list control)
- Appearance overhauls overriding each other (e.g. Modpocalypse → PAN)

## Asset-level conflicts (NIF/texture)

For file-level NIF/texture conflict detection, use MO2 VFS tools:
- `mo2_assets_conflicts({ path_prefix: "meshes", ... })` — which mod's NIF wins
- `mo2_assets_resolve({ virtual_path: "meshes/.../file.nif" })` — trace a specific NIF

For INTERNAL NIF analysis (BSLightingShaderProperty, NiNode skeleton, bhkCollisionObject),
NifSkope or pyffi/nifly is required. The MO2 VFS surface is file-level only.
