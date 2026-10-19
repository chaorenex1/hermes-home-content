---
name: code-review-workflows
description: "Use for pre-commit, large-diff, or boundary code review."
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [code-review, pre-commit, security, large-diff, integration]
---

# Code Review Workflows

## Overview

Class-level guide for independent code review before commit or merge. Start with the ordinary pre-commit pipeline, then select the large-changeset or cross-boundary branch when risk shape demands it. No agent should be the sole verifier of its own implementation.

## Baseline Workflow

1. Bind the exact review target: repository, worktree, staged/unstaged state, base revision, and whether review is read-only or may auto-fix.
2. Inventory the diff and untracked files; split large output by file/risk class.
3. Scan added lines for secrets, injection, unsafe deserialization, dangerous evaluation, and path/auth boundary changes.
4. Run project-native tests, lint, and type checks; distinguish pre-existing baseline failures from new regressions.
5. Self-review scope, validation, error handling, debug leftovers, and tests.
6. Obtain a fresh independent review with a fail-closed structured verdict.
7. If repair is authorized, use a bounded fix/re-review loop; review-only tasks never mutate.
8. Verify the exact final staged candidate, report commands and limits, and commit/push only when explicitly authorized.

The original detailed pipeline is preserved at `references/pre-commit-code-review.md`.

## Large Changeset Branch

Use when the tree has roughly 50+ entries, thousands of lines, multiple architectural layers, or accumulated generated/untracked artifacts. Inventory by risk class: backup/cache artifacts, lock-file platform drift, security-sensitive runtime, new large executables, test deletions, and docs/config. Stage only the intended candidate, run cached whitespace/artifact checks, rescan after tests/builds, and independently review the final staged state. See `references/large-changeset-review.md` and its worked examples.

## Cross-Boundary Branch

Use when correctness crosses Host/plugin, middleware authority, dispatch, concurrency, registration, installers, or companion patches. Trace schema/registration through every dispatcher to final authorization and operation. Test valid, malformed, and absent authority; audit transactional rollback and deployment prerequisites; hash/recheck patch artifacts; and require public-caller integration tests. See `references/cross-boundary-code-review.md` and focused trust-boundary references. For browser-extension/native-messaging takeover stacks (MV3 worker + native host + local registry), also use `references/cross-boundary-extension-native-bridge-review.md` — it covers the two-authority desync pattern, authorization-token atomicity across awaits, and fire-and-forget signals over reconnectable ports.

## Response Shape Change Branch

When a handler's response shape changes (array to `{ items, mailDomain }`, a new nested field, a renamed column), grep every reader AND writer of that cache key before calling the change done. `setQueryData`, `prefetchQuery`, `fetchQuery`, and `onSuccess` merge callbacks typed against the old shape still compile, then silently write the old shape over the new payload: a list cache typed `Account[]` leaves `data.items` undefined and the pane empties after a reorder. Grep the query-key literal and the response type name. Merge only the fields a partial endpoint actually returns into the cached record; never overwrite a full record with a partial API row. Verify with one mutation that touches the cache (reorder, edit, delete), not with a page reload.

## Cleanup and Simplification Branch

Use when working code needs an explicit after-the-fact cleanup pass rather than correctness triage. Review the complete recent diff across four evidence-backed angles: reuse, code quality, efficiency, and implementation altitude. Require each finding to state concrete cost, confidence, and SAFE/CAREFUL/RISKY mutation risk; check history before removing apparently intentional boundaries. Apply SAFE items first, verify CAREFUL items incrementally, and report rather than auto-apply RISKY public-contract, concurrency, or architectural changes. See `references/simplify-code.md` for the full parallel-review prompts and aggregation procedure.

## Finding Contract

Order findings by severity. Include exact `path:line`, reachable failure/exploit path, coverage gap, smallest safe remediation, commands actually run, exit codes, and unresolved limits. Do not overstate focused green tests as whole-suite health.

## Verification Checklist

- [ ] Exact worktree/revision and candidate state fixed.
- [ ] Untracked files and generated artifacts included.
- [ ] Security/boundary-sensitive paths traced end to end.
- [ ] Baseline versus new failures distinguished.
- [ ] Independent final-state review completed.
- [ ] Review-only scope remained non-mutating when requested.
- [ ] No unrequested commit, push, or deployment occurred.
