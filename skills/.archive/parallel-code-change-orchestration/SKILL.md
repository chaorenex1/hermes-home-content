---
name: parallel-code-change-orchestration
description: "Safely repair or evolve one shared codebase with parallel delegated workers and parent-owned integration verification."
version: 1.1.0
author: Masía
created_by: agent
---

# Parallel Code-Change Orchestration

Use when a user asks to fix several independent defects or plan gaps in one repository through delegated workers.

## Core rule

Parallelize **independent mutation surfaces**, not merely independent problem statements. A shared schema, migration file, central registry, or broad integration test is a serialized ownership boundary.

## Workflow

1. **Map write ownership before delegating.**
   - List files each repair must edit.
   - Identify shared surfaces: database schema/migrations, central registries, package manifests, provider entrypoints, shared fixtures, and cross-cutting tests.
   - Put all work that needs one shared surface into one worker, or stage later work after that worker is verified.
   - Treat “read only” in a Worker prompt as an instruction, not a filesystem boundary. Before dispatch, record `git status --short` plus the intended writable path set; prefer an isolated worktree or a tool-denied audit lane when the parent will mutate the shared checkout concurrently.
   - If an allegedly read-only lane coincides with unexpected file changes, stop parent writes until the lane is terminal, re-read live task/run evidence, inventory changed and untracked paths, and re-read each file before editing. Never overwrite an externally changed file from a stale or paginated read. Use `references/read-only-auditor-shared-tree-contamination.md` for the bounded recovery sequence.

2. **Dispatch workers with bounded contracts.**
   Each worker prompt must state:
   - exact acceptance behavior;
   - owned files and prohibited files;
   - required migration compatibility, if applicable;
   - strict TDD cycle: focused RED test, minimal GREEN implementation, focused regression;
   - no commit and no drive-by refactor;
   - failure path: stop with a concrete blocker rather than fabricate evidence or weaken the contract.

3. **Keep the parent as integrator.**
   - Do not treat a worker summary as proof.
   - Re-read changed source before modifying it.
   - Immediately inspect each worker-owned tree with `git status --short`, a file inventory, and the focused test command. A worker can report tests or patches that only exist in its isolated worktree.
   - Read-only audits are snapshots, not locks. If an asynchronous audit returns after the parent has implemented or verified the change, classify every finding against the current source before acting; preserve still-valid structural gaps, discard superseded “not implemented” claims, and rerun only the targeted checks affected by follow-up fixes.
   - When a late audit identifies a cross-surface safety gap (for example a supposedly AI-only path still exposing manual CLI/tool decisions), repair the gap with a new RED/GREEN slice and rerun the full acceptance suite rather than appending an unverified caveat to the handoff.
   - Never publish a verified/completed handoff while an independent reviewer is still pending. If a late reviewer invalidates an earlier provisional result, repair every still-current finding with RED/GREEN evidence, rerun focused and full integration gates, dispatch a narrow follow-up reviewer against the final source, and wait for its terminal pass before the final completion claim.
   - Treat deletion of a pre-existing test as a regression by default. Restore it unless the worker gives a contract-level reason and a parent-visible replacement test.
   - Run a combined focused suite after all non-conflicting workers finish.
   - Repair stale tests that encoded superseded implementation details only when the new behavior fulfills the accepted contract.

4. **Recover and integrate isolated uncommitted worktrees deliberately.**
   - If a parallel runtime leaves useful uncommitted route worktrees, preserve them as evidence; do not force commits when commit authority was absent.
   - Integrate into a separate clean sibling checkout, never the user's original dirty checkout. Apply tracked diffs by explicit path set; copy untracked artifacts with source/target hash verification.
   - Inventory overlaps before applying. Nominally separate workers can invent competing abstractions for the same boundary. Select one ownership/API model, align roots and callers, and remove the duplicate rather than carrying two sources of truth.
   - After mechanical integration, run a combined focused suite before any semantic follow-up, then run the full suite. Record the isolated-worker test counts separately from integrated evidence.
   - If remaining work shares the now-dirty integration directory, replace parallel mutation with a sequential Dev → independent-QA dependency chain. A review handoff completes the Dev card; it must not self-block merely because QA is next.

5. **Stage shared-schema work.**
   - Never concurrently edit the same migration/schema file from two workers in a shared checkout.
   - Verify the first migration and its upgrade tests before dispatching follow-on work that depends on it.
   - Require a new monotonic migration version, data backfill where needed, schema verification, and restart compatibility tests.
   - For lifecycle-state expansion in SQLite, inspect existing `CHECK` constraints and append-only triggers before choosing a migration. If rebuilding a constrained base table would endanger foreign keys or immutable history, prefer a new versioned state/projection table plus an effective-state query; prove that default reads exclude the transitional state and that explicit resolution restores the allowed state.
   - Keep an implementation ledger when work is interrupted: `RED command/result → changed paths → GREEN command/result → remaining acceptance criteria`. A later integrator must resume from this evidence rather than infer completion from a partial diff.

