---
name: analyzing-codebases
description: "Systematically orient in unfamiliar codebases, including structure, data flow, and size/composition metrics. Use when the user asks to analyze, review, explain, or measure a repository. NOT for writing execution plans (use plan) or debugging a specific bug (use systematic-debugging)."
version: 1.0.0
author: Masia
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Codebase Analysis, Architecture, Orientation, Reverse Engineering, Project Review]
    related_skills: [plan, systematic-debugging]
---

# Analyzing Codebases

Systematically understand an unfamiliar codebase fast. The goal is a mental model of: tech stack, module boundaries, data flow, and complexity centers — enough to answer follow-up questions and locate code without re-reading everything.

## When to Use

- User says "分析这个项目" / "analyze this project" / "what is this codebase"
- User drops you into a repo and asks open-ended questions about how it works
- User asks "how does X work in this codebase" where X spans multiple files
- You need to locate a feature across a large multi-subsystem project

## The Orientation Sequence

Run these in **batches** — issue independent reads/searches together, not one at a time. The order is from cheapest-highest-signal to most-expensive:

### Batch 1: Manifest + Structure + Docs (parallel)

```
read_file:  package.json / pyproject.toml / Cargo.toml / go.mod  → tech stack, deps, entry points, scripts
terminal:   ls -la root                                          → all files + subdirectories at a glance
search_files: README.md / AGENTS.md / CLAUDE.md / .cursorrules   → architecture intent, conventions, constraints
```

The manifest tells you: runtime, frameworks, what the project *does* (description field), how to run it (scripts), and dependency surface. `ls -la` reveals subsystems (subdirectories) and tooling (Dockerfile, compose, CI configs). README/AGENTS docs encode the author's mental model — read them before the code.

### Batch 2: Schema + Compose + Git log (parallel)

```
read_file:  *-schema.sql / migrations / prisma.schema  → data model = business logic skeleton
read_file:  Dockerfile / docker-compose*.yml           → deployment topology, multi-role design
terminal:   git log --oneline -20 && git branch -a     → what's actively being worked on, branch structure
```

**Schema is the highest-signal artifact.** Table names, foreign keys, status/state columns, and index patterns reveal the domain model and state machines without reading any business logic. A `task_logs` table with `status` + `progress` + `job_key` tells you there's an async task system. A `phone_assets` table with `in_use` + `locked_at` + `locked_by` tells you there's a resource-locking state machine.

Docker compose files reveal multi-node topology (activation/registration/sales roles) and shared state (remote MySQL). Git log shows the *current* development focus — recent commits are what the user cares about most.

### Batch 3: Complexity Centers + Entry Points (parallel)

```
terminal:   wc -l major-*.js major-*.py | sort -n      → identify the 3-5 files holding all the complexity
terminal:   head -80 server.js / main.py / index.ts     → require/import graph at the top of the entry point
read_file:  top 50-60 lines of the main orchestrator    → config constants, retry limits, key URLs
```

`wc -l` sorted ascending instantly reveals where the real logic lives. In a 30K-line project, 2-3 files often hold 60%+ of the code — those are your complexity centers. Read their headers to get the import graph and config constants.

### Batch 4: Subsystem Deep-Dive (serial, only if asked)

If the project has subsystems (e.g., `phone-reg/` inside a larger project), and the user asks about a specific flow:

```
1. Read the subsystem's own package.json / entry point
2. Read the subsystem's worker/orchestrator (the file that spawns/coordinates)
3. Read the protocol/core files (the actual business logic)
4. Trace data flow: what writes to DB, what reads, what state transitions happen
```

For each subsystem, identify: its own storage (SQLite vs shared MySQL), its own port, its own frontend, and how it talks to the parent system (shared DB tables, HTTP, spawn child processes).

## Dead-Code Cleanup Audit

For Python cleanup after an implementation is replaced:

1. Scope the review to the working diff or last relevant commit; exclude generated/ignored mirrors from symbol counts.
2. Combine AST definition/reference counts, exact repository searches, and `git blame`/history. No single dead-code tool is sufficient evidence.
3. Remove the complete orphan closure: dead entrypoint, exclusive helpers, imports, constants, dataclass fields, state keys, and unused parameters.
4. Preserve public aliases, persisted configuration keys, and historical state-machine action names unless compatibility and migration evidence proves removal safe.
5. Verify the test interpreter before the full suite, especially when packaging tests spawn `sys.executable -m pip` and require the build backend in that same environment.
6. Report correctness bugs discovered during cleanup separately rather than silently broadening the refactor.

See `references/python-dead-code-cleanup.md` for the evidence recipe, risk tiers, interpreter checks, and final gates. For broader reachable legacy surfaces, use the later Architecture-Replacement Cleanup Audit.

## Shared-Workspace Change Boundaries

When orienting before a scoped implementation in a dirty or concurrently edited repository, record `git status --short` first. Treat pre-existing modified paths as off-limits unless the task explicitly names them. During handoff, verify the implementation's own footprint with `git diff --name-only -- <allowed paths>` and `git diff --check`; do not rewrite unrelated tests to conceal a changed architectural contract. If a targeted legacy test conflicts with the new requested contract, run it once and report the exact incompatibility rather than adding a compatibility shim that defeats the new behavior.

**Transient shared-source failures.** If a previously passing targeted test suddenly fails while importing or initializing a concurrently edited schema/config module, do not repair that unrelated path. First run a minimal isolated initialization/import probe against the current source; if it succeeds after the concurrent edit settles, rerun the targeted test and record the transient condition separately. For the final full suite, preserve exact failures outside the allowed paths as blockers/owner follow-up rather than broadening the patch to make unrelated assertions pass.

**Read-only audit under an active writer.** A long audit can observe several different implementations if another agent edits the scoped files mid-run. Fingerprint the relevant diff or files before behavioral probes, re-read changed callsites when the fingerprint changes, and rerun only the affected deterministic probes against the final snapshot. Label evidence by snapshot and never combine an early source reading with later test output as though they described one implementation. Confirm final status separately and report zero audit footprint.

**Workspace interpreter identity.** Prefer `python -m pytest` over a bare `pytest` launcher when verifying checkout changes, especially on Windows or systems with several virtual environments. A PATH-resolved pytest executable may belong to another interpreter and import an installed package copy, producing misleading `ModuleNotFoundError` failures for files that exist in the checkout. When import behavior disagrees with the filesystem, compare `sys.executable`, the launcher path, and the imported module's `__file__`; then rerun through the intended interpreter instead of repeating the same pytest command.

## Cross-Surface Command Integration Audit

When analyzing a command or workflow that spans CLI, messaging gateway, TUI protocol, Desktop, and web clients, trace the **entire state-machine path**, not merely the command registry.

