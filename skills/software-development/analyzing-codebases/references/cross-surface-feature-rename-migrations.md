# Cross-Surface Feature Rename Migrations

Use this reference after the main codebase-analysis skill identifies a rename that crosses public APIs, runtime state, or deployment boundaries.

## 1. Establish the semantic verdict

Write the current behavior as a state machine before discussing names:

```text
entry → classification/intake → persisted state → user/reviewer interaction
→ approved artifact → downstream handoff → terminal/archive state
```

Then classify the request:

- **Rebrand:** behavior remains unchanged; only vocabulary changes.
- **Semantic redesign:** the proposed name promises behavior the current system does not perform.
- **Both:** rename plus a deliberate state-machine change.

Do not hide a semantic mismatch inside a mechanical rename. A name such as “interview” normally implies elicitation and user-question states; a planning loop that edits and approves an artifact is not automatically an interview.

## 2. Canonical occurrence inventory

Count canonical source separately from mirrors and history.

| Scope | Include | Report separately |
|---|---|---|
| Core source | tracked runtime modules and registries | linked worktrees, vendored copies |
| Tests | active focused/integration tests | snapshots generated from source |
| Clients | Desktop/TUI/web/gateway protocol consumers | built bundles |
| Plugins | editable plugin source | installed deployed copy |
| Skills/docs | active skills and current docs | archives, caches, historical plans |
| Persistence | live keys/tables/columns/artifacts | immutable audit/history vocabulary |

For every count, state exclusions. A raw recursive count that includes worktrees and installed mirrors exaggerates the implementation cone and invites duplicate edits.

## 3. Naming-layer matrix

Fill this before proposing edits:

| Layer | Current token | New canonical token | Compatibility policy |
|---|---|---|---|
| Product label | Human-facing name | New label | update immediately |
| Slash/CLI | `/old-name` | `/new-name` | temporary alias is cheap |
| Model tools | `old_name_execute` | `new_name_execute` | bounded alias or fresh-session cutover |
| Module/types | `old_name.py`, `OldState` | new module/type | optional import shim |
| Protocol | event names, `kind`, RPC mode | new tokens | clients accept both; server emits one |
| Persistence | key prefixes, tables, columns | versioned or neutral names | migrate transactionally |
| IDs/artifacts | plan/run IDs, filenames, digests | usually preserve old values | readers accept legacy IDs |
| Downstream handoff | `old_plan_id`, source kind | neutral `source_plan_id` where possible | backfill before removal |
| Plugin API | commands/tools/hooks | neutral or new names | deploy source then verify installed copy |
| History | audit events, legacy DB names | retain historical vocabulary | never rewrite provenance |

Prefer neutral names such as `source_plan_id`, `approved_plan`, or `source_kind` at execution boundaries. Brand-specific names make every future rename a schema migration.

## 4. Live-state read-only probe

Before designing migration, collect aggregate evidence without reading private bodies:

- legacy and new state-key prefix counts;
- template/history table row counts;
- downstream rows carrying the old source ID;
- active/nonterminal rows;
- immutable artifact counts and roots;
- old and new column presence;
- legacy database presence;
- profile and project scope of each store.

Existing IDs are durable references, not display strings. Preserve old IDs unless every foreign reference, audit record, path, and resume selector is migrated atomically.

## 5. Compatibility decisions

### Slash and CLI aliases

Usually safe for a deprecation window. They do not expand the model tool schema. Help output should show only the new canonical command.

### Model-tool names

Tool names are model-visible protocol. Advertising old and new tools simultaneously increases schema tokens on every model request and can reduce prompt-cache stability. Choose explicitly among:

1. fresh-session/restart cutover with only new names;
2. one bounded release with both schemas;
3. old schema retained while only user-facing branding changes.

Never hot-swap a long-lived conversation's toolset.

### Events and interactive request kinds

During staggered backend/client upgrades, clients may accept both names. The backend should emit only one canonical event; dual emission can create duplicate notifications, review cards, and transcript rows.

### Persistence

Use one authoritative writer. Avoid indefinite dual writes to old and new key prefixes because they can create two owners for one plan. Prefer a stopped-service transaction or a reader-first migration with an explicit atomic ownership transfer.

## 6. Migration sequence

1. Freeze the naming and semantic contract.
2. Record dirty-worktree and live-store baselines.
3. Add characterization tests for current state, resume, search, review, and downstream handoff.
4. Add new readers/aliases and test legacy data.
5. Rename canonical core modules, types, tools, and command labels.
6. Update Gateway/TUI/Desktop protocol consumers with old-token acceptance.
7. Introduce neutral downstream fields and backfill old source references.
8. Stop live writers; back up stores; migrate keys/tables/columns with exact expected counts.
9. Update editable plugin source; dry-run deployment; deploy; verify installed hash parity.
10. Regenerate package metadata and update active docs/skills.
11. Restart at the declared session/tool-schema boundary.
12. Verify old plans resume, new plans use new vocabulary, approved handoff works, and no duplicate lifecycle UI appears.

## 7. Verification gates

- Old persisted state remains discoverable and resumes once.
- New state writes only the canonical prefix/field.
- Plan/run IDs and digests remain stable unless the migration explicitly versions them.
- CLI, Gateway, TUI, and Desktop agree on the canonical command and lifecycle states.
- Old client tokens remain accepted for the documented compatibility window.
- Tool registry exposes the intended names without accidental permanent duplication.
- Downstream execution accepts both migrated legacy sources and new sources.
- Plugin source and installed copy match after deployment.
- Full-text search finds the old name only in compatibility, migration, history, and deprecation material.
- Final Git status contains only the intended worktree changes.

## 8. Unsafe patterns

- Global search-and-replace across worktrees, caches, plans, databases, and generated metadata.
- Renaming persisted IDs because they “look like branding.”
- Giving a downstream execution engine the new brand-specific field instead of neutralizing the boundary.
- Dual-emitting old and new lifecycle events.
- Advertising duplicate model tools indefinitely.
- Editing the installed plugin while leaving its source checkout stale.
- Rewriting historical audit text or legacy database filenames.
- Claiming a rename is cosmetic without inspecting live state and independent clients.
