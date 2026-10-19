---
name: persistent-planning-loops
description: "Design and implement persistent planning-only loops that iteratively refine a plan, track state, and stop without executing the planned work. Use when a user wants continuous plan writing rather than autonomous implementation."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [planning, plan-mode, persistence, state-tracking, guarded-execution, hermes]
    related_skills: [plan, kanban-orchestrator, hermes-agent]
---

# Persistent Planning Loops

Use this skill when the user wants Hermes to keep improving an implementation plan across turns, while explicitly **not executing the planned work**.

## Core distinction

Do not use a normal autonomous goal loop for this request:

- `/goal` is an execution loop. Its continuation prompt tells the agent to take the next concrete implementation step and it can use normal write/terminal tools.
- `/plan` is planning-only, but normally completes one planning turn and stops.
- A persistent planning loop is a third mode: repeated planning turns, persistent plan state, and hard execution restrictions.

The desired behavior is:

```text
inspect read-only context
  -> update only the designated plan document
  -> judge plan completeness
  -> continue planning OR pause for input OR finish
```

## Required invariants

1. **Planning-only:** Never modify source, tests, configuration, dependencies, git history, external systems, or deployment state.
2. **Single writable artifact:** Permit writes only to the exact designated plan path. If the user supplies a path such as `.hermes/plans/lancedb-hermes.md`, it overrides the normal timestamped default; never create a second plan file or write to a guessed absolute-path variant.
3. **Session-bound enforcement:** Bind Ralph state and tool restrictions to the active session identifier. Never use a process-global environment flag or global plan path as the authorization source: another session must remain unrestricted. `pause` must immediately remove the binding for that session; `resume` must bind the persisted paused plan to the current session, including when resuming from a different/new session.
4. **Persistent state:** Save goal, plan path, status, turn budget, subgoals, and latest judge reason in durable session state; do not rely on conversation context alone. Provide a separate `show-all`/enumeration path that queries every persisted `ralph:*` record instead of loading only the current session; include active, paused, done, cleared, and detached/resumable records, while keeping `status` scoped to the current session.
4. **Bounded loop:** Use a finite turn budget. On exhaustion, pause with a reviewable plan rather than continuing forever.
5. **Evidence-based completion:** A plan is complete only when it has enough concrete detail to execute later; a model claim such as “the plan is done” is insufficient.
6. **Multiline command arguments:** Slash-command parsers must preserve pasted newlines in the argument. Do not use regex `.*` for the full command payload unless dotAll is enabled; use `([\\s\\S]*)` (or equivalent) so multiline `/ralph` objectives reach the backend intact. Test a pasted multiline command through the actual Desktop/Web dispatch path; otherwise the client may misparse it and show `empty slash command`.
7. **Cross-surface response contracts:** Structured command responses must use the fields consumed by every client (`exec`/`plugin` with `output`, `send` with `message`). Unsupported shapes such as `notice`/`message` can render as `/<command>: no output` even when the backend handled the command.
6. **User preemption:** A real user message pauses or preempts automatic continuation. Commands that inspect or add criteria should not silently destroy the loop state.
7. **Explicit blocking:** Pause when a missing decision materially changes the plan. Do not invent requirements to avoid asking.

## State model

Persist a separate planning state, not the execution goal state. When the user requires a dedicated SQLite file, resolve it under the active profile (`<HERMES_HOME>/<name>.db`), instantiate the state store with an explicit `db_path`, and cache connections by Hermes-home path. If moving records out of shared `state.db`, use an idempotent copy-forward migration that never overwrites newer destination rows and retains the legacy rows for rollback. See `references/dedicated-sqlite-state.md` for the implementation and verification recipe.

A minimal record is:

```json
{
  "mode": "planning",
  "goal": "...",
  "plan_path": ".hermes/plans/2026-01-01_120000-example.md",
  "status": "active",
  "turns_used": 2,
  "max_turns": 20,
  "subgoals": [],
  "last_verdict": "continue",
  "last_reason": "..."
}
```

Recommended statuses: `active`, `paused`, `blocked`, `completed`, `cleared`.

