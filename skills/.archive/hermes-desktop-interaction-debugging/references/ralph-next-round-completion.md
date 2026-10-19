# Ralph next-round completion transcript regression

## Symptom

In Desktop, clicking **完成当前计划** resolved the Clarify card and completed the Ralph state machine, but did not add a result in the chat transcript.

## Root cause

The TUI Gateway's next-round completion handling emitted only `status.update`. Desktop consumes that as status UI; transcript updates are driven by `message.start` followed by `message.complete`.

## Minimal fix pattern

```python
def _emit_ralph_completion_message(sid: str, detail: Any) -> None:
    _emit("message.start", sid)
    _emit("message.complete", sid, {"text": f"✓ Ralph plan complete: {detail}"})
```

Invoke it after `handle_next_round_input(...)` returns `("done", detail)` in both:

- the blocking `clarify.request` path used by Desktop cards;
- the conversational/TUI fallback path.

## Regression contract

For a completed next-round action, assert this ordered event sequence:

1. existing `status.update` with the completion detail;
2. `message.start` for the same session;
3. `message.complete` for that session, with a non-empty completion text.

The current project regression lives in `tests/tui_gateway/test_ralph_command.py::test_tui_next_round_finish_adds_a_transcript_message`.

## Reload note

Source edits require a Gateway restart. `hermes gateway restart` invoked from inside the running gateway is intentionally refused; run it from an external shell.
