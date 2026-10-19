---
name: python-resource-lifecycle
description: "Use when Python resources outlive scope or lock files."
version: 1.0.0
author: Masía
metadata:
  hermes:
    tags: [python, resource-lifecycle, sqlite, windows, debugging, testing]
---

# Python Resource Lifecycle

Use this skill when Python code appears functionally correct but leaves files, sockets, subprocesses, database handles, temporary directories, or other OS resources alive beyond the intended scope. It is especially useful for Windows-only cleanup failures, where open handles prevent deletion and expose lifecycle bugs that Unix often masks.

## Core principle

Separate **transaction scope** from **resource lifetime**. A context manager may commit, roll back, flush, or restore state without closing the underlying resource. Verify the concrete object's `__exit__` contract instead of assuming `with resource_factory()` owns cleanup.

## Workflow

1. **Build a lock-sensitive reproduction.**
   - Exercise the smallest real path that acquires the resource.
   - Force cleanup before process exit while the owning application object is still alive.
   - For filesystem-backed resources, use `TemporaryDirectory` so leaving the block attempts immediate deletion.
   - Assert useful behavior inside the block; a cleanup exception after successful output is still a failing lifecycle test.

2. **Identify ownership and semantics.**
   - Trace every factory call that can create the resource (`sqlite3.connect`, `open`, `Popen`, client/session constructors, archive readers, etc.).
   - Determine whether the returned context manager closes the object or merely manages a transaction/state boundary.
   - Check wrappers and helper context managers before changing callers; prefer fixing the shared ownership boundary when one exists.

3. **Write the regression test first.**
   - Keep the test specific to externally observable cleanup, not internal calls to `.close()`.
   - Run it red and confirm the failure is the actual lock/cleanup error, not an unrelated setup problem.
   - Avoid `gc.collect()`, sleeps, retries, or `ignore_cleanup_errors`; they hide the ownership defect.

4. **Make closure explicit.**
   - Use a project-owned context manager with a `finally: resource.close()` block, `contextlib.closing`, or `ExitStack` when several resources must unwind together.
   - Preserve a separate transaction context when needed. For SQLite, explicit lifetime plus transaction scope can be expressed as:

     ```python
     from contextlib import closing

     with closing(sqlite3.connect(path)) as connection, connection:
         connection.execute(...)
     ```

   - Apply the fix to every acquisition path in the affected class/module that shares the same ownership contract; do not leave read-only paths leaking while fixing only writes.

5. **Check name collisions introduced by the fix.**
   - Before importing helpers such as `closing`, `open`, or `lock`, search the enclosing module for local variables with the same name.
   - Rename semantic data variables (`closing_tag`, `closing_text`) rather than aliasing lifecycle helpers obscurely.
   - Run all behavior paths that reach each edited acquisition site, not only the new cleanup test.

6. **Verify in widening rings.**
   - New cleanup regression.
   - Related behavior tests, including read and write paths.
   - Syntax/type/lint checks.
   - Full test suite once.
   - Diff hygiene (`git diff --check`) and confirmation that no unrelated resource policy was broadened.

## Diagnostic distinctions

- **Business operation succeeds, cleanup fails:** treat it as a real lifecycle defect, not a harmless test artifact.
- **Deletion works only after process exit or GC:** ownership is nondeterministic and still defective.
- **Only Windows fails:** open-handle semantics are providing a stronger signal; do not weaken the test for portability.
- **SQLite close-time checkpoint fails while integrity remains clean:** inventory every process holding the database before blaming the disk. Explicit connection closure does not mean the database is quiescent across processes. If gateway, dashboard, CLI, or workers share a WAL database, avoid `wal_checkpoint(TRUNCATE)` in automatic close paths; prefer `PASSIVE` and reserve exclusive maintenance for a deliberately quiesced database.
- **A wrapper transforms inputs before the failing subsystem sees them:** inspect the transformed boundary value separately from the application code. Do not patch repository logic when the defect is in the caller/tool wrapper.

## Pitfalls

- Assuming every `with` statement closes its object.
- Calling `.close()` only on the happy path instead of using structured unwinding.
- Fixing one occurrence while sibling acquisition paths retain the same leak.
- Replacing explicit closure with garbage collection, retry loops, delayed deletion, or permissive cleanup flags.
- Importing `closing` into a module that already uses `closing` as a string or sentinel variable.
- Declaring a repository defect from a malformed command/tool input before reproducing the intended input directly.

## Completion evidence

Completion requires a red-to-green cleanup regression and the relevant full-suite result. Report the resource whose lifetime was wrong, the ownership boundary changed, and any tool-layer issue that remains outside the repository.

For a concrete Windows SQLite reproduction and the name-shadowing failure mode, see [references/windows-sqlite-temp-cleanup.md](references/windows-sqlite-temp-cleanup.md).
