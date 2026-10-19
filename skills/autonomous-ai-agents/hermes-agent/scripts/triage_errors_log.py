#!/usr/bin/env python3
"""Triage Hermes' errors.log: rank signatures, isolate one day, list tracebacks.

    python triage_errors_log.py --day 2026-10-19
    python triage_errors_log.py --tracebacks --top 40
    python triage_errors_log.py --log <HERMES_HOME>/logs/errors.log

A block begins at a line starting with a timestamp; every following line up to
the next timestamp belongs to it. Grouping by block (not by line) is the point:
one exception is one hit no matter how many frames it printed, and the whole
traceback stays attached to its event.
"""
from __future__ import annotations

import argparse
import collections
import os
import re
import sys
from pathlib import Path

TS = re.compile(r"^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})")
SID = re.compile(r"\[[0-9A-Za-z_\-]{6,}\]")
HASH = re.compile(r"\b[0-9a-f]{16,}\b")
NUM = re.compile(r"\b\d+\b")
EXC = re.compile(r"^(?:[A-Za-z_][\w.]*)?(?:Error|Exception|Timeout|Cancelled)\b")
ERROR_LEVEL = (" ERROR ", " CRITICAL ")


def default_log() -> Path:
    home = os.environ.get("HERMES_HOME")
    if home:
        return Path(home) / "logs" / "errors.log"
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "hermes" / "logs" / "errors.log"


def load_blocks(path: Path) -> list[tuple[str, list[str]]]:
    lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    starts = [i for i, line in enumerate(lines) if TS.match(line)]
    out: list[tuple[str, list[str]]] = []
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        out.append((TS.match(lines[start]).group(1), lines[start:end]))
    return out


def signature(line: str) -> str:
    """Same event twice == same signature: strip ids, hashes, counts."""
    text = TS.sub("", line)
    text = SID.sub("[SID]", text)
    text = HASH.sub("HASH", text)
    text = NUM.sub("N", text)
    return text[:170].strip()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log", default=str(default_log()))
    ap.add_argument("--day", help="YYYY-MM-DD: print that day's ERROR blocks in full")
    ap.add_argument("--top", type=int, default=25, help="signatures to rank (default 25)")
    ap.add_argument("--tracebacks", action="store_true",
                    help="also rank distinct traceback endings")
    ap.add_argument("--max-lines", type=int, default=40,
                    help="lines per printed block with --day (default 40)")
    args = ap.parse_args(argv)

    path = Path(args.log)
    if not path.exists():
        print(f"no log at {path} (set HERMES_HOME or pass --log)", file=sys.stderr)
        return 2

    blocks = load_blocks(path)
    if not blocks:
        print(f"no timestamped blocks in {path}")
        return 0

    per_day = collections.Counter(day for day, _ in blocks)
    print(f"{path}: {len(blocks)} blocks, {blocks[0][0]} .. {blocks[-1][0]}")
    for day, count in sorted(per_day.items()):
        print(f"  {day}: {count}")

    ranked: collections.Counter[str] = collections.Counter()
    seen: dict[str, list[str]] = {}
    for day, block in blocks:
        key = signature(block[0])
        ranked[key] += 1
        seen.setdefault(key, []).append(day)
    print(f"\ntop {args.top} signatures:")
    for key, count in ranked.most_common(args.top):
        days = seen[key]
        print(f"{count:4d}x  {days[0]}..{days[-1]}  {key}")

    if args.tracebacks:
        finals: collections.Counter[str] = collections.Counter()
        for _, block in blocks:
            for line in block:
                if line.startswith("Traceback (most recent call last)") or EXC.match(line.strip()):
                    finals[line.strip()[:160]] += 1
        print("\ntraceback endings:")
        for line, count in finals.most_common(15):
            print(f"{count:4d}x  {line}")

    if args.day:
        picked = [(d, b) for d, b in blocks if d == args.day]
        print(f"\n{len(picked)} blocks on {args.day}:")
        for day, block in picked:
            interesting = any(marker in (block[0] or "") for marker in ERROR_LEVEL) or any(
                "Traceback" in line for line in block)
            if not interesting:
                continue
            print("-" * 78)
            print("\n".join(block[: args.max_lines]))
            if len(block) > args.max_lines:
                print(f"... ({len(block) - args.max_lines} more lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
