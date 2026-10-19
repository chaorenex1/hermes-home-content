# Hermes standalone user-plugin deployment reference

This is a concise, reusable operational example for a source checkout deployed to Hermes's user-plugin directory on Windows.

## Paths

- Source checkout: `C:/Users/<user>/projects/<plugin>`
- Installed user plugin: `C:/Users/<user>/AppData/Local/hermes/plugins/<plugin-name>`
- Controller database (when the plugin owns one): `C:/Users/<user>/AppData/Local/hermes/<controller>.db`
- Backup root: `C:/Users/<user>/AppData/Local/hermes/backups/plugins`

Use forward slashes in shell arguments. The terminal is Git Bash/MSYS, not PowerShell.

## Preflight

```bash
hermes plugins list --plain --no-bundled
python -m pytest tests/test_deploy_plugin.py -q
python -m pytest -q
python scripts/deploy_plugin.py \
  --source . \
  --target 'C:/Users/<user>/AppData/Local/hermes/plugins/<plugin-name>' \
  --controller-db 'C:/Users/<user>/AppData/Local/hermes/<controller>.db' \
  --backup-root 'C:/Users/<user>/AppData/Local/hermes/backups/plugins' \
  --dry-run
```

Dry-run output should contain the expected plugin name, source/installed manifest SHA-256 values, a comparison result, and `dry run: no files changed`.

## Live deployment sequence

```bash
hermes gateway stop
hermes gateway status

python scripts/deploy_plugin.py \
  --source . \
  --target 'C:/Users/<user>/AppData/Local/hermes/plugins/<plugin-name>' \
  --controller-db 'C:/Users/<user>/AppData/Local/hermes/<controller>.db' \
  --backup-root 'C:/Users/<user>/AppData/Local/hermes/backups/plugins'

hermes plugins enable <plugin-name>
hermes gateway start
hermes gateway status
hermes plugins list --plain --no-bundled
```

## Release provenance

When the request bundles commit, push, and deploy, publish first and install the committed tree:

```bash
git status --porcelain        # must be empty: never install from a dirty worktree
git add <paths> && git commit -F <message-file>   # or one -m per paragraph
git push origin <branch>
git ls-remote origin refs/heads/<branch>   # must equal: git rev-parse HEAD
```

Compose the message with `-F` or repeated `-m` flags. A heredoc carrying backslashes or quotes is
folded by MSYS and lands mangled in the commit body.

Only then run the replacement sequence, and report the commit hash next to the backup path and the
new PID. The installed plugin tree is not a git repository, so nothing else records which revision is
live; an unpushed deployment cannot be rebuilt from the remote or audited later.

If `hermes plugins enable` offers an optional permission to replace built-in tools, do not grant it merely to refresh an already enabled plugin. It is a separate privileged capability; grant it only when the user explicitly requests built-in tool replacement.

## Enable auto-reloads a running Gateway

`hermes plugins enable <key>` soft-reloads plugins in a running Gateway by itself — its output reports `Gateway reloaded plugins — deferred: tools (next session)`. When the stop/start pair exists only to make the Gateway load a plugin that was NOT previously loaded (fresh install, re-enable, or a plugin whose tools/skills were absent), enable alone is sufficient: no stop/start is required, and the tool/skill surfaces land in the next session. Keep the stop/start cycle for replacing the code of an already-loaded plugin (see `runtime-source-coherence.md`) and whenever a clean process is otherwise required.

Prove the live load from the Gateway's own log instead of assuming it:

```bash
hermes plugins list --plain | grep -i <plugin-key>
grep -i "<plugin-key>" "$HERMES_HOME/logs/agent.log" | tail
```

For a harness-style plugin, expect `Loading plugin '<key>'`, `registered web provider: <name>`,
`registered tool: …`, `registered skill: …` lines alongside `enabled` in the plugin list — that is
live-host evidence, distinct from the copy digests of the preflight.

An **exclusive** plugin (a memory provider whose manifest declares `kind: exclusive`) never logs
`Loading plugin` at Gateway boot. The log shows `detected exclusive, treating as kind='exclusive'`
and `Skipping '<key>' (exclusive, handled by category discovery)` because the provider is built per
session from `memory.provider`. Those lines are a healthy discovery pass, not a load failure; do not
conclude the deploy failed because the expected load line is absent. Prove the deployed bytes by
importing the installed package with the host venv and asserting the changed symbol, then exercise
it in one fresh session:

