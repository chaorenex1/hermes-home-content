---
name: lancedb-memory-plugin-development
description: "Develop, verify, and log-diagnose the hermes-lancedb-memory / minir-memory plugin repo."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [hermes, lancedb, memory-provider, plugin, kanban, acceptance]
---

# LanceDB Memory Plugin Development

Use when implementing, fixing, or verifying the user's file-authoritative memory provider
(`hermes-lancedb-memory`). The repo is developed over many rounds driven by spec documents and
short user rulings; this skill is the stable workflow across those rounds.
See `references/architecture-anchors.md` for the domain map (paths, DBs, pipeline contracts,
env vars) — re-verify anchors against live code before relying on them. For a live
"检查Hermes日志/报错" request follow `references/log-triage.md` (pass order, signature table,
benign-noise list, report shape).

## 1. Decide which tree you are editing (do this FIRST)

- Resolve the live names first: the provider may live in the successor repo
  `<USER_HOME>\projects\minir-memory` as package `plugin/minir`, installed at
  `$HERMES_HOME\plugins\minir`, instead of `hermes-lancedb-memory`/`plugins/lancedb`. List the
  repo root and `$HERMES_HOME\plugins`, then substitute the actual repo/package/deployed names
  in every command below; never patch the installed copy in place of the repo.
