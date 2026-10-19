# xEdit MCP Session-Timeout: Full Code Trace

Provenance: session 2026-07-02, pbr profile (934 plugins, SkyrimSE, tri-split layout).

## Trace: from `xedit_session` tool call to the 30s timeout

```
xedit_session (tool call)
  → toolset.invoke("xedit_session", args)          // index.js:883
    → buildContext({ adapter, sessionId })          // session.js:1
      → Promise.all([                               // 3 parallel calls
          adapter.call({ command: "system.describe" }),
          adapter.call({ command: "system.capabilities" }),
          adapter.call({ command: "files.list" }),   // ← this one times out
        ])
        → adapter.call(...)                          // daemon-adapter.js:19
          → runPwsh(pwsh, [                         // daemon-adapter.js:34
              "automation", "call",
              "--timeout-seconds", String(timeoutSeconds),  // ← 30
              ...
            ])
            → xedit-client.ps1 automation call       // xedit-client.ps1:27
              → Invoke-XeditClientAutomationCallCommand  // call.ps1:61
                → Invoke-XeditClientAutomationCall      // call.ps1:3
                  → $process.WaitForExit($TimeoutSeconds * 1000)  // 30s
```

## The two hardcoded 30s defaults

### Default 1: `daemon-adapter.js:14` (MCP side — the root cause)
```js
export function createPowershellAdapter(opts) {
    const timeoutSeconds = opts.timeoutSeconds ?? 30;  // ← HARDCODED 30
    // ...
}
```

`launchDaemon()` in `launch.js:112` calls `createPowershellAdapter` WITHOUT `timeoutSeconds`:
```js
const adapter = createPowershellAdapter({
    clientScript: opts.clientScript,
    pid: launchedPid,
    gameMode: opts.gameMode,
    scratchDir: join(tmpdir(), "xedit-mcp-calls", String(launchedPid)),
    pwshExe: pwsh,
    // timeoutSeconds: opts.timeoutSeconds,  // ← MISSING — never passed
});
```

Since `opts.timeoutSeconds` is never passed, it falls through to the `?? 30` default.

### Default 2: `xedit-client.call.ps1:10` (PS1 side — defense in depth)
```powershell
function Invoke-XeditClientAutomationCall {
    param(
        ...
        [int]$TimeoutSeconds = 30   # ← HARDCODED 30
    )
```

This is the default when `--timeout-seconds` is NOT explicitly provided. The MCP
always provides it (from default 1), so this default 2 is only hit when the MCP
somehow omits the flag — rare but worth patching for safety.

## Env var: why `BGS_XEDIT_READY_TIMEOUT_SECONDS` doesn't fix session timeout

`resolveLaunchOpts()` in `index.js:78` reads env vars for paths and game mode:
```js
function resolveLaunchOpts(overrides = {}) {
    const envClient = process.env.BGS_XEDIT_CLIENT_SCRIPT;
    const envLauncher = process.env.BGS_XEDIT_LAUNCHER_PATH;
    const envGameMode = process.env.BGS_XEDIT_GAME_MODE;
    // ... BGS_MO2_PROFILE, BGS_XEDIT_DATA_PATH, BGS_XEDIT_PLUGINS_FILE, BGS_MO2_ROOT
    // BGS_XEDIT_READY_TIMEOUT_SECONDS — NOT READ
}
```

The returned opts are used by `launchDaemon()` which reads `opts.readyTimeoutMs ?? 180_000`
for the daemon-launch poll loop — NOT for the automation-call timeout.

The env var does influence `Wait-XeditClientAutomationReady` in the PS1 (240s default),
which controls how long to poll for daemon liveness during launch, NOT how long to
wait for individual automation calls during session build.

## YAML quoting pitfall

Original config had:
```yaml
BGS_XEDIT_READY_TIMEOUT_SECONDS: '"300"'
```

In YAML, single-quoted `'"300"'` means the literal string value `"300"` (including
double-quote characters). When passed as a Node env var, this becomes `"300"` with
literal quotes, which fails `[int]` casts in PowerShell.

Fix: `hermes config set mcp_servers.bgs-xedit-mcp.env.BGS_XEDIT_READY_TIMEOUT_SECONDS 300`
— bare integer, no quotes.

## MCP restart: why `hermes config set` doesn't force cold reload

1. `hermes config set ...` writes config.yaml.
2. Hermes detects the change and reconnects the MCP transport (stdio).
3. The existing Node process is REUSED — it has the old JS modules cached.
4. `taskkill /F /IM node.exe` kills all Node processes, forcing Hermes to spawn
   fresh ones that load the patched dist files.

## Patching procedure (verified)

1. Patch `dist/daemon-adapter.js`: `?? 30` → `?? 300`
2. Patch `lib/xedit-client.call.ps1`: `TimeoutSeconds = 30` → `TimeoutSeconds = 300`
3. `xedit_stop({ force: true })` — stop any running daemon
4. `taskkill /F /IM node.exe` — kill all MCP processes
5. Wait 20-30s for Hermes to auto-restart MCP servers
6. Verify patches survived: `search_files` on both files
7. `xedit_start(...)` — with tri-split params
8. Wait 90-120s for daemon launch (934 plugins)
9. `xedit_session()` — should succeed in ~40-60s
