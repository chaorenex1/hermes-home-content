---
name: hermes-profile-synchronization
description: "Use when comparing, synchronizing, or maintaining skills across Hermes profiles, especially when one profile is the authoritative source and targets must be updated safely."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, profiles, skills, synchronization, cron, backups]
    related_skills: [hermes-agent, hermes-agent-skill-authoring]
---

# Hermes Profile Skill Synchronization

## Overview

Hermes profiles are isolated homes: each profile can have its own skills, configuration, memory, sessions, and cron state. Use this skill to compare and synchronize skill trees without accidentally merging unrelated profile state or deleting target-only skills.

The default safe policy is **one authoritative source, additive/update-only targets**. Before overwriting an existing source-controlled entry, create a timestamped backup of that entry. This is reversible without repeatedly copying complete profile trees on every scheduled run. Synchronization must never copy secrets, personality, memory, sessions, configuration, or cron jobs unless the user explicitly requests those categories.

For the concrete Windows recipe and the failure transcript showing the cron script-path rule, see [`references/windows-cron-profile-sync.md`](references/windows-cron-profile-sync.md). For explicitly authorized exact-mirror synchronization—including changed-node copying, target-only deletion, no-backup mode, cleanup of read-only historical backups, and cron verification—see [`references/exact-mirror-no-backup.md`](references/exact-mirror-no-backup.md).

## When to Use

- The user asks to compare skills across two or more Hermes profiles.
- The user names a source/authoritative profile and one or more target profiles.
- A recurring job should keep profile skill trees aligned.
- A profile has drifted and needs a safe, reviewable repair.

Do not use this for cloning a complete profile, migrating credentials, or synchronizing sessions/memory; those are broader and higher-risk operations.

## Source and Scope Contract

1. Resolve the actual Hermes home for each profile before reading files. The default profile is the base Hermes home; named profiles live under the profile directory. Do not infer paths from the current working directory.
2. Enumerate skills by their `SKILL.md` metadata name, not only by folder name. Preserve the source folder layout for newly copied skills.
3. Compare complete skill directories, not just `SKILL.md`: include `references/`, `templates/`, `scripts/`, and other support files.
4. Treat bundled and hub-installed skills as protected content unless the operation explicitly permits updating them. Prefer copying user-local/agent-created skills; do not overwrite protected targets merely because a source copy exists.
5. Keep the synchronization scope limited to skills. Never copy `.env`, `SOUL.md`, config files, memory, sessions, or cron definitions as a side effect. Include `plugins/` (extensions) only when the user explicitly requests it; apply the same additive/update-only policy to that root.

## Safe Synchronization Procedure

### 1. Confirm the policy

Record the source profile, targets, schedule, and deletion policy. If the source is not explicit, ask rather than selecting a source based on skill count. The default deletion policy is **never delete target-only skills**.

Completion criterion: the source and every target are named, and the operation is explicitly additive/update-only.

### 2. Inspect before mutation

For every profile, collect the set of skill names, enabled/provenance information when available, and a deterministic comparison result for each complete skill directory. For a one-off integrity audit, use content hashes. For a frequent filesystem cron, compare the source tree against its target projection with path/type/size/mtime metadata; this avoids repeatedly reading large bundled assets while still detecting normal updates. Produce a dry-run report with added, changed, unchanged, and target-only skills.

Completion criterion: the report covers every source skill and identifies target-only skills that will remain untouched.

### 3. Back up each target unless explicitly disabled

The safe default is to back up every changed entry before overwrite. Exclude nested `.git` metadata: it is not skill content, can be locked on Windows, and makes short-interval backups unnecessarily expensive. If the user explicitly requests no backups, remove the backup code path completely rather than merely suppressing reports; pause the cron job first, delete historical backup roots, and verify they remain absent after direct and scheduled runs.

Completion criterion: either each overwritten entry has a separate backup, or an explicit no-backup policy is recorded and zero backup roots remain.

### 4. Apply additive/update-only changes

- Copy source-only skills into the target while preserving source layout.
- Overlay changed source skills in place, including all support files, rather than deleting their directory first. Exclude nested `.git` and do not remove target-only files inside a source skill directory.
- Leave target-only skills untouched.
- Do not delete empty directories or “clean up” target state.

Completion criterion: every source skill has matching content in the target, and the target-only set is unchanged.

### 5. Verify after mutation

Re-enumerate and hash all profiles. Verify that source and targets agree for every synchronized source skill, target-only skills still exist, and the backup is present. Run the sync once manually before relying on the scheduler.

Completion criterion: post-sync output reports zero remaining source/target drift under the selected policy.

## Explicit Configuration Synchronization

