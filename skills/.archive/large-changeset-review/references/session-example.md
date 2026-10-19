# Session Example: 65-File Hermes Agent Pre-Commit Review

Worked example from a real pre-commit review of a large Hermes Agent working
tree on Windows. Shows the grouped-inspection protocol in action.

## Initial State

- `git status --porcelain`: 65 modified, 19 untracked (84 entries total)
- Diff size: 4,286 insertions, 1,832 deletions across 65 files
- Time span: multi-week accumulation

## Commands Used

```bash
# Full inventory
git status --porcelain > /tmp/status.txt
git diff --stat > /tmp/diffstat.txt
git diff --no-color > /tmp/full.diff

# Secret scan
grep -nEi '(api[_-]?key|secret|password|token|BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16})' /tmp/full.diff

# Risky pattern scan
grep -nE '^\+.*(shell\s*=\s*True|os\.system|eval\(|exec\(|pickle\.loads)' /tmp/full.diff

# Syntax check all modified Python
git diff --name-only -- '*.py' | xargs python -m py_compile
```

## Findings by Group

### Merge / Backup Artifacts (BLOCKING)

| File | Size | Why Blocking |
|---|---|---|
| `hermes_cli/web_server.py.orig` | 545KB / 13,734 lines | Editor merge backup of `web_server.py`; never intentional |
| `Python/` | 34MB | Python install-manager cache (`pythoncore-3.14-64`) |
| `~/` | 1KB | Literal tilde directory with `.mem0/config.json` containing user UUID |

### Lock-File Drift (BLOCKING)

`package-lock.json` lost 416 lines — all `@esbuild/*` optional platform deps.
Regenerated on Windows, drops non-Windows install support.

### Security-Sensitive Runtime Changes

- `tools/approval.py`: Refactored three bypass sites into
  `is_approval_bypass_active()`. Verified the helper still covers
  `approvals.mode == "off"`. Added `noninteractive_approval_required()`
  context for plugin-agent sessions.
- `agent/plugin_agent.py`: Added `_normalize_plugin_id()`, `_snapshot_json_value()`
  with depth/container/size bounds, `_normalize_tool_context()`. Removed
  "at least one toolset" requirement — verified by test
  `test_explicit_empty_toolsets_disable_every_tool`.
- `agent/background_review.py`: Removed provider-review request plumbing.
  Verified no dangling references to `ProviderBackgroundReviewRequest` or
  `build_background_review_router`.

### Test Deletions (Acceptable)

| File | Lines | Removed Tests | Verdict |
|---|---|---|---|
| `tests/run_agent/test_background_review_toolset_restriction.py` | -59 | `test_background_review_whitelist_includes_only_declared_provider_tools` | Tests removed provider-review feature; acceptable |
| `tests/run_agent/test_codex_app_server_integration.py` | -34 | `test_background_review_provider_trigger_fires_without_builtin_memory` | Tests removed provider-review feature; acceptable |
| `tests/hermes_cli/test_kanban_*.py` | -4 to -5 | None (fixture changes) | Acceptable |

### New Executable Modules

- `hermes_cli/ultrawork_kanban.py` (5,356 lines): New native swarm Kanban
  module. No `shell=True`, `eval`, `exec`, or raw `os.system` found.
- `apps/desktop/src/app/chat/swarm-entry-actions.tsx`: React component for
  swarm entry actions. No security issues.

## Final Staging and Repair

The initial tracked-only diff stat understated the commit candidate because it
excluded 18 untracked source/test/doc files. After artifact cleanup, staging
showed 82 files with 14,494 insertions and 1,433 deletions.

`git diff --check` had been clean before staging, but
`git diff --cached --check` found 4,458 trailing-whitespace reports in two new
files. Both files had mixed CRLF/LF endings. Only those files were normalized
to LF, re-staged, and checked again; the cached whitespace check then passed.

Changed-file tests also exposed an incomplete security boundary: ACP transport
fields were meant to be operator-controlled, but still appeared in the model
schema and were forwarded by model-facing dispatch. The narrow repair removed
those schema/dispatch fields while retaining direct trusted/config ACP plumbing
and defensive stripping of hidden per-task fields. The canonical targeted test
then passed 161/161. A focused independent review confirmed the final boundary.

The pre-existing `.orig` backup was moved outside the repository rather than
deleted, preserving recovery while keeping the commit clean. A final artifact
inventory was repeated after all test and reviewer tooling, then the committed
diff and worktree were read back.

## Final Verdict Shape

```json
{
  "passed": false,
  "blocking_findings": [
    {"path": "hermes_cli/web_server.py.orig", "line": 1, "rationale": "545KB merge backup; should not be committed"},
    {"path": "Python/", "line": null, "rationale": "34MB Python install-manager cache; should not be committed"},
    {"path": "~/", "line": null, "rationale": "Literal tilde directory with mem0 user UUID; indicates path-expansion bug and leaks user ID"},
    {"path": "package-lock.json", "line": null, "rationale": "416 lines removed; drops platform-specific esbuild deps, breaks non-Windows installs"}
  ],
  "nonblocking_findings": [
    {"path": "agent/plugin_agent.py", "line": 36, "rationale": "Empty toolsets=[] now allowed; AIAgent with enabled_toolsets=None receives all default toolsets — intentional per test coverage"}
  ],
  "recommended_targeted_tests": [
    "python -m pytest tests/agent/test_plugin_agent.py -v",
    "python -m pytest tests/hermes_cli/test_kanban_db.py -v",
    "python -m pytest tests/hermes_cli/test_ultrawork_kanban.py -v",
    "python -m pytest tests/hermes_cli/test_native_swarm_cli.py -v"
  ]
}
```
