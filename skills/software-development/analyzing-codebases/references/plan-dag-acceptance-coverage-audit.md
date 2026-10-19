# Plan DAG and Acceptance Coverage Audit

Use this reference for read-only audits of a proposed multi-task implementation plan against the current repository.

## Required evidence matrix

Create one row per Acceptance criterion, preserving multiplicity: a criterion covering three settings is three runtime obligations, not one.

| Criterion | Runtime owner/task | Production files | Focused test | Release command | Verdict |
|---|---|---|---|---|---|
| exact behavior | task/step | exact current owners | exact test | executable check | pass/partial/fail |

Mark **fail** when no runtime Task exists. Mark **partial** when a Task exists but its file list, test, migration, or verification command is incomplete.

## Change-cone inventory

For each behavior, inspect and compare:

1. Defaults/schema and validators.
2. Load migration and direct save/update normalization.
3. Runtime reads at the narrowest owner.
4. Public entrypoints and alternate/first-turn routes.
5. DTOs/serializers, file artifacts, database tables, and migrations.
6. Policy/allowlist routers and host-side membership validation.
7. Tests, docs, diagnostics, and release checks.

Common omission pattern: a Task names the orchestrator but misses the router that authorizes values, the store DTO that records them, or the physical schema that must persist them.

## Configuration-specific checks

For every new setting record:

| Setting | Exact persisted key | Default | Validator | Legacy mapping | Runtime read | Non-default test |
|---|---|---|---|---|---|---|

Additional rules:

- Sibling cadence/depth/budget settings need separate runtime evidence.
- A legacy key must be accepted and normalized by both `load(old_file)` and direct `save({old_key: value})` if the public writer previously accepted it.
- Two independent budgets need two effective values and a test proving truncation in one layer cannot spend the other layer's allowance.
- Document whether a compatibility alias is load-only, write-compatible, or rejected.

## DAG audit

Parse declared dependencies into a directed graph and compute transitive reachability. For each Task pair with no path in either direction, intersect planned modified files. Any non-empty intersection is a parallel-write hazard unless the plan explicitly provides isolated worktrees and a merge owner.

Also flag:

- A Task consuming a table/column/artifact introduced only by a downstream Task.
- A recovery Task not depending on every Task that produces the recoverable state.
- Parallel migrations that both advance one schema version chain.
- A verification/cleanup Task that is the first place an essential behavior is mentioned.

A minimal deterministic probe can parse `### Task N`, each Files list, and the handoff edges, then report unordered shared-file pairs. Treat parser output as evidence, not as a substitute for semantic dependency review.

## Public-route completeness

When the target is strict context layering or one canonical renderer, enumerate every production route that can emit model-visible content:

- normal prefetch;
- first-turn/system-context preparation;
- background cache fallback;
- legacy wrappers;
- direct tool/CLI serialization;
- transport fences and context-stripping helpers.

Define whether an outer transport fence counts as a semantic layer. Test the combined host-visible result, not only each renderer in isolation.

## Test evidence discipline

Run a bounded existing baseline to show the repository is currently coherent, but report it separately:

- **Baseline green:** existing behavior still passes.
- **Planned coverage:** future Acceptance has an owning red test and runtime Task.

A green baseline never upgrades a missing planned test from fail to pass.

## Report format

1. Outcome: approvable or blocked.
2. Blocking gaps: criterion → missing Task/file/test → exact correction.
3. Non-blocking clarifications: naming, docs, compatibility-window semantics.
4. DAG hazards: unordered shared writes and reversed dependencies.
5. Acceptance matrix: pass/partial/fail.
6. Verification evidence and unchanged-worktree proof.

Always name the exact Task and exact test to add or modify. Do not stop at “needs more coverage.”