1. **Registry and parsing** — locate the canonical command definition, aliases, argument hints, and every surface's parser/dispatcher.
2. **State ownership** — identify the durable store, session-key translation at each boundary, and whether lifecycle state is profile-scoped. **Do not assume every adjacent lifecycle uses the same identifier:** a planning/workflow state may be keyed by a durable routing/session key while transcript-backed goals or history use a storage session ID. When repairing one lifecycle's key, preserve sibling lifecycles' existing key contract and add a regression test that exercises both paths.
3. **Kickoff transport** — distinguish a text acknowledgement from an actual agent turn. On each surface, verify that starting/resuming returns or enqueues a real prompt (`pending_input`, adapter FIFO, RPC `send` directive, or `prompt.submit`). Use the shared continuation builder rather than a hand-written acknowledgement so template-specific instructions and execution-manifest requirements survive every transport.
4. **Post-turn transitions** — trace the hook that reads the final response, persists the next state, emits status/review UI, and schedules the next phase. Check that user messages preempt automatic continuations.
5. **Safety boundary** — find enforcement both in the prompt/handler layer and at the shared tool dispatcher. Also inspect busy-session behavior: read/status commands may be safe while start/resume/mutating transitions may not be.
6. **Typed RPC parity** — for TUI/Desktop/web, inspect both `slash.exec` and fallback/direct `command.dispatch`. A successful `slash.exec` may itself return a typed `{type: 'send'|'exec'|...}` directive; clients must parse it before assuming `{output}`.
7. **Surface parity and tests** — compare subcommands accepted by every frontend. Query verbs implemented in one transport must not fall through to a destructive/default action in another. Name the exact missing tests alongside each gap.

Report the result as: **shared core → per-surface route → lifecycle continuation → concrete gap → exact file/function/test**. Do not recommend a code change without stating which transport contract it preserves.

## Live File-Canonical SQLite Store Health Audit

Use this when the user asks for the current state of a live SQLite-backed memory, curation, retrieval, or workflow store.

1. **Inspect the direct source read-only.** Open SQLite with `mode=ro`; record a UTC snapshot time and database mtime, then check `quick_check`, foreign keys, contiguous migrations, logical table counts, state distributions, timestamp ranges, and pending/nonterminal work. Report content lengths and counts rather than private bodies.
2. **Separate substrate health from semantic readiness.** A valid schema and zero foreign-key violations do not mean the application is healthy. Report independently: database integrity, canonical-file integrity, candidate/review reachability, accepted-document visibility, retrieval materialization, optional projection state, and current background jobs.
3. **Respect content authority.** In a file-canonical design, verify every active metadata row resolves to an existing file whose hash matches. Treat non-empty compatibility body columns or rows without source metadata as migration residue, not valid canonical content. Count exact migration gaps by artifact class.
4. **Exercise bounded public reads.** Compare SQL state with the application's status/tree/list/read surfaces. A status endpoint can report candidate counts while candidate reads still fail on missing canonical files; include both results.
5. **Account for live mutation.** Background workers may update the database during analysis. Gather broad structure first, investigate defects, then take one final compact snapshot and label its timestamp. Do not combine counts from different snapshots without saying so.
6. **Diagnose hash-fence failures at the byte boundary.** When staged-write hashes fail selectively on Windows, compare the persisted `after_hash` with SHA-256 of raw input and newline-normalized input. Trace the producer hash, file-write newline mode, and verification read. Hashing raw CRLF text before a universal-newline `read_text()` verification deterministically produces a false conflict; use one explicit byte or newline-canonicalization contract end to end.
7. **Classify empty projections truthfully.** An available optional index with zero tables/records can be a healthy projection of an empty accepted store. Do not call it an indexing failure unless accepted sources exist or retry/error state proves one.
8. **Audit hash deletion by semantic role, not by name.** Build a `file:line → purpose → delete/retain/rename` matrix before removing any `*hash*`, `*digest*`, or checksum field. Keep file-integrity, optimistic-concurrency, crash-recovery, idempotency, dedupe, snapshot, and audit-provenance hashes unless an exact caller/history fence proves them redundant. Distinguish canonical-text hashes from raw-byte hashes, and inspect legacy pending journals before changing either representation. A duplicated alias inside a versioned artifact may be retired only with backward-compatible readers; it is not evidence that similarly named transaction-journal fields are redundant.
9. **Design legacy-body migration as an explicit operator state machine.** Use `plan → apply → verify → rollback`, exact expected counts per artifact class, create-only publication, production-API read-back before clearing exact DB rows, body-free audit receipts, and a drift-fenced pre-apply backup. A SQLite body may be used once only when its canonical destination is absent; an existing file is a conflict or already-migrated artifact, never an overwrite target. Trace whether a supposedly read-only `verify` path initializes schema or rewrites a manifest, and do not infer exact migration counts from a truncated issue list.
10. **Do not invalidate an outer SQLite cursor during audit aggregation.** Fetch the outer result set first or use a separate cursor/connection for nested lookups. Executing another query on the same cursor while iterating it can silently terminate the outer iteration and produce plausible but false counts; rerun any affected aggregate after correcting the cursor ownership.

See `references/live-sqlite-file-canonical-health-audit.md` for bounded query recipes, public-surface cross-checks, migration-gap checks, and the CRLF hash diagnostic. See `references/hash-deletion-scope-audit.md` for semantic inventory, mixed legacy-journal contracts, safe deletion candidates, and regression gates. See `references/explicit-file-canonical-migration.md` for eligibility, create-only publication, trigger-safe body clearing, idempotent recovery, rollback fences, and tests.

## AI Candidate Review → Automatic Promotion Audit

Use this when a memory, curation, moderation, or learning system must replace human candidate review with an independent AI verdict that automatically accepts/promotes or rejects the persisted candidate.

0. **Establish content authority before tracing persistence.** Do not assume SQLite or any database is the source of truth merely because it contains body-like columns or the current code writes projections from it. Read the user/architecture contract and classify canonical content, metadata/control state, quarantine/staging, and rebuildable projections. In a file-canonical design, reviewers must reread immutable staged files plus evidence; accepted files outrank SQLite metadata during recovery; metadata, summaries, FTS, and vectors rebuild from files; and stale database content must never overwrite canonical documents. Report current implementation disagreement separately from the required target contract.
1. **Start from persisted state, not producer output.** Trace `candidate creation → immutable rendered/versioned form → evidence links → reviewer request`. “Persisted” means the declared canonical candidate artifact—database version or staged file—not automatically a database row. The reviewer must reread that real candidate version and evidence after creation; passing the extractor/classifier's in-memory proposal directly is not independent review.
2. **Prove every candidate is reviewable.** Find all creation paths, including tools, CLI, lifecycle mirroring, extraction, imports, and derived candidates. A bare candidate with no rendered/versioned record cannot enter a promotion function that requires a latest version. Either render it before review, route it through an AI assembly stage, or remove the unsupported creation surface.
3. **Separate reviewer identity from model output.** Use a distinct callback/service from the producer. Build the request from stable candidate ID/version, rendered content, all linked redacted evidence, and claim-source spans. The host fixes the AI actor identity; the model must not choose or echo authorization-bearing IDs.
4. **Keep the verdict minimal and closed.** Prefer `{decision: approve|reject, rationale, evidence_id}` where `evidence_id` must belong to the request. Apply the request's candidate ID and expected version independently of callback output. Reject unknown fields, malformed decisions, oversized rationale, unrelated evidence, and stale versions.
5. **Audit both terminal branches symmetrically.** Approval and rejection must both validate that cited evidence belongs to the candidate/rendered claims. Check for asymmetries where promotion validates linkage but rejection merely checks that an evidence row exists.
6. **Distinguish functional state from operational durability.** Existing candidate lifecycle plus promotion/audit tables may already support the functional minimum with no migration. A migration is needed only when the requirement includes durable review attempts, model/prompt provenance, retry/backoff state, malformed-response audit, or multi-evidence verdict citations. State this decision explicitly.
7. **Define failure behavior without inventing a human fallback.** Callback exception or invalid output should fail closed and leave the candidate quarantined. Add a bounded rescan/retry path if fully automatic eventual resolution is required. Do not silently route to operator review when the contract says no human fallback.
8. **Audit public surfaces.** Search tool schemas, CLI commands, operations facades, prompts, docs, and tests for manual review routes. A background AI path does not satisfy a no-human-fallback contract while `candidate_review` or CLI approve/reject remains exposed.
9. **Prove production reachability.** A callback injected only by tests is not integration. Trace the installed host/provider initialization and show the reviewer is wired in normal startup, or provide an internal production adapter with explicit failure handling.
10. **Test replay and visibility.** Cover persisted-input independence, approve→accepted visibility, reject→terminal rejection with no accepted projection, unrelated evidence, stale version, callback failure, replay/idempotency, startup recovery, and absence/disablement of manual review surfaces.

