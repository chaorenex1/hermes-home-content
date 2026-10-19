# Cron Job Prompt Template — GitHub Trending Pipeline

Tested on 2026-07-05. Replace `{MODE}` with `daily`, `weekly`, or `monthly`.

---

Run the GitHub Trending {MODE} analysis pipeline. Execute all steps in order.

## Step 1: Collect data
```bash
bash ~/.hermes/scripts/trending_run.sh --mode {MODE}
```
This collects trending data and runs keyword-based analysis, generating an analysis JSON at ~/.hermes/github_trending_data/<year>-<month>/analysis/<date>_analysis.json

## Step 2: AI delegation classification
The keyword-based categorization from Step 1 is too broad (assigns 3-6 categories per repo). You must improve it by delegating AI subagents to classify each repo precisely.

### 2a. Prepare batches
```bash
python3 ~/.hermes/scripts/ai_classify_prepare.py <analysis_json_path>
```
This splits repos into batches of 6 and prints batch file paths. Parse the output to get BATCH_COUNT, BATCH_<n>_PATH values, and RESULT_DIR.

### 2b. Delegate subagents (parallel)
For each batch (up to 3 batches), use delegate_task with tasks=[...] to dispatch parallel subagents. Each task:
- goal: "Classify GitHub repos by category and scene using AI analysis"
- context: Read the batch file at <BATCH_n_PATH>. For each repo, assign ONE category from: AI/Agent生态, 开发工具, 安全/隐私, 教育/知识, 媒体/娱乐, Web/前端, 系统/底层, 基础设施. Assign ONE scene from: AI编程助手, Agent技能与编排, 安全渗透与审计, 隐私保护与本地化, 学习与教育, 媒体管理与播放, 开发效率工具, 浏览器与Web自动化, 游戏开发, 系统提示词与AI研究. Write a concise ONE-LINE Chinese description (max 40 chars) as one_line_zh. Write a Chinese core-capability summary (一句话概括核心功能，max 60 chars) as core_capability_zh. Output a JSON array of {repo_id, category, scene, one_line_zh, core_capability_zh} and write it to <RESULT_DIR>/result_<n>.json

### 2c. Merge results
After all subagents complete, run:
```bash
python3 ~/.hermes/scripts/ai_classify_merge.py <analysis_json_path> <RESULT_DIR>
```
This merges AI classifications (ai_category, ai_scene, one_line_zh, core_capability_zh) into the analysis JSON and recomputes category/scene distribution counts.

## Step 3: Generate PPT + Send Feishu Notification
The PPT generation was already handled in Step 1 by the orchestrator. If Step 1 succeeded, the PPT is at ~/.hermes/github_trending_data/ppt/.

The Feishu document + IM notification are handled by:
```bash
python3 ~/.hermes/scripts/feishu_report.py --analysis <analysis_json_path>
```
This creates a Feishu doc with Mermaid pie charts (language/category/scene) and sends a plain-text IM notification (using `--text`, NOT `--markdown`) with summary stats and doc link.

## Notes
- If delegation fails for some reason, the keyword-based analysis from Step 1 is still usable as fallback.
- The analysis_json_path follows the pattern: ~/.hermes/github_trending_data/<year>-<month>/analysis/<date>_analysis.json
- Clean up the temp directory after merging if possible.

---

## Cron Job Configuration

| Setting | Value |
|---------|-------|
| `schedule` | `0 9 * * *` (daily), `0 10 * * 1` (weekly), `0 11 1 * *` (monthly) |
| `enabled_toolsets` | `["terminal", "delegation"]` — MUST include "delegation" |
| `deliver` | `"local"` (output saved, not delivered to chat) |
| `repeat` | `forever` |

## Validation Results (2026-07-05)

End-to-end pipeline test with 18 repos:
- Step 1 (keyword analysis): ~3s
- Step 2a (prepare batches): ~1s
- Step 2b (3 parallel subagents): ~47s
- Step 2c (merge results): ~1s
- Total: ~52s

All 18 repos received accurate single-category + single-scene + one_line_zh classification.
