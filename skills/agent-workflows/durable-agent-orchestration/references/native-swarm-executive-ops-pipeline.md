# Native Swarm Executive Decomposition and Ops Pipeline

Use this reference when a Native Kanban Swarm should accept a goal, optionally bind an external plan, let an executive role decompose work, pair each implementation route with independent QA, run cleanup/documentation stages, and deliver one verified final candidate.

## Canonical lifecycle

```text
intake and immutable source binding
→ executive planning manifest
→ validate/freeze route DAG and profile pairs
→ for each dependency-ready route: Dev → paired QA → executive semantic Judge
→ integrate accepted route commits into the run-owned integration branch
→ scoped Ops cleanup → independent QA → executive Judge
→ conditional documentation drift audit/update → independent QA → executive Judge
→ freeze final integration SHA
→ independent Global QA → executive Global Judge
→ read-only executive synthesis → root completion and creator notification
```

Only `accepted` routes release dependencies. Dependency-ready routes run in parallel; each matching QA starts as soon as its Dev evidence is durably committed, without waiting for unrelated Dev routes.

## Entry modes and profile resolution

Preserve two Native entry modes:

- **Manual topology:** repeated Worker declarations compile directly into frozen routes.
- **Executive auto-topology:** when no Workers are declared, create only the active root and one executive planning attempt. The executive returns a strict route manifest; the controller validates and freezes it before creating Dev cards.

Resolve omitted verifier, synthesizer, and executive profiles from configured Swarm topology. Treat `CEO`/`CTO` as logical executive labels mapped to the configured physical profile; never hard-code one profile name.

Code delivery requires a trusted Git repository. Resolve it from an explicit repository argument or validated board project root, require a clean tree, and freeze the base SHA before worktrees. Do not promise commits from scratch/general runs.

## Optional external plan binding

A phrase such as “the plan is at X” is not an execution contract. Normalize it into an explicit Native plan binding before dispatch, preferably through `--plan-file`, and persist resolved path, SHA-256, complete frozen content, and stable source refs. Executive, Dev, QA, and Judge receive the frozen content or a complete digest-bound packet—not only a path or excerpt. Later edits must not silently alter the run. Every generated route cites the plan sections it implements, and coverage is validated before dispatch. This remains `source_kind=native_swarm`; do not upgrade it to Ralph merely because a plan exists.

## Executive planning manifest

The executive proposes; the deterministic controller owns task creation, dependency mutation, retries, integration, and completion. Require a schema containing, per route: stable key, title, dependencies, Dev/QA profiles, file scope, source refs, acceptance criteria, evidence requirements, and bounded attempts.

Validate unique IDs, known acyclic dependencies, complete source coverage, non-empty criteria/evidence, existing profiles, Dev/QA independence, compatible file ownership, and bounded retries. Persist route-level Dev/QA mappings. If routes outnumber available pairs, schedule in waves rather than assigning one global verifier to every route.

## Dev, QA, and executive Judge

Dev works inside its assigned scope/worktree and returns a clean immutable candidate commit plus raw command/artifact evidence.

The paired QA independently verifies that exact SHA against:

1. targeted tests and relevant regressions;
2. applicable project contracts (`AGENTS.md`, `CLAUDE.md`, then config/tests/code conventions if explicit contracts are absent);
3. route/global goal criteria;
4. complete frozen plan sections when a plan is bound.

QA reports `pass|rework|blocked` with criterion IDs and raw evidence; it must not implement the reviewed code. The executive Judge receives frozen criteria plus raw Dev/QA packets. A pass requires cited evidence for every criterion. Rework creates a fresh bounded Dev attempt carrying exact failed criteria, preserved passing regressions, and a materially changed strategy. The executive model never directly edits sibling task state; the controller applies validated decisions transactionally.

## Ops cleanup

Treat cleanup as a mutating implementation route over the integrated candidate:

```text
integrated implementation candidate
→ cleanup scan/proposal
→ executive scope authorization
→ cleanup commit
→ independent cleanup QA
→ executive cleanup Judge
→ integration
```

Deletion requires evidence. Do not classify dynamically loaded entries, plugin registrations, migrations, compatibility code, external contracts, or uniquely valuable tests as dead solely because static references are absent. Deleting a test requires proof that requirement coverage is preserved and before/after verification evidence. If no safe cleanup exists, produce a structured no-op instead of forcing a diff.

## Documentation stage

During active implementation, documentation/governance observers are read-only; changing `AGENTS.md` or `CLAUDE.md` mid-run changes the contract seen by later Workers.

An elapsed-time threshold triggers a **documentation drift audit**, not unconditional edits. Also audit for public API, CLI, config schema, architecture, or user-visible behavior changes. Update only existing relevant files unless the frozen plan requires new documentation. Typical scope: `AGENTS.md`, `CLAUDE.md`, `README*`, `.gitignore`, and `docs/**`. Any edit is a candidate mutation and needs evidence plus independent review.

## Final commit and QA ordering

All candidate-mutating work precedes final Global QA:

```text
accepted route commits
→ cleanup/docs commits
→ deterministic integration or squash commit
→ freeze final SHA
→ Global QA on that SHA
→ Global Judge
→ read-only synthesis
```

The executive may author the commit message or authorize strategy, but the controller creates/freezes the commit before Global QA. If any Ops/docs stage changes the candidate after Global QA, mark that review superseded and require Delta Global QA. A post-QA metadata-only commit is acceptable only when a deterministic tree-hash check proves the tested tree is unchanged.

## Completion and required regressions

Complete the root only after every route and Ops stage is accepted, Global QA/Judge pass on the final SHA, and synthesis returns a substantive structured handoff. Notify the creator with final SHA, tests, changed files, cleanup/docs outcomes, risks, and lookup IDs.

Regression coverage must prove: goal-only planning creates no Dev card before manifest validation; manual mode remains compatible; plan bytes/digest are frozen; independent routes and matching QA pairs progress concurrently; invalid DAG/profile/scope/source coverage fails before dispatch; unsafe cleanup deletion fails; docs remain read-only during implementation; post-Global-QA mutation forces Delta QA; executive naming resolves through config; and completion delivery includes synthesis plus final SHA.
