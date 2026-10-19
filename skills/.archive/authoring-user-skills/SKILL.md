---
name: authoring-user-skills
description: "Create and edit user-local Hermes skills with skill_manage."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, skills, skill-manage, authoring, memory]
    related_skills: [hermes-agent-skill-authoring, hermes-profile-management]
---

# Authoring user-local Hermes skills (skill_manage)

Use when the user asks to add, edit, or remove Hermes skills that live in the user tree:
`%LOCALAPPDATA%\hermes\skills\<category>\<name>\SKILL.md` (default profile). For skills committed
INSIDE the hermes-agent repo, use the bundled `hermes-agent-skill-authoring` skill instead —
different tree, validator, tests, and docs.

## Procedure

1. Decide scope: NEW skill vs extending an existing one; `skill_view` the candidates before
   choosing (this also satisfies the read-before-write guard for any later patch).
2. Draft the SKILL.md: YAML frontmatter (`name`, `description`, `version`, `author: Hermes Agent`,
   `license`, `platforms`, `metadata.hermes.tags`/`related_skills`) + a procedural body with
   concrete commands and pitfalls.
3. **Description budget (hard-enforced):** one sentence, trigger first, ends with a period, ≤60
   chars. `skill_manage(action='create')` REJECTS longer descriptions and the system-prompt index
   truncates at 57 chars + "…" — the trigger must be self-contained in that window; all other
   detail goes in the body.
4. Apply with a single `skill_manage` call; batch related edits together (e.g. new skills + the
   `related_skills` cross-links they need on existing skills).
5. Verify: `skill_view(name)` for every new/edited skill and spot-read the on-disk frontmatter.
   New skills are visible immediately (fresh load); no restart needed.
6. Distribution: default-profile skills mirror to named profiles via
   `$HERMES_HOME/scripts/sync_default_profile_extensions.py` (dry-run → apply → dry-run) — never
   hand-copy into profile trees; the sync also DELETES target-only skills there.

## Pitfalls

- **Atomic batches:** all operations in one `skill_manage` call apply together; one failure (e.g. an
  over-long description on a `create`) rolls back EVERYTHING applied earlier in that call. After a
  rollback, re-issue the COMPLETE corrected batch — re-running only the failed op leaves the rest
  unapplied.
- **Read-before-write guard:** patching an existing skill, or overwriting an existing support file,
  requires a fresh `skill_view` of that exact target in the CURRENT session; content quoted earlier
  in the conversation does not count.
- **Unique `old_string`:** patch ops fail and take the whole batch down with them when the snippet
  matches several files' similar text — include enough skill-specific context.
- **Protected skills:** bundled and hub-installed skills refuse edits ("Refusing … for bundled
  skill"). Note the gap in the reply and recommend `hermes curator adopt <name>` instead of
  retrying.
- **Support files:** `references/<topic>.md` (topical depth), `templates/`, `scripts/` — added via
  `write_file` with a skill-relative `file_path`, then a one-line pointer in SKILL.md. Extend an
  existing reference over creating a per-session file, and never name files after dates/incidents.
- Do not restate environment or tool-schema basics in skill bodies; skills carry the workflow, the
  order of operations, and the pitfalls.

## Verification Checklist

- [ ] Every new/edited description ≤60 chars, ends with a period, trigger self-contained in the first 57.
- [ ] `skill_view` loads every touched skill; on-disk frontmatter spot-read.
- [ ] `related_skills` entries resolve to skills that exist in the same tree.
- [ ] No manual copies into profile trees (the sync script owns distribution).
