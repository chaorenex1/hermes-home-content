# TUI Ralph session binding

## Symptom
A plan exists and is `active`, but it has `current_round: 0` and no continuation/review event after the planning response.

## Root-cause check
Compare the live TUI conversation/session identifier with the Ralph plan record's `session_id`. The TUI transport-facing id may differ from the durable `session["session_key"]`. Ralph state and the post-turn hook are keyed strictly by the durable session key.

## Correct TUI command path
When `/ralph <objective>` starts a plan, route through the lifecycle tool with the live key:

```python
ralph_execute_tool(
    action="start",
    objective=objective,
    runtime_session_id=str(session["session_key"]),
)
```

Do not fall back to the transport request id. Consume the tool's structured `status` and `plan` response, and surface its error cleanly.

## Regression test seam
At `command.dispatch`, inject a distinct transport id and session key, mock `ralph_execute_tool`, dispatch `/ralph`, and assert `runtime_session_id` equals the live session key. This catches state being created where the TUI post-turn hook cannot find it.

## Behavioral boundary
Correct session binding enables the Ralph lifecycle hook only. Review-gated Ralph still transitions to `awaiting_review` after a planning turn; a user approval is required before the next continuation is queued unless that policy is deliberately changed.