- "当前仓库" / implementation requests mean the **dev repo** `<USER_HOME>\projects\hermes-lancedb-memory` (git master). Implement there.
- `%LOCALAPPDATA%\hermes\plugins\lancedb` (or `plugins/minir` in the minir generation) is the **deployed copy** the running Hermes imports. It lags the repo and can mix code generations — do not patch it in place of the repo, and do not treat its files as the source of truth.
- `%LOCALAPPDATA%\hermes\hermes-agent` carries the **host** contract (sync_turn, turn finalizer, session env) — largely locally-modified/untracked WIP. Plugin agents receive Host toolsets ONLY via the facade `bind(toolsets=...)` channel (private tool names go through `tools=`); a green repo suite does not prove this seam — fixtures fake the facade (repo fakes supply `_plugin_id="memory/lancedb"` while the real `PluginAgentFacade` holds only `_identity`, so plugin-agent kb_* calls refuse with `plugin Agent context belongs to another plugin`; probe the real classes with `scripts/host_facade_probe.py` before touching plugin code). Keep host edits minimal and record them under `$HERMES_HOME\patches\hermes-agent\` as a `<date>-<topic>.md` note (diff + evidence + tests + replay hint) plus a full-file `<name>.py.patched-<date>` copy; run the affected host test files (`hermes-agent/venv/Scripts/python -m pytest <paths> -q`) before/after and include the raw counts in the note; see `references/real-host-integration.md`.
- Deployment (only on an explicit request) = `python scripts/install_dev_plugin.py --target-hermes-home <HERMES_HOME> --replace` → verify deployed tree == repo tree (sha256 manifest, caches excluded; run this skill's `scripts/tree_parity_check.py <src> <dst…>` for the walk — it also accepts profile copies as targets) → mirror to named profiles (`$HERMES_HOME/scripts/sync_default_profile_extensions.py`; the gateway-down cron never fires) → `hermes gateway restart` → one-shot smoke (`hermes chat -q "Reply with exactly: PROBE_OK" --oneshot`) then read `$HERMES_HOME/logs/{agent,errors}.log`. A skills-side `post-mirror verification failed` on some profiles is usually the live `.usage.json`/`.bundled_manifest` mtime race — content sha decides, do not chase it. Full chain, verification probes, and failure signatures: `references/real-host-integration.md`.
- minir 代际部署（`plugin/minir`，无 install_dev_plugin.py 时）：同步 `plugin/minir` 源文件到
  `$HERMES_HOME\plugins\minir`、删目标 `__pycache__`、逐文件 sha256 对齐；`hermes plugins validate`
  与 `doctor` 通过后 `hermes gateway restart`，再确认新 PID 占用 API 端口（restart 会短暂提示旧端口
  仍在监听，不要据此重跑）；`scripts/verify_against_host.py` 必须显式传 `--host-python` 与
  `--workspace`，自动探测在宿主外会失败。
- After a deploy, long-running host processes (TUI host, Desktop backends, gateways) keep executing the
  PREVIOUS generation from memory — Python never reloads. Symptoms in `logs/agent.log`/`errors.log`:
  the `...lancedb__source_<digest>.lifecycle_hooks: lancedb lifecycle store unavailable` flood +
  `SchemaVerificationError: database schema is newer than this provider` (DB migrated by the new
  generation while the old one runs), and `Hook 'post_tool_call' callback callback skipped after
  previous timeout...` (old generation registers hooks via a nested `def callback`; the current one
  registers bound methods) — a skip line naming a REAL callback (e.g. `post_tool_call`) is NOT this
  class: it is a live stuck/slow callback; attribute it by registrant (`references/log-triage.md`).
  `<digest>` = sha256(resolved `$HERMES_HOME/plugins/lancedb`)[:16] — proves
  the load path. Attribute the emitter by walking your shell's parent chain to the hosting python.exe
  and compare its start time against the deploy times. A restart of the stale host is the fix; verify
  the deployed tree == repo tree (`diff -rq`, __pycache__ excluded) before blaming current code.

## 2. Read the spec stack before implementing

- `Documents\记忆最新需求2.md` — current requirements (semantics authority).
- `Documents\记忆最新需求2-执行计划.md` — WP execution plan + progress table; **its progress column lags reality** (written before rounds land, not kept current) — treat it as leads/history and verify status against the workspace and commits.
- Repo `.omx/plans/lancedb-memory-session-context-engine-plan.md` — meta-plan; its audit tables mix two code generations — re-verify every claim against live code before trusting a row.
- Short, terse user messages ("X 所有权：Y") are rulings: implement exactly on the dev repo, add regression tests around the changed contract, and note any doc/ruling conflict in the final report instead of silently picking a side.

## 3. Test harness

- `cd <repo> && python -m pytest tests -q -p no:cacheprovider` — use whichever interpreter actually has pytest: the system Python (3.14) on the old repo, the host Hermes venv python on minir-memory (verified there as `python -m pytest tests -q`). Confirm with `python -c "import pytest"` instead of assuming from `.venv`. Add `--continue-on-collection-errors` when a collection error may exist.
- Full suite size and runtime grow each round; read the collected count from the run instead of trusting a fixed number. 2 symlink skips are environmental and normal. Focused files first, full suite last — never claim acceptance without the full run.
- CI-free repo: the suite IS the acceptance gate.

## 4. Contract-change sweep (the failure this repo punishes)

When renaming a contract, moving ownership, or changing an API/DB/file shape:

1. BEFORE edits: `rg -n --no-ignore "<old term>" <repo>` WITHOUT `-g '*.py'`. Contract text lives in Python, prompt-template strings, `skills/*/SKILL.md`, tests, and README.
2. **`skills/*/SKILL.md` are runtime-registered instructions** (registered via `ctx.register_skill`, injected into background provider agents) — stale wording there is a live defect, not a doc nit. Prompt-template strings are the same class of artifact.
3. Change every layer: module code → prompt templates → skills/*/SKILL.md → README → tests.
4. AFTER edits: grep the TEST TREE for every changed symbol (`commit_generation`, `prepare_files`, `refresh(`, `dynamic_target_paths`, …) — hand-rolled fixtures/mocks reimplement the old shape and fail only on shards you did not run. Exact-shape assertions (`assert result == {...}`, `assert_called_once_with(...)`, "<term> not in hint" checks) also encode the old contract — grow them in the same change whenever a payload key, signature, or hint string is added.
5. Finish with focused tests, then the full suite, plus residual-wording greps; expect an independent verifier to check wording too.

## 4c. PluginAgent 接缝（context-run gate）修复配方（2026-09-13 实证）

- `resolve_context_run` 的拒绝对可叠加出现，必须用**真实宿主对象**逐项验证，不能只看第一条错误：
  `plugin_id`（宿主门面须暴露 `_plugin_id = identity.plugin_id`）→ `purpose`（envelope purpose 必须等于注册 purpose；
  插件 adapter 的 `handle.run` 必须透传 `purpose=`，宿主 `PluginAgentHandle.run/arun` 有该形参并回退 bind purpose）→
  `host_session_id`（注册 workflow bundle 必须携带 `session_id`，且运行 envelope 传入同一值）→
  `attempt_id`（同上）。修复一层会暴露下一层，按此顺序一次排查完。
- 参照实现＝flows（`agent_context_runtime` 的 flow runner）：`runtime_bundle["session_id"]=host_session_id`、
  `runtime_bundle["attempt_id"]=attempt_id` 后才 `register_context_run`；`agent_pipeline`/`profile_review` 等
  落后应向其对齐（bundle 补键，而非改 guard）。
- 宿主机验证：宿主 venv 直接构造 `PluginRuntimeServices(PluginIdentity(...)).agent` 检查门面属性；
  repo 侧 fakes 自带 `_plugin_id` 会掩盖真实门面缺口（"绿套件不证明宿主接缝"的又一实例）。
- end-to-end 复证：one-shot 宿主机保活跑 job——`hermes chat -q 'Use the terminal tool to run exactly: python -c "import time; time.sleep(150)"...' --oneshot`
  可在进程存活期捕捉 job 会话的 kb 工具成败；新代码信号＝`provider.tool_metric tool=kb_* success=True`
  （旧代码=invalid_arguments 拒绝），写完盘信号＝`lancedb-memory/<type>/summary.md` 等文件 mtime 更新。
- workflow 文件边界 guard（`_enforce_workflow_file_boundary`）必须同时解析 **现代 `operation=` 形态与 legacy
  `mode=` 形态**；否则 summary/extraction agent 的现代调用被误判 permission_denied（"write path is invalid"）。
- 每条修复配 regression：adapter purpose 透传（fake handle 断言）、pipeline bundle 键、guard 双形态；
  精确形状断言（`assert workflow_runtime == {...}`、handle 签名集合）要在同一变更里扩展，否则全量套件报红。
- kb 工具集 runner 对齐清单（seam 修复/审计轮后必扫）：`grep -n KB_AGENT_TOOLSETS plugin/lancedb/*.py`
  列出的每个 `agent.run(` 点必须同时有 `register_context_run(...) as run_id` + `tool_context={"context_run_id": run_id}`
  + workflow bundle 与 run 的 `host_session_id`/`attempt_id` 一致；漏掉的 runner（实证：`quality_agent.py`、
  `reasoning.py` 的 kb_reasoning）让该 agent 的**全部** kb_* 调用以
  `invalid_arguments: "plugin Agent context payload is invalid"` 被拒（tool_context=None 落在 `resolve_context_run`
  第 2 层 payload 校验）——症状像宿主 bug，其实是 runner 漏注册。job 型 runner 的 run_id 取
  `attempt["context_run_id"]`（call site job dict 补键，与 `bind_job_operation_store` 的 run_id 对齐）；
  kb_reasoning 经 `KnowledgeReasoner(..., session_id, profile_name)` 携带会话/档案。注册后语义：context 读
  （kb_summary_search/kb_context）按 `bound_profile_name` 做 self-scope；文件工具在未授权 purpose 下报
  `this Context Agent phase has no file-memory authority`（按设计，非 bug）。死代码 `ProfileReviewPipeline`
  （profile_review.py，无实例化点）可忽略。

## 4d. 宿主 durable boundary outbox 契约（deferred 边界投递）

- 宿主 run_agent 把 session 边界（shutdown/compression/new_session）写入 state.db `memory_boundary_outbox`，先内联投递，
  失败由后台 worker 以 ≤60s 退避重投（`agent/memory_boundary_outbox.py`）；投递携带**事件自身的** `parent_session_id`，
  跨进程/跨会话重放是设计内行为（延迟投递必然发生在旧会话不再是 live binding 之后）。
- 插件侧 on_session_end/on_session_switch 不得用 live binding 校验（`_bound_session`）拒绝事件会话，否则事件永久搁浅：
  实证 14 条事件 attempts 868–1893、每 ~60s 一次 ValueError 堆栈（`_bound_session` raise "does not match the active Provider session"）。
  正确语义＝事件会话为权威：expire 该会话 working set、stop 该会话计数、按该会话 counters 行的 scope/mode 触发辩证推理
  （`_boundary_session` / `_boundary_turn_number` / `_enqueue_dialectic_reasoning(counters=...)`）。
- deferred on_session_switch 只做旧 scope 过期＋事件 id 记录，**不得重绑** live session；内联路径（parent==bound）保持原重绑行为。
- 自检：`rg -n "_bound_session" plugin/lancedb/__init__.py` 只应命中 live 表面（working_scope/set_session_mode/on_turn_start/compress_context）。
- 回归：`tests/test_boundary_deferred_delivery.py`（deferred end/switch、unknown session no-op、inline 重绑回归）。
- 宿主接缝探针：`scripts/boundary_outbox_probe.py`（用宿主真实 `_build_session_end_kwargs`/`deliver_memory_boundary_event`
  驱动修复后的插件——延迟 end 必须停计数+产 1 条触发、延迟 switch 不得重绑、重放必须被接受；FAILURES 为空才算过）。
- 探针/测试的 Windows 陷阱：provider 会一直持有 `memory.db` 句柄，`tempfile.TemporaryDirectory` 清理必报
  WinError 32 —— 用 `mkdtemp` + `shutil.rmtree(ignore_errors=True)`，并在 finally 里 best-effort `provider.shutdown()`。
- 部署前修复不生效：部署副本仍为旧代际，搁浅事件继续 ≤60s 重投刷 DEBUG 堆栈；部署后积压被消费一次
  （无 counters 行的旧会话 `stop_session` 返回 None → 干净 no-op，不会凭空造数）。

## 5. Repo editing pitfalls

- `plugin/lancedb/__init__.py` is ~130 KB / ~3000 lines: patch surgical regions only; re-read the file (or the region) before patching after any other actor may have touched it.
- Files are CRLF; the patch tool normalizes endings. After an edit confirm with `git diff --stat` that the change is the intended line delta, not a whole-file rewrite.
- Never edit `build/` (stale package copies) and exclude it from greps.
- Do not commit unless asked; large uncommitted working trees are normal here. Keep each actor on a mutually exclusive file set when several run in parallel.

## 6c. Repair rounds (checklist-driven waves, proven)

- Build waves by mutually exclusive FILE whitelists; every card carries the same global rules
  (requirements doc = acceptance baseline, only-whitelist, no commit/stash, focused tests only).
- Chain: workers -> verifier (qa1 must emit metadata.gate) -> synthesizer (cto). With the gateway
  down, run a bounded background dispatch loop (`hermes kanban dispatch` every 120s; exit on
  terminal synthesizer) — nothing auto-promotes without it.
- Fleet reroute when every worker blocks instantly: read $HERMES_HOME/kanban/logs/<task>.log — an
  HTTP 403/quota error is a provider fault. Probe the replacement lane with the exact worker argv
  (`hermes -p dev1 --cli -m <model> --provider <provider> chat -q "Reply with exactly: PROBE_OK"`),
  then `hermes kanban set-model <id> <model> --provider <provider>` on EVERY card of the graph,
  `hermes kanban unblock <id> <reason>` on blocked ones, and one dispatch pass.
- gate=fail handling: contain the running synthesizer immediately (`hermes kanban block <id>
  <reason>`; `block` takes a positional reason), then create the bounded chain
  rework -> replacement QA -> fresh synthesizer and record recovery on the root blackboard. The
  rework card may span multiple whitelists (it is the only active writer then).
- Cross-worker handoff pitfall: a worker that finishes earlier never sees a later sibling's root
  comment (this round: the template-consumption note arrived 90s after W2 completed -> follow-up
  dev+QA chain). After every wave, audit ALL root comments for unhandled cross-whitelist notes.
- Orchestrator closes with its own full-suite rerun plus a git-status/HEAD check before reporting,
  and reports the raw counts from its own run (expected magnitude ~490 passed, 0 failed, 2 env symlink skips).

## 7. Acceptance pattern (user's established standard)

- Deliverable = dev-repo change + full suite 0 failed + targeted probes per changed contract; report evidence (commands + raw results), not claims.
- Work is tracked as Kanban cards with `--workspace dir:<repo>` and a no-commit rule; verifier profiles qa1/qa2, synthesizer cto. See the `kanban-orchestrator` skill for swarm mechanics (provider reroute on worker crashes, manual dispatch when the gateway is down, replacement-QA rework).
- Swarm wiring for this repo: workspace `dir:<repo>` + no-commit on every card. `hermes kanban swarm` auto-attaches `requesting-code-review` (verifier) and `humanizer` (synthesizer) — verify they load for qa1/cto's real skills tree first (`.archive/` copies don't count), otherwise build the graph via the board Python API: root(`initial_status="blocked"`) → workers(`parents=[root]`, `goal_mode=True`, full brief in body) → verifier(`parents=<all workers>`) → synthesizer(`parents=[verifier]`); activate with `complete_task(root)`; post `[swarm:blackboard]` topology/contract notes; read every card back before dispatching.
- Gateway-down chains need a bounded dispatch loop: nothing auto-promotes the verifier/synthesizer after workers finish. Run `hermes kanban dispatch` every ~120s in a background loop with a per-card status script; exit when the terminal card is done/blocked and nothing is running; restart the loop after any reroute. From bash, give Windows `python.exe` `C:/...`-style paths (MSYS `/c/...` gets mangled to `C:\c\...`); after starting the loop confirm its first status line landed in the log — a broken logger leaves the dispatcher cycling alone and the exit condition never fires.
- Worker-provider reroute: probe by replicating the worker argv (`hermes -p <profile> --cli -m <model> --provider <provider> chat -q "Reply with exactly: PROBE_OK"`) — that proves profile-scoped resolution end-to-end. Goal-mode workers mask quota faults as `Goal-mode worker exhausted its turn budget ... judge error: PermissionDeniedError`; read `$HERMES_HOME/kanban/logs/<task>.log` for the real 403, then `set-model` every card (workers+verifier+synthesizer) + `unblock` + one dispatch pass.
- Verifier briefs must explicitly require the verifier's `kanban_complete` to carry a JSON `metadata.gate` (`pass`/`fail`) plus `evidence`/`failed_criteria` — verifiers default to prose-only summaries otherwise.
- A narrow gate=fail limited to wording/docs: fix inline, then create one replacement QA card scoped to the rework + full regression; reserve full rework chains for code/semantic failures.
- gate=fail 先冻结在跑的 synthesizer：`hermes kanban block <id> <reason words…>`（reason 是位置参数；`--reason` 会报错；unblock 才用 `--reason`）——native 依赖调度只读任务 status、不读 gate metadata，不冻结就会对失败轮次照常产出“成功”合成。随后按失败项归属建链：返工卡（含失败判据原文+复现步骤）→ 替换 QA 子卡（先复现原缺陷再验修复 + 全量回归）→ 新 synthesizer 子卡；旧卡留档，root 黑板记 recovery（fail 卡/判据/新链 ID）。
- Worker briefs must require completion metadata `{changed_files, tests_run, items_fixed, residuals}`——QA 与合成读它，白话摘要不够。
- 并行轮收尾纪律：采信任何 gate 之前先逐条盘点 root 黑板全部注释，确认每条跨边界交接（worker 请求到他人白名单文件里的后续修复）已被消费——完工早于注释的 worker 看不到它（时序差可低至数十秒），verifier 探针可能不覆盖该缺口；未消费即建有界补齐链（目标文件 owner → 独立 QA + 全量回归），不重开整轮。
- 编排者终验（交付前）：亲自复跑全量套件 + 对每个修复点做默认/显式两态直探，数字与 QA/合成报告三方对齐后才交付。
- Report open items plainly at the end (uncommitted, undeployed, pending host wiring, unrun audits) — the user decides the next round.

## 9. Deep Interview / Ultrawork host contract (integrate branch)

- Host surface (`/deep-interview`): objective | status | show | resume <deep-interview-id> | cancel | subgoal. `pause/stop/done/clear` are deleted by ruling; `resume` rebinds the interview's session to the current one. start/resume set `HERMES_SESSION_MODE=deep-interview` + `HERMES_DEEP_INTERVIEW_ID`; cancel returns mode to `session`. The session-env machinery is IN the integration line (ported from the memory-program WIP + two additions): `gateway.session_context.set_current_session_mode` / `set_current_deep_interview_id` (ContextVar + env mirror, delegated-child suppression) and `scoped_session_env_vars`; `run_agent._resolved_workflow_task_env` (includes `HERMES_SESSION_MODE` beyond the WIP's four names) is rebound task-locally per turn by `agent/turn_facade` — the setting is effective in-process, not a no-op.
- Projection design B (host tables, provider direct read): the host writes `deep_interview_for_memory` rows **inside its kanban write transactions** (`hermes_cli/workflow_memory_tables.py::upsert_deep_interview_for_memory_on`; `projected_goal_state_version` is stamped with the write, `_sync_memory_tables` in `deep_interview_store`). The lancedb plugin's `workflow_projection.load_workflow_projection` reads the tables directly, keyed by `HERMES_DEEP_INTERVIEW_ID`. The provider `publish_deep_interview_projection` channel is optional/best-effort and must never fail-close a turn.
- Tools lane: `interview_state`, `interview_search`, `deep_interview_execute`, `deep_interview_import_plan` (registered on the core list + a `workflow` toolset); `planning_tool_guard` is enforced both at the dispatcher boundary (`model_tools.handle_function_call`) and in `agent/tool_executor._dispatch_authorized_once`.
- `hermes deep-interview` subcommand: start (goal) | status (no goal) | `--resume <deep-interview-id>` --session ...; `cmd_deep_interview` in `hermes_cli/main.py`.
- State: this line is landed on live `main`; the live working tree carries the feature plus the memory-program WIP as unstaged changes (converged via a pre-activation worktree; WIP snapshot / resolved activation patch / backup branch under `$HERMES_HOME\backups\pre-di-activation-*`). The running CLI and Desktop still need a restart to load it.
- Ultrawork 实现面（与 DI 相反：完整体未落 main）：完整实现 = hermes-agent 分支
  `codex/deep-interview-hard-cut-recovery` tip `d40424f256`（用 `git log --all -- <路径>` 复核）——
  `hermes_cli/ultrawork_{commands,planner,source,context,execute,kanban,policy,pr}.py`、
  `hermes_cli/subcommands/ultrawork.py`（main.py `cmd_ultrawork` 接线）、
  `tools/ultrawork_{search,execute,archive}_tool.py`、`plugins/ultrawork-observation-gate/`
  （2-Action Rule 门禁：计数 qualifying 工具调用、第三个前阻塞）、17 个 `tests/**/test_ultrawork*`、
  契约 skill `software-development/ultrawork` + website 文档（skill/文档在 main 上也有）；
  main 仅调用点/CommandDef/env/表定义，模块缺失（`/ultrawork` import 即失败）。
- Ultrawork 数据面：planner 写 `HERMES_HOME/lancedb-memory/resource/plan/`（`<title>-<plan_id前8>.md`）
  + kanban.db `ultrawork_plans`；policy 表 `ultrawork_iteration_loops/ultrawork_iterations/
  ultrawork_file_baselines`（mode ∈ fixed|max|adaptive）；lancedb 插件是读侧消费者：
  `workflow_projection.py` 读 `ultrawork_for_memory`/`ultrawork_kanban_runs`/`ultrawork_kanban_routes`
  渲染 `<ultrawork>` 块，`paths.py::ultrawork_phase_document_path` 算相位文档路径。
- 勿混淆旧代际：`~/projects/ultrawork-swarm-kanban{,-plugin}`（Ralph/Ops 控制器）与被 hard-cut 的
  `backups\*\removed\*\ultrawork-swarm-kanban` 都是旧线，不是现行实现。

## 8. Requirements audits (需求 vs 代码 — the repo's recurring round type)

- 需求文档是唯一验收基线：“需求是基线，不要质疑我的需求”——不提问、不推回裁定、不以“注释声称设计
  演进”把需求排除在判定之外。代码与文档分歧 = 缺陷（partial/violates）+ 修复方向；判定对象是工作区
  (`plugin/lancedb/`、`tests/`，含未提交改动)，不是 git HEAD 或计划进度表。
- 零命中即缺陷：需求要求的构造物在代码中搜不到 = 该条 violates（进修复清单）——不得以“现行代际已换
  模板/被新设计取代”为由放行；`references/architecture-anchors.md` 的旧代际指纹只用于排除死代码名，
  不构成需求豁免。行为若确以他名存在于最终执行路径（hook/provider/工具任一层），按该层判
  conforms/partial 并记录 naming 锚点。
- 判“最终行为”而非“钩子名”：generic `on_session_end`/`on_session_finalize` 钩子为 no-op 属既定
  分工（host 每 `run_conversation` 触发；真实边界=`MemoryProvider.on_session_end`），`prefetch()`
  返回 ""（注入仅 `pre_llm_call`）、compression 不写 `session_summary.md` 均为正确设计；
  `system_prompt_block`/`on_pre_compress` 是 provider 方法而非 7 个注册钩子之一。但需求要求的
  最终行为（停计数/触发辩证推理/范围窗口/落库）在哪层发生就在哪层判：provider 方法里发生=符合；
  哪层都不发生=缺陷——不得用 no-op 注释为其开脱，修复可落在 hook 或 provider 任一处。
- Compare NAMES, not just presence: kb_file's live enum is `delete_path` (+ `insert/update/
  update_lines/delete_lines`, legacy `mode=create|update|delete`) while the requirements say
  `delete` with line ops nested under `patch_file` — report naming/manner drift as partial with
  anchors on both sides.
- 粒度=原子条目：每条 hook / 每个工具模式 / 每个注入元素各一条（~100+ 条）逐条判定——簇级汇总会被
  判“太粗糙”。Verdict per item: conforms | partial | violates（或等价 implemented|partial|
  missing|contradicted）+ `file:line` 证据原文 + covering test + 缺口（需求要求X/代码实际Y）+ 修复
  方向；`missing`/`violates` 必须附实际执行的零命中 grep。Partition the doc by requirement cluster
  for parallel streams; delegated audit streams are self-reports — spot-check their anchors with
  your own greps before synthesis.
- Long grep output is truncated by the terminal to
  `...\hermes\cache\terminal-output\out-*.log` — read that file with read_file instead of
  re-running the command, and batch related greps into one call so a single log read covers
  several checks.
- 审计轮执行配方（编排者会话 + 4 条并行 delegate_task 流；审计本体不进 Kanban——Kanban 是修复轮的载体）：
  1) 框架复用：`%LOCALAPPDATA%\Temp\memory_audit\audit_items_v2.md`（127 条 R 编号 + 需求行号 + H1–H4
  分簇）——复用前核对需求文档未变（mtime）且框架覆盖全文行段（未覆盖行=追加 X 条目）；产物目录被清理则
  按同簇逻辑从文档重derive。
  2) 分簇：H1 钩子/计数触发/压缩/注入结构（R01-R25,R105-R113,R126）｜H2 agent 装配/模式/观察/投影
  （R26-R46,R99-R101,R114-R116,R120）｜H3 路径/improvement/提取检索/记忆类型（R47-R58,R81-R90,
  R121-R125,R127）｜H4 kb 工具/skills/receipt/清理（R59-R80,R91-R95,R96-R98,R102-R104,R117-R119）。
  3) 每簇一条流：内联条目清单（行号+验证提示）+ 判定规则 + 输出路径 `memory_audit\round<N>\h<k>_out.json`；
  条目 JSON={id,requirement,verdict,evidence[],tests[],gap,fix}，收尾用 json.load 验证条目数==分配数（分配数按“独立判定项”口径在框架文件里写死：父项与子项是否分开计数逐条列出，防流按不同口径自检失败）；
  流内硬约束：只读仓库、不跑全量套件（≤3 个焦点测试）、不建 Kanban、不动 %LOCALAPPDATA%\hermes。需求
  文档把 `_` 转义写作 `\_`——在流提示里注明搜索时还原为 `_`。
  4) 同步后台起全量套件（`… | tee <log>`）作全局证据——与流并行，勿串行干等。
  5) 流返回后：每簇 ≥2 条锚点自行 grep 抽查；上轮声明的残余项显式重验（root comments、QA metadata、
  `hermes kanban show <id>`），报告含“上轮声明 X / 本轮判定 Y”对照。
- 并行流“已完成≠已交付”：交付层可能把某条流标为 failed / `Subagent did not produce a response`，而其
  JSON 产物已在磁盘完整落盘并自检通过（最终消息丢失才触发该状态）。收到该类失败先查产物文件与 live
  transcript 尾部：产物存在且可解析（json.load + 条目数==分配数）即视为完成、直接进入抽查/合成，不重派；
  仅产物缺失/不完整/不可解析才重派——重派会重跑整簇，白烧一轮完整审计。流 brief 的完成契约固定三件套：
  写 JSON 产物 → python 读回断言 → 打印一行摘要（把“已完成”与“已交付”解耦，交付层故障不吞产物）。
- Kanban 只读侦查：默认板 DB=`%LOCALAPPDATA%\hermes\kanban.db`（其他板在 `kanban\boards\<slug>\kanban.db`）；
  用 Python sqlite3 只读 URI（`file:…?mode=ro`）查询，`tasks.created_at`=epoch 秒，按 tenant
  `hermes-lancedb-memory` 过滤；`hermes kanban show <id>` 打印 body/comments/summary/runs——卡 body
  即当时的 worker 合同。
- 交付物 = 逐条报告 + 修复清单：每项含需求行号、缺口、修复方向、逐 worker 的文件+测试白名单；修复轮
  直接把清单当 worker 合同（Kanban 卡 body 引用它）。
- 修复轮编排：按互斥文件白名单分 worker；共享热文件（`plugin/lancedb/__init__.py`、
  `prompt_templates.py`）每波只给一个 worker，依赖它的条目降下一波；worker 必须清零“反向断言”
  （断言旧/no-op 行为的测试改为需求行为）并携带覆盖测试交付。
- 需求条款内部张力（如固定路径 vs 按模式切换）按最具体/专门条款实现、对另一条款最大兼容；不得以
  “需求冲突”为由停摆或推回用户。
- 每轮重查、勿凭记忆：全量套件先跑作全局证据（本机 2 个 symlink 环境性 skip 属正常）；`kb_file`
  通用 operations 与 `kb_feedback` 不受 profile 约束（仅权威根边界）——声称写入隔离前先实测。
- 审计对象可以不在工作区：需求实现面可能在 hermes-agent 分支或其他树（例：ultrawork 完整实现只在分支、
  main 仅残片）。用户一句话给出“审计 X”时，先按侦察路径定位实现面、再建条目框架（别先写框架再找代码）。
  分支快照按只读物化：`git archive <ref> | tar -x -C %TEMP%\<feat>_audit\src`（不 checkout、不加
  worktree、不动用户工作区）；编排者与流都在快照上审计并跑聚焦套件（host venv python + `HERMES_HOME`
  指向 Temp 目录 + `-p no:cacheprovider`）；快照套件先逐文件 `--collect-only -q` 计数再整体运行——通过数
  偏小先怀疑收集范围；陈旧快照的 fixture 参数超出实现签名（setup TypeError）照实记为快照缺陷证据。
- landing 意识（分支 vs main）：报告须含 landing 表，逐构造标注 branch/main——`git merge-base
  --is-ancestor <impl-commit> main`、`git diff --stat main <branch> -- <共享文件>`（量级=收敛工作量）、
  `python -B -c "import hermes_cli.<mod>"`（`-B` 防在树里写 __pycache__；ModuleNotFoundError 就是
  landing 缺口证据）。main 有调用点但 import 目标缺失 = 该 `/命令` 调用即失败（已知缺口类）。
- 功能面侦察路径（“X 在哪实现”逐层证伪，别在第一层收工）：main 调用点 grep → `git log --all
  --format="%h %ad %s" --date=short | grep -i <feat>` 与 `--diff-filter=A/D` / `-S "<symbol>"`
  定位引入与删除 → `git branch -a --contains <commit>` → `git worktree list` 逐 worktree
  `git ls-tree -r <ref> | grep -i <feat>` → `%LOCALAPPDATA%\hermes\backups\*`（`*-hard-cut-*` 的
  `removed/` = 被砍旧实现，`pre-*-hard-cut-*` = 砍前数据库快照）→ `~/projects/*` 独立仓库（多为旧代际）。
- ultrawork.md 轮框架：`%TEMP%\uw_audit\uw_items.md`（80 条 R01–R80：H1 规划/计划格式 29｜H2 上下文
  11｜H3 迭代 17｜H4 清理/规模/红旗 23；含 landing 表与共享规则）；被清理时按同簇逻辑从
  `Documents\ultrawork.md` 重 derive。
