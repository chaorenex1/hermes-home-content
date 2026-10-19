# Pipeline Scripts Reference

The full trending report pipeline uses 5 scripts in `~/.hermes/scripts/`:

## Scripts Overview

| Script | Language | Purpose |
|--------|----------|---------|
| `github_trending.py` | Python | Collect trending data from GitHub (scrape + gh api enrichment) |
| `trending_analyzer.py` | Python | Analyze collected data: new project detection, categorization, hot project identification |
| `ai_classify_prepare.py` | Python | Split analysis repos into batches of 6 for AI delegation; outputs batch paths + instructions |
| `ai_classify_merge.py` | Python | Merge AI classification results back into analysis JSON; recomputes category/scene distributions |
| `feishu_report.py` | Python | Create Feishu document (in managed Drive folder) + send IM notification via lark-cli |
| `generate_html.py` | Python | Generate Linear dark-theme HTML report from analysis JSON (replaces `generate_ppt.js`) |
| `html2pdf.js` | Node.js | Render HTML to PDF via puppeteer-core + system Edge browser (1280×720px pages) |
| `pdf2img.py` | Python | Convert PDF pages to JPEG images for vision QA (PyMuPDF) |
| `trending_orchestrator.py` | Python | Main orchestrator — determines target date, collects, analyzes, reports |
| `trending_run.sh` | Bash | Wrapper that calls orchestrator |

## trending_analyzer.py — Key Design Decisions

### New Project Detection Logic

Scans ALL previous period data files (same period type only — daily vs daily, not daily vs weekly) to build a set of previously-seen `repo_id` values. A repo is "new" if its `repo_id` hasn't appeared in any prior same-period file.

```python
# Only compare same-period files (daily vs daily, weekly vs weekly)
if data.get("period") != period:
    continue
```

### Category Classification

Uses a **two-tier word-boundary regex matching** strategy to avoid false positives:

1. **High-signal text** (checked first): repo_name + topics + short_description
2. **Full text** (fallback): high-signal text + cleaned README excerpt (HTML tags stripped, first 1000 chars)

Keywords are matched with `re.search(r'\b' + re.escape(kw) + r'\b', text)` — NOT plain `in` operator substring matching. This prevents `"ai"` from matching `available`, `"model"` from matching `model-view`, etc.

Categories: AI/ML, Developer Tools, Web/Framework, Data/Database, Security, DevOps/Infra, Mobile/App, Game/Media, Blockchain, System/Low-level.

Scenes (more granular): 代码生成与辅助, 模型推理与部署, 数据处理与分析, 开发效率提升, 基础设施与运维, 前端开发, 后端服务, 安全审计, 内容创作, 学习与教育.

### HTML Cleaning (`strip_html`)

The `detailed_summary` field contains raw README which often includes inline HTML. Before any text processing:

1. Strip HTML tags: `re.sub(r'<[^>]+>', ' ', text)`
2. Decode entities: `&amp;`, `&lt;`, `&gt;`, `&quot;`, `&#39;`, `&nbsp;`, `&#x27;`
3. Collapse horizontal whitespace but **preserve newlines**: `re.sub(r'[^\S\n]+', ' ', clean).strip()`
   - Do NOT use `re.sub(r'\s+', ' ', clean)` — this merges newlines and breaks feature-list regex extraction downstream.

### Capability Extraction

From the cleaned (HTML-stripped) README text, extracts feature lists by looking for markdown patterns:
- `#+\s*Features?\s*\n` followed by bullet points (`-` or `*`)
- `Features?:\s*\n` followed by bullet points

Falls back to first 3 meaningful lines (skipping headers `#`, images `![`, HTML `<`, blockquotes `>`, table rows `|`, bare URLs).

### Hot Project Thresholds

- Daily: `period_stars >= 1000`
- Weekly: `period_stars >= 5000`
- Monthly: `period_stars >= 10000`

### Output Schema

The analysis JSON contains:
```json
{
  "period": "daily|weekly|monthly",
  "date_str": "2026-7-5",
  "display_label": "2026年7月5号",
  "total_repos": 18,
  "new_project_count": 18,
  "hot_project_count": 2,
  "hot_threshold": 1000,
  "languages_covered": {"JavaScript": 10, "Python": 5, ...},
  "categories": {"AI/ML": 15, "Developer Tools": 12, ...},
  "scenes": {"前端开发": 8, "后端服务": 6, ...},
  "repos": [...],          // all repos, sorted by stars desc
  "new_projects": [...],   // subset: new only, sorted by stars desc
  "hot_projects": [...]    // subset: hot only
}
```

Each repo in the analysis has the enriched fields from collection plus: `summary`, `primary_language`, `categories`, `scenes`, `is_new_project`, `is_hot`.

## feishu_report.py — Key Design Decisions

### Document Content Format

Uses lark-cli XML format (not Markdown). The document has three sections:
1. **项目总体概览** — overview paragraph with stats, **three Mermaid pie charts**, hot projects highlight
2. **项目列表** — all repos with author, URL, stars, **structured multi-line summary fields**, topics, license
3. **新秀项目** — new projects with author, URL, stars, structured summary fields

