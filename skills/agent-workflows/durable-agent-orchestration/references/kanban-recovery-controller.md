# Kanban recovery controller

Use when a durable Swarm has blocked work. Run exactly ONE board-wide Recovery Controller for all active roots — never one controller or cron job per plan. On each pass, discover active roots across boards, inspect live task/run/comment evidence, and make at most one bounded decision per failed route.

## Evidence packet

For each blocked task, collect live `show`, `runs`, and latest comment/log evidence:

- task status, parents, children, assignee, workspace/branch;
- blocking reason and run outcome;
- immutable candidate SHA and base ancestry where code is involved;
- raw focused/full test evidence and clean status;
- direct QA children and downstream integration children.

Never infer a blocker from a stale notification.

## Decision table

| Evidence | Controller action |
|---|---|
| `review-required` plus SHA, clean status, tests, risks, and a direct QA child | Complete the Dev task as `handoff_state=awaiting_review`; dispatch QA. |
| QA `gate: fail` with a named failed criterion and changed recovery strategy | Create one idempotent Dev → Functional QA → CTO QA rework chain; rewire downstream only after read-back verification. |
| Same route/SHA/criterion already has an active recovery chain | Archive the duplicate subtree and its duplicate parent; keep comments/runs as lineage. |
| Wrong-base, dirty, or target-file-missing assigned worktree | Do not edit/reset it; treat it as routing evidence and stop the duplicate. |
| Integration merge conflict | Stop unless the user explicitly authorizes resolution; resolve only in the isolated integration worktree, then run focused and full validation before creating the integration commit. |
| Security, credentials, permissions, missing evidence, or no changed strategy | Keep blocked and request exact human input on the root Blackboard. |

## Safe dependency replacement

1. Link the replacement parent to every downstream child.
2. Read each child back and confirm both expected prerequisites are present.
3. Remove the obsolete parent edge with the board CLI.
4. Read each child back again.
5. Archive superseded children before their parent so archival cannot promote stale work.
6. Dispatch once and verify resulting task statuses.

Never edit the board SQLite database directly.

## Dedupe key

```text
recovery:<route>:<failed-candidate-sha>:<failed-criterion>:<strategy-number>
```

Check it before creating any card. The controller must not create a second active chain for the same identity.
