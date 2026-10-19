#!/usr/bin/env python3
"""Compare bare-name and resolved-path subprocess launches.

Use this when an interactive shell finds a CLI but the application runtime does
not. The probe intentionally reports only bounded command results; it does not
print the full environment or PATH.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from typing import Any


def _run(
    executable: str,
    args: list[str],
    env: dict[str, str],
    timeout: float,
) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            [executable, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            env=env,
            check=False,
        )
    except Exception as exc:
        return {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
        }

    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip()[:1000],
        "stderr": proc.stderr.strip()[:1000],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare bare and shutil.which-resolved CLI launches."
    )
    parser.add_argument("command", help="Bare command name, for example codex")
    parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help="Arguments passed to the command (default: --version)",
    )
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument(
        "--path",
        help="Optional child PATH used for both resolution and subprocess launch",
    )
    ns = parser.parse_args()

    command_args = ns.args or ["--version"]
    if command_args[:1] == ["--"]:
        command_args = command_args[1:]

    env = os.environ.copy()
    if ns.path is not None:
        env["PATH"] = ns.path
    effective_path = env.get("PATH")
    resolved = shutil.which(ns.command, path=effective_path)

    result: dict[str, Any] = {
        "command": ns.command,
        "args": command_args,
        "path_present": bool(effective_path),
        "pathext_present": bool(env.get("PATHEXT")),
        "resolved": resolved,
        "bare": _run(ns.command, command_args, env, ns.timeout),
        "resolved_launch": (
            _run(resolved, command_args, env, ns.timeout) if resolved else None
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    resolved_result = result["resolved_launch"]
    return 0 if isinstance(resolved_result, dict) and resolved_result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
