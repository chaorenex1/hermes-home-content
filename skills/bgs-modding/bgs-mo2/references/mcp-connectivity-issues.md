# MCP Transport Connectivity Issues

## Symptoms

| In Hermes tool calls | What it means |
|---|---|
| `ClosedResourceError: ClosedResourceError()` | Hermes MCP client's stdio pipe to the Node.js server process is dead. The server process may still be running. |
| `MCP server 'bgs-*-mcp' is unreachable after N consecutive failures` | Same root cause — the client transport broke. Hermes auto-retries every ~15s (exponential backoff), but the dead pipe won't magically revive. |
| `hermes mcp test <name>` succeeds but tool calls still fail | The `test` command spawns a fresh process with its own connection. The main Hermes session still has the stale pipe. |

## Diagnosis

1. **Check if server processes are alive:**
   ```bash
   tasklist | grep -i "node\|xEdit64\|xEdit"
   ```
   If processes show but tool calls fail → MCP transport is dead (not the server).

2. **Test connectivity from a fresh context:**
   ```bash
   hermes mcp test bgs-mo2-mcp
   hermes mcp test bgs-xedit-mcp
   ```
   If this succeeds (lists tools) → servers are healthy, only the Hermes session pipes are stale.

## Recovery

**Option A — Terminal kick (most reliable, no session restart):**
```bash
hermes mcp test bgs-mo2-mcp
```
This creates a fresh stdio connection. In practice, this often resets Hermes's internal MCP client state, and subsequent tool calls in the same session start working again.

**Option B — In-session reload (slash command):**
```
/reload-mcp
```
Reloads all MCP server connections without restarting the session. Equivalent to `hermes mcp test` for all servers at once.

**Option C — Restart the Hermes session** if neither A nor B works.

## Prevention Notes

- This has been observed with both `bgs-mo2-mcp` and `bgs-xedit-mcp`. The KB MCP (`bgs-kb-mcp`) is less prone because its connection is stateless and short-lived.
- xEdit MCP is especially vulnerable — the daemon launch takes 30-90 seconds (large load orders), and the MCP transport can time out or break during the startup window.
- If `xedit_status` shows `starting` for >90 seconds then flips to `ClosedResourceError`, the daemon may have launched but the MCP pipe died. Check `tasklist` for `xEdit.exe`/`xEdit64.exe` — if running, use `/reload-mcp` and try again.