Useful controls are analogous to goal controls but must remain planning-specific:

```text
/ralph status
/ralph show
/ralph resume [plan-selector]
/ralph clear
/ralph subgoal <criterion>
```

Do not expose a separate user-facing `pause` control for Ralph. A finite turn budget may place a plan into a resumable paused state internally, but recovery is performed with `/ralph resume <selector>` and immediately re-enters the planning loop. The selector should accept the persisted plan/session identifier, plan path or filename, and an enumerated plan index when the UI presents a list. Resume must rebind the recovered state to the current session rather than assuming the original session remains active.

At the end of every Ralph round, persist a bounded round record containing the model response, verdict, reason, goals/subgoals, timestamp, and a conversation snapshot sufficient to roll back or inspect that round. Save the round after the judge runs so the snapshot corresponds to the evaluated response. Keep the persisted history bounded and avoid storing secrets or unrestricted tool payloads.

Every round should judge both plan completeness and goal coverage: the plan must explain how all declared goals/subgoals can be achieved, not merely contain generic implementation sections. If the user sends a change request during Ralph, classify it before editing: target `goal` or `plan` content, and action `add`, `modify`, or `delete`. Goal changes update acceptance criteria/subgoals; plan-content changes update the designated plan artifact. Preserve this distinction in the next round's state and judge prompt.

See `references/ralph-round-state-and-intent.md` for the durable-state, rollback, intent-routing, and cross-surface integration checklist.

Do not expose a separate user-facing `pause` control for Ralph. A finite turn budget may place a plan into a resumable paused state internally, but recovery is performed with `/ralph resume <selector>` and immediately re-enters the planning loop. The selector should accept the persisted plan/session identifier, plan path or filename, and an enumerated plan index when the UI presents a list. Resume must rebind the recovered state to the current session rather than assuming the original session remains active.

At the end of every Ralph round, persist a bounded round record containing the model response, verdict, reason, goals/subgoals, timestamp, and a conversation snapshot sufficient to roll back or inspect that round. Save the round after the judge runs so the snapshot corresponds to the evaluated response. Keep the persisted history bounded (for example, the latest 50 rounds) and avoid storing secrets or unrestricted tool payloads.

Every round should judge both plan completeness and goal coverage: the plan must explain how all declared goals/subgoals can be achieved, not merely contain generic implementation sections. If the user sends a change request during Ralph, classify it before editing: target `goal` or `plan` content, and action `add`, `modify`, or `delete`. Goal changes update acceptance criteria/subgoals; plan-content changes update the designated plan artifact. Preserve this distinction in the next round's state and judge prompt.

## Review-gated automatic progression

## Ralph review-gated loop semantics (Scheme B)

The default review-gated flow is **candidate -> judge -> user review -> continuation**, not candidate -> user review -> judge. Keep these phases distinct:

```text
model produces candidate plan
  -> persist candidate/round result
  -> judge candidate
  -> awaiting_review
       approve + judge=done     -> completed
       approve + judge=continue -> enqueue next planning round
       feedback                 -> re-analyze the same round, then judge again
```

User approval confirms the already-judged candidate; it does not itself run the judge again. A revision comment increments the attempt, not the logical round. Only `judge=done` plus explicit approval completes the plan; `judge=continue` plus approval is the self-continuation path. Budget exhaustion pauses without enqueueing another round. Do not implement a hidden automatic continuation while `awaiting_review`.

When the user wants Ralph to remain automatic but add a review gate, do not convert it into manual single-step mode. The round lifecycle is:

```text
automatic analysis -> candidate plan/state -> persist round -> awaiting_review
  -> approve -> confirm round -> automatic continuation
  -> feedback -> persist feedback -> re-analyze the same logical round -> awaiting_review
```

Present review as an ordinary question/answer interaction, not as new user-facing `/ralph approve` or `/ralph revise` subcommands. Persist a review request containing `plan_id`, logical `round`, `attempt`, question, options, and status so replies can be routed after reconnect/restart across CLI, gateway, and TUI/Desktop. Explicit approval (`通过`, `approve`, etc.) resumes automatic continuation; any other non-empty answer is revision feedback and must re-analyze the current round rather than advance it. Ambiguous or empty answers keep the gate open.

