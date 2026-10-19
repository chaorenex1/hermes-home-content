---
name: large-changeset-review
description: "Review large mixed-scope diffs before commit."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [code-review, security, verification, pre-commit, large-diff, artifacts]
    related_skills: [requesting-code-review, analyzing-codebases]
---

# Large Changeset Review

Pre-commit review for working trees that contain weeks of accumulated work:
feature branches, merge artifacts, generated files, platform-specific lock
churn, and mixed executable + test + documentation changes.

The standard `requesting-code-review` pipeline assumes a small, coherent diff.
When `git status --porcelain` shows 50+ entries, that pipeline under-reports
untracked artifacts, lock-file drift, and security-boundary shifts hidden in
large executable diffs.

## When to Use

- `git status --porcelain` shows 50+ modified/untracked entries
- The diff exceeds ~4,000 lines or touches multiple architectural layers
- The working tree has been accumulating changes for days/weeks
- The user asks for a "review before commit" on a large mixed-scope changeset

## The Core Problem

Large diffs fail review in three ways that small diffs do not:

1. **Untracked artifacts** that should never be committed (`.orig` backups,
   runtime caches, literal `~/` directories created by tools that didn't
   expand `~`).
2. **Lock-file platform drift** — `package-lock.json` regenerated on Windows
   drops optional platform-specific native deps (`@esbuild/win32-*`, etc.)
   and breaks installs on other platforms.
3. **Security boundary shifts** hidden in large executable diffs — e.g. an
   approval-bypass refactor that looks like a cleanup but changes which code
   paths honor `approvals.mode: off`.

## Grouped Inspection Protocol

Do NOT read every file. Group by risk class and inspect per class:

| Risk class | What to inspect | Example from real session |
|---|---|---|
| **Merge / backup artifacts** | `*.orig`, `*.rej`, `*.bak`, `*.tmp`, `Python/`, literal `~/` dirs | `hermes_cli/web_server.py.orig` (545KB), `Python/` (34MB install cache), `~/` (literal tilde dir with mem0 UUID) |
| **Lock / manifest files** | `package-lock.json`, `poetry.lock`, `Cargo.lock` — check for platform-dep removal | `package-lock.json` dropping `@esbuild/*` optional deps |
| **Security-sensitive runtime** | `tools/approval.py`, `tools/registry.py`, `agent/plugin_agent.py`, `agent/tool_executor.py` | Approval-gate refactor changing `approvals.mode: off` handling |
| **New executable modules** | Untracked `.py` / `.ts` >200 lines | `hermes_cli/ultrawork_kanban.py` (5356 lines) |
| **Test deletions** | Files with net-negative line changes in `tests/` | Removed provider-review tests — verify they test removed code, not weakened coverage |
| **Docs / config** | `*.md`, `sidebars.ts`, `*.yaml` | Additive, usually safe |

## Verification Shortcuts

```bash
# 1. Syntax-check all modified Python files in one pass
git diff --name-only -- '*.py' | xargs python -m py_compile

# 2. Secret scan on added lines only
git diff | grep '^+' | grep -iE '(api[_-]?key|secret|password|token)\s*=\s*["\'][^"\']{8,}["\']'

# 3. Find risky patterns in the diff
git diff | grep '^+' | grep -E 'shell\s*=\s*True|os\.system|eval\(|exec\(|pickle\.loads'

# 4. Find test deletions (potential coverage loss)
git diff --stat -- 'tests/*' | grep -E '\|\s+[0-9]+\s+-+'
git diff -- 'tests/*' | grep '^-.*def test_'
```

### Final Index Verification

Unstaged checks are not sufficient when new files exist: `git diff` and
`git diff --check` ignore untracked files. After grouped review and artifact
cleanup, stage the intended tree and verify the exact commit candidate:

```bash
git add -A
git diff --cached --check
git diff --cached --name-status
git diff --cached --stat
```

