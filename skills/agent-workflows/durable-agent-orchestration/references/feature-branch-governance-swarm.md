# Feature-Branch Governance Swarm

Use when an approved Ralph RouteManifest executes as a multi-role software-delivery swarm.

## Branch / PR ownership

- One Ralph plan owns one integration branch: `feat/ralph-<plan-id>` and one Draft PR to the declared base branch.
- Each dependency-ready route attempt gets its own branch/worktree based on the recorded integration SHA; never let a worker default to the repository's moving `HEAD`.
- Preflight must require a readable Git repository and clean base worktree. Put controller-created worktrees outside the repository worktree or exclude them deliberately, otherwise they make `git status` dirty.
- Dev handoff requires route branch, commit SHA, clean status, diff range, and raw test output. Functional QA verifies that exact candidate revision. CTO QA validates process completeness, scope, style/static checks, and merge eligibility.
- Integrate accepted route commits into the plan-owned branch in dependency order. Block on merge conflict or base drift. PR lifecycle is idempotent: record branch, PR number/URL/head SHA; never auto-merge, force-push, close, or delete branches without an explicit policy.

## QA split

- Functional QA: requirement behavior, error paths, regression, reproducible tests.
- CTO QA: plan digest, evidence/handoff completeness, branch/commit integrity, changed-file scope, code-style and project-config consistency.
- Neither `done` nor QA prose is acceptance. A criterion-cited CTO decision over raw evidence is the promotion gate.

## Observer operations team

- Ops Docs, Ops Config, and Ops Protocol are read-only against the execution board and feature branch.
- Snapshot governance at dispatch: agent/project instructions, changelog, ignore/config/static rules, CI metadata, and protocol version/digests.
- Ops emits versioned observations and maintenance proposals. It may block only demonstrated security, compliance, reproducibility, or CI-breakage issues.
- All other docs/config/protocol changes use a separate `ops/<run-id>/<topic>` maintenance branch/PR; never modify active worker context or an in-flight feature branch.

## Hook safety

- Kanban lifecycle hooks are observers, often running in worker processes. Install the plugin in dispatcher and every participating profile.
- Hooks write append-only, idempotent observation snapshots only. They must not directly create successor tasks or mutate route state.
- Use a separate explicit controller decision (`snapshot_id + expected plan digest/revision + structured report`) to perform transitions. Persist malformed reports as evidence and fail closed.