Distinguish logical rounds from attempts: feedback increments `attempt`, not `round`. Keep prior analysis/review entries for auditability. Only an approved candidate is confirmed plan state; if candidates are written directly, preserve a snapshot/version boundary so an unapproved candidate cannot be mistaken for an approved plan.

If state navigation accepts a plan ID and user statement, treat it as a state transition rather than a read-only query. Record forward/backward direction, source statement, from/to state or round, and transition ID without deleting historical rounds. After a transition, re-analyze and return to `awaiting_review`; never bypass the gate. Keep read-only operations separate: one query returns all rounds for a plan, another enumerates plans with status filtering.

Do not add user-visible subcommands solely for review control. Intercept the next ordinary user response while `awaiting_review` before normal agent dispatch; otherwise words such as “approve” or revision comments may be misinterpreted as a new planning objective. Test this routing separately in classic CLI, gateway, and TUI/Desktop, including restart/reconnect persistence.

## Planning-only enforcement

Prompt instructions alone are not a sufficient safety boundary. Add capability/tool enforcement where possible:

### Allowed
- read-only file and repository inspection;
- read-only web/documentation lookup;
- read-only terminal commands;
- writing or patching only the designated plan file.

### Forbidden
- ordinary file writes or patches;
- source/test/configuration edits;
- package installation or deletion;
- mutating git commands, commits, pushes, or deploys;
- service starts/stops;
- browser/API actions with side effects;
- secret handling or credential changes.

If the runtime cannot enforce a write allowlist, use a separate planning workspace and fail closed on non-plan writes rather than pretending prompt-only restrictions are reliable.

## Template-stable plans and execution handoff

When a planning loop may later hand an approved plan to an execution loop, persist the plan's **template identity** alongside the normal goal state. Do not make a resumed plan depend on a fresh, possibly different classification.

Recommended persisted fields:

```json
{
  "template_id": "code-feature",
  "template_version": 1,
  "template_source": "explicit|classified|fallback",
  "execution_profile": "code|config|research|manual"
}
```

Use a small deterministic template registry where possible. A code template must require exact task headings, TDD/verification criteria, files or component boundaries, and rollback/risk content; a research or manual template must not be silently treated as executable code work.

For a durable handoff, require both explicit Ralph approval and a readable plan artifact. Store the approved plan ID, path, template/version, execution profile, acceptance criteria, and a digest of the plan content. Execution must reject unapproved, missing, changed, or non-executable plans rather than reconstructing instructions from chat history.

An execution loop needs relational, transactional workflow state rather than a single opaque session JSON record: workflow, ordered steps, phase/review attempts, and append-only evidence events. For code work, do not advance a step on prose alone; require phase evidence through a finite state machine such as `RED -> GREEN -> REVIEW -> completed|rework|blocked`. Missing or malformed evidence must leave the durable cursor unchanged. A blocked step is a terminal escalation state, not an invitation to retry indefinitely.

### Execution-contract invariants

Treat an approved Ralph manifest as an execution contract, not merely a suggested task list:

- **Validate the dependency graph at handoff.** Require unique step IDs, reject self-dependencies, unknown dependencies, and forward edges. Requiring dependencies to target earlier steps makes the graph acyclic by construction.
- **Schedule by completed dependencies, not ordinal alone.** A pending step becomes runnable only after every declared dependency is `completed`. Recheck this invariant when re-opening steps after global review.
- **Give an approved plan one active owner.** Prevent concurrent execution of the same Ralph plan across sessions with a friendly preflight check and a database uniqueness constraint covering active statuses; the constraint is the race-safe backstop.
- **Bind evidence to the manifest.** For Ralph-origin workflows, require substantive phase and global-review evidence. Passing step reviews and global reviews must include a `criteria`/`acceptance_criteria` mapping that gives verification evidence for every declared acceptance criterion. Keep the cursor unchanged on rejection.
- **Account for terminal outcomes once.** On every `completed`, `blocked`, or `failed` terminal transition, write one idempotent template-history outcome (`passed` or `failed`) with review findings. Cover both normal post-turn routing and direct state API calls.

