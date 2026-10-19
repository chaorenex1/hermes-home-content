---
name: github-trending-collector
description: "Scrape GitHub Trending (daily/weekly/monthly), enrich via gh api, analyze for new/hot projects, generate Feishu reports and HTML→PDF visual reports. Use when collecting, scheduling, analyzing, or reporting on GitHub trending project data."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Trending, Data Collection, Cron, Scraping, gh CLI]
    related_skills: [github-repo-management, github-auth]
---

# GitHub Trending Data Collector

Collect GitHub Trending repository data across three time periods (daily, weekly, monthly), enrich each repo with full GitHub API metadata, and save as structured JSON files. Designed for scheduled (cron) execution.

## When to Use

- User asks to collect/scrape GitHub trending repos
- User wants scheduled trending data collection (cron job)
- User asks for trending project popularity/heat data
- User needs repo data fields: name, ID, URL, language breakdown, stars, forks, description, README summary, owner info
- User wants to analyze trending data (new projects, categories, hot projects)
- User wants Feishu reports or PDF visual reports from trending data
- User asks to set up automated trending report pipeline (cron + Feishu + PDF)

## When NOT to Use

- Querying a single known repo → use `gh api repos/owner/repo` directly
- General repo CRUD (clone/create/fork) → use `github-repo-management`
- GitHub PR/issue workflows → use `github-pr-workflow` / `github-issues`

## Architecture

```
GitHub Trending HTML → parse repo list → gh api enrichment per repo → structured JSON
         ↑                                    ↓
    urllib.request                   /repos/{repo}           → stars, forks, description, topics, owner
    (trending page only)             /repos/{repo}/languages  → language byte counts → percentage
                                     /repos/{repo}/readme     → README (base64) → detailed summary
                                     /users/{owner}           → owner GitHub ID + URL
```

## Critical Decision: `gh api` over `urllib` on Windows

**Always use `gh api` (subprocess) for GitHub API calls on Windows.** `urllib.request` fails with intermittent SSL/TLS errors (`UNEXPECTED_EOF_WHILE_READING`, `TLS handshake timeout`) against `api.github.com`. The `gh` CLI handles SSL, auth, and retries internally and is dramatically more reliable.

The trending **HTML page** itself can be fetched via `urllib.request` — only the API endpoint has SSL issues.

### Token Redaction Pitfall

The Hermes `terminal` tool **redacts** `gh auth token` output — it appears as `gho_6L...427S` (truncated). Do NOT attempt to capture the token into a Python variable via `terminal()`. Instead, call `gh api` as a subprocess from Python:

```python
result = subprocess.run(["gh", "api", endpoint], capture_output=True, text=True, timeout=30)
data = json.loads(result.stdout)
```

## File Path Convention

Data is saved under `~/.hermes/github_trending_data/YYYY-M/`:

