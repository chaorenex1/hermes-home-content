# Dedicated SQLite persistence for a planning loop

Use this pattern when a planning mode must persist outside Hermes' shared `state.db` while retaining the existing `SessionDB` schema, locking, WAL fallback, and metadata API.

## Storage contract

- Resolve the active profile with `get_hermes_home()`.
- Put the database at `<HERMES_HOME>/<requested-name>.db` (for Ralph: `harness.db`).
- Instantiate `SessionDB(db_path=home / "harness.db")` explicitly.
- Cache by resolved Hermes-home path, not globally, so profile switches cannot share a connection.
- Store mode records under a namespaced key such as `ralph:<session_id>` in `state_meta`.

Do **not** rely on `SessionDB()` when testing a dynamically changed `HERMES_HOME`: `DEFAULT_DB_PATH` may have been computed when `hermes_state` was imported. Passing `db_path` explicitly makes runtime/profile intent and tests deterministic.

## One-way legacy migration

On first database access:

1. Open the dedicated database.
2. If `<HERMES_HOME>/state.db` exists, open it explicitly with `SessionDB(db_path=legacy_path)`.
3. Select only the old namespace (`WHERE key LIKE 'ralph:%'`).
4. Copy a row only when the destination has no value for that key.
5. Keep migration best-effort and logged; failure to migrate must not corrupt or overwrite newer dedicated state.

This is an idempotent copy-forward migration. Do not delete legacy rows during normal startup; deletion makes rollback harder.

## Verification recipe

Use three levels of evidence:

1. **Syntax:** compile the changed module and test module.
2. **Targeted behavior:** verify creation, write/read recovery, and legacy migration.
3. **Direct smoke:** under a temporary `HERMES_HOME`, start a state record and print/assert:
   - database basename is the requested name;
   - database file exists;
   - reloaded state has the same durable identifier.

Also run `git diff --check` for the touched files. If the broader pre-existing test file has an unrelated failing assertion, report it separately and do not represent the whole file as passing; provide the exact targeted tests that passed.

## Common pitfalls

- A bulk replacement of `_get_session_db()` can accidentally alter the migration source and make it recursively read the destination. Re-read the migration block after replacement.
- A shell variable embedded inside a quoted Python snippet may not resolve to the same path Hermes sees. For smoke tests, create/set the temporary path inside Python and inspect `db.db_path` directly.
- Creating a full `SessionDB` for a dedicated state namespace reuses the complete Hermes schema. This is pragmatic and compatible, but record the tradeoff if database size or schema coupling becomes relevant; a narrow store may be preferable later.