Report this class of audit as: **creation source → rendered/versioned seam → evidence bundle → reviewer callback → terminal transaction → retrieval visibility → remaining manual surface**. Include an explicit **schema migration: yes/no/conditional** verdict and the exact missing tests.

## Dynamic AI-Authored Memory Content Template Audit

Use this when the user defines profile-local prompts that create memory document bodies, especially when field names or cardinality come from conversation content.

1. **Separate three contracts before editing.** The memory-type template owns document content and organization. The outer extraction/controller prompt owns evidence IDs, source spans, trust/safety rules, JSON shape, candidate operations, and review state. Runtime integration owns loading, validation, rendering, persistence, and activation. Do not leak outer-protocol mechanics into a content-only template.
2. **Preserve the user's topology literally.** If entity name labels and attribute labels are dynamic, do not reinterpret them inside fixed `Properties`, `Relationships`, or `Entity Attributes` wrappers. Model one dynamic name field followed by any number of dynamic atomic attribute fields.
3. **Normalize without strengthening.** A field label may turn source language into a concise noun phrase, but its value and scope cannot exceed the conversation. `uses Windows` does not justify `Windows 10`; context-limited usage should not become an unrestricted permanent attribute.
4. **Use memory-type-specific body semantics.** Entities use dynamic name/property fields. Events preserve one bounded event and separate result from impact. Experiences preserve one problem/goal resolution process. Tools are normal one-tool usage-experience content prompts unless replacement semantics are explicitly requested. Trajectories preserve one user requirement from observable analysis through actual implementation and verification without reconstructing hidden chain-of-thought. Projects preserve one project's aggregated identity, current/planned state, architecture, decisions, blockers, risks, and open work. Identity is a privacy-minimized singleton summary of the user's stable identity and work.
5. **Keep content prompts content-only.** Do not add `Evidence Contract`, `Structured Semantic Output`, evidence-ID/source-span schemas, candidate lifecycle instructions, or review workflow unless the user explicitly asks that template to own them. Grounding requirements such as “use only the supplied conversation” remain valid content constraints.
6. **Use rendered-content examples.** Examples should demonstrate the target memory body, not an intermediate JSON protocol. Never invent details (`uses Windows` cannot become `Windows 10`) or fill unsupported sections with `Unknown`, `N/A`, or placeholders.
7. **Trace fixed-topology assumptions separately.** When asked to audit integration, inspect prompt construction, section whitelists, omission rules, renderer loops, body validation, patch anchors, path/slug rules, singleton identity gating, and tests. Do not silently broaden a request to create/edit prompt files into provider integration work.
8. **Separate storage from activation.** Verify the editable template exists, then independently prove whether production loads and enforces it. Report `stored`, `loaded`, and `enforced` as distinct states.
9. **Verify the requested boundary.** For content-only templates, check required body headings and confirm forbidden protocol terms are absent (`Evidence Contract`, `Structured Semantic Output`, `evidence_ids`, `source_spans`, `source_ref`).

Report the audit as: **conversation fact → memory-type body topology → normalized rendered content → forbidden protocol leakage → stored/loaded/enforced status**.

References:
- `references/dynamic-evidence-template-contracts.md` — worked dynamic-field and grounding pattern.
- `references/memory-body-prompt-template-audit.md` — complete entities/events/experiences/tools/trajectories/projects/identity contract matrix, privacy boundaries, runtime-gap checks, and verification probe.

## Directory-Summary Navigation Prompt Audit

Use this when a memory system aggregates accepted documents under a type directory into short and detailed summaries for later retrieval.

1. **Resolve snapshot versus delta semantics first.** A rebuild from all current accepted descendants produces a current-state navigation snapshot, even when triggered by one update. It cannot truthfully describe “what changed this time” unless the runtime supplies changed-document operations, before/after content, or the previous summary.
2. **Audit three integration layers independently.** Prove the prompt file is stored, the template type is allowed/loadable, and production prompt construction actually reads and enforces it. A manually created file may still be rejected by a type whitelist or bypassed by a hardcoded runtime prompt.
3. **Inspect payload sufficiency.** Titles and bodies can support topic aggregation, but reliable navigation also needs target directory, memory type, and document logical paths. True delta summaries additionally need action metadata and comparison state.
4. **Keep editable semantics separate from transport.** The template should define accepted-only grounding, directory boundaries, type-specific aggregation, topic indexing, conflicts/qualifiers, drill-down routing, and retrieval terms. The outer runtime should own exact JSON keys, input serialization, character bounds, strict parsing, and fail-closed behavior.
5. **Require two useful layers.** `summary` is a compact routing synopsis; `detailed_summary` is a structured topic → fact/state → document-path navigation index. Reject generic prose that adds little FTS/vector discrimination.
6. **Apply memory-type lenses.** Entities emphasize names/attributes, events time/result/impact, experiences problem/solution/verification, tools workflow/pitfalls, trajectories requirement/implementation/outcome, projects architecture/state/open work, identity stable work identity, and preference scoped collaboration defaults.
7. **Trace refresh and retrieval together.** Verify accepted/current visibility, descendant and ancestor refresh scope, output limits, indexed fields, downstream body-read escalation, and tests that prove semantic navigation—not merely JSON shape and length.

Report this audit as: **desired summary meaning → actual source set/payload → stored/loadable/enforced status → snapshot/delta verdict → navigation gaps → exact runtime or test changes needed**.

Reference: `references/directory-summary-navigation-prompt-audit.md` — payload contract, type lenses, integration checklist, and common failure modes.

## Lagged Prefetch and Bounded Memory Retrieval Audit

Use this when a memory provider combines next-turn prefetch caching, explicit search tools, directory summaries, lexical indexes, optional vectors, and canonical body reads.

