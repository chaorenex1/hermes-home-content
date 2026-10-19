# KB MCP: Version Upgrade & MCP Restart Workflow

## Symptom

`bgs_kb_status` reports 0 packs loaded with warnings:
```
Pack bgs-kb-core requires plugin >= 0.2.0; current is 0.1.0
Pack candidate at <path> has no manifest.json; skipped
```

## Root cause

The KB MCP `package.json` ships at `0.1.0`, but the KB packs declare
`minPluginVersion: "0.2.0"` in their manifests.

Additionally, packs extracted from zip may have nested structure:
- Actual: `pack/version/packName/manifest.json` + `pack/version/packName/kb.sqlite`
- Expected: `pack/manifest.json` + `pack/kb.sqlite`

## Fix steps (in order)

### 1. Bump KB MCP version and rebuild

```bash
cd "$HERMES_HOME/skills/bgs-modding/tools/bgs-kb-mcp"
sed -i 's/"version": "0.1.0"/"version": "0.2.0"/' package.json
npm run build   # tsc -p tsconfig.json
```

### 2. Fix pack structure (manifest + sqlite at pack root)

```bash
PACKS_ROOT="$HOME/.bgs-modding-superpowers/kb/packs"

# bgs-kb-core
cp "$PACKS_ROOT/bgs-kb-core/2026.06.23/core/manifest.json" "$PACKS_ROOT/bgs-kb-core/manifest.json"
cp "$PACKS_ROOT/bgs-kb-core/2026.06.23/core/kb.sqlite" "$PACKS_ROOT/bgs-kb-core/kb.sqlite"

# bgs-kb-skyrim (adjust version as needed)
cp "$PACKS_ROOT/bgs-kb-skyrim/2026.06.02/bgs-kb-skyrim/manifest.json" "$PACKS_ROOT/bgs-kb-skyrim/manifest.json"
cp "$PACKS_ROOT/bgs-kb-skyrim/2026.06.02/bgs-kb-skyrim/kb.sqlite" "$PACKS_ROOT/bgs-kb-skyrim/kb.sqlite"
```

### 3. Kill stale MCP Node processes

Write a short PowerShell script and run it:

```powershell
# save to %TEMP%/kill_kb_mcp.ps1
$procs = Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object { $_.CommandLine -like '*bgs-kb-mcp*' }
foreach ($p in $procs) {
    Stop-Process -Id $p.ProcessId -Force
    Write-Host "Killed PID $($p.ProcessId)"
}
```

```bash
powershell -ExecutionPolicy Bypass -File "$TEMP/kill_kb_mcp.ps1"
```

### 4. Restart the MCP server in Hermes

**Critical**: Hermes does NOT have `hermes mcp restart`. Must remove + re-add.

**Also critical**: The active Hermes profile may override the global config.
Check if the profile has its own `config.yaml` with a different `mcp_servers` block:
`$HOME/AppData/Local/hermes/profiles/<profile>/config.yaml`

If the global config has the server but `hermes mcp list` doesn't show it, the
profile config is missing the entry. Use `hermes config set`:

```bash
hermes config set mcp_servers.bgs-kb-mcp.command node
hermes config set mcp_servers.bgs-kb-mcp.args.0 "C:/Users/.../bgs-kb-mcp/dist/index.js"
hermes config set mcp_servers.bgs-kb-mcp.timeout 120
```

If `hermes mcp add` fails with `PermissionError` (config locked by running
Hermes), fall back to `hermes config set` which writes atomically.

To properly register with tool discovery, do:
```bash
echo "y" | hermes mcp remove bgs-kb-mcp
echo "y" | hermes mcp add bgs-kb-mcp --command node --args "<absolute-path>/dist/index.js"
```

The `echo "y"` auto-confirms both the remove prompt and the "Enable all N tools?" prompt.

### 5. Verify

```bash
hermes mcp list   # should show bgs-kb-mcp ✓ enabled
```

Then in the agent session: `bgs_kb_status({})` should show packs loaded.

Note: `hermes mcp add` may say "Start a new session to use these tools." If the
old MCP client connections are stale (ClosedResourceError), use `/new` in Hermes
TUI to start a fresh session.

## Deep dive: `resolvePluginRoot` depth bug (source fix applied)

The KB MCP's `readCurrentPluginVersion()` calls `resolvePluginRoot(import.meta.url)`
to find the plugin's `package.json` and read its version. The original code
hardcoded 4 `..` levels up from the calling module:

```
src/discovery/resolve-roots.ts (original, broken):
  resolve(dirname(moduleUrl), "..", "..", "..", "..")
```

From `dist/discovery/index.js`, 4 levels up lands at `skills/bgs-modding/` —
where there is no `package.json`. The function catches the error and falls back
to `"0.1.0"`, causing every pack to be rejected with `min_plugin_version_unmet`.

**Fix (applied 2026-07-01)**: walk upward looking for `package.json` (up to 8 levels):

```ts
export function resolvePluginRoot(moduleUrl: string): string {
  let dir = dirname(fileURLToPath(moduleUrl));
  for (let i = 0; i < 8; i++) {
    if (existsSync(resolve(dir, "package.json"))) return dir;
    dir = resolve(dir, "..");
  }
  return resolve(dirname(fileURLToPath(moduleUrl)), "..", ".."); // fallback
}
```

This is depth-adaptive: works for `dist/discovery/` (2 levels), `src/discovery/`
(2 levels), or any deeper bundler nesting. After applying, rebuild with
`npm run build`.

If you see `current is 0.1.0` even after bumping `package.json` AND rebuilding,
the running process still has the old `resolvePluginRoot` logic in memory. Kill
processes and restart MCP per steps 3-4 above.

## Common pitfalls

- **PermisionError on save**: The running Hermes process may lock the profile
  config. Use `hermes config set` instead of `hermes mcp add` for the initial
  config write, then remove+add to trigger tool discovery.
- **Profile vs global config**: The active Hermes profile's `config.yaml` is at
  `~/.hermes/profiles/<profile>/config.yaml`. `hermes mcp list` reads from the
  profile config, not the global one at `~/.hermes/config.yaml`.
- **npm rebuild required**: After bumping `package.json` version, must run
  `npm run build` to recompile the `dist/` TypeScript output. The old dist
  cached the `0.1.0` fallback.
- **Multiple zombie processes**: Killing one process may leave others. The
  PowerShell script above kills ALL matching processes.
