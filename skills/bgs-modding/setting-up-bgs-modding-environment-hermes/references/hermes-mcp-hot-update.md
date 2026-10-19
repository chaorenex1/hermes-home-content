# Hermes MCP Hot-Update Recipe

How to sync source-file changes into a running Hermes install and reload the MCP
server without restarting the entire application.

## Where Hermes loads MCP from

Hermes MCP servers point at compiled JS in the **global** skills tree:

```
bgs-xedit-mcp:  %LOCALAPPDATA%/hermes/skills/bgs-modding/tools/xedit-mcp/dist/index.js
bgs-mo2-mcp:    %LOCALAPPDATA%/hermes/skills/bgs-modding/tools/mo2-mcp/dist/index.js
bgs-kb-mcp:     %LOCALAPPDATA%/hermes/skills/bgs-modding/tools/bgs-kb-mcp/dist/index.js
```

On Windows: `%LOCALAPPDATA%` = `C:\Users\<user>\AppData\Local`.

Source files live under `tools/<mcp>/src/` and `tools/mo2-vfs-launcher/`.

## Dual sync target

Per `hermes-skill-paths.md`, Hermes uses TWO skill directories:

| Tier | Path | When MCP reads from it |
|------|------|------------------------|
| Global | `%LOCALAPPDATA%/hermes/skills/bgs-modding/` | YES — this is what `config.yaml` `mcp_servers` args point at |
| Profile-specific | `%LOCALAPPDATA%/hermes/profiles/<profile>/skills/bgs-modding/` | NO for MCP runtime — but skills/setup scripts may reference it |

**Always sync to the global dir first.** Sync to profile-specific dir as well for
consistency (the curator expects both to match).

## Step-by-step hot-update

### 1. Copy source files from dev checkout to Hermes install

```bash
SRC="C:/Users/<user>/Documents/aduib-app/bgs-modding-superpowers"
DST="C:/Users/<user>/AppData/Local/hermes/skills/bgs-modding"

# PowerShell scripts
cp "$SRC/tools/mo2-vfs-launcher/lib/xedit-client.launch.ps1" "$DST/tools/mo2-vfs-launcher/lib/"

# TypeScript sources
cp "$SRC/tools/xedit-mcp/src/launch.ts" "$DST/tools/xedit-mcp/src/"
cp "$SRC/tools/xedit-mcp/src/index.ts" "$DST/tools/xedit-mcp/src/"
```

### 2. Rebuild TypeScript in Hermes install

```bash
cd "$DST/tools/xedit-mcp"
npm install    # if node_modules missing
npm run build  # tsc -p tsconfig.json
```

### 3. Restart the MCP server

```bash
echo "y" | hermes mcp remove bgs-xedit-mcp
echo "y" | hermes mcp add bgs-xedit-mcp --command node --args "$DST/tools/xedit-mcp/dist/index.js"
```

## Pitfall: `hermes mcp add` strips env vars

**`hermes mcp add` replaces the entire MCP entry** — it does not merge env vars.
If the entry had an `env:` block, it will be gone after `mcp add`.

To restore env vars, use `hermes config set` AFTER the add:

```bash
hermes config set mcp_servers.bgs-xedit-mcp.env.BGS_MO2_ROOT "H:\\path\\to\\mo2"
hermes config set mcp_servers.bgs-xedit-mcp.env.BGS_MO2_PROFILE "pbr"
# ... etc for all env vars
```

Since Hermes MCP servers are persistent processes, the new env vars won't take
effect until the NEXT `hermes mcp remove` + `hermes mcp add` cycle — or the
next Hermes session start. Plan for two cycles when env vars changed:
1. `mcp add` → creates entry without env → `config set` → adds env to config
2. `mcp remove` + `mcp add` → picks up env from config

If Hermes shows `config.yaml is locked by running process`, edit the YAML
directly and restart.

## Verification

```bash
# Confirm compiled JS has the change
grep "instanceRoot\|mo2-instance-root\|mo2InstanceRoot" "$DST/tools/xedit-mcp/dist/launch.js" "$DST/tools/xedit-mcp/dist/index.js"

# Confirm config has env block
grep -A 15 "bgs-xedit-mcp" "$LOCALAPPDATA/hermes/profiles/bgs-modding/config.yaml"
```

## When to use this vs full Hermes restart

Use hot-update for:
- Source-code changes to MCP tool implementations
- PowerShell launch-script changes
- Adding new MCP tool parameters

Use full Hermes restart for:
- Config.yaml structural changes outside `mcp_servers`
- New MCP servers added for the first time
- If the hot-update cycle fails 2+ times
