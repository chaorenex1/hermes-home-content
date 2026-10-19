# Ralph Review-Gated Loop: Session Pitfalls

This reference records durable implementation lessons from reviewing a multi-surface Ralph loop.

## Correct Scheme B ordering

```text
model candidate -> persist round -> judge -> awaiting_review
  approve + done -> completed
  approve + continue -> enqueue continuation
  feedback -> same logical round, re-analyze, judge again
```

Approval is a gate after judge, not a second judge invocation. Revision increments `attempt`, not `round`. Budget exhaustion must pause without enqueueing another continuation.

## Failure signatures to test

- `after_turn()` must return `awaiting_review` for both `done` and `continue`; the review handler decides whether the result becomes `done` or a continuation.
- A completed plan must not return a continuation after approval.
- A revision must return `reanalyze` and preserve the same round.
- CLI, Gateway, and TUI/Desktop must all consume `continue` and `reanalyze` consistently.
- Review interception must happen only for ordinary text; slash commands must route first.
- Gateway continuation checks must not use a narrower condition than CLI/TUI.

## State and safety checks

- Save/reload must preserve `history`, current/active round, review attempt, transitions, and bounded round records.
- Planning-only enforcement belongs before executor special branches as well as in the generic dispatcher; otherwise delegation, memory, or context-engine paths may bypass it.
- Static compilation is insufficient after large insertions. Inspect neighboring handlers for accidental fragments, undefined variables, and missing imports, then run a focused smoke test.

## Minimal smoke matrix

1. judge `continue` -> `awaiting_review` -> approve -> continuation.
2. judge `done` -> `awaiting_review` -> approve -> `done`, no continuation.
3. judge `continue` -> feedback -> same-round `reanalyze`.
4. max-turn boundary -> `paused`, no enqueue.
5. save/reload -> state fields unchanged.
