---
name: extract-nexus-articles
description: Extract Nexus Mods articles into structured reference docs.
version: 0.1.0
author: Hermes
platforms: [windows]
metadata:
  hermes:
    tags: [Nexus, Documentation, Browser, CDP, BGS]
---

# Extract Nexus Mods Articles

Extracts all articles from a Nexus Mods mod page's Articles tab and compiles them into a structured reference document. Uses CDP (Chrome DevTools Protocol) through a pre-authenticated browser session on port 9222. Does NOT fetch Description, Files, Posts, or Bugs tabs — articles only.

## When to Use

- "extract the articles", "read the articles from this mod"
- "compile a reference from the mod's articles"
- "summarize all the author's article docs"
- User provides a Nexus mod URL with `?tab=articles` or says "articles tab"
- Building a skill from mod-author documentation hosted as articles

## Prerequisites

- Chrome/Edge running with `--remote-debugging-port=9222` AND logged into Nexus Mods
- Node.js >= 18 with `ws` module available (`require("ws")`)
- The CDP browser's page WebSocket URL (discover via `curl http://127.0.0.1:9222/json`)

## How to Run

1. Use `terminal` to check CDP availability with `curl -s http://127.0.0.1:9222/json/version`
2. Extract article IDs from the listing page via CDP `Runtime.evaluate`
3. Fetch each article body via `#mainContent article` selector
4. Compile extracted content into a structured reference `.md` document

No external scripts are inlined — the CDP extraction is done through the `terminal` tool running small Node.js scripts from `scripts/`.

## Quick Reference

| Step | CDP Method | Key Selector |
|------|-----------|--------------|
| Get article list | `Runtime.evaluate` on `?tab=articles` | `.tabcontent-mod-page a[href*="/articles/"]` |
| Fetch article body | `Page.navigate` to article URL | `#mainContent article` |
| Get article title | `Runtime.evaluate` | `#pagetitle h1` |

## Procedure

### Phase 1: Confirm browser connectivity

```bash
curl -s http://127.0.0.1:9222/json/version
```

If this returns JSON with a `webSocketDebuggerUrl`, the browser is reachable. If not, the BGS-Nexus-automation `init-browser.js` script must be run first.

### Phase 2: Extract the article ID list

Navigate to the mod's articles tab and extract all article links:

```
URL: https://www.nexusmods.com/{game_domain}/mods/{mod_id}?tab=articles
```

Use the CDP extraction script from `scripts/extract-article-list.js`, which:
- Navigates to the articles tab
- Waits 10s for Next.js rendering
- Extracts `a[href*="/articles/"]` links (text + href)
- Handles pagination by checking for page 2+ links

### Phase 3: Fetch each article body

Use `scripts/extract-one-article.js` for each article URL. This script:
- Navigates to the article page
- Waits 10s for rendering
- Extracts from `#mainContent article` (body) and `#pagetitle h1` (title)
- Returns JSON: `{title, url, content}`

Run in a bash loop for batches:
```bash
for aid in 6085 6094 6091; do
  node scripts/extract-one-article.js "$PAGE_WS" "https://www.nexusmods.com/skyrimspecialedition/articles/$aid"
  sleep 2
done
```

### Phase 4: Compile the reference document

After collecting all article JSON, compile them into a structured markdown reference:
1. Group articles by type (general info first, then alphabetical by patcher type)
2. Extract filter tables and operation tables from the raw text
3. Add a quick-reference index table at the top
4. Save with `write_file` to the target location

## Pitfalls

- **Cloudflare gate**: The Hermes `browser_navigate` tool triggers Cloudflare. Must use the pre-authenticated CDP browser on port 9222.
- **Next.js render delay**: Pages need 8-12 seconds after navigation before `#mainContent article` is populated.
- **Article ID redirects**: Some article URLs redirect. Always check `window.location.href` after navigation.
- **8KB CDP limit**: `Runtime.evaluate` returns strings truncated to ~8KB. Most articles fit; long ones need chunking.
- **Node.js inline script quoting**: Avoid `node -e` with complex scripts — use `write_file` to create a .js file first, then run it.
- **Background processes**: Long-running CDP scripts (looping over 20+ articles) often fail in background mode. Run foreground or in batches of 5-8 articles.

## Verification

After extraction, confirm:
1. Article count matches the Articles tab listing
2. Each entry has a non-empty `content` field (not `NO_ARTICLE`)
3. Reference document has one section per patcher type
