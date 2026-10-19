# Refactor-Aware Rebase Conflict Resolution

Use this reference when a local commit is being replayed across an upstream structural refactor, especially when a former god-file was split into focused modules.

## Reconstruct intent before editing

For the commit currently being replayed, inspect its original delta rather than treating the conflicted worktree as the specification:

```bash
git show --stat --oneline <local-commit>
git diff --unified=5 <local-parent> <local-commit> -- <path>
git show :2:<path>   # upstream/current side during rebase
git show :3:<path>   # replayed local commit side during rebase
```

During a rebase, `ours` is the new upstream-based history and `theirs` is the local commit being replayed. Do not apply merge-era intuition blindly.

## Identify the replayed commit and its exact patch

During an interactive rebase stop, the commit being replayed is `REBASE_HEAD` (also in `.git/rebase-merge/stopped-sha`; `.git/rebase-merge/patch` holds its full patch). Get the ground-truth delta for the conflicted file directly:

```bash
git show REBASE_HEAD -- <path>          # the exact hunks to re-express
git show :1:<path> > base.py            # common ancestor
git show :2:<path> > ours.py            # new upstream + earlier replayed commits
git show :3:<path> > theirs.py          # replayed commit applied to old base
```

`REBASE_HEAD` is more reliable than reconstructing `<local-parent>..<local-commit>` by hand during a long rebase, especially when earlier picks were already rewritten.

## Check for a partially-applied worktree before "resolving"

A conflicted file can sit in the index at all three stages while the worktree copy contains no conflict markers — because a prior partial resolution, an editor, or a previous agent already merged the hunks manually. Before rewriting anything, diff the worktree against both sides:

```bash
git show :2:<path> | diff - <path>     # worktree vs ours
git show :3:<path> | diff - <path>     # worktree vs theirs
```

If the worktree equals `ours` plus exactly the `REBASE_HEAD` hunks (adapted to ours-side call signatures), the resolution is already done semantically — verify it (below) and report rather than re-editing. Never assume no-markers means resolved, and never assume a 3-stage index means the worktree is untouched.

## Verify semantic fit of replayed hunks against refactored ours

Cleanly-placed hunks can still be semantically wrong when ours refactored the surrounding call. For each replayed hunk, locate the same call site in ours and confirm:

- the callee signature on the ours side accepts every keyword the hunk passes (check the real `def` in the target module, not just the diff text);
- middleware/helper wrapping matches ours' convention (e.g. ours returning a 4-tuple via a wrapper where theirs called a 2-tuple helper directly — keep ours' wrapper, swap only the `execute=` body and condition);
- symbols the hunk references exist on the ours side (`grep -rn '<symbol>' --include='*.py'`), including attributes introduced by earlier replayed commits in the same stack;
- no duplicate branch remains: after merging an `elif A:` into a new `elif A or B:` condition, confirm no second copy of the old branch survived elsewhere in the function.

## Same-anchor additive conflicts: keep both, upstream first

A frequent low-risk conflict shape: upstream and the replayed commit each insert a **different** entry at the **same** insertion point of an ordered list (sidebar nav items, import blocks, CLI flag tables, enum members, menu arrays). Git flags it as one conflict region with one line per side even though the entries are semantically independent. Example from a Docusaurus `sidebars.ts` rebase:

```
<<<<<<< HEAD
                'developer-guide/subagent-lifecycle-api',
=======
                'developer-guide/plugin-agent-access',
>>>>>>> REBASE_HEAD
```

Resolution recipe:

1. Confirm both entries are independent (not renames of each other): check stage 2 and stage 3 each contain only one of them, and inspect the replayed commit's patch (`git show REBASE_HEAD -- <path>`) to see the entry's intended position relative to its neighbors.
2. Keep **both** lines: upstream entry first (preserve upstream navigation/ordering), then the replayed entry placed by the theirs-side convention (e.g. grouped after a related sibling entry).
3. Verify referents exist: for doc-ID lists, `ls` the referenced files; for imports/routes, grep the symbol. A sidebar entry pointing at a doc the replayed commit adds in a *later* pick is fine only if that pick is still queued — check the rebase todo list.
4. No other file changes are needed when the worktree outside the conflict region already matches stage 2 verbatim — confirm with `git show :2:<path> | diff - <path>` after editing.
5. Validate with the doc site's own gate: for Docusaurus, `npm run typecheck` (`tsc -p . --noEmit`) catches broken syntax, and `npm run build` validates that every sidebar doc ID resolves — prefer these over generic parsers for `sidebars.ts`.

## Reading long patches when terminal output is truncated

On hosts where terminal output is head+tail truncated (Windows MSYS capture window), `git show REBASE_HEAD -- <path>` for the exact hunk can be cut off mid-diff. Redirect to a temp file and page with the file reader instead of re-running:

