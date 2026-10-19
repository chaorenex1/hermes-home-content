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

## Safety invariant

The synchronization script must compare full skill-directory content and copy only source-only or changed source skills. It must never replace the entire target skills tree and must never delete target-only skills.
