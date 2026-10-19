# Local patches to Hermes (2026-10-19)

Local source fixes kept out of `hermes-agent`'s own commit history so a release
update does not silently drop them. Each patch is reversible and was verified to
reproduce the current file bytes.

## 1. `20261019-hermes-agent-checkpoint-malformed-nested-repo.patch`

Target: `hermes-agent` (release 0.22.2 checkout, detached HEAD).
Files: `tools/checkpoint_manager.py`, `tests/tools/test_checkpoint_malformed_nested_repo.py`.

Bug (from `logs/errors.log`, 10 occurrences on 2026-10-19):
`tools.checkpoint_manager: Git command failed: git add -A (rc=128) stderr=fatal:
'kyvault/.git' not recognized as a git repository`.
A work-tree directory whose `.git` is not a usable repository (here an empty
`.git/objects` left in `cache/scratch/kyvault`) makes git abort the whole stage,
so every snapshot of that project failed and `/rollback` kept only the last
pre-break state.

Fix: `_stage_all()` runs `git add -A`, recognises that specific git error, adds
the offending path as a literal exclude, retries (up to 4 broken paths), and
remembers the path per work tree for the rest of the process. Other git failures
keep the old behaviour (log, return not-ok).

Verify:

```
cd <HERMES_HOME>/hermes-agent
git apply -p1 <HERMES_HOME>/local-patches/20261019-hermes-agent-checkpoint-malformed-nested-repo.patch
./venv/Scripts/python.exe -m pytest tests/tools/test_checkpoint_malformed_nested_repo.py \
  tests/tools/test_checkpoint_manager.py tests/tools/test_checkpoint_gitlinks.py -q
```

Rollback: `git apply -R -p1 <same patch>` from the repo root.

## 2. `20261019-minir-store-shutdown-and-adviser-scope.patch`

Target: local memory provider `plugins/minir` (not a git repo).
Files: `adviser_mode.py`, `worker.py`, `__init__.py`.

Bug A (`adviser_mode.py`): the reviewer worker was a bare `threading.Thread`,
so it started with an empty contextvars scope. The adviser LLM call then read
`HERMES_CUSTOM_API_*` in an unscoped thread and failed with
`UnscopedSecretError: Hermes could not read this profile's ...`
(7 occurrences on 2026-10-19). Fixed by spawning through
`agent.memory_provider.spawn_context_thread`, the same path the prefetch and
layer worker already use.

Bug B (`worker.py`, `__init__.py`): `shutdown()` closed the SQLite store after a
bounded 5 s join. A layer job still inside an LLM call outlived the join and its
error handler called `store.fail_job()` on a closed connection, raising
`AttributeError: 'NoneType' object has no attribute 'execute'` and dumping an
unhandled thread traceback to `logs/tui_gateway_crash.log`. Fixed by making
`worker.stop()` / `adviser_mode.stop()` report whether the thread actually
stopped, and skipping `store.close()` when a job is still running (its row stays
`running`; `reclaim_open_jobs` re-queues it in the next process).

Verify (real probe used during the fix):

```
cd <HERMES_HOME>/hermes-agent
./venv/Scripts/python.exe -m py_compile ../plugins/minir/adviser_mode.py ../plugins/minir/worker.py ../plugins/minir/__init__.py
```

Behaviour checks performed:
- a thread spawned by `AdviserMode._ensure_thread` sees the caller's ContextVar
  (`profile=opsconfig`), a bare `threading.Thread` sees `""`;
- with a drain still running, `shutdown()` leaves the connection open and
  `fail_job()` succeeds; with the drain finished, the connection is closed.

Reapply after reinstalling the plugin:

```
cd <HERMES_HOME>/plugins/minir
git -c core.autocrlf=false apply -p1 -R <HERMES_HOME>/local-patches/20261019-minir-store-shutdown-and-adviser-scope.patch  # if needed to get originals
```

The patch was generated from the pre-change files and reproduced the current
files byte-for-byte, so it applies forward to a pristine copy of the plugin.

Backup of the fixed files: `backups/minir-<timestamp>-after-store-shutdown-fix/`.

## Not fixed (environment, not code)

- `pytest-asyncio` is not installed in `hermes-agent/venv`, so
  `tests/gateway/test_diff_command.py` fails with "async def functions are not
  natively supported" (pre-existing; 128 other checkpoint tests pass).
- `concurrent-log-handler unavailable ... pywintypes` — bundled Python has no
  `pywin32`; logging falls back, no data loss.
- `RateLimitError` (SiliconFlow TPM), `codex` binary not found, and MCP servers
  reporting zero connections are provider/tool-installation issues.
