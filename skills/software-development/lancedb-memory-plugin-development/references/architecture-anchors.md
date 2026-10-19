# Architecture anchors (re-verify against live code; this repo moves fast)

## Storage layout (HERMES_HOME/lancedb-memory/)

```text
contexts/<profile>/<session>/            current-focus.md, current-progress.md, future-needs.md,
                                         session_summary.md, ai_self_representation.md,
                                         ai_identity_card.md, user_representation.md, user_peer_card.md
contexts/<profile>/ultrawork/<PLAN_ID>/<PHASE_INDEX>/   sections + plan.md, todo.md
contexts/<profile>/deep-interview/<INTERVIEW_ID>/       sections
agents/<profile>/identity.md, preference.md   profile-local AI identity/preference
identity.md, preference.md                    provider user identity/preference
prompts/            profile-local prompt templates (seeded once; never overwritten on initialize)
memory.db           jobs / metadata / control state (never body content)
session-context.db  dynamic_turn_jobs, session_dynamic_state, compression_records
writer.lock, manifest.json
```

Logical accepted paths map directly below `lancedb-memory/`; SQLite is never body authority.

## Dynamic pipeline (all three modes)

- `CommonDynamicPipeline`: D1 (cold when generation==0, else warm) → D2 → D3 → `dynamic-final`;
  final output validated as `lancedb-dynamic-result/v1` (sections c-f/c-p/f-n, synthesis ≤600).
- Commit = `SessionStateRepository.commit_generation`: CAS before the FIRST mutation, atomic
  os.replace of exactly 4 prepared files (3 sections + `session_summary.md` = receipt synthesis),
  generation +1 exactly once. Do not add a second generation owner.
- Cold D1 must delegate `base-refresh` via `kb_subagent`; warm D1 must delegate `memory-retrieval`.
  Missing delegation fails closed. Each stage's session_summary candidate comes from its own
  `candidate.summary` output.
- Window = RFC3339 UTC `(start_time, end_time]`; `end_time` frozen at turn finalization;
  no message high-watermarks or compound cursors.

## Base refresh vs Dynamic ownership

- Base refresh publishes ONLY the four cards; it never writes `session_summary.md` and takes no
  dynamic synthesis input.
- The Common Dynamic pipeline is the sole publisher of `session_summary.md`
  (`contexts/<profile>/<session>/session_summary.md`, ≤600 chars, `dynamic-synthesis-core` template).
- Compression consumes the published summary; it never writes it.

## Injection and projection

- `pre_llm_call` is the ONLY Dynamic injection point; `prefetch()` returns `""`. One
  `<dynamic-context>` block: optional `<ultrawork>`/`<deep-interview>`, always `<session-context>`
  (summary + user-representation + user-peer-card). Section bodies are never injected.
  A citation-feedback instruction (hidden `<kb-citations>` tag request) is appended.
- `workflow_projection.py` reads kanban.db READ-ONLY (`mode=ro`) from
  `deep_interview_for_memory` / `ultrawork_for_memory` (host-written static rows
  `interview_id/session_id/spec_path[/plan_path]`); missing db/table/row ⇒ omit the block, never raise.
- `HERMES_ULTRAWORK_PHASE_INDEX` (gateway session env preferred, `os.environ` fallback) selects the
  ultrawork phase directory; empty/invalid ⇒ omit the ultrawork block.
- `<ultrawork>` 的 `<status>` 来源序（只读 kanban.db）：`ultrawork_kanban_runs.status` →
  `ultrawork_kanban_routes.status` → `tasks.status`，映射 done/in-progress/pending/blocked；
  无法判定保守 `pending`。`<deep-interview>` 的 `<goals>` 来自 `deep_interview_goals`
  （status 分四组容器；无行=空容器，不虚构）。

## Env and host glue

- Task-local env: `HERMES_SESSION_MODE`, `HERMES_ULTRAWORK_PLAN_ID`, `HERMES_ULTRAWORK_PHASE_INDEX`,
  `HERMES_DEEP_INTERVIEW_ID`, `HERMES_KANBAN_DB`.
- Host turn finalizer calls `MemoryManager.sync_all(...)` with an epoch-FLOAT `completed_at`;
  the provider normalizes it to RFC3339 UTC `Z` (`_frozen_completion_time`) before freezing the
  window. Host filters kwargs by provider signature.

## Config keys (lancedb namespace)

- `observationMode`: `directional|self`, default `directional` (read scope only, never write scope).
- `boundedMessagesMode`: `all|self`, default `self` (message-body exposure to agents).
- `agents.<route>.{provider,model,persist_session}` for extraction/dialectical/retrieval.

## kb tool surface

`kb_tree`, `kb_search` (content matches + directory/file-path three-state hits), `kb_read` (default
200 lines; zero hash fields by default — `include_content_hashes=true` explicitly returns
`full_content_hash`=sha256(current bytes), the only token source for managed-doc delete CAS),
`kb_file` (create_dir/create_file/rename/move/copy/delete [delete_path kept as alias]/
patch_file with line-level insert/update/delete operations; never able to delete the authority
root), `kb_reasoning`,
`kb_profile` (cross-profile full reads allowed), `kb_context` (5-doc session context),
`kb_summary_search` (ripgrep excerpts), `kb_subagent` (delegation), `kb_mode`, `kb_feedback`
(9 whitelisted targets, replace-after-kb_profile; automatic agents cannot use it to bypass
write targets).

## Layer trigger model (counters + cadence — re-verify against live code)

- 需求行10-20/34 的“基础层/辩证推理层轮数计数 + 触发轮数倍数门控 + 触发台账”已在修复轮落地：
  `session-context.db` 新增 `session_layer_counters`（base_turns/dialectic_turns/counting/
  started_at/stopped_at）与 `context_layer_triggers`；`sync_turn` 以 `base_due or dialectic_due`
  （各自 `context.cadence_turns` / `dialectical.cadence_turns`，默认 1 ≡ 每轮，门控仍生效）
  决定是否入队。
- `on_session_end`（provider 入口）停计数 + 按“倍数去重”触发一次辩证；`on_pre_compress` 同规则，
  并把触发窗口作为返回文本交给压缩；`compress` 触发辩证推理并消费 [上轮辩证触发时间 →
  `compression_records.recorded_at`] 窗口（同时保持 Task Handoff 模板且不写 `session_summary.md`）。
- 通用钩子 `on_session_end` / `on_session_finalize` 保持 telemetry-only 是 host 语义下的既定分工
  （host 每 `run_conversation` 触发通用钩子；真实会话边界 = `MemoryProvider.on_session_end`）——
  审计判“最终行为”在哪层发生，不判钩子名；`system_prompt_block` / `on_pre_compress` 是 provider
  方法，注册钩子集合仍为 `register_lifecycle_hooks` 的 7 个。
- 计划里的旧名 `lifecycle_sessions` / `context_trigger_records` / `TriggerRequest` 从未落地，
  当前实现用上表新名；需求构造物零命中 = 修复项，不得以“代际残留”豁免。`context_turn_jobs` /
  `context_scope_state` / `dialectical_init_claims` 为 schema-only DDL；`context_generations` /
  `context_artifacts` 仍被 review 模块使用。
- 底层触发模型保留：每个完成主回合入队一个 Dynamic job（窗口 `(last_committed_window_end,
  frozen_cutoff]`，`commit_generation` CAS 提交）——cadence=1 时与旧“每轮”行为一致。
