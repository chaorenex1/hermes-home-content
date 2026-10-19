---
name: hermes-desktop-interaction-debugging
description: Diagnose and fix Hermes Desktop interactions whose backend state changes but whose transcript/UI does not reflect the result.
version: 1.0.0
created_by: agent
---

# Hermes Desktop Interaction Debugging

Use for Hermes Desktop/TUI Gateway interaction defects: a button or Clarify response succeeds server-side, but the chat transcript, busy state, review card, or status UI is missing or inconsistent.

## Core model

- **Gateway/TUI is authoritative for state transitions.** Desktop renders gateway events.
- **Status is not transcript.** `status.update` changes status UI; it does not append an assistant message.
- To place a result in the Desktop chat, emit the normal transcript lifecycle in order:
  1. `message.start` for the session;
  2. `message.complete` with a non-empty `{ "text": ... }` payload.
- Keep lifecycle events session-scoped. Do not create a new command route or make the Desktop invent authoritative state.

## Investigation workflow

1. Build a tight test at the Gateway/TUI seam: simulate the user action and capture emitted events.
2. Trace the exact data path:
   - Desktop card/button → `clarify.respond`;
   - TUI/Gateway pending response / state handler;
   - emitted event(s) → `apps/desktop/src/app/session/hooks/use-message-stream/gateway-event.ts`.
3. Compare the event type to its Desktop consumer. In particular, confirm whether the consumer mutates transcript state or only status state.
4. Add a regression test that asserts the exact sequence and payload for the user-visible completion.
5. Make the smallest backend fix, preferably a helper that emits the transcript lifecycle and is shared by equivalent entry paths.
6. Verify targeted Python tests, `py_compile`, `git diff --check`, and `npm run typecheck` in `apps/desktop`.

## Ralph review composer extensions

When a Ralph review needs attachments or voice input, preserve the blocking Clarify contract instead of routing through the normal chat composer. Use request-scoped Desktop draft state (`sessionId + requestId`), stage evidence before `clarify.respond`, validate it only for a pending Ralph request on the Gateway, and use dictation only to insert editable text. See `references/ralph-review-composer.md`.

## Ralph review composer mode

When a Ralph review must replace the regular Desktop composer, model it as a session-scoped UI mode—not a second overlay:

1. Derive the mode only from the active session's clarify request: `ralph_review` and `ralph_next_round` select the Ralph composer; ordinary Clarify keeps its existing UI.
2. Render exactly one composer. Unmount the normal ChatBar in Ralph mode, disable its drop path, and mount the Ralph composer in the normal bottom-composer area. Keep Thread clearance and scroll controls whenever either composer is present.
3. Preserve ordinary composer drafts while it is unmounted. Review drafts and evidence remain scoped by `sessionId + requestId`, so switching between foreground and background sessions cannot leak state.
4. Do not restore ChatBar merely because `clarify.respond` returned. Restore only after the matching Gateway `clarify.resolved` event has cleared that request.
5. Add a pure mode-selector test plus lifecycle coverage for: Ralph hides ChatBar, ordinary Clarify does not, switching into a background Ralph review activates the mode, and only a matching resolution restores normal input.

## Dashboard toolset-list defects

Use this branch when Desktop’s **Skills & Tools → Toolsets** view disagrees with `hermes tools list` or a plugin was renamed/removed.

1. Identify the process that owns the displayed HTTP port before restarting anything. A local Dashboard and a Gateway are separate processes; restarting the Gateway does not reload the Dashboard’s plugin registry.
2. Trace `GET /api/tools/toolsets` to `hermes_cli/web_server.py::get_toolsets`. The response is built at request time from `config.yaml`, `discover_plugins()`, and the in-process tool registry—not from a SQLite toolset table.
3. Inspect the installed plugin’s actual `register()` calls. Stale tool registrations create real plugin toolsets, so the API faithfully returns them; remove or rename registrations and stale manifest metadata rather than filtering the Desktop UI.
4. Migrate `platform_toolsets.<platform>` and `known_plugin_toolsets.<platform>` when a plugin toolset key changes; otherwise a previously known old key can remain disabled/stale in the effective configuration.
5. Restart only the exact Dashboard listener process after changing installed plugin code or registry shape, then verify both the new listener PID and the handler result. Treat a raw HTTP 401 as evidence that the browser/Desktop has a local session or header; do not read, print, or reuse its credential merely to inspect the endpoint.

## Pitfalls

- Never terminate a Dashboard process tree recursively from an ancestor: it can include the Gateway and unrelated child processes. Identify the listener PID and use the product’s supported Dashboard lifecycle, or terminate only that listener after confirming its direct descendants.
- A successful `clarify.respond` only resolves the prompt; it does not itself create a transcript message.
- A `message.complete` without an appropriate preceding `message.start` can attach to stale turn state; emit the pair.
- Cover both blocking Clarify flows and typed/TUI fallback paths when they share a domain transition.
- Restart the Gateway from an external shell after source edits. Hermes blocks gateway self-restart from within a running gateway to prevent restart loops.

## Evidence standard

Report the failing event sequence before the fix, the green regression assertion after it, and the runtime reload requirement. Do not claim Desktop verification from a status event alone.

See `references/ralph-next-round-completion.md` for a concrete Ralph next-round completion example.
