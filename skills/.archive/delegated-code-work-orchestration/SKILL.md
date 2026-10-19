---
name: delegated-code-work-orchestration
description: "Dispatch code work to workers or agent CLIs; verify."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [delegation, coding-agents, cli, worktrees, parallel, controller-plugin, verification]
    related_skills: [durable-agent-orchestration, hermes-kanban-orchestration, test-driven-development]
---

# Delegated Code Work Orchestration

One class: code work done by something that is not you — an external coding CLI, parallel delegated workers, or a controller plugin — plus the parent-side obligation to prove the repository state that resulted. Covers dispatch, isolation, integration, and automating the loop.

## When to Use

- "Implement/refactor/fix this with Claude Code / Codex / OpenCode."
- "Fix these several defects in parallel" / "spin up workers for each of these."
- "Build the controller that dispatches, reviews, and integrates this automatically."
- "Integrate what the workers produced."

Don't use for: durable plan→execution workflow state machines and their manifests/review gates (`durable-agent-orchestration`), Kanban board operation (`hermes-kanban-orchestration`), or review-lane verdicts on a Kanban handoff (`sdlc-review`).

## Dispatch contract (every worker, every provider)

1. Confirm repository/workdir, task boundaries, Git state (a clean `git status --short`), tool version, and authentication readiness.
2. Write a bounded prompt: acceptance criteria, allowed write scope, prohibited files/operations, required tests, and the failure path — stop with a concrete blocker rather than fabricate evidence or weaken the contract.
3. Prefer the provider's non-interactive one-shot command; use a PTY only when required, and long bounded work via a background process that you monitor — never shell `&`.
4. Give every concurrent writer its own worktree/workdir.
5. Answer worker prompts only within the user's authority and the task scope. Use the narrowest permission mode that can finish the task; dangerous bypass modes need explicit justification, a constrained workdir, a clean Git state, and diff review, and never authorize an unrequested commit, push, deploy, or unrelated-file edit.
6. Wait for completion, then inspect Git state, diff, and test output yourself — worker prose is not verification. Clean up PTY/tmux/process sessions and temporary worktrees.

Provider specifics (Claude Code print mode/tmux/permissions; Codex exec, PTY/sandbox caveats, gateway behaviour; OpenCode run/TUI lifecycle, provider selection) are archived with the former provider playbooks at `.archive/coding-agent-cli-orchestration/references/` — read the matching file before invoking that CLI.

## Parallel work: ownership, not problem statements

1. **Parallelize independent mutation surfaces.** A shared schema, migration file, central registry, package manifest, provider entrypoint, shared fixture, or broad integration test is a serialized ownership boundary: all work touching one such surface goes to one worker, or a later stage waits for the earlier one to be verified.
2. **Map write ownership before dispatch.** List the files each change must edit, name the shared surfaces, record `git status --short` plus the intended writable path set, and prefer an isolated worktree or a tool-denied audit lane whenever the parent will mutate the shared checkout concurrently.
3. **"Read only" is an instruction, not a filesystem boundary.** If an allegedly read-only lane coincides with unexpected changes, stop parent writes until that lane is terminal, re-read live task/run evidence, inventory changed and untracked paths, and re-read every file before editing. Never overwrite an externally changed file from a stale or paginated read.
4. **Stage shared-schema work.** Never let two workers edit the same migration/schema file in a shared checkout; verify the first migration and its upgrade tests before dispatching dependent work; require a new monotonic migration version, data backfill where needed, schema verification, and restart-compatibility tests. For lifecycle-state expansion in SQLite, inspect existing `CHECK` constraints and append-only triggers first — when rebuilding a constrained base table would endanger foreign keys or immutable history, prefer a new versioned state/projection table plus an effective-state query, and prove default reads exclude the transitional state.
5. **Keep an implementation ledger** when work is interrupted: `RED command/result → changed paths → GREEN command/result → remaining acceptance criteria`. A later integrator resumes from that evidence instead of inferring completion from a partial diff.

## Parent-owned integration

