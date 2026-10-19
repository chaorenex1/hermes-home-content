# Repo discovery & shortlist triage

## Search

- Repo discovery: `gh search repos "KEYWORD" --limit 20` (add `--stars`, `--language`,
  `--topic`, `--owner` filters as needed — `gh search repos --help` lists the exact flags).
- Term-in-code discovery: `gh search code "KEYWORD" --limit 20` — works with default gh
  token scopes, no extra auth. Finds how a term/scheme is used inside projects (docs,
  configs, implementations), not just which repos mention it in metadata.
- Search every spelling of the term, not one: run BOTH the local-language form and the
  English form (`本地密钥存储` AND `local key storage`). Chinese projects carry Chinese
  descriptions but often English code/README identifiers — a single-language query
  silently misses roughly half the field.
- `gh search` tables are long and the terminal truncates at head+tail; read the full log
  file the tool reports instead of re-running (and never re-run just to page output).
- Cap output at the source: descriptions run to tens of KB (spam/oversized repos) and one
  multi-query batch can produce hundreds of KB. Search with
  `--json fullName,stargazersCount,description` and truncate the description in a
  post-process step before it lands in context. In `--template`, `\t`/`\n` written as
  plain text stay literal — escapes only take effect inside an action like `{{"\n"}}`.
- A broad single-word query in Chinese ("密钥管理") returns unrelated high-star repos;
  local-language queries work only when the phrase is distinctive ("本地密钥存储").
  Don't read a broad local-language query as a signal about the field.
- Search ranks what matches, not what matters: in any domain the mature projects often
  use different vocabulary than the topic ("password manager" vs "key storage"), so the
  top of the results is newcomers. Treat results as leads, then add the domain's
  known-name candidates and enrich BOTH sets with the metadata loop below. In the final
  deliverable, say which candidates came from search vs known-name verification.

## Enrich a shortlist with one loop

Rank candidates before deep-reading any of them:

```bash
for r in owner1/repo1 owner2/repo2; do
  gh api "repos/$r" --jq '"\(.full_name)\t★\(.stargazers_count)\t\(.language // "?")\t\(.pushed_at)\t\(.description // "")'"' 2>/dev/null
done
```

The same endpoint carries `archived`, `license.spdx_id`, `fork`, `open_issues_count` —
add those when the purpose is adoption vetting (an archived or long-stale repo is
rejected before it costs you a clone).

## Maintenance & health signals (same jq pattern)

- Releases — cadence AND which platforms actually ship binaries:
  `gh api repos/O/R/releases --jq '.[0:8][] | .tag_name+"  "+.published_at+"  "+([.assets[].name]|join(","))'`
  A missing OS asset means that OS is second-class, whatever the README claims.
- Bus factor:
  `gh api repos/O/R/contributors --jq '.[] | .login+"  "+(.contributions|tostring)'`
  One login owning nearly everything is the finding — report it as such.
- Recent activity — commit subjects tell more than the README:
  `gh api repos/O/R/commits --jq '.[0:12][] | .commit.author.date+"  "+(.commit.message|split("\n")[0])'`

## Next step

For a full usage / pros-cons adoption review built on these signals, see the
`oss-project-evaluation` skill.