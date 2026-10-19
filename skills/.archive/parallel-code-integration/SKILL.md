---
name: parallel-code-integration
description: Safely integrate parallel delegated code changes in one shared repository with evidence-based worker status and final regression gates.
version: 1.0.0
author: Masia
created_by: agent
---

# Parallel Code Integration

Use for multi-file implementation work split across delegated coding agents that may share a checkout or produce overlapping migrations, contracts, and tests.

## Partition before dispatch

1. Map each requested change to owned production files, tests, and migrations.
2. Run only agents with disjoint write sets concurrently.
3. Serialize changes that touch a shared schema, migration chain, public interface, or fixture contract.
4. Give every worker a strict TDD contract: focused RED command, minimal implementation, focused GREEN suite, no commit.
5. Require each worker to return changed paths, migration compatibility notes, and exact test output.

## Integrate every completion

1. Treat a worker summary as unverified until source and tests are checked in the parent session.
2. Re-read every changed file before editing it or accepting its claims.
3. Run the combined focused suites across every changed boundary, not just each worker's isolated tests.
4. If a public schema, CLI output, tool list, or required argument changes, update all exact-contract tests, smoke scripts, and callers in the same integration step.
5. Trace full-suite failures to the contract-changing worker; do not label a deterministic integration regression as unrelated merely because its test file was outside that worker's nominal scope.
6. Use smoke tests to catch installed-copy / runtime call-site drift that unit tests miss.

## Worker status reporting

- Report a worker as **running** only when the delegation runtime has supplied a current running/completion event in this conversation.
- Do not infer live delegation status from uncommitted files or a prior dispatch acknowledgement.
- If no current status event exists, state that the last known state is unavailable; verify repository state separately.

## Final gate

Before declaring the group complete, run once after all integration fixes:

```text
<focused cross-boundary tests>
python -m pytest -q
<disposable smoke script>
<package build>
git diff --check
```

Report all actual pass/fail counts. Keep untracked user artifacts untouched and never commit unless asked.

## Pitfalls

- Shared schema migrations are not safe to parallelize in one checkout.
- A stricter runtime API often breaks smoke scripts and exact JSON/tool-set assertions; update those callers deliberately.
- A test that mocks an obsolete bridge can become invalid after a design moves to a direct persisted controller; replace it with an assertion for the new boundary rather than preserving obsolete behavior.