1. **Separate automatic and explicit recall.** Trace completed-turn query → background worker/cache → next-turn `prefetch()` → request injection independently from tool/CLI search. Record which turn supplies and consumes the query; do not assume `prefetch(current_query)` searches the current query.
2. **Prove projection-to-result reachability.** A canonical body read, evidence IDs, or `sufficient=true` is not a useful recall result unless a public result reaches prefetch/tool serialization. Test summaries disabled/unavailable as a first-class mode.
3. **Enforce scope at every round.** Verify path, recursive, memory type, profile/session, and accepted/current filters separately for summary lexical, summary vector, hybrid merge, body-gap selection, fallback traversal, and serialization. Requested-scope telemetry must reflect actual execution.
4. **Name the implemented ranking truthfully.** Distinguish SQLite FTS/BM25 from an in-process substring scan, hash embeddings from semantic embeddings, concatenated hit lists from score fusion, and positional `1/rank` scores from relevance scores.
5. **Inspect sufficiency semantics.** Determine whether a real independent judge or lexical token coverage stops the loop; test punctuation, phrases, CJK text, cross-document coverage, and evidence-to-result binding.
6. **Audit goal-driven escalation as a state machine.** When types are omitted, verify AI routing uses a closed host-owned enum. Then trace selected-type summary FTS → AI sufficiency Judge → bounded accepted-only tree → AI selection of new unvisited documents → canonical body reads → at most the configured evidence-producing retries → grounded answered/partial/no-match output.
7. **Treat external prompts as versioned runtime inputs.** Verify each router/Judge/selector/synthesizer/summary template is stored, loadable, enforced at the production callsite, and snapshotted by hash for one search. Templates own semantics; host code retains schemas, scope, IDs, budgets, evidence authorization, and terminal state. Missing authoritative templates fail closed without a hidden hardcoded semantic fallback.
8. **Verify live deployment, not source alone.** Check selected provider, deployed-source identity, active-profile config parsing, provider initialization, backend capability, and one bounded status/search call. Tool schemas can remain advertised when initialization failed.
9. **Audit budget adoption.** Locate runtime reads for every advertised limit, ensure per-round deadlines reset per round, and identify unused configuration or hard-coded plan budgets.

Report: **live readiness → automatic route → explicit route → round table → projection reachability → verified defects → passing versus missing tests**.

Reference: `references/memory-retrieval-pipeline-audit.md` — timing, projection reachability, scope isolation, truthful ranking, runtime-readiness checks, and deterministic probes.

For standalone memory-provider changes that affect model-visible context structure, cadence, recovery, discovery purity, or initialization/rollback, also use `references/external-memory-provider-context-migration.md`. It covers host-call reachability, provider semantic layers versus host/built-in system-memory sources, persisted `api_content`/prompt-cache history, first-turn bootstrap, host-versus-plugin concurrency, frozen completed-turn identity, cadence watermarks, SOUL cache coherence, durable feedback handoff, semantic config migration, mechanical plan-DAG checks, inspection-only registration, and transactional rollback across manager-local and process-global tool/runtime state.

## Legacy Nonterminal Checkpoint and Loop Convergence Audit

Use this when a durable SQLite-backed provider retains old `pending`, `planning`, `executing`, `judging`, `running`, or `retryable` state after crashes, deadlines, callback loss, or migration.

1. **Separate status from resumability.** A retry flag, plan JSON, action enum, or snapshot hash does not reconstruct a process-local executor closure. Require durable redacted payload, valid artifacts, registry/template compatibility, a live deadline/lease, and a bounded resolver before preserving a retry.
2. **Trace parent ownership.** Map checkpoint → turn job, plan → run, materialization → retrieval intent, and source transaction → authoritative upstream payload. An abandoned child may need terminalization even when its parent payload can support a fresh attempt.
3. **Never synthesize success.** Recovery may choose failed-terminal, blocked, cancelled, stale, or a new generation-bounded attempt. It must not infer completed from partial actions, missing callbacks, hashes, or metadata.
4. **Recover in dependency order.** Quiesce and capture a cutoff; recover file transactions first; reconcile SQL/checkpoint state with compare-and-set updates plus append-only events; verify postconditions; only then start eligible workers.
5. **Make convergence replay-safe.** Decisions are functions of entity kind, before-state digest, and algorithm version. A second pass over unchanged state must write no rows and append no events.
6. **Preserve retries only with proof.** Validate payload presence, artifact hashes, current template/registry digests, owner/continuation identity, retry/deadline budget, and a fresh recovery generation that cannot collide with an abandoned idempotency key.
7. **Audit byte boundaries on Windows.** Raw-CRLF hashing followed by universal-newline text verification causes deterministic false hash conflicts. Use one explicit byte contract end to end; fix the producer/verification boundary before creating any fresh recovery attempt.
8. **Prove no semantic promotion.** Terminalization must not increase accepted documents, promoted candidates, committed transactions, or success counts. Test planning/retryable/executing/judging matrices, orphan checkpoints, ownerless retrieval, hash-only reasoning jobs, source rollback, CAS races, event dedupe, and second-pass no-op behavior.

See `references/legacy-nonterminal-convergence.md` for the resumability proof, domain decision matrix, deterministic reconciler, audit-event schema, stop conditions, CRLF diagnostic, and regression suite.

## Architecture-Replacement Cleanup Audit

Use this after a commit replaces a retrieval, orchestration, storage, or protocol architecture. Do not stop at reviewing the new diff: establish the canonical route, then audit every public surface, background worker, CLI, operations facade, smoke script, direct library caller, package export, registry, config key, and response serializer for old behavior that remains reachable or dead beside it.

1. **Prove reachability before removal.** Search tracked source, tests, scripts, docs, exports, registries, and dynamic access; then use AST/call-graph inspection to distinguish real callers from references inside a dead implementation.
2. **Use history as a removal fence.** Check blame, `git log -S`, and the parent revision to identify the original purpose and the exact transition that superseded it. Compatibility migration backed by old persisted defaults is not dead code.
3. **Report the dependency cone.** A dead old implementation often leaves exclusive helpers, imports, context fields, telemetry, constants, and tests. Remove the root path first, then only dependencies whose remaining references disappear with it.
4. **Separate low-level primitives from public retrieval.** Direct FTS may remain valid for integrity/smoke checks while being obsolete as a CLI or model-facing search. Rename/narrow the primitive or route the public surface through the canonical engine rather than deleting blindly.
5. **Compare sentinel semantics across callers.** `None`, omitted, and `[]` must not silently choose different architectures unless that distinction is explicit and named. Audit automatic/background callers separately from tool normalization.
6. **Trace new response fields to every consumer.** If the new engine returns synthesized information/citations but a cache or wrapper still serializes only legacy summary rows, run a body-only reachability probe and treat empty model-visible output as a defect.
7. **Audit fake knobs and stale registry vocabulary.** Every accepted config setting and allowed action needs a live runtime read/emitter. Settings used only by validation tests and actions referenced only by registry tests are residue, not capabilities.
8. **Check durability abstraction depth.** Flag broad persisted actions that hide several external AI calls, reads, judgments, or synthesis stages. Stage-level replay/provenance repair is RISKY architecture work, not mechanical cleanup.

Report each finding as `file:line → problem → concrete cost → suggested fix | confidence | SAFE/CAREFUL/RISKY`, with exact callers, history evidence, deterministic probes, and test evidence.

Reference: `references/architecture-replacement-cleanup-audit.md` — full caller fencing, response-adoption probes, compatibility classification, registry/config residue checks, and Chesterton’s Fence workflow.

## Durable Swarm Entrypoint, Status, and Transcript Audit

Use this when a durable execution runtime has both a direct/native entrypoint and a plan-backed entrypoint (for example, a native Kanban swarm versus a Ralph-approved-plan swarm). Treat entrypoint labels, status, creator routing, and lifecycle transcript delivery as one contract.