If the cached whitespace check reports nearly every nonblank line in a newly
added file, inspect its byte-level line endings. Mixed CRLF/LF files can appear
as thousands of trailing-whitespace errors only after staging. Normalize only
the affected text files to the repository convention, re-stage them, and rerun
the cached check. Do not run blanket line-ending conversion across the tree.

Run one final `git status --porcelain` after tests, builds, package installs,
and reviewer tools. Verification itself can create caches, installer logs, or
literal path directories after the initial artifact sweep.

## Pitfalls

- **Do not skip untracked files.** `git diff` ignores them. Run
  `git status --porcelain | grep '^??'` and inspect anything that is not
  clearly source code.
- **Do not call an unstaged whitespace check final.** `git diff --check` also
  ignores untracked files. The commit candidate is clean only after
  `git diff --cached --check` passes.
- **Re-scan after verification.** Tests, package installs, and reviewer probes
  can create new repo-root caches/logs after the first inventory.
- **Preserve ambiguous backups before removal.** Move a pre-existing `.orig`
  or similar backup outside the repository when its contents may be unique;
  clean the commit without destroying the user's recovery copy.
- **Use the project's canonical test runner.** If a broad run has known
  baseline/platform failures, isolate changed-file tests, rerun concrete
  failing affected tests after each fix, and record unrelated baseline
  failures separately. An ad hoc runner is not stronger evidence.
- **Review the final state after fixes.** Give the independent reviewer the
  final staged diff plus canonical test evidence. Constrain a focused retry to
  code review when tests are already authoritative; do not let a noncanonical
  rerun replace valid evidence.
- **`.orig` files are never intentional commits.** They are editor merge
  backups. Treat as blocking.
- **Literal `~/` or `Python/` directories in repo root** indicate a tool failed
  to expand a path. Treat as blocking and check whether the tool's config
  leaked a user UUID or absolute home path.
- **package-lock.json shrinking on Windows** is almost always npm dropping
  optional platform deps. Compare against `git show HEAD:package-lock.json |
  grep -c '@esbuild'` to confirm.
- **Test deletions are acceptable only when they test removed functionality.**
  Cross-check the removed test names against the feature diff.
- **Approval / auth / gate refactors** deserve line-by-line reading of the
  boolean expressions. A change from `A or B or C` to `helper()` is only safe
  when `helper()` is proven to cover `C`.

## Final Commit Gate

Commit only when all four conditions hold:

1. The exact staged tree has passed artifact, secret, and whitespace checks.
2. Changed behavior has canonical test evidence; unrelated baseline failures
   are explicitly separated from regressions.
3. An independent reviewer has reviewed the final staged state, not an older
   pre-fix diff.
4. After commit, `git show -1 --shortstat`, `git diff HEAD^ HEAD --check`, and
   `git status --short --branch` verify the recorded artifact and clean
   worktree. Do not push unless the user asked for a remote write.

## Verdict Template

For large changesets, return a structured verdict:

```json
{
  "passed": false,
  "blocking_findings": [
    {"path": "hermes_cli/web_server.py.orig", "line": 1, "rationale": "545KB merge backup; should not be committed"},
    {"path": "package-lock.json", "line": null, "rationale": "416 lines removed; drops platform-specific esbuild deps, breaks non-Windows installs"}
  ],
  "nonblocking_findings": [
    {"path": "agent/plugin_agent.py", "line": 36, "rationale": "Empty toolsets=[] now allowed; verify AIAgent handles None as 'all default toolsets'"}
  ],
  "recommended_targeted_tests": [
    "python -m pytest tests/agent/test_plugin_agent.py -v",
    "python -m pytest tests/hermes_cli/test_kanban_db.py -v"
  ]
}
```

## Reference

- `references/session-example.md` — worked example from a real 65-file
  Hermes Agent pre-commit review, including exact commands and findings.
- `references/json-only-post-fix-review.md` — pattern for when the user asks
  for a focused post-fix review with strict JSON-only output (e.g. "Return
  ONLY valid JSON"). Covers staged-diff scoping, `git show :<file>` reads to
  verify removals and remaining plumbing, and the verdict template.
