---
name: agent-internals-forensics
description: "Use when reverse-engineering another agent CLI's internals."
version: 1.0.0
author: Masia
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [reverse-engineering, agents, prompts, bun, transcripts, design-port]
    related_skills: [hermes-plugin-development, reverse-engineer-anything, codebase-onboarding]
---

# Agent internals forensics

Recover how a *shipped* coding agent works — prompt shape, tool surface, scheduling, delivery —
from the artifact and the residue it leaves on disk, then turn that into a design for our system.

## When to Use

- "How does <agent> implement X", "compare their reviewer/adviser/planner with ours", "port this
  feature into Hermes".
- The thing is a binary or package the user runs, not a source checkout you can open.
- You need evidence, not a blog-post summary: the deliverable is a mechanism table plus a mapping
  to our seams.

Skip it when the source repo is available — read the source, that is cheaper and exact.

## Procedure

1. **Pin the build.** `<bin> --version`, install directory, binary size/date. Write the version in
   the report; upstream `main` may be months ahead, so every code reference carries that caveat.
2. **Read `--help` end to end.** Look for a verb that dumps internals: `agents unpack`, `config
   dump`, `--print-system-prompt`, `debug *`. A supported unpack command writes prompt/agent assets
   to a user directory and beats string archaeology.
3. **Classify the artifact.** Source tree / bundled JS (Bun, Node SEA, pkg) / ASAR / native /
   managed. Bundled JS: see `references/bundled-js-binaries.md`. ASAR: unpack and read. Native:
   strings + symbols, or the REA tooling in `reverse-engineer-anything`.
4. **Map files before reading code.** In bundled JS, grep for section comments of the form
   `// packages/<pkg>/src/<path>.ts` with byte offsets. The gaps between marks are the minified
   files, in build order. Extract the JS region to a scratch file and grep that; never pull a
   200 MB binary into context.
5. **Recover prompts and assets.** Embedded `.md` assets show up as handles like
   `y("B:/~BUN/root/<name>-<hash>.md")` while the bodies are often compressed. Do not spend the
   session decoding them: fetch the same paths from the upstream repo at the closest tag and
   verify two or three distinctive sentences byte-for-byte against the local binary.
6. **Mine local session data.** `<home>/sessions/**`, `*.jsonl`, sqlite. Side-agent transcripts
   (one file per reviewer/planner) show the exact input format — headers, truncation markers,
   `[in progress]` flags — and the structured outputs, which is often better evidence than the
   prompt itself. Check whether the user's data was produced by the version under analysis.
7. **Extract the checklist:** config keys and defaults, tool/permission surface, prompt composition
   order, trigger/scheduling rules, delivery channels, cost/limit handling, failure paths.
8. **Verify each claim:** byte-search the binary or stat the file; keep the offset or line. Mark
   observed vs inferred vs unknown, and list what you could not verify.

## Pitfalls

- **Search both encodings.** Prompt tables and Windows resources are often UTF-16LE; a UTF-8 grep
  that finds nothing has not proven absence. Search the UTF-16LE form too.
- **Minified identifiers are noise.** `$6e`, `Xp`, `pde` mean nothing across builds; anchor on
  section comments, user-visible strings, error messages, and config key names.
- **Upstream parity is not given.** Verify a constant you rely on (a default, a schema field) in
  the local binary before citing upstream line numbers as if they were the running code.
- **Docs describe intent; the artifact describes behavior.** When they disagree, the artifact wins;
  record both and say which one the design follows.
- **Do not copy the target's prompts into the repo.** Port the semantics (role, evidence rules,
  severity definitions) in your own words and quote only the short fragment the design needs.
  Licensing applies to prompt text exactly as it does to code.
- **Behavioral evidence can be stale.** Transcripts only reflect how the user actually drove the
  agent; a feature never exercised locally has no transcript, so absence proves nothing.

## Output shape

1. Mechanism table: component → responsibility → evidence (`file:line`, byte offset, version).
2. Capability mapping to our system: per mechanism one verdict — direct translation, degraded,
   impossible — with the exact seam that implements it.
3. Evidence index and an explicit "not verified" list.
4. If the user then asks to implement, the mapping's seam column is the implementation plan; keep
   one design doc in the repo and implement in slices with tests per slice.

## Reference

`references/bundled-js-binaries.md` — locate the JS region, build a file map, handle embedded
prompt assets, and read side-agent transcripts.
