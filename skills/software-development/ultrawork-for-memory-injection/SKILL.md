---
name: ultrawork-for-memory-injection
description: "Use when an ultrawork plan is created or its paths change."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [ultrawork, memory, kanban, injection, dynamic-context, lancedb]
    related_skills: [ultrawork, deep-interview-for-memory-injection]
---

# Ultrawork → ultrawork_for_memory 静态信息注入（教程）

适用范围：ultrawork 模式 / UW 工作流进行中（会话 env `HERMES_ULTRAWORK_PLAN_ID` 存在时）。
目标：在计划创建/路径更新时向 kanban.db 的 `ultrawork_for_memory` 写入/补全**静态行**；动态内容永不写本表。

## 1. 这张表的作用（为什么注入）

- 记忆插件每轮 `pre_llm_call` 从 kanban.db 读静态行渲染 `<ultrawork>` 块：
  - 本表提供：`<id>`=plan_id、`<spec-path>`=spec_path、`<path>`=plan_path（后两者为空时渲染**空标签**，块不因缺路径而消失）。
  - 块内 `<Phase>` 的 index/current-focus/current-progress/future-needs/plan/todo **路径**由插件按 `contexts/<profile>/ultrawork/PLAN_ID/PHASE_INDEX/` 规范计算，**不来自本表**；`<status>` 来自 `ultrawork_kanban_runs` / `ultrawork_kanban_routes` / `tasks`（读侧 `_ultrawork_status`，按该 plan 或其创建会话解析）。
- 渲染前提：会话 env 同时有 `HERMES_ULTRAWORK_PLAN_ID` 与合法的 `HERMES_ULTRAWORK_PHASE_INDEX`（正整数），且本表存在该 plan_id 行；否则整块省略、不报错。
- 需求合同（记忆最新需求2 行282-285）：静态 = plan-id（将规格或直接需求变成计划后产生）+ spec-path（规格路径）+ plan-path（计划文件路径）；动态 = 辩证推理产出的 600 字 `session_summary.md`。

## 2. 触发点（什么时候注入）

1. **计划创建后、plan-id 产生时**（如 `hermes ultrawork plan <spec-path|goal> [repo]` 之后）：
   `upsert(plan_id=<id>, session_id=<当前会话>, spec_path=<若有>, plan_path=<计划文件路径>)`
   - 规格规范位置：`HERMES_HOME/lancedb-memory/resource/spec/<title>.md`
   - 计划规范位置：`HERMES_HOME/lancedb-memory/resource/plan/<title>.md`（Ultrawork 唯一权威计划文件，见 skill `ultrawork` 的 Plan Contract）
2. **路径补齐/变化时**（spec/plan 文件重导出、路径修正）：再次 upsert 同 plan_id，传新值。

幂等安全：`None` 字段不覆盖旧值；`created_at` 保留首次时间、`updated_at` 每次刷新。

## 3. 注入方法（首选：宿主 helper）

```bash
python - <<'PY'
import sys
sys.path.insert(0, r"<HERMES_HOME>\hermes-agent")  # HERMES_HOME\hermes-agent
from hermes_cli.workflow_memory_tables import upsert_ultrawork_for_memory

row = upsert_ultrawork_for_memory(
    plan_id="<plan-id>",              # 必填、非空
    session_id="<session-id>",        # 可选；建议给（<status> 解析会用到该会话）
    spec_path=None,                   # 若有规格：resource/spec/<title>.md
    plan_path=None,                   # 计划文件：resource/plan/<title>.md
)
print(row)
PY
```

- 落库解析（写入侧）：`HERMES_KANBAN_DB`（宿主已注入 worker 环境）→ 否则当前看板 → default 板 = `<HERMES_HOME>/kanban.db`；命名看板 = `<HERMES_HOME>/kanban/boards/<slug>/kanban.db`。仅测试/跨库时传 `db_path=...`。
- helper 自带 `ensure_tables`、RFC3339 UTC `Z` 时间戳、busy_timeout=120s，返回落库行。

