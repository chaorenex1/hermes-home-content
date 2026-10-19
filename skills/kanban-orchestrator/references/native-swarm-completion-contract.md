# Native Swarm completion-contract and blocked-run recovery

## Failure signature

A repository-backed Native Swarm may create valid worktrees and let Workers finish, yet set the shared runtime to `blocked` immediately after the first completion while sibling Workers remain healthy and running.

Confirm all three facts before acting:

1. The completed Kanban task has a human-readable `summary` and useful structured `metadata`.
2. The shared runtime parser requires `summary` (or `report`) itself to decode as a complete `ULTRAWORK_REPORT_V1` envelope.
3. The completion hook forwards only `summary`, not run metadata.

A typical deterministic rejection is `completion lacks a valid ULTRAWORK_REPORT_V1 JSON envelope` or `completion lacks ULTRAWORK_REPORT_V1 identity`. If status output shows `blocked` with no reason, inspect the runtime completion parser and the completed task's run/event evidence; status may point at another still-active route and hide the actually blocked route.

## Prevention before dispatch

For a repository-backed code Swarm, make these contracts explicit in the frozen root goal and each Worker context:

- The Worker must call `kanban_complete(summary=<serialized full ULTRAWORK_REPORT_V1 JSON>, metadata=<machine-readable duplicate/index fields>)` when the installed runtime parses the summary field.
- The report must contain exact bound identity: workflow ID, route key, attempt, phase, source digest, spec digest, optional child key, and substantive command or artifact evidence.
- Generic Kanban guidance that asks for a 1–3 sentence summary is insufficient and can conflict with the runtime contract. Verify the actual completion hook/parser before large fan-out.
- A worktree candidate must be a clean commit when the runtime derives candidate SHA and integrates branches. Obtain commit authorization before choosing this backend; explicitly require an isolated route-branch commit and clean status. If commits are not authorized, use a non-committing execution path instead.
- Run a one-route completion smoke before large fan-out whenever the installed Native runtime or worker prompt contract has changed.

## Recovery

1. Do not cancel healthy sibling Workers merely because the composite runtime blocked on one malformed completion.
2. Record the exact transport mismatch on the root Blackboard and preserve all worktrees, branches, logs, test evidence, and dirty status.
3. Run one public reconcile pass. If it advances nothing, do not generic-unblock the run or edit the Kanban database.
4. Inspect each terminal worktree for changed paths, clean/dirty status, commit SHA, tests, and overlap. A `done` Worker with a dirty worktree is not an integration candidate.
5. After remaining Workers finish, create a bounded replacement integration/QA path that explicitly fixes both defects: strict report transport and clean immutable candidate commits. Reconcile duplicate implementations and overlapping files before QA.
6. Independent QA must verify the integrated candidate, not isolated Worker claims. Preserve the blocked original run as audit evidence.

## Common overlap pattern

Parallel routes may independently invent competing source abstractions (for example, two filesystem-source modules) even when their nominal file ownership differed. Treat this as an integration design conflict: select one API, migrate callers/tests, and delete the duplicate rather than merging both implementations.

## Non-committing recovery path

When isolated route commits were not authorized, do not force commits after the fact merely to satisfy the blocked runtime:

1. Wait for every still-healthy sibling Worker to reach a terminal Kanban state; monitor those Worker IDs, not the composite runtime that is already blocked.
2. Inventory every route worktree with `status --short`, changed paths, focused/full test evidence, and content hashes for untracked files.
3. Recover into a separate clean sibling checkout, never the user's original dirty checkout. Apply tracked diffs mechanically, copy untracked artifacts with hash verification, then resolve overlapping APIs deliberately.
4. Run one integrated focused suite and one full suite before creating follow-up work.
5. Create a **sequential** standalone Dev → independent-QA dependency chain using `dir:<integration-path>` and explicit `Do not commit` contracts. Serialize stages because they share one dirty directory. Use the blocked Swarm root only as a Blackboard; do not make it a dependency parent, because it cannot release children.
6. Require each standalone implementation card to complete normally with a review handoff. `review-required` is not a reason to self-block when an explicit QA child depends on the card.

This path preserves the no-commit constraint while retaining durable task state and independent verification. It is a recovery backend, not evidence that the original Native run completed.

## Dispatcher and monitor isolation

A malformed Native run can have `runtime.status=blocked` while its root Kanban card remains `status=running` with an expired controller claim. A board-wide `dispatch` pass may reclaim and spawn that root as an ordinary Worker while also dispatching the recovery chain.

- Before starting an automatic dispatcher loop, make the failed root an inert audit anchor through a supported public transition, or place the recovery chain on a separate board. Never edit the Kanban database directly.
- If isolation is unavailable, inspect every dispatcher result for an unexpected root spawn and stop the loop rather than allowing duplicate orchestration.
- Do not use the failed root's runtime status as the recovery monitor stop condition; it is already terminally blocked. Monitor the ordered recovery-card IDs: stop on the first active-chain block or when the final synthesis is done.
- A monitor should emit only state changes and use a bounded deadline. It should not repeatedly print heartbeats or retry an unchanged blocked card.