1. **Prove the two start actions are actually distinct.** Trace each action from UI label → RPC/slash transport → backend dispatcher → persisted `source_kind`. A planning/review composer is not a launch surface. If the native route can accidentally start planning, or the plan-backed route can accept an unapproved plan, report it as a contract break.
2. **Audit Desktop and TUI separately.** Desktop command allowlists may intentionally hide an otherwise valid TUI slash command. Do not infer UI parity from a CLI parser or plugin registration. Locate the actual Desktop action/palette/dialog and the TUI `slash.exec` / `command.dispatch` path.
3. **Start from the root status query.** A root task’s status must resolve the run's currently active attempt, not only an attempt whose `task_id` equals the root. Require: `source_kind`, source id/digest, run id, current phase, route, active attempt id/number/status, next eligible routes, and exact block reason.
4. **Follow lifecycle data across stores.** Runtime event tables are not automatically user-visible. Trace `runtime event → root/task event or durable outbox → creator subscription → surface-specific delivery → transcript row`. Check Global QA and final synthesis as well as normal route success/failure.
5. **Treat TUI routing as session-keyed.** A TUI/desktop slash worker often has `HERMES_SESSION_KEY` but no platform/chat id. Creation must persist a `platform='tui'`, `chat_id=session_key`, and session-key subscription without inventing a recipient. The TUI server must then poll/deliver those rows itself; a messaging-gateway watcher cannot deliver a `tui` subscription through a messaging adapter.
6. **Separate live visibility from durable transcript persistence.** Emitting a websocket `message.complete` can show a lifecycle event live without storing it for session resume. State explicitly whether the requirement is live-only or durable, and test the relevant invariant.
7. **Test the transport contract.** Add tests for both root types, exact action labels, no Native-to-planning call, approved-plan-only Ralph dispatch, root-status active-attempt resolution, per-session routing/no hardcoded recipient, lifecycle dedupe, Global QA visibility, and background-session transcript attribution.

## Durable Planning → Hierarchical Execution Contract Audit

When reviewing an upgrade from a flat approved-plan manifest to a hierarchical route/child-execution model, audit the **boundary first**. It is common for plan parsing and compiler tests to land before the executor can consume the new manifest.

1. **Versioned handoff compatibility.** Trace `extract/validate manifest → approval/digest persistence → execution trigger → workflow creation`. For every new manifest version, verify the executor branches by version rather than unconditionally indexing a legacy field (for example, `manifest["steps"]`). Run the smallest v2 handoff test directly; a parser-only green test is not integration evidence.
2. **Immutable route vs. mutable child state.** Confirm route-node definitions preserve `task_ref`, source refs, acceptance/evidence contracts, and dependency edges; runtime child graphs, evidence, retries, and handoffs must be stored separately. A dependency-blocked task must not materialize or dispatch its child graph early.
3. **Coverage is multiplicity-sensitive.** Verify every source task is covered **exactly once** by a route task node. Set equality alone misses duplicate task references; add a duplicate-plus-complete-coverage regression as well as missing and unknown-reference tests.
4. **Source-backed refinement.** A child prompt must receive selected source-section text, frozen route background, and approved upstream handoffs—not merely section names/titles or a full prior transcript. Test unique sentinel text from global/task sections and handoff artifacts survives into activated-child context.
5. **Closure and propagation gates.** A parent task closes only after child evidence plus independent review passes. Prove failed/exhausted child work blocks the parent and leaves downstream nodes pending; prove a successful parent persists a concise handoff available after reload to the next dependency-unblocked task.
6. **Judge contract alignment.** If an independent judge cites evidence paths, validate citations against persisted raw evidence rather than merely requiring non-empty strings. Route/child review must judge child → parent closure, not only legacy flat workflow steps.
7. **Surface parity.** Exercise model tool/registry dispatch, gateway, and TUI `slash.exec → command.dispatch → {type:"send"}` paths. Assert the same durable session key and first-route continuation across surfaces; status/read verbs must not accidentally start a route.

Report each result as **manifest/route source → executor state owner → surface transport → observed result → missing test or contract**.

## Dynamic User-Profile Modeling Audit

Use this when a memory or agent plugin claims to model a user across turns or sessions. Treat the feature as a layered state-and-authority system, not merely an LLM summary.

1. **Separate the profile layers first.** Distinguish dynamic user representation, accepted long-term user memory (for example preferences or identity), session working state, and agent behavior policy. A profile card is not accepted knowledge, and user traits must not silently become agent-policy edits.
2. **Trace the complete lifecycle.** Follow completed turn → context stripping → queued inference → bounded reasoning → validation → persisted profile/session artifacts → next-turn injection → post-answer adoption feedback. Verify production callback wiring, not only direct model tests.
3. **Audit every influential field for provenance.** Structured insights may carry confidence and evidence refs while free-form `user_representation`, profile-card, summary, or focus fields have only length checks. Identify which fields are injected, which are independently reviewed, and whether their claims can be audited back to source evidence.
4. **Require contradiction and supersession semantics.** Append-only insight merging cannot correct a changed preference. Check for explicit active/contradicted/superseded/stale states, version-fenced revisions, confidence decay, and tests where a later user correction removes the old behavioral effect rather than merely adding opposite text.
5. **Resolve cross-layer authority.** Dynamic profile text and accepted preference/identity documents can disagree. Define and test a precedence order such as current explicit instruction → current correction → current accepted memory → verified profile insight → inferred conclusion → old summary/card. Do not leave contradictory blocks for the downstream model to arbitrate implicitly.
6. **Audit relevance and feedback coverage.** Determine whether profile fields are query/topic-fenced or injected unconditionally. Confirm adoption or usefulness feedback covers every influential field—not only insight IDs—and that ignored/no-opportunity semantics affect ranking truthfully.
7. **Prove authoring as well as retrieval reachability.** A declared identity template or explicit-only memory type is incomplete if no public or host-owned path can create, review, accept, revise, and revoke it. Search call sites for the renderer and creation transaction rather than inferring capability from schemas.
8. **Keep review exhaustion fail-closed.** A reviewer repeatedly requesting revision must end as rejected, blocked, or exhausted. Never promote a user-profile candidate merely because a revision quota expired.
9. **Check concurrent profile writes.** Reasoning usually occurs outside the write lock. Require a source/version fence or conflict-aware merge for free-form profile fields; non-empty stale snapshots must not overwrite newer cross-process updates.
10. **Run semantic probes, not only schema tests.** Cover cross-session warmth, new-session cold grounding, changed preference, stale-insight removal, topic switch, dynamic-versus-accepted conflict, adoption ranking, identity creation, restart loss/recovery, and concurrent writers. Report tests that only pass empty profile fields separately from real profile-behavior coverage.

Report this audit as: **profile layers → turn/inference/injection lifecycle → field/provenance matrix → correction behavior → authority conflicts → feedback/relevance → authoring reachability → concurrency/durability → passing and missing semantic tests**.

Reference: `references/dynamic-user-profile-modeling-audit.md` — field matrix, deterministic correction probe, authority-order checklist, and common false-positive capability claims.

## Lifecycle Cadence Migration Audit

Use this when analyzing a change from idle/session-end/background-batch processing to per-turn or per-event processing. Treat it as a state-model migration, not a timer tweak.

