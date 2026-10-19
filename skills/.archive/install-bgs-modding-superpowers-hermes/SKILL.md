---
name: install-bgs-modding-superpowers-hermes
description: "Use when the user says '在hermes安装bgs-modding-superpowers' or 'install bgs-modding-superpowers into Hermes' — copies ALL skills, tools, and scripts into HERMES_HOME, builds each tool by type, and registers the 3 MCP servers in config.yaml via the hermes config CLI."
version: 1.2.0
author: BGS Modding Team
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [bgs-modding, superpowers, installation, hermes, mcp]
    related_skills: [using-bgs-modding-superpowers, setting-up-bgs-modding-environment]
---

# Install bgs-modding-superpowers for Hermes

Copies the bgs-modding-superpowers skills and ALL tools into the local Hermes environment, builds each tool based on its type, then registers the 3 MCP servers in Hermes `config.yaml` using the `hermes config set` CLI (not direct file edits, which Hermes rejects as security-sensitive).

## When to Use

- "在hermes安装bgs-modding-superpowers"
- "install bgs-modding-superpowers into Hermes"
- "set up bgs superpowers for Hermes"
- First-time setup of BGS modding tools in a Hermes profile
- Reinstall after a plugin update or skill tree corruption

## Source Layout

The repo must contain at least:

```
bgs-modding-superpowers/
├── skills/            # skill subdirectories (each with SKILL.md)
├── scripts/           # helper PowerShell/Python/shell scripts
└── tools/
    ├── bgs-archive/         # Rust CLI (cargo build --release)
    ├── bgs-kb-mcp/          # Node.js MCP server (npm install + build)
    ├── bgs-papyrus/         # Python (pip install -e .)
    ├── bgs-translator/      # Python (may require >=3.12 widening on 3.11)
    ├── mo2-assets-engine/   # Python (pip install -e .)
    ├── mo2-control-plane/   # mixed (broker + live-bridge, no top-level build)
    ├── mo2-mcp/             # Node.js MCP server (npm install + build)
    ├── mo2-mcp-sidecar/     # Python (pip install -e .)
    ├── mo2-vfs-launcher/    # PowerShell/script (no build)
    ├── xedit-hook-bridge/   # Legacy Delphi DLL (copy only, do not build)
    └── xedit-mcp/           # Node.js MCP server (npm install + build)
```

Destination layout:

```
$HERMES_HOME/skills/bgs-modding/
├── <skill-name>/          # one directory per skill
├── scripts/               # helper scripts from repo scripts/
└── tools/
    ├── bgs-archive/...
    ├── bgs-kb-mcp/...
    ├── ...
    └── xedit-mcp/...
```

## Step 1 — Validate repo root

```bash
test -d skills/using-bgs-modding-superpowers && test -d tools/xedit-mcp && echo "OK" || echo "NOT-REPO"
```

If not in the repo, ask the user for the absolute path, then `cd` there. Do not proceed without confirming `skills/` and `tools/xedit-mcp/` exist.

## Step 2 — Determine HERMES_HOME

```bash
HH="${HERMES_HOME:-$HOME/.hermes}"
echo "$HH"
```

On Windows (MSYS/git-bash) `$HOME` expands to `/c/Users/<user>`. Store as `$HH`. The destination path must be the user's `.hermes` directory.

## Step 3 — Create category tree

```bash
rm -rf "$HH/skills/bgs-modding"
mkdir -p "$HH/skills/bgs-modding/tools"
mkdir -p "$HH/skills/bgs-modding/scripts"
```

A clean install removes the old `bgs-modding` skill tree first. If the user wants an in-place upgrade instead, ask before `rm -rf`.

## Step 4 — Copy skills

```bash
for dir in skills/*/; do
  name=$(basename "$dir")
  cp -r "$dir" "$HH/skills/bgs-modding/$name"
done
```

Count the copied directories; expect roughly the number of subdirectories in `skills/`, plus any extras from the repo's own skill set (e.g., `bgs-mo2`, `bgs-nexus-automation`).

## Step 5 — Copy tools (exclude build artifacts and node_modules)

```bash
for tool_dir in tools/*/; do
  name=$(basename "$tool_dir")
  [ "$name" = "node_modules" ] && continue
  rsync -a --exclude=node_modules --exclude=target --exclude=dist \
    "$tool_dir" "$HH/skills/bgs-modding/tools/$name" 2>/dev/null \
    || cp -r "$tool_dir" "$HH/skills/bgs-modding/tools/$name"
done
```

Excluding `target/`, `dist/`, and `node_modules/` avoids copying stale build artifacts. They will be rebuilt/installed in the destination.

## Step 6 — Build / install tools by type

### Rust

```bash
cd "$HH/skills/bgs-modding/tools/bgs-archive"
cargo build --release
```

