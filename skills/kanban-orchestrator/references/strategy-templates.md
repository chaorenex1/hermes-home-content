# Kanban strategy templates

Use `kanban_get_strategy` before creating a task when the work type is known.

## general
- scratch workspace
- max runtime 30m
- max retries 2
- acceptance: summary plus verification evidence

## code
- worktree workspace
- max runtime 2h
- max retries 2
- acceptance: changed files, tests passing, risks recorded

## research
- scratch workspace
- max runtime 2h
- max retries 2
- acceptance: sources, findings, uncertainty

## review
- scratch workspace
- max runtime 45m
- max retries 1
- acceptance: findings, severity, recommendations

## deploy
- scratch workspace
- max runtime 30m
- max retries 1
- acceptance: evidence or dry-run, rollback plan, result

Never retry deploy or permission failures indefinitely. Use `needs_input` for missing credentials or approval.
