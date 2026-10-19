# Hook and middleware seams

Which seam decides *when* a plugin's effect lands. Verify each claim against the live install;
the public hooks page lags `VALID_HOOKS` in `hermes_cli/plugins.py`.

| Seam | Fires | Return contract | Effect | Cost |
|---|---|---|---|---|
| `pre_llm_call` | once per turn, in the turn prologue (`agent/turn_context.py::_collect_pre_llm_call_context`) | `str` or `{"context": ...}` | appended to the current user message | agent must reason over it every turn |
| `llm_request` (middleware) | once per provider attempt (`agent/turn_api_request.py`) | `{"request": {...}}` replaces provider kwargs | rewrite this attempt's messages | synchronous, no timeout wrapper |
| `pre_tool_call` | before each tool executes (`agent/agent_runtime_helpers.py::_pre_tool_block_message`) | `{"action": "block", "message": ...}` | deny one call; the message becomes that call's result | visible rejected tool call |
| `pre_verify` | end of turn, only when the turn edited files (`agent/turn_stop_gates.py`) | continue message | keeps the turn going | capped by `agent.verify_hooks.max_verify_nudges` |
| `post_tool_call`, `post_llm_call`, `on_interim_message` | observers | ignored | record only | 30s callback budget |
| `pre/post_api_request`, `pre/post_auxiliary_call` | per provider attempt | ignored | usage/latency evidence | 30s callback budget |

## Rules

- `pre_llm_call` is once per turn, not once per model call. The prologue stamps the composed user
  message into `api_content`, and every later provider attempt in that turn replays those bytes. It
  cannot deliver context per tool-loop iteration.
- `llm_request` is the only seam that runs inside the tool loop. It runs synchronously with no
  timeout wrapper: read an in-memory ledger, never call a model there. If it must wait, bound the
  wait and fall through with what is already available.
- A `pre_tool_call` block is user-visible outcome, not a silent skip: the model receives the message
  as the tool result and may retry. Cap blocks per turn on mutating tools.
- `pre_verify` is not a general "continue after the final answer" channel; a non-coding turn never
  triggers it.
- Hooks run under `plugins.hook_callback_timeout` (default 30s) and a slow callback is abandoned and
  suppressed for 60s. Model work goes on a worker thread; the hook only appends or reads memory.
- The system prompt is built once per session and replayed verbatim. Dynamic plugin text belongs in
  the user message or the request, never in a mid-session system prompt rewrite.
- Injecting into the user message changes the prompt prefix, so provider prompt-cache hits drop.
  Spend the injection on advice that changes the next action.

## Channel mapping for an advisory/injector plugin

| Urgency | Seam | Notes |
|---|---|---|
| low (nit, cleanup, background note) | `pre_llm_call` | once per advice id; survives a retry |
| medium (should change course before the next step) | `llm_request` | delivered before the next attempt, after any unanswered tool call is paired |
| high (must not execute this action) | `pre_tool_call` block | opt-in, mutating tools only, capped per turn |
| completion nudge (turn ended, work unverified) | `pre_verify` | opt-in, capped by `max_verify_nudges` |
| cannot do | — | no abort of in-flight tools, no starting a new turn, no system-prompt rewrite, no UI card |

## Proving the seam

One turn with one tool call produces two provider attempts. Register counters on both
`pre_llm_call` and `llm_request` and assert `pre_llm_call == 1` and `llm_request == 2`; that single
test distinguishes the two seams and catches a provider that coalesces attempts. Also assert the
block message equals the tool-result string the model sees, and that advice staged for a failed
attempt returns to pending after `api_request_error`.

Unit tests prove the callback; they do not prove the host calls it or consumes the return. Add one
dispatch probe against the staged plugin:

```python
# host venv python, workspace on sys.path, HERMES_HOME = temp dir holding plugins/<name>
import hermes_cli.plugins as hp
from plugins.memory import load_memory_provider

hp.discover_plugins()                      # runs register(ctx); hooks now live
provider = load_memory_provider("<name>", register_skills=False)
provider.initialize("probe-session", hermes_home=str(home), platform="cli")
# seed the state the hook reads, then dispatch exactly like the loop
blocked = hp.invoke_hook("pre_tool_call", tool_name="write_file",
                         session_id="probe-session", args={"path": "x"})
assert [i for i in blocked if isinstance(i, dict) and i.get("action") == "block"]
assert hp.get_pre_verify_continue_message(session_id="probe-session",
                                          changed_paths=["a.py"], attempt=0)
assert hp.get_pre_verify_continue_message(session_id="probe-session",
                                          changed_paths=["a.py"], attempt=1) is None
```

Assert the *second* call too. A gate or continuation that keeps firing after it consumed its
advice turns one note into a blocked tool loop or an endless nudge; the consuming write is part of
the contract, not an implementation detail.

## Emission discipline (reviewer / injector plugins)

A reviewer that can inject must decide what is worth saying before it writes the ledger:

- Normalize the note to a dedupe key (NFKC, lowercase, punctuation stripped) and key the ledger on
  that, not on the raw bytes. Rephrasing the same finding must not create a second row.
- A repeat at the same severity is a duplicate; the *same key at a higher severity* is an escalation
  and must pass. Store the severity with the key so the comparison is possible.
- Drop acknowledgements ("looks good", "no issues", "continue") before they spend budget — the
  reviewer's silence and its noise must not look the same in telemetry.
- Budget non-blockers per update; exempt blockers. Sort blockers first so a chatty reviewer cannot
  crowd the one note that matters out of the delivery window.
- Record why each note was dropped (`empty`, `noise`, `duplicate`, `rate-limit`) on the review row.
  Without the reason counts, a silent reviewer and a noisy one produce the same empty ledger.

## Proactive egress (no next turn)

No plugin API starts a turn, and no hook return becomes a chat message mid-run. When advice is
published after the turn's final answer it can only ride the next user turn — unless the turn was a
gateway turn, where the host's own send tool is callable in-process:

```python
send_message_tool({"target": platform, "action": "send", "message": text})  # -> JSON string
```

`target` with no `:<chat_id>` resolves to that platform's home channel. Parse the returned JSON and
require `success: true`; do not substring-match for "error"/"failed". A failed send must leave the
rows pending so the normal channels still carry them. Notify each ledger id once: an advice that is
mailed at every turn end is noise even when each send succeeded.
