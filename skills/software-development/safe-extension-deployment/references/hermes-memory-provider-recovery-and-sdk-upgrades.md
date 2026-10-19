# Hermes memory-provider recovery and SDK upgrade

Use this reference when a Hermes memory provider fails to initialize, a profile database must be recovered, or “install the latest version” could mean either provider code or its upstream SDK.

## Separate the three layers

Treat these as independent artifacts:

1. **Provider code** — the standalone plugin under `plugins/<provider>` and its source checkout.
2. **Provider SDK/runtime dependency** — a package installed in the Hermes Python environment.
3. **Profile state** — the profile-local authoritative files, manifest, and control/projection database.

Do not replace one layer to repair another. Before an upgrade, compare source and installed plugin hashes, inspect the provider manifest/version, query the SDK distribution version, and verify the profile store separately.

## Recover a file-authoritative provider safely

A manifest that names a canonical database while that database is absent is a fail-closed integrity condition. Prefer a verified whole-profile archive over copying an arbitrary standalone database: the archive preserves authoritative Markdown alongside manifest and control state.

1. Locate the newest whole-profile archive and inspect it before restoration:
   - archive entries are confined to the provider state root;
   - manifest names the expected canonical store and current schema;
   - the embedded SQLite database passes `PRAGMA quick_check`;
   - schema migrations form the expected contiguous range;
   - authoritative Markdown is present when the provider is file-authoritative.
2. Back up the broken current state even if the database is missing. This preserves forensic evidence and rollback material.
3. Use the provider’s own confirmed restore command rather than manual extraction. A safe restore stages the archive, copies the prior state to a rollback sibling, then swaps the staged state into place.
4. Run provider `status` first because it may perform initialization or reconciliation. Run `verify` only after status completes.
5. Independently verify SQLite integrity and then call one live provider read tool. A CLI success alone does not prove the active tool path can initialize.
6. Preserve the exact pre-restore backup and source archive paths in the completion report.

### Example acceptance sequence

```text
hermes <provider> status
hermes <provider> verify
SQLite: quick_check=ok, integrity_check=ok
Live provider read: succeeds against one authoritative file
```

## Clear stale lifecycle markers without losing evidence

If a completed or timed-out operation leaves retry markers that generate repeated notifications:

1. Read only non-secret metadata first: marker ages, target platform, exit code, and whether a destination identifier is present. Do not print identifiers or captured output.
2. Move the exact marker set into a timestamped backup directory instead of deleting it.
3. Include both pending and claimed names because a watcher may rename between them. Use a bounded retry loop around atomic moves, then wait briefly and confirm no marker reappears.
4. Verify the relevant log signature has a zero count delta over a bounded observation window. Historical lines may remain; success means no new lines are appended.

## Upgrade the correct “latest version”

When a local provider and an upstream SDK share a name, determine which layer is actually outdated:

- If source and installed provider digests are identical and the provider has no release remote, redeploying it is a no-op.
- Query the official package index for the SDK’s latest stable version and compare it with the distribution inside the Hermes virtual environment.
- Back up profile state before changing the environment.
- If index resolution is unavailable but an official wheel URL is retrievable, download the exact platform wheel, verify its published SHA-256, inspect its metadata and dependencies, then install the local wheel into the Hermes virtual environment. Capture the working fallback pattern, not the transient transport error.
- Verify both distribution metadata and runtime import version.
- Exercise a real temporary database: connect, create a table, insert records, run a vector query, and assert the nearest result.
- Re-run provider `status`, then `verify`, and one live provider read. An SDK smoke test does not prove profile compatibility.

Restart the owning host only when the upgraded code can be resident in that process. If the provider does not import the SDK and live provider verification passes, do not restart merely for ceremony.

## Reporting

Report the upgraded layer and version explicitly. Also state whether provider code changed, the profile backup path, database verification results, live-tool evidence, and whether a restart was required.