1. **Worker claims are not acceptance evidence.** Re-read changed source, and inspect each worker-owned tree with `git status --short`, a file inventory, and the focused test command — a worker can report tests or patches that exist only in its isolated worktree.
2. **Sequence:** combined focused suite once all non-conflicting workers finish → full suite → smoke/build when applicable → `git diff --check` and a final diff/stat review.
3. **Late audits are snapshots, not locks.** Classify every late finding against the current source: keep still-valid structural gaps, discard superseded "not implemented" claims, rerun only the checks affected by follow-up fixes. Repair a late cross-surface safety gap (for example a supposedly agent-only path still exposing a manual route) with a fresh RED/GREEN slice and a rerun of the full acceptance suite, not a caveat. Never publish a verified or completed handoff while an independent reviewer is still pending.
4. **Test ownership.** Treat deletion of a pre-existing test as a regression by default: restore it unless the worker gives a contract-level reason plus a parent-visible replacement test. Repair stale tests that encode superseded implementation details only when the new behavior fulfills the accepted contract.
5. **Trace integration failures.** New failures in unrelated integration tests are integration signals: decide whether they assert an obsolete bridge or expose a real regression. When the task grants a bounded writable-file list, run adjacent public-contract tests read-only and hand any required-but-unowned edit to its owner instead of making it.
6. **Recover isolated uncommitted work deliberately.** Preserve it as evidence and do not force commits when commit authority was absent; integrate into a separate clean sibling checkout, never the user's dirty checkout; apply tracked diffs by explicit path set and copy untracked artifacts with source/target hash verification; inventory overlaps and settle on one ownership/API model rather than carrying two sources of truth; record isolated-worker test counts separately from integrated evidence. When further work shares the now-dirty integration directory, switch from parallel mutation to a sequential Dev → independent-QA chain.
7. **Non-committing shared-workspace mode.** Exactly one active writer (parallel workers inspect only; their findings are snapshots, never gates that consume implementation retries). Baseline audits run before the writer or are labelled non-gating. Start fresh Functional QA only after the writer emits a terminal evidence packet and the tree is stable, then Global QA and one synthesizer. Repeat the absolute repository path, frozen plan path, "do not commit", protected dirty paths, failed criteria, and required commands in every generated recovery and QA task — a scratch worker does not inherit the root task's workspace context. Preserve a blocked historical runtime as evidence while identifying exactly one active replacement chain, and supersede stale `todo` descendants so they are not reported as current work.

## Automating the loop: controller plugins

Use when the durable workflow lives in a plugin that turns immutable plans into task graphs, worker handoffs, review gates, or external integration lifecycles. This is the implementation arm of `durable-agent-orchestration`; its state-machine, judge, and evidence semantics stay owned there.

