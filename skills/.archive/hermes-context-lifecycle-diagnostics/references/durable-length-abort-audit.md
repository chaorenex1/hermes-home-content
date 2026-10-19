# Durable-Length Abort Audit — Hermes Compression Lease/Rotation

Session-specific detail from an audit of `agent/conversation_compression.py`
locking/lease/rotation logic (rotation-mode only). Use as a map when a session
shows `compression aborted: session=<sid> changed before lease acquisition;
preserving newer durable messages`.

## The abort site

`compress_context` (agent/conversation_compression.py, ~line 1692–1721):

- Lock acquired via `SessionDB.try_acquire_compression_lock` on the OLD
  session_id; `_CompressionLockLeaseRefresher` daemon thread starts (TTL 300s,
  refresh `min(60, ttl/2)`s, tolerates one TTL's worth of consecutive failures).
- Rotation check first: `_session_was_rotated_by_compression` →
  `_adopt_live_compression_child` rebinds the stale agent to the unique live
  child (re-validated after load; fail-closed when ambiguous).
- Then the durable-length guard, **rotation-mode only** (`not in_place`):
  `get_messages_as_conversation(_lock_sid)` length > caller snapshot length →
  release lock, return `(messages, existing_prompt)`.
- Deliberately a LENGTH check, not content equality: in-memory mutation of past
  turns is legal (multimodal compression, retry history replacement, think-tag
  stripping); content-equality would wedge compression permanently (#14694).
- In-place compaction skips the guard: `archive_and_compact` soft-archives
  pre-compaction rows (active=0, compacted=1) — non-destructive, no data-loss
  shape to guard against.

## Caller-visible semantics (the trap)

The abort returns the **same input list object** and:

- does NOT set `agent._compression_skipped_due_to_lock` (only the lock-contend
  path sets it, ~line 1564);
- does NOT emit `_emit_compression_attempt_telemetry` (invisible in attempt
  analytics; only trace is the WARNING log line).

Every `_compress_context` call site detects no-ops as
`messages is <input> and compression_skipped_due_to_lock(agent)` for the
lock-skip defer. A durable-length abort fails the second clause and falls into
the generic no-op branch:

| Call site | Behavior on durable-length abort |
|---|---|
| `agent/turn_context.py` preflight loop (~861–923) | arms `_preflight_compression_blocked`, breaks; no retry this turn |
| `agent/conversation_loop.py` pre-API gate (~1703) | re-baselines history, refunds api_call_count, retries the oversize request |
| `conversation_loop.py` 413 handler (~4216) | falls to terminal "Cannot compress further", `compression_exhausted` |
| `conversation_loop.py` overflow handler (~4470) | same terminal branch → gateway auto-reset logic (`gateway/run.py` ~14446) |
| `gateway/run.py` session hygiene (~13653) | uses `compression_in_place=True` → guard skipped, cannot hit this abort |
| CLI `/compress`, `acp_adapter/server.py` | one-shot, no retry |

No caller reloads the durable history and retries. A contender whose in-memory
snapshot is persistently shorter than the durable parent re-aborts every
attempt — **intentionally safe (no lineage fork) but non-progressing**.

## Lock subsystem reference

- `hermes_state.py` `try_acquire_compression_lock` (~4568): single-transaction
  reclaim-expired-or-dead-PID-holder + INSERT OR IGNORE + SELECT verify;
  dead-PID reclaim via `_compression_lock_holder_process_is_dead` (psutil,
  line ~48). SQLite errors fail open → return False → caller skips compression.
- `release_compression_lock` (~4656): holder-qualified DELETE, idempotent.
- `compress_context` probes `_lock_api_is_absent_on_session_db` (~287):
  structural absence of the lock API on a hot-reloaded SessionDB fails OPEN
  (proceed unlocked) so version skew cannot wedge compression; any other lookup
  error fails CLOSED (skip this cycle).

## Test coverage

- `tests/agent/test_compression_concurrent_fork.py:319`
  `test_durable_message_committed_before_lease_aborts_stale_snapshot` pins the
  abort contract (input returned verbatim, no rotation, durable rows survive,
  `compress` never called).
- `tests/agent/test_preflight_lock_defer.py` pins lock-skip defer.
- **Gap**: no test covers caller behavior after the durable-length abort
  (no reload/retry expectation). Recovery contract is implicit: the caller
  must re-read `get_messages_as_conversation` before the next attempt.

## Regression probe recipe

After `test_durable_message_committed_before_lease_aborts_stale_snapshot`
aborts, re-invoke with the reloaded durable history and assert success:

```python
returned, _sp = agent._compress_context(
    db.get_messages_as_conversation(parent_sid), "sys", approx_tokens=120_000
)
assert agent.session_id != parent_sid  # rotation proceeded
```

## Live-log confirmation shape (observed 2026-08-03, session 20260803_015827)

```
WARNING agent.conversation_compression: compression aborted: session=<sid>
        changed before lease acquisition; preserving newer durable messages
ERROR   agent.conversation_loop: Context length exceeded: 442,629 tokens.
        Cannot compress further.
```

One abort per overflow-handler invocation, then the turn dies with
`compression_exhausted`. Repeated across turns (agent.log.2 and .3) because the
in-memory snapshot was never refreshed relative to durable rows.

## Open question when triaging a live occurrence

Who wrote the extra durable rows? Candidates: background-review fork sharing
`session_id` (`agent/background_review.py`), the pre-rotation flush
(`_flush_messages_to_session_db`, ~2098), or gateway writers. A probe logging
`len(durable_parent) - len(messages)` plus the lock holder at the abort site
would identify it. Also unverified: whether `compression_exhausted` on this
path can trigger gateway auto-reset for a session whose durable parent is
persistently longer — no test covers that interaction.
