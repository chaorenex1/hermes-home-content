# Hermes Docker Curl Playbook (web tools down / Chinese-web research)

Context: in the Hermes docker terminal backend, `web_search`/`web_extract` can
time out while the container has fast direct network (verify once:
`curl -m 12 -sS -o /dev/null -w "%{http_code}" https://www.baidu.com`), and the
system browser (`browser_tabs`) may be claimed by another task. Drive `curl`
from the terminal instead of retrying the web tools.

## Engine cheat sheet (observed behavior)

- `baidu.com/s` and `www.sogou.com/web`: work for 1-3 queries, then serve
  bot-check stubs (84/259-byte pages). Space queries >=3s; never retry-hammer.
- `cn.bing.com/search?q=<quote()>&mkt=zh-CN`: keeps working. Quote exact
  phrases; multi-term UNquoted queries degrade to junk (dictionary sites).
  Some rows are filtered ("为回应符合本地法律要求的通知..."). `site:` operator
  unreliable - skip it.
- `so.com/s?q=`: reliable, snippets often include full law text
  (e.g. amended regulation text).
- `m.baidu.com/s?wd=` with a mobile UA: reliable, rich snippets.
- `html.duckduckgo.com/html/?q=`: 1-2 queries then duck-challenge. Sparingly.
- URL-encode with `urllib.parse.quote`; keep queries short, split long
  questions into distinctive 8-20 char fragments.
- Extract result hrefs from RAW html (`<a[^>]+href="(https?://...)"`) before
  tag-stripping: cn.bing hrefs are direct target URLs. Sogou `/link?url=`
  redirects do NOT resolve with curl (JS-gated) - use snippet text instead.

## Output handling (critical)

- Terminal stdout truncates to ~4KB head+tail; the full-output log lives on
  the HOST and is not readable from the container. Never print long text.
- Pattern: script curls -> strips tags -> writes `/root/out/<name>.txt`;
  second script scans keywords, writes ~250-char windows around each hit to
  `analysis.txt`; read that with `read_file`.
- `read_file` chokes on very long single lines: `textwrap.wrap(text, 110)`
  into a file first.
- curl flags: `-m 30 -sS -L -A <browser UA> -H "Accept-Language: zh-CN..."`
  plus shared cookie jar `-c/-b /root/cookies.txt`; warm up baidu with one
  homepage hit.
- Common HTML strip: remove script/style, tags, unescape entities, collapse
  whitespace. MPS/gov.cn may be unreachable (521/empty) - rely on mirrors,
  government portals (xx.gov.cn), and dated snippets.

## Verifying Chinese facts / answer keys

- 驾考题库 pages show question + options + 答案 + 最佳分析:
  `ybjk.com/tiku/<id>.htm` (元贝驾考), `tiba.jsyks.com/Post/<id>.htm`
  (驾考宝典). Find `<id>` via a cn.bing exact-question query; the page
  `<title>` often embeds "答案是X".
- Prefer CURRENT-dated sources: amended rules invalidate older pages e.g.
  公安部令第172号 (effective 2025-01-01): 轻型牵引挂车 (C6) 申请年龄上限
  60 -> 70周岁; 大中型客货车 -> 63周岁. Old regional 题库 still show 60.
- `ailegal.baidu.com` and `b2bwiki.baidu.com` are JS-rendered: fetch via
  search SNIPPETS, direct curl yields empty shells.
