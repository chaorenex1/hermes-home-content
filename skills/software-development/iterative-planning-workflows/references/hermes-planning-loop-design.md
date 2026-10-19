# Hermes Planning Loop Design Notes

## Session-derived distinction

| Mode | Repeats automatically | Writes | Purpose |
|---|---:|---|---|
| `/plan` | No, normally one turn | Only the Markdown plan | Produce an actionable plan without execution |
| `/goal` | Yes, until judge/budget/user stop | Normal agent workspace | Keep implementing a goal |
| Proposed `/plan-goal` | Yes, until plan judge/budget/user stop | Only one designated plan file | Iteratively improve a plan without implementing it |

## Why reusing `/goal` directly is unsafe

The existing execution goal loop uses a continuation prompt that asks the agent to take the next concrete step. Even if the plan skill is loaded, a normal agent runtime may still expose terminal and file mutation capabilities. A planning-only loop must have both a planning-specific prompt and a tool/write boundary.

## Suggested state

Use a separate state key such as `plan_goal:<session_id>` so planning state cannot collide with implementation goals. Persist at least `goal`, `plan_path`, `status`, `turns_used`, `max_turns`, `subgoals`, and the latest judge verdict/reason.

## Suggested judge contract

```json
{"verdict":"done|continue|blocked","reason":"evidence-based explanation"}
```

`done` means the plan has a concrete outcome, boundaries, assumptions, ordered tasks, exact paths/interfaces where known, verification, risks, and stop conditions. `continue` identifies a missing planning artifact. `blocked` identifies a decision that must come from the user.

## Acceptance matrix

| Scenario | Expected result |
|---|---|
| Initial `/plan-goal` | Read context, write designated plan only |
| Judge says continue | Same plan path is refined in a new planning turn |
| Judge says done | Loop stops with plan path and evidence |
| Judge says blocked | State pauses and asks for the missing decision |
| Turn budget exhausted | State pauses; no automatic execution |
| Forbidden source/config write | Tool/controller rejects it |
| User sends real message | Automatic continuation is preempted |
| `/plan-goal resume` | Same plan and criteria are restored |
| `/plan-subgoal` | Criteria persist and affect the next judge |
| Existing `/goal` | Execution semantics remain unchanged |

## Implementation surface in the Hermes source tree

Likely areas are `hermes_cli/goals.py` for reusable persistence/judge mechanics, `cli.py` and `hermes_cli/commands.py` for the CLI command, `gateway/slash_commands.py` for gateway parity, and tests under `tests/hermes_cli/` plus CLI/gateway tests. Keep the bundled `skills/software-development/plan/SKILL.md` one-turn contract intact; add a controller around it rather than weakening its restrictions.