Regression tests should use a real temporary database and cover each contract boundary: invalid graph rejection, dependency-gated activation, cross-session duplicate-plan rejection, empty/criteria-incomplete evidence rejection, and exactly-once success/failure outcome history.

## Plan-file update workflow

When refining an existing designated plan across turns:

1. Read the relevant plan section before editing; do not overwrite a partially paged file from memory.
2. Inspect only the minimum read-only Hermes/provider context needed to ground the new requirement.
3. Patch the existing designated file in place. Do not substitute a timestamped filename, absolute-path alias, or new sibling plan.
4. Re-read the changed section and report the exact path plus the substantive additions.
5. Keep the plan-only boundary active even when the user adds a concrete implementation requirement; update tasks, configuration, acceptance criteria, and risks rather than implementing code.

## Hermes memory-provider planning pattern

For plans involving a custom `MemoryProvider`, explicitly model the provider lifecycle (`initialize`, `prefetch`, `sync_turn`, `on_turn_start`, `on_session_switch`, `on_session_end`, `shutdown`) and distinguish memory-layer behavior from gateway session expiry. Background observation or extraction should specify activity semantics, watermarks, idempotent job identity, cancellation on new user input, bounded queues, restart checkpoints, and a finite shutdown drain. Treat retrieved memory as data behind fencing and limits, not as instructions.

### Self-improving memory-provider plan requirements

A plan for automatic memory extraction is incomplete unless it specifies both the **canonical memory templates** and the **end-to-end extraction pipeline**. Do not leave either as "LLM summarizes the session".

- Define one template registry as the source of truth: common frontmatter, allowed memory types/subtypes, canonical paths, deterministic section rendering, versioning, and validation. For type-specific memories, state exactly which fields are dynamic vs fixed; omit unsupported fields rather than filling `unknown`/`none` placeholders.
- Define extraction input/output contracts: bounded watermark-frozen message window; redacted, provenance-tagged evidence records; strict JSON candidate schema; required evidence IDs per claim; server-validated limits.
- Break the pipeline into explicit stages: eligibility/window freeze → redaction/evidence capture → deterministic prefilter → constrained type classification → claim extraction → dedupe/conflict analysis → template rendering → policy/schema validation → atomic candidate persistence → review notification.
- Separate candidate quarantine from accepted retrieval: unreviewed content must not update production summaries, embeddings, FTS indexes, `prefetch`, or normal search. Promotion must be a separate version-checked, auditable operation.
- Include tests for every template, malformed model output, unsupported claims, fake evidence IDs, prompt-injection text, duplicate/conflicting candidates, candidate visibility leakage, cancellation on new messages, and restart-idempotent jobs.

Reuse the persistence pattern of an execution goal loop, but use a separate judge contract. The judge evaluates whether the **plan** is ready, not whether the implementation is complete.

Return a structured verdict:

```json
{"verdict":"done|continue|blocked","reason":"one concise evidence-based sentence"}
```

Completion should require, when relevant:

- clear outcome and scope;
- assumptions and constraints;
- dependencies and unresolved decisions;
- ordered, bite-sized tasks;
- exact files, modules, or external boundaries;
- implementation approach and relevant interfaces;
- verification commands and acceptance criteria;
- risks, rollback/recovery, and stop conditions;
- no fabricated repository facts;
- the designated plan file exists and is readable.

`continue` should name the missing planning artifact or decision. `blocked` should identify the specific user input needed. Do not convert an implementation failure into a planning completion.

## Continuation prompt

Continuation must explicitly prohibit execution:

```text
[Continuing planning-only work]
Goal: {goal}
Plan file: {plan_path}

Review the current plan and read-only project context. Improve the plan only.
Do not implement, run mutating commands, edit any file other than the plan file,
or claim completion without concrete plan evidence. Address the judge's gap:
{reason}
```

Never reuse the ordinary execution continuation prompt (`Take the next concrete step`) without adding the planning-only boundary.

## Implementation guidance for Hermes

When extending Hermes itself, prefer a dedicated planning state manager or a clearly separated mode over overloading `/goal`:

