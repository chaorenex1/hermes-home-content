---
name: ralph-iterative-planning
description: "Use when the user enters Ralph planning mode (/ralph) or asks for iterative, evidence-driven plan refinement with exact old_string→new_string patches."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [ralph, planning, iterative, evidence-driven, gap-analysis]
    related_skills: [plan]
---

# Ralph Iterative Planning

Use when Ralph planning mode is active (objective-driven, write-only to designated plan file). The core pattern: read authoritative sources → identify concrete gaps at line level → write executable patches → verify each with read_file.

## Core Behavior

**In Ralph mode:**
- Do not implement code, run mutating commands, install deps, commit, or modify any file except the designated plan file.
- Do inspect repos, source code, docs, and existing artifacts with read-only tools.
- Your deliverable is a concrete, executable meta-plan saved to the designated plan file.

**Artifact format vs. edit mechanics:**
- The designated plan is a readable execution artifact. Do **not** embed `old_string` blocks in it; include target, injected/replacement content, verification, recovery, and stop conditions instead.
- Exact `old_string` text remains an operational input to a later `patch` tool call. Obtain it from `read_file` immediately before that call; never persist it as plan content unless the user explicitly requires it.
- For current Ralph v2 plans that require an Ultrawork handoff, author stable `### Task N: ...` sections. Approval compiles and persists exactly one canonical `<!-- ULTRAWORK_MANIFEST ... -->` RouteManifest v2 block; verify its opening marker occurs once after approval. Legacy v1 manifests are only for explicitly preserved historical plans.
- When review expands a compact objective (for example, from one calculation to several), revise the goal, scope, every affected task, acceptance criteria, risks, stop conditions, and manifest together; preserve independently verifiable steps for each requested result.
- If the plan says an operation runs once, align the Ultrawork manifest with `max_attempts: 1` and prohibit retries, substitutions, or reruns of that operation. Do not use a generic retry allowance that can silently repeat a one-shot action.
- For non-mutating execution plans, require a rollback statement: no rollback is needed because changes are prohibited; an unintended mutation must stop execution, preserve command/target/change evidence, and require separate authorization before any cleanup.
- After `ultrawork_execute` starts a workflow, treat its returned `next_instruction` as the live phase contract. If it explicitly mandates `delegate_task` with an exact template, goal, and context—even for a review phase—dispatch exactly that child rather than substituting a prose review. Preserve the returned delegation ID and wait for its completion evidence before emitting the required `ULTRAWORK_REPORT`.

**When the Ralph loop says "Previous planning review: ...":**
- The review tells you what's missing (verification commands, blocker conditions, exact paths, etc.)
- Address every point in the review directly — each complaint becomes a concrete addition
- Do not defend the previous plan; just add what was asked for

## Evidence-Driven Gap Analysis

**Step 1: Read authoritative sources**

| Source type | How to access | What to extract |
|-------------|---------------|-----------------|
| Source code (ABC, interface) | `read_file(path)` or `search_files` | Method signatures, required params, hook lists |
| Official docs | `web_extract(urls=[...])` | API reference, conventions, lifecycles |
| Existing artifacts | `read_file(path)` | Current state, line numbers, exact text |
| User directives | Parse from conversation | Requirements, constraints, directory structures |

**Step 2: Identify concrete gaps**