### Non-committing shared-workspace execution

When commits are not authorized and a dirty repository must be edited in place:

1. Use exactly one active writer. Parallel workers may inspect, but their findings are snapshots and must not be wired as feature-delivery gates that can consume implementation retries while the writer is still changing the tree.
2. Run baseline audits before the writer or label them non-gating. Start fresh Functional QA only after the writer emits a terminal evidence packet and the shared tree is stable; follow with fresh Global QA and one Synthesizer.
3. Repeat the absolute repository path, frozen plan/spec path, `Do not commit`, protected dirty paths, failed criteria, and required commands in every generated recovery and QA task. Scratch/retry workers may not inherit the root task's workspace context.
4. Preserve a blocked historical runtime as evidence, but identify one active replacement chain. Archive or explicitly supersede abandoned branches so stale `todo` descendants are not reported as current work.
5. Update the external checklist from independent gate evidence: mark individually proven criteria complete and leave only unresolved integration/end-to-end gates in progress.
6. For hermetic packaging fixes, search every nested package-build command. Repairing one `pip wheel` invocation while a sibling still uses build isolation can leave the full suite network-dependent.

See `references/noncommitting-shared-workspace-recovery.md` for the compact topology, failure signatures, and verification checklist.

6. **Verify integration, not just slices.**
   - Run the full suite, smoke test, and build when applicable.
   - Run `git diff --check` and inspect the final diff/stat.
   - Treat new failures in unrelated integration tests as integration signals; trace whether they assert an obsolete implementation bridge or expose a real regression.
   - When the task grants a bounded writable-file list, still run adjacent public-contract tests read-only. If a required output grows (for example, a new diagnostic JSON count) and an unowned exact-payload test fails only because it lacks that field, do not edit it. Capture the exact command and delta as an integration handoff for its owner.

## Reference

- `references/sqlite-lifecycle-state-expansion.md` — migration and regression pattern for adding a non-terminal lifecycle state without rebuilding a foreign-keyed, append-only base table.

## Pitfalls

- **Parallel workers touching `schema.py` or equivalent:** leads to unmergeable migration drift. Serialize ownership.
- **Fake durable evidence:** do not add synthetic loop/audit records after a one-shot algorithm. Persist the actual work at the round/action boundary.
- **Worker-reported success:** a child claim is not acceptance evidence; parent must run tests and inspect relevant source/diff.
- **Stale tests after a deliberate architecture change:** update only after confirming the replacement path provides equal or stronger contract coverage.
- **Tool-surface changes hidden by tests:** compare schemas/CLI flags directly with the plan or public contract, not only with existing tests.
- **Cross-surface safety parity:** when a tool and CLI expose the same operation, add focused tests for both schema/parser acceptance and the shared service behavior. Require explicit safety acknowledgements for rebuild/destructive scope, and make export targets logical or profile-contained names rather than host paths.
- **Out-of-scope atomicity expansion:** do not edit a prohibited state-owner module merely to make a facade-level optimistic version check fully atomic. Implement and test the bounded preflight contract that the owned surface can enforce, then name the remaining TOCTOU limitation in the handoff so the owner can make the transaction atomic later.

## Integration of Parallel Worker Results

Treat integration as a first-class phase, not an implied consequence of worker completion:

1. Verify current worker state from runtime events; uncommitted files or a dispatch acknowledgement do not prove a worker is still running or finished.
2. Re-read every changed file and run each focused suite in the parent/integration checkout.
3. Run combined cross-boundary tests whenever workers changed shared public schemas, CLI/tool outputs, fixtures, migrations, or smoke scripts.
4. Trace deterministic full-suite failures back to the contract-changing route instead of dismissing them as unrelated.
5. Finish with focused tests, the full suite, smoke/build checks, and `git diff --check` after all integration repairs.

This section absorbs the former narrow parallel-integration workflow; partitioning, worker status, and final regression gates now live in one class-level skill.

## Completion checklist

- [ ] Each delegated change had exclusive file ownership or staged dependency ordering.
- [ ] Every new behavior had RED then GREEN evidence.
- [ ] Migrations are monotonic and upgrade-tested.
- [ ] Combined focused tests pass.
- [ ] Full suite, smoke/build, and diff checks pass.
- [ ] Any required independent reviewer has completed against the final stable source; no reviewer is still pending.
- [ ] Remaining plan gaps are explicitly listed; no success claim relies only on worker summaries.