### Mermaid Pie Charts

Three `<whiteboard type="mermaid">` blocks render as native Feishu whiteboard charts:

```xml
<h2>📊 语言分布</h2>
<whiteboard type="mermaid">pie title 项目语言分布
    "JavaScript" : 15
    "Shell" : 14
    ...
    "其他" : 42</whiteboard>
```

- **语言分布**: Top 10 languages by repo count + "其他" group for the rest
- **分类分布**: AI category counts (only non-zero categories)
- **场景分布**: Scene counts (only non-zero scenes)

Mermaid pie syntax: `pie title <title>` followed by `    "<label>" : <count>` lines.

### Structured Summary Fields (format_repo_summary_lines)

Each repo's info is displayed as separate `<p><b>field</b>：value</p>` lines instead of a single concatenated paragraph:

```
主语言：Rust
语言分布：Rust: 90.3%、MDX: 2.12%...
分类：开发工具
场景：开发效率工具
描述：agent multiplexer that lives in your terminal.
一句话概括：终端内的AI编程Agent多路复用器
核心能力：herdr.dev · install · quick start...
```

Priority: uses `ai_category`/`ai_scene`/`one_line_zh` (from AI delegation) when available, falls back to keyword-based `categories`/`scenes`.

### Cross-module Import

`feishu_report.py` imports from `trending_analyzer.py`:

```python
SCRIPTS_DIR = os.path.expanduser("~/.hermes/scripts")
sys.path.insert(0, SCRIPTS_DIR)
from trending_analyzer import strip_html  # only strip_html needed after AI classification switch
```

After switching to AI-generated `core_capability_zh`, the `extract_capabilities()` import was removed from `feishu_report.py`. Only `strip_html` is still needed. If you re-add English capability extraction, add `extract_capabilities` back to the import.

### Title Tag Rule

Do NOT include `<title>...</title>` in `build_feishu_doc_content()`. The `--title` flag in `lark-cli docs +create` already prepends it. Including it in both places causes a duplicate title tag.

### IM Notification Format

**Use `--content` + `--msg-type post` (NOT `--markdown`, NOT `--text`).** The IM notification uses structured post JSON with per-line content elements:

- Summary stats (total, new, hot)
- Categories and scenes (non-zero only)
- Hot projects (with `one_line_zh`)
- Top 3 new projects (with `one_line_zh`)
- Document link (if created)

> **CRITICAL:** `--markdown` and `--text` both collapse multi-line messages to title-only on Feishu mobile clients. Only `--content` + `--msg-type post` with each line as a separate `{"tag":"text","text":"..."}` element renders full multi-line content reliably. See Pitfall #19 in SKILL.md for the complete `build_post_json()` pattern.

> **PITFALL:** After `ai_classify_merge.py` runs, `hot_projects` and `new_projects` arrays do NOT automatically inherit AI fields (`one_line_zh`, `core_capability_zh`). You must manually enrich them from the main `repos` list. See Pitfall #21 in SKILL.md.

### Identity Fallback Strategy

Both `create_feishu_doc()` and `send_notification()` try `user` identity first, then fall back to `bot`:

```python
for identity in ["user", "bot"]:
    result = run_lark_cli([... , "--as", identity, ...])
    if result and result.get("ok"):
        return True
```

This is required because of a scope split: `user` can create docs but not send messages; `bot` can send messages but not create docs. See Pitfall #15 in SKILL.md.

The user's `open_id` is resolved via `lark-cli whoami --json` → `onBehalfOf.openId`, with a hardcoded fallback.

## generate_html.py + html2pdf.js — HTML→PDF Report Pipeline (replaces generate_ppt.js)

The old `generate_ppt.js` (PptxGenJS → .pptx → LibreOffice → PDF) pipeline has been **deprecated and replaced**. The new pipeline uses `generate_html.py` (Python) to produce a self-contained HTML file, then `html2pdf.js` (Node.js + puppeteer-core) to render it to PDF via the system Edge browser.

### generate_html.py — Linear Dark Theme HTML Report

Produces a self-contained HTML file (no external JS/CSS dependencies except Google Fonts). Uses a Linear-inspired dark design system:

- **Design tokens**: `#08090a` background, Inter font with `cv01`/`ss03` OpenType features, semi-transparent white borders, indigo-violet accent `#7170ff`
- **Page system**: Each `.page` div is exactly `1280×720px` with `height: 720px; overflow: hidden; page-break-after: always`. Fixed `height` (not `min-height`) is critical — `min-height` allows content overflow that creates extra blank pages.
- **Slide layout**:
  1. Cover — GitHub Octocat SVG + title + 3 stat cards
  2. Overview — dual bar charts (language distribution Top 10 + category breakdown)
  3-N. Project cards — 6 per page (2-column grid), `min-height: 140px; max-height: 165px`
  N+1. Summary ranking table — all repos, compact `td padding: 3px 10px; font-size: 11px`
- **Language colors**: GitHub Linguist colors hardcoded in `LANG_COLORS` dict
- **Card pagination**: `CARDS_PER_PAGE = 6`, cards chunked into pages in Python before HTML generation

