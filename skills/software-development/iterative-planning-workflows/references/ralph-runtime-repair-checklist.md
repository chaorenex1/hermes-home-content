# Ralph Runtime Repair Checklist

Use this checklist when reviewing a Ralph implementation that spans the planning module, tool executor, CLI, gateway, or TUI.

## State-machine checks

- Judge `done` → review gate → explicit approval must end in `status=done`; no continuation may be queued.
- `from_json()` must restore every resume/audit field, especially `active_round`, bounded `history`, `rounds`, review state, and transition history.
- A backward transition from round 0 remains 0. Every transition updates the persisted canonical round and the returned `from_round`/`to_round` values.

## Execution-boundary checks

- Apply the planning-only guard before both sequential and concurrent executor dispatch.
- Keep the lower-level dispatcher guard as defense in depth.
- Verify special branches (`delegate_task`, `memory`, `todo`, context-engine tools) and tool-search unwrapping cannot bypass the policy.

## Surface-routing checks

- CLI, gateway, and TUI must recognize slash commands before review interception.
- Ordinary review text may be consumed only when state is `awaiting_review`.
- Completion and review responses must use the response shape consumed by each surface.

## Verification fallback

If the full test runner is unavailable, run:

```bash
python -m py_compile hermes_cli/ralph.py agent/tool_executor.py cli.py gateway/run.py tui_gateway/server.py
PYTHONPATH=. python - <<'PY'
# deterministic smoke test: reload state, approve done, and transition backward
PY
```

Report the missing test dependency honestly; do not claim the suite passed.