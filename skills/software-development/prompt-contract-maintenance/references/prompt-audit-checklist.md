# Prompt ↔ parser audit checklist

Run this before declaring a prompt change complete. Each row is a claim in the prompt and the
place it must be true; drift on any row is a contract bug invisible to the model call.

| Prompt claim | Where it must be enforced | Symptom when it drifts |
|---|---|---|
| Key set / JSON shape | required-keys check or schema in the parser | whole reply rejected, or extra keys silently ignored |
| Item count per field | `_MAX_ITEMS`-style cap and truncation | prompt says 0-6, parser allows 8 → longer lists than stated |
| Character limits | per-field truncation constants | prompt stricter than parser is safe; the reverse truncates silently |
| Enum values (severity, target) | normalize step mapping unknown → default | both producers must share one table, else the agent sees two vocabularies |
| "You are given X" blocks | the user-message builder | model reasons over evidence it never receives, or ignores evidence it does |
| Read/trust order | order of blocks in the built message | prompt's step 1 contradicts the actual sequence |
| Empty vs placeholder semantics | the write-back filter | placeholder text persists into a card; "clear" becomes unreachable |
| Explicit-empty clear | raw reply list before normalization + change-list gate | an omitted or malformed value silently clears a card |
| Generated sections (ROLE, definitions) | every composed variant, not only the primary prompt | cold-start/audit/retry variants run without the shared vocabulary |
| Defaults for missing fields | parser default branch | omitted value silently becomes a different target/severity |

## Commands that make the audit cheap

```bash
# prompt constants and where they are used
grep -n "SYSTEM_PROMPT\|_BRIEF\|_CONTRACT" path/to/*.py
grep -n "def parse_\|def _parse\|def _json_items\|def _advices" path/to/*.py

# limits stated in prompts vs enforced in code
grep -n "characters\|0-[0-9] items\|1-[0-9] strings" path/to/*.py
grep -n "_MAX_" path/to/*.py
```

For a remote repository, read prompts without cloning (large repos are often gigabytes of test
data):

```bash
gh api "repos/OWNER/REPO/git/trees/main?recursive=1" > tree.json   # filter paths with python/grep
gh api "repos/OWNER/REPO/contents/PATH" -H "Accept: application/vnd.github.raw" > file.md
gh api -X GET search/code -f q='repo:OWNER/REPO "prompt-name.md"' --jq '.items[].path'
```

Then read the saved files; long trees and diffs do not belong in a terminal capture.

After composing prompts from shared tables, print the section headings of every variant instead of
reading one prompt:

```bash
python - <<'PY'
import importlib
mod = importlib.import_module("plugin.package.prompts")   # the module holding the constants
for name in dir(mod):
    if name.endswith(("_SYSTEM_PROMPT", "_BRIEF", "_CONTRACT")) and name.isupper():
        text = getattr(mod, name)
        print(name, len(text), [l for l in text.splitlines()
                                if l.strip() in ("ROLE", "WORKFLOW", "INPUTS", "TRUST ORDER")])
PY
```

Every variant must show the same skeleton; a missing heading is a composer that attached the
generated sections to the wrong constant.

## Empty-value decision table

| Situation | Parser | Prompt |
|---|---|---|
| Nothing to say about a field | keep current content, do not list the field | say so explicitly |
| Evidence proves the field should be empty | accept `[]` only when the field is listed as changed | "`[]` empties the card; it must be listed" |
| Placeholder (`[unknown] ...`) | drop before write-back; all-placeholder = no correction | "a placeholder is not a correction" |
| Cumulative inventory (markers, summaries) | merge only, never clear | "this field is merged, never emptied" |

Clearing must be an explicit, narrow permission: gated on the change list, limited to fields whose
loss does not destroy evidence, and refused (whole reply) when it arrives outside that gate.
