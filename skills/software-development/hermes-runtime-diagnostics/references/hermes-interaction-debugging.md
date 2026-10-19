---
name: hermes-interaction-debugging
description: "Use when Hermes interaction state and UI disagree."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, desktop, tui, gateway, interaction, debugging, events]
    related_skills: [systematic-debugging, hermes-agent]
---

# Hermes Interaction Debugging

## Overview

Diagnose duplicated, stale, missing, or unresponsive Hermes interactions across Desktop, TUI, Gateway, workflow state, and transcripts. Treat backend lifecycle, event transport, renderer ownership, and persisted state as separate layers; success in one does not prove the others updated.

## When to Use

- A button or Clarify answer succeeds server-side but chat/status remains stale.
- A review/prompt card appears twice, persists after submission, or requires repeated completion.
- Desktop and Gateway disagree about pending interaction state.
- A toolset/status view disagrees with the live backend registry.

## Evidence-First Workflow

1. Identify exact session, request/interaction ID, workflow/plan ID, and runtime revision.
2. Trace user action → gateway handler → durable transition → emitted events → client consumer → rendered owner.
3. Classify:
   - same request ID, two controls: renderer ownership/mount or clear defect;
   - different request IDs: backend retry/re-emission or duplicate delivery;
   - accepted response, stale UI: resolution event/order/scope defect;
   - status changed, transcript absent: wrong event class.
4. Compare each event with the actual reducer/renderer. `status.update` changes status, not transcript. Transcript completion normally requires session-scoped `message.start` then non-empty `message.complete`.
5. Add a tight regression for cardinality, exact sequence/payload, and response-to-clear behavior.
6. Make the smallest authoritative-side fix; do not make Desktop invent workflow truth.
7. Verify targeted backend tests, frontend typecheck/tests, `git diff --check`, runtime reload, and one controlled trace.

## Request and Event Contract

Correlate:

```text
session_id, workflow_id, interaction_id, request_id,
event, response_status, transition_status, retry_reason
```

Keep request metadata structured and privacy-safe. Do not serialize raw machine payloads into user-visible transcript text.

## Ralph Review and Composer Branch

Ralph review is a blocking request-scoped Clarify lifecycle, not a normal chat message or second global composer.

- Scope drafts/evidence by `sessionId + requestId`.
- Render exactly one composer owner for the active session.
- Preserve ordinary drafts while review composer is mounted.
- Restore normal input only after matching `clarify.resolved` clears the request.
- Stage attachments before resolution; failed uploads keep the request pending.
- Voice is editable dictation only, never auto-submit.

See `references/ralph-review-composer.md` and `references/ralph-next-round-completion.md`.

## Compression Lock Branch

When compression aborts with "changed before lease acquisition" or skips with
"another path is compressing", the abort is a LENGTH guard: after acquiring
the durable per-session lock, rotation-mode compression reloads durable rows
and aborts if a writer committed a turn between the caller's in-memory
snapshot and lease acquisition. Enumerate every `SessionDB.append_message`
writer that can target the same session id in that window (agent turn flush,
gateway transcript retry queue, gateway mirror, TUI/desktop model-switch
markers, background-review fork sharing session_id). In-place compaction
(gateway hygiene) skips the guard — an abort implies a rotation-mode caller.

See `references/compression-lock-race.md` for the full architecture map,
writer table, race-window diagram, and diagnostic recipe.

## Dashboard Session Authentication Branch

When a user asks for a Dashboard session token or Desktop requests one, identify the auth mode before naming a location: local loopback tokens are ephemeral and available from `window.__HERMES_SESSION_TOKEN__`, Desktop-spawned tokens may be process-local, deliberately static self-hosted tokens may live in the active `$HERMES_HOME/.env`, and OAuth/password-gated deployments intentionally omit the injected token. Never expose the credential; give the user a local retrieval method and inspect only token presence during diagnostics.

See `references/dashboard-session-auth.md` for the mode matrix, bounded checks, and API-header details.

## Toolset and Registry Branch

When Desktop toolsets disagree with CLI:

1. Identify the process owning the displayed HTTP port; Dashboard and Gateway registries are distinct process state.
2. Trace the endpoint to configuration, plugin discovery, and in-process registrations.
3. Repair stale registrations/manifest/config vocabulary rather than filtering UI or editing unrelated databases.
4. Restart only the owning process and verify PID plus endpoint result without exposing credentials.

## Memory-Provider Binding Branch

Treat configuration, provider discovery, provider storage, host binding, Agent-backed tools, and background jobs as separate health layers. A green `hermes doctor` or provider CLI does not prove that the current Desktop/Gateway process bound the same profile or that its Agent call contract is compatible.

1. Confirm the resolved provider selection without exposing secrets.
2. Run the provider's read-only operator checks (`status`, `verify`, `tree`, and one known-content search).
3. Exercise equivalent tools through the live session: list, search, exact read, and Agent-driven reasoning.
4. Compare scope and path evidence. If the operator CLI sees a known file while live tools return an empty tree, missing file, or no active provider, classify this as host/profile binding or stale owning-process state—not storage corruption.
5. If direct file tools work but Agent-backed reasoning raises an unexpected keyword/signature error, classify host/plugin API drift separately from storage and indexing health.
6. Inspect durable job counts; pending/running/failed work is independent evidence and must not be hidden by a successful storage verification.
7. Run repository tests in a clean project environment. Hermes-launched shells may inject `PYTHONPATH` entries for the host source and site-packages; inspect `PYTHONPATH`, `VIRTUAL_ENV`, and `sys.path`, then remove only the contamination and use the project-declared test environment. Do not treat collection failures caused by package shadowing or incompatible binary wheels as provider regressions.

See `references/memory-provider-live-binding.md` for the diagnostic matrix and a bounded probe recipe.

## Verification Checklist

- [ ] One trace identifies duplicate mount, duplicate request, or unresolved request.
- [ ] Durable transition and user-visible event lifecycle are both verified.
- [ ] One pending request has one visible owner.
- [ ] One response reaches one terminal or explicit retry transition.
- [ ] Matching resolution clears scoped attention/draft state.
- [ ] The owning process was restarted after source/registry changes.

## Pitfalls

- JSX searches cannot distinguish duplicate renderer ownership from duplicate backend requests.
- Final success may omit earlier retries; inspect request boundaries.
- `clarify.respond` resolves a prompt but does not append transcript text.
- `message.complete` without matching start can attach to stale turn state.
- Do not recursively terminate a Dashboard ancestor process tree.
