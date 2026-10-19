# Kanban Persistence Conflict Semantics (Session 8c585c52cc)

Session-specific three-way conflict semantics captured during a delegated Ultrawork CODER pass. Use as a concrete example when reconciling Kanban persistence conflicts; do not treat the line numbers as durable.

## Stage map (rebase 8c585c52cc onto 91937a6dc3)

- Base (stage 1): 9824-line `hermes_cli/kanban_db.py`, 4788-line `tests/hermes_cli/test_kanban_core_functionality.py`, 4972-line `tests/hermes_cli/test_kanban_db.py`.
- Ours (stage 2, upstream): 10311-line `kanban_db.py` (+556/-69), heavily refactored tests (+95/-3473 in core_functionality, +235/-3622 in kanban_db). Upstream kept `test_worktree_workspace_explicit_target_materializes_linked_worktree` in `test_kanban_db.py` but deleted the other worktree tests and `test_reap_worker_zombies_noop_on_windows`.
- Theirs (stage 3, local native-swarm commit): 9926-line `kanban_db.py` (+210), conservative tests (+8/-6, +23/-8). Adds `_listed_worktree_paths` helper, Windows path normalization, and updates `test_reap_worker_zombies_noop_on_windows` to expect `os.waitpid` called once with `(0, 0)`.

## Semantic hunks in kanban_db.py (theirs vs base)

1. `remove_board`: add `_retry_fs` helper that retries PermissionError up to 10× with `gc.collect()` + 0.1s sleep; wrap `d.rename(target)` and `shutil.rmtree(d)`. Windows file-lock resilience.
2. `recompute_ready`: after promotion loop, reconcile the single shared-runtime outbox via `from hermes_cli.ultrawork_kanban import advance_post_commit_events` (guarded try/except with `_log.warning`). Keeps deferred post-commit events recoverable without a per-swarm scheduler.
3. `complete_task`: after the write txn, enqueue `event_kind="completed"` payload `{"summary": ...}` via `enqueue_post_commit_event` then `advance_post_commit_events`. Durable post-commit reconciliation keeps route transitions out of the Kanban transaction.
4. `block_task`: refactor so the `kind == "dependency"` fast path exits early, and the truly-blocked path (with recurrence counter) runs after. Both paths enqueue `event_kind="blocked"` payload `{"reason": ..., "kind": ...}` post-commit. The dependency path now fires `kanban_task_blocked` outside the write txn.
5. `_classify_worker_exit`: when `os.WIFEXITED` is unavailable (Windows), decode a raw wait-status shape: `raw_code >= 256 and raw_code % 256 == 0` → `>>= 8`; then `0` → `clean_exit`, `KANBAN_RATE_LIMIT_EXIT_CODE` → `rate_limited`, `>0` → `nonzero_exit`, else `unknown`.
6. `reap_worker_zombies`: guard on `not hasattr(os, "waitpid")` instead of `os.name != "nt"`; use `getattr(os, "WNOHANG", 1)`. This makes the function call `waitpid` on Windows when available, matching the updated test.
7. `_terminate_reclaimed_worker`: on `OSError`, check `if not _pid_alive(pid): info["terminated"] = True` before returning. Prevents a zombie from being reported alive when the terminate syscall raced.
8. `_path_search_names`: prepend the bare `command` to the PATHEXT list (`return [command, *(command + ext for ext in exts)]`). Fixes `shutil.which` on Windows when the caller already passed `hermes.exe`.
9. `_resolve_hermes_argv`: use `shutil.which("hermes")` unconditionally, then if `_IS_WINDOWS and _resolved_from_cwd(hermes_bin)` fall back to `_safe_which_no_cwd("hermes")`. Avoids picking up a cwd-local `hermes` shim.
10. New helper `_resolved_from_cwd(path)` compares `Path(path).expanduser().resolve(strict=False).parent == Path.cwd().resolve(strict=False)`.

## Test semantics (theirs vs base)

- `test_kanban_db.py`: adds `_listed_worktree_paths(listed)` helper that parses `git worktree list` lines, strips `worktree ` prefix, resolves paths, and returns a `set[str]`. All four worktree tests switch from substring membership (`f"worktree {expected}" in listed`) to exact resolved-path membership (`str(expected.resolve(strict=False)) in _listed_worktree_paths(listed)`), with rerun test using `sum(1 for path in listed_paths if path == expected_resolved) == 1` and asserting the `.worktrees/{tid}` subpath is absent.
- `test_kanban_db.py`: `test_reap_worker_zombies_noop_on_windows` docstring changes from "never calls os.waitpid" to "harmless on Windows when no zombies exist"; patches `os.waitpid` with `return_value=(0, 0)` and asserts `assert_called_once()` instead of `assert_not_called()`. This matches the `hasattr(os, "waitpid")` refactor.
- `test_kanban_core_functionality.py`: `test_list_profiles_on_disk` uses `hermes_constants.get_default_hermes_root()` and sets `LOCALAPPDATA` to a tmp path instead of assuming `~/.hermes/profiles`. `test_gateway_dispatcher_retries_corrupt_board_after_quarantine` relaxes exact-count assertions to `>= 1` so the dispatcher keeps ticking while quarantined.

## Migration hazards

- The `block_task` refactor moves `_fire_kanban_lifecycle_hook` for the dependency path outside the `write_txn`. Any downstream hook that assumed it ran inside the transaction will now see committed state; verify hook idempotence.
- `complete_task` and `block_task` now write to the ultrawork post-commit queue. Replays must be deduplicated by `(task_id, event_kind, payload_hash)` or equivalent; otherwise a retried completion creates duplicate QA/Judge cards.
- `_resolve_hermes_argv` now prefers `shutil.which` even on Windows, then filters cwd-local results. Environments that relied on `_safe_which_no_cwd` for PATH hygiene may see different resolution order.
- `reap_worker_zombies` no longer short-circuits on `os.name == "nt"`. On Windows Python builds that expose `os.waitpid` (e.g. Cygwin/MSYS2), it will now reap; the test expectation must be updated in sync.

## Merge recipe (upstream-first + overlay)

1. Take ours (upstream) as the base for all three files.
2. Overlay theirs' semantic hunks onto the corresponding functions in the upstream file. Upstream refactored tests heavily; only `test_worktree_workspace_explicit_target_materializes_linked_worktree` still exists in ours, so only that test needs the `_listed_worktree_paths` + resolved-path assertion overlay. The other worktree tests and `test_reap_worker_zombies_noop_on_windows` were deleted upstream; re-adding them is a product decision, not a conflict resolution.
3. For `test_kanban_core_functionality.py`, apply theirs' two relaxed assertions (`>= 1` for quarantine retries) and the `get_default_hermes_root` + `LOCALAPPDATA` profile test if the corresponding tests still exist in the upstream-slimmed file; otherwise skip.
4. After overlay, run the surviving focused tests plus a smoke import of `hermes_cli.kanban_db` to catch syntax/indentation drift from the large upstream refactor.