Verify: `$HH/skills/bgs-modding/tools/bgs-archive/target/release/bgs-archive` (or `.exe` on Windows).

### Node.js MCP servers

```bash
for tool in xedit-mcp mo2-mcp bgs-kb-mcp; do
  cd "$HH/skills/bgs-modding/tools/$tool"
  npm install --ignore-scripts
  npm run build
  ls -la dist/index.js
done
```

Use `--ignore-scripts` first, then `npm run build` separately, because some tools have `prepare` scripts that run `build` and can fail on the first install pass.

### Python tools

```bash
for tool in bgs-papyrus bgs-translator mo2-assets-engine mo2-mcp-sidecar; do
  cd "$HH/skills/bgs-modding/tools/$tool"
  if [ "$tool" = "bgs-translator" ] && [ "$(python -c 'import sys; print(sys.version_info.minor)')" = "11" ]; then
    sed -i 's/^requires-python = ">=3.12"/requires-python = ">=3.11"/' pyproject.toml
  fi
  uv pip install -e . || python -m pip install -e .
done
```

`bgs-translator` may declare `requires-python = ">=3.12"`. If the active Hermes venv is Python 3.11, widen it in the target copy to `>=3.11` before installing, or the install will fail.

### No build needed

- `mo2-control-plane/` — copied as-is; sub-components are built/referenced by their own skills.
- `mo2-vfs-launcher/` — PowerShell scripts only.
- `xedit-hook-bridge/` — legacy Delphi DLL. Copy it but **do not try to build it**. It will not work without the matching xEdit fork and is documented for removal.

## Step 7 — Copy helper scripts

```bash
cp -r scripts/* "$HH/skills/bgs-modding/scripts/"
```

If the repo has scripts in a `scripts/` subfolder of a `plugins/` mirror (e.g., `plugins/bgs-modding-superpowers/scripts/`), copy the canonical repo `scripts/` directory, not the nested plugin copy, unless the user explicitly says otherwise.

## Step 8 — Register MCP servers in config.yaml

Only these 3 tools expose MCP servers and should be registered:

| Entry name | Entry point |
|---|---|
| `bgs-xedit-mcp` | `.../xedit-mcp/dist/index.js` |
| `bgs-mo2-mcp` | `.../mo2-mcp/dist/index.js` |
| `bgs-kb-mcp` | `.../bgs-kb-mcp/dist/index.js` |

Do NOT register non-MCP tools (bgs-papyrus, bgs-translator, mo2-assets-engine, mo2-mcp-sidecar, mo2-vfs-launcher, xedit-hook-bridge). They do not speak the MCP protocol and will crash Hermes startup.

**Use `hermes config set` — never write the file directly.** Direct edits to `config.yaml` are rejected by the patch/write tools as a security-sensitive configuration. Instead, run the CLI commands from the Hermes shell:

```bash
hermes config set mcp_servers.bgs-xedit-mcp.command node
hermes config set mcp_servers.bgs-xedit-mcp.args.0 "$HH/skills/bgs-modding/tools/xedit-mcp/dist/index.js"
hermes config set mcp_servers.bgs-xedit-mcp.timeout 600

hermes config set mcp_servers.bgs-mo2-mcp.command node
hermes config set mcp_servers.bgs-mo2-mcp.args.0 "$HH/skills/bgs-modding/tools/mo2-mcp/dist/index.js"
hermes config set mcp_servers.bgs-mo2-mcp.timeout 600

hermes config set mcp_servers.bgs-kb-mcp.command node
hermes config set mcp_servers.bgs-kb-mcp.args.0 "$HH/skills/bgs-modding/tools/bgs-kb-mcp/dist/index.js"
hermes config set mcp_servers.bgs-kb-mcp.timeout 600
```

The path must be absolute. On Windows, forward slashes (`C:/Users/...`) work fine in the `args` list and are easier to read in YAML. Verify with `hermes config show` or by reading `config.yaml` lines around `mcp_servers:`.

## Step 9 — Restart Hermes

Tell the user:

> Installation complete. Restart Hermes for MCP servers and new skills to take effect.

After restart, optionally run `hermes mcp list` to confirm the three BGS MCP servers appear.

## Verification Checklist

- [ ] `$HH/skills/bgs-modding/` exists with skill subdirectories
- [ ] `$HH/skills/bgs-modding/scripts/` exists with the helper scripts
- [ ] `$HH/skills/bgs-modding/tools/` contains all tool directories
- [ ] `bgs-archive` built: `target/release/bgs-archive` (or `.exe`) exists
- [ ] `xedit-mcp`, `mo2-mcp`, `bgs-kb-mcp` built: `dist/index.js` exists for each
- [ ] Python tools importable (e.g., `python -c "import bgs_papyrus, bgs_translator, mo2_assets_engine, mo2_mcp_sidecar"`)
- [ ] `config.yaml` has exactly 3 BGS MCP entries under `mcp_servers`
- [ ] MCP config paths are absolute
- [ ] No non-MCP tool appears in `mcp_servers`
- [ ] Hermes restarted and the three MCP servers show in `hermes mcp list`
- [ ] (deferred) Step 10 — `Mo2AssetsInspector/` deployed to MO2 plugins; requires known `<MO2_Root>`

