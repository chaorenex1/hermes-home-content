# Python Dead-Code Cleanup Audit

Use this reference when a working Python implementation has recently been replaced or routed through a new state machine and the user asks for dead-code cleanup.

## Evidence sequence

1. Establish scope with `git status --short`. If tracked working-tree code is clean, inspect the last relevant commit rather than unrelated pre-existing dirty files.
2. Enumerate definitions in changed production modules with `ast`. Count both `Name` loads and `Attribute` names across tracked source and tests.
3. Confirm every candidate with an exact repository search and `git blame`/history. Exclude generated or ignored mirrors such as `build/`, `dist/`, egg-info, caches, worktrees, and copied install trees; otherwise one real definition appears falsely live twice.
4. Trace the removal closure. A dead entrypoint commonly leaves orphaned helpers, imports, constants, dataclass fields, state-map keys, and parameters. Remove the whole proven closure, not only the top-level function.
5. Re-run the scan and require every removed private symbol to have zero definitions and zero references.

## Risk classification

SAFE:
- Private function with no call sites.
- Helper used only by that dead function.
- Import, constant, state key, field, or parameter with no runtime reads.

CAREFUL:
- Configuration key validated and persisted but not currently read.
- Performance waste that is still reachable, such as filtering after file reads.
- Internal aliases that may be imported outside the repository.

RISKY:
- Public compatibility aliases.
- Persisted action names or state-machine vocabulary needed to reload historical runs.
- CLI/API routes that are architecturally obsolete but still reachable.

Do not call reachable legacy behavior dead code. Report it as an architecture migration or bugfix task instead.

## Verification interpreter check

Before a full suite, verify that the selected interpreter provides:

- the test runner;
- host/application imports used by fixtures;
- `pip` when packaging tests spawn `sys.executable -m pip`;
- the declared build backend when tests use `--no-build-isolation`.

Use one project-authoritative interpreter that satisfies all four. If the environment intentionally separates these tools, inject a temporary offline dependency target rather than modifying project dependencies merely to run verification. Treat missing test-environment components as environment evidence, not a code regression.

## Final gates

- syntax/compile check;
- focused tests for touched modules;
- full suite under the verified interpreter;
- `git diff --check`;
- final symbol scan;
- explicit confirmation that unrelated dirty files were untouched.

If the audit discovers a correctness issue (for example, a canonical path that cannot match its type root), record it separately. Do not fold a behavioral fix into a dead-code cleanup pass unless the user expands scope.