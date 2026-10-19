# Shared Ultrawork Kanban Runtime Delivery

Use when evolving a Core `ultrawork_kanban` runtime plus a local controller plugin.

## Core lifecycle contract

- Persist child attempts separately with unique `(run_id, route_key, child_key, attempt, phase)` identity; route-attempt identity cannot represent sibling child work.
- Route Judge pass with materialized children must transition the parent to `awaiting_children`, not `accepted`.
- Child completion flow is Dev → independent QA → auxiliary Judge. Persist child Dev/QA reports and Judge decision before each state transition.
- Child acceptance dispatches all newly dependency-ready siblings in one controller turn. Only when every child is accepted may the parent handoff be written and successors dispatched.
- A child block must block the parent route and run with the exact persisted reason.

## Global acceptance

- Global Judge is a second auxiliary-Judge invocation, not a self-reported Global QA verdict.
- Its packet must include frozen input identity, all route Dev/QA evidence, accepted handoffs/Judge decisions, global-QA evidence, and candidate artifact/commit facts when applicable.
- Persist the packet and Judge decision before synthesis. Fail closed on unavailable/malformed/uncited verdicts.

## Worktree lifecycle

- Register every route worktree at creation with run/route/attempt, branch, frozen base SHA, and cleanup state.
- Before integration: require a clean candidate worktree, readable candidate SHA, frozen-base ancestry, and explicit current-base policy. Block on drift or merge conflict; never silently rebase/reset.
- Terminal cleanup is CAS-claimed and limited to registered clean worktrees. Quarantine dirty/missing/unreadable trees and preserve branches.

## Plugin source and deployment

1. Keep an editable Git source repository separate from installed plugin copies.
2. Run source tests with the intended Core checkout on `PYTHONPATH`.
3. Commit the tested source and advance the manifest version before deployment.
4. Stop the Gateway, make a timestamped backup, then deploy the source tree (exclude `.git` and caches) to default plus every configured controller/Dev/QA profile copy.
5. Compare a deterministic source-vs-installed tree digest, restart once, then verify enabled manifest version, Gateway PID/status, and an installed-copy import/test.
6. Legacy migration is explicit and terminal-only: open old state read-only, refuse any active/mutating state before backup or Core writes, write an idempotency ledger, and retain both original DB and pre-migration backup.

## Verification minimum

- Focused child/event/global runtime tests.
- Worktree integration/drift/conflict/cleanup tests.
- Plugin migration fixture plus complete plugin suite.
- Desktop launcher/route tests and TUI `slash.exec → command.dispatch` test.
- Gateway/plugin status after restart.
