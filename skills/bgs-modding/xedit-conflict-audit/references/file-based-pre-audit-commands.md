# File-Based Pre-Audit Command Patterns

Exact shell command recipes for the Phase B analysis in `xedit-conflict-audit` fallback section.
All commands assume `cd` into the profile directory (e.g. `<PATH_TO_MO2_INSTANCE>\profiles\pbr\`).

## Basic counts

```bash
# Enabled plugins count
grep -c '^\*' plugins.txt

# Disabled plugins count + listing with line numbers
grep -c '^[^*#]' plugins.txt
grep -n '^[^*#]' plugins.txt

# Total lines (includes comment header)
wc -l plugins.txt
```

## Category hotspot scan

Run one block per conflict domain. Pipe through `tail -10` to see last-loading (winning) plugins.

```bash
cd "<PATH_TO_MO2_INSTANCE>/profiles/pbr" && {
echo "=== 吸血鬼/Sacrosanct ==="
grep -i "sacrosanct\|vampire\|vampiric\|sanguinare" plugins.txt | tail -10
echo ""
echo "=== 水体/Water ==="
grep -i "water" plugins.txt | tail -10
echo ""
echo "=== 光照/Lux ==="
grep -i "lux" plugins.txt | tail -10
echo ""
echo "=== NPC ==="
grep -iE "npc|modpocalypse|bijin|pandorable" plugins.txt | tail -10
echo ""
echo "=== 动画/战斗 ==="
grep -iE "mco|attack|dodge|precision|combat|animation|oar" plugins.txt | tail -10
echo ""
echo "=== OStim ==="
grep -i "ostim\|oromance\|ovirgin\|oblush\|ocum\|odrain\|obottom" plugins.txt | tail -10
echo ""
echo "=== 外观/UBE ==="
grep -i "ube\|cbb\|3ba\|body\|hair\|eye\|makeup\|skin" plugins.txt | tail -10
```

## Winner-zone dump (last 30 enabled plugins)

```bash
TOTAL=$(grep -c '^\*' plugins.txt)
grep '^\*' plugins.txt | tail -30 | nl -v $((TOTAL - 29))
```

## Installed-but-not-activated cross-reference

```bash
# Check if a known mod's plugin exists in plugins.txt
grep -c -i "lux" plugins.txt          # count matches
grep -in "lux" plugins.txt            # show with line numbers

# Verify mod folder exists
find "<PATH_TO_MO2_INSTANCE>/mods" -maxdepth 2 -name "Lux.esp" 2>/dev/null

# Check meta.ini for version info
head -10 "<PATH_TO_MO2_INSTANCE>/mods/Lux/meta.ini"
```

## Order anomaly scan

```bash
# Check where a key plugin loads (line number)
grep -n "NAT-ENB" plugins.txt

# Check for weather mods loading order
grep -in "nat\|weather\|storm\|cabbage\|cathedral\|obsidian" plugins.txt | head -20
```

## Disabled plugin master-dependency check

```bash
# List all disabled with line numbers
grep -n '^[^*#]' plugins.txt

# Check if any enabled plugin references a disabled one (simple grep)
# For each disabled plugin name, grep for it in enabled plugins:
DISABLED_NAME="Half Dragon High Poly Head.esp"
grep -c "$DISABLED_NAME" plugins.txt   # should be 0 if only the disabled line matches
```

## Full-plugin list with enriched metadata

Use MO2 MCP (not shell) for enriched data:

```
mo2_pluginlist({ profile: "<name>", enrich: true })
mo2_assets_conflicts({ profile: "<name>", max_results: 5000 })
mo2_plugin_warnings()   # live-only, may fail if MO2 not running
```

## Category keyword reference

| Domain | grep keywords |
|---|---|
| Water | `water\|waterfall\|river\|lake\|ocean\|pond\|creek` |
| Lighting | `lux\|light\|elfx\|lantern\|candle\|torch\|window\|emitter\|ambient\|shadow` |
| NPC | `npc\|serana\|lucien\|inigo\|modpocalypse\|bijin\|pandorable` |
| Landscape | `landscape\|terrain\|grass\|tree\|flora\|mountain\|rock\|blended road` |
| Location | `city\|town\|village\|riften\|whiterun\|windhelm\|solitude\|markarth\|dawnstar\|winterhold\|morthal\|falkreath` |
| Combat | `combat\|attack\|dodge\|precision\|valhalla\|strike\|blade\|scar` |
| Vampire | `vampire\|sacrosanct\|drain\|vampiric\|blood\|sanguinare` |
| Animation | `animation\|anim\|fnis\|nemesis\|mco\|oar\|dar\|smooth\|pose` |
| Appearance | `hair\|eye\|brow\|makeup\|skin\|body\|face\|cbb\|3ba\|bbe\|ube` |
| UI | `ui\|hud\|menu\|interface\|icon\|widget\|map\|maid\|quickloot` |
| OStim | `ostim\|osex\|oromance\|ovirgin\|oinflat\|oblush\|ocum\|odrain\|obottom\|odevour\|osso` |
| LOD | `lod\|dyndolod\|xlodgen\|occlusion` |
