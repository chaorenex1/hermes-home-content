# Hermes File/LanceDB Memory Provider — Implementation Map

Use when auditing or modifying the Hermes memory provider (compatibility plugin id `lancedb`) or its host integration: the two-layer Context engine (Base refresh + dialectical D1/D2/D3), workflow projections, compression, and response quality.

## Where the code lives (check every copy before concluding)

- Dev repo: `~/projects/hermes-lancedb-memory` — plugin package `plugin/lancedb/`, tests in `tests/`. Branches carry route/refactor work; check `git branch -v` and `git status` first.
- Installed copy the runtime actually loads: `$HERMES_HOME/plugins/lancedb/` (copied by `scripts/install_dev_plugin.py --target-hermes-home ...`). It can lag the repo by whole modules — diff the two file sets before trusting either. Redeploy + restart the gateway before any live-behavior claim. The lag can be a whole generation with different module names: the older runtime generation ships `base_context.py`, `dialectical_context.py`, `context_scheduler.py`, `stale_tools.py` plus the `publish_deep_interview_projection` / `publish_ultrawork_projection` entries; the dev-repo generation ships `base_summary.py`, `dynamic_pipeline.py`, `dynamic_result.py`, `message_context_policy.py`, `workflow_projection.py`, `session_context_state.py`, `compression_agent.py` and no `publish_*`. A plan row citing the older module names is describing the installed copy — classify each symbol per copy.
- Host source: `$HERMES_HOME/hermes-agent` (checkout, usually `main`). Feature host code (deep-interview runtime, ultrawork runtimes, projection outboxes) is developed in git worktrees under `$HERMES_HOME/worktrees/<branch>` and task workspaces under `$HERMES_HOME/kanban/workspaces/<task>/`; missing symbols in main are not missing features. Locate with `git branch -a`, `git log --all --oneline -- <path>`, `git worktree list`. The working tree commonly carries uncommitted feature changes — run `git status` and read the working tree, not branch names, before concluding a host contract is absent. Host-side anchors for the extended sync contract: `run_agent.py::_sync_external_memory_for_turn` (metadata snapshot → `sync_all`), `agent/memory_manager.py::sync_all` + `_provider_sync_accepts` (signature-filtered kwargs, serialized background worker), `agent/turn_finalizer.py` (`_qualifies_for_memory_sync` — the single call site), `agent/memory_provider.py::sync_turn` (base signature).
- Live state: board DB `$HERMES_HOME/kanban.db` (tasks/task_links plus feature tables such as `deep_interview_*`, `ultrawork_*`); provider storage root `$HERMES_HOME/lancedb-memory/` containing `memory.db`, `session-context.db` (durable dynamic-turn state and generations), `prompts/` (profile-local prompt copies), `contexts/` (published context documents), `agents/<profile>/identity.md|preference.md`.

## Env → provider chain

- Session-scoped ContextVars in `gateway/session_context.py`: `HERMES_SESSION_MODE`, `HERMES_ULTRAWORK_PLAN_ID`, `HERMES_DEEP_INTERVIEW_ID`, `HERMES_KANBAN_DB`; bound task-locally via `scoped_session_env_vars(...)` and in the `run_agent.py` workflow-task env bindings. The provider reads them through `gateway.session_context.get_session_env` with an `os.environ` fallback.
- A new session-scoped variable requires all four links: ContextVar + `_VAR_MAP` entry, run_agent binding, a setter at the feature runtime's dispatch site, and the provider read. Absence of any link means the contract does not work yet.

## Provider module map

- Base layer: `base_summary.py` (Base refresh agent + multi-document generation), templates `context-base-refresh-*`.
- Dialectical layer: `dynamic_pipeline.py` (D1 cold/warm → D2 audit → D3 reconcile → dynamic-final), `dynamic_result.py` (closed result contract), `session_context_state.py` (durable `DynamicTurnJob`, generations, counters), `dynamic_documents.py` (section-file format and budgets).
- Injection: `dynamic_context.py` renders the single `<dynamic-context>` block; the only production producer is the plugin `pre_llm_call` hook (`lifecycle_hooks.py` → provider `pre_llm_context`); provider `prefetch()` deliberately returns "".
- Delegation: `kb_subagent` is authorized only for cold-D1→base-refresh and warm-D1→memory-retrieval, exactly one each, frozen scope (enforced in `__init__.py`).
- Workflow projection: `workflow_projection.py` reads the board DB via a read-only URI from `HERMES_KANBAN_DB` and renders ultrawork/deep-interview blocks (historically via defensive tasks/task_links column detection).
- Compression: `compression_agent.py` + `context_engine.py`; response quality: `quality_agent.py` + `response_quality.py`.
- Paths: `paths.py` — session documents under `/contexts/<profile>/<session_id>/...`; ultrawork plan/todo and workflow dynamic documents use separate builders (`workflow_scope_root`, `ultrawork_phase_document_path`) that have carried different segment orders — read both functions before assuming a layout. Write authority: `profile_authority.py`; public tool schemas: `context_tools.py`, `context_kb_tools.py`.
- Prompt content: `prompt_templates.py` holds all defaults; `PromptTemplateStore.initialize()` creates missing files and NEVER overwrites, so changed defaults do not reach existing profiles — treat default-prompt changes as a migration, not an edit.
- Namespaced agent skills: `plugin/lancedb/skills/{kb_tools,kb_agents,kb_memory}/SKILL.md` (runtime-editable lane contracts).

## Verification commands (Windows git-bash)

- Which copy differs: `diff <(ls $HERMES_HOME/plugins/lancedb | sort) <(ls ~/projects/hermes-lancedb-memory/plugin/lancedb | sort)`.
- Board tables (enumerate before assuming a contract exists): `python -c 'import sqlite3; c=sqlite3.connect("file:"+p+"?mode=ro", uri=True); print([r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type=? ORDER BY name",("table",))])'`.
- Find feature code absent from main: `git branch -a`, `git log --all --oneline -- <path>`, `git worktree list` in the host checkout; component facts also appear under `$HERMES_HOME/kanban/workspaces/<task>/`.
- Search hygiene: keep ripgrep patterns to plain substrings; backslash-escaped parens inside alternations can fail to parse ("unclosed group") — retry with bare symbol names and no metacharacters.

## Pitfalls

- Never describe runtime behavior from the dev repo alone: the installed plugin copy plus the running gateway process decide behavior.
- A board table's absence is authoritative for what the host writes today; verify table existence before designing a pull/push contract around it. Conversely, tables present from earlier feature runs do not prove their writer code is current — pair table checks with a writer-code search.
- The provider prompt store only adds files: changed default templates must be migrated for existing profiles.
- Prompt contract and receipt validator can drift (the dynamic-final prompt lists a `status` field the closed validator does not accept). Before reporting such a mismatch as a runtime bug, check whether the pipeline whitelists fields between model output and validation — `dynamic_pipeline.py` picks the eight receipt keys before `validate_dynamic_result`, so dropped extras make the drift inert.

## Reporting shape for spec-vs-implementation gap analyses

Lead with verified environment facts (which copies exist, what the live DBs contain), then per spec item: current state with file:line anchors → required change → affected files/tests → open questions; close with a workstream split (plugin vs host) and the acceptance path (repo test suite, disposable-`HERMES_HOME` E2E, redeploy + gateway restart for live claims).

When the input is the user's correction-notes file rather than a formal plan, run the notes↔plan↔code reconciliation first — see the notes-ingestion contract in the `iterative-planning-workflows` skill.
