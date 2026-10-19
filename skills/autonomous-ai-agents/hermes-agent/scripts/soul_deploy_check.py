#!/usr/bin/env python3
"""Deploy a candidate SOUL.md and prove it, or recover the previous body.

    python scripts/soul_deploy_check.py doc/hermes-soul.md [--home DIR] [--dry-run]
    python scripts/soul_deploy_check.py --recover OUT.md [--home DIR]

Deploy: hash live vs candidate, snapshot live, refuse a snapshot that already
equals the candidate, copy, then re-load the live home through the host
loader in the hermes-agent venv.
Recover: slice the previous SOUL out of the newest request dump in
$HERMES_HOME/sessions ("# Role" -> the host's "You run on Hermes Agent"
paragraph), which is the only reliable source when a snapshot is invalid.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

CHILD = r"""
import json, logging, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
logging.basicConfig(level=logging.WARNING, stream=sys.stderr,
                    format="%(levelname)s %(message)s")
from agent.prompt_builder import load_soul_md
out = load_soul_md(context_length=None, home_override=Path(sys.argv[2])) or ""
print(json.dumps({
    "chars": len(out),
    "words": len(out.split()),
    "headings": sum(1 for line in out.splitlines() if line.startswith("# ")),
    "truncated": "[...truncated" in out,
    "first_line": out.splitlines()[0] if out else None,
    "last_line": out.strip().splitlines()[-1] if out else None,
}))
"""


def default_home():
    env = os.environ.get("HERMES_HOME")
    if env:
        return Path(env)
    for base in (os.environ.get("LOCALAPPDATA"), os.environ.get("APPDATA")):
        if base and (Path(base) / "hermes" / "SOUL.md").exists():
            return Path(base) / "hermes"
    return Path.home() / ".hermes"


def find_src():
    roots = [os.environ.get("HERMES_SRC"),
             Path.home() / ".hermes" / "hermes-agent",
             Path(os.environ.get("LOCALAPPDATA", "")) / "hermes" / "hermes-agent"]
    for root in roots:
        if root and (Path(root) / "agent" / "prompt_builder.py").is_file():
            return Path(root)
    sys.exit("hermes-agent source not found; set HERMES_SRC")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_live(home):
    src = find_src()
    venv = [src / ".venv" / "Scripts" / "python.exe", src / ".venv" / "bin" / "python"]
    python = next((p for p in venv if p.is_file()), Path(sys.executable))
    run = subprocess.run([str(python), "-c", CHILD, str(src), str(home)],
                         capture_output=True, text=True)
    print(run.stdout.strip())
    for line in run.stderr.splitlines():
        if line.strip():
            print(" ", line)
    return run.returncode


def deploy(candidate, home, dry_run):
    cand, live = Path(candidate).resolve(), home / "SOUL.md"
    if not cand.is_file():
        sys.exit(f"not a file: {cand}")
    ch = sha(cand)
    lh = sha(live) if live.exists() else None
    print(f"candidate sha={ch[:16]} live sha={(lh or 'missing')[:16]}")
    if lh == ch:
        print("already deployed: live equals candidate; no pre-deploy snapshot can exist")
        return load_live(home)
    if live.exists():
        backup = home / f"SOUL.md.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        shutil.copy2(live, backup)
        if sha(backup) == ch:
            print(f"BACKUP_INVALID: {backup} already holds the candidate; not a rollback point")
            return 3
        print(f"snapshot: {backup} sha={sha(backup)[:16]}")
    if dry_run:
        print("dry run: live untouched")
        return 0
    shutil.copyfile(cand, live)
    print(f"live sha={sha(live)[:16]} equal={sha(live) == ch}")
    return load_live(home)


def recover(out_path, home):
    dumps = sorted((home / "sessions").glob("request_dump_*.json"),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    if not dumps:
        sys.exit(f"no request dumps under {home / 'sessions'}")
    marker = re.compile(r"\n{1,3}\s*You run on Hermes Agent")
    for dump in dumps[:20]:
        try:
            data = json.loads(dump.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        texts = []

        def walk(o):
            if isinstance(o, str):
                if "# Role" in o and len(o) > 4000:
                    texts.append(o)
            elif isinstance(o, dict):
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)

        walk(data)
        for t in sorted(texts, key=len, reverse=True):
            start = t.find("# Role")
            if start < 0:
                continue
            m = marker.search(t, start)
            end = m.start() if m else t.find("\n# Finishing the job", start)
            if end <= start:
                continue
            soul = t[start:end].rstrip() + "\n"
            heads = sum(1 for line in soul.splitlines() if line.startswith("# "))
            if heads < 10:
                continue
            Path(out_path).write_text(soul, encoding="utf-8")
            print(f"recovered from {dump.name}: chars={len(soul)} "
                  f"words={len(soul.split())} headings={heads}")
            return 0
    sys.exit("no usable SOUL block found in dumps")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("candidate", nargs="?")
    ap.add_argument("--home")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--recover", metavar="OUT")
    a = ap.parse_args()
    home = Path(a.home) if a.home else default_home()
    if a.recover:
        return recover(a.recover, home)
    if not a.candidate:
        ap.error("candidate or --recover required")
    return deploy(a.candidate, home, a.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