### html2pdf.js — Puppeteer-core + Edge PDF Renderer

```bash
node html2pdf.js <input.html> <output.pdf>
```

Uses `puppeteer-core` (NOT `puppeteer` — no browser download needed) with the system Edge browser:

```javascript
const browser = await puppeteer.launch({
  executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  headless: true,
});
const page = await browser.newPage();
await page.setContent(htmlContent);
await page.pdf({ path: outputPath, width: '1280px', height: '720px', printBackground: true });
```

### QA Pipeline

1. Generate HTML: `python3 generate_html.py <analysis.json> <output.html>`
2. Render PDF: `node html2pdf.js <output.html> <output.pdf>`
3. Convert PDF to images: `python3 pdf2img.py <output.pdf>` (PyMuPDF, outputs to `slides/slide-NN.jpg`)
4. Visual QA: `vision_analyze` on key slides (cover, overview, card page, summary table)
5. Fix CSS issues → regenerate → re-verify

### Why HTML Replaced PptxGenJS

- **CSS Grid/flexbox** provides far better layout control than PptxGenJS absolute positioning
- **`overflow: hidden`** on `.page` divs guarantees no content spills across PDF pages
- **`text-overflow: ellipsis`** handles long project names natively — no manual truncation needed
- **No LibreOffice dependency** — eliminated the `soffice --headless --convert-to pdf` step that had file locking issues (Pitfall #24)
- **No icon rendering** — SVG icons are inline HTML, no `react-icons` + `sharp` + base64 pipeline needed

## trending_orchestrator.py — Target Date Logic

```python
# Daily: yesterday
target = now - timedelta(days=1)
# → "2026-7-4"

# Weekly: last week (same weekday, previous week)
target = now - timedelta(weeks=1)
week_of_month = ((target.day - 1) // 7) + 1
# → "2026-6-4" (4th week of June)

# Monthly: last month
if now.month == 1:
    return f"{now.year - 1}-12"
else:
    return f"{now.year}-{now.month - 1}"
# → "2026-6"
```

## trending_run.sh — Wrapper Script

```bash
#!/usr/bin/env bash
set -e
export NODE_PATH=$(npm root -g 2>/dev/null || echo "")
SCRIPTS_DIR="$HOME/.hermes/scripts"
python3 "$SCRIPTS_DIR/trending_orchestrator.py" "$@"
```

This wrapper is used by cron jobs to ensure `pptxgenjs` is discoverable by Node.js.

## ai_classify_prepare.py — AI Classification Batch Splitter

Splits analysis repos into batches of 6 for parallel AI delegation. Reads an analysis JSON, extracts compact repo data (truncating `detailed_summary` to 800 chars), and writes batch files to a temp directory.

### Input
```bash
python3 ai_classify_prepare.py <analysis_json_path>
```

### Output Format

Prints structured key=value lines that the cron agent parses:

```
BATCH_DIR=<temp_dir>
BATCH_COUNT=3
TOTAL_REPOS=18
BATCH_1_PATH=<path>
BATCH_2_PATH=<path>
BATCH_3_PATH=<path>
RESULT_DIR=<temp_dir>
INSTRUCTIONS: ...
```

### Batch Data Schema

Each batch file is a JSON array of repo objects with compact fields:

```json
[{
  "repo_id": "openai/codex-plugin-cc",
  "repo_name": "codex-plugin-cc",
  "stars": 24699,
  "period_stars": 718,
  "languages": ["JavaScript"],
  "short_description": "Use Codex from Claude Code...",
  "topics": [],
  "detailed_summary_excerpt": "# Codex plugin...(truncated 800 chars)",
  "license": "Apache License 2.0"
}]
```

### Design Decision: Batch Size = 6

- 18 repos / 6 = 3 batches → 3 parallel subagents (matches `delegate_task` max of 3)
- 6 repos per batch fits comfortably in a subagent's context window
- Each subagent makes 3-4 API calls (read batch + classify + write result) ≈ 30-35s wall time

## ai_classify_merge.py — AI Classification Result Merger

Reads all `result_*.json` files from a directory, merges `ai_category`/`ai_scene`/`one_line_zh` into each repo in the analysis JSON, and recomputes distribution counts.

### Input
```bash
python3 ai_classify_merge.py <analysis_json_path> <result_dir>
```

### Merge Logic

1. Load all `result_N.json` files from the result directory
2. Build a `{repo_id: classification}` lookup map
3. For each repo in `analysis["repos"]`, add `ai_category`, `ai_scene`, `one_line_zh`
4. Recompute `analysis["categories"]` and `analysis["scenes"]` dicts from the AI classification counts
5. Save the updated analysis JSON (overwrites in place)

### Field Mapping

| Result File Field | Analysis Repo Field |
|-------------------|---------------------|
| `category` | `ai_category` |
| `scene` | `ai_scene` |
| `one_line_zh` | `one_line_zh` |

The original keyword-based `categories` (list) and `scenes` (list) fields remain on each repo for traceability, but the top-level `categories` and `scenes` dicts are recomputed from the AI fields.
