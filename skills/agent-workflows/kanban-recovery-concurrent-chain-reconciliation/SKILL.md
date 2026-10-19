---
name: kanban-recovery-concurrent-chain-reconciliation
description: Reconcile a semantic QA failure when another Kanban controller creates a replacement chain concurrently.
---

# Concurrent Kanban Recovery Reconciliation

Use during a bounded recovery-controller pass when a failed QA gate has a clear rework strategy but another controller may be mutating the graph concurrently.

## Procedure
1. Read the failed gate's task, runs, metadata, comments, and its direct children. Extract the failed criterion, immutable SHA, passed regressions, and explicit changed strategy.
2. Inspect running/downstream tasks to contain dependency-wait retry loops. Block legacy CTO/verifier cards only after confirming their runs are looping on the semantic failure.
3. Before creating a replacement chain, search recent task titles/comments for an existing Dev → Functional QA → CTO QA chain with the same failed SHA and strategy.
4. If a concurrent valid chain exists, preserve it. Do not create another chain or rewire its cards.
5. If a duplicate was already created:
   - block its active Dev card with the routing/base anomaly and preserve evidence;
   - archive only its unstarted descendants, deepest-first;
   - never delete branches or task evidence;
   - append a correction record to the Swarm root Blackboard identifying the valid chain and the duplicate IDs.
6. Run exactly one dispatcher pass and read back the valid chain, contained legacy tasks, duplicate statuses, root comment, and board stats.

## Valid-chain checks
- Dev starts from the required immutable failed candidate, not master.
- Functional QA depends directly on Dev; CTO QA depends directly on Functional QA.
- Strategy is materially different and addresses the failed criterion.
- No master mutation, merge, rebase, force-push, or branch deletion is authorized.

## Pitfalls
- A native worktree task may default to the repository's current master when its intended base was not explicitly established. Treat that as an unsafe duplicate, not a valid rework.
- A task status of `running` can be a repeated dependency-wait loop; inspect runs/events rather than trusting status.
- Do not claim a new recovery chain is authoritative until post-mutation `show` confirms it.
