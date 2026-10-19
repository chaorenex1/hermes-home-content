# Profile-local state recovery and stale marker cleanup

Use this reference when Hermes logs show a profile-scoped provider cannot initialize because a manifest exists but its canonical database is missing, or when a completed/failed operation leaves marker files that cause repeated gateway notifications.

## Scope and diagnosis

1. Resolve the active profile home from `HERMES_HOME`; do not infer it from a generic home path.
2. Correlate the warning to one profile, process, and provider. Confirm the manifest/database mismatch on disk.
3. Distinguish active faults from historical log entries. Record the latest matching line and later prove that the count stops increasing.
4. Inspect marker metadata without printing recipient IDs, tokens, captured output, or message bodies.

## Restore a file-authoritative profile safely

Prefer the provider's whole-profile archive over copying a loose `memory.db`. A file-authoritative provider needs its database, manifest, configuration, prompts, and authoritative Markdown to remain mutually consistent.

1. Select the newest valid whole-profile archive for the affected profile.
2. Preflight the archive before mutation:
   - entries are confined beneath `lancedb-memory/`;
   - `lancedb-memory/manifest.json` and `lancedb-memory/memory.db` exist;
   - the manifest names `memory.db` as the canonical store;
   - archive schema version is compatible with the installed provider;
   - SQLite `PRAGMA quick_check` returns `ok`;
   - expected authoritative Markdown entries are present.
3. Preserve the broken state first:

   ```bash
   hermes lancedb backup --archive "C:/path/to/backups/lancedb-memory-broken-before-restore-<UTC>.zip"
   ```

4. Restore through the provider CLI so replacement is staged, confined, and rollback-safe:

   ```bash
   hermes lancedb restore --archive "C:/path/to/validated-profile-archive.zip" --confirm
   ```

   The restore implementation also preserves the prior state as a timestamped sibling directory. Do not replace only `memory.db` unless no whole-profile archive exists and compatibility has been independently proved.
5. Initialize and verify through the supported surface:

   ```bash
   hermes lancedb status
   hermes lancedb verify
   ```

6. Require all of the following evidence:
   - status reports `ok=true` and the installed schema version;
   - verify reports `ok=true` with no projection/hash/metadata drift;
   - SQLite `PRAGMA quick_check` and `PRAGMA integrity_check` return `ok`;
   - migration versions are complete through the current schema;
   - one live provider read such as `kb_tree` succeeds.

A successful SQLite check alone is insufficient: it proves the database file, not the file-authoritative repository or live provider binding.

## Clean stale operation markers without restarting the gateway

Typical update markers include:

- `.update_pending.json`
- `.update_pending.claimed.json`
- `.update_exit_code`
- `.update_output.txt`
- `.update_prompt.json`
- `.update_response`

1. Confirm the pending marker is stale by comparing its modification time, exit state, target adapter availability, and current operation status.
2. Move all related markers into a timestamped backup directory instead of deleting them outright.
3. The gateway may rename `pending` to `claimed` while polling. Handle both names with bounded retries and re-check after a short wait; do not race with an unbounded loop.
4. Avoid restarting the gateway when moving the stale markers is sufficient.
5. Verify:
   - none of the marker names remains in the active profile home;
   - the repeated log signature count has zero growth over a bounded observation window;
   - normal platform traffic continues.

## Pitfalls

- Do not restore a database from a different profile.
- Do not trust filename recency alone; validate archive contents and SQLite integrity.
- Do not treat old warnings remaining in append-only logs as repair failure. Prove no new occurrences after the repair boundary.
- Do not expose `chat_id`, session keys, provider credentials, update output, or memory bodies in diagnostics.
- Remember that archive timestamps may be UTC while gateway log timestamps are local.
