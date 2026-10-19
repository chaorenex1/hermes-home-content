# Compression Lock and the "changed before lease acquisition" Race

Map of the Hermes context-compression locking architecture and the specific
stale in-memory vs durable message-count race that aborts rotation-mode
compression. Built by tracing the code paths; verify against the source
before citing line numbers (they drift).

## The abort site

`agent/conversation_compression.py` `compress_context()`:

1. Caller passes an in-memory `messages` snapshot built BEFORE any lock.
2. `compress_context` acquires the durable per-session lock
   (`SessionDB.try_acquire_compression_lock(session_id, holder, ttl)`).
3. Immediately after acquisition, for **rotation mode only** (`not in_place`),
   it reloads durable rows via
   `SessionDB.get_messages_as_conversation(session_id)` and compares LENGTHS:

   ```python
   if not in_place and _lock_db is not None and _lock_sid:
       durable_parent = durable_loader(_lock_db, _lock_sid)
       if len(durable_parent) > len(messages):
           logger.warning(
               "compression aborted: session=%s changed before lease "
               "acquisition; preserving newer durable messages", ...)
           _release_lock()
           return messages, existing_prompt   # no-op, no rotation
   ```

Key design facts:

- It is deliberately a **length** check, not content equality. In-memory
  mutation of past turns is legal (multimodal compression, retry history
  replacement, think-tag stripping) — a content-equality abort would
  permanently wedge compression on such sessions (issue #14694).
- **In-place compaction** (`compression_in_place=True`,
  `compression.in_place` config) skips the guard entirely: it soft-archives
  old rows (`active=0, compacted=1`) under the SAME session id, so snapshot
  drift cannot lose data there. The gateway hygiene path sets
  `_hyg_agent.compression_in_place = True`, so hygiene auto-compress never
  hits this abort. The abort implies a **rotation-mode** caller: the agent
  loop's in-turn auto-compress, CLI `/compress`, or TUI-gateway
  `session.compress` RPC (all force or loop paths that keep
  `compression_in_place` False).

## The race window

```
caller builds messages snapshot (in-memory list)
        │  <-- RACE WINDOW: any committed append_message() here
        ▼        makes len(durable) > len(snapshot)
compress_context acquires durable compression lock
        ▼
reload durable rows → length compare → abort
```

The lock only serializes compressors against each other; it does NOT block
message writers during the window between snapshot and acquisition. Note
`SessionDB.append_message` DOES refuse writes while a compression lock is
held by another holder (`CompressionSessionBusyError`) — but that check only
helps AFTER acquisition, not during the pre-acquisition window.

## All writers that can append to the same session concurrently

`SessionDB.append_message` call sites (each can grow durable rows inside the
race window):

| Writer | File | Notes |
|---|---|---|
| Agent turn flush | `run_agent.py` `_flush_messages_to_session_db` → `append_message` (self-turn persist; the live turn agent itself) | The agent's own turn running in parallel with a compression attempt from another path |
| Gateway transcript writer | `gateway/session.py` `_append_transcript_message` | Background retry queue (`_transcript_retry_lock`, pending deque) can flush LATE — a previously failed write landing inside the window |
| Gateway mirror | `gateway/mirror.py` `_append_to_sqlite` | Opens its OWN SessionDB() instance per write |
| Gateway branch create | `gateway/slash_commands.py` (~4282) | Writes to NEW session id, not the parent — not a parent-race source |
| CLI branch copy | `hermes_cli/cli_commands_mixin.py` (~986) | Same — new session id |
| TUI/Desktop model-switch marker | `tui_gateway/server.py` (~3186) | `display_kind="model_switch"` user-role marker written via the agent's db or a scoped db — CAN target the live session id mid-window |
| TUI/Desktop branch copy | `tui_gateway/server.py` (~10165) | New session id — not a parent-race source |
| TUI/Desktop session.persist | `tui_gateway/server.py` (~11600 area) | scoped_db append |

Also relevant: `agent/background_review.py` forks a review agent that SHARES
`session_id` with the parent-turn agent — the original motivation for the
lock (two AIAgent instances compressing overlapping snapshots of one
conversation, both rotating session_id → orphaned child sessions).

## Other guards near the same code (do not confuse)

- **Lock-contention skip**: acquire fails → "compression skipped: another
  path is compressing" + `agent._compression_skipped_due_to_lock` set.
  Different message from the length-guard abort.
- **Rotation-ownership re-check**: after acquisition,
  `_session_was_rotated_by_compression` — a delayed contender that acquires
  the lock after the winner released it adopts the live child instead of
  re-compressing (`_adopt_live_compression_child`).
- **TUI history_version guard**: `tui_gateway/server.py`
  `_compress_session_history` snapshots under `history_lock` and, after
  `_compress_context` returns, re-checks `session["history_version"]` —
  drops the compressed result if an external mutation happened during the
  LLM call. This is the SECOND, later window (during the summary call
  itself), in-memory only, no durable compare.
- **Persisted-guard refresh**: `_refresh_persisted_compression_guards`
  re-reads durable breaker state after lock acquisition so a stale
  `bind_session_state()` snapshot cannot wrongly fire the failure-cooldown
  gate.

## Diagnostic recipe for a reported abort

1. Grab the log line: session id, and whether the caller was rotation mode
   (any non-in-place path). If the session's source is desktop and mode is
   rotation, the caller is the in-loop auto-compress or a `session.compress`
   RPC — NOT gateway hygiene (in-place).
2. List candidate writers active for that session id in the window:
   - Is a user turn in flight on the same session (agent turn flush)?
   - Is the gateway transcript retry queue non-empty for that session
     (late flush)?
   - Did a model-switch marker write land (desktop model picker)?
   - Is a background-review fork alive with the shared session id?
3. The abort is SAFE (no data loss: newer durable rows are preserved, the
   no-op return lets the next cycle retry). Persistent abort loops indicate
   a writer that continuously appends during every attempt — check for a
   stuck transcript retry queue or a runaway background fork.