Compare existing plan against sources. Each gap must have:
- Exact line number(s) in the existing plan
- The specific difference (what's wrong/missing)
- The authoritative source that proves the gap
- A severity label

**Step 3: Prepare executable edit mechanics separately from the artifact**

Use exact `old_string` only as the immediate input to the edit tool; never include it in the designated plan unless the user explicitly requires it. The plan itself must state the target, injected or replacement content, verification, recovery, and stop conditions.

When documenting a patch outside the plan artifact, it may include:
```
## P{N}: {descriptive title}

**目标行:** L{start}-{end}

**old_string:**
```
{exact text from the existing plan — copy-pasted, not paraphrased}
```

**new_string:**
```
{exact replacement text — complete, copy-pasteable}
```

**验证:**
`read_file(offset={N}, limit={M})` → 含 "{keyword1}"、"{keyword2}"。

**失败恢复:** {what to do if old_string doesn't match — e.g. read_file to confirm, adjust, retry max 2x}
```

## Iterative Refinement Pattern

When the user provides additional requirements after the initial plan is written:

1. **Give it a sub-number** — P2a, P2b, P2c inserted between existing patches
2. **Insert in the gap table** and renumber downstream if needed
3. **Update execution order** — P1→P2→P2a→P2b→P3→...
4. **Update full-review checklist** if new verification items are needed
5. **Never rewrite the entire plan** — surgical patches preserve existing structure

## Cross-surface Ralph runtime review

When Ralph changes touch runtime code rather than only plan documents, review the complete state machine and all dispatch surfaces. Confirm terminal approval, restart-safe state restoration, canonical round transitions, executor-level planning guards, and slash-command precedence over review interception. Use `references/ralph-runtime-repair-checklist.md` for the compact acceptance checklist and fallback verification shape.

### TUI session-bound starts

Ralph lifecycle state is keyed by the durable live session key, not necessarily the transport/UI session id. For a TUI `/ralph` start, route through `ralph_execute_tool(action="start", objective=..., runtime_session_id=session["session_key"])`, consume its structured result, and test the `command.dispatch` seam with distinct transport and durable ids. This prevents active plans with no recorded rounds because the post-turn hook cannot locate their state. See `references/tui-session-binding.md`.

### Gateway session-key symmetry and kickoff routing

Gateway sessions have both a routing `session_key` and an internal, potentially rotating `session_id`. Ralph start, review interception, snapshotting, and post-turn transitions must use the **same** Ralph key—normally the source-derived `session_key`. Do not start under `session_key` and then call `ralph.after_turn()` or `snapshot_round()` with `SessionEntry.session_id`; that strands the plan at `active`, round 0 because the hook loads a different state record.

A Gateway `/ralph` start or resume acknowledgement is not itself a planner turn. Queue or recursively route `ralph.continuation(state)` through the normal adapter FIFO/message path, retaining the normal user-message-preemption behavior.

**Continuation handoff must carry plan identity.** The queued continuation can run under a newly allocated turn session even when `/ralph` started under a different session key. Put `Plan ID: <state.plan_id>` inside the single canonical `[Continuing Ralph planning loop]` envelope (do not prepend a second marker). At the earliest gateway prompt-submit boundary, recognize that tagged internal message, resolve the sole live owner of that `plan_id`, and atomically rebind it to the session key that will execute the turn before calling the agent. New traffic must never infer identity from goal text or plan path. A temporary legacy fallback is acceptable only for an untagged continuation whose exact `(goal, plan_path)` identifies exactly one **active** owner; refuse ambiguous matches. Preserve user-message preemption by restricting either bind path to the internal marker. Regression coverage must use distinct slash-session and actual-turn ids, include the unique legacy path, and prove that the old owner is removed, the new owner remains `active`, and the subsequent `after_turn()` reaches `awaiting_review`.

Add regression coverage using deliberately different key/id values for: start → actual planning turn → awaiting review; resume → actual continuation; review reply → approval/reanalysis; and user input preempting queued continuations.

### Lifecycle ownership and detached-state invariants

Treat `plan_id` as a single-owner state machine. A detached entry may help route a resume, but it must not be a second independently resumable copy. On `pause`, `clear`, or `archive`, synchronize or remove any detached alias. A cross-session resume must transfer ownership or refuse; never leave two sessions active for the same plan ID. Starting a plan in a session that already has an active/awaiting-review plan must require an explicit replacement action instead of silently overwriting the existing state. Run the temporary-home regression probes in `references/ralph-lifecycle-invariants.md`.

**Make cross-session transfer compare-and-swap, not read-then-write.** Selection can happen outside the transaction for UX, but the write transaction must re-read all `ralph:*` records for the selected `plan_id`; require exactly one non-detached owner (or one detached-only legacy record), require `status == "paused"`, and reject a live target session. In that same transaction, delete the old owner plus any matching detached alias and write the target as active. A separately atomic write after an unlocked read is still racy: two calls can both observe `paused` and create two active owners. Add a deterministic two-thread/barrier regression that races target-session resumes and asserts exactly one success and one persisted active owner.

### Ultrawork handoff integrity

For executable Ralph plans, audit the handoff as a contract rather than a prompt convention:

- Validate manifest dependencies as an ordered DAG: reject unknown, self, forward, and cyclic dependencies; activate a pending step only after all dependencies are completed.
- Treat `evidence_required` and acceptance criteria as enforceable gates. Ralph-origin phase, review, and global-review evidence must be substantive; a passing review must map every acceptance criterion to verification evidence.
- Atomically allow at most one running/global-review Ultrawork workflow per Ralph `plan_id` across sessions.
- Record exactly one template-history outcome when a Ralph-origin workflow reaches `completed`, `blocked`, or `failed`, including the normal global-review completion path.
- When listing append-only workflow events, use a deterministic insertion-order tie-breaker in addition to timestamps; rapid event writes can share a timestamp.

### Artifact-backed independent Judge + Clarify review loop

When extending Ralph review, keep authoring, judging, and human approval separate:

1. **Judge the designated artifact.** The auxiliary judge must receive bounded Markdown from `state.plan_path`, not merely the planner's final prose or a filesystem path it cannot read. Treat an unreadable or empty artifact as `blocked`; cap large documents with a head/tail window.
2. **Use a Ralph-specific auxiliary task.** Route through `get_text_auxiliary_client("ralph_judge")` so providers/models can be configured independently of `/goal` (`auxiliary.ralph_judge.*`). The Judge returns strict JSON: `approve|revise|blocked`, `reason`, structured findings (`severity`, `criterion`, `evidence`, `required_change`), and evidence strings. Parse failures and unavailable Judge backends must fail safe to `revise`, never silently approve.
3. **Persist review evidence.** Store the normalized report in `RalphState` and the current round before exposing it to users. Persist approval, continuation, revision, pause, and clear decisions as round/audit events keyed by the existing plan and review attempt.
4. **Ask the human through the platform clarify primitive.** On `awaiting_review`, render the Judge summary and choices such as adopt recommendation, approve, pause, and clear; use the built-in Other/free-text route for specific revision feedback. Do not make the model translate a review choice into a lifecycle action.
5. **Resume only after a decision.** `approve` may complete an accepted plan; a Judge-backed revision or free-text feedback calls `handle_review()`. A clarify timeout leaves the plan `awaiting_review`; it must not auto-approve or manufacture feedback.
6. **Make continuations explicitly low priority.** Do not put Ralph continuation strings into the same FIFO as real user input without distinction. In CLI, stage one internal continuation separately and consume it only after the real user queue is empty. In TUI, drain queued user prompts before a follow-up. In Gateway, stage a tokenized continuation, yield one scheduler turn, and cancel it when a real inbound message arrives before dispatch; a synthetic continuation must be recognizably marked so it does not cancel itself.
7. **Preserve cross-surface review identity.** CLI/TUI review bridges may block on their native clarify callback. Gateway must use `adapter.send_clarify()` plus `clarify_gateway`, handle text/button replies before legacy Ralph review interception, and validate `plan_id`, `round`, and `review_attempt` still match the active `awaiting_review` state before calling `handle_review()`.
8. **Audit the Desktop renderer, not just the event handler.** A Ralph review is raised after `message.complete`, outside a model `clarify` tool-call part. Desktop may receive `clarify.request` and persist it in a store while rendering nothing if its only UI consumer is the live inline tool row (`messageRunning && tool result pending`). Keep the Python runtime authoritative for Ralph state, review validation, request IDs, and continuation priority, but make Desktop own review presentation and local interaction state. Emit semantic review metadata (`kind: "ralph_review"`, `interaction_id`, `plan_id`, `round`, `attempt`) rather than a server-selected layout such as `presentation: "dialog"`. Render Ralph review in the active chat scope as a non-modal card; reserve global modal overlays for sudo, secrets, and dangerous approvals. Keep ordinary model-initiated clarify calls on their existing inline UI to avoid duplicate prompts.
9. **Close the complete Desktop interaction lifecycle.** A review answer must produce a semantic resolution event (for example `clarify.resolved`) that clears the per-session attention indicator even though Ralph review has no matching `tool.complete`. For a revision path, emit exactly one `message.start` carrying an `internal_prompt` / turn-origin payload; Desktop projects it as a system transcript row before streaming the next assistant output. Do not synthesize a user message. An approve action correctly ends Ralph (`done`) and therefore must not be presented as a missing continuation.
10. **Diagnose lifecycle failures from persisted ownership, not UI symptoms.** Compare the plan owner stored under `ralph:<session>` with the actual planner turn session in agent logs. If the owner remains `active` with `turns=0` while the turn ended under another session ID, `after_turn()` never ran and no review event exists. Continuations must carry `Plan ID` in the canonical envelope; a legacy `(goal, plan_path)` fallback is safe only when it identifies exactly one active owner.

Regression coverage should prove: the Judge receives actual plan Markdown and task name `ralph_judge`; report persistence survives reload; choosing the Judge's revision queues the same-round continuation; CLI user input wins over a staged continuation; CLI/TUI use their clarify bridge; and Gateway Clarify validates review identity before dispatching a revision.

### Desktop Ralph review composer: attachments and voice

When extending the Desktop Ralph review/next-round card, treat it as a **constrained review composer**, not an instance of the ordinary chat `ChatBar`:

1. **Reuse narrow primitives, not chat orchestration.** Rich text / IME-safe editing, attachment pills, upload staging, and push-to-talk transcription can be reused. Do not import queueing, normal prompt submission, slash/@ command execution, Steer/Stop, history navigation, model selection, voice conversation, or TTS into a blocking review card.
2. **Keep review state request-scoped.** Text, attachments, and per-item upload state must be keyed by `sessionId + requestId`; never reuse the global chat-composer attachment store. On `clarify.resolved`, clear only the matching review scope.
3. **Preserve the `clarify.respond` string contract.** For Ralph-only `kind: ralph_review|ralph_next_round`, an optional attachment manifest may travel beside `answer: string`. Gateway must validate that the pending request is Ralph-owned, validate and normalize staged references, and append one canonical evidence block to the returned answer string before the existing Ralph handlers consume it. Ordinary Clarify remains text-only and backward compatible.
4. **Stage evidence before resolution.** Files/images selected on Desktop must use the existing session workspace staging path; remote clients must upload bytes and never send a client-only absolute path. A failed upload must not resolve the pending request: retain the draft, preserve successful items, expose the failed item, and allow a retry.
5. **Voice is dictation only.** Use the existing recorder/transcription primitive to insert editable text into the review draft. Never auto-submit a transcript, start a voice-conversation loop, or speak the assistant response. During transcription, prevent duplicate recording and review submission; restore focus afterward.
6. **Ralph semantics differ by kind.** Review may allow an attachment-only response only when the UI adds an explicit textual instruction. Next-round intake must require non-empty line-based goals; attachments are supporting evidence, not replacement goals.
7. **Test the full lifecycle.** Cover Enter/Shift+Enter, CJK IME composition, choice actions, staging failure/retry, session isolation, foreign-session rejection, `clarify.resolved` cleanup, and proof that review/next-round evidence reaches the existing plan owner without creating a second plan or synthetic user message.

### Lifecycle-tool extensions

When adding a lifecycle action to `ralph_execute`, trace the action through all three layers:

1. **Domain behavior** — reuse the matching `hermes_cli.ralph` state transition when it exists; reject terminal or absent plans rather than reviving them accidentally.
2. **Tool contract** — add the handler branch, include the action in the schema enum, and return the canonical plan view with the resulting status.
3. **Regression path** — test the full transition (for example, pause → persisted `paused` → resume → `active`) and assert the schema exposes the action. Run the focused workflow-tool test plus `tests/hermes_cli/test_ralph.py`.

This avoids a common partial implementation: the state machine supports an action, but the model-facing `ralph_execute` contract cannot invoke it.

## Ralph → Ultrawork v2 Handoff Audit

When a user reports that a completed Ralph plan did not produce a v2 route or an `ULTRAWORK_MANIFEST`, inspect the lifecycle contract before proposing a fix.

1. **Separate version concepts.** `template_version` describes the Ralph template; it is not necessarily the execution-manifest version. Report both independently.
2. **Inspect the persisted plan state.** Verify `execution_profile`, `execution_manifest`, `plan_digest`, status, and rounds for the affected `plan_id`; do not infer handoff success from a plan's `done` status.
3. **Trace the completion gate.** Check whether the execution profile participates in manifest approval. A non-executable/manual profile may intentionally bypass route compilation, leaving a completed planning artifact without a manifest.
4. **Check the plan grammar used by the route compiler.** Dynamic v2 routes commonly require stable `### Task N: ...` headings. A generic numbered `ordered tasks` list may satisfy a planning Judge yet be un-compilable into route nodes.
5. **Distinguish artifact and state contracts.** Some implementations compile a v2 route at approval and persist it only in `execution_manifest`, explicitly forbidding a Markdown `ULTRAWORK_MANIFEST` block for new plans. If the product expectation is an artifact-backed manifest, identify this as a contract mismatch—not a missing parser—and require a decision on whether approval may deterministically write the generated v2 block back to the designated plan file.
6. **Require regression coverage for the bypass.** Cover default/classified manual plans, completion without a manifest, non-null digest and v2 manifest invariants for executable plans, legacy-v1 import compatibility, and task-heading coverage.

**Pitfall:** A quality Judge that validates only general planning sections can approve an artifact that is not dispatchable to Ultrawork. Gate `done` on the correct execution-manifest invariant whenever the plan is meant to be executable.

## Verification Per Patch

Every patch needs a standalone verification step. Pattern:
```
read_file(path="target.md", offset=N, limit=M) → must contain "expected keyword"
search_files(pattern="unique-pattern", path="target.md") → expected count
```

**Good verification:** `read_file(offset=14, limit=12)` → 含 "15 个方法"、"`on_turn_start()`"

**Bad verification:** "read the file and check it looks right"

## Failure Recovery Per Patch

Every patch needs a recovery path for when `old_string` doesn't match:
1. `read_file` the target area to confirm actual text
2. Adjust `old_string` to match actual content
3. Retry patch — max 2 retries before reporting blocker

## Full-Review Checklist

After all patches applied, run automated checks:
```
search_files(pattern="~/\\.hermes", path="target.md")   → 0 hits (no hardcoded paths)
search_files(pattern="old-convention", path="target.md")  → 0 hits (conventions updated)
search_files(pattern="new-feature", path="target.md")     → ≥ N hits (feature propagated)
```

## When to Use This vs Generic `plan` Skill

| Scenario | Use |
|----------|-----|
| One-shot plan, no iteration expected | `plan` skill |
| Ralph mode, user will iterate | **This skill** |
| Plan needs exact patch specifications | **This skill** |
| Plan needs verification commands | **This skill** |
| Evidence required from source code/docs | **This skill** |

## Pitfalls

- **Don't hardcode line numbers for downstream patches.** When P2a inserts 50 lines, P3's old_string is at a new position. Use `search_files` to locate before each patch.
- **Don't paraphrase old_string.** Copy-paste exactly from the file, including whitespace and indentation.
- **Don't skip verification.** A patch that claims success without `read_file` confirmation is not done.
- **Don't rewrite the entire plan for small additions.** Use surgical patches — the existing structure is valuable.
- **Import external plans through the designated artifact.** In an active Ralph session, inspect the source read-only, then write a concise reference import into the designated Markdown file: source path, inspected scope, immutable constraints, task/test registry, and the refinement protocol. Keep the detailed source immutable and cite it as authoritative. Do not bypass the designated-file boundary by copying files or using shell/code write paths.
