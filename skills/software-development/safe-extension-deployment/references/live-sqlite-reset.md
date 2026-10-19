# Live SQLite Reset for File-Authoritative Extensions

Use this when a local extension stores durable bodies in files but keeps rebuildable metadata, queues, leases, or projections in a profile-local SQLite database, and the user explicitly requests a database reset or rebuild.

## Applicability gate

Use this workflow only when all of the following are proved:

- authoritative content lives outside SQLite and will survive the reset;
- the reset scope is one verified profile/provider database;
- the user explicitly requested destructive reset/rebuild;
- a current schema initializer and integrity verifier exist;
- rollback artifacts can be created outside the live state directory.

If SQLite contains authoritative bodies, use a migration/restore workflow instead. Never infer that a database is disposable from its filename.

## Preflight and backups

1. Fix the source checkout, installed target, profile home, database path, importing process, and current schema version.
2. For an unversioned local plugin (`0.0.0`, no remote/release channel), define “latest” as the selected source tree. Compare source and installed trees by relative-path digest, excluding caches. If identical, do not churn the target or force a restart merely to copy the same bytes.
3. Run the provider source test suite before resetting live state.
4. Query every durable job/lease table for nonterminal work. Distinguish published rows such as `active` generations from executable jobs such as `pending`, `claimed`, or `running`.
5. Create both:
   - a whole-profile archive preserving Markdown, config, manifest, and database;
   - a consistent SQLite backup using `sqlite3.Connection.backup`, followed by `PRAGMA quick_check`.

Record exact rollback paths before mutation.

## Windows open-handle pattern

A live Windows host may keep `memory.db` open even when no WAL/SHM file exists and no job is running. `os.replace`, rename, or delete can then fail with `WinError 32`. Do not retry the same move, kill an unverified process, or delete around the lock.

When the database is explicitly rebuildable, reset it in place:

1. Build a clean temporary database with the currently installed schema initializer.
2. Verify the temporary database with the provider schema verifier.
3. Acquire the provider’s writer lock.
4. In the live database, terminalize any reset-owned nonterminal leases/jobs with a bounded operator-reset error. Prefer the provider API. If a continuously renewing job prevents a reset and the database is about to be replaced anyway, perform the guarded terminal transition in the same writer-lock critical section.
5. Commit and close the live transaction.
6. While still holding the writer lock, use SQLite’s backup API with the clean database as source and the live database connection as destination. This replaces database pages without renaming the open file.
7. Before releasing the lock, verify the rebuilt schema and zeroed control tables.

The critical invariant is one lock-protected transition: terminalize old work, then replace the live pages before another claimant can begin.

## Reconciliation and acceptance

Run these dependently, not in parallel:

1. provider `status`/initialization, which may recreate schema state and reconcile file projections;
2. provider `verify`, which must pass schema, manifest, file metadata, and content-hash checks;
3. direct SQLite `quick_check`/`integrity_check` as appropriate;
4. one live read of preserved authoritative content;
5. a fresh-process provider initialization/read smoke.

Capture counts twice:

- immediately after page replacement: queue/control/source-projection tables should be empty;
- after status reconciliation: only expected file-derived metadata should return, and no old nonterminal jobs should remain.

A reset-time worker can emit one lease-loss/conflict when its old binding observes the new database. Treat that as expected only if the job is terminal, no old row reappears, and provider error counts stop increasing during a bounded observation window.

## Smoke-test contamination pitfall

A “fresh provider” smoke that supplies an `agent_runner` can start background workers and create failed or queued jobs in the newly reset live database. Prefer an isolated temporary profile for lifecycle smokes. If the live profile must be used:

- restrict the smoke to read-only provider calls;
- shut the provider down deterministically;
- identify and remove only run-owned test jobs;
- re-run status and verify afterward.

Do not leave a test-created failure row and still report the database as clean.

## Runtime coherence and restart

- If source and installed digests were identical and the host started after the newest installed mtime, no code reload is required; prove fresh provider initialization instead of forcing a no-op restart.
- If plugin bytes changed, restart the importing host from an independent process. Hermes blocks gateway self-restart from inside the gateway process by design.
- An already-open conversation may keep an old provider binding even after a state reset. Verify a fresh request/session separately and report the distinction.

## Rollback

If initialization, verification, or preserved-content reads fail:

1. stop/drain the importing host from an independent control process when required;
2. restore the whole-profile archive, not just `memory.db`, when file/database coherence is uncertain;
3. otherwise restore the SQLite backup through the backup API;
4. run status first, then verify, then one live content read;
5. retain the failed reset artifacts for diagnosis until acceptance is complete.
