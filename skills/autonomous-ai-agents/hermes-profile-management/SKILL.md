---
name: hermes-profile-management
description: "Use when managing identity or state across Hermes profiles."
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, profiles, identity, soul, skills, synchronization, cron]
---

# Hermes Profile Management

## Overview

Class-level workflow for managing isolated Hermes profiles: role identity (`SOUL.md`), profile-local skills/plugins, safe synchronization, and recurring maintenance. Profiles are separate `HERMES_HOME` trees. Never assume the default profile's identity, memory, configuration, skills, credentials, or cron state is inherited by named profiles.

Load `hermes-agent` and consult current Hermes documentation before using profile or cron commands.

## Scope Contract

Name the authoritative source, every target profile, and the categories in scope: identity/SOUL, extensions, configuration, credentials, memory/sessions, and cron. Treat them independently. The default safe operation synchronizes only explicitly selected skills, additive/update-only, with backups before overwrite. Never copy credentials, memory, sessions, config, cron, or SOUL incidentally.

## Identity and SOUL Branch

Build each role identity from a shared behavior baseline plus a role-specific authority contract. Keep Workers bounded to their phase; distinguish handoff, QA recommendation, Judge acceptance, and controller finalization. Back up each target SOUL, deploy idempotently with stable markers, preserve role-specific content, read back every role class, and start fresh sessions because running sessions retain startup identity.

See `references/profile-identity-management.md` and the migrated role baseline.

## Skill Synchronization Branch

1. Resolve actual profile homes from the live profile registry.
2. Inventory complete packages, including support files and provenance.
3. Produce a dry-run manifest: added, changed, unchanged, target-only.
4. Back up changed targets unless explicit no-backup policy was selected.
5. Apply additive/update-only overlays by default; preserve target-only content.
6. Re-enumerate and verify deterministic equality for synchronized source nodes.
7. For recurring filesystem-only jobs, use a profile-local deterministic script and no-agent cron where supported; verify the cron record and owning Gateway. Gateway down ⇒ the job silently never fires: run the deployed deterministic script directly (dry-run → apply → dry-run) and verify profile-side discovery (`hermes -p <profile> skills list`) — exact recipe in `references/windows-cron-profile-sync.md`.

Exact mirrors/deletion require explicit authorization and a per-node manifest. Do not replace whole roots for tiny drift.

## Configuration and Cron Branch

Configuration synchronization is opt-in. Read the current schema rather than assuming keys. If targets must not receive messages, derive target config while forcing each platform disabled, then pause target cron jobs separately. Use profile-qualified commands and verify under the profile that owns the job.

## Verification Checklist

- [ ] Source, targets, categories, deletion, and backup policies explicit.
- [ ] Complete packages compared.
- [ ] Identity edits preserved role authority.
- [ ] No credentials, memory, sessions, or unrelated config crossed profiles.
- [ ] Post-write manifests/readbacks match policy.
- [ ] Fresh-session requirement for SOUL changes reported.
- [ ] Scheduled maintenance ran directly once and Gateway prerequisite checked.

## Support Files

- `references/profile-identity-management.md` — full SOUL/role procedure.
- `references/profile-synchronization.md` — additive and exact-mirror synchronization procedure.
