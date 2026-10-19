# Skill Validator Rules and Local Pre-Flight

Absorbed from the former bundled `hermes-agent-skill-authoring` skill. Companion to `in-repo-skill-authoring.md`; this file is the mechanical side (what the validator actually enforces), the other is the review/PR side.

## Validator source of truth

`tools/skill_manager_tool.py::_validate_frontmatter`. Hard requirements:

- First bytes are `---` — no leading blank line, no BOM.
- Closes with `\n---\n` before the body.
- Parses as a YAML mapping.
- `name` present; lowercase, hyphens, ≤64 chars (`MAX_NAME_LENGTH`).
- `description` present; validator ceiling 1024 chars (the repo hardline is ≤60 — see below).
- Non-empty body after the closing `---`.
- Full SKILL.md ≤100,000 chars (`MAX_SKILL_CONTENT_CHARS`).

## What the validator does NOT check

`platforms:`, `author` format, description length within its 1024 ceiling, tests, docs regeneration, `related_skills` resolution, or machine-local paths. Reviewers check all of those — meeting the validator is not meeting the standard.

## Local pre-flight

```python
import yaml, re, pathlib
content = pathlib.Path("skills/<category>/<name>/SKILL.md").read_text()
assert content.startswith("---")                      # byte 0, no BOM/blank line
m = re.search(r'\n---\s*\n', content[3:])
fm = yaml.safe_load(content[3:m.start()+3])
assert "name" in fm and "description" in fm
assert len(fm["description"]) <= 60, f"description {len(fm['description'])} chars — hardline is 60"
assert fm["description"].endswith(".")
assert "platforms" in fm
assert len(content) <= 100_000
```

Also verify every `related_skills` entry exists in the same tree state as the change — a planned, user-local, or archived skill name is a dangling reference.

## Editing an existing in-repo skill

- Small fix: `skill_manage(action='patch', ...)` or the `patch` tool.
- Major rewrite: `write_file` the whole SKILL.md.
- Support files: `write_file` under `references/`, `templates/`, `scripts/`.
- Re-run the docs generator whenever frontmatter changed; keep every relative link resolvable from the skill root, and update the instructions that point at a file you move or inline — in the same commit.

## Batch atomicity

Every op in one `skill_manage` call applies together: a single failure (an over-long description on a `create`, a non-unique `old_string` on a `patch`) rolls back the whole batch. After a rollback, re-issue the complete corrected batch — re-running only the failed op leaves the rest unapplied.
