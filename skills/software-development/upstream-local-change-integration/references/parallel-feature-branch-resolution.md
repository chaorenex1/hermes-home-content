# Parallel Feature-Branch Conflict Resolution: Feature-Existence Matrix

Use when a rebase/replay conflict shows **two sides implementing the same user-visible goal with different mechanisms** (e.g. "preserve parent transcript tail across compression" implemented upstream as `watermark` ints vs. locally as `parent_tail_messages` + outbox events). The naive whole-side pick silently drops one mechanism's contract; the naive union of kwargs breaks because the underlying store functions on each side only know their own kwargs.

## The diagnostic

1. **Extract both sides' callees, not just the conflicted caller.** The conflict sits in `agent/conversation_compression.py`, but the real contract lives in `hermes_state.py:archive_and_compact` / `publish_compression_child`. Run:

   ```bash
   git show HEAD:hermes_state.py | grep -n 'def archive_and_compact\|def publish_compression_child'
   git show 494659b7e:hermes_state.py | grep -n 'def archive_and_compact\|def publish_compression_child'
   ```

2. **Build a feature-existence matrix** (columns = side, rows = mechanism):

   | mechanism | HEAD (upstream) | theirs (local) |
   |---|---|---|
   | `watermark` / `watermark_ceiling` ints | ✓ signature + tail-clone SQL | ✗ |
   | `parent_tail_messages` / `boundary_event_id` / `boundary_payload` / `timing` | ✗ | ✓ signature + `_insert_memory_boundary_outbox_event` |
   | `_memory_boundary_outbox` table + helpers | ✗ | ✓ |
   | `_commit_watermark` / `_foreign_tail_ceiling` caller-side capture | ✓ | ✗ |
   | `_pending_parent_tail_for_boundary()` helper | ✗ | ✓ |
   | `_emit_stream_end(...)` on Bedrock error paths | ✓ | ✗ |

   If a row is empty on one side, that side **does not have the feature** — you cannot "keep both kwargs" because the callee will raise `TypeError: unexpected keyword argument`.

3. **Pick the contract owner by call-site authority.** Count every caller of the callee in the *current* (HEAD-side) tree:

   ```bash
   git grep -n 'archive_and_compact\|publish_compression_child' HEAD -- '*.py'
   ```

   If upstream has more call sites, or its mechanism is referenced by new upstream modules (e.g. `agent/context_compressor.py` expecting `watermark`), upstream's signature is authoritative. The local mechanism must be **ported or dropped**, not unioned.

4. **Classify the local delta:**

   - **Port**: the local behavior is still required and has no upstream equivalent (e.g. the outbox event drives a memory-subsystem consumer that upstream lacks). Move the *minimum* local code (helper + callee kwargs + caller capture) into the upstream-shaped callee, preserving upstream's new kwargs.
   - **Drop**: upstream's mechanism covers the same invariant better (e.g. `watermark_ceiling` prevents the duplicate-clone hazard that `parent_tail_messages` also solved). Drop the local kwargs, helpers, and table writes; keep the upstream side.
   - **Relocate**: the local helper is still useful but belongs in a different module (e.g. `_pending_parent_tail_for_boundary` → `agent/context_compressor.py` or `hermes_state.py` private helper).

## Resolution pattern for the compression conflict

For the specific conflict in `agent/conversation_compression.py` (lines ~3505–3623) and `agent/chat_completion_helpers.py` (lines ~3670–3705):

- **`archive_and_compact` call**: keep HEAD's `watermark=_commit_watermark, lock_holder=_lock_holder`; drop theirs' `parent_tail_messages`, `boundary_event_id`, `boundary_payload`, `boundary_reason`, `timing` because HEAD's `hermes_state.py` does not accept them and has no outbox consumer.
- **Rotation-path flush block**: keep HEAD's `_persist_user_message_idx` + `_flush_messages_to_session_db` + `_foreign_tail_ceiling` capture; drop theirs' empty marker (the flush is HEAD's mechanism for ensuring the parent tail is durable before the watermark ceiling is read).
- **`publish_compression_child` call**: keep HEAD's `watermark=...` and `watermark_ceiling=_foreign_tail_ceiling`; drop theirs' `parent_tail_messages`, `boundary_event_id`, `boundary_payload`, `timing`.
- **Bedrock post-worker block (`chat_completion_helpers.py`)**: keep HEAD's `_emit_stream_end(...)` calls and the `raise result["error"]` / `InterruptedError` ordering; drop theirs' `setattr(result["error"], "provider_health_counted", True)` because upstream's stale-stream breaker (`_bump_stale_streak` / `_check_stale_giveup`) supersedes the ad-hoc health flag.

## Pitfalls

- **Do not splice kwargs from both sides into one call.** The callee will reject unknown keywords at runtime.
- **Do not assume the local commit's helper is dead just because the conflict marker is small.** `_pending_parent_tail_for_boundary` is defined elsewhere in the local file and may be load-bearing for other local logic; grep the local stage blob before deciding to drop it.
- **Verify the callee body, not just the signature.** HEAD's `publish_compression_child` contains tail-clone SQL guarded by `watermark is not None`; theirs' contains `INSERT INTO memory_boundary_outbox`. The conflict resolution must match the *body* that will survive the rebase.
- **Check for table/method absence on the winning side.** If HEAD lacks `_insert_memory_boundary_outbox_event`, any retained local call to it is a runtime `AttributeError`.
- **Chat-completion health flags vs. breakers.** A local `provider_health_counted` attribute is often a lightweight workaround; upstream's `_bump_stale_streak` + `_check_stale_giveup` is the maintained breaker. Prefer the breaker and drop the flag unless a downstream consumer greps for the attribute name (verify with `git grep`).
