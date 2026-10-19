# Authoring In-Repo Skills (hermes-agent)

For SKILL.md files committed inside the hermes-agent repo (`skills/<category>/` or `optional-skills/<category>/`). The repo section AGENTS.md → "Skill authoring standards (HARDLINE)" is the source of truth; this reference is the operational walkthrough. Reviewers reject PRs that violate the hardline standards, so meeting them up front is cheaper than a salvage pass.

Use this path when the user says "add a skill in this branch/repo/commit", or when the workflow should ship with hermes-agent. Editing an existing in-repo skill: `patch` for small edits, `write_file` for rewrites (`skill_manage action=patch` still works on in-repo skills, but `create` does not — it writes to the user tree).

## Decide the tier first: bundled vs optional

- **Bundled (`skills/<category>/`)** — daily-driver behavior, broadly useful, low footprint. The bar: you can say "a user will load this in 5+ sessions per month" with a straight face.
- **Optional (`optional-skills/<category>/`)** — niche, vertical-specific (blockchain, gaming, finance, one app), recurring jobs, or anything heavy. Installed via `hermes skills install official/<category>/<skill>`.

**When in doubt, optional.** Promoting later is easy; demoting is churn. "Useful to anyone who ever needs this" is an optional-tier argument.

Pick the category by what the tool IS, not what it feels like (an AI-agent CLI goes in `autonomous-ai-agents/` even if it "feels productivity"). Confirm existing categories with `search_files(pattern='*', target='files', path='skills')`; don't invent top-level categories casually.

No **router / index / hub** skills: a routing table pointing at siblings adds an indirection hop and duplicates the siblings' own triggers.

## Required frontmatter

Validator source of truth: `tools/skill_manager_tool.py::_validate_frontmatter`. Hard requirements: first bytes are `---` (no leading blank line or BOM); closes with `\n---\n` before the body; parses as a YAML mapping; `name` and `description` present; non-empty body.

Repo-standard shape (all fields expected even where the validator doesn't enforce them):

```yaml
---
name: my-skill-name               # lowercase, hyphens, ≤64 chars
version: 0.1.0                    # semver; new skills start at 0.1.0
author: Real Name (github-handle), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Short, Descriptive, Tags]
    related_skills: [other-in-repo-skill]
---
```

### `description` (HARDLINE — the validator's 1024 is not the standard)

≤60 chars, one sentence, ends with a period; state the capability, not the implementation; don't repeat the skill name; no marketing words. The index truncates at 57 chars + "...", so the trigger must be self-contained there. Quote the value if it contains a colon.

### `author`

Credit the **human first**, then "Hermes Agent": `Ben Barclay (benbarclay), Hermes Agent`. Never `author: Hermes Agent` alone for contributed skills, even when an agent drafted the text. Maintainer-authored: `Teknium (teknium1), Hermes Agent`.

### `related_skills`

Every entry must resolve to an existing **in-repo** skill in the same tree state as the PR — not planned, not in another PR, not user-local. Verify with `search_files(pattern='<name>', target='files', path='skills')` (and `optional-skills/`).

## Platform gating: audit, don't trust

| Skill uses only… | `platforms:` |
|---|---|
| Hermes tools + stdlib Python + cross-platform CLIs | `[linux, macos, windows]` |
| bash pipelines, `grep`/`awk`/`sed` chains, heredocs | `[linux, macos]` |
| `osascript`, `defaults`, `pmset` | `[macos]` |
| `apt`/`systemctl`/`/proc` | `[linux]` |

POSIX-only signals to search for in `scripts/`: `fcntl`, `termios`, `pty`, `os.fork`, `os.killpg`, `signal.SIGKILL`, `os.kill(pid, 0)` liveness checks, hardcoded `/tmp` `/proc` `/etc`. Default posture: fix cross-platform first (`tempfile.gettempdir()`, `pathlib.Path`, `psutil.pid_exists`); gate narrower only when the dependency is genuinely platform-bound, and say why under Pitfalls.

## Size limits and body structure

Full SKILL.md is capped at 100,000 chars, but target ~100 lines for a simple skill and ~200 for a complex one (peers sit at 8–14k chars). Bulky or branch-specific material goes in `references/`, `templates/`, or `scripts/`, pointed to from SKILL.md. Ship a helper script rather than expecting the model to inline-write a parser every call.

Modern section order:

```
# <Skill> Skill
2-3 sentence intro: what it does, what it doesn't do, dependency stance.

## When to Use          — bulleted triggers (+ "Don't use for:" counter-triggers)
## Prerequisites        — exact env vars, installs, API key sourcing
## How to Run           — canonical invocation through the `terminal` tool
## Quick Reference      — flat command list, no narration
## Procedure            — numbered steps, each with a checkable completion criterion
## Pitfalls             — known limits, things that look broken but aren't
## Verification         — how to prove the skill worked
```

When to Use + actionable body + Pitfalls + Verification are the minimum. Cut marketing intros, "Setup Check" no-ops, and re-explanations of variables already in Prerequisites. Name Hermes tools in backticks rather than raw shell wrappers; frame CLI invocations as `terminal(command="<tool> ...", timeout=...)` — bare shell prose is a review-blocking non-conformance. Never bake machine-local paths into a committed skill.

## Tests and docs (required for repo skills)

1. **Tests** at `tests/skills/test_<skill>_skill.py` — stdlib + pytest + `unittest.mock` only, no live network. Run via `scripts/run_tests.sh tests/skills/test_<skill>_skill.py -q`. The generic `tests/tools/test_skill_manager_tool.py` passing proves nothing about your skill.
2. **Docs regen:** `python website/scripts/generate-skill-docs.py`, then apply scope discipline — the generator rewrites every auto-gen page. `git checkout --` everything that isn't yours; the final diff shows only your SKILL.md, your one per-skill docs page, a one-line catalog row, and one `website/sidebars.ts` insertion (verify exactly one hit for your slug, or the page is an orphan).
3. **`.env.example`** only if the skill needs new env vars: one clearly delimited commented block; touch nothing else.

## Workflow

1. Survey peers in the target category (`search_files(target='files')`), read 2–3 peer SKILL.md files, and prefer extending an existing skill over creating a narrow sibling.
2. Decide tier and category; when in doubt, optional — and ask before pushing.
3. Draft with `write_file` to the repo path. Note: `skill_manage(action='create')` writes to `~/.hermes/skills/`, not the repo tree.
4. Validate locally: frontmatter at byte 0, required fields, `len(description) <= 60` and ends with a period, `platforms` present, `len(content) <= 100_000`, and every `related_skills` entry present in-repo.
5. Add tests and regenerate docs (above).
6. `git add` + commit on the active branch; open a PR.
7. Expect the current session not to see the new skill until a new session starts — the loader is cached at session start. This is not a bug.

## Common pitfalls

1. Using `skill_manage(action='create')` for an in-repo skill (wrong tree).
2. Trusting the validator's limits as the standard — it allows 1024-char descriptions and doesn't check `platforms:`, author format, tests, or docs; review does.
3. `author: Hermes Agent` alone on a contributed skill.
4. Leading whitespace or a BOM before `---`.
5. A description too generic, or with the trigger buried past char 57.
6. `related_skills` pointing at non-existent or out-of-tree skills.
7. Duplicating a peer instead of extending it.
8. Skipping the docs generator (orphan page) or pushing its unrelated drift (ballooned diff) — both are wrong.
9. Letting skills accumulate sediment: when adding a rule, remove the wording it replaces.
