# Fork and Rebrand a Deployable App

Use when a fork must ship as a separate product: new repository name, brand, domain, and deploy configuration. Renaming a fork preserves its parent link and contribution graph, so keep the fork relationship instead of creating an unrelated empty repository.

## When to Use

- The user asks to fork an existing app into their account under a new name.
- A fork needs a new brand, domain, package metadata, and deploy configuration.
- A cloned upstream repository must become the writable origin while upstream stays available for sync.

## 1. Fork without touching the working clone

Preflight the target name before creating anything:

```bash
gh auth status
gh repo view <you>/<new-name> --json name,url  # "Could not resolve" means free
gh repo fork <upstream-owner>/<repo> --clone=false
gh repo rename <new-name> -R <you>/<repo> --yes
gh repo view <you>/<new-name> --json name,isFork,defaultBranchRef,parent,url
```

`--clone=false` keeps the current working clone untouched. The rename changes the repository name but not the fork network.

## 2. Rewire remotes

A clone made from upstream has `origin` pointing at the upstream repository, which is not writable. Keep it as `upstream` and make the fork `origin`:

```bash
git remote rename origin upstream
git remote add origin https://github.com/<you>/<new-name>.git
git fetch origin
```

If the product starts a fresh history line, move the working branch to `main` and unset the inherited upstream tracking:

```bash
git branch -m <working-branch> main
git branch --unset-upstream
```

Commit, then push and set the fork default:

```bash
git push -u origin main
gh repo edit <you>/<new-name> --default-branch main
```

If `git push` hangs silently, it is the credential helper, not the network. Push through gh for that one command; see the `github` SKILL.md core discipline.

## 3. Rebrand the application, not only the repository

Search the whole tree before editing, including gitignored build caches only when needed for diagnosis:

```bash
rg -n "Old Brand|old-domain|old-owner/old-repo" --glob '!node_modules' --glob '!dist'
```

Update every user-facing or deployment-facing occurrence:

- Deploy config: worker or service name, route or custom domain, deploy URL, repository URL, index page title, TOS maintainer and contact.
- Package manifest: `name`, `description`, `repository`, `homepage`.
- Documentation: README title and intro, docs index and agent-skill frontmatter, install URLs.
- CLI and scripts: default domain, help text, completion comments, download URLs.
- UI: logo initials, fallback page title, accessible labels.
- Tests and fixtures that assert the old title, heading, or domain.

Keep protocol and storage identifiers unchanged during a rebrand: API header prefixes, binding names, cache keys, database table names, and environment variable names. Renaming those breaks existing clients or stored data.

Preserve upstream attribution. Add a Credits section and keep the original LICENSE, even when every visible string carries the new brand.

Values you cannot know, such as a support mailbox or a cloud resource id, are placeholders. Mark them explicitly and report them instead of inventing a working-looking value.

## 4. Verify before publishing

- Run the repository's full gates: typecheck, lint, tests, client build, and server or deploy dry run.
- Search again for the old brand. Remaining matches should be intentional attribution only.
- If the index or display pages are server-rendered, check the server HTML with a browser User-Agent; a CSR fallback renders the same UI and hides the regression. Load `ssr-web-app-development` for the exact check.
- Commit and push, then verify the remote commit and raw deploy config:

```bash
gh api repos/<you>/<new-name>/commits/main --jq '.sha[0:7]'
gh api repos/<you>/<new-name>/contents/wrangler.toml?ref=main -H "Accept: application/vnd.github.raw"
```

- Inherited workflows may still target the old default branch or require deploy secrets. Check `gh workflow list` and `gh run list`; never claim CI green without a run to inspect.

## 5. Deployment handoff

A fork and rename do not create cloud resources. List the remaining prerequisites explicitly: account login, KV namespace id, R2 bucket, custom domain in the same account, and CI secrets. For Cloudflare Workers, the route and `DEPLOY_URL` must match, and the KV namespace id inherited from upstream is a placeholder that must be replaced before the first deploy. Do not deploy when credentials are absent or the resource ids still point at another account. When the user explicitly asks to deploy and authorizes the cloud login, load `cloudflare-workers-deployment` and follow its resource, production-build, and live-verification gates.

After creating the resources, update the deploy config with the real ids and commit that change before or immediately after the deploy. A deployed environment whose `wrangler.toml` still points at upstream's namespace is not reproducible: the next clone will deploy against the wrong resource.