- Reuse persistence and bounded-judge infrastructure where safe.
- Give the mode its own state key, such as `plan_goal:<session_id>`.
- Add a distinct command such as `/plan-goal`, leaving `/goal` semantics unchanged.
- Keep the existing bundled `plan` skill's one-turn contract intact; add a loop controller around it rather than weakening its no-execution rules.
- Test CLI and gateway surfaces separately if both are supported.
- Test that a queued real user message preempts continuation, while status/subgoal commands preserve state.

## Hermes TUI/Desktop integration pitfall

Supporting only `cli.py` is insufficient. The Desktop/TUI surface dispatches slash commands through `tui_gateway/server.py`, not the classic CLI command loop. For a command that queues a synthetic planning turn:

1. Add the command name to `_PENDING_INPUT_COMMANDS` so `slash.exec` routes it to `command.dispatch` instead of the slash worker.
2. Implement the command branch in `command.dispatch`, returning the structured `send` payload for the first/resumed planning prompt and a response shape the client actually renders for status/pause/clear/subgoal operations. Desktop/Web clients currently render `exec`/`plugin` payloads via `output`; an unrecognized `{type: "notice", message: ...}` can silently degrade to `/<command>: no output`.
3. Add a post-turn hook beside the existing `/goal` continuation hook. It must call the planning manager with the session key used by TUI, emit `status.update`, and chain the returned continuation only after `session["running"]` is released.
4. Test both command resolution/catalog visibility and actual `slash.exec` → `command.dispatch` behavior. A command can appear in the registry yet still fail at runtime if it is missing from `_PENDING_INPUT_COMMANDS` or returns an unsupported response shape.
5. Restart the TUI/Desktop backend or Gateway after source changes; the running Python process does not hot-reload modified modules. Before troubleshooting the client, verify the live process has loaded the changed source.

Keep the classic CLI and TUI state keys aligned, but do not assume the CLI's `_pending_input` queue is consumed by the TUI slash worker. The TUI must translate planning commands into its own structured prompt submission path.

## Verification checklist

Before claiming the feature works, verify all of the following with tests or a controlled smoke test:

- first turn writes only the plan artifact;
- a continuation updates the same plan path;
- a forbidden write is rejected;
- `continue`, `done`, `blocked`, pause, resume, clear, and turn exhaustion have distinct transitions;
- state survives session resume/restart;
- user input preempts automatic continuation;
- the completion judge requires concrete plan evidence;
- normal `/goal` still permits its existing execution behavior;
- classic CLI and TUI/Desktop both resolve and dispatch the command;
- TUI/Desktop is restarted before runtime verification;
- the live log contains command dispatch and Ralph continuation evidence, not merely a registry entry.

## Ralph implementation review pitfalls

When reviewing or extending an actual Ralph implementation, validate the state machine and every execution path—not only the planner module's unit tests:

- A judge `done` result should enter an explicit approval state; after approval it must terminate as `done` and must not enqueue another continuation. Test the full `after_turn -> review -> approval -> dispatcher` path.
- Persist and restore every state field used for recovery (`history`, active/current round, review attempt, transitions, and bounded round records). A dataclass field is not durable until `from_json()` restores it; test save/reload, not just same-process behavior.
- Enforce planning-only policy before all tool-execution branches. A guard placed only in the generic dispatcher can be bypassed by executor special cases such as delegation, memory, context-engine, or built-in tools. Test both direct dispatch and special branches.
- Review interception must not consume slash commands as feedback. Route recognized control commands before ordinary review answers on CLI, gateway, and TUI/Desktop.
- State transitions must update both the recorded transition and the live cursor/round; verify backward transitions at round zero and after reload.
- Inspect unrelated modified code around insertion points. Static compilation can pass while an accidental runtime fragment references undefined variables in a neighboring handler.

The session-specific reproduction matrix and observed failure signatures are in `references/ralph-review-pitfalls.md`.

## Reference

See `references/hermes-planning-loop-design.md` for the session-derived comparison of `/plan`, `/goal`, and the proposed planning-only loop, plus an implementation sketch and acceptance matrix.
