# Kanban Health Check

Run `kanban_board_health` or `hermes kanban stats --json`.

Check:
- ready tasks older than the expected dispatch interval;
- running tasks with expired claims or stale heartbeat;
- blocked tasks and their reasons;
- crashed, timed_out, gave_up, spawn_failed, and protocol_violation events;
- worker logs for new startup errors;
- Gateway and Dispatcher status.

If a task is stale, do not manually edit the database. Inspect `show`, `runs`, and `log`; let Dispatcher reclaim it or use the documented reclaim/reassign path.

If failure events exist:
- transient: allow bounded retry;
- capability or needs_input: notify and block;
- repeated failures: keep the circuit breaker active and escalate.
