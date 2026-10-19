# Foreign prompt architecture

Use when the request is to explain, compare or reproduce the system prompt of another shipped
agent/product (coding CLIs, IDE agents, assistant apps) rather than a prompt in the repo you are
editing. The deliverable is the prompt family, where each piece is attached, and the verbatim text
when asked — not a plan to obtain it.

## 1. Pin the version before reading anything

- `<tool> --version` and the install path (`which <tool>`, `~/.<tool>`, `%LOCALAPPDATA%`).
- The shipped artifact is usually a single-file binary plus an npm/distribution package with the
  same version. Resolve the package name from the binary's layout (top-level `packages/<name>`, a
  `@scope/name` import, or the docs) and confirm the version matches the binary's.

## 2. Extract from the package, not the binary

```bash
npm pack <scope>/<pkg>@<exact-version>       # tarball lands in the cwd
npm view <scope>/<pkg> version               # cross-check the registry head
```

The published tarball normally carries `package/src/prompts/**` (or `dist/prompts/**`) as verbatim
`.md`/`.ts` assets, including the Handlebars templates. A compiled single-file binary (Bun/SEA/
pkg) generally does not expose prompt bodies to `grep -a`: zero hits for a distinctive sentence from
a prompt you already hold is expected, not evidence the prompt is absent. Extract from the tarball
and treat the binary only as the thing that consumes the render.

## 3. Prove provenance

- Keep the extracted tree in scratch under the version (`.../omp-18.12.1/src/prompts/`).
- Compare every file against any earlier copy by `sha256` + size; equal hashes mean the copies are
  the same release, so an earlier session's extraction can be reused instead of redone.
- State version and hash prefix in the answer so the reader can verify a pasted dump.

## 4. Inventory the prompt family before reading

"The system prompt" is almost always several files:

| Surface | Typical file | Role |
| --- | --- | --- |
| Main instruction template | `prompts/system/system-prompt.md` | block 0 of the provider prompt |
| Alternate template | `prompts/system/custom-system-prompt.md` | used when the user replaces the prompt |
| Always-appended context footer | `prompts/system/project-prompt.md` | workstation, AGENTS.md files, tree, final `<critical>` |
| Subagent variant | `prompts/system/subagent-system-prompt.md` | separate agent, separate rules |
| Personality presets | `prompts/system/personalities/*.md` | injected into the template's personality slot |
| Secondary subsystems | `prompts/advisor/*.md` | watchdog/adviser: own system, injected blocks, tool description, delivery prefix |

List the directory and sizes first; the size table already tells you which files are whole prompts
and which are one-paragraph injected blocks.

## 5. Build the composition map from imports

Grep the package `src` for each prompt path. The importer tells you the role:

- `import x from "../prompts/advisor/system.md"` in the session/advisor module → that is the
  subsystem's system message.
- A template that wraps `{{#each contextFiles}}` or `{{name}}` → an injected block, not a prompt.
- A one-liner imported next to a tool definition → the tool's description.
- A header string prepended to a batch → delivery framing (e.g. stale reviews arriving after work).

Then read the template's conditionals: `{{#has tools "..."}}`, `{{#if subagent}}`, `{{#if
personality}}`, delegation-bias branches. Those are the axes along which the real prompt varies;
name them so "the system prompt" is understood as a render, and never present the raw template as
the text the model saw.

## 6. Deliver

- Composition map first (one line per surface: file → where it attaches → what it constrains),
  then the full verbatim text when the user asked for the prompt.
- Give the on-disk path and hash of what you pasted. A path alone is a supplement, not the answer.
- Keep design commentary short and tied to the text: structure, severity tiers, explicit
  prohibitions, config axes. Do not editorialize per line.

## Pitfalls

- **Short tokens match inside words.** A search for `omp` hits `compress`, `prompt`, `complete`.
  Anchor the pattern (`\bomp\b`) or you will report noise as hits and conclude the term is absent.
- **`read_file` truncates long prompt lines** with `[truncated]`, and `execute_code` stdout is
  JSON-serialized, so backslashes arrive doubled. Reproduce text from a hash-verified file, not
  from a truncated read — and un-double escapes (`` \\textcolor `` on screen is `\textcolor` in the
  file) before pasting.
- **Terminal truncation eats the list that mattered.** File listings and size tables beyond a few
  KB come back head+tail; use `execute_code` with `tarfile`/`os` to enumerate and hash instead of
  chaining `tar -tzf | grep`.
- **Don't skip the docs shipped in the package.** Files like `docs/system-prompt-customization.md`
  state the block order, precedence rules and provider cache breakpoints — the structural half of
  the answer the user usually wants.
- **A previous session may have extracted the same assets.** Search session history and scratch
  before re-extracting; hash-diff the copies against the pinned tarball to decide whether reuse is
  safe. An extraction without delivery is still worth reusing.
