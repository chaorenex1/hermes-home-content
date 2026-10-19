---
name: prompt-contract-maintenance
description: "Use when editing multi-pass LLM prompt contracts."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [prompts, llm-pipelines, structured-output, schema, prompt-audit]
    related_skills: [test-driven-development, systematic-debugging, prompt-engineer]
---

# Prompt Contract Maintenance

In a multi-pass LLM pipeline a prompt is an API: the system prompt states a shape, the parser
enforces a shape, and the store persists it. Changing one without the others ships a model reply
nothing accepts, or a rule the guard makes unreachable.

## When to use

- Adding or reworking sections of a layer / reviewer / adviser prompt.
- Unifying vocabulary across passes (entity or marker types, advice targets, severity levels).
- Changing an output contract: allowing empty values, renaming keys, new count or length caps.
- Auditing why a prompt's stated rule never takes effect in stored artifacts.
- Explaining another project's prompt architecture (usually: file:line map + structure read-out,
  verbatim text only on request). For a shipped agent whose prompts travel inside a binary or an
  installed package, follow `references/foreign-prompt-architecture.md` — version-pinned extraction,
  provenance hash, composition map before any text dump.

## Workflow

1. **Inventory before editing.** Grep the prompt constants, then for each one find: the call that
   passes it as the system message, the user-message builder that supplies its input blocks, the
   parse/normalize function that consumes the reply, and the store writer. Write the
   prompt → parser → store triple per pass. A section cannot be judged without its consumer.

2. **Section skeleton**, in this order:
   - `ROLE` — what the pass owns, plus an explicit "what you are not" line (not the assistant, not
     the implementer, not a second writer).
   - `INPUTS` + `TRUST ORDER` — the blocks that actually arrive, ranked.
   - `WORKFLOW` — numbered steps naming those blocks in the order the builder emits them.
   - JSON shape, `OUTPUT CONTRACT`, per-topic rules, then `DEFINITIONS` last.
   - Definitions go last so the body reads top-down while the reference block stays self-contained
     even though its text is generated once and shared.

3. **Single-source every shared vocabulary.** Put the table in the lightest shared module (prompt
   formatting module, not the store), expose `glossary()` / `section()` string builders, and
   compose every prompt that mentions the vocabulary from them. Four hand-written copies of the
   same five type definitions drift within one release. Attach the generated sections to the
   shared contract constant itself when several prompts compose it (cold start, audit, reconcile,
   retry): a section appended only in the primary system-prompt composer silently disappears
   from every variant.

4. **Compose, never f-string a prompt that embeds JSON.** Braces in the example object collide with
   replacement fields, and doubling every brace is silent-corruption risk. Attach generated
   sections by concatenation: `"""static body""" + "\n\n" + marker_section()`. The same rule kills
   placeholder-then-`replace()` schemes.

5. **Audit prompt ↔ parser symmetry** before declaring the edit done — see
   `references/prompt-audit-checklist.md` for the check matrix and commands. The recurring misses:
   a count or character limit stated in the prompt but enforced wider (or narrower) by the parser;
   a "you are given X" claim the builder does not supply; a section order claim that does not
   match the built message.

6. **Move behaviour end-to-end when the rule is semantic.** A rule like "an empty listed field
   clears the card" needs four edits in one change: prompt text, parser/guard, store write, and
   README. Keep the neighbouring negative path (placeholder or unlisted empty = not a correction)
   and test both.

7. **Verify with the repo's own suite.** Prove pre-existing failures with a clean tree instead of
   guessing (`git worktree add <dir> HEAD`), and treat full-suite-only failures as flakes after one
   isolated rerun. Report the failing test name, its real cause, and whether it predates the change.

## Pitfalls

- **Section text contradicts the builder.** A ROLE line claiming "the window is the only evidence"
  while the builder also supplies a first-message anchor and operator files teaches the model to
  ignore evidence you feed it. Read the builder before writing any inputs/trust claim.
- **The guard makes the new rule dead on arrival.** A review that rejects empty cards can never
  clear one; a parser that drops `[unknown]` items cannot accept a placeholder rule. Change guard
  and prompt together and keep both branches tested.
- **Placeholders leak into artifacts.** `[unknown]`-style fillers are only safe when write-back
  filters them; check the store writer before adding such a rule, and never let a placeholder
  reach a persisted card.
- **Test builders swallow empty values.** Helpers written as `value or default` cannot express
  `[]`; switch to `value if value is not None else default` before writing an empty-state test.
- **Normalization erases empty vs missing.** A `_json_items`/`_string_list` helper returns `[]`
  for an omitted key, a malformed value and an explicit empty list, so an "`[]` clears this
  field" rule cannot be read after normalization. Decide clears from the raw reply object
  (`payload.get(field) == []`), require the field in the change list, and keep a non-list value
  from counting as a clear.
- **Snapshot vs live row.** Revision/audit tables usually store the pre-change snapshot while the
  live row carries the change. Assert the old value on the snapshot and the new value on the live
  row; asserting both on the same row fails for the wrong reason.
- **Prompt growth is real cost.** A generated glossary section costs roughly 400-900 characters per
  prompt per run; prefer one shared table over per-prompt prose and state the delta when reporting.
- **Duplicated vocabulary already in flight.** Before adding a definition, search the pipeline for
  an existing one (store constants, tool descriptions, provider system block). Extend that source
  instead of creating a second.

## Reporting

Lead with the file:line map of what changed (prompt constant, parser, store, tests) and the
structural findings; keep verbatim prompt text out of the summary unless requested. When the
request *is* "show me the system prompt", the reply carries the full text and the composition map;
a file path is a supplement, never the answer. Separate
"fixed" from "found but needs a decision" — contract asymmetries are often intentional.
