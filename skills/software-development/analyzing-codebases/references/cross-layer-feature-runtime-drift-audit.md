# Cross-Layer Feature Runtime Drift Audit

Use this when a feature appears to exist in requirements, skills, plugins, backups, or old branches but may be absent from the currently running host.

## Evidence sequence

1. **Inventory the named artifacts precisely.** Resolve the exact requested path, similarly named files, file size/hash when identity matters, and any filename typo. Treat requirements, skills, source, installed copies, backups, and persisted state as different artifact classes.
2. **Prove current-HEAD ownership first.** Record branch, HEAD, dirty baseline, tracked paths, source occurrences, command/tool registrations, and one live help/status probe. Searching backups or all refs before current HEAD can create a false impression that a removed feature is active.
3. **Inspect historical implementations without checkout.** Use `git ls-tree`, `git show`, ancestry checks, and `git rev-list --left-right --count` against the current branch. Report the exact unique-commit distance and whether the historical implementation is an ancestor; never call an old branch deployable merely because its tests once passed.
4. **Separate Host reachability from Provider capability.** Trace `public entrypoint → registration → Host controller/state owner → plugin/provider call → persisted result → user-visible continuation`. Provider methods and green provider tests prove only capability, not production reachability.
5. **Verify source/deployment parity independently.** Hash the relevant editable-source and installed files, then run the smallest focused provider/plugin test. Label a matching but unreachable provider as **healthy but dormant**, not operational.
6. **Audit guidance as executable surface.** Compare active class-level skills, linked references, mirrored profile copies, command examples, and same-name workflows in other runtimes. An old linked reference is still active guidance even when a newer standalone skill exists.
7. **Build a contradiction matrix.** Compare requirement wording, current Host behavior, historical branch behavior, provider behavior, installed skill contract, and live CLI/UI result. Resolve identifier disagreements such as ID versus path, digest versus revision, or hyphenated versus underscored commands.
8. **Close read-only.** Recheck dirty status and distinguish pre-existing changes from audit footprint.

## Required verdicts

Report each layer as one of:

- **Current and reachable** — registered in current Host and exercised through a public surface.
- **Healthy but dormant** — implemented/deployed below the Host boundary with no current caller.
- **Historical only** — present only in non-ancestor branches, backups, or archived artifacts.
- **Guidance-only** — documented or skill-described without implementation reachability.
- **Split-brain** — two or more active instructions or surfaces prescribe incompatible contracts.

Lead with the end-to-end operational verdict. Do not infer runtime availability from a requirements file, a skill, an installed plugin, old test evidence, or a historical branch alone.
