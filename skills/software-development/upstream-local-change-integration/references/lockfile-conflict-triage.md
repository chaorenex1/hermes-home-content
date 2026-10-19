# Lockfile Conflict Triage During Rebase

When `package-lock.json` (or any generated lockfile) conflicts while replaying a local commit onto upstream, resolve it by blob evidence, not by reading hunks. Lockfiles are generated artifacts — the correct resolution is almost always "take the side whose manifest is authoritative and regenerate."

## Decision procedure (read-only, works in a paused rebase)

1. List stages: `git ls-files -u package-lock.json`
   - stage 1 = merge base, stage 2 = ours (upstream side during rebase), stage 3 = theirs (replayed local commit).
2. Compare blob hashes to identify which stage matches the live upstream tip:
   - `git rev-parse origin/main:package-lock.json` and compare with the stage-2 blob hash from `ls-files -u`. If they match, stage 2 IS the current upstream lockfile.
   - Verify `git show <local-commit>:package-lock.json | sha1sum` equals the stage-3 blob — confirms stage 3 is exactly the local commit's result.
3. Check the manifest: `git ls-files -u package.json` (empty = no conflict) and `git diff 494659b7e^ origin/main -- package.json`.
   - If upstream's package.json **removed or moved the dependency blocks** the local lockfile hunks concern, the local lockfile change is a stale regeneration artifact of the old manifest. Take `--ours` (stage 2) and regenerate if needed.
   - If the local commit changed package.json dependencies, its lockfile may carry real intent — but still prefer regenerating from the merged manifest rather than hand-merging hunks.
4. Classify the local lockfile diff: `git show <commit> -- package-lock.json | grep -c '^-'` vs `'^+'`. A **deletion-only** diff (pruning optional/peer subtrees, e.g. `@electron/windows-sign`, nested `fs-extra`) is almost always environment-noise from `npm install` on a different platform/registry, not intent.
5. Confirm no conflict markers remain after checkout: `grep -c '^<<<<<<<' package-lock.json`.

## Evidence to report

- Stage blob hashes and their relationship to `origin/main` blobs (proves "ours == upstream tip").
- package.json diff base→upstream (proves whether the manifest still owns the pruned entries).
- Local lockfile diff shape (deletion-only vs version bumps).

## Large-diff inspection pitfall

`git diff --stat` / `--shortstat` output on multi-hundred-KB diffs gets truncated by terminal capture limits and pollutes context with head+tail fragments. Use numeric, machine-sized output instead:

```bash
git diff --numstat origin/main <local-commit> -- <path> | head -1
```

numstat prints `added<TAB>deleted<TAB>path` — one short line per file, safe to loop over many files. For symbol-level presence checks across a ref use `git grep -l '<Symbol>' origin/main -- '*.py'` (works on refs without checkout).

## Duplicate-hazard scan for cleanly applied files

A clean 3-way apply does not mean semantic safety. For each new module the local commit adds (e.g. `agent/plugin_agent.py`, `agent/provider_circuit_breaker.py`):

- `git cat-file -e origin/main:<path>` — distinguishes "new file, no upstream owner" from "upstream already has this module".
- `git grep -l '<ClassName>' origin/main` — finds upstream implementations of the same feature under a different name (moved owner / renamed symbol). If none found, the feature is genuinely local-unique and its tests are load-bearing.
- Large upstream-side numstat on shared files (e.g. `cli.py` upstream +1963 lines) signals the local commit's clean hunks may reintroduce code paths upstream deliberately restructured — flag for the verifier even when no conflict marker exists.

## Clean-apply cross-file feature-cluster audit

For a broad "audit all cleanly applied files" lane, scan for **feature clusters** whose members split across conflicted and clean files. A module that applies cleanly is dead or broken if its only consumers sit in UU-conflicted files that resolve toward upstream:

1. Compute the clean-applied set: files in the replayed commit (`git show --name-only --format= <commit>`) that are staged (`git diff --cached --name-only`) and not unmerged (`git diff --name-only --diff-filter=U`).
2. For each clean file, extract symbols added by the local commit (regex `^\s*(async def|def|class)` on `git show <commit>:<path>` minus `git show <commit>^:<path>`), then check upstream: `git grep -F '<symbol>' origin/main -- .`. Symbols absent upstream AND consumed only from conflicted files (e.g. a new state field read by a UU `conversation_loop.py`) are **dangling-if-upstream-wins** hazards — list them with their consumer files so the verifier keeps or drops the whole cluster atomically.
3. New SQLite tables/indexes added in a clean schema file are cross-file invariants: enumerate every producer/consumer of the table name across the commit (`git grep -F '<table>' <commit>`) and flag the set as keep-together/drop-together.
4. Signature extensions in clean files (new kwargs on a shared method) must be matched against their callers: if the authoritative caller is conflicted, the signature and call sites must be verified as one unit — a clean apply of one side causes TypeError or silently skipped behavior.
5. Watch for import-only drift: a clean import hunk can land while the helper's usage sites were upstream-restructured away. Count symbol occurrences in the staged blob (`git show :<path>`), not just the local commit blob — an import alias with zero remaining usages is a dead-import finding.
6. Large terminal captures truncate silently on Windows (head+tail, ~10-50KB). For anything you must read fully, write tool output to a file from inside a script and `read_file` it in pages; never audit from truncated stdout.
