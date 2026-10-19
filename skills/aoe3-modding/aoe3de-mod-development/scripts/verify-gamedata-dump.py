#!/usr/bin/env python3
"""Verify GEMOD content merged into the game DebugOutputGameData dump.

Usage:
  python verify-gamedata-dump.py NAME [NAME ...] [--show] [--dir DIR]

Run the game once first (startup regenerates the dump, ~60-90s; see the
DebugOutputGameData notes in SKILL.md), then run this to confirm that unit
names / tech names / string ids / tactics actions actually merged.
Exit code 0 = every NAME found at least once; 2 = some missing.
"""

import os
import sys

DUMP_DEFAULT = '<USER_HOME>/AppData/Local/Temp/Age of Empires 3 DE/Data/data'


def load(path):
    raw = open(path, 'rb').read()
    texts = []
    for enc in ('utf-16', 'utf-8-sig', 'utf-8', 'latin-1'):
        try:
            texts.append(raw.decode(enc))
        except Exception:
            pass
    if not texts:
        return raw.decode('latin-1', 'replace')
    # Pick the decode that looks most like XML: a wrong-encoding decode yields
    # mojibake with far fewer '<' characters and would cause false misses.
    return max(texts, key=lambda t: t.count('<'))


def main():
    args = sys.argv[1:]
    show = '--show' in args
    if show:
        args.remove('--show')
    dump = DUMP_DEFAULT
    if '--dir' in args:
        k = args.index('--dir')
        dump = args[k + 1]
        del args[k:k + 2]
    names = args
    if not names:
        print(__doc__)
        return 1
    hits = {n: 0 for n in names}
    files_checked = 0
    for root, _dirs, files in os.walk(dump):
        for f in sorted(files):
            p = os.path.join(root, f)
            try:
                text = load(p)
            except OSError:
                continue
            files_checked += 1
            rel = os.path.relpath(p, dump)
            for n in names:
                c = text.count(n)
                if c:
                    hits[n] += c
                    print('HIT  %-58s x%-4d %s' % (n, c, rel))
                    if show:
                        i = text.find(n)
                        print('     ...' + text[max(0, i - 140):i + 240] + '...')
    print()
    missing = [n for n in names if not hits[n]]
    for n in missing:
        print('MISS %s' % n)
    print('checked %d files under %s' % (files_checked, dump))
    print('result: %s' % ('ALL FOUND' if not missing else ('MISSING %d' % len(missing))))
    return 0 if not missing else 2


if __name__ == '__main__':
    sys.exit(main())