```bash
cd /c/Users/<user>/AppData/Local/hermes/plugins
python -c "import <pkg>.<changed_module> as m; assert hasattr(m, '<new_symbol>'); print(m.__file__)"
hermes plugins doctor <installed-dir>   # imports and registers the real package
```

After `hermes gateway restart`, a `still accepting connections — new api_server may fail to bind`
warning means the old process has not released the health port yet, not that the restart failed.
Confirm the listener belongs to the new PID and that the host logged a fresh bind:

```bash
hermes gateway status                    # new PID
netstat -ano | grep 8642                 # LISTENING line must end in that PID
grep "API server listening" "$HERMES_HOME/logs/agent.log" | tail -1
```

## Restarting from a gateway-hosted Hermes session

A terminal tool launched by the running Hermes Gateway is inside the process tree it would be stopping. `hermes gateway stop` or `hermes gateway restart` may therefore refuse with a message that the command would kill itself before completion. Treat this as a safety guard, not a transient command failure: do not retry the same command in that terminal and do not obfuscate it to evade the guard.

Use an independent operator shell. On Windows, a foreground user can open Windows Terminal manually. For an automated Desktop deployment, create a short `%TEMP%` `.cmd`, launch it in a separate Windows Terminal process, and clear the inherited gateway-context marker only inside that independent shell:

```bat
@echo off
set "_HERMES_GATEWAY="
set "RESULT=%TEMP%\hermes_gateway_restart_result.txt"
hermes gateway restart > "%RESULT%" 2>&1
del "%~f0"
```

Launch the helper from Git Bash without keeping it in the Gateway-owned terminal:

```bash
cmd.exe /c start "" wt.exe -w new cmd.exe /c "C:\\path\\to\\restart_gateway.cmd"
```

After the Desktop reconnects, read the captured result, run `hermes gateway status` independently, and delete the result file. If no genuinely external control shell is available, stop and ask the user to restart the Gateway rather than bypassing the guard.

## Dependent post-restart provider checks

Do not parallelize host/provider status initialization with provider integrity verification. Some providers rebuild file metadata during status or startup; a concurrent verifier can race that reconciliation and return a transient mismatch. Sequence them:

