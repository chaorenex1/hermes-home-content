# Windows-Specific Quirks

Hermes runs natively on Windows (PowerShell, cmd, Windows Terminal, git-bash
mintty, VS Code integrated terminal). Most of it just works, but a handful
of differences between Win32 and POSIX have bitten us — document new ones
here as you hit them so the next person (or the next session) doesn't
rediscover them from scratch.

### Input / Keybindings

**Alt+Enter doesn't insert a newline** — Windows Terminal (and mintty) grab it
for fullscreen before prompt_toolkit sees it. Use **Ctrl+Enter** instead (the
CLI binds it to newline on Windows; raw Ctrl+J does the same, harmlessly).
To inspect how your terminal reports a keystroke, run
`python scripts/keystroke_diagnostic.py` from the repo root.

### Config / Files

**HTTP 400 "No models provided" on first run** — `config.yaml` was saved with
a UTF-8 BOM (Notepad does this). Re-save as UTF-8 without BOM;
`hermes config edit` writes correctly.

### `execute_code` / Sandbox

**WinError 10106** from the sandbox child process — it can't create an
`AF_INET` socket. Root cause is usually Hermes's env scrubber dropping
`SYSTEMROOT`/`WINDIR`/`COMSPEC` (Python's `socket` needs `SYSTEMROOT` to find
`mswsock.dll`), not a broken Winsock LSP. The `_WINDOWS_ESSENTIAL_ENV_VARS`
allowlist in `tools/code_execution_tool.py` covers it; if you still hit it,
echo `os.environ` inside an `execute_code` block to confirm `SYSTEMROOT` is set.

### Testing on Windows

`scripts/run_tests.sh` is POSIX-only (expects `.venv/bin/activate`); the
Hermes-installed `venv/Scripts/` has no pip/pytest (stripped for size).
Run directly with `-n 0` (`pyproject.toml`'s `addopts` already sets
`-n`). Prefer a pytest-capable project/shared-checkout interpreter instead of
a hard-coded system-Python path; installer locations vary by host and version:

```bash
# From the worktree root, probe the current/shared checkout first.
for py in .venv/Scripts/python.exe venv/Scripts/python.exe \
  "$HERMES_HOME/hermes-agent/.venv/Scripts/python.exe" \
  "$HERMES_HOME/hermes-agent/venv/Scripts/python.exe"; do
  if [ -x "$py" ] && "$py" -m pytest --version >/dev/null 2>&1; then
    PYTEST_PY="$py"; break
  fi
done

test -n "$PYTEST_PY" || {
  echo "No pytest-capable Hermes interpreter found" >&2
  exit 1
}
export PYTHONPATH="$(pwd)"
if "$PYTEST_PY" -c 'import xdist' >/dev/null 2>&1; then
  "$PYTEST_PY" -m pytest tests/foo/test_bar.py -v --tb=short -n 0
else
  # pyproject.toml may include an xdist -n addopt even when this interpreter
  # does not have pytest-xdist. Clear project addopts and run serially.
  "$PYTEST_PY" -m pytest -o addopts='' tests/foo/test_bar.py -v --tb=short
fi
```

Only install pytest/pytest-xdist into a system Python when no project/shared
interpreter is available.

Test fixtures that delete a nested git repo need the repo's own helper —
`from utils import rmtree_readonly` — because `shutil.rmtree` stops with WinError 5 on the
read-only `.git/objects` files. Build the fixture on that helper instead of retrying with
`onerror`/`onexc` permission hacks.

(POSIX-only tests need skip guards — see the cross-platform guard list in
`references/contributor-guide.md`.)

### git in the persistent bash session

The `terminal` tool keeps its shell and exported variables across calls, so git state leaks between
unrelated commands:

- **Never `export GIT_DIR` / `GIT_WORK_TREE` / `GIT_INDEX_FILE`.** They persist: a later `git status`
  in an unrelated directory silently reports that shadow store (a checkpoint index makes the repo
  look like it contains someone else's files). Pass them per command
  (`GIT_DIR=... GIT_WORK_TREE=... git add -A`) and `unset` them the moment you are done.
- **Native git does not read MSYS paths.** Path translation is disabled for the terminal on this
  host, so `GIT_DIR=/c/Users/...` fails with `fatal: not a git repository: '/c/Users/...'` even
  though the directory exists. Use `C:/Users/...` forward-slash native paths for every path handed
  to git (bash accepts them too).
- **`git apply` obeys `core.autocrlf`**, which defaults to `true` under Git for Windows. Applying a
  patch can then rewrite every line ending, and a byte comparison against the live file fails for no
  real reason. Verify patch fidelity with `git -c core.autocrlf=false apply -p1 <patch>` and compare
  bytes; generate the patch as a real diff rather than by hand.
- **Do not `git stash` or rewrite the live hermes-agent checkout** to get a baseline — the terminal
  guard blocks it. Compare against a clone instead: `git clone --shared <checkout> <scratch>/baseline`
  and run the same tests there; identical failures prove the problem pre-dates the edit.

### Path / Filesystem

**Line endings.** Git may warn `LF will be replaced by CRLF`. Cosmetic — the
repo's `.gitattributes` normalizes. Don't let editors auto-convert committed
POSIX-newline files to CRLF.

**Editing a CRLF file with `patch`.** Single-line replacements apply, but a
multi-line `old_string` copied from a `read_file` view can fail as
`Could not find a match` — the view shows `\n`, the bytes carry `\r\n`. After one
failed retry on the same region, stop re-patching and do an exact replace in
`execute_code`: read with `open(path, encoding="utf-8", newline="")`, match
against `raw.replace("\r\n", "\n")`, then write the result back with its `\n`
turned into `\r\n` under `newline=""` so the file keeps its original endings.
Verify with the project's typecheck or build, not by re-reading the diff.

**`write_file` refuses on a stale or partial read.** Re-read the file to
completion once in the same turn, then retry. If it still refuses, use `patch`
for targeted edits or an exact replace in `execute_code`; do not loop on writes.

**Forward slashes work almost everywhere.** `C:/Users/...` is accepted by
every Hermes tool and most Windows APIs. Prefer forward slashes in code
and logs — avoids shell-escaping backslashes in bash.

