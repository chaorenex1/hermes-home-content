---
name: researching-bgs-mod-internals
description: Use when asked how a BGS mod works internally.
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [bgs-modding, research, source-analysis, mod-internals]
    related_skills: [diagnosing-bgs-problems, evaluating-bgs-mods, archify]
---

# Researching BGS Mod Internals

## When to Use

Use when the user asks how a Bethesda mod or framework works internally: "研究一下X原理", "how does this mod work", "why is it faster", "这个框架怎么实现的", "what does this setting actually do".

Not for inclusion verdicts (use `evaluating-bgs-mods`) or symptoms (use `diagnosing-bgs-problems`).

The mod page is a claim; the source is evidence. Version, requirements, and author intent come from Nexus; behavior comes from a pinned commit of the authoritative repository, or, when the uploader ships no repository, from the distributed DLL itself. A DLL/framework mod is an engine, so explain the layer boundary first: what it computes, what content mods supply, and which layer a user-facing problem belongs to.

## Procedure

1. Query the KB first for engine/framework facts about the current game. If the pack has no record, say `[GAP]` and continue with source evidence.
2. Read the Nexus page for version, uploader, requirements, and the Source Code spoiler. Descriptions sell behavior and routinely omit architecture; never build the explanation from them alone.
3. Resolve the authoritative repo and its fork chain. Framework DLLs are usually forks of forks; the repo linked by the current uploader wins. Record `git rev-parse HEAD` and the credential-free origin. No repo and no source spoiler means step 4b, not a description-based answer.
4. Clone shallow into the scratch directory (`git clone --depth 1 <url>`), then pin `git log -1 --format='%H %ad %s'`. Read files from disk; do not page source through a web extractor.
4b. Closed-source plugin: download the archive, record the archive hash and entry sizes, then recover the design from the binary (build-provenance strings, string table, hook sites, and the IDs/offsets each site uses). Full recipe in `references/dll-static-reverse-engineering.md`. Map every recovered numeric ID onto CommonLibSSE-NG before naming anything: clone the framework at a pinned commit and grep the ID under `include/RE/`; class headers carry member offsets as `// 0xNN` and `Offsets_VTABLE.h` carries the `VTABLE_*` variant IDs.
5. Map before reading: directory tree, file sizes, entry point (SKSE `main.cpp` / hooks), frame loop, domain core, and config parser. Read that connected slice instead of the whole tree.
6. Trace one frame end to end and write down thread, stage, input, output for each step. That skeleton is the answer; details hang off it.
7. Verify every quantitative claim in source: solver constants, caps, timestep defaults. Grep build presets before crediting an ISA path (`#ifdef AVX2` code is dead unless a preset passes `/arch:AVX2`). Grep for a capability before denying it (`grep -ri cuda`) rather than trusting a leftover comment.
8. Separate engine from content: physics/animation/skeleton frameworks provide the runtime; XML, NIF, and ESP files supplied by content mods are a different layer. State which layer owns the behavior a user is asking about.
9. Deliver in this order: what it is not, data model, per-frame pipeline, cost model (why it is fast), hard limits, practical knobs. Cite repository-relative paths with line ranges.
10. When the conclusion has structure, produce one archify diagram and keep the prose numbers identical to it.

## Pitfalls

- Do not explain a fork by its ancestor's README. Check whether the current code still uses the ancestor's solver or replaced it.
- Comments are not features. An extension-point comment or an unbuilt `#ifdef` branch does not ship in the DLL.
- Do not repeat marketing performance claims. Derive the cost model from what the code skips (culling, parallelism, caching) and from its hard caps.
- "Soft" behavior may not come from simulating the mesh at all. Find what is actually integrated before explaining softness, jiggle, or stiffness.
- If neither a repository nor an inspectable binary is available, mark the explanation as description-based `[unverified]`; do not present the mod page as architecture.
- Read the runtime dispatch before trusting any constant table. `REL::Module::Runtime` is a bitmask (`AE = 1`, `SE = 2`, `VR = 4`), so a compare against `2` selects SE and `4` selects VR; assuming 1/2/3 ordering silently swaps every ID, vtable, and struct offset in the answer.
- Confirm a struct identity by a layout fingerprint, not by one matching field. `ShadowSceneNode` on VR shifts every member by the documented `+0x28`; a candidate table that shifts by exactly that delta is the same object, while one landing on a plausible member proves nothing.
- A vtable byte offset divided by pointer size is the slot index the framework comments use: on x64 `vtable + 0x150` is slot `0x2A`, which CommonLibSSE-NG names `BSShaderProperty::GetRenderPasses`. Never infer the method from its neighbouring slots.
- Read the plugin's own pre-patch guards to learn the intended target: an opcode-byte check plus a callee-ID comparison names the hook target even when the engine function has no symbol. Cite that ID, and label any human-readable engine name as inference.
- A fix that only writes engine render caches (per-object masks, per-pass arrays) is safe to add and remove because it never touches records or saves; say that explicitly instead of implying the plugin rewrites the renderer.

## Output conventions

- Reply in the user's language; keep file names, API names, console commands, and numeric constants verbatim.
- Lead with the one-sentence mechanism, then the layered explanation; do not open with history.
- Distinguish verified source facts from inference; label anything not exercised or read.

## See also

- `references/fsmp-physics-pipeline.md` — worked example: Faster HDT-SMP data model, frame pipeline, collision limits, and tuning map.
- `references/dll-static-reverse-engineering.md` — no-source plugin: PE/capstone procedure, string-to-function xref, and mapping recovered IDs onto CommonLibSSE-NG headers.
- `diagnosing-bgs-problems` — when the question is a symptom rather than a mechanism.
- `archify` — pipeline or architecture diagram for the explanation.
