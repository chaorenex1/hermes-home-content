---
name: terminal-web-research
description: "Use when web tools fail: keyless terminal research routes."
version: 1.0.0
author: Masía
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [Research, Search, Fallback, Curl, APIs]
    category: web
    related_skills: [blocked-page-recovery, grounded-citations, search-rule-engineering]
---

# Terminal Web Research (web tools down / blocked)

Companion to `blocked-page-recovery` (per-URL archive recovery). This skill is
the routing layer: what to reach for when `web_search`/`web_extract` are
unavailable, misconfigured, or the search engines block direct fetches — and
for "does X exist / which port exists" reconnaissance, where structured APIs
beat scraping outright.

## When to Use

- `web_search`/`web_extract` error out, time out, or are unconfigured, and
  the task still needs web facts.
- A search engine or site challenges direct fetches (bot page, empty body, or
  a multi-KB HTTP 200 interstitial).
- "Does a Python port / SDK / alternative for X exist?" reconnaissance, where
  org and registry APIs answer in one call.
- A JS-heavy content page needs rendering and the browser tools are not
  available to carry it.

## Route order

1. **Structured APIs first** when the question is about software, packages,
   repos, or orgs (§2) — fastest and most reliable, no anti-bot surface.
2. **Keyless SERP route** for prose / news / docs discovery (§1).
3. **r.jina.ai** to render content pages that block plain curl (§3).
4. **Real browser** only when it is connected and the page is JS-heavy; the
   routes above should otherwise carry the task.

When `web_search`/`web_extract` error with a provider-config message ("no
registered web search provider has that name"), the permanent fix is the user
picking a provider via `hermes tools` — note it, but do not stall the task on
it; the terminal routes below complete the research anyway.

## 1. Keyless SERP routes (preference order)

```bash
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
curl -s -m 30 -A "$UA" "https://lite.duckduckgo.com/lite/?q=<url-encoded>" -o lite.html
curl -s -m 40 "https://r.jina.ai/https://www.bing.com/search?q=<url-encoded>" -o serp.md
```

- `lite.duckduckgo.com/lite/` accepted a first query when
  `html.duckduckgo.com` was already serving its "anomaly" bot page, and
  returns full desktop result HTML. Result hrefs are wrapped as
  `uddg=<urlencoded-url>` plus an `&rut=` tail — decode with
  `urllib.parse.unquote`, then strip the tail.
- `www.bing.com/search` via plain curl returns a ~200-byte bot wall; route
  global Bing SERPs through `r.jina.ai` (comes back as markdown with titles
  and URLs), or use `cn.bing.com/search`, which stays curl-friendly.
- `r.jina.ai` keyless calls are rate-limited and flaky but often succeed —
  attempt once WITHOUT a key; add `Authorization: Bearer $JINA_API_KEY` only
  after a 401/Turnstile.
- Challenge detection: tiny body plus markers `anomaly`, `captcha`, `robot`,
  `unusual traffic` = blocked. Switch route once; never retry unchanged.

## 2. Structured APIs (skip SERPs entirely)

All keyless, all runnable straight from the terminal:

- Enumerate an org's repos (settles "is there an official SDK?" in one call):
  `gh api "search/repositories?q=org:<org>&per_page=50" --jq '.items[] | .full_name + "  *" + (.stargazers_count|tostring) + "  " + ((.description // "") | .[0:130])'`
- Find ports / alternatives / prior art:
  `gh api "search/repositories?q=<topic>+language:python&sort=stars&per_page=10" --jq '.items[] | .full_name + "  *" + (.stargazers_count|tostring) + "  " + ((.description // "")|.[0:130])'`
- Repo facts and README:
  `gh api repos/<o>/<r> --jq '{full_name, description, stars: .stargazers_count, language, homepage, pushed_at}'`
  and `gh api repos/<o>/<r>/readme --jq '.content' | base64 -d | head -80`
- PyPI metadata: `curl -s https://pypi.org/pypi/<pkg>/json` — read
  `.info.{version,summary,requires_python,project_urls}` and the `.releases`
  keys. A <100 B reply = name absent; a ~1 KB reply can be an unrelated
  package — read the summary before citing it.
- Prefer `gh api` over python-urllib for GitHub on Windows hosts (TLS quirks).
- Before recommending a community port, check the project's own docs for what
  its official SDK does and does not cover (e.g. a docs "SDK" page stating
  in-process TypeScript-only is the evidence that a Python port is warranted).

## 3. Rendering blocked content pages

`r.jina.ai/<url>` renders any page as markdown, JS SPAs included — try it
before escalating to a browser. For durable, timestamped copies of a single
blocked URL, use the archive ladder in `blocked-page-recovery` instead
(snapshot provenance matters when citing).

## Windows host (git-bash) rules

- Write curl artifacts as `cd <research-dir> && curl -o out.html`; `curl -o`
  onto a `~`-expanded or `/c/...` path fails ("No such file or directory") —
  native binaries do not get MSYS path translation; a `C:/...` path also works.
- Truncated terminal output prints its full-log path
  (`...\hermes\cache\terminal-output\out-*.log`); read it with `read_file`
  instead of re-running the command.
- Parse in `execute_code` (Python `re`/`json` + a small strip_html helper)
  rather than shell one-liners; keep all artifacts in one per-topic research
  directory so later steps and aggregation can reuse them.

## Pitfalls

- Don't dump raw HTML or long text to stdout — save to a file, parse
  programmatically; stdout truncates.
- Don't trust status codes or byte sizes: challenge pages are multi-KB HTTP
  200s — validate content markers (expected title words, strings).
- Don't cite existence from a search snippet: confirm through the registry /
  repo API response itself (its fields are the evidence).
- Don't alternate between two blocked routes — change the endpoint, the
  proxy, or move to an API once, then stop with a precise blocker if all fail.
- Answer "is there an X for Y" questions with a verified pointer per candidate
  (repo, package, version, last-push date) — a list of names without evidence
  is not a satisfying answer.
