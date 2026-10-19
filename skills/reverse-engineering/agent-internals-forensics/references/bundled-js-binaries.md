# Bundled JS agent binaries

Concrete commands for a compiled JS agent (Bun single-file, Node SEA, pkg snapshot). Run them from
a scratch directory; never load the whole binary into the conversation.

## 1. Identify the packer

```bash
file <bin>
<bin> --version
<bin> --help | grep -iE 'unpack|dump|export|print.*prompt'
strings -n 8 <bin> | grep -m5 -E 'B:/~BUN/root/|NODE_SEA_BLOB|/snapshot/|__bun'
```

| Marker | Packer | Notes |
|---|---|---|
| `B:/~BUN/root/` | Bun single-file | embedded assets + `bunfs` table near EOF |
| `NODE_SEA_BLOB` | Node SEA | blob appended to the node binary |
| `/snapshot/` | pkg | virtual FS, `PKG_` env errors |

## 2. Build the file map (Bun example)

```python
import re
data = open(path, 'rb').read()
marks = [(m.start(), m.group(1)) for m in
         re.finditer(rb'// (packages/[^\n]{3,120})', data)]
print(len(marks), marks[0][0], marks[-1][0])
```

Each mark is the start of a bundled source file; the section runs to the next mark. Dump the
contiguous region between the first and last mark (plus slack) as UTF-8 to a scratch file and grep
that. Typical layout: one large JS region, then a tail with the asset-name table.

## 3. Embedded prompt assets

References look like `var FD = y("B:/~BUN/root/system-fr2m7089.md")`. The name table sits near EOF
but the bodies are frequently compressed, so a plain UTF-8 search finds only the handle. Recover the
text from the upstream repo instead:

```text
https://raw.githubusercontent.com/<owner>/<repo>/main/<path>
```

If the repo was renamed or mirrored, search a distinctive sentence from a recovered prompt to find
a mirror. Then confirm 2-3 sentences exist in the local binary (byte search, UTF-8 and UTF-16LE) so
the design cannot be dismissed as upstream drift.

## 4. Side-agent transcripts

Agents that run reviewers/planners/advisers record them next to the main session:

```text
<home>/sessions/<cwd>/<session>/__advisor*.jsonl
```

Each line is a JSON record (`{"type": "message", "message": {...}}`). Parse them with Python rather
than reading raw: the first user messages show the exact injected format (headers, truncation
markers, `[in progress]` flags), and the assistant tool calls show the structured output contract.
This is behavioral evidence from the real build the user runs.

## 5. Budget

- Dump only the regions you need; grep the scratch text and print ±3 KB windows.
- Deduplicate hits before printing; a minified bundle has hundreds of identifier collisions.
- Keep a small `(offset, path)` map so every later quote can cite a location.
