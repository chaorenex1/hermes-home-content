# Directory-Summary Navigation Prompt Audit

Use this reference when a memory system summarizes accepted documents under a type directory for later retrieval.

## Core semantic decision

Decide whether the summary represents:

- **Current-state snapshot:** regenerate from all currently accepted descendants after any change. This is rebuildable and usually matches directory-summary projections.
- **Change delta:** describe what this refresh added, patched, revoked, or deleted. This is only supportable when the input includes change operations, before/after state, or a previous summary.

Never ask a model to report “this update changed…” when its input contains only current titles and bodies. Reword the contract as “regenerate the navigation view after an update,” or extend the runtime payload.

## Three independent integration layers

1. **Stored artifact** — the expected `summary.md` exists under the profile-local prompt directory.
2. **Loadability** — the template type is present in allowlists/initializers and can be loaded and versioned.
3. **Runtime enforcement** — production prompt construction actually reads the file rather than a hardcoded instruction.

Report `stored`, `loaded`, and `enforced` separately. A file on disk is not runtime integration.

## Minimum runtime payload for navigation

A useful directory-navigation summary needs more than document title and content:

- target directory path;
- memory type;
- each accepted document's logical path;
- title and canonical current content;
- optional version/update time when needed for staleness;
- for true delta semantics: action plus before/after or previous-summary context.

Without logical paths, the model can produce topic aggregation but not reliable drill-down routing.

## Content contract versus transport contract

Keep the editable template focused on summary semantics:

- accepted-only grounding;
- directory/type boundary;
- topic clustering;
- state, conflicts, qualifiers, and replacement relationships;
- document navigation;
- retrieval terms;
- no invented facts or full-body copying.

Keep transport mechanics in the outer runtime prompt and parser:

- exact JSON keys such as `summary` and `detailed_summary`;
- character limits;
- input serialization;
- malformed/duplicate-key rejection;
- fail-closed behavior.

## Two-layer output

- `summary`: short routing synopsis answering what knowledge is present and when this directory is worth searching.
- `detailed_summary`: structured navigation index containing topic → key facts/state → document paths → useful retrieval terms.

The detailed layer should support FTS or hybrid retrieval; generic prose such as “this directory contains user memories” has little index value.

## Memory-type lenses

- `entities`: names, kinds, durable attributes, relationships.
- `events`: event, occurrence time, result, impact.
- `experiences`: problem, adopted solution, verification, reusable lesson.
- `tools`: tool, task, workflow, invocation, pitfalls.
- `trajectories`: requirement, implementation, verification, outcome/blocker.
- `projects`: purpose, architecture, current state, decisions, open work.
- `identity`: stable identity, work roles, sustained focus.
- `preference`: communication/execution/verification/risk defaults with scope.

Do not flatten every directory into one generic summarization style.

## Evidence checklist

Inspect and cite:

1. actual prompt-directory contents;
2. template type allowlist and initializer;
3. production prompt builder;
4. runtime payload fields;
5. accepted/current visibility query;
6. refresh granularity and ancestor propagation;
7. output parser and configured limits;
8. retrieval fields and downstream search behavior;
9. focused tests proving custom template activation and navigation quality.

## Common failure modes

- A `summary.md` exists but the allowlist rejects it.
- The store loads it, but production still uses a hardcoded prompt.
- The prompt says “this update” while receiving only a current snapshot.
- The model receives no target path/type and cannot apply the correct semantic lens.
- The model receives no document paths and cannot create drill-down navigation.
- Tests verify JSON shape and length but not semantic routing quality.
- Planned or stale facts are presented as current; conflicts are silently resolved.