1. **Define the event boundary precisely.** Distinguish a completed user→assistant turn from an internal model/tool-loop iteration, turn start, and true session end. Locate the host callback that receives the finalized, non-interrupted event and verify whether it runs inline, on a serialized background worker, or concurrently.
2. **Trace production reachability, not test injection.** A callback supplied manually by tests is not a production implementation. Follow provider construction and initialization from the real loader and prove the classifier/planner/executor dependency is wired in normal startup.
3. **Audit persisted identity cardinality.** A checkpoint keyed only by session cannot safely become a per-turn queue: successive turns may overwrite or cancel each other. Require an idempotent event/job key derived from stable event watermarks, durable FIFO semantics, bounded retries, and restart recovery.
4. **Revisit cancellation semantics.** New input may legitimately cancel an idle snapshot, but it must not cancel extraction for a previously completed turn. Preserve interrupted-turn exclusion at the host boundary rather than guessing from partial provider state.
5. **Bound the evidence window.** When the host passes full conversation history after each turn, extract only the current-turn delta. Reprocessing the trailing N messages causes duplicate evidence, token growth, and candidate churn.
6. **Check persistence ordering and privacy amplification.** If the pipeline persists every message before deciding whether it contains a durable signal, per-turn cadence turns the evidence ledger into a transcript archive. Prefer ephemeral redaction/classification first, then atomically persist only cited evidence plus quarantined candidates.
7. **Separate extraction from activation.** Per-turn candidate extraction does not imply next-turn recall when promotion/review remains explicit. Report freshness of candidate creation and freshness of accepted-memory visibility as separate contracts.
8. **Align configuration with runtime.** Remove or migrate obsolete idle-delay settings without breaking existing profiles, and verify configured limits are actually read by the live path rather than shadowed by hard-coded constants.
9. **Test overlap, replay, and lifecycle edges.** Cover two rapid completed events, duplicate delivery, interrupted events, session switch, process restart, retry/backoff, no-signal privacy, current-event slicing, and production-loader dependency wiring.

For a concrete Hermes memory-provider source map, see `references/per-turn-extraction-audit.md`.

## Plan-Implementation Audits in Split Core/Plugin Deployments

When auditing a plan implemented across a core repository and an installed plugin, treat the source boundary, persisted-state boundary, and test boundary as first-class acceptance criteria.

1. **Record each location's provenance independently.** Check core Git status/log separately; verify whether an installed plugin is a Git checkout. If it is not, state that source-history verification is unavailable.
2. **Trace both entrypoints to their durable owner.** Follow UI/CLI → adapter → run creation → route/attempt tables → completion consumer. A shared DTO is not proof of a shared controller: flag remaining parallel run/route/attempt tables or direct lifecycle transitions.
3. **Audit report and Judge identity structurally.** Completion reports must bind active run, route/child, phase, attempt, and frozen source/spec digest. Judge citations must resolve to persisted raw Dev/QA evidence; non-empty citation strings are not proof.
4. **Check root status separately from phase-card status.** A root often is not an attempt. Require root status to resolve the active run attempt, route, phase, attempt state, next eligible routes, and block reason.
5. **Run isolated and ordered tests.** A green isolated test is not full-matrix evidence. Run focused tests alone and in planned order; module/registry reloads can make monkeypatches target stale modules and silently invoke live integrations.
6. **Validate deployment against the real installed layout without mutation.** Run deployment dry-run with defaults, prove source/target are distinct, inspect installed manifest/version, plugin discovery, and gateway health. Fixture-only deploy tests do not prove the installed path.
7. **Extend worktree review to children and reviewers.** Require child code attempts to have isolated registered worktrees; verify reviewers receive frozen candidate SHA/artifact references and dirty/drift/conflict paths fail closed.

### Loop, provenance, configuration, and packaging checks

A green full suite is necessary but not sufficient when a plan requires a persisted state-machine kernel or a deployable plugin artifact.

1. **Trace the inner loop, not merely its wrapper.** Follow each logical round through the adapter. Flag a raw `for`/`while` multi-round controller inside one kernel `execute` callback when the plan requires one persisted `loop_round`, validated plan, and judge transition per logical round. Outer-wrapper tests do not prove per-round persistence, cancellation, idempotency, or retry semantics.
2. **Compare declared configuration to runtime sources.** For every planned setting—timeouts, queue bounds, retries, idle thresholds, feature gates, and model input/output bounds—locate the runtime read path. A hard-coded literal where the plan calls for profile configuration is a contract deviation even if it matches the default.

   **Configurable-default audit.** Verify four links as one contract: (a) the schema/default object declares the setting, (b) profile merge and validation accept it, (c) the live service instance reads its effective profile value rather than an import-time constant, and (d) prompt construction and output validation use the same effective value. Preserve named constants only as compatibility aliases for defaults; they must not override a configured profile. Add a focused test that writes non-default values, asserts persistence, proves the generated bounded input reflects them, and proves an over-limit response is rejected.
3. **Audit provenance at the capture caller.** Nullable ledger columns and schema tests do not prove provenance is recorded. Confirm callers pass available session/message/tool identifiers into the ledger.
4. **Inspect the built archive, not only source or installer behavior.** After a successful wheel build, list archive members. Verify required package data is present and development bytecode/caches are absent. A direct-copy installer can work while a distributable wheel is incomplete or dirty.
5. **Separate verified behavior from plan conformance.** Report full-suite and smoke-test passes in their own evidence section, then separately list structural contract gaps with source lines; do not downgrade a state-machine violation because adjacent tests are green.

Report a criterion table with **pass / partial / fail**, exact `file:line` evidence, a high-severity section, and a test-evidence section separating isolated green coverage from failing or missing integration coverage.

For end-to-end standalone Hermes plugin verification—including deployed-source hash parity, argparse CLI registration, test-package shadowing, disposable-home smoke tests, and clean-wheel member checks—use `references/hermes-plugin-verification.md`.

## Host-Owned Structured LLM Contract Migration Audit

Use this when a plugin is being migrated from a supervised-agent or raw chat-completion path to a host-owned structured-completion facade.

