# Hermes TUI/Desktop Ralph Integration Notes

## Failure pattern

A command may be present in `hermes_cli/commands.py` and work in the classic CLI while failing in Desktop/TUI. TUI slash requests travel through `tui_gateway/server.py`:

```text
slash.exec
  -> _PENDING_INPUT_COMMANDS check
  -> command.dispatch
  -> structured send/notice payload
```

The TUI slash worker does not consume the classic CLI `_pending_input` queue.

## Required wiring

- Register the command in `hermes_cli/commands.py`.
- Handle it in `cli.py` for classic CLI.
- Add it to `tui_gateway/server.py::_PENDING_INPUT_COMMANDS`.
- Add a `command.dispatch` branch using the TUI session's `session_key` for durable state.
- For automatic continuation, hook after TUI turn completion and before the existing continuation chain, but enqueue only after `session["running"]` is released.
- Emit `status.update` for visible progress.

## Client response-shape pitfall

`slash.exec` clients do not necessarily render arbitrary structured payloads. In the current Web/Desktop path, `slash.exec` falls back to `command.dispatch`; `exec` and `plugin` directives are rendered from `output`, while `send`/`skill` are submitted as agent messages. A backend branch returning `{type: "notice", message: "..."}` is not part of that client contract and can surface as `/<command>: no output`. For informational subcommands, return `{type: "exec", output: "..."}` (or extend and test the client directive union deliberately).

Before runtime debugging, inspect the client dispatcher and compare the backend payload against its typed response union. Then compile, exercise the dispatch path, and restart the already-running Python backend.

## Evidence interpretation

The absence of `ralph` in logs while the session is `platform=tui` indicates a routing gap, not an LLM failure. API timeouts, missing pytest, and unrelated gateway warnings should not be conflated with slash-command routing.
