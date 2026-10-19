#!/usr/bin/env python3
"""SHA256 tree-parity check for deployed / profile extension trees.

Usage:
  python tree_parity_check.py <src_dir> <dst_dir> [<dst_dir> ...]

Compares every non-cache file by CONTENT hash — never by mtime. Live files such as
skills/.usage.json and skills/.bundled_manifest are rewritten by running sessions, so
metadata-based comparisons report phantom drift; content sha is the arbiter.
Cache dirs (__pycache__, .pytest_cache) and *.py[co] are excluded on both sides.

Typical calls:
  python tree_parity_check.py <repo>/plugin/lancedb %LOCALAPPDATA%/hermes/plugins/lancedb
  python tree_parity_check.py %LOCALAPPDATA%/hermes/plugins/lancedb \\
      %LOCALAPPDATA%/hermes/profiles/qa1/plugins/lancedb \\
      %LOCALAPPDATA%/hermes/profiles/cto/plugins/lancedb

Exit codes: 0 = every pair IDENTICAL, 1 = some pair drifted or is missing, 2 = usage.
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

EXCLUDE_DIRS = {"__pycache__", ".pytest_cache"}
EXCLUDE_SUFFIXES = (".pyc", ".pyo")


def files(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for current, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for name in names:
            if name.endswith(EXCLUDE_SUFFIXES):
                continue
            path = Path(current) / name
            out[path.relative_to(root).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    return out


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    src = Path(argv[1]).resolve()
    if not src.is_dir():
        print(f"ERROR: source is not a directory: {src}")
        return 2
    base = files(src)
    print(f"source: {src}  files={len(base)}")
    drifted = 0
    for raw in argv[2:]:
        dst = Path(raw).resolve()
        if not dst.is_dir():
            print(f"--- {dst}: MISSING")
            drifted += 1
            continue
        target = files(dst)
        only_src = sorted(set(base).difference(target))
        only_dst = sorted(set(target).difference(base))
        differ = sorted(
            key for key in set(base).intersection(target) if base[key] != target[key]
        )
        verdict = "IDENTICAL" if not (only_src or only_dst or differ) else "DRIFT"
        print(
            f"--- {dst}\n"
            f"    files={len(target)} only_in_src={len(only_src)} "
            f"only_in_dst={len(only_dst)} differing={len(differ)} -> {verdict}"
        )
        for label, items in (
            ("only_in_src", only_src),
            ("only_in_dst", only_dst),
            ("differing", differ),
        ):
            for key in items[:10]:
                print(f"    {label}: {key}")
            if len(items) > 10:
                print(f"    {label}: ... ({len(items) - 10} more)")
        if verdict != "IDENTICAL":
            drifted += 1
    return 1 if drifted else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