1. Read the facade implementation and its tests, not only the public signature. Record the exact keyword-only call shape, result DTO, parse-failure behavior, schema-validation dependency, timeout forwarding, and audit-only fields.
2. Separate three compatibility layers: host injection (`ctx.llm` or equivalent), plugin adapter return type, and existing downstream parsers/validators. A correct facade call can still be unreachable through a legacy fake collector or loader context.
3. Treat `parsed=None` as a normal structured-result state that the plugin must fail closed on; do not infer success from non-empty raw text or silently issue a second paid completion.
4. Verify schema enforcement in the deployed dependency set. An optional validator that is absent by default turns a schema into a provider hint, not a local correctness guarantee; retain plugin-side top-level/type checks and downstream semantic validators.
5. Preserve strict raw-text checks deliberately. Re-serializing a parsed object can erase duplicate-key evidence or normalize malformed output that legacy parsers correctly rejected. When compatibility requires strict parsing, validate `parsed` for structured success but return the original text to the established parser.
6. Distinguish parameter semantics: request timeout versus workflow deadline, purpose as audit/log metadata versus routing, trusted system prompt versus untrusted input blocks, and host instructions versus user-supplied content.
7. Build the smallest TDD matrix around: one exact structured call, `parsed=None`, schema error/no retry, trust-boundary separation, registration using only the host facade, and an upstream loader/collector injection test. Keep existing strict-parser and input-bound characterization tests green.
8. **Inventory call sites with an AST completeness fence.** List every wrapper and underlying runtime call with line number and enclosing function. In a second AST pass, find invocations of callable parameters and callable attributes; classify each as production-reachable AI, optional injection seam, deterministic callback, test-only callback, or dead/legacy surface. Text search supplies context but is not sufficient evidence that all calls were found.
9. **Respect explicit scope without losing wiring evidence.** If the user excludes adapter/runtime files from the call inventory, omit their calls from the result but inspect them when necessary to prove callback wiring, default adapters, and literal purpose propagation. State this distinction instead of treating excluded files as unreadable.
10. **Separate literal and logical purpose.** If several callers share one literal `purpose`, report that exactly and classify their real roles separately; do not present proposed purpose names as existing code. A single dynamic helper may dispatch several incompatible stage contracts, while one literal purpose may hide incompatible legacy and production shapes.
11. **Describe the accepted contract, not merely the prompt.** Compare prompt-required fields, validator-required fields, consumed fields, legacy branches, defaults, early-return shapes, truncation/deduplication, callback envelope conventions, and the current extra-field policy. Treat drift among them as a migration blocker.
12. **Generate one host-owned schema per logical purpose.** Include exact required sets, `additionalProperties`, enums, bounds, and request-bound `const`/`enum` values. For `payload == expected_plan`, prefer a root `const` schema and retain the equality/hash validator. Record any behavior tightening—such as rejecting previously ignored extras or making an optional field required—rather than describing it as current behavior.
13. Report the migration boundary as `host context → facade call → result gate → compatibility adapter → downstream validator`, then name any upstream loader change that must land first. Also identify semantic checks JSON Schema cannot replace: cross-array cardinality, evidence/span membership, active-record ownership, stale version/hash fences, template parsing, replay/after-image equality, and TOCTOU checks.
14. **Close read-only audits cleanly.** Record the initial dirty-worktree baseline and verify final status is unchanged. Separate pre-existing modifications from audit footprint and report unreachable legacy callsites separately from production migration scope.

See `references/host-owned-structured-llm-migration.md` for the call-site evidence matrix, schema-design checklist, test matrix, and common collector-injection blocker.

## Plugin Agent API Compatibility Audit

Use this when a plugin's host-owned Agent call fails at runtime even though plugin unit tests are green.

1. Read the installed facade implementation and exact runtime signature; when the host checkout is dirty, compare committed and working-tree signatures.
2. Trace injection through every wrapper/proxy to determine whether kwargs are transformed or forwarded unchanged.
3. Reproduce with the real facade or a deterministic host constructor and record whether the underlying runner executed.
4. Treat `run(self, **kwargs)` fakes as signature-blind. Add a strict keyword-only fake or real-facade seam test that rejects nonexistent keywords.
5. Establish compatibility from host history. Do not add speculative dual-keyword retries when the facade used one spelling from inception or did not exist in earlier hosts.
6. Distinguish exact tool names from toolset names. Resolve the proposed toolset to concrete tools before calling a keyword swap safe.
7. Report functional compatibility and authority preservation separately. A toolset-level fix can restore execution while granting write tools to a workflow documented as read-only.
8. Never catch broad `TypeError` and rerun with another keyword; an internal post-execution error could duplicate a paid Agent run.

Reference: `references/plugin-agent-api-compatibility.md` — source/history fence, strict-fake RED recipe, wrapper trace, toolset expansion check, and report format.

## Acceptance-to-Task/Test Coverage Audit

Use this when reviewing an implementation plan against an existing codebase. Build a multiplicity-sensitive matrix of **Acceptance criterion → owning Task → changed production files → focused test → release verification**. An Acceptance statement is not covered merely because a Task mentions the behavior.

1. Flag every criterion with no explicit runtime Task, no focused test, or no executable verification command. Pay special attention to sibling settings where one cadence/budget is implemented and another is only declared.
2. Trace each planned behavior to the current owning callsite. Compare Task file lists with the real change cone, including public entrypoints, policy routers, persistence DTOs, physical schema migrations, compatibility readers/writers, and context filters.
3. Audit legacy migration on both load and direct save/update paths. A test that loads an old file and later saves an unrelated key does not prove a caller can submit the deprecated key through the writer.
4. Treat independent budgets as a configuration contract: separate defaults, validation, persistence, runtime reads, and a non-default test proving one budget cannot consume the other.
5. Parse the Task DAG and compute transitive reachability. Report unordered Tasks that write the same file, Tasks that consume schema/state introduced only by a downstream Task, and recovery Tasks that do not depend on every producer of the state they recover.
6. Enumerate all production injection/transport entrypoints. A canonical renderer does not prove strict layering while a first-turn/system-context or legacy wrapper path can still emit an extra public block.
7. Separate baseline-green evidence from plan completeness. Existing tests passing does not close missing future acceptance coverage.

See `references/plan-dag-acceptance-coverage-audit.md` for a compact evidence matrix, DAG-overlap probe, configuration checks, and report format.

## Cross-Surface Feature Rename and Protocol Migration Audit

Use this when a feature name appears across CLI/slash commands, model tools, Python/TypeScript identifiers, transport events, persisted state, execution handoffs, plugins, skills, and documentation. Treat the rename as a contract migration, not a repository-wide replacement.

1. **Validate semantics before vocabulary.** Describe the current state machine from source and compare it with what the proposed name promises. If behavior is planning/approval while the new name implies elicitation/interview, report the mismatch explicitly and separate pure rebranding from behavioral realignment.
2. **Inventory canonical surfaces without double-counting mirrors.** Exclude worktrees, installed copies, generated package metadata, caches, archived skills, and historical plans from the primary source count. Report those separately when they still affect deployment or compatibility.
3. **Build a naming-layer matrix.** Cover user labels and slash commands; model-visible tool names; modules/classes/constants; event and clarify-kind tokens; persistence keys/tables/columns/IDs; downstream source-kind fields; deployed plugin commands/tools; tests/docs/skills. Prefer neutral names at downstream boundaries so execution engines do not inherit upstream branding.
4. **Inspect live persisted state read-only.** Count legacy key prefixes, history rows, downstream foreign/source IDs, and plan artifacts. Existing identifiers and immutable plan files are data, not prose; never bulk-rewrite them without a versioned migration and uniqueness/ownership proof.
5. **Design compatibility per surface.** Cheap CLI/slash aliases can coexist temporarily. Model-tool aliases enlarge every request schema and affect prompt caching, so choose a fresh-session/restart boundary or a deliberately bounded deprecation window. Clients should accept old and new event tokens during staggered upgrades, while the backend emits one canonical event to avoid duplicate UI/transcript effects.
6. **Separate active and historical vocabulary.** Legacy database filenames, migration readers, audit events, and read-only compatibility tools may need to retain the historical name. Renaming history erases provenance and can break recovery.
7. **Respect source/deployment authority.** For standalone plugins, locate the editable source and installed copy, verify parity, modify source only, deploy through the supported path, and verify the installed artifact afterward.
8. **Plan migration in dependency order.** Add readers/compatibility and tests first; rename canonical core APIs; update transports and clients; neutralize downstream persistence fields; migrate live state transactionally; update plugin source/deployment; regenerate metadata; then update docs and active skills. Run the change from an isolated worktree when the primary checkout is dirty.

Report as: **semantic verdict → canonical occurrence inventory → public/internal/protocol/persistence/plugin naming matrix → live-state migration risk → compatibility policy → ordered verification gates**. Include an explicit verdict on whether the change is a rebrand, a semantic redesign, or both.

