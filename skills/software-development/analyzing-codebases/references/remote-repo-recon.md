# Remote Repo Recon Without a Clone

For questions about a GitHub project you are not editing (prompt/architecture/doc audits, vendor behaviour, "how does X assemble Y"). The API tree plus raw fetches beat a clone: no disk cost, no partial clone failures, and every fetch is a cacheable local file afterwards.

## 1. Identify and size the repo

```bash
gh api repos/<owner>/<repo> --jq '{name,default_branch,description,size,pushed_at}'
```

`size` is in KB and flags repos where cloning is the wrong move (hundreds of MB of testdata/binaries). `pushed_at` tells you whether the answer you give is current.

## 2. Dump the tree once, filter it many times

```bash
gh api "repos/<owner>/<repo>/git/trees/<branch>?recursive=1" > tree.json
```

Then filter offline:

```python
import json
d = json.load(open("tree.json"))
print(d.get("truncated"), len(d["tree"]))
for e in d["tree"]:
    if e["type"] == "blob" and e["path"].startswith("src/prompts"):
        print(e.get("size", 0), e["path"])
```

Why not `gh api ... | head`:

- The tree is often thousands of entries; the terminal capture window truncates to a few KB and hides the part you needed.
- `head` closes the pipe while gh is still writing, producing `write /dev/stdout: The pipe is being closed` — a failure that looks like a broken tool but is just an early-exit sink.
- The saved JSON answers every follow-up filter without another network call.

Check `truncated: true` — a truncated tree silently omits paths, so fall back to per-directory `contents/` listing for the subtree you actually need.

## 3. Fetch individual files as raw bytes

```bash
gh api "repos/<owner>/<repo>/contents/<path>" -H "Accept: application/vnd.github.raw" > <local-name>
```

- Keep local names flattened (`advisor_system.md`) so a loop can fetch a dozen files in one command.
- Fetch only what the tree showed is relevant; sizes in the tree are the budget signal.
- Verify with a line count (`wc -l`) — a 1–3 line file where you expected 90 usually means you fetched an HTML error page or a pointer file, not the asset.

## 4. Find the consumer of an asset (code search)

```bash
gh api -X GET search/code -f q='repo:<owner>/<repo> "advisor/system.md"' --jq '.items[].path'
```

- Quote the exact basename; unquoted searches dissolve into token matches.
- The hits are importers/loaders, which answer "how is this assembled" — the question behind most "what is the system prompt" asks.
- Note `total_count` can be an upper bound and requires auth; treat the item paths as the signal.
- If a prompt fragment yields no importer, it is usually loaded through a directory walk or a `with { type: "text" }` import under a different basename — search the fragment's unique inner phrase instead.

## 5. Continue locally

Once the handful of files are in the scratch dir, do all remaining reading and grepping there (`read_file`, `search_files`). One more remote call per question is pure latency.

## 6. Report

- Name the branch/commit you read (`main @ <date>`), because `path:line` from the API is not the user's checkout.
- Give the local scratch paths of fetched files when their content will be quoted or opened.
- Prefer structure + line anchors over pasted file bodies; the user can open the local copy.