## 4. 兜底：等价 SQL（仅当 helper 不可导入；表已存在时）

```sql
INSERT INTO ultrawork_for_memory(plan_id, session_id, spec_path, plan_path, created_at, updated_at)
VALUES (:id, :sid, :spec, :plan, :now, :now)
ON CONFLICT(plan_id) DO UPDATE SET
  session_id = COALESCE(excluded.session_id, ultrawork_for_memory.session_id),
  spec_path  = COALESCE(excluded.spec_path,  ultrawork_for_memory.spec_path),
  plan_path  = COALESCE(excluded.plan_path,  ultrawork_for_memory.plan_path),
  updated_at = excluded.updated_at;
```

`:now` = `%Y-%m-%dT%H:%M:%SZ`。切勿另写 schema（列固定）。

## 5. 陷阱

- **plan_id 必须与 env 一致**：渲染只认 `HERMES_ULTRAWORK_PLAN_ID` 的精确值；另外 `HERMES_ULTRAWORK_PHASE_INDEX` 非正整数或缺省 ⇒ 整块省略（phase 不写本表、也无处可写）。
- **写读同库**：插件读序 = `HERMES_KANBAN_DB` → `HERMES_HOME/kanban.db` → `<hermes_home>/kanban.db`；与写入端不一致 ⇒ 白写。
- **只写静态标识**：plan_id / session_id / spec_path / plan_path。绝不写 600 字摘要、状态、阶段内容（动态走 session_summary.md；状态走 runs/routes/tasks）。
- **session_id 有实际用途**：读侧 `_ultrawork_status` 用它解析该 plan 创建会话的 run 状态；缺失可能导致 `<status>` 保守回退 `pending`。
- **当前无宿主自动接线**（截至 2026-09-13）：全机检索（主检出 + 8 个 worktree），`upsert_ultrawork_for_memory` 除模块自身与单测外无生产调用方 ⇒ 由运行 UW 流程的 agent/操作者按第 2 节触发点显式注入；接线落地后本技能用于校验/回填。
- 本机无 sqlite3 CLI：直查用 python（见第 6 节）。

## 6. 验证

```bash
# a) helper 读回
python - <<'PY'
import sys
sys.path.insert(0, r"<HERMES_HOME>\hermes-agent")
from hermes_cli.workflow_memory_tables import read_ultrawork_for_memory as read_row
print(read_row("<plan-id>"))
PY

# b) 直查（只读）
python - <<'PY'
import sqlite3, os
p = os.path.expandvars(r"%LOCALAPPDATA%\hermes\kanban.db")
con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
print(con.execute("SELECT * FROM ultrawork_for_memory WHERE plan_id=?", ("<plan-id>",)).fetchall())
PY
```

c) 端到端：在同时设置 `HERMES_ULTRAWORK_PLAN_ID` + 合法 `HERMES_ULTRAWORK_PHASE_INDEX` 的会话跑一轮 → 下一轮注入应含 `<ultrawork>` 块，`<id>`=<plan_id>，`<spec-path>`/`<path>` 为写入值（未写入则为空标签）。

## 7. 契约锚点

- 写入 API：`HERMES_HOME\hermes-agent\hermes_cli\workflow_memory_tables.py`（`upsert_ultrawork_for_memory` / `read_ultrawork_for_memory` / `ensure_tables`）。
- 读侧：repo `plugin/lancedb/workflow_projection.py`（`active_workflow` / `_ultrawork_xml` / `_ultrawork_status`；渲染前提行474-476）。
- 流程：skill `ultrawork`（Plan Contract：`resource/plan/<title>.md`）。规格来自 DI 时，先按 skill `deep-interview-for-memory-injection` 补齐 DI 行。
- 需求：`记忆最新需求2.md` 行237-238（env 传递）、行282-299（静态/动态与 Phase 结构）。