| Period   | Filename Pattern             | Example                     | When Updated          |
|----------|------------------------------|-----------------------------|-----------------------|
| Daily    | `YYYY-M-D.json`             | `2026-7/2026-7-5.json`      | Every day             |
| Weekly   | `YYYY-M-W.json` (W=week #)  | `2026-7/2026-7-1.json`      | Every Monday (or first run in week) |
| Monthly  | `YYYY-M.json`                | `2026-7/2026-7.json`        | 1st of month (or first run) |

Week-of-month = `((day - 1) // 7) + 1` — so days 1-7 = week 1, 8-14 = week 2, etc.

The script has built-in skip logic: if the target file already exists, that period is skipped (prevents redundant re-collection within the same day/week/month). Use `--force` to override.

## Output Data Schema

Each JSON file contains:

```json
{
  "period": "daily|weekly|monthly",
  "collected_at": "2026-07-05T12:45:15.205702",
  "total_repos": 18,
  "repos": [
    {
      "repo_name": "codex-plugin-cc",
      "repo_id": "openai/codex-plugin-cc",
      "repo_url": "https://github.com/openai/codex-plugin-cc",
      "languages": {"JavaScript": 100.0},
      "stars": 24691,
      "forks": 1495,
      "short_description": "Use Codex from Claude Code to review code or delegate tasks.",
      "detailed_summary": "# Codex plugin for Claude Code\n...(README, truncated to 5000 chars)",
      "owner": {
        "login": "openai",
        "github_id": 14957082,
        "github_url": "https://github.com/openai"
      },
      "topics": [],
      "homepage": "",
      "license": "Apache License 2.0",
      "created_at": "2026-03-30T15:29:52Z",
      "updated_at": "2026-07-05T04:39:04Z",
      "period_stars": 718
    }
  ]
}
```

## Running the Collector

### One-time / manual run

```bash
# Collect all periods (skips existing files)
python <HERMES_HOME>/scripts/github_trending.py --period all

# Force re-collect all periods
python <HERMES_HOME>/scripts/github_trending.py --period all --force

# Collect only daily
python <HERMES_HOME>/scripts/github_trending.py --period daily
```

### Scheduled (cron)

Create a daily cron job at 09:00:

```
Schedule: 0 9 * * *
Prompt: Run `python <HERMES_HOME>/scripts/github_trending.py --period all`
```

The script's skip logic means daily data updates every day, weekly data updates on the first run of each week, and monthly data updates on the first run of each month — all from the same daily cron trigger.

> **Note:** Cron jobs in Hermes TUI sessions are local-only. Output is saved but not delivered to the session. For notifications, set `deliver` to a gateway-connected platform (e.g., `telegram`).

## Performance Notes

- ~18-25 repos per trending page (daily/weekly/monthly vary)
- 4 API calls per repo (details + languages + readme + owner) = ~80-100 calls total
- 0.5s delay between API calls = ~1-2 minutes per period
- Total runtime for all 3 periods: ~5-7 minutes
- GitHub API rate limit: 5000 req/hour with auth (well within limits)

## Files

### Skill scripts
- `scripts/github_trending.py` — the complete collector script (standalone, re-runnable)

### Pipeline scripts (in `~/.hermes/scripts/`)
- `trending_analyzer.py` — analysis engine (new projects, categorization, hot projects)
- `ai_classify_prepare.py` — splits analysis repos into batches of 6, outputs batch paths for AI delegation
- `ai_classify_merge.py` — merges AI classification results back into analysis JSON, recomputes distributions
- `feishu_report.py` — Feishu document creation + IM notification
- `generate_html.py` — HTML report generator (Python, Linear dark theme design system) — **replaces `generate_ppt.js`**
- `html2pdf.js` — HTML→PDF converter (puppeteer-core + system Edge browser, 1280×720px pages) — **replaces LibreOffice PPTX conversion**
- `pdf2img.py` — PDF→JPEG image converter (PyMuPDF, for vision QA)
- `trending_orchestrator.py` — main orchestrator for cron jobs
- `trending_run.sh` — bash wrapper (sets up environment and calls orchestrator)

### References
- `references/trending-page-structure.md` — HTML parsing details, API endpoints, Windows SSL workaround
- `references/pipeline-scripts.md` — detailed design decisions for all pipeline scripts (analyzer, feishu, PPT, orchestrator)
- `references/ai-classification-workflow.md` — AI delegation taxonomy, prompt template, and merge script for accurate repo classification
- `references/pipeline-test-procedure.md` — step-by-step end-to-end test procedure (reset → prepare → delegate → merge → verify → cleanup) with expected timing and troubleshooting
- `references/feishu-drive-folder-management.md` — Feishu Drive folder hierarchy (root + monthly subfolders), local token cache, required OAuth scopes, and `ensure_report_folder()` design

### Templates
- `templates/cron-prompt-template.md` — full tested cron job prompt (3-step pipeline) ready to copy, with cron config table and validation results

## Full Report Pipeline (Collect → Analyze → Feishu → HTML/PDF Report)

The collector is the first stage of a full trending report pipeline. After data collection, three additional scripts process the data into Feishu documents and PPT reports. All pipeline scripts live in `~/.hermes/scripts/`.

### Pipeline Architecture

```
github_trending.py  →  trending_analyzer.py  →  feishu_report.py
(collect data)          (analyze + classify)     (Feishu doc + IM notify)
                                                   ↓
                                             generate_html.py
                                             (Linear dark theme HTML report)
                                                   ↓
                                             html2pdf.js
                                             (puppeteer-core + Edge → PDF)
                                                   ↓
                                             trending_orchestrator.py
                                             (orchestrates all of the above)
```

### Analysis (`trending_analyzer.py`)

The analyzer reads collected JSON and produces structured analysis:

- **New project detection**: Scans all previous period data files to identify repos that have never appeared before. A repo is "new" if its `repo_id` doesn't exist in any prior same-period file.
- **Categorization**: Classifies each repo into categories (AI/ML, Developer Tools, Web/Framework, Data/Database, Security, DevOps/Infra, Mobile/App, Game/Media, Blockchain, System/Low-level) and scenes (代码生成与辅助, 模型推理与部署, etc.) using **word-boundary regex matching** (`\b...\b`) against a two-tier text source: first high-signal text (repo name, topics, short description), then a cleaned README excerpt as fallback. HTML tags are stripped from the README before matching. See `references/pipeline-scripts.md` for the full classification design and the pitfalls of naive substring matching.
- **Hot project detection**: Flags repos with `period_stars ≥ threshold`. Thresholds: daily ≥1000, weekly ≥5000, monthly ≥10000.
- **Project summary generation**: Extracts capabilities from cleaned (HTML-stripped) README, identifies primary language, categories, and scenes.

```bash
# Analyze a specific date
python trending_analyzer.py --period daily --date 2026-7-5 --save
# Output: ~/.hermes/github_trending_data/2026-7/analysis/2026-7-5_analysis.json
```

### Feishu Report (`feishu_report.py`)

Creates a Feishu document with the analysis and sends a notification message:

- **Drive folder management**: Documents are organized in a hierarchical folder structure in Feishu Drive — root folder "GitHub Trending" → monthly subfolder (e.g., "2026-7"). Folder tokens are cached locally in `~/.hermes/github_trending_data/feishu_folders.json` to avoid repeated API calls. The `ensure_report_folder()` function is called before document creation to get the target folder token. **Important:** `docs +create --parent-token` does NOT reliably place documents into folders (Feishu API limitation). The `create_feishu_doc()` function uses a create-then-move pattern: creates the doc without `--parent-token`, then immediately calls `drive +move` to move it into the target folder. See `references/feishu-drive-folder-management.md` for the full implementation and scope requirements.
- **Document**: XML content with sections: 总体概览 (overview + **Mermaid pie charts** for language/category/scene distributions + hot projects), 项目列表 (full repo list with **structured multi-line fields**), 新秀项目 (new projects).
- **Mermaid pie charts**: Three `<whiteboard type="mermaid">` blocks render as native Feishu whiteboards:
  - 📊 语言分布 — top 10 languages + "其他" group (pie chart)
  - 📊 分类分布 — AI category counts (pie chart)
  - 📊 场景分布 — scene counts (pie chart)
- **Structured summary fields**: Each repo's info is displayed as separate `<p><b>field</b>：value</p>` lines:
  - 主语言 / 语言分布 / 分类 / 场景 / 一句话概括 / 核心能力
  - **All fields use Chinese AI-generated text** — `one_line_zh` replaces the English `short_description`, and `core_capability_zh` replaces the old `extract_capabilities()` English README extraction
  - The `extract_capabilities()` import is no longer needed in `feishu_report.py`; only `strip_html` is imported from `trending_analyzer`
- **Notification**: `--content` + `--msg-type post` JSON message via Feishu IM (NOT `--markdown`, NOT `--text`). Each line is a separate content element; title goes in `title` field. Includes summary stats, categories/scenes, and document link. See Pitfall 19 for the full pattern.

```bash
python feishu_report.py --analysis ~/.hermes/github_trending_data/2026-7/analysis/2026-7-5_analysis.json
```

### Report Generation (`generate_html.py` + `html2pdf.js`)

**Architecture: HTML → PDF (not PptxGenJS).** The report is generated as a self-contained HTML file with a Linear-inspired dark design system, then rendered to PDF via puppeteer-core + system Edge browser headless. This replaced the old `generate_ppt.js` (PptxGenJS) pipeline because HTML/CSS provides far more layout control and the user explicitly requested the switch.

- **Design system**: Linear dark theme — `#08090a` background, Inter font with `cv01`/`ss03` OpenType features, semi-transparent white borders (`rgba(255,255,255,0.08)`), indigo-violet accent (`#7170ff`). GitHub Linguist language colors for bar charts and card accent bars.
- **Page system**: Each `.page` div is exactly 1280×720px with `overflow: hidden` and `page-break-after: always`, producing one PDF page per div. Fixed `height` (not `min-height`) is critical — `min-height` allows content overflow that creates extra blank pages.
- **Slide layout**:
  1. Cover — GitHub Octocat SVG + title + 3 stat cards (blue/green/orange accent)
  2. Overview — dual bar charts (language distribution Top 10 + category breakdown)
  3-N. Project cards — 6 cards per page (2-column grid), with language accent bar, star count, AI Chinese descriptions, hot/category badges
  N+1. Summary ranking table — all repos in a compact table (18 rows fit on one page with 3px row padding + 11px font)
- **Card sizing**: `min-height: 140px; max-height: 165px` per card. Six cards (3 rows × 2 columns) at this height fit within the 720px page minus header/footer. Gap reduced to 12px.
- **Long project names**: CSS `text-overflow: ellipsis` with `white-space: nowrap` and `max-width: 220px` handles truncation natively — no JS truncation needed.

```bash
# Step 1: Generate HTML from analysis JSON
python3 generate_html.py <analysis.json> <output.html>

# Step 2: Render HTML to PDF via Edge headless
node html2pdf.js <output.html> <output.pdf>

# Step 3 (optional QA): Convert PDF pages to images for vision_analyze
python3 pdf2img.py <output.pdf>
```

### Orchestrator (`trending_orchestrator.py`)

Main entry point for cron jobs. Determines target date (previous day/week/month), collects data if missing, runs analysis, creates Feishu report, generates HTML+PDF report.

```bash
python trending_orchestrator.py --mode daily     # Analyze yesterday
python trending_orchestrator.py --mode weekly    # Analyze last week
python trending_orchestrator.py --mode monthly   # Analyze last month
python trending_orchestrator.py --mode daily --skip-collect  # Use existing data only
```

The orchestrator Step 3 calls `generate_html.py` (Python) then `html2pdf.js` (Node.js) to produce the PDF report.

### Cron Schedule

| Mode   | Cron          | Target                    |
|--------|---------------|---------------------------|
| Daily  | `0 9 * * *`   | Yesterday's data          |
| Weekly | `0 10 * * 1`  | Last week's data          |
| Monthly| `0 11 1 * *`  | Last month's data         |

### Report Output

Reports are saved to `~/.hermes/github_trending_data/ppt/`:
- HTML: `Github项目{display_label}热度.html`
- PDF: `Github项目{display_label}热度.pdf`
- (e.g., `Github项目2026年7月5号热度.pdf`)

## AI-Powered Classification (Recommended over Keyword Matching)

The keyword-based classification in `trending_analyzer.py` (word-boundary regex against topics/description/README) produces **poor results in practice**: every repo gets tagged with 3-6 categories and multiple scenes, and the assignments are often nonsensical (e.g., a ROM manager tagged as "前端开发/安全审计"; a photo manager tagged as "Web/Framework/Mobile/App/Game/Media/System/Low-level"). This makes the category/scene distribution counts meaningless for reports and PPT generation.

**When to use AI classification instead:** any time you need accurate, human-quality category + scene + one-line Chinese description for the analysis output. The keyword classifier is acceptable as a fast first pass for bulk processing, but for published reports (Feishu docs, PPTs), always upgrade to AI classification.

### Workflow: Parallel AI Delegation

1. **Split repos into batches of 6** (18 repos → 3 batches). This balances parallelism against per-subagent token limits.
2. **Write each batch to a temp JSON file** with compact fields: `repo_id`, `repo_name`, `stars`, `period_stars`, `languages`, `short_description`, `topics`, `detailed_summary_excerpt` (truncate README to ~800 chars).
3. **Dispatch 3 parallel `delegate_task` subagents**, each classifying one batch. Each subagent reads its batch file and writes results to a `result_N.json` file. Output fields: `repo_id`, `category`, `scene`, `one_line_zh` (≤40 chars Chinese one-liner), `core_capability_zh` (≤60 chars Chinese core capability).
4. **Merge results** back into the analysis JSON, replacing the keyword-based `categories`/`scenes` fields with `ai_category`, `ai_scene`, `one_line_zh`, and `core_capability_zh`. Use `ai_classify_merge.py` for this.
5. **Clean up temp files** (batch + result JSONs).

The full cron prompt template (tested on 2026-07-05, ready to copy) is in `templates/cron-prompt-template.md`. A step-by-step pipeline test procedure (reset → prepare → delegate → merge → verify → cleanup) is in `references/pipeline-test-procedure.md`.

### Automated Pipeline (Cron Jobs)

The AI classification step is now baked into all three cron jobs (daily/weekly/monthly). The cron prompt has a 3-step structure:

| Step | Action | Toolset |
|------|--------|---------|
| 1 | Collect data + keyword analysis + HTML/PDF generation (`trending_run.sh`) | terminal |
| 2 | AI delegation classification (2a prepare → 2b parallel delegate → 2c merge) | terminal + delegation |
| 3 | Report already generated in Step 1 (HTML→PDF) | — |

**Critical cron config:** `enabled_toolsets` must include `"delegation"` alongside `"terminal"`. Without the delegation toolset, the cron agent cannot call `delegate_task` and will silently fall back to keyword-only classification.

**Cron prompt structure for Step 2:**

```
### 2a. Prepare batches
python3 ~/.hermes/scripts/ai_classify_prepare.py <analysis_json_path>

### 2b. Delegate subagents (parallel)
Use delegate_task with tasks=[...]. Each task reads <BATCH_n_PATH> and writes result to <RESULT_DIR>/result_<n>.json

### 2c. Merge results
python3 ~/.hermes/scripts/ai_classify_merge.py <analysis_json_path> <RESULT_DIR>
```

**Fallback:** If delegation fails, the keyword-based analysis from Step 1 is still usable — the analysis JSON will have `categories`/`scenes` (multi-tag) but no `ai_category`/`ai_scene`/`one_line_zh`.

### Taxonomy (8 categories, 10 scenes)

The AI classification uses a fixed taxonomy designed for GitHub trending repos. Each repo gets exactly ONE category and ONE scene (no multi-tagging):

**Categories:** AI/Agent生态, 开发工具, 安全/隐私, 教育/知识, 媒体/娱乐, Web/前端, 系统/底层, 基础设施

**Scenes:** AI编程助手, Agent技能与编排, 安全渗透与审计, 隐私保护与本地化, 学习与教育, 媒体管理与播放, 开发效率工具, 浏览器与Web自动化, 游戏开发, 系统提示词与AI研究

See `references/ai-classification-workflow.md` for the full delegation prompt template, taxonomy definitions, and merge script pattern.

## Pitfalls

1. **Keyword classification floods categories** — Using `kw in text` for classification causes every repo to match every category, because short keywords like `"ai"`, `"model"`, `"api"`, `"tool"` appear as substrings inside common English words (`available`, `domain`, `capital`, etc.) and inside large README text. **Always use word-boundary regex** (`re.search(r'\b' + re.escape(kw) + r'\b', text)`) and match against high-signal text first (repo name + topics + description), only falling back to README if no high-signal match. **However, even with word-boundary regex, keyword classification still produces multi-category noise** — prefer AI delegation for published reports. See `references/ai-classification-workflow.md` for the AI-based alternative.
2. **Token redaction** — Hermes terminal tool redacts `gh auth token` output. Never try to capture the token string into Python; call `gh api` directly as a subprocess.
3. **`/tmp` path mismatch** — On Windows git-bash, `/tmp` maps to `C:\Users\<user>\AppData\Local\Temp`, but Windows Python doesn't understand `/tmp`. Use `os.environ['TEMP']` or `os.path.expanduser()` in Python scripts.
4. **README base64** — The `/repos/{repo}/readme` endpoint returns base64-encoded content in the `content` field. Decode with `base64.b64decode()` before using.
5. **Language percentages** — The `/repos/{repo}/languages` endpoint returns byte counts, not percentages. Divide each by the total byte count × 100.
6. **`gh api` timeout** — Set subprocess timeout to 30s and retry 3 times with exponential backoff for transient TLS handshake timeouts.
7. **PPT generation needs NODE_PATH** — `pptxgenjs` is installed globally via npm. Set `NODE_PATH=$(npm root -g)` before running `node generate_ppt.js`, or the module won't be found.
8. **README content in summaries** — The README extraction pulls raw markdown including HTML tags. When building summaries, strip HTML tags from the first few lines to avoid cluttering output with `<p>`, `<img>`, `<a>` tags.
9. **Whitespace collapse destroys feature-list extraction** — `re.sub(r'\s+', ' ', clean)` merges all newlines into a single line, which breaks downstream regex patterns that expect `^`/`$` anchors or `\n` delimiters (e.g., feature-list extraction `r'(?:^|\n)#+\s*Features?\s*\n(...)'`). Use `re.sub(r'[^\S\n]+', ' ', clean)` to collapse horizontal whitespace while preserving newlines.
10. **HTML in detailed_summary** — The `detailed_summary` field contains the raw README which often includes inline HTML (`<p>`, `<a>`, `<img>`, `<picture>`, `<source>`). Always run `strip_html()` (tag removal + entity decode) before using the README text for classification, capability extraction, or summary generation.
11. **lark-cli `.CMD` on Windows** — Python's `subprocess.run(["lark-cli", ...])` fails on Windows because lark-cli is a `.CMD` shim. Use `shutil.which("lark-cli")` to resolve the full path (returns `lark-cli.CMD`), then pass that to subprocess.
12. **lark-cli `@file` requires relative paths** — The `--content @file` flag in lark-cli docs requires a path relative to CWD, NOT an absolute temp path. Write temp content files to `os.getcwd()` and reference them by filename only.
13. **Duplicate `<title>` tag** — `build_feishu_doc_content()` must NOT include `<title>...</title>` in the XML content body. The `--title` flag in `lark-cli docs +create` already prepends `<title>` automatically. Adding it in both places causes a duplicate title tag and the API may reject the document.
14. **`extract_capabilities` no longer needed in `feishu_report.py`** — After switching to AI-generated `core_capability_zh`, the `extract_capabilities()` import was removed from `feishu_report.py`. Only `strip_html` is still imported from `trending_analyzer`. If you re-add English capability extraction, add `sys.path.insert(0, SCRIPTS_DIR)` + `from trending_analyzer import extract_capabilities, strip_html`.
15. **lark-cli identity scope split** — The Feishu app has a split scope situation: `user` identity can create documents (`docx:document:create`) but CANNOT send IM messages (missing `im:message.send_as_user` scope); `bot` identity can send IM messages but CANNOT create documents (missing `docx:document` scope). Both `create_feishu_doc()` and `send_notification()` must try `user` first, then fall back to `bot`. Do NOT assume a single identity works for both operations.
16. **`patch` tool doubles backslash-quote in f-strings** — When using the `patch` tool to edit Python f-strings containing `href=\"...\"` patterns, the tool can introduce extra backslash escaping (`href=\\\"...\\\"` instead of `href=\"...\"`). After patching Python files with quoted XML attributes, verify the result with `python3 -c "import module"` and fix any doubled backslashes with `execute_code` byte-level replacement if needed.
17. **Feishu Mermaid pie charts need `<whiteboard type="mermaid">`** — To render pie charts in Feishu documents, wrap Mermaid `pie` syntax in `<whiteboard type="mermaid">...</whiteboard>`. Do NOT use `<pre>` or `<code>` blocks for Mermaid — they render as plain text, not charts. The Mermaid syntax is: `pie title <title>\n    "Label" : <value>\n    ...`.
18. **Content size shrinks dramatically after AI Chinese fields** — Switching from English README excerpts to AI-generated `one_line_zh` + `core_capability_zh` reduced document content from ~30K chars to ~19.6K chars while improving readability. This is expected — the English `detailed_summary` and `extract_capabilities()` output was verbose and noisy.
19. **Feishu IM notification: `--content` + post JSON is the ONLY reliable method (user corrected 5+ times)** — When sending IM notifications via `lark-cli im +messages-send --as bot`, there are three content flag options:
    - `--text` — sends `msg_type=text`. **Collapses to title-only** on both mobile and desktop. Multi-line content is NOT visible. **Never use for multi-line notifications.**
    - `--markdown` — sends `msg_type=post` wrapping content as a single `{"tag":"md","text":"line1\nline2"}` element. **ALSO collapses to title-only** on some Feishu clients. **Do NOT use `--markdown` for multi-line notifications** — user explicitly rejected this multiple times.
    - `--content` with `--msg-type post` — **THE ONLY RELIABLE METHOD.** Each line MUST be a separate content element. The title goes in the `title` field, NOT duplicated in the content body. The correct pattern:
      ```python
      def build_post_json(title, text):
          lines = text.strip().split("\n")
          content = []
          for line in lines:
              if not line.strip():
                  continue
              if line.startswith("http"):
                  content.append([{"tag": "a", "text": line, "href": line}])
              else:
                  content.append([{"tag": "text", "text": line}])
          return {"zh_cn": {"title": title, "content": content}}

      post_json = build_post_json("标题", text)
      # Send:
      lark_cli("im", "+messages-send", "--as", "bot", "--user-id", ou_xxx,
               "--msg-type", "post",
               "--content", json.dumps(post_json, ensure_ascii=False))
      ```
    **Key rules:** (1) Each line of text MUST be a separate `[{"tag":"text","text":"..."}]` array — putting `\n`-separated text in a single element does NOT work. (2) URL lines use `{"tag":"a","text":"url","href":"url"}`. (3) Title goes in `title` field only, do NOT repeat it as the first content line.
    **Verified 2026-07-05:** User mobile + desktop screenshots confirmed `--content` + post JSON with per-line elements renders full multi-line content reliably. `--markdown` and `--text` both collapsed to title-only. User explicitly demanded `--content + 完整 post JSON` and rejected `--markdown` 5+ times.
20. **Notification content should use AI Chinese fields** — The `build_notification_text()` function should use `one_line_zh` (not `short_description`) for project descriptions in the IM notification, and should filter categories/scenes to non-zero counts only (`[k for k,v in analysis["categories"].items() if v > 0]`). Include hot projects in the notification (not just new projects) since hot projects have `period_stars` data users care about.
21. **`hot_projects` and `new_projects` lack AI fields after merge** — The `ai_classify_merge.py` script only enriches `analysis["repos"]` with `ai_category`/`ai_scene`/`one_line_zh`/`core_capability_zh`. The `analysis["hot_projects"]` and `analysis["new_projects"]` arrays are separate references built by `trending_analyzer.py` and do NOT automatically inherit AI fields. After merging, **you must manually enrich these arrays** by looking up each project's `repo_id` in the main `repos` list and copying the AI fields:
    ```python
    repos_map = {r["repo_id"]: r for r in analysis["repos"]}
    for p in analysis.get("hot_projects", []) + analysis.get("new_projects", []):
        r = repos_map.get(p["repo_id"])
        if r:
            p["one_line_zh"] = r.get("one_line_zh", "")
            p["core_capability_zh"] = r.get("core_capability_zh", "")
    ```
    Without this step, `build_notification_text()` and `format_repo_summary_lines()` will fall back to English `short_description` for hot/new projects even though AI Chinese fields exist on the main repos.
22. **pptxgenjs `wrap: false` does NOT clip text** — It only prevents line breaks within the textbox. Text still renders beyond the textbox boundary horizontally, causing overlap with adjacent elements (star icons, shapes). Fix by manually truncating long strings (`name.substring(0, 14) + "…"`) and reducing font size. Do NOT rely on `autoFit: true` — it is unreliable in LibreOffice rendering.
23. **Vision QA false positives at 1440x811 resolution** — Vision models at low render resolution misidentify truncated text as full text, and small font differences as identical. When vision QA reports issues that seem wrong, verify by unzipping the .pptx and inspecting slide XML: `re.findall(r'<a:t>([^<]*)</a:t>', xml)` for text content, `sz="(\d+)"` for font size (1200=12pt), `<a:ext cx="(\d+)"` for textbox width in EMUs (914400 per inch). XML is ground truth.
24. **LibreOffice locks .pptx after conversion** — After `soffice --headless --convert-to pdf`, the soffice process may keep a file lock. Regenerating the same file fails with `EBUSY`. Kill the process first (`taskkill //F //IM soffice.bin` on Windows) or output to a different filename.
25. **PyMuPDF as pdftoppm alternative** — When Poppler's `pdftoppm` is unavailable, use `pip install pymupdf` then `fitz.open("file.pdf")` + `page.get_pixmap(dpi=150)` to convert PDF slides to images for visual QA.
26. **PPT icon colors must match accent bars** — Each stat card icon must be rendered in the same color as its accent bar. A mismatch (e.g., orange rocket icon on a green-accented card) is immediately visible. Pass the hex color to `iconToBase64Png(IconComponent, iconColor, 256)`.
27. **HTML→PDF pagination: use fixed `height` not `min-height`** — When generating PDFs from HTML with puppeteer-core, `.page` divs must use `height: 720px; overflow: hidden` (NOT `min-height`). `min-height` allows content to grow beyond the page boundary, creating extra blank PDF pages. The `page-break-after: always` CSS property handles page splitting between `.page` divs.
28. **Card pagination: 6 per page at 140-165px height** — For a 1280×720px page with ~60px header + ~30px footer, 6 project cards (3 rows × 2 columns) fit at `min-height: 140px; max-height: 165px` with 12px gap. More than 6 cards per page causes overflow; fewer wastes space.
29. **Table fitting: compact row padding for 18 rows** — An 18-row summary table fits on one 720px page with `td padding: 3px 10px; font-size: 11px; line-height: 1.3`. Default `padding: 8px 16px` causes the table to overflow to a second page, losing rows.
30. **puppeteer-core requires explicit `executablePath`** — `puppeteer.launch()` without `executablePath` fails with "No Chrome/Edge executable found". On Windows, detect Edge at `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` and pass it to `launch()`. No `npm install puppeteer` needed — `puppeteer-core` uses the system browser.
31. **HTML report replaces PptxGenJS** — The old `generate_ppt.js` pipeline (PptxGenJS → .pptx → LibreOffice → PDF) is deprecated. The new pipeline is `generate_html.py` (Python) → `html2pdf.js` (puppeteer-core + Edge). The HTML/CSS approach provides better layout control (CSS Grid, flexbox, `overflow: hidden`), native text truncation via `text-overflow: ellipsis`, and eliminates the LibreOffice rendering inconsistencies that plagued the PptxGenJS pipeline (wrap:false not working, autoFit unreliable, icon color mismatches).
32. **Feishu Drive folder management requires additional OAuth scopes** — Creating folders (`drive +create-folder`) and listing folder contents (`drive files list`) require scopes not included in the default auth: `drive:drive` + `space:folder:create` (for folder creation), `space:document:retrieve` (for listing folder contents). Run `lark-cli auth login --scope "drive:drive" --scope "space:folder:create" --scope "space:document:retrieve"` and have the user authorize via QR code. **Do NOT use `drive +search`** — it requires `search:docs:read` which is an admin-managed scope that cannot be self-authorized. Use `drive files list --folder-token <token>` instead (only needs `space:document:retrieve`).
33. **Folder token cache prevents redundant API calls** — `feishu_folders.json` at `~/.hermes/github_trending_data/` stores `{ "root": "<token>", "month_2026-7": "<token>" }`. The `ensure_folder()` function checks the cache first before listing/creating. If a cached token becomes stale (e.g., folder deleted manually), the doc creation with `--parent-token` will fail — delete the cache file to force a fresh search.
34. **`docs +create --parent-token` does NOT reliably place docs in folders — use `drive +move` after creation**
35. **Check for existing docs before creating — delete duplicates first** — Before creating a new Feishu document, list the target folder contents via `drive files list --folder-token <token>` and look for a child with the same name. If found, delete it with `drive +delete --file-token <token> --type docx --yes` before creating the new one. This prevents duplicate documents accumulating in the folder across re-runs. The `create_feishu_doc()` function calls `find_child_by_name(parent_token, title, child_type="docx")` and `delete_file_by_token()` before creating.
36. **Use `drive files list` NOT `drive +search` for folder/file checks** — `drive +search` requires `search:docs:read` scope (admin-managed, cannot self-authorize). `drive files list --folder-token <token>` only needs `space:document:retrieve` scope (user-authorizable). The `list_folder_contents()` function wraps `drive files list` and returns `[{name, token, type, ...}]`. Use `find_child_by_name(folder_token, name, child_type)` to check for existing folders or docs by name within a specific folder. — The Feishu API accepts the `--parent-token` parameter (visible in `--dry-run` output as `parent_token` in the request body), but the created document is **NOT** actually placed inside the specified folder. Verified 2026-07-05: three test documents created with `--parent-token` all landed in Drive root, not the target folder. **The reliable method is a two-step sequence:**
    ```python
    # Step 1: Create doc WITHOUT --parent-token
    result = run_lark_cli(["docs", "+create", "--as", identity,
                          "--title", title, "--content", f"@{tmp_name}"])
    doc_id = result["data"]["document"]["document_id"]

    # Step 2: Move doc into target folder
    if parent_token and doc_id:
        run_lark_cli(["drive", "+move", "--as", identity,
                      "--file-token", doc_id, "--type", "docx",
                      "--folder-token", parent_token])
    ```
    This is a Feishu API-level limitation, not a lark-cli bug. The `feishu_report.py` `create_feishu_doc()` function implements this create-then-move pattern.