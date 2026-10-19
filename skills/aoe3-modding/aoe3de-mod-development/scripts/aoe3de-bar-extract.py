#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AoE3DE .bar (ESPN v6) file-table parser + extractor.  No external deps.

Verified format (2026-10, ArtEffects.bar / Art.bar / UI.bar, current DE build):
  - Tail of the .bar = file table. Each record (contiguous):
        [u32 f1][u32 data_offset][u32 zero][u32 s1][u32 s2][u32 s3]
        [u32 name_len_chars][utf-16le name]
    The six u32 fields PRECEDE the name block: read 24 bytes before the
    name_len u32. Reading them AFTER the name silently yields the NEIGHBOUR
    file's fields -- always sanity-check extracted head bytes.
  - f1=1: stored raw; s1 bytes at data_offset (s3 = padded block size).
  - f1=0: LZ4; at data_offset: b'alz4' + u32 uncompressed_size +
    u32 compressed_size + u32(1), then the LZ4 block stream.
  - .ddt textures may be extra-obfuscated in DE bars; returns stored bytes.
  - The file table is located by scanning for needle substrings, normalizing
    each hit to its full name (walk back/forward), validating the name_len
    u32, then chaining candidates by exact 28+2*nl stride. UI.bar has no
    "effects\\" names, so the old single-needle scan found 0 records -> now
    multi-needle by default (effects\\, resources\\, xaml, ui).

Usage:
  python aoe3de-bar-extract.py <bar> list [substr] [--needle STR[,STR...]]
  python aoe3de-bar-extract.py <bar> extract <name> <out_path> [--needle STR[,STR...]]

Examples:
  python aoe3de-bar-extract.py "H:/.../Game/UI/UI.bar" list xaml
  python aoe3de-bar-extract.py "H:/.../Game/UI/UI.bar" extract uimainnew.xaml out.xaml
  (for a bar whose names match none of the defaults, add --needle with any
   substring of known entry names)

Python API:
  from aoe3de_bar_extract import BarTable   # (import from this file's dir)
  t = BarTable(r'...\\ArtEffects.bar')
  data, how = t.extract(r'effects\\ypack_auras\\econpower.xml.XMB')
  t.close()
