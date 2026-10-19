# Hermes managed checkout: update + local merge reference

Use this reference when Hermes is installed from a Git checkout and `hermes --version` reports carried commits or the source tree is dirty.

## Why the built-in updater may be unsafe for a carried stack

The inspected Hermes update path follows this shape:

1. stash dirty files;
2. `git pull --ff-only origin <branch>`;
3. if fast-forward fails, `git reset --hard origin/<branch>`;
4. restore the stash.

That protects uncommitted files but not divergent local commits. For a checkout with carried commits, perform the explicit backup/rebase/restore workflow from the umbrella skill instead of invoking the updater blindly.

## Hermes checkout discovery

Useful live checks:

```bash
hermes --version
hermes update --help
hermes update --check
hermes status --all
```

The source checkout is commonly reported directly by `hermes --version`; do not assume the current shell directory is the repository.

## Shallow carried-commit recovery

Hermes installer checkouts can contain many shallow boundaries. A carried commit can still name a real parent in `git cat-file -p` even when Git traversal treats it as a root.

```bash
commit=<carried-sha>
parent=$(git cat-file -p "$commit" | sed -n 's/^parent //p' | sed -n '1p')
git fetch --no-tags origin "$parent"
git diff --stat "$parent" "$commit"
git diff --name-only "$parent" "$commit"
```

Use this to distinguish:

- a true local patch that must be replayed;
- a formerly local feature now implemented by upstream;
- a misleading full-tree diff caused by a shallow boundary.

When the feature now exists upstream, verify the current implementation and tests, then leave the duplicate snapshot commit out of the carried stack.

## Recommended Hermes sequence

```bash
# 1. Backup commit state and all WIP.
stamp=$(date +%Y%m%d-%H%M%S)
git branch "backup/hermes-pre-update-$stamp" HEAD
git stash push -u -m "hermes-local-wip-pre-update-$stamp"
stash_sha=$(git rev-parse stash@{0})

# 2. Fetch and rebase only the carried stack.
git fetch origin main
GIT_SEQUENCE_EDITOR=true \
  git rebase --onto origin/main <old-upstream-base> main

# 3. Restore WIP while keeping the stash as rollback evidence.
git stash apply --index "$stash_sha"
# Resolve conflicts, then:
git add <resolved-files>
git restore --staged .
```

Keep every recovery branch/stash until the Desktop package and Gateway runtime have been verified.

## Conflict patterns seen in Hermes

Common semantic combinations:

- Desktop event chains: retain both new upstream event branches and local Ralph/Swarm branches; repair the `else if` braces rather than choosing one side.
- Prompt/component imports: retain new session/tile scoping plus local review-mode helpers.
- TUI submit signatures: combine upstream display metadata parameters with local internal-continuation parameters.
- Async completion formatting: preserve upstream transcript persistence and local Ultrawork instructions.
- Kanban notification routing: preserve upstream retry/cursor safety while retaining creator-specific routing and Swarm lifecycle events.

For very large generated files such as `package-lock.json`, prefer the upstream version when `package.json` is unchanged and the local diff is only platform/install churn. Reinstall dependencies from the retained lockfile, then restore any regenerated lockfile churn again.

## Windows runtime handoff

After source integration:

```bash
# Focused Python and Desktop tests first.
python -m py_compile <changed-python-files>
npm --workspace apps/desktop run typecheck

# Build the packaged Desktop artifact, not only renderer dist.
hermes desktop --build-only

# Restart the live Gateway and confirm the replacement process is running.
hermes gateway restart
hermes gateway status
```

`hermes desktop --build-only` may report that the content stamp already matches after a history-only rebase; that is sufficient when the Desktop source tree is unchanged.

## Final currentness check

Hermes upstream can advance during a long integration. Check once after verification and, if it changed, perform one bounded additional rebase from the previously integrated upstream base. Do not loop indefinitely chasing a moving branch.

```bash
remote=$(git ls-remote origin refs/heads/main | sed -n '1s/[[:space:]].*//p')
tracked=$(git rev-parse origin/main)
printf 'remote=%s\ntracked=%s\n' "$remote" "$tracked"
git rev-list --left-right --count main...origin/main
```

Expected completion state for a carried stack is `N 0`: local commits ahead, zero upstream commits behind.
