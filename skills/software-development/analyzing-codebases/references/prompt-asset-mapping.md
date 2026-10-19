# Mapping Prompt Assets in a Codebase

Task class: "show me the system prompt of X", "where does the reviewer prompt live", "how does this project assemble its prompt". The deliverable is a navigable map — template file, section line numbers, renderer, assembly order, optional fragments — not a pasted template.

## 1. Establish the prompt root and tiers

List the prompt directory with file sizes. Typical tiering in a coding-agent/plugin repo:

- `<prompts>/system/system-prompt.md` (largest) — the base agent prompt.
- `<prompts>/<role>/system.md` — reviewer/advisor/judge roles.
- `<prompts>/system/personalities/*.md`, `<prompts>/system/project-prompt.md`, `<prompts>/system/custom-system-prompt.md` — overlays and tails.
- `<prompts>/tools/*.md`, `<prompts>/internal-urls/*.md` — per-tool and per-scheme snippets pulled in conditionally.

Sizes do the sorting: the base prompt is 10–15 KB, role prompts 2–8 KB, fragments 100–900 bytes.

## 2. Get the outline from the file itself

```bash
grep -n '^§ \|^# \|<' <prompt>.md
```

Section markers in these templates are usually `§ Name` (top-level), `# Name` (sub-section), and XML-ish blocks (`<contract>`, `<completeness>`, `<critical>`). The result is the line-numbered skeleton — the map body.

## 3. Find the renderer, the data, and the conditionals

```bash
grep -n 'import .* from ".*prompts/' <module>.ts      # which module owns the template
grep -n 'prompt.render(\|prompt.compile(' <module>.ts # where it is rendered
```

Read the `data` object built just before the render call. Every key is a switch:

- `{{#if skills.length}}`, `{{#has tools "lsp"}}`, `{{#each rules}}` — presence of a tool/skill changes the prompt text.
- `{{toolRefs.write}}`, `{{max_notes_per_update}}` — names and numbers injected at render time.
- Handlebars-style helpers run through a `prompt.render(template, data)` helper plus precompiled `prompt.compile(...)` for statically-bound fragments.

Consequence to report: two sessions with different tool sets receive different prompt text, so "the system prompt" is a family, not a single string.

## 4. Record assembly order

Look for the array the renderer fills:

```python
systemPrompt = [rendered]
for prelude in evalPreludes: systemPrompt.push(prelude.guidance)
systemPrompt.push(projectPrompt)   # project-context tail
```

Three things are worth naming explicitly:

1. Order — base → mode/prelude blocks → project/context tail.
2. Cache intent — dynamic, directory-scoped content is placed last on purpose so the static prefix stays cacheable (Anthropic-style head cache breakpoint). Say this, because it explains why the file looks the way it does.
3. Tail block provenance — which template produced it (`project-prompt.md` → `<project-context>` with context files, workspace tree, active repo).

## 5. Trace optional fragments to their builder

For each fragment basename (`memory-context.md`, `context-files.md`, `WATCHDOG.md`, `boundary-guidance.md`, personalities):

```bash
gh api -X GET search/code -f q='repo:<owner>/<repo> "memory-context.md"' --jq '.items[].path'
```

The hit is a builder like `watchdog.ts` that renders the fragment with its own variables. Typical finding: the role prompt (`.md`) is short, and half of what the reviewer actually sees is appended by a builder from user-editable files discovered by walking up the tree.

Also capture:

- Which templates are user-overridable and how discovery works (`AGENTS.md`, `WATCHDOG.md`, `<dir>/.omp/<file>`, agent-dir configs), and the precedence order (user-level first, ancestor → leaf last, leaf most prominent).
- Trust framing lines at the top of each template (RFC 2119 keyword definitions, "XML tags are system-authored") — these are the same mechanism as labeled-data-block hardening and are worth quoting as one line each.

## 6. Deliverable shape

Per role, one block:

```
role prompt file  path/to/prompts/<role>/system.md (N lines)
  1-3      conventions / trust framing
  5-11     role definition and mandate
  13-17    <workflow> — inputs, tool grant, budget per note
  ...
assembly  module.ts:1312-1319 — [role prompt] + context + memory + watchdog + shared + per-instance instructions
fragments prompts/<role>/{context-files,memory-context}.md, discovered <FILE>.md blocks
```

Then one short paragraph on what the split buys: static role contract in the template, project/user specifics appended by builders, dynamic content last for caching.

## Pitfalls

- Do not equate the prompt directory with the prompt. The role file is typically the smallest part of what the model receives.
- Do not paste whole templates when the ask is "where is it". Line anchors plus section names are what let the user navigate; verbatim dumps hide the structure.
- Do not report line numbers without the branch/commit when the files came from a remote fetch.
- Conditional sections mean a "complete" prompt cannot be quoted from the file alone — state which switches gate the missing parts.
