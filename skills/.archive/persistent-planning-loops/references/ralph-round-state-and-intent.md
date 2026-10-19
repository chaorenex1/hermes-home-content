# Ralph round state and intent classification

Session-derived implementation notes:

- Ralph state is separate from `/goal` execution state and is persisted under `ralph:<session_id>`.
- `/ralph resume <selector>` should recover by session ID, plan path/filename, or enumerated plan index, then save the same state under the current session ID and enqueue a continuation prompt.
- A round record should capture: round number, timestamp, model response, judge verdict/reason, current goal/subgoals, and a bounded conversation snapshot. Persist after judging so rollback data corresponds to the evaluated turn.
- Keep the record bounded (for example, latest 50 rounds) and filter conversation fields to role/content/name/tool name; do not persist unrestricted tool arguments or secrets.
- End-of-round judging must verify both actionable plan completeness and coverage of every declared goal/subgoal. Generic “plan looks good” claims are insufficient.
- Route user changes by `{target: goal|plan, action: add|modify|delete}`. Goal changes alter acceptance criteria/subgoals; plan changes alter only the designated plan file.
- Ralph surfaces must stay aligned across CLI, gateway, and TUI/Desktop. Remove `pause` from Ralph command registration and handlers, while retaining an internal paused status for finite-budget exhaustion so the plan remains resumable.
- TUI/Desktop dispatch must return supported payloads (`exec.output` for immediate command output and `send.message` for a queued planning turn); unsupported response shapes can render as no output.
