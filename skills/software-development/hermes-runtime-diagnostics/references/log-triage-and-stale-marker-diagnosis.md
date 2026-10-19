# Hermes Log Triage and Stale-Marker Diagnosis

Use this reference for broad requests such as “check the logs” when no narrower symptom is supplied. The goal is to identify the current owning runtime, distinguish active faults from historical noise, and report evidence without changing state.

## 1. Fix the scope

1. Resolve the active home from `HERMES_HOME`; do not assume a default location.
2. Record the active profile, process/surface, and latest startup time before interpreting errors.
3. Treat each profile’s `logs/`, provider state, and Desktop backend as separate scopes. Never merge a named-profile error into the default profile’s diagnosis.

On Windows, a zero-result recursive search is not proof that logs are absent. First verify the resolved home and directory existence. If a file-search path is normalized inconsistently, enumerate filenames and mtimes with a bounded Python `os.walk`, skipping dependency/cache trees, then read only the selected files with the normal file-reading tool.

## 2. Establish the current-runtime cutoff

Read the recent tail of the principal logs together:

- `logs/gateway.log`
- `logs/errors.log`
- `logs/agent.log`
- `logs/gateway-stdio.log`
- `logs/desktop.log` or `logs/gui.log` when that surface is involved
- `logs/mcp-stderr.log` only when MCP startup or tool availability is relevant

Find the most recent `Starting Hermes Gateway` or backend-ready event. Classify findings after that timestamp as active; describe older entries as historical unless the same failure recurs after the cutoff. Also record each principal log's first-line timestamp (and the `.__*` lock mtimes): a rotated/recreated file proves only its own window, so 'zero occurrences' of an old signature is never global — cross-check rotated siblings before declaring a class of errors gone. For per-session tallies, session ids look like `YYYYMMDD_HHMMSS_<hex>`; keep hex letters in the regex (`grep -oE '[0-9]{8}_[0-9]{6}_[0-9a-f]{6}'`) — a digits-only pattern silently yields zero matches. Any signature reported as still active must show a second, later count: report the growth, not a snapshot.

Useful health evidence includes a completed startup, expected adapter connections, adapter `Ready`, and a real inbound-message lifecycle. One current inbound message is stronger evidence than an old clean-exit record.

## 3. Diagnose state-file loops, not just log lines

### Deferred update notifications

Repeated `Update notification deferred: <platform> adapter not connected yet` entries normally mean the retry loop is preserving completion markers until the target adapter returns. Inspect only metadata for:

- `.update_pending.json`
- `.update_pending.claimed.json`
- `.update_exit_code`
- `.update_output.txt`
- `.update_prompt.json`

Report marker age, target platform, whether a chat target exists, and exit code. Do not print chat IDs or captured update output. A marker that predates the current gateway by days and targets an unavailable adapter is a stale-state/log-flood diagnosis; diagnosis-only work must not delete it.

### Provider manifest/database mismatch

For `manifest exists but canonical memory.db is missing`:

1. Verify the exact profile-local provider directory.
2. Read the manifest’s declared canonical filename.
3. Confirm the file is absent rather than relying on the warning alone.
4. Locate candidate backups by path, mtime, and size only.
5. Do not restore automatically: a backup may be older than file-authoritative Markdown content or belong to a different profile/schema generation.

Report the functional impact narrowly: provider initialization and its dependent memory/context lifecycle are unavailable; this does not by itself prove the gateway or messaging adapter is down.

## 4. Separate expected noise from incidents

- MCP `ready` followed by `binding=unbound` is a readiness/binding fact, not a crash.
- “No indexed repos yet” is setup state, not an MCP transport failure.
- Desktop idle-profile reaping and nonzero child exits are not a current Gateway crash unless the owning backend was still active or immediately restarted unexpectedly.
- `Iteration budget exhausted` indicates a non-converging agent run. Correlate it to the same session/process before treating it as the user’s current incident.
- Adapter reconnects and clean WebSocket closes are historical transport events unless they prevent a later `Ready` state.

## 5. Privacy-safe extraction

Raw stdio logs may contain query-string credentials or platform connection parameters even when normal application logs are redacted. Never paste entire lines from connection URLs. Project only timestamp, component, severity, event class, exit code, and non-secret state flags. Avoid message bodies, chat IDs, access keys, tokens, and full command lines.

## Report contract

Lead with current health, then list active faults in priority order. For each fault include:

- exact log signature and most recent timestamp;
- corroborating file/runtime state;
- scoped impact;
- whether a reversible recovery artifact exists;
- whether any state was changed.

Finish with secondary historical findings only when they materially explain the situation. A successful log review does not require repair; it requires a current-runtime cutoff, direct corroboration, and no cross-profile or privacy leakage.
