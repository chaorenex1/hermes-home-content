# Tool output on each surface

Use when the user says the CLI shows no tool output, asks where tool results went, or wants to
change how much tool detail renders. Diagnose the surface before touching code.

## What each surface prints

- **Classic CLI** (`display.interface: cli`, `hermes --cli`): one summary line per tool call,
  committed to scrollback. It does not print the tool result body. `display.tool_progress`
  controls the trail: `off` hides it, `new` shows new calls, `all` shows every call, `verbose`
  adds full arguments. In the classic CLI `verbose` still does not print results.
- **Ink TUI** (`hermes --tui`, `display.interface: tui`): renders an Args/Result block for a tool
  only when the session's tool progress mode is `verbose`. The TUI gateway attaches `result_text`
  to the `tool.completed` event only for verbose sessions (`tui_gateway/tool_progress.py`;
  `_session_verbose` in `tui_gateway/server.py`). With `all`, rows carry the summary only. Result
  previews are truncated; long stdout is not shown in full.
- **Messaging surfaces** gate `/verbose` behind `display.tool_progress_command: true`; each
  surface still decides how much of the tool call it renders.
- **Raw output** lives in `$HERMES_HOME/cache/terminal-output/out-*.log` when a command's output
  is truncated; `$HERMES_HOME/logs/agent.log` records completion/progress lines, not bodies.

## Changing it

```bash
hermes config set display.interface tui
hermes config set display.tool_progress verbose
```

- Applies to the next launch or session; the running process keeps the mode it started with.
- `hermes --cli` overrides `display.interface: tui`. The interface setting is honored only on a
  real TTY.
- Inside a session, `/verbose` cycles the mode and persists it to config.

## Pitfalls

- `hermes config set display.tool_progress` warns that the key is not recognized (the schema
  knows `display.tool_progress_command`). The key is real: `hermes_cli/cli_init_mixin.py` and
  `tui_gateway/server.py` read it. Verify with `hermes config get display.tool_progress`; do not
  rename the key to silence the warning.
- Back up `config.yaml` before changing display keys, then diff the file: `hermes config set`
  rewrites YAML.
- "The CLI does not print tool output" is a surface design fact, not a broken renderer. Check
  whether the TUI with `verbose`, or the raw output files, already satisfy the user before
  patching Hermes core to add result printing.
- Do not confirm TUI rendering from a pty capture: an Ink redraw can leave only spinner fragments
  in the log. Confirm the mode from config, then have the user look at a live TUI session.
