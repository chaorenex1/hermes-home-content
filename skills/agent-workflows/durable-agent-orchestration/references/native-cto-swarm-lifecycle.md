# Native CTO Swarm lifecycle

Use this reference when a durable Native Kanban Swarm starts from a root goal or a user-supplied plan path rather than an approved Ralph plan.

## Canonical roles and task graph

- `ceo == cto` is a naming correction, not a configurable role mapping. New Native actors, tasks, reports, route Judges, and finalization use `cto` directly.
- Dev and QA are paired per route. A completed Dev starts only its bound QA while unrelated routes continue.
- Ops contains only `opsconfig` and `opsdocs`; do not materialize `opsprotocol` for Native runs.
- A goal-only command starts CTO Planning. Preserve static Worker/Verifier/Synthesizer arguments only as compatibility mode.

The Controller copies the exact Root Goal. If the Goal names a plan file, CTO reads it and the Controller freezes its bytes/digest before any Dev starts. The minimal CTO-authored graph contains task `id`, `title`, self-contained `goal`, `origin` (`root_goal` step or `plan_stage` ref), dependencies, Dev/QA profiles, write scope, and acceptance criteria. Runtime fields—kind, canonical source refs, evidence contract, retries, workspace, branch, phase/status, source/spec digests, tenant, and skills—are Controller-derived. Persist immutable Intake separately from the once-frozen graph digest.

Every Dev and QA context receives the exact Root Goal, its task Goal, origin, complete frozen Plan when present, project contracts, accepted upstream handoffs, scope, acceptance criteria, and candidate identity.

## Fixed lifecycle

```text
Root/Intake
→ CTO Planning
→ [Dev_i → QA_i → CTO Route Judge] over accepted dependencies
→ Integration
→ Opsconfig
→ Opsdocs due check
→ CTO Final
→ merge Integration into original checkout/target branch
→ unconditional registered-worktree cleanup
→ creator completion/failure notification
```

`opsconfig` audits the integrated candidate and returns a commit or substantive no-op. Deleting tests requires proof that behavior was removed or equivalently covered; lack of references alone is insufficient.

`opsdocs` has no user-approval gate. When the Root has run longer than three days, it autonomously audits existing `AGENTS.md`, `CLAUDE.md`, `README*`, `.gitignore`, and `docs/**` against repository state, commits justified changes, or returns `completed_noop`. Run it after implementation/cleanup and before final acceptance so active Dev workers never see contract drift.

## CTO Final

New Native runs use one `cto_final` card instead of separate Global QA, Global Judge, and Synthesis cards. It receives all route/Ops evidence, runs global checks, judges Root Goal and frozen Plan coverage, and produces the final summary. CTO Final is read-only with respect to the candidate; findings create bounded Dev/Ops rework rather than CTO editing and self-approving. Historical three-stage rows remain readable.

## Worktree, main merge, and cleanup

Resolve one Root-owner `HERMES_HOME` in the creator/dispatcher process; workers must not recompute from profile-local homes. Persist:

```text
<HERMES_HOME>/worktree/<normalized-repository-key>/<kanban-root-task-id>/
```

Use subdirectories for integration, per-route attempts, opsconfig, and opsdocs. Normalize the canonical repository path to a bounded hyphen slug and prevent collisions with an owner record or path digest.

After CTO Final passes, attempt a no-ff merge from Integration into the original checkout and target branch frozen at Intake. Record Integration and main-merge SHAs. Conflicts/base drift fail the merge; never silently rebase/reset.

Cleanup runs in a `finally` path after the merge attempt and has no clean/branch/HEAD/SHA/active-attempt business preconditions. Force-remove registered worktrees, prune, then remove the registered Root directory if necessary. The non-negotiable security boundary is ownership: delete only paths registered for that Run and contained beneath the owner `HERMES_HOME/worktree` root. Merge failure still triggers cleanup and a failure/block notification.

## Required regressions

- Goal-only CLI creates Root + CTO Planning and no premature Dev cards.
- Plan path is frozen; Dev/QA receive exact Root Goal, task Goal, and Plan.
- CTO graph rejects cycles, unknown/same Dev-QA profiles, ownership conflicts, and replay drift.
- Each Dev starts only its paired QA; accepted dependencies release successors.
- New Native records contain `cto`, never `ceo`.
- Ops contains only opsconfig/docs; Docs runs automatically only when due.
- Exactly one `cto_final` replaces the old three-card global chain.
- Main merge precedes cleanup; merge failure still force-cleans registered worktrees.
- Dirty/drifted worktrees are deleted, while paths outside the owner root are refused.
- Completion includes CTO summary, Integration SHA, main-merge SHA, Ops outcomes, cleanup outcome, and risks.
