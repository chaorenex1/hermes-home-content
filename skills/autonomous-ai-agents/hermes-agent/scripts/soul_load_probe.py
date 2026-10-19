#!/usr/bin/env python3
"""Load a candidate SOUL.md through the host's own loader, live file untouched.

    python scripts/soul_load_probe.py path/to/SOUL.md [--src DIR]

Copies the candidate into a throwaway home, then runs the hermes-agent venv
interpreter on agent.prompt_builder.load_soul_md(home_override=that home).
Prints size, heading count, truncation flag and every loader warning.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

CHILD = r"""
import json, logging, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
logging.basicConfig(level=logging.WARNING, stream=sys.stderr,
                    format="%(levelname)s %(message)s")
from agent.prompt_builder import load_soul_md
home = Path(tempfile.mkdtemp(prefix="soul-home-"))
shutil.copyfile(sys.argv[2], home / "SOUL.md")
out = load_soul_md(context_length=None, home_override=home) or ""
print(json.dumps({
    "chars": len(out),
    "words": len(out.split()),
    "headings": sum(1 for line in out.splitlines() if line.startswith("# ")),
    "truncated": "[...truncated" in out,
    "first_line": out.splitlines()[0] if out else None,
    "last_line": out.strip().splitlines()[-1] if out else None,
}))
"""


def find_src(explicit):
    roots = [explicit, os.environ.get("HERMES_SRC"),
             Path.home() / ".hermes" / "hermes-agent",
             Path(os.environ.get("LOCALAPPDATA", "")) / "hermes" / "hermes-agent"]
    for root in roots:
        if root and (Path(root) / "agent" / "prompt_builder.py").is_file():
            return Path(root)
    sys.exit("hermes-agent source not found; pass --src DIR")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("soul")
    ap.add_argument("--src")
    args = ap.parse_args()
    src = find_src(args.src)
    soul = Path(args.soul).resolve()
    if not soul.is_file():
        sys.exit(f"not a file: {soul}")
    venv = [src / ".venv" / "Scripts" / "python.exe", src / ".venv" / "bin" / "python"]
    python = next((p for p in venv if p.is_file()), Path(sys.executable))
    run = subprocess.run([str(python), "-c", CHILD, str(src), str(soul)],
                         capture_output=True, text=True)
    print(run.stdout.strip())
    warnings = [line for line in run.stderr.splitlines() if line.strip()]
    print(f"warnings: {len(warnings)}")
    for line in warnings[:10]:
        print(" ", line)
    return run.returncode


if __name__ == "__main__":
    raise SystemExit(main())