1. **Constrain the write scope.** Confirm the plugin repository; never edit host/core code merely because the plugin imports it (core is inspectable for public API signatures only).
2. **Orient before changing code.** Read the manifest/entrypoint, state schema, controller lifecycle, and every plugin test; record the existing test command and a clean git state.
3. **Use vertical TDD slices.** Per lifecycle boundary: one behavioral test → red → smallest implementation → green. Never batch all tests before implementation.
4. **Inject external effects.** Git-hosting/PR/network behaviour sits behind a tiny injected protocol or client; tests use a fake client and assert payload plus idempotency; production code must not secretly call a remote provider.
5. **Keep observer and controller roles separate.** Hooks record immutable observations only. A state transition requires an explicit authorization artifact that references the observation and carries a replay-resistant identity; reject reused authorization IDs with an explicit error.
6. **Treat durable state as an upgrade surface.** Additive migrations, explicit columns in inserts, unique keys for idempotency/replay protection, and a persisted audit event for every transition.
7. **Freeze one validated child graph per parent route** and reject replacement; validate child IDs, bounded attempts, source provenance, dependency references, duplicate edges, self-dependencies, and cycles; dispatch only dependency-ready children. A parent may enter `awaiting_children` but is not accepted until every child is independently accepted — a failed or exhausted child blocks parent closure.
8. **Generate run-owned branches.** Derive feature and integration branch names from the durable run ID, not only the plan ID, so completed runs cannot collide with new ones; persist base repository, base branch, feature branch, integration branch, and PR lifecycle state; keep a run-owned feature worktree for Dev work only (never send a branch name with scratch QA tasks); keep PR opening idempotent and require completed execution before opening it unless asked otherwise.
9. **Govern Ops lanes.** Snapshot tracked governance files and persist snapshot ID plus digest before creating run worktrees; create read-only Ops observer tasks linked to that snapshot; accept only versioned maintenance proposals from registered Ops tasks and record them as proposals, never as feature-branch mutations.
10. **Notifications are a durable projection, not workflow truth.** Capture the originating Gateway routing descriptor at creation (`gateway.session_context.get_session_env(...)`, with environment fallback only when no ContextVar value exists) and persist platform, chat ID, chat type, thread ID, user ID, session key, and notifier profile via `kanban_db.add_notify_sub` — never infer a group/DM destination or hard-code a platform, and leave a CLI/cron caller with no durable target unsubscribed rather than pretending it can deliver. Write the controller event plus an idempotent outbox row in controller state, publish to the root Kanban `task_events` only after the controller transaction commits, keep a persisted dedupe key in the payload, and mark the outbox row published only after verifying the root event exists. Reuse native notifier kinds (`swarm_created`, `swarm_progress`, `swarm_blocked`, `swarm_completed`) so Gateway/TUI delivery stays centralized, and give a terminal `swarm_completed` a non-empty synthesis summary grounded in the final verified handoff. Delivery failure must never accept, unblock, or otherwise mutate execution state.
11. **Replace a local plugin without leaving a shadow copy.** Stage the new tree outside the active plugin directory, stop the Gateway, move the old tree to a backup root **outside** `$HERMES_HOME/plugins/` (a renamed backup inside `plugins/` is rediscovered as a duplicate manifest and can override the active copy in `hermes plugins list` and at Gateway load), place the verified staged tree at the canonical path, restart once, then verify the canonical manifest hash/version and `hermes plugins list --plain --no-bundled` before a controlled installed-code smoke run. A source test suite is not proof that the installed manifest is enabled.
12. **Deployment verification.** Run `python -m py_compile` over the controller modules, the plugin's unittest discovery, `git diff --check`, and `git status --short`; strip generated `__pycache__`/`.pyc` from the diff; ensure the final test run follows the last implementation or test edit; commit only when green and report the actual commit SHA plus any unverified limitation. On Windows, close `kanban_db.connect(...)` explicitly in SQLite tests — a bare connection context manager commits without releasing the handle before temporary-directory cleanup.
13. **Browser-provider plugins are a different class.** For a plugin that owns a Chromium process, exposes loopback CDP, synchronizes an isolated browser profile, provides logical tabs, evaluates target-scoped JavaScript, or requests native browser takeover, follow `cdp-browser-automation`: `Target.activateTarget` is not a target-isolation primitive, and takeover consent must come from the human in the browser's own permission UI — never a chat confirmation, synthetic consent page, or agent-clicked approval.

## Pitfalls

- **Parallel workers touching one migration/schema/registry file:** unmergeable drift. Serialize ownership.
- **Fake durable evidence:** never add synthetic loop/audit records after a one-shot algorithm; persist the actual work at the round/action boundary.
- **Tool-surface changes hidden by tests:** compare schemas/CLI flags against the plan or public contract, not only against existing tests.
- **Cross-surface safety parity:** when a tool and a CLI expose the same operation, test both the schema/parser acceptance and the shared service behaviour, require explicit safety acknowledgements for destructive scope, and keep export targets logical or profile-contained rather than host paths.
- **Out-of-scope atomicity expansion:** do not edit a prohibited state-owner module just to make a facade check fully atomic — implement the bounded preflight contract the owned surface can enforce and name the remaining TOCTOU limitation in the handoff.
- **Orphan processes/sessions** left behind by a worker, and stale tests updated without confirming the replacement path gives equal or stronger coverage.

## Verification checklist

- [ ] Repository scope, Git state, tool version, and auth confirmed before dispatch.
- [ ] Every worker had a bounded contract, exclusive file ownership or staged dependency ordering, and its own worktree when concurrent.
- [ ] Every new behaviour had RED then GREEN evidence; migrations are monotonic and upgrade-tested.
- [ ] Parent re-read changed source and ran the focused suite per worker plus the combined suite.
- [ ] Full suite, smoke/build, and `git diff --check` pass; final diff reviewed.
- [ ] No required independent reviewer is still pending against the final stable source.
- [ ] No unrequested commit, push, deploy, or destructive action occurred; sessions/worktrees cleaned up.
- [ ] Remaining gaps are listed explicitly; no success claim rests only on worker summaries.
