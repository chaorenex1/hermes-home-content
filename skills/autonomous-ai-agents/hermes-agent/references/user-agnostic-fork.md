# Publishing a Hermes build with no operator state

Load when the task is "make my Hermes usable by someone else", "publish / fork
Hermes", or "audit an install before sharing it".

## The split you publish along

Hermes is already two layers. The checkout is upstream code; everything that
makes an install belong to one person is state next to it.

| Path under `$HERMES_HOME` | Publish? | Why |
|---|---|---|
| `hermes-agent/` | tracked files only | upstream code, MIT |
| `.env`, `auth.json`, `gopass-source` | never | provider keys, OAuth pools |
| `config.yaml`, `SOUL.md` | never | absolute paths, account ids, persona |
| `sessions/`, `state.db`, `memories/`, `logs/`, `checkpoints/`, `backups/` | never | transcripts, real project trees, paths |
| `skills/`, `plugins/`, `cron/` | case by case | licenses, delivery targets, vendored repos |
| `profiles/<name>/` | never | each profile repeats this whole layout |

Start by proving the checkout itself is clean:

```bash
git -C "$HERMES_HOME/hermes-agent" grep -n -I -i -E '<account>|<home-dir-name>|<email>'
```

Expect zero. If it is not zero, the branch carries a real leak and no amount of
state exclusion fixes it.

## Publish procedure

1. **Never switch branches in the live checkout.** Hermes guards its running
   source tree against `git checkout` because mixed module versions can break
   the process. Work in a shared clone on real disk instead:

   ```bash
   git clone --shared "$HERMES_HOME/hermes-agent" "$SCRATCH/hermes-fork"
   ```

   Copy only the files intended for publication, branch, commit and push there.
   Delete the clone afterwards and confirm the live checkout still shows its
   original working-tree changes.

2. **Base the distribution branch on the release the machine runs**
   (`git describe --tags`, or the tag shown by `hermes --version`). Keep the
   fork's `main` as an upstream mirror; do not rewrite it. Consumers must pass
   the branch explicitly.

3. **Create the fork through the API.** `gh repo fork` treats `--clone` and
   `--remote` as booleans, so `--remote=false` is rejected and prints help:

   ```bash
   gh api --method POST /repos/OWNER/REPO/forks --jq '.full_name'
   ```

4. **Push with gh credentials**, because the Git credential manager can stall
   on this host:

   ```bash
   git remote add fork https://github.com/ACCOUNT/REPO.git
   git -c credential.helper='!gh auth git-credential' push -u fork <branch>
   ```

5. **Install into a fresh home.** Both installers read `HERMES_REPO_URL` and
   accept a branch and a home path:

   ```bash
   curl -fsSL https://hermes-agent.nousresearch.com/install.sh \
     | HERMES_HOME="$HOME/.hermes-clean" \
       HERMES_REPO_URL="https://github.com/ACCOUNT/REPO.git" \
       bash -s -- --branch <branch>
   ```

   ```powershell
   $env:HERMES_REPO_URL = "https://github.com/ACCOUNT/REPO.git"
   .\scripts\install.ps1 -Branch <branch> -HermesHome "$env:LOCALAPPDATA\hermes-clean"
   ```

   Then `hermes setup`. Never copy `config.yaml`, `SOUL.md`, `.env`,
   `auth.json`, `state.db`, `sessions/`, `memories/`, `cron/`, `profiles/`,
   `skills/` or `plugins/` from the old home.

## The pre-publish gate

Scan the files git would publish, not the working tree. Ignored build output
(`.docusaurus/`, `release/`, duration dumps) embeds absolute user paths and will
dominate a naive scan:

```bash
git -C <root> ls-files -z
```

Rules that keep the gate honest and quiet:

- Identity strings block anywhere. Match them with alphanumeric boundaries and
  skip lockfiles and lines over ~400 characters: base64 integrity hashes and
  generated bundles can contain the username by chance.
- Credential shapes block outside docs and test fixtures; inside them they are
  warnings, because upstream ships placeholders such as `sk-...` and `xoxb-...`.
- Require quoted values for generic `api_key:` / `token=` patterns. Unquoted
  assignments match ordinary code expressions (`token = base64...`) and block
  clean trees.
- Forbidden state filenames block: `.env`, `auth.json`, `state.db*`,
  `gopass-source`. Allow `.env.example`, `.env.sample`, `.env.template`,
  `.env.dist`.
- Print path, line and kind only; never the matched value, so the report can be
  pasted in public.

If the checkout already carries `contrib/user-agnostic/audit_tree.py`, run it
and keep its rules in sync with this list. Otherwise implement the gate from
these rules.

**Negative control:** point the gate at a probe tree containing a fake identity
string and a `.env`; it must exit nonzero. A gate that has only ever returned 0
proves nothing.

**Verify the artifact, not the source tree:** shallow-clone the pushed branch
from the fork, rerun the gate there, and compare
`gh api repos/ACCOUNT/REPO/git/ref/heads/<url-encoded-branch>` with local HEAD.

## What must not ship

- `skills/` and `plugins/` wholesale: hundreds of MB, mixed third-party
  licenses, vendored git repos. Only self-authored, license-cleared skills are
  candidates.
- `cron/` delivery targets, session transcripts, memories, checkpoints, logs.
- `hermes backup` archives: they contain `.env` and `state.db`.
- Git history: deleting a file in a later commit leaves it in earlier commits.
  `git log -p --all` is the only check that covers history.
