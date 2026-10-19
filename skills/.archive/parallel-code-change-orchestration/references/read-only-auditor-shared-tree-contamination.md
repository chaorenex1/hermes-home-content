# Read-only auditor shared-tree contamination

Use this when a parent writer and one or more nominally read-only auditors share a checkout and files change unexpectedly.

## Prevention

1. Before dispatch, capture `git status --short`, the current commit, and the parent writer's allowed path set.
2. A prompt saying **read only** is not an OS permission boundary. Prefer an isolated worktree, a toolset without write tools, or run the audit before the writer starts.
3. Do not let a read-only audit become a delivery dependency while a shared-tree writer is still active.

## Detection signals

- New untracked files or tracked modifications outside the active writer's ledger.
- A file-read or patch tool reports that the file changed since the last read.
- Tests, file counts, or public schemas change without a recorded parent edit.
- Worker summaries and live repository state disagree.

These signals prove concurrent or unattributed mutation, not which actor caused it. Do not assign blame from timestamps or summaries alone.

## Bounded recovery

1. Pause parent writes immediately; do not keep patching around the moving tree.
2. Read each Worker/task's live terminal state and latest run. Wait only for active writers/auditors to become terminal; do not poll indefinitely.
3. Re-capture repository status and inventory every changed/untracked path.
4. Re-read full files before editing. A partial/paginated read is stale once any external-write warning appears.
5. Classify each delta:
   - parent-owned and ledgered;
   - worker-owned and intentionally handed off;
   - useful but unattributed candidate;
   - conflicting/unsafe;
   - generated artifact.
6. For useful candidate code, treat it as untrusted input: read it, map it to acceptance criteria, run its focused tests, and integrate deliberately. Do not accept it because a Worker says it passed.
7. Restore or delete only from a known baseline. Never discard an unattributed delta by guessing that it is temporary.
8. Once the tree is stable, resume with exactly one writer. Start fresh independent QA only after the writer emits a terminal evidence packet.

## Verification

- `git status --short` matches the integration ledger.
- Every retained file maps to an accepted requirement and owner.
- Focused tests for retained candidate code pass in the parent checkout.
- Combined and full suites pass after integration.
- No Worker/reviewer remains active when the parent publishes completion.

## Pitfalls

- Continuing parent edits while files are still changing creates stale-patch overwrites and mixed ownership.
- Treating a read-only prompt as enforcement hides the need for worktree/tool isolation.
- Treating late Worker summaries as proof confuses reported state with repository evidence.
- Re-running the same test does not establish provenance; inspect file state and task runtime first.
