# Windows Recipe: Profile Skill Sync with Cron

## Observed layout

On this Windows setup, the active default Hermes home was under:

```text
<HERMES_HOME>
```

Named profiles were under:

```text
<HERMES_HOME>\profiles\oscar
<HERMES_HOME>\profiles\orchestrator
```

Do not assume `C:\Users\<user>\.hermes` is the active home; use `hermes profile show <name>` and the reported `Path` as the evidence.

## Reliable command pattern

Create and inspect the job through the executing profile:

```bash
hermes -p oscar cron create '0 4 * * *' \
  --name 'default技能同步到oscar和orchestrator' \
  --deliver local \
  --script 'sync_profile_skills.py' \
  --no-agent

hermes -p oscar cron list --all
hermes -p oscar cron status
```

The script must be placed where the profile's cron resolver accepts it. Hermes rejects an absolute script path with an error equivalent to:

```text
Script path must be relative to ~/.hermes/scripts/ ... Place scripts in ~/.hermes/scripts/ and use just the filename.
```

In practice, confirm the profile-specific script root and use the filename accepted by the installed Hermes version rather than assuming the global default profile's root.

## Verification pattern

1. Run the script directly once.
2. Confirm the report includes added/updated/unchanged counts.
3. Confirm a timestamped backup path is printed when changes occur.
4. Confirm target-only skills are reported as preserved.
5. Confirm `cron status` separately; a listed active job does not mean it will fire if the executing profile Gateway is stopped.

A manual `cron run` may time out while the deterministic script itself succeeds. Do not retry the identical trigger repeatedly; inspect filesystem/output artifacts and execute the script directly for a bounded verification.

## Manual deploy pass (current machine — exact mirror)

The 5-minute cron job "default profile skills and plugins sync" runs
`sync_default_profile_extensions.py` from `$HERMES_HOME/scripts/`; it fires only while the Gateway
is running, so with the Gateway down a manual pass IS the deploy path:

1. `python sync_default_profile_extensions.py --dry-run` → per-profile `would-replaced` lines + counts.
2. Node-level pre-check (cheap, do it before any mutation): load the script with
   `importlib.util.spec_from_file_location` and reuse its own `tree_manifest` / `target_profiles` /
   `topmost_paths` to print the per-profile copy and DELETE node lists — target-only deletions are
   permanent under no-backup mode, so eyeball them first.
3. If a to-be-deleted target-only node looks recent or valuable, copy it to a retention dir before
   the run and disclose the deletion in the report (adopt it into the default tree if it should live on).
4. Run the script for real; a clean run prints `replaced=<n> … failures=0` (each root is re-manifested
   after mirroring and raises on residual mismatch).
5. Second `--dry-run` must report `unchanged` for every profile — that IS the zero-drift proof.
6. Profile-side discovery check: `hermes -p <profile> skills list` shows the new/changed skills as
   `enabled`; `ls -d "$HERMES_HOME"/profiles/*/.profile-sync-backups` must stay empty (no-backup mode).

## Safety invariant

Under the default additive policy the synchronization script compares full skill-directory content and copies only source-only or changed source skills; it never replaces the entire target skills tree and never deletes target-only skills. The user has separately authorized an exact-mirror mode for this machine (also deletes target-only nodes, no backups) implemented by `sync_default_profile_extensions.py` — see `references/exact-mirror-no-backup.md`; run the mode that matches the user's standing authorization and the deployed script.
