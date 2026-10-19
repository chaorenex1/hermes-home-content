---
name: deep-interview-for-memory-injection
description: "Use when a deep-interview starts or its spec is approved."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [deep-interview, memory, kanban, injection, dynamic-context, lancedb]
    related_skills: [deep-interview-planning-workflows, ultrawork-for-memory-injection]
---

# Deep Interview → deep_interview_for_memory 静态信息注入（教程）

适用范围：deep-interview 模式 / DI 工作流进行中（会话 env `HERMES_DEEP_INTERVIEW_ID` 存在时）。
目标：在两个触发点向 kanban.db 的 `deep_interview_for_memory` 写入/补全**静态行**；动态内容永不写本表。

## 1. 这张表的作用（为什么注入）

- 记忆插件（hermes-lancedb-memory provider）在每轮 `pre_llm_call` 组装 `<dynamic-context>` 时，从 kanban.db 读取静态标识并渲染：
  - `<deep-interview>` 块 = `<deep-interview-id>`（来自本表行/env）+ `<goals>`（来自 `deep_interview_goals` 表，四组状态；无行为空容器）+ `<spec><path>`（本表 `spec_path` 非空时才渲染）。
- 插件读侧为只读（`mode=ro`）；缺库/缺表/缺行/空字段 ⇒ 整个块省略、绝不抛错。
- 需求合同（记忆最新需求2 行269-281）：静态 = deep-interview-id（启动时产生）+ spec-path（审核通过生成规格后产生）；动态 = 辩证推理产出的 600 字 `session_summary.md`（只读 session 布局，不在本表）。

## 2. 触发点（什么时候注入）

1. **Interview 启动、deep-interview-id 产生时**：
   `upsert(interview_id=<id>, session_id=<当前会话>, spec_path=None)`
2. **规格审核通过、生成规格文件后**：
   同一 `interview_id` 再次 upsert，补 `spec_path`（规格规范位置：`HERMES_HOME/lancedb-memory/resource/spec/<title>.md`，以流程实际给出的路径为准）。

幂等安全：`None` 字段不覆盖旧值（COALESCE 语义）；`created_at` 保留首次时间、`updated_at` 每次刷新。

## 3. 注入方法（首选：宿主 helper）

```bash
python - <<'PY'
import sys
sys.path.insert(0, r"<HERMES_HOME>\hermes-agent")  # HERMES_HOME\hermes-agent
from hermes_cli.workflow_memory_tables import upsert_deep_interview_for_memory

row = upsert_deep_interview_for_memory(
    interview_id="<deep-interview-id>",   # 必填、非空
    session_id="<session-id>",            # 可选；建议给（可追溯）
    spec_path=None,                       # 规格出来后再传；None 不覆盖旧值
)
print(row)
PY
```

- 落库解析（写入侧）：`HERMES_KANBAN_DB`（宿主已注入 worker 环境）→ 否则当前看板 → default 板 = `<HERMES_HOME>/kanban.db`；命名看板 = `<HERMES_HOME>/kanban/boards/<slug>/kanban.db`。仅测试/跨库时传 `db_path=...`。
- helper 自带 `ensure_tables`（缺表自动建）、RFC3339 UTC `Z` 时间戳（秒精度）、busy_timeout=120s，返回落库行。

## 4. 兜底：等价 SQL（仅当 helper 不可导入；表已存在时）

```sql
INSERT INTO deep_interview_for_memory(interview_id, session_id, spec_path, created_at, updated_at)
VALUES (:id, :sid, :spec, :now, :now)
ON CONFLICT(interview_id) DO UPDATE SET
  session_id = COALESCE(excluded.session_id, deep_interview_for_memory.session_id),
  spec_path  = COALESCE(excluded.spec_path,  deep_interview_for_memory.spec_path),
  updated_at = excluded.updated_at;
```

`:now` = `%Y-%m-%dT%H:%M:%SZ`。切勿另写 schema（列固定，由 helper 的 ensure_tables 维护）。

## 5. 陷阱

- **渲染由 env 驱动**：注入是否出现取决于任务会话 env `HERMES_DEEP_INTERVIEW_ID`（读侧锚点 `plugin/lancedb/workflow_projection.py:191`）。env 未设置 ⇒ 行存在也不渲染。写入的 id 必须与流程后续导出的 env id 完全一致（勿改写、勿截断）。
- **写读同库**：插件读序 = `HERMES_KANBAN_DB` → `HERMES_HOME/kanban.db` → `<hermes_home>/kanban.db`。与写入端不一致 ⇒ 白写。
- **只写静态**：interview_id / session_id / spec_path。绝不写 summary、状态、轮次快照（那些走 `deep_interview_goals` 与 session_summary.md）。
- **当前无宿主自动接线**（截至 2026-09-13）：全机检索主检出 + 8 个 worktree，`upsert_deep_interview_for_memory` 除模块自身与单测外无生产调用方 ⇒ 由运行 DI 流程的 agent/操作者按第 2 节触发点显式注入；接线落地后本技能用于校验/回填。
- 本机无 sqlite3 CLI：直查用 python（见第 6 节）。
- 与插件私有库（memory.db / session-context.db）无关：本表只存在于 kanban.db。

## 6. 验证

```bash
# a) helper 读回
python - <<'PY'
import sys
sys.path.insert(0, r"<HERMES_HOME>\hermes-agent")
from hermes_cli.workflow_memory_tables import read_deep_interview_for_memory as read_row
print(read_row("<id>"))
PY

# b) 直查（只读）
python - <<'PY'
import sqlite3, os
p = os.path.expandvars(r"%LOCALAPPDATA%\hermes\kanban.db")
con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
print(con.execute("SELECT * FROM deep_interview_for_memory WHERE interview_id=?", ("<id>",)).fetchall())
PY
```

c) 端到端：在设置 `HERMES_DEEP_INTERVIEW_ID` 的会话跑一轮 → 下一轮注入应含 `<deep-interview>` 块（id 必有；spec_path 有则含 `<spec><path>…</path></spec>`）。

## 7. 契约锚点

- 写入 API：`HERMES_HOME\hermes-agent\hermes_cli\workflow_memory_tables.py`（`upsert_deep_interview_for_memory` / `read_deep_interview_for_memory` / `ensure_tables`；模块 docstring 即宿主合同）。
- 读侧：repo `plugin/lancedb/workflow_projection.py`（`active_workflow` / `_deep_interview_xml`）。
- 流程：skill `deep-interview-planning-workflows`（DI 合同与规格路径）。DI→Ultrawork 交接时按 skill `ultrawork-for-memory-injection` 写 UW 行。
- 需求：`记忆最新需求2.md` 行218-223（<deep-interview> 块结构）、行237-238（env 传递）、行269-281（静态/动态分工）。
