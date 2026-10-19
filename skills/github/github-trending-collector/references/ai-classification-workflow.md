# AI-Powered Repo Classification Workflow

Alternative to the keyword-based classifier in `trending_analyzer.py`. Uses parallel `delegate_task` subagents to produce accurate single-category + single-scene + one-line Chinese description for each repo.

## When to Use

- Preparing analysis for published reports (Feishu docs, PPTs)
- User asks for "分类" / "场景" extraction via AI
- Keyword classifier produces multi-category noise (3-6 categories per repo)

## Problem with Keyword Classification

The `trending_analyzer.py` keyword matcher assigns 3-6 categories per repo because many keywords overlap. Example from 2026-07-05 daily data:

- `immich-app/immich` (photo manager) → tagged: Web/Framework/Mobile/App/Game/Media/System/Low-level
- `rommapp/romm` (ROM manager) → scene: 前端开发/安全审计 (nonsensical)

AI delegation fixes this by assigning exactly ONE category and ONE scene per repo.

## Taxonomy

### Categories (8)

| Category | Covers |
|----------|--------|
| AI/Agent生态 | AI agent frameworks, skills, prompts, MCP, agent orchestration |
| 开发工具 | IDEs, terminals, dev workspaces, code editors, multiplexers |
| 安全/隐私 | Pentesting, security tools, privacy-focused apps |
| 教育/知识 | Textbooks, courses, documentation, learning resources |
| 媒体/娱乐 | Photo management, music players, ROM managers, game tools |
| Web/前端 | Frontend frameworks, web apps, browser tools |
| 系统/底层 | OS, kernel, embedded, terminal systems |
| 基础设施 | Cloud, docker, self-hosted, DevOps |

### Scenes (10)

| Scene | Covers |
|-------|--------|
| AI编程助手 | Code review, code generation, coding agent integration |
| Agent技能与编排 | Agent skills, plugins, MCP servers, agent multiplexing |
| 安全渗透与审计 | Pentesting, vulnerability scanning, security auditing |
| 隐私保护与本地化 | Self-hosted, privacy-first, local AI, offline |
| 学习与教育 | Textbooks, courses, tutorials |
| 媒体管理与播放 | Photo/video/music management, ROM management |
| 开发效率工具 | Terminal multiplexers, dev workspaces, productivity tools |
| 浏览器与Web自动化 | Browser automation, web GUI agents, DevTools |
| 游戏开发 | Unity, game engines, game dev tools |
| 系统提示词与AI研究 | System prompt leaks, LLM research, AI model resources |

## Workflow Steps

### 1. Split repos into batches of 6

18 repos → 3 batches. Balances parallelism against per-subagent context limits.

### 2. Write compact batch JSON files

Each batch file contains repos with these fields (truncate `detailed_summary` to ~800 chars):

```json
[{
  "repo_id": "openai/codex-plugin-cc",
  "repo_name": "codex-plugin-cc",
  "stars": 24699,
  "period_stars": 718,
  "languages": ["JavaScript"],
  "short_description": "Use Codex from Claude Code to review code or delegate tasks.",
  "topics": [],
  "detailed_summary_excerpt": "# Codex plugin for Claude Code\n...(truncated)",
  "license": "Apache License 2.0"
}]
```

### 3. Dispatch parallel `delegate_task` subagents

Use `tasks` array mode with 3 tasks. Each subagent:
- Reads its `batch_N.json` file
- Classifies each repo: category (1), scene (1), one_line_zh (≤40 chars), core_capability_zh (≤60 chars)
- Writes `result_N.json` with fields: `repo_id`, `category`, `scene`, `one_line_zh`, `core_capability_zh`

### 4. Subagent prompt template

```
Read the file <batch_path> containing 6 GitHub repos. For each repo, based on ALL available fields (short_description, topics, detailed_summary_excerpt, languages), assign:

1. category — ONE primary category from this list:
  - "AI/Agent生态" (AI agent frameworks, skills, prompts, MCP, agent orchestration)
  - "开发工具" (IDEs, terminals, dev workspaces, code editors, multiplexers)
  - "安全/隐私" (pentesting, security tools, privacy-focused)
  - "教育/知识" (textbooks, courses, documentation, learning resources)
  - "媒体/娱乐" (photo management, music players, ROM managers, game tools)
  - "Web/前端" (frontend frameworks, web apps, browser tools)
  - "系统/底层" (OS, kernel, embedded, terminal systems)
  - "基础设施" (cloud, docker, self-hosted, DevOps)

2. scene — ONE primary use scenario from this list:
  - "AI编程助手" (code review, code generation, coding agent integration)
  - "Agent技能与编排" (agent skills, plugins, MCP servers, agent multiplexing)
  - "安全渗透与审计" (pentesting, vulnerability scanning, security auditing)
  - "隐私保护与本地化" (self-hosted, privacy-first, local AI, offline)
  - "学习与教育" (textbooks, courses, tutorials)
  - "媒体管理与播放" (photo/video/music management, ROM management)
  - "开发效率工具" (terminal multiplexers, dev workspaces, productivity tools)
  - "浏览器与Web自动化" (browser automation, web GUI agents, DevTools)
  - "游戏开发" (Unity, game engines, game dev tools)
  - "系统提示词与AI研究" (system prompt leaks, LLM research, AI model resources)

3. one_line_zh — A concise ONE-LINE Chinese description of what the project does (max 40 chars).

4. core_capability_zh — A Chinese one-line summary of the project's core capability/functionality (中文，一句话概括核心功能，max 60 chars).

Output strictly as a JSON array of objects with fields: repo_id, category, scene, one_line_zh, core_capability_zh.
Write the result to <result_path>.
```

