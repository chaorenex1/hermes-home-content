# Callee-Conflicted Rebase: Authority Files That Are Themselves UU

Companion to `readonly-index-stage-conflict-resolution.md` for the rebase replay case where the file that would normally arbitrate a conflict hunk (the callee whose signature decides which kwargs/contract to keep) is **itself conflicted (UU)** in the same rebase. Example from a real session: replaying a local memory-boundary commit onto upstream, the caller `agent/conversation_compression.py` conflicted on kwargs to `archive_and_compact(...)` / `publish_compression_child(...)`, but the authoritative signatures live in `hermes_state.py` — which was *also* `UU`, so "query the callee's current contract" has no single clean answer.

## 1. Recognize the situation early

When a conflict hunk is "which kwargs does this call pass?", immediately check whether the callee file is clean:

```bash
git status --short | grep -v '^??'          # full UU inventory — conflicts may extend beyond the scoped files
git ls-files -u | awk '{print $4}' | sort -u
```

Do not assume the task's stated conflict scope ("Conflict scope: A.py and B.py") is complete — verify with the UU list. If the callee (e.g. `hermes_state.py`) is also UU, its "current signature" is a negotiation, not a fact, and the caller hunk cannot be resolved by reading one side of the callee.

## 2. Read the callee's two sides, not its worktree

The callee worktree contains conflict markers; its stage blobs give both candidate contracts:

```bash
git show :2:hermes_state.py > /tmp/callee_upstream.py   # upstream-side signature (HEAD)
git show :3:hermes_state.py > /tmp/callee_local.py      # replayed-commit-side signature
diff /tmp/callee_upstream.py /tmp/callee_local.py | head -80
```

Extract each candidate signature and compare kwarg-by-kwarg against the caller-hunk's two sides. In the session example:

- HEAD side of `archive_and_compact` accepted `watermark`, `lock_holder`; local side accepted `parent_tail_messages`, `boundary_event_id`, `boundary_payload`, `boundary_reason`, `timing`.
- HEAD side of `publish_compression_child` accepted `watermark`, `watermark_ceiling` (concurrent-append clone/orphan-recovery contract #75316); local side accepted `parent_tail_messages`, `boundary_event_id`, `boundary_payload`, `timing` (durable boundary + outbox delivery).
- Therefore the caller resolution must splice: keep upstream's watermark/ceiling kwargs (upstream's concurrent-append clone mechanism is the current orphan-recovery owner) AND keep the local boundary/timing kwargs (the replayed commit's feature) — provided the callee resolution also merges both parameter sets. If the delegated scope forbids touching the callee, report the splice as blocked on the callee resolution instead of picking one side silently.

## 3. Attribute conflict-hunk sides to the right commit — REBASE_HEAD is not always the author

A stage-3 conflict side may contain content that is **absent from the replayed commit's own diff**. Verify before attributing:

```bash
git rev-parse --short REBASE_HEAD                 # the commit being replayed
git show <rebase-head> -- <file>                  # does the hunk content appear here?
```

In the session, the stage-3 side of a `chat_completion_helpers.py` hunk (`setattr(result["error"], "provider_health_counted", True)` + a dedented Bedrock post-worker block) did **not** appear in `git show <REBASE_HEAD> -- agent/chat_completion_helpers.py` — the replayed commit only added provider-circuit-breaker imports and token-admission helpers. Conclusion: the hunk content came from an **earlier local commit in the replay stack** (already layered into the stack base), and stage 3 reflects the cumulative stack state, not just REBASE_HEAD's diff. Find the true author before recommending:

```bash
git log --all --oneline -S 'provider_health_counted' -- agent/chat_completion_helpers.py
git log --oneline <onto>..<original-local-tip>    # enumerate the full local stack
```

Recommendation impact: when the stage-3 side originates from an earlier in-stack commit, its "intent" must be reconstructed from that commit's diff (`git show <earlier-sha> -- <file>`), and the resolution for the current hunk should preserve that earlier commit's mechanism unless upstream has superseded it — do not re-attribute it to REBASE_HEAD and do not drop it as "not part of this commit".

## 4. Trace local-mechanism obsolescence via upstream's new owners

The delegated question is often "which local mechanisms are now obsolete?" Answer it by locating the upstream owner of each local behavior, not by diffing prose:

- Local pre-rotation `_flush_messages_to_session_db(...)` + foreign-tail-ceiling (#75316) vs. upstream's `parent_tail_messages=` kwarg on `publish_compression_child` (pure-SQL column clone documented in the callee docstring). If upstream's `watermark`/`watermark_ceiling` clone covers concurrent appends and the local `parent_tail_messages` covers the *current-turn tail*, they are **complementary, not duplicates** — the obsolete local piece is the best-effort flush block, because upstream's in-place path and the callee-level tail handling subsume it; the piece to relocate is the `_pending_parent_tail_for_boundary(...)` helper only if the callee resolution keeps that kwarg.
- Cross-check that upstream's replacement exists **and is wired**: grep for the kwarg's consumers inside the callee body (`git show :2:hermes_state.py | grep -n 'parent_tail_messages\|watermark_ceiling'`) — a signature accepting a kwarg whose body ignores it means the local mechanism is NOT yet obsolete.

## 5. Output shape for per-hunk artifacts (blocked-callee variant)

When the callee is conflicted and out of the delegated edit scope, each caller-hunk recommendation should carry an explicit dependency line:

- `recommendation`: the merged call (e.g. keep upstream kwargs `watermark=_commit_watermark, lock_holder=_lock_holder` AND append local kwargs `parent_tail_messages=..., boundary_event_id=..., boundary_payload=..., boundary_reason="compression", timing=_db_timing` in callee-signature order).
- `evidence`: cite both callee stage sides (`:2:` and `:3:` signature lines) and the callee-body consumer greps proving both kwarg sets are honored.
- `risks`: "resolution depends on hermes_state.py callee hunk merging both parameter sets; if the callee resolution drops the boundary kwargs, this call must drop them too" — a *conditional* resolution, stated as such.
- `blocker`: non-null only when no self-consistent resolution exists across the caller/callee pair.

## Pitfalls

- **Never resolve a kwarg-conflict from the caller side alone.** The conflict marker shows two kwarg sets; only the callee stages tell you which are legal. With the callee conflicted, "current upstream signature" is the `:2:` blob, not the worktree.
- **Two kwarg sets at the same call site are almost always a union splice in callee-signature order**, not a pick-a-winner — same rule as the additive-lines case in `readonly-index-stage-conflict-resolution.md`, but verify against *both* callee sides.
- **`git show :2:<file>` fails for clean files** ("path is in the index, but not at stage 2") — fall back to `git show <onto-sha>:<path>`; conversely, for a UU callee, `<onto-sha>:` gives upstream's pre-merge version which may already be superseded by previously replayed local commits — prefer `:2:` when it exists.
- **Stage-3 side content not in REBASE_HEAD's diff is not an error** — it is cumulative stack state. Attribute it to the true author commit via `git log -S` before judging its intent.
- **Signature accepted ≠ behavior implemented.** A callee side may accept `parent_tail_messages` but its body may not consume it; grep the stage blob body before declaring a local mechanism obsolete.