1. `hermes memory status` (or the provider's status command) and require installed/available/active state.
2. Run the provider's integrity verification only after status completes.
3. If the first verification fails and status just reconciled derived metadata, retry verification once; this is a changed-state retry, not an identical retry.

## Manual replacement when the repository ships no deploy script

The swap primitives still apply; only the tooling is missing.

```bash
# Backup with MSYS paths: native tar reads "C:..." as a remote host and fails.
tar -czf /c/Users/<user>/AppData/Local/hermes/cache/scratch/<plugin>-backup-$(date +%Y%m%d-%H%M%S).tgz \
  -C /c/Users/<user>/AppData/Local/hermes/plugins <plugin-name>

hermes gateway stop
rm -rf /c/Users/<user>/AppData/Local/hermes/plugins/<plugin-name>
cp -r /c/Users/<user>/projects/<repo>/plugin/<plugin-name> \
      /c/Users/<user>/AppData/Local/hermes/plugins/<plugin-name>
rm -rf /c/Users/<user>/AppData/Local/hermes/plugins/<plugin-name>/__pycache__ \
       /c/Users/<user>/AppData/Local/hermes/plugins/<plugin-name>/.pytest_cache

diff -rq --exclude=__pycache__ /c/Users/<user>/projects/<repo>/plugin/<plugin-name> \
  /c/Users/<user>/AppData/Local/hermes/plugins/<plugin-name> && echo IDENTICAL

hermes gateway start
```

Hash the tree with an explicit MSYS path, not `$LOCALAPPDATA`:

```bash
INST=/c/Users/<user>/AppData/Local/hermes/plugins/<name>
for f in plugin/<name>/*.py plugin/<name>/plugin.yaml; do
  rel=${f#plugin/<name>/}
  [ "$(sha256sum "$f" | cut -d' ' -f1)" = "$(sha256sum "$INST/$rel" | cut -d' ' -f1)" ] || echo "DIFF $rel"
done
```

`$LOCALAPPDATA` expands with backslashes (`C:\Users\...`); a native `sha256sum` handed
`...\Local/hermes/...` fails to open the file, yields an empty digest, and makes every file look
different. When a whole tree reports "all files differ" while
`diff -rq --exclude=__pycache__` says identical, suspect the path expansion before believing a mass
divergence. Never hide the hash command's stderr, which is the only signal that it never read the
target.

If `rm -rf` or `mv` of the installed directory fails with `Device or resource busy` (Windows), a live
host process that imported the plugin still holds the directory — `hermes gateway stop` does not
release a running CLI or Desktop backend. Do not delete the only copy to force it: copy the new files
over the existing directory in place (`cp -R <repo>/plugin/<name>/. <target>/`), remove
`__pycache__`, and verify with `diff -rq --exclude=__pycache__`. Python closes `.py` files after
import, so overwriting is safe; only the directory rename is blocked, and the restart (or the next
CLI start) makes the new bytes effective.

`hermes plugins validate` takes a directory path; a bare plugin name fails with `is not a directory`.
Pass the installed directory and require the closing `Validation passed.` Private-seam warnings are
pre-existing policy notes, not failures.

## Stale gateway trees survive a service stop

`hermes gateway stop` drains the service it knows about, but an older `gateway run` process tree can
stay alive for days, holding a port and executing the code the deployment just replaced. Enumerate
and explain every serve process; terminate the stale ones from an independent shell:

```bash
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { \$_.CommandLine -like '*gateway run*' } | ForEach-Object { '{0} | {1} | {2}' -f \$_.ProcessId, \$_.CreationDate, \$_.ParentProcessId }"
netstat -ano | grep LISTENING | grep -E " (<pid-a>|<pid-b>)$"
```

Any PID whose start time predates the deployment and still listens is stale residue, not the new
host. Kill it with PowerShell (`Stop-Process -Id <pid> -Force`); in Git Bash `taskkill //PID` is
rejected because MSYS rewrites the switches. Then re-check that one gateway PID remains and its
health port answers.

## Fresh-session acceptance probe

Digest equality and `enabled` status prove what was copied, not what the host serves. Finish with one
throwaway session that exercises both new surfaces in a single answer:

```bash
hermes chat -q "Call <provider-tool> once. Then quote verbatim the heading lines that follow the '<Provider block heading>' line in your system prompt."
```

A wrong tool name fails the call; unchanged prompt text shows up as the old headings. Record the
tool's real output and the headings verbatim in the deployment report.

## Host verification scripts

A repository's own host probe is the strongest single acceptance check, but its exit code is not the
gate. Run it with explicit host paths when autodetect fails, and require its success marker:

```bash
python scripts/verify_against_host.py \
  --host-python C:/Users/<user>/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe \
  --workspace  C:/Users/<user>/AppData/Local/hermes/hermes-agent
```

An autodetect miss can print `Could not locate the Hermes install` and still exit 0, so a zero status
proves only that the script started. Quote the `PASS` line and its result JSON in the report; treat a
missing marker as a failed deployment check regardless of the exit code.

## Post-deploy verification checklist

- Source and installed `plugin.yaml` hashes match.
- Backup directory contains the prior `plugin/` tree.
- Backup controller database exists and `PRAGMA integrity_check` returns `ok`.
- Installed tree does not contain `.pytest_cache`, `.pytest-cache`, or `__pycache__`.
- The plugin list reports `enabled` for the expected user plugin/version.
- Gateway status reports a running process after restart.
- Exactly one gateway PID remains after the restart, and its health port answers.
- A fresh-session probe produced one real provider-tool result and the new prompt headings.

## Deployment-tool test coverage

The deployment utility should be self-contained and test:

1. dry run is non-mutating;
2. target swap copies plugin files but excludes VCS/test/bytecode artifacts;
3. the previous plugin and SQLite controller database are saved in the backup;
4. a simulated post-swap manifest mismatch rolls back to the prior installed plugin and clears temporary stage/rollback directories.
