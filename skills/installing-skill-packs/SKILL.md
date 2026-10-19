---
name: installing-skill-packs
description: "Use when installing third-party skill packs into Hermes."
version: 1.0.0
author: Masia
license: MIT
metadata:
  hermes:
    tags: [hermes, skills, install, third-party]
    related_skills: [hermes-agent, authoring-hermes-skills]
---

# Installing third-party skill packs into Hermes

## When to Use

User asks to install a third-party skill pack, agent library, or skill repo into Hermes: a GitHub repo of SKILL.md folders, a hub identifier, or a whole-repo package.

## Target

Target is always the DEFAULT profile skills dir `<HERMES_HOME>\skills\` (= `$LOCALAPPDATA/hermes/skills`). Never install into `profiles/<name>/skills` directly: the default-to-profiles mirror job deletes target-only extensions there.

Try routes in order; verify after each.

## Route 1 — Hermes hub

1. `hermes skills search "<query>" --json` → identifier; `hermes skills install <id> --yes`.
2. Pitfall: skills.sh index entries go stale ("files no longer exist upstream") while the repo is fine → Route 2 via raw URL.
3. Hub installs fetch ONLY SKILL.md. If the upstream skill folder ships scripts/VERSION, copy them from a clone into the installed folder, then run `hermes skills check` (expect `up_to_date`).

## Route 2 — repo ships skill folders under `skills/`

1. Clone, inspect layout; install each skill via `hermes skills install https://raw.githubusercontent.com/<owner>/<repo>/<branch>/<dir>/SKILL.md --yes`.
2. Copy non-SKILL.md files from the clone (hash-verify).
3. Example: anti-slop (6 skills, antislop-human needs contrast-check.py).

## Route 3 — whole-repo package

Clone to `~/tools/<name>` (`~/tools` = tool packages; `~/projects` = user's own repos). Follow the repo's own Hermes docs when present:

- **agency-agents-zh**: `bash scripts/convert.sh --tool hermes` → `integrations/hermes/<category>/<slug>/SKILL.md` (two-level) → copy all into the skills dir. 277 agents × ~25 categories.
- **reverse-skill**: repo IS the router (scripts + config must stay together); keep clone and install a small adapter skill that points at the clone path.
- **ECC (affaan-m/ECC)**: clone to `~/tools/ECC`, run `npm install --ignore-scripts --no-audit --no-fund` FIRST (apply needs prod deps like sql.js; dry-run alone works without them). Preview: `node scripts/install-apply.js --target hermes --profile full --dry-run --json`. Real run writes to `$HOME/.hermes`. Payload (~492 files): `rules/` (122) `agents/` (68) `commands/` (94) `skills/` (52 skill dirs, flat) `.agents/` `.pi/` `scripts/` `mcp-configs/` `AGENTS.md` `README.md` `ecc-install-state.json`.

Pitfalls:

- Repo installer guards profile machines (`install.sh --tool hermes` errors "检测到 profile 目录…请用 --profile"). On this machine `<base>/skills` IS the default profile root: replicate the copy step manually (mkdir -p + cp SKILL.md), never pass `--profile`.
- ECC refuses symlinked/junction target roots by design ("Refusing to install ECC file through symlinked path") — do not junction `$HOME/.hermes` onto the real home; stage instead.
- Repos that assume `~/.hermes` while this machine's home is `$HERMES_HOME` (= `%LOCALAPPDATA%\hermes`): run the installer with `HOME=<staging>` (writes `<staging>/.hermes/...`), then merge the payload into the ACTIVE home and rewrite the state file's path prefix (`<staging>\.hermes` → `<HERMES_HOME>`) so metadata stays truthful. Update recipe: `git -C ~/tools/ECC pull` + `npm install --ignore-scripts` + rerun staged install + re-merge.
- Before mass-copying: check category-name and skill-slug collisions against existing skills (`comm` names, `uniq -d` for dup slugs).
- Large packs inflate the system-prompt skill index (~277 skills ≈ tens of thousands of tokens per session). Tell the user; trim per category by deleting `skills/<category>`. (Discord slash-command 8000-char limit is why the repo warns past 80 skills.)

## Verify (always)

- `find <skills>/<cat> -name SKILL.md | wc -l` equals the converted count.
- `skill_view("<one-new-skill>")` → success + readiness `available`.
- `hermes skills list` shows the new entries enabled.
- Clean probe clones from $TMPDIR afterwards; update an installed pack later with `git -C ~/tools/<name> pull` + re-run its convert/copy steps.