## Step 10 — Deploy Mo2AssetsInspector support tree to MO2 plugins

The `mo2_assets_inspector` Python plugin (used by `mo2-control-plane`) relies on
a support tree at `<MO2_Root>/plugins/Mo2AssetsInspector/` with a vendored copy
of `mo2_assets_engine`. Failing to deploy this causes MO2 startup errors:

```
ModuleNotFoundError: No module named 'mo2_assets_engine'
```

The source lives in the bgs-modding tools tree. Deploy it:

```bash
SRC="$HH/skills/bgs-modding/tools/mo2-control-plane/live-bridge/mo2_assets_inspector"
DEST="<MO2_Root>/plugins/Mo2AssetsInspector"

mkdir -p "$DEST"
cp -r "$SRC"/* "$DEST/"

# Vendored mo2_assets_engine (from mo2-assets-engine/src/)
mkdir -p "$DEST/vendored"
cp -r "$HH/skills/bgs-modding/tools/mo2-assets-engine/src/mo2_assets_engine" "$DEST/vendored/"

# Clear MO2 plugin bytecode cache so the new code loads
rm -rf "<MO2_Root>/plugins/__pycache__"/*assets* 2>/dev/null
rm -rf "$DEST/__pycache__" 2>/dev/null
```

**Verification**: after MO2 restarts, the log should NOT contain `ModuleNotFoundError: No module named 'mo2_assets_engine'`.

**Why vendored, not pip-installed**: MO2's embedded Python may not share the
Hermes venv's site-packages. `archive_order.py` (the only module imported at
plugin init) uses stdlib only (`re`, `enum`), so no external deps are needed
for the vendored copy. Heavier modules (`types.py`, `profile.py`) are only
lazy-imported when the user opens the inspector window.

## Common Pitfalls

1. **Wrong `HERMES_HOME` on Windows.** Use `$HOME/.hermes` in MSYS/git-bash. Do not use `%USERPROFILE%` syntax in bash.
2. **Direct `config.yaml` edit rejected.** Hermes treats `config.yaml` as security-sensitive. Always use `hermes config set` for MCP registration.
3. **Node.js too old.** `xedit-mcp` and `bgs-kb-mcp` require Node >= 22. `mo2-mcp` needs >= 18. Check `node --version` first.
4. **npm install failure.** Some tools run `build` in `prepare`. Use `npm install --ignore-scripts` then `npm run build` separately.
5. **Python install on Windows with MSYS paths.** `uv pip install -e .` handles this more reliably than bare `pip install -e .` from an MSYS cwd. If `uv` fails, fall back to `python -m pip install -e .` with an absolute path.
6. **Only 3 MCP servers.** Registering non-MCP tools (e.g., `bgs-papyrus`) will cause Hermes startup failures.
7. **Relative paths in MCP config.** `node` will not resolve them when spawned as a subprocess. Use absolute paths.
8. **Stale build artifacts.** Exclude `node_modules/`, `target/`, and `dist/` when copying tools to avoid confusing failures from old builds.
9. **`bgs-translator` requires-python widening.** On Python 3.11, widen the target copy's `pyproject.toml` to `>=3.11` before installing.
10. **`xedit-hook-bridge/` is legacy.** Copy it, but do not attempt to build the Delphi DLL.
11. **Scripts directory confusion.** The repo may also have a nested `plugins/bgs-modding-superpowers/scripts/` copy. Use the top-level `scripts/` directory.
12. **lxml version conflict between pyfomod and bgs-translator.** `pyfomod` (dep of `mo2-mcp-sidecar`) requires `lxml<5,>=4`, while `nicegui` (dep of `bgs-translator`) requires `lxml>=6.1.0`. Installing them in the same venv causes pip dependency resolver errors. The current workaround: install `lxml>=6.1.0` (which satisfies `bgs-translator`) and accept the `pyfomod` declared-conflict warning. In practice, `pyfomod` functions correctly with lxml 6.x — the constraint is overly conservative. If `pyfomod` releases an updated version, remove this pitfall.

## See also

- `using-bgs-modding-superpowers` — per-session toolkit overview and hard rules.
- `setting-up-bgs-modding-environment` — first-run environment bootstrap after installation (MO2, xEdit, KB packs).
