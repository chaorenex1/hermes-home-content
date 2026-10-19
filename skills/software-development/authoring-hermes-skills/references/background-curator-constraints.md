# Background Curator Pass Constraints

Observed limits of a background skill-curator consolidation pass in Hermes. Each one changes what the pass can achieve, so plan around them before doing reconnaissance.

## Bundled and hub-installed skills are read-only to the curator

`patch`, `write_file`, and `delete` all refuse on a bundled skill:

```
Refusing background curator write_file for bundled skill '<name>'.
Refusing background curator delete for bundled skill '<name>'.
```

The refusal does **not** depend on `absorbed_into` and does **not** lift for a pass whose instructions enable pruning of built-ins. Consequences:

- A consolidation whose umbrella is bundled cannot complete: the umbrella cannot receive a `references/` file and its siblings cannot be archived.
- A consolidation whose *sibling* is bundled also cannot complete, even when the umbrella is agent-owned and the sibling's content is already a labeled branch of it.
- Never retry the refused op — one attempt establishes the policy. Report the gap and tell the user to run `hermes curator adopt <name>` first if they want the skill curator-managed.
- Plan the pass so agent-provenance skills are the umbrellas; treat bundled members as immovable neighbours and classify them as "blocked by policy", not "kept by judgement".

## SKILL.md patching is effectively single-shot per session

The read-before-write guard requires the target file's *content* to be returned in the current review turn. All of these were observed to fail the guard:

- a load whose result was deduped (`{"status": "unchanged", "content_returned": false}`),
- a content-returning load issued one turn earlier,
- a load of a supporting file (`references/...`), and
- a load of the same file through `file_path='SKILL.md'` after the name-only load.

So once a SKILL.md has been loaded, the load layer suppresses re-emission and the guard can never be satisfied again in that session: **a target is patchable only alongside its first content-returning load.**

Practical rules for a pass:

1. Do reconnaissance reads for decisions, then treat every one of those skills as unpatchable.
2. When a `references/` addition is needed, prefer `write_file` to a **new** path — new files need no read — and accept that the pointer line in SKILL.md cannot be added in that session. The file is still discoverable through the skill's `linked_files` listing.
3. Only create a plan that depends on a patch for a target you have not yet loaded.

## Reads that the loader refuses outright

A skill gated to another platform (`net: unsupported`) or disabled by the user cannot be loaded even by explicit `file_path='SKILL.md'`. Its content therefore cannot be verified, absorbed, or judged obsolete — leave it in place and say so rather than archiving on a guess.

## Ledger discipline

`skill_manage` is the only mutation surface available to the curator (no terminal). Every consolidation must go through `write_file` on the umbrella and `delete` with `absorbed_into=<umbrella>` on the source so `hermes curator rollback` can restore it; a shell `mv`/`cp` would archive an already-stripped package.
