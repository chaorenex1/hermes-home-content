# Meta-Plan Pattern: Patch-Sequence for Plan Updates

This file is a concrete worked example of the meta-plan technique, extracted from the
`lancedb-hermes.md` update session. Use it as a template when writing Ralph-mode meta-plans.

## The Pattern in 30 Seconds

1. Read the target plan → identify sections that need changing
2. Read the authoritative sources → extract exact diffs
3. Build a gap→patch mapping table
4. For each patch: old_string (verbatim from target), new_string, verify command, failure recovery
5. Add blocking conditions and a consistency review checklist
6. Order patches sequentially (inserts shift line numbers of later patches)

## Worked Example: Gap Table

```
| # | Target Lines | Operation | Evidence Trigger |
|---|-------------|-----------|-----------------|
| P1 | L15 (§1 bullet 1) | replace | ABC has 15 hooks, plan lists 5 |
| P2 | L17 (§1 bullet 3) | replace | ABC initialize() kwargs incomplete |
| P2a | L25-71 (§2 data model) | append | User specified directory topology |
| P3 | L93 (§4.1 entry) | replace | Docs: ctx.register_memory_provider() |
| P4 | L114-120 (§4.3 hooks) | bulk replace | ABC added 5 new hooks |
| P5 | L128-157 (§5 config) | append | LanceDB v0.35 API changes |
```

## Worked Example: Patch Specification

Each patch entry:

```markdown
## P2a: Update §2 — Directory Topology

**Target:** L25-71 (§2.0 header + §2.1 constraints + §2.2 source_type)

**Operation 1 — Insert §2.0:**

**old_string:**
## 2. 目标数据模型

### 2.1 `nodes` 表：目录树

**new_string:**
## 2. 目标数据模型

### 2.0 预定义知识库目录拓扑
[ASCII tree + depth constraint table here]

### 2.1 `nodes` 表：目录树

**Verification:** `read_file(offset=25, limit=10)` → output must contain "### 2.0"
**Failure recovery:** If patch fails, `read_file(offset=23, limit=5)` to confirm actual text, adjust old_string, retry (max 2).
```

## Worked Example: Consistency Review Checklist

```markdown
| Check | Method | Pass Criterion |
|-------|--------|---------------|
| No `~/.hermes` hardcoded | `search_files(pattern="~/\.hermes")` | 0 results |
| No stale `register(ctx)` calls | `search_files(pattern="register\\(ctx\\)")` | 0 results (except meta-plan) |
| Hook name appears ≥3 times | `search_files(pattern="on_turn_start")` | ≥ 3 occurrences |
| LanceDB version pin consistent | `search_files(pattern="lancedb>=0\\.17")` | ≥ 2 occurrences |
```

## Worked Example: Blocking Conditions

```markdown
**Blocking conditions (stop ALL subsequent patches):**
1. Any patch returns `error` → stop, report patch # and error message
2. Verification `read_file` doesn't contain expected text → stop, report missing keyword
3. Consistency review finds contradiction → stop, report exact line and mismatch
```

## When the Ralph Loop Rejects

| Rejection text | What it means | Fix |
|---------------|---------------|-----|
| "does not present a concrete, ordered implementation plan" | Missing patch-level granularity | Add old_string/new_string to every task |
| "尚未证明计划包含可执行的验证命令" | Missing verification commands | Add read_file calls with expected output |
| "没有明确的阻塞条件、停止条件" | Missing blocker/stop conditions | Add blocking conditions section |
| "未具体列出每项任务将修改的文件/组件" | Missing file paths and line ranges | Add Target: L[N] to every patch |

## Reuse Checklist

Before applying this pattern to a new plan-update task:
- [ ] Target plan fully read (all sections to be touched)
- [ ] Authoritative sources read (ABC source, docs, user requirements)
- [ ] Gap table complete (one row per change)
- [ ] Each patch has old_string (from read_file), new_string, verify command, failure recovery
- [ ] Blocking conditions specified
- [ ] Consistency review checklist has ≥5 checks
- [ ] Patches ordered (inserts before appends)
- [ ] Risk table addresses line drift and old_string mismatch
