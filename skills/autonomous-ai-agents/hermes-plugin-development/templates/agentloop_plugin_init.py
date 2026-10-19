"""Template: run a full agent loop from a Hermes plugin tool.

Copy alongside templates/agentloop_plugin.yaml. Passed `hermes plugins validate`
and `hermes plugins doctor` as written.

The child is a real Hermes session (own LLM + tool loop) launched through the same
host-owned path delegate_task uses. A plugin cannot start a turn on the user's
session, so multi-step agentic work from a plugin == child session.
"""

import json
from typing import Any

from agent.subagent_lifecycle import SubagentLaunchRequest  # public allowlisted import

_ctx = None

TOOL_NAME = "agentloop_review"
TOOLSET = "agentloop"  # own namespace, never a core toolset name (file/terminal)

SCHEMA = {
    "name": TOOL_NAME,
    "description": (
        "Run a child agent loop (LLM + tools) that handles the given goal and returns "
        "its summary. Use for multi-step reasoning/inspection work you want isolated "
        "from the main conversation."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "goal": {"type": "string", "description": "What the child agent must accomplish."},
            "context": {"type": "string", "description": "Background facts the child needs."},
            "timeout_seconds": {"type": "number", "description": "How long to wait (default 180)."},
        },
        "required": ["goal"],
        "additionalProperties": False,
    },
}


def _run_loop(args: dict[str, Any], **_kwargs) -> str:
    # Raises SubagentLifecycleError outside an active turn -> keep the call inside
    # a tool handler or hook callback, never in a background thread or cron body.
    svc = _ctx.subagent_lifecycle
    handle = svc.launch(
        SubagentLaunchRequest(
            goal=str(args["goal"])[:16000],
            context=(args.get("context") or "")[:32000] or None,
            role="leaf",
            allowed_toolsets=("file",),  # narrows the parent's toolsets; never broadens
            correlation_id=None,          # set to dedupe re-launches (unique per session)
            # timeout_seconds / working_directory / blocked_tools are REJECTED by launch()
            # even though they exist as dataclass fields. Do not pass them.
        )
    )

    terminal = svc.wait(handle, timeout_seconds=float(args.get("timeout_seconds") or 180))
    if terminal.timed_out:
        # Not a failure: the child keeps running; report the handle and return.
        return json.dumps({"success": True, "data": {
            "state": terminal.state.value, "handle": handle.to_dict()}})

    res = svc.result(handle)
    if not res.ready:
        return json.dumps({"success": False, "error": {
            "type": "not_ready", "code": res.error_classification or "NOT_READY"}})

    # Handlers MUST return a JSON string; the registry rejects plain dicts.
    return json.dumps({"success": res.terminal_state.value == "SUCCEEDED", "data": {
        "state": res.terminal_state.value,
        "summary": res.summary,
        "result_hash": res.result_hash,
        "usage": dict(res.usage_metadata),
        "tools": dict(res.tool_execution_summary),
        "duration_s": (res.completed_at - res.started_at)
        if res.completed_at and res.started_at else None,
    }})


def register(ctx) -> None:
    global _ctx
    _ctx = ctx  # handlers have no other route back to the plugin context
    ctx.register_tool(
        name=TOOL_NAME,
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=_run_loop,
        description="Run an isolated child agent loop and return its summary.",
        emoji="🌀",
    )
