---
name: ralph-planning
description: "Write executable meta-plans under Ralph planning mode — patch-level updates to existing plan documents with new_string content, verification commands, and blocker conditions. Do NOT include old_string blocks."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [planning, ralph, meta-plan, plan-update, verification]
    related_skills: [plan, subagent-driven-development]
---

# Ralph Planning Mode

Use this skill when the user is in Ralph planning mode (`/ralph` or `[Ralph planning mode]`)
and the objective involves **updating an existing plan file**.

## Difference from `plan` Skill

| | `plan` skill | `ralph-planning` skill |
|---|---|---|
| Deliverable | New plan from scratch | Updated version of existing plan |
| Target audience | Human implementer | Ralph loop (automated review) |
| Granularity | Task-level (2-5 min each) | Patch-level (exact string ops) |
| Verification | Test commands | read_file + search_files assertions |
| Failure mode | Human catches gaps | Ralph loop rejects and requests retry |

## Core Behavior

For this turn, you are **planning a plan update**. You must:

- Read the existing plan file in full (all sections you'll touch)
- Read the authoritative sources that triggered the update (ABC source, docs, user requirements)
- Classify the objective before adding implementation workflow. A request to calculate, simplify, prove, or otherwise solve a mathematical expression is a **math task**, not a repository task, unless the user explicitly asks for code. For a math task, remove repository discovery, source/test paths, command execution, dependency, deployment, and file-level rollback work; define the mathematical domain, special cases, derivation, symbolic/numeric output boundary, and mathematical verification instead.
- When a math request names a variable but supplies no value, plan a symbolic result and state that a numeric result requires the value; do not invent a repository or block on an implementation target.
- Write an **executable meta-plan** — a sequence of `patch` operations with:
  - Exact `old_string` copied from the target file (via `read_file`, not memory)
  - Exact `new_string` replacement text
  - Verification command (`read_file` or `search_files`) with expected output keywords
  - Failure recovery path (re-read, adjust, retry — max 2)
- Save to the designated plan file (given in the Ralph directive)
- Do NOT implement, run mutating commands, or modify any other file

## Ralph Loop Rejection Signals

The Ralph loop will reject a plan that:
1. Describes gaps without executable patch operations — needs a gap→patch mapping table
2. Has no verification commands with expected output keywords
3. Lacks blocker/stop conditions (what stops the entire sequence?)
4. Uses vague references ("§4 needs updating") instead of exact section targets and new_string content
5. Presents as a prose narrative rather than an ordered, numbered patch sequence

**Expect 1-3 rejection cycles.** First rejection: add verification commands. Second: add concrete new_string content. Third: fundamentally wrong approach.

## Meta-Plan Structure

```markdown
# [Target Plan] Update — Execution-Level Meta-Plan

**Goal:** [One sentence]
**Evidence sources:** [Table: source | what it proves]
**Architecture:** [How many patches, what order, why]

## Gap & Mapping Table

| # | Target Lines | Operation | Evidence Trigger |
|---|-------------|-----------|-----------------|
| P1 | L15 (§1 bullet) | replace | [source change] |

## Execution Order & Constraints

P1→P2→... must be SEQUENTIAL because [line drift / dependency reason].

**Blocking conditions (stop ALL subsequent patches):**
1. Any patch returns `error` → stop, report patch # and error
2. Verification read_file doesn't contain expected text → stop
3. Consistency check finds contradiction → stop, report location

## P1: [Name]

**Target:** §X in target file
**Content to inject:** [the new_string text — what gets written]
**Verification:** `read_file(offset=N, limit=M)` → expected: [keywords]
**Failure recovery:** [what to try if patch fails]

## P[N]: Full-Text Consistency Review

| Check | Method | Pass Criterion |
|-------|--------|---------------|
| No stale imports/calls | search_files | 0 results |
| Hook name cross-refs | search_files | ≥ N occurrences |
| ... | ... | ... |

## Risks & Mitigations

| Risk | Probability | Mitigation |
|------|------------|-----------|
| Line number drift after inserts | High | Use search_files to re-locate before each patch |
| old_string mismatch (whitespace) | Medium | Copy from read_file output, not memory |
```

## Critical Pitfalls

### Do NOT include old_string in meta-plans
The meta-plan is a **design document** — only `new_string` content and verification criteria
belong in it. `old_string` blocks are implementation details for the patch tool's find-target.
They bloat the plan and make it unreadable as a design doc. The user explicitly prefers clean
meta-plans without `old_string`. When executing the plan later, the executor resolves
old_string from the target file using search_files/read_file.

### Iterative Refinement Pattern
Users often provide requirements incrementally across 2-6 rounds. Each round:
1. Analyze the new requirement — which sections (§2/§3/§4/§5/§6/§7) are affected?
2. Classify the message before editing: a plan-content change updates the designated plan; an out-of-scope question or analysis request must be answered without writing the plan. Treat explicit “分析/先分析/不要写计划内容” as analysis-only.
3. Insert a new patch (P2a, P2b, P2c, ...) into the meta-plan when the requirement adds genuinely new scope.
4. Update the gap table, execution order, and full review checks.
5. Keep prior patches intact by default. If the user explicitly says a later patch replaces an earlier patch, convert the earlier patch into a non-executable superseded marker, make the replacement target/operation/order/verification explicit, and ensure both versions cannot be executed or coexist.
6. Maintain one authoritative specification per concept. If a patch owns a taxonomy or document templates, put the complete templates there; downstream sections must describe only implementation behavior, CRUD, synchronization, or tests and must not duplicate competing template definitions.
7. Preserve semantic corrections exactly: distinguish project knowledge documents from a generic container while retaining explicitly requested project-scoped CRUD; keep tool-use statistics separate from entity subtypes; do not add `confidence` or `context_relevance` fields when the user has removed them; and never generate dynamic fields without evidence.
8. Treat “some memory-type templates are undefined” as a completeness gap, not a wording tweak: the authoritative template patch must contain an explicit path, frontmatter/type binding, body sections, evidence/omission rules, summary rule, and injection behavior for every declared type. Verify all type headings and required sections after insertion; do not rely on a prose claim that templates are complete.
9. For algorithmic requirements, specify the runtime state machine, bounded budgets, structured return contract, failure semantics, and tests—not just prose describing the desired behavior.
10. If the requirement adds staged retrieval or fallback behavior, make early success explicit, record evidence for each stage, and define a hard server-side maximum so the model cannot bypass the bound.
11. For large implementation plans, insert an explicit MVP gate before the full patch sequence. Define the smallest end-to-end closed loop, what is explicitly out of scope, the exact tests/evidence required, and a hard stop condition: later extensions must not proceed until the MVP passes.
12. For entity-memory templates, distinguish metadata/provenance from entity properties. Do not make fields such as context relevance, extraction method, mention counts, or first/last-seen timestamps part of the entity template when the requirement is dynamic properties only. Define subtype examples as non-binding possibilities; extract only properties evidenced in the source (for example, a script may have only function, inputs, and outputs), without auto-filling absent fields, fixed sections, or `none` placeholders.
13. When a plan has a single authoritative template section, keep downstream implementation/verification sections referential rather than duplicating or contradicting the template. Verify both positive presence of the authoritative template and negative absence of superseded fields or competing fixed schemas.

### Multi-round retrieval requirements
When a plan adds goal-driven retrieval over hierarchical memory, model it as a bounded state machine rather than a generic “search more” loop:

- Round 1 should use cheap directory-level signals first (for example, vector search over directory summaries plus FTS over detailed summaries) and return immediately when those signals satisfy the goal.
- Only after an explicit insufficiency decision should the plan invoke semantic goal decomposition, such as identifying multiple allowed memory types and mapping them to known top-level directories.
- Later rounds should depth-first/breadth-first traverse only mapped directories, read documents in bounded batches, and judge them against the original goal plus required fields.
- Define a maximum round count enforced by the service, per-round node/document/character/time budgets, visited-node/document deduplication, and cancellation or stale-result fencing on session changes.
- Require a structured result containing at least sufficiency, rounds used, searched types, visited paths, evidence document IDs, missing requirements, and degraded/error state. Failure or invalid LLM output must not become an implicit success.
- Add acceptance cases for success in each round, insufficient-after-limit, no-fulltext-on-round-1-success, multi-type mapping, budget exhaustion, and invalid/timeout LLM output.

### Line Number Drift
After a patch inserts lines (P2a adds 45 lines), all subsequent patches' hardcoded line numbers are wrong.
**Fix:** Use `search_files` to locate the actual text position before each patch that follows an insert.
Or target by unique text content rather than line number.

### old_string Must Come from read_file
Never invent `old_string` from memory. The patch tool uses fuzzy matching but exact whitespace/indentation
still matters. Always `read_file` the target section and copy-paste the exact text.

### Verification Must Be Runnable
Verification commands must operate on the **patched** state of the file. They can't reference lines
that were deleted by the same patch. Use `read_file` or `search_files` — both are read-only and fast.

### Execution-Plan Contracts Must Be Internally Consistent
When a Ralph artifact hands work to Ultrawork, make the plan executable without making the planner execute it:

- Keep authoring evidence separate from future execution evidence. In planning-only mode, write the exact future command and its required capture/validation contract; do not claim the command was run unless the loop explicitly permits it.
- If an evaluator or tool choice matters, specify a deterministic precedence order, each availability command, the exact execution command, the fallback boundary, and stdout/stderr/exit-code expectations. “Use a preferred evaluator” is not executable.
- Align one-shot operations with manifest retries. If the plan says an evaluation, migration, or external action runs once only, its manifest step must use `max_attempts: 1` and explicitly prohibit rerun, substitution, or retry after an attempted invocation. Higher retry limits are valid only for non-repeating review or discovery work and must not re-trigger the one-shot action.
- Include an explicit `## rollback` section. For a non-mutating plan, state that rollback is not required because modifications are prohibited; define the response to an unintended mutation: stop, preserve evidence of the target/command/change, report a blocker, and do not attempt cleanup or restoration without separate authorization.
- When a handoff manifest is required, emit exactly one `<!-- ULTRAWORK_MANIFEST ... -->` block. Verify one opening marker, one closing marker, valid step dependency order, and retry limits consistent with the prose tasks.

### Don't Over-Update
An existing plan that's been iteratively refined may be high quality. Focus on gap-filling,
not rewriting. If a section has no gaps, don't touch it.

## When to Use

- Ralph planning mode with objective containing "更新计划文件" or "update plan file"
- Task: "prepare to update plan X to reflect changes in Y"
- Any Ralph loop where the deliverable modifies an existing document
