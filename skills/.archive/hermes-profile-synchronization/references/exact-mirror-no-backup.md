# Exact-Mirror Profile Extensions: Incremental, Optional No-Backup Mode

Use this recipe only when the user explicitly makes the default profile authoritative for complete `skills/` and `plugins/` trees, including deletion of target-only nodes.

## Why whole-root replacement is the wrong implementation

A metadata-only change such as `.usage.json` can mark a large skills tree as drifted. Replacing the complete root for every target multiplies I/O by `source tree size × target count` and can exceed cron runtime limits. Moving complete roots into timestamped backups also causes rapid storage growth.

Implement exact mirroring per node instead:

1. Pause the recurring job before changing its script or deleting old backups.
2. Build one source manifest containing relative path, node type, file size, and mtime; directory mtimes should not determine drift.
3. Build a target manifest for each profile.
4. Copy only missing or changed source nodes through same-volume temporary files plus `os.replace`.
5. Delete target-only nodes and type-mismatched nodes, deepest/topmost as appropriate.
6. Verify the complete target manifest equals the source manifest.
7. Run a synthetic regression probe proving that one changed source file copies one file—not the whole tree—and that one target-only file is removed.
8. Run the real script directly, then a second dry run expecting zero drift.
9. Resume the cron job and manually trigger it once; require `last_status=ok`.

## No-backup mode

When the user explicitly requests no backups:

- Remove all backup creation, timestamp, return-value, and report logic from the script—not merely disable one call.
- Delete existing `.profile-sync-backups` trees while the job is paused.
- On Windows, old nested Git objects may be read-only. Use `shutil.rmtree(..., onerror=handler)` where the handler adds writable/readable permissions with `os.chmod` and retries the failed removal.
- Exclude nested `.git` directories from extension manifests and remove them from target projections: repository metadata is not deployable skill/plugin content, and locked/read-only Git objects can break mirroring.
- Before `os.replace(temp, target)`, clear the target's read-only bit. Also make the `shutil.copy2` temporary writable so a failed replace can clean it up; otherwise Windows raises `WinError 5` and leaves `.sync-*` files.
- Verify `backup_roots_remaining=0` after deletion, after a direct synchronization, and after the cron smoke test.
- State plainly that rollback is no longer provided by the synchronization task.

## Session scale evidence

In the observed case, default `skills/` contained 15,608 files and about 888 MB across 17 targets. Whole-root replacement turned one metadata drift into about 14 GiB of writes. Historical full-tree snapshots accumulated about 30 GiB. Incremental mirroring reduced steady-state work to manifest traversal and changed-node copies.
