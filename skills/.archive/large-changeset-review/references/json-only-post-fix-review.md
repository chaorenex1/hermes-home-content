# JSON-Only Post-Fix Review

When the user explicitly asks for a post-fix pre-commit review with a strict JSON-only output format (e.g., "Return ONLY valid JSON", "Output exactly: {...}", "Do not include prose outside JSON"), follow this pattern.

## Trigger

- User says "post-fix review", "pre-commit review", "verify the fix", or similar
- User specifies exact JSON shape with `passed`, `blocking_findings`, `nonblocking_findings`, `summary`
- User forbids prose outside JSON
- User asks to inspect `git diff --cached` or staged changes

## Workflow

1. **Get the staged diff**: `git diff --cached -- <files>` (or all files if none specified)
2. **Get staged status**: `git status --short` (check for secret/artifact paths)
3. **Read the full staged file** (not just diff) for context on remaining ACP/config plumbing: `git show :<file> | grep -n "<pattern>"`
4. **Verify each requested assertion** systematically:
   - Absence of removed fields from model schema / dynamic overrides
   - Absence of removed args from model-facing dispatch / registry handlers
   - Presence of defensive stripping (e.g., `_strip_model_hidden_task_fields`)
   - Presence of trusted direct-call signature and config plumbing
   - Clean staged status (no secrets, logs, build artifacts, temp files)
5. **Construct the JSON verdict** exactly as requested

## Key Commands

```bash
# Diff scoped to relevant files
git diff --cached -- tools/delegate_tool.py run_agent.py > /tmp/diff.txt

# Staged status
git status --short > /tmp/staged.txt

# Search staged content for patterns (not just diff)
git show :tools/delegate_tool.py | grep -n "acp_command\|acp_args"
git show :tools/delegate_tool.py | grep -n "_MODEL_HIDDEN_TASK_FIELDS\|_strip_model_hidden_task_fields"
git show :run_agent.py | grep -n "acp_command\|acp_args"

# Check staged paths for secrets/artifacts
cat /tmp/staged.txt | grep -E "\.env|secret|credential|token|key|\.log|\.tmp|\.bak|\.zip|\.tar|\.gz|\.sqlite|\.db|\.pyc|node_modules|__pycache__|dist|build"
```

## JSON Output Template

```json
{"passed":true|false,"blocking_findings":[],"nonblocking_findings":[],"summary":"..."}
```

- `passed=false` only for concrete code/status blockers with `path:line` evidence
- `blocking_findings` = concrete issues that must be fixed before commit
- `nonblocking_findings` = observations that don't block commit
- `summary` = one-sentence verdict with evidence

## Pitfalls

- **Don't run tests** unless explicitly asked — the user said "do not run tests"
- **Don't include prose outside JSON** — the user said "do not include prose outside JSON"
- **Read staged files, not just the diff** — the diff shows what changed, but `git show :<file>` shows what remains, which is needed to verify "fields are absent" and "plumbing remains"
- **Check the full schema definition**, not just the diff hunk — the diff shows removals, but you need to confirm the remaining schema is clean
- **Staged status check is mandatory** — a clean diff doesn't mean clean status if artifacts were staged accidentally