"""
import mmap
import re
import struct
import sys

DEFAULT_NEEDLES = ["effects\\", "resources\\", "xaml", "ui"]


class BarTable:
    def __init__(self, path, needles=None):
        self.path = path
        self.f = open(path, "rb")
        self.mm = mmap.mmap(self.f.fileno(), 0, access=mmap.ACCESS_READ)
        self.names = []          # ordered record names
        self._name_pos = {}      # name -> (nlen_pos, name_pos, nlen)
        self._build(needles or DEFAULT_NEEDLES)

    def _try_at(self, hp, namechars):
        """Normalize a needle hit to a full record name and validate it."""
        mm = self.mm
        s = hp
        while s >= 6:
            try:
                ch = bytes(mm[s - 2:s]).decode("utf-16-le")
            except Exception:
                break
            if namechars.match(ch):
                s -= 2
            else:
                break
        e = hp
        n = len(mm)
        while e + 2 <= n:
            try:
                ch = bytes(mm[e:e + 2]).decode("utf-16-le")
            except Exception:
                break
            if namechars.match(ch):
                e += 2
            else:
                break
        name = bytes(mm[s:e]).decode("utf-16-le")
        nl = (e - s) // 2
        if not (4 <= nl <= 250) or s - 4 < 0:
            return None
        if struct.unpack_from("<I", mm, s - 4)[0] != nl or len(name) != nl:
            return None
        return (s - 4, s, nl, name)

    def _build(self, needles):
        mm = self.mm
        namechars = re.compile(r"^[A-Za-z0-9_\\.\- ,()]+$")
        cands = {}
        for nd in needles:
            nb = nd.encode("utf-16-le")
            pos = 0
            while True:
                hp = mm.find(nb, pos)
                if hp < 0:
                    break
                c = self._try_at(hp, namechars)
                if c:
                    cands[c[0]] = c
                pos = hp + 2
        starts = {c[0]: c for c in cands.values()}
        # longest contiguous chain = the real file table
        best = None
        seen = set()
        for c in sorted(cands.values()):
            if c[0] in seen:
                continue
            cur = c
            cnt = 0
            while cur is not None and cur[0] not in seen and cnt < 100000:
                seen.add(cur[0])
                cnt += 1
                cur = starts.get(cur[0] + 28 + 2 * cur[2])
            if best is None or cnt > best[1]:
                best = (c, cnt)
        if best is None:
            raise RuntimeError(
                "no file-table candidates found (needles=%r). Pass --needle "
                "with a substring of known entry names." % (needles,))
        cur = best[0]
        while cur is not None:
            start, hp, nl, s = cur
            self.names.append(s)
            self._name_pos[s] = (start, hp, nl)
            cur = starts.get(start + 28 + 2 * nl)

    def fields_by_name(self, name):
        """Return (f1, offset, zero, s1, s2, s3) for a table entry or None.
        Fields live 24 bytes BEFORE the name_len u32 that precedes the name."""
        p = self._name_pos.get(name)
        if not p:
            hp = self.mm.find(name.encode("utf-16-le"))
            if hp < 0:
                return None
            return struct.unpack_from("<6I", self.mm, hp - 4 - 24)
        return struct.unpack_from("<6I", self.mm, p[0] - 24)

    def extract(self, name):
        """Return (bytes, status). Handles raw (f1=1) and LZ4 (f1=0)."""
        fl = self.fields_by_name(name)
        if fl is None:
            return None, "no-such-name"
        f1, off, z, s1, s2, s3 = fl
        raw = bytes(self.mm[off:off + s3])
        if raw[:4] == b"alz4":
            usize = struct.unpack_from("<I", raw, 4)[0]
            out, why = lz4_block(raw[16:], expected=usize)
            return out, "lz4 %d/%d %s" % (len(out), usize, why)
        return raw[:s1], "raw %d" % s1

    def list(self, substr=None):
        return [n for n in self.names if substr is None or substr in n]

    def close(self):
        try:
            self.mm.close()
        finally:
            self.f.close()


def lz4_block(src, expected=None):
    """Minimal LZ4 block-format decoder (no external deps)."""
    out = bytearray()
    pos = 0
    n = len(src)
    while pos < n:
        token = src[pos]
        pos += 1
        lit = token >> 4
        if lit == 15:
            while True:
                if pos >= n:
                    return bytes(out), "eof-lit"
                b = src[pos]
                pos += 1
                lit += b
                if b != 255:
                    break
        out += src[pos:pos + lit]
        pos += lit
        if pos >= n:
            return bytes(out), "eof"
        if pos + 2 > n:
            return bytes(out), "eof2"
        offset = src[pos] | (src[pos + 1] << 8)
        pos += 2
        if offset == 0:
            return bytes(out), "off0"
        mlen = token & 0xF
        if mlen == 15:
            while True:
                if pos >= n:
                    return bytes(out), "eof3"
                b = src[pos]
                pos += 1
                mlen += b
                if b != 255:
                    break
        mlen += 4
        start = len(out) - offset
        if start < 0:
            return bytes(out), "badstart"
        for i in range(mlen):
            if start + i >= len(out):
                return bytes(out), "desync"
            out.append(out[start + i])
        if expected and len(out) >= expected:
            return bytes(out), "reached"
    return bytes(out), "loop-end"


def main():
    argv = list(sys.argv)
    needles = None
    if "--needle" in argv:
        i = argv.index("--needle")
        if i + 1 >= len(argv):
            print(__doc__)
            return 1
        needles = argv[i + 1].split(",")
        del argv[i:i + 2]
    if len(argv) < 3:
        print(__doc__)
        return 1
    bar = argv[1]
    cmd = argv[2]
    t = BarTable(bar, needles)
    try:
        if cmd == "list":
            sub = argv[3] if len(argv) > 3 else None
            for n in t.list(sub):
                print(n)
            print("# total %d records" % len(t.names))
        elif cmd == "extract":
            name = argv[3]
            outp = argv[4]
            data, how = t.extract(name)
            if data is None:
                print("MISS", name)
                return 2
            open(outp, "wb").write(data)
            print("wrote", outp, len(data), "bytes (" + how + ")")
            print("head:", data[:32].hex())
        else:
            print(__doc__)
            return 1
    finally:
        t.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