Configuration is outside the default skill-only scope and must be synchronized **only when the user explicitly requests it**. Treat the default profile's `config.yaml` as authoritative, but never copy `.env` or any credential store.

When targets must not run background work or receive messages:

1. Read the source and target YAML schemas first; do not assume a `cron.enabled` key exists. Hermes cron jobs are stored separately from `config.yaml`.
2. Generate each target config from the source configuration, then force every entry in `platforms` to `{enabled: false}`. This keeps all configured message/API channels disabled even if the source has them enabled.
3. Enumerate each named target profile's cron jobs through `hermes -p <profile> cron list --all`, then pause every active job with `hermes -p <profile> cron pause <id>`. Pause rather than delete so the change is reversible.
4. Back up a target `config.yaml` before replacing it, write atomically, and preserve all non-config profile state.
5. Verify all targets match the masked source config, every target platform has `enabled: false`, and no target active cron jobs remain.

For recurring enforcement, place a deterministic Python script in the **default profile's** `scripts/` directory and create the job under default with `--no-agent --script <filename> --deliver local`. The default Gateway must be running. A local cron delivery is intentionally not a messaging-channel notification.

## Recurring Cron Design

For a deterministic filesystem-only synchronization, prefer a cron job with `--no-agent` and a checked-in/reusable script. The script should print a concise report and remain silent only when silence is explicitly desired. Use the executing profile's script directory, and pass the script filename in the cron definition when Hermes resolves it relative to that profile's home; do not hard-code a global home path into the job prompt.

Pin the executing profile explicitly with `hermes -p <profile> ...`. A cron job created from the default profile is not automatically an `oscar` job. Verify the job using the same profile's `cron list --all` and `cron status`.

A scheduled job is not sufficient by itself: the executing profile's Gateway must be running for the scheduler to fire. Report this as an operational prerequisite rather than claiming the job is active in practice.

## Common Pitfalls

1. **Using the current working directory as Hermes home.** Resolve profile homes through Hermes/profile commands or the configured profile root; Windows installations commonly use a local application-data Hermes home.
2. **Creating the script outside the cron profile's script root.** Hermes validates `--script` paths and expects a profile-relative script filename. Put the script in the executing profile's scripts directory and pass only the accepted relative filename.
3. **Running the job without a dry run.** Always inspect the diff first when the target has more or fewer skills than the source.
4. **Replacing the whole target skills directory.** This violates the additive policy and destroys target-only skills. Copy individual source skill directories instead.
5. **Confusing scheduled with runnable.** Verify both the job record and Gateway status; a job can be listed as active while no Gateway is running.
6. **Treating a timed-out manual trigger as proof of failure.** Check for partial filesystem changes and output/backup artifacts, then run the deterministic script directly once using a different verification path.
7. **Backing up entire skill trees every tick.** On large profile sets this can exceed a five-minute interval and may traverse locked nested `.git` objects. Back up only changed entries that will be overwritten, excluding `.git`.
8. **Using content hashing for every target on a short interval.** It repeatedly reads all bundled assets and can time out. Use a source-to-target projection comparison with path/type/size/mtime metadata for routine syncs; reserve full hashing for explicit integrity audits.
9. **Deleting a source directory before copying.** Locked files and target-only content make destructive replacement unsafe. Overlay source files, exclude `.git`, and retain target-only files. If an interrupted destructive attempt occurred, restore missing non-Git files from its pre-write backup before resuming the overlay sync.
10. **Copying profile state beyond authorized scope.** Keep `.env`, configuration, memory, sessions, SOUL, and cron isolated. Plugins/extensions may be included only when the user explicitly requests them.
11. **Implementing explicit exact-mirror policy by replacing an entire root on any drift.** Large skill trees and volatile files such as `.usage.json` can turn a tiny metadata change into one full-tree copy per target, exceeding cron limits and multiplying storage. Use a per-node incremental mirror: scan once, copy only changed source nodes, remove target-only nodes, and verify the final manifest. Back up only changed/deleted nodes under the default safe policy; create no backups when the user explicitly selects no-backup mode.

## Verification Checklist

- [ ] Source and targets are explicit.
- [ ] Dry-run diff was generated.
- [ ] Backup policy is explicit: backups verified when enabled, or zero backup roots verified when disabled.
- [ ] All source skills match target content after synchronization.
- [ ] Target-only handling matches policy: preserved for additive sync, absent for exact mirror.
- [ ] No non-skill profile state was copied or modified.
- [ ] The sync script passed syntax validation and one direct execution.
- [ ] Cron record is present under the intended executing profile.
- [ ] Gateway status was checked and any inactive prerequisite was reported.