```bash
git show REBASE_HEAD --format= --patch -- <path> > /tmp/patch.txt
```

Then read `/tmp/patch.txt` (with line numbers). Do the same for stage blobs when grepping a section: `git show :2:<path> | sed -n 'N,Mp' > /tmp/ours.txt`. Never resolve a conflict from a truncated view of the patch.

## Detect relocated ownership

If the local side restores a large handler or configuration block that upstream removed:

1. Search the new tree for the behavior, symbol, route, or command name.
2. Use `git log -S'<symbol>' -- <old-path>` and inspect the structural-refactor commit.
3. Keep the upstream file split or extraction.
4. Port only the local behavioral delta into the new owning module.

Examples:

- If `command.dispatch` moved from a large server file into `methods_tools.py`, do not restore the old handler wholesale; add the local command branches to `methods_tools.py`.
- If `DEFAULT_CONFIG` moved from `config.py` into `config_defaults.py`, retain the import-only `config.py` and add the local key under the existing section in `config_defaults.py`.

Whole-file `--ours` is acceptable only when the local commit delta has been enumerated and every still-required hunk will be reapplied deliberately. Otherwise it silently drops cleanly-applied local hunks outside the visible conflict.

## Audit cleanly-applied duplicate hazards

Git only marks textual conflicts. A replay can also apply cleanly while duplicating behavior upstream already added. Before continuing, run a broad parser/compiler check over all touched modules. Look specifically for:

- repeated keyword arguments;
- duplicate CLI/argparse option registration;
- duplicate route or command handlers;
- stale imports after a module extraction;
- fresh-schema and rebuild-schema column order drift.

Then run the narrow regression files for the replayed commit. A compile pass should precede pytest so collection errors do not obscure the real conflict.

## Diff relocated handlers by behavior, not by file

A high-risk extraction conflict has this shape: the upstream side is empty at the old insertion point, while the replayed side restores hundreds of lines containing a decorated route or command handler. The same handler now exists in a focused upstream module. Keeping both creates duplicate registration; choosing upstream wholesale silently drops local branches.

Use this resolution:

1. Search the whole current tree for the decorator key, route name, RPC method, or command string. Confirm the new owner before editing.
2. Extract the replayed handler from the old commit and the current handler from the new owner. For Python, an AST-based extractor keyed by the decorator argument is more reliable than line ranges after a god-file split.
3. Diff those two function bodies. Classify each delta as:
   - upstream evolution already present in the new owner;
   - formatting only;
   - a unique local behavior that still needs porting.
4. Keep the upstream extraction. Port only unique local branches, lifecycle emissions, or arguments into the new owner.
5. Remove the entire old-owner conflict block and verify the decorated handler is registered exactly once in the live tree.
6. Run producer/consumer tests when the port crosses a boundary (for example, Python emits an event and Desktop consumes it).

Do not leave the old function renamed or undecorated as dead code merely to avoid deleting a large conflict region. The goal is one authoritative owner, not two copies with only one active.

## Revalidate old tests against current architecture

Replayed tests are evidence of the local commit's intent, but their mechanism may be obsolete after upstream architectural changes. Preserve the behavioral contract, not an outdated assertion path.

Common adaptations:

- If upstream added progressive disclosure, test raw registration through the documented pre-assembly/catalog API rather than asserting every plugin schema remains directly model-visible.
- If upstream extracted a function, test the live imported behavior rather than reading or parsing source text.
- If a local test snapshots mutable catalogs, counts, or implementation shape, replace it with an invariant before continuing the rebase.
- When a huge legacy test file exceeds the per-file timeout, enumerate the test names added by the replayed commit from its diff and run those with `-k`, then run the broader focused subsystem files separately.

A test that fails because the upstream architecture intentionally changed is not resolved by restoring the old architecture. First identify the new supported seam, then move the assertion to that seam.

## Verification gate per conflicted commit

Before `git rebase --continue`:

```bash
python -m compileall -q <touched-python-packages>
git diff --check
git diff --name-only --diff-filter=U
scripts/run_tests.sh <targeted-test-files> -q
```

An unmerged-file list remains until the resolved files are staged; that is expected. Stage only tracked resolution files, leave unrelated untracked files untouched, then continue non-interactively.

When test output is truncated, capture the canonical test command to a temporary log and inspect the complete traceback before changing code. Do not retry the same failing command without first extracting the actual failure.

## Editing-tool isolation fallback

A source checkout being updated can temporarily shadow modules used by the host's own editing tool. If a targeted edit backend fails while its requested replacement is still valid, use a fresh helper process and invoke the same targeted file patch API there. Preserve exact old/new anchors and verify the resulting diff; do not convert this into an unrestricted whole-file rewrite.