Reference: `references/cross-surface-feature-rename-migrations.md` — detailed compatibility matrix, live-state probe checklist, migration sequencing, and common unsafe replacement patterns.

## Remote-Repo Orientation Without a Clone

Use when the target is a GitHub project you were not asked to modify — a documentation/prompt/architecture question, or a repo whose working copy is larger than the question. Cloning is waste; the API tree plus raw file fetches produce the same map in seconds.

```bash
gh api repos/<owner>/<repo> --jq '{default_branch,description,size,pushed_at}'
gh api "repos/<owner>/<repo>/git/trees/<branch>?recursive=1" > tree.json   # one shot, filter offline
gh api "repos/<owner>/<repo>/contents/<path>" -H "Accept: application/vnd.github.raw" > local-name
gh api -X GET search/code -f q='repo:<owner>/<repo> "<asset-name>"' --jq '.items[].path'
```

- Filter `tree.json` in Python through `execute_code`; do not pipe `gh api` into a truncating shell viewer. The recursive tree is thousands of rows, the terminal capture keeps only a few KB, and an early-exit pager closes gh's stdout (`write /dev/stdout: The pipe is being closed`). The saved JSON is also re-filterable for every follow-up question.
- Choose targets by size from the tree before fetching. A prompt/asset directory's file sizes immediately separate the base artifact (largest) from role fragments (a few hundred bytes each).
- To learn what *consumes* an asset, code-search its exact basename in quotes. The hits are the loaders (`system-prompt.ts`, `session-advisors.ts`), which are the files that answer “how is this assembled”.
- Fetch into the scratch dir and continue with `read_file`/`search_files`. Prefer this over one more remote call per question.

## Prompt-Asset Mapping (system, reviewer, and layer prompts)

Use when asked for “the system prompt of X” in a codebase that renders prompts from `.md` templates.

1. List the prompt directory with sizes: the largest file is the base system prompt, the next tier holds role prompts (advisor, reviewer, judge, agents).
2. Get the skeleton for free: a `search_files` regex on leading `§`, `#`, and `<` (or `grep -n '^§ \|^# \|<' <file>.md` when you want the exact numbers) yields a line-numbered outline — exactly the deliverable shape for a “where is what” question.
3. Find the renderer through the import (`import tpl from "./prompts/.../system.md"`), then the call (`prompt.render(tpl, data)` / `prompt.compile`), then the `data` object assembled just above it. Those data keys are the conditional switches (`{{#if skills.length}}`, `{{#has tools "lsp"}}`), so they explain why one model sees a different prompt than another.
4. Report assembly order, not only file contents: base template → mode/prelude blocks → project/context tail, with dynamic content usually last on purpose (provider prompt caching). Separately grep each optional fragment's basename (`memory-context.md`, `WATCHDOG.md`, `personality`) to locate the builder that appends it.
5. Answer with `path:line` plus structure bullets per role, then the assembly order and fragment sources. Do not dump verbatim template text unless asked; a section-by-section line map is what makes the prompt navigable.

Reference: `references/prompt-asset-mapping.md`.

## Codebase Size and Composition Metrics

When the request is specifically about repository size, language mix, file counts, or code/comment ratios, use a bounded metrics pass inside this broader analysis workflow:

1. Prefer `pygount --format=summary` when available.
2. Exclude dependency, VCS, cache, generated, and build directories (`.git`, `node_modules`, virtualenvs, `__pycache__`, `dist`, `build`, `.next`, `.tox`, vendor trees).
3. Narrow by suffix for very large monorepos and use JSON output when machine processing is needed.
4. Explain tool semantics: Markdown commonly counts as comments, generated/binary/unknown files may appear as pseudo-languages, and JSON counts can be conservative.
5. Report command, exclusions, file count, code/comment totals, and limitations. Do not mistake code volume for architectural importance.

This absorbs the former pygount-only inspection skill so orientation and quantitative composition are discoverable under one codebase-analysis class.

## Output Format

Lead with the deliverable, not the process. A good analysis answer has this shape:

1. **One-sentence positioning** — what the project does, in plain language
2. **Tech stack table** — runtime, framework, storage, automation, deployment
3. **Architecture diagram** — ASCII or mermaid, showing module boundaries and data flow
4. **Core modules by code volume** — `wc -l` table, identifies complexity centers
5. **Data model summary** — key tables and their roles (state machines, asset pools, etc.)
6. **Key design patterns** — 3-5 bullets on the non-obvious decisions (retry strategy, anti-fingerprint, proxy routing, etc.)
7. **Risk/quality observations** — giant files, duplicated paths, missing abstractions

For follow-up questions about a specific flow, trace it file-by-file with a **file → function → API call** table, then a numbered step sequence.

## Pitfalls

1. **Don't read files linearly.** A 9000-line `server.js` is not meant to be read top-to-bottom. Read the header (imports + config), grep for the function you need, read that function + its callees.
2. **Don't skip the schema.** The DB schema is the fastest path to understanding business logic. A 100-line schema file encodes more domain knowledge than 2000 lines of CRUD code.
3. **Don't ignore subsystems.** Many projects have a `subdir/` that is itself a complete app with its own package.json, server, and DB. Treat each as a mini-project.
4. **Don't confuse code volume with importance.** A 200-line `chatgpt.js` API client may be more architecturally significant than a 8000-line `mysql-store.js` CRUD layer.
5. **Batch independent reads.** Reading 4 files one-at-a-time wastes 3 round-trips. Issue them together.
6. **Git log is context, not code.** Recent commits tell you what the user is *currently* struggling with — weight your analysis toward those areas.
7. **Feature code may live in git worktrees, not the checked-out branch.** When symbols are absent from the main checkout, run `git branch -a`, `git log --all --oneline -- <path>`, and `git worktree list` before concluding "not implemented"; then read the worktree directly. An installed/deployed copy can likewise lag the source by whole modules — compare file sets, not just hashes.
8. **Keep search patterns metacharacter-light.** When a ripgrep pattern fails to parse ("unclosed group"), retry with the bare symbol name — plain substring alternation without parens parses reliably.
9. **A short acronym is not a searchable token.** A 3–4 letter name searched case-insensitively without word boundaries matches `compress`, `complete`, `computer_use` and similar — noise that reads like a hit. Use `-w`/`\b`, exclude `.venv`, `.git`, and site-packages, and stop after one targeted pass. When the name has no local artifact at all, it is usually an external project or the user's shorthand: ask once with concrete grounded candidates ("this provider's injected block / the reviewer prompt / the layer prompts") instead of widening the search across home directories, config, and session memory.
10. **Line numbers from a remote fetch are the branch's, not the local checkout's.** When reporting `path:line` for files read through the API, name the branch/commit once so a later local diff does not look like drift.

## Reference Files

- `references/orientation-workflow.md` — the full proven sequence with example commands and a worked example from a real multi-subsystem Node.js project.
- `references/per-turn-extraction-audit.md` — concrete source map and checks for per-turn memory extraction migrations.
- `references/ai-candidate-review-promotion-audit.md` — persisted-state reviewer contract, schema decision, common gaps, and focused test matrix for automatic promotion/rejection.
- `references/remote-repo-recon.md` — gh-api tree/raw/code-search recipes, offline filtering, and the traps that truncate terminal output.
- `references/prompt-asset-mapping.md` — mapping template files → renderer → data keys → assembly order for system, reviewer, and layer prompts.
