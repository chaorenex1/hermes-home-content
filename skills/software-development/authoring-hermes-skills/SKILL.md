---
name: authoring-hermes-skills
description: "Author Hermes skills: user-local or in-repo SKILL.md."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, skills, skill-manage, authoring, memory]
    related_skills: [hermes-profile-management, hermes-runtime-diagnostics]
---

# Authoring Hermes Skills

Two trees, one discipline. Decide which tree first — the tooling, validator, and review bar differ.

| Tree | Path | How to write |
|---|---|---|
| **User-local** | `$HERMES_HOME/skills/<category>/<name>/SKILL.md` | `skill_manage(action='create' \| 'patch' \| 'write_file')` |
| **In-repo** | `skills/<category>/` or `optional-skills/<category>/` inside the hermes-agent repo | `write_file` + `git add`; `skill_manage create` does **not** target this tree |

For in-repo skills (tier choice, frontmatter bar, platform gating, tests, docs regeneration, PR workflow) read `references/in-repo-skill-authoring.md` before writing.

## Shared rules

- **Description is the trigger.** One sentence, ≤60 chars, trigger first, ends with a period. `skill_manage(action='create')` rejects longer ones and the system-prompt index truncates at 57 chars + "…" — everything needed to *match* the skill must fit in that window. All other detail belongs in the body. Quote the value if it contains `:` or YAML parses it as a mapping. Direct `write_file` edits bypass that validation, so re-check the 57-char trigger window by hand after writing a SKILL.md outside `skill_manage`.
- **Optimize for process predictability.** If a line does not change model behavior, cut it. "Be careful" and "use best practices" are no-ops; replace with a checkable criterion.
- **Each step ends with a completion criterion**, checkable and exhaustive when it matters ("every modified file accounted for" beats "summarize changes").
- **Co-locate a rule with the concept it governs**, and when adding a rule remove the wording it replaces — skills accumulate sediment otherwise.
- **Support files carry depth:** `references/<topic>.md` (topical depth, named by topic — never by date or incident), `templates/` (starter files to copy), `scripts/` (re-runnable actions). Add with `write_file` and one pointer line in SKILL.md. Extend an existing reference instead of adding a sibling.
- **Don't restate environment or tool-schema basics.** A skill carries the workflow, order of operations, and pitfalls.

## Procedure — user-local

1. Decide NEW vs extend: `skill_view` the candidates first. That read also satisfies the read-before-write guard for a later patch.
2. Draft the SKILL.md: YAML frontmatter (`name`, `description`, `version`, `author`, `license`, `platforms`, `metadata.hermes.tags`/`related_skills`) plus a procedural body with concrete commands and pitfalls.
3. Apply with a **single** `skill_manage` call; batch related edits (new skills plus the `related_skills` cross-links they need on existing skills) together.
4. Verify: `skill_view(name)` for every new/edited skill and spot-read the on-disk frontmatter. New user-local skills load immediately; no restart. (An in-repo skill is invisible to the current session — the loader initializes at session start.)
5. Distribution: default-profile skills mirror to named profiles via `$HERMES_HOME/scripts/sync_default_profile_extensions.py` (dry-run → apply → dry-run). Never hand-copy into profile trees — the sync also **deletes** target-only skills there.

## Pitfalls

- **Atomic batches:** all operations in one `skill_manage` call apply together; one failure (e.g. an over-long description on a `create`) rolls back every earlier op. After a rollback, re-issue the **complete** corrected batch — re-running only the failed op leaves the rest unapplied.
- **Read-before-write guard:** patching an existing skill, or overwriting an existing support file, requires a fresh `skill_view` of that exact target in the current session; content quoted earlier in the conversation does not count.
- **Unique `old_string`:** a patch whose snippet matches several places fails and takes the whole batch down — include enough skill-specific context.
- **Protected skills:** bundled and hub-installed skills refuse edits ("Refusing … for bundled skill"). Note the gap and recommend `hermes curator adopt <name>` — do not retry.
- **Router skills:** a skill whose core is a routing table pointing at siblings adds an indirection hop and duplicates their triggers. If it would be empty without "load skill X instead", don't write it.
- **Dangling `related_skills`:** every entry must resolve in the same tree state; archived or user-only names break resolution.
- **Machine-local paths** baked into a skill break for everyone else: write `~/.camofox/downloads`, `$HOME/...`, `%USERPROFILE%`, `$TEMP` — never `C:\Users\<name>\...` or `/home/<you>/...`. In shell snippets quote the expansion, not the tilde: `"~/.x"` passes a literal `~` and the command fails, so write `"$HOME/.x"`.
- **Referencing raw shell instead of Hermes tools:** name `terminal`, `read_file`, `write_file`, `patch`, `search_files`, `web_search`, `web_extract`, `browser_navigate`, `vision_analyze`, `delegate_task`, `cronjob` — not `grep`/`cat`/`sed`/`find`.
- **Wholesale rewrite of a long SKILL.md:** `write_file` refuses to overwrite a file it did not read in one unpaginated pass, and reading page-by-page does not clear that guard. For a true rewrite, move the old file aside with a git/tree rollback point and write the new one; for everything smaller, `patch` the offending sentences. Append no "UPDATE:" block — a stale rule left standing still gets followed.
- **Migrating a skill to a new tool surface:** transplant the domain knowledge, but exercise each ported procedure against the live target before it lands in the doc, and label what was not exercised as unverified. Delete the superseded implementation and put a one-line deprecation header on every reference file that still prescribes it — two contradictory procedures in one skill are worse than either alone, because the next session follows the stale one.

## Verification Checklist

- [ ] Tree chosen deliberately (user-local vs in-repo), and in-repo work follows `references/in-repo-skill-authoring.md`.
- [ ] Frontmatter starts at byte 0, `name` + `description` present, body non-empty.
- [ ] Description ≤60 chars, trigger self-contained in the first 57, ends with a period, no marketing words.
- [ ] Every `related_skills` entry resolves.
- [ ] Each ordered step has a checkable completion criterion; `## Pitfalls` and verification are present.
- [ ] `skill_view` loads every touched skill; on-disk frontmatter spot-read.
- [ ] No manual copies into profile trees (the sync script owns distribution).
