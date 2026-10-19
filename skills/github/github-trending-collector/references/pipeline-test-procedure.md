# Pipeline Test Procedure — GitHub Trending

Validated end-to-end on 2026-07-05 with 18 repos.

## Purpose

When modifying any part of the GitHub Trending pipeline (collector, analyzer, AI classification scripts, cron prompts), run this test to verify the full flow works before relying on the next cron run.

## Prerequisites

- Today's raw data exists at `~/.hermes/github_trending_data/<year>-<month>/<date>.json`
- All pipeline scripts present in `~/.hermes/scripts/`

## Steps

### 1. Reset analysis to keyword-only state

Re-run the keyword analyzer to produce a fresh keyword-based analysis, overwriting any previous AI classification:

```python
import json, os, sys
sys.path.insert(0, os.path.expanduser("~/.hermes/scripts"))
from trending_analyzer import analyze_trending, get_analysis_filepath

date_str = "2026-7-5"  # adjust to target date
result = analyze_trending("daily", date_str)
analysis_path = get_analysis_filepath("daily", date_str)
with open(analysis_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"Keyword categories: {result['categories']}")
print(f"Keyword scenes: {result['scenes']}")
# Verify NO ai_category fields
has_ai = any("ai_category" in r for r in result["repos"])
print(f"Has AI fields: {has_ai}")  # Should be False
```

Expected: `categories` shows broad multi-tag counts (e.g., `AI/ML: 14, Developer Tools: 8, ...`). `Has AI fields: False`.

### 2. Run ai_classify_prepare.py

```bash
python3 ~/.hermes/scripts/ai_classify_prepare.py ~/.hermes/github_trending_data/<year>-<month>/analysis/<date>_analysis.json
```

Parse output for:
- `BATCH_COUNT` — should be 3 for 18 repos (6 per batch)
- `BATCH_1_PATH`, `BATCH_2_PATH`, `BATCH_3_PATH` — temp file paths
- `RESULT_DIR` — where subagents should write results

### 3. Dispatch parallel subagents

Use `delegate_task` with `tasks=[...]` array mode. Dispatch 3 leaf subagents, one per batch.

Each subagent context must include:
- The batch file path
- The full taxonomy (8 categories, 10 scenes)
- The output JSON schema: `{repo_id, category, scene, one_line_zh}`
- The result file path: `<RESULT_DIR>/result_<n>.json`

Wait for all 3 to complete (they run in parallel, ~30-50s total).

### 4. Run ai_classify_merge.py

```bash
python3 ~/.hermes/scripts/ai_classify_merge.py <analysis_json_path> <RESULT_DIR>
```

Expected output:
- `Loaded 18 classifications`
- `Merged: 18/18`
- Updated `categories` dict with single-category counts
- Updated `scenes` dict with single-scene counts

### 5. Verify final analysis

```python
import json
with open(analysis_path, "r", encoding="utf-8") as f:
    a = json.load(f)

# All repos must have ai_category, ai_scene, one_line_zh
all_ok = all(
    all(k in r for k in ["ai_category", "ai_scene", "one_line_zh"])
    for r in a["repos"]
)
print(f"All repos have AI fields: {'✅' if all_ok else '❌'}")

# Print summary table
for i, r in enumerate(a["repos"], 1):
    print(f"{i:2d}. {r['repo_id']:45s} {r['ai_category']:12s} {r['ai_scene']:20s} {r['one_line_zh']}")
```

### 6. Clean up

```python
import shutil, os
tmp = os.path.join(os.environ.get("TEMP", ""), "ai_classify_tmp")
if os.path.exists(tmp):
    shutil.rmtree(tmp)
```

## Expected Timing (18 repos)

| Step | Duration |
|------|----------|
| Step 1 (keyword analysis) | ~3s |
| Step 2 (prepare batches) | ~1s |
| Step 3 (3 parallel subagents) | ~30-50s |
| Step 4 (merge results) | ~1s |
| **Total** | **~35-55s** |

## Key Differences: Keyword vs AI Classification

| Metric | Keyword (Step 1) | AI (Step 2) |
|--------|------------------|-------------|
| Categories per repo | 3-6 (overlapping) | 1 (precise) |
| Scenes per repo | 1-3 (imprecise) | 1 (precise) |
| Chinese description | None | ✅ one_line_zh |
| Example: ROM manager | "前端开发/安全审计" | "媒体管理与播放" |
| Example: Photo manager | "Web/Framework/Mobile/App/Game/Media/System/Low-level" | "媒体管理与播放" |
| Wall time | ~3s | ~35-50s |

## Troubleshooting

### Subagent didn't write result file
- Check if the subagent reported success but the file is missing
- Re-dispatch that specific batch

### Merge says "No classification results found"
- Check that result files are named `result_N.json` (N = 1, 2, 3)
- Check that files are valid JSON arrays
- Check that `RESULT_DIR` path is correct

### Some repos missing ai_category after merge
- Check that `repo_id` in result files matches `repo_id` in analysis repos
- The merge script reports `Merged: X/18` — if X < 18, some repo_ids didn't match

## Step 7: Test Feishu Report (Optional)

After AI classification is complete, test the Feishu report generation:

```bash
python3 ~/.hermes/scripts/feishu_report.py --analysis ~/.hermes/github_trending_data/<year>-<month>/analysis/<date>_analysis.json
```

Expected output:
- `✅ Document created (as user): <URL>` — Feishu doc with Mermaid pie charts + structured fields
- `⚠️ Send as user failed` → `✅ Notification sent (as bot)` — IM notification via bot fallback

Verify the created document contains:
1. Three `<whiteboard>` Mermaid pie charts (语言分布, 分类分布, 场景分布)
2. Each repo shows separate `<p><b>主语言</b>：...`, `<b>场景</b>：...`, `<b>核心能力</b>：...` lines (not a single concatenated paragraph)
3. Categories/scenes in the pie charts reflect AI classification (not keyword multi-tag)

### Common Feishu report failures

| Error | Cause | Fix |
|-------|-------|-----|
| `NameError: extract_capabilities` | Missing import from trending_analyzer | Add `sys.path.insert` + `from trending_analyzer import extract_capabilities, strip_html` |
| Duplicate `<title>` tag | `build_feishu_doc_content` includes `<title>` AND `--title` flag prepends it | Remove `<title>` from content body; let `--title` flag handle it |
| `app_scope_not_applied: docx:document` (bot) | Bot lacks document creation scope | Use `user` identity for doc creation (already in fallback loop) |
| `missing_scope: im:message.send_as_user` (user) | User lacks IM send scope | Use `bot` identity fallback (already in fallback loop) |
| Doubled backslashes in `href=\"...\"` | `patch` tool escaped f-string quotes | Fix with `execute_code` byte-level replacement: `raw.replace(b'\\\\\\"', b'\\"')` |