### 5. Merge results into analysis JSON

```python
import json, os
from collections import Counter

# Read all 3 result files
all_classifications = []
for i in range(1, 4):
    with open(f"result_{i}.json", "r", encoding="utf-8") as f:
        all_classifications.extend(json.load(f))

# Build lookup
cls_map = {c["repo_id"]: c for c in all_classifications}

# Merge into analysis repos
for r in analysis["repos"]:
    c = cls_map.get(r["repo_id"])
    if c:
        r["ai_category"] = c["category"]
        r["ai_scene"] = c["scene"]
        r["one_line_zh"] = c["one_line_zh"]
        r["core_capability_zh"] = c["core_capability_zh"]

# Recompute distributions
cat_counts = Counter(r["ai_category"] for r in analysis["repos"])
scene_counts = Counter(r["ai_scene"] for r in analysis["repos"])
analysis["categories"] = {k: cat_counts.get(k, 0) for k in cat_keys}
analysis["scenes"] = {k: scene_counts.get(k, 0) for k in scene_keys}

# Save
with open(analysis_file, "w", encoding="utf-8") as f:
    json.dump(analysis, f, ensure_ascii=False, indent=2)
```

### 6. Clean up temp files

Delete the batch and result JSON files after merging.

## Performance

- 3 parallel subagents processing 6 repos each
- Total wall time: ~35-40 seconds (all run concurrently)
- vs. keyword classifier: instant but inaccurate

## Automated Scripts

Two helper scripts automate the manual steps above. They live in `~/.hermes/scripts/`.

### `ai_classify_prepare.py` — Batch Splitter

```bash
python3 ~/.hermes/scripts/ai_classify_prepare.py <analysis_json_path>
```

Reads the analysis JSON, extracts compact repo data (repo_id, name, stars, languages, short_description, topics, detailed_summary truncated to 800 chars), splits into batches of 6, writes `batch_N.json` to a temp dir. Prints structured output:

```
BATCH_DIR=C:\Users\...\Temp\ai_classify_tmp
BATCH_COUNT=3
BATCH_1_PATH=...\batch_1.json
BATCH_2_PATH=...\batch_2.json
BATCH_3_PATH=...\batch_3.json
RESULT_DIR=C:\Users\...\Temp\ai_classify_tmp
INSTRUCTIONS: ...
```

The cron agent parses this output to get batch paths and result dir for delegation.

### `ai_classify_merge.py` — Result Merger

```bash
python3 ~/.hermes/scripts/ai_classify_merge.py <analysis_json_path> <result_dir>
```

Reads all `result_*.json` files from the result directory, merges `ai_category`/`ai_scene`/`one_line_zh` into each repo in the analysis JSON, recomputes `categories` and `scenes` distribution dicts, and saves the updated analysis file.

## Cron Job Integration

All three cron jobs (daily/weekly/monthly) use a 3-step pipeline:

```
Step 1: trending_run.sh --mode <daily|weekly|monthly>    [terminal]
Step 2: AI delegation classification                       [terminal + delegation]
  2a: ai_classify_prepare.py <analysis_path>
  2b: delegate_task (3 parallel subagents, each classifies 1 batch)
  2c: ai_classify_merge.py <analysis_path> <result_dir>
Step 3: PPT already generated in Step 1                   [—]
```

**Critical config:** cron `enabled_toolsets` must be `["terminal", "delegation"]`. Without `"delegation"`, the agent cannot call `delegate_task`.

**Fallback:** If delegation fails, keyword-based analysis from Step 1 is still usable (multi-category, no `one_line_zh`).

## Output Fields Added to Analysis

Each repo in `analysis["repos"]` gains:
- `ai_category` — single best-fit category
- `ai_scene` — single best-fit scene
- `one_line_zh` — concise Chinese one-liner (replaces English `short_description` in reports)
- `core_capability_zh` — Chinese core capability summary (replaces English `extract_capabilities()` output in reports)

The top-level `categories` and `scenes` dicts are recomputed from `ai_category`/`ai_scene` counts.
