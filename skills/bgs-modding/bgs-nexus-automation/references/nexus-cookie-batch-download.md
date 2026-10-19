> ⚠️ 2026-10-18 起本技能改用 Hermes 内置 browser 工具（`browser_navigate` / `browser_console` / `browser_click`）。
> 本文档中的 CDP、Node 脚本、`nexus-automation.js` 命令均已失效；实现以 `references/browser-console-snippets.md` 为准。
> DOM 结构记录仍可参考，但选择器可能与线上不一致（以 S1–S17 的实测结果优先）。

> 本方案依赖提取 CDP 浏览器 cookies；内置 browser 工具无法导出 httpOnly cookie，因此**不可用**。下载改走 UI + `docker cp`（见 SKILL.md 功能 13）。

# Cookie-Based Batch Nexus Downloads

When the CDP click-based download (Function 10) or Nexus API key approach
fails (403 errors), extract browser session cookies and download directly via
HTTP. This is the most reliable fallback and works for bulk downloads.

## When To Use

- CDP `nexus-automation.js download` fails with "Download type not available"
  (download-modal not found on files tab)
- Nexus API key returns 403 for CDN download URLs
- Bulk downloading 10+ mods where CDP click-based approach is too slow

## Prerequisites

- CDP Chrome browser running (via `init-browser.js`)
- User logged into Nexus Mods in that browser
- MO2 downloads folder path known

## Recipe: Extract Cookies + Bulk Download

### Step 1: Extract cookies from CDP browser

Write a script that connects to the CDP page-level WebSocket and calls
`Network.getCookies`. Save as Netscape cookie file format.

```javascript
const ws = require('ws');
const http = require('http');

http.get('http://127.0.0.1:9222/json', (res) => {
  let data = '';
  res.on('data', chunk => data += chunk);
  res.on('end', () => {
    const pages = JSON.parse(data);
    const page = pages.find(p => p.url && p.url.includes('nexusmods.com'));
    const pageWs = new ws(page.webSocketDebuggerUrl);

    pageWs.on('open', () => {
      pageWs.send(JSON.stringify({id:1, method:'Network.getCookies',
        params:{urls:['https://www.nexusmods.com']}}));
    });

    pageWs.on('message', (msg) => {
      const r = JSON.parse(msg);
      if (r.id === 1) {
        let cookieText = '# Netscape HTTP Cookie File\n';
        for (const c of r.result.cookies) {
          const domain = (c.domain.startsWith('.') ? c.domain : '.' + c.domain);
          cookieText += `${domain}\tTRUE\t${c.path||'/'}\t${c.secure?'TRUE':'FALSE'}\t${c.expires||9999999999}\t${c.name}\t${c.value}\n`;
        }
        console.log(cookieText);
        process.exit(0);
      }
    });
  });
});
```

Save to a temp file: `node get-cookies.js > nexus-cookies.txt`

### Step 2: Get download URLs via API

The MO2 API key (from Nexus `/settings/api-keys`) works for the Nexus API v1
to get file metadata and CDN download URLs. The API key itself returns 403
when used on CDN URLs, but works for metadata endpoints.

```python
import urllib.request, json

API_KEY = "XXX"  # from CDP extraction of /settings/api-keys
GAME = "skyrimspecialedition"

# Get files list
url = f"https://api.nexusmods.com/v1/games/{GAME}/mods/{mod_id}/files.json"
req = urllib.request.Request(url, headers={"apikey": API_KEY})
files = json.loads(urllib.request.urlopen(req).read())["files"]

# Pick MAIN file
main = next((f for f in files if f.get("category_name") == "MAIN"), files[0])

# Get download link
dl_api = f"https://api.nexusmods.com/v1/games/{GAME}/mods/{mod_id}/files/{main['file_id']}/download_link.json"
dl_req = urllib.request.Request(dl_api, headers={"apikey": API_KEY})
cdn_url = json.loads(urllib.request.urlopen(dl_req).read())[0]["URI"]
```

### Step 3: Download with cookies + URL encoding

The CDN URL from the API contains spaces and special characters that
urllib rejects. URL-encode the path component:

```python
import urllib.parse

parsed = urllib.parse.urlparse(cdn_url)
encoded_path = urllib.parse.quote(parsed.path, safe='/-_.=')
encoded_url = parsed._replace(path=encoded_path).geturl()

# Read cookies from Step 1 output
cookies = {}
with open("nexus-cookies.txt") as f:
    for line in f:
        if line.startswith('#') or not line.strip(): continue
        parts = line.strip().split('\t')
        if len(parts) >= 7: cookies[parts[5]] = parts[6]

cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())

# Download
req = urllib.request.Request(encoded_url, headers={
    "Cookie": cookie_str,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": f"https://www.nexusmods.com/{GAME}/mods/{mod_id}?tab=files"
})
with open(out_path, 'wb') as f:
    f.write(urllib.request.urlopen(req, timeout=120).read())
```

## Key Pitfalls

- **CDN URLs contain literal spaces** — must URL-encode the path with
  `urllib.parse.quote(path, safe='/-_.=')` before passing to urllib
- **API key works for metadata, not CDN downloads** — the MO2 API key
  succeeds on `/v1/games/.../files.json` and `/download_link.json` but
  returns 403 when used as auth header on the CDN URL. Use browser cookies
  for the actual file download.
- **Cookies expire** — the `cf_clearance` and `nexusmods_session` cookies
  have session lifetimes. Re-extract if downloads fail mid-batch.
- **Rate limit**: Add `time.sleep(0.5)` between downloads to avoid
  triggering Nexus rate limiting.

## MO2 Install After Download

Once files are in the MO2 downloads folder, install via the MO2 MCP
`mo2_install` tool in plan/apply cycles. Note: requires
`.mo2-mcp.json` at the mo2Root with `{"permission_ceiling": "full-control"}`.

## Complete Batch Pattern

```python
for mid, label in MOD_LIST:
    # 1. Get file list via API + apikey
    # 2. Pick MAIN file
    # 3. Get CDN URL via API + apikey
    # 4. URL-encode CDN URL
    # 5. Download with browser cookies -> MO2 downloads/
    # 6. sleep(0.5)
```
