# Architecture-Replacement Cleanup Audit

Use this reference after a commit replaces a retrieval, orchestration, storage, or protocol architecture. The purpose is to find old paths that still exist beside the new route, including dead implementations, reachable alternate surfaces, response-shape adapters, compatibility branches, stale configuration, and registry vocabulary.

## 1. Establish the new canonical route

Trace the new entrypoint end to end:

```text
public surface -> input normalization -> canonical engine -> persisted controller -> stage execution -> response -> downstream serializer
```

Do this separately for every production surface: model tool, CLI, automatic/background worker, API, smoke scripts, and direct library calls. A new public tool does not prove that the CLI or background recall path adopted the same engine.

## 2. Fence removals with repository-wide reachability

For every suspected obsolete symbol:

1. Search all tracked source, tests, scripts, docs, and package exports—not only the changed file.
2. Distinguish definition/self-reference from external callers.
3. Check dynamic access (`getattr`, plugin registries, import aliases, command maps) before calling a symbol dead.
4. Use AST/call-graph inspection when textual searches are ambiguous.
5. Use `git blame`, `git log -S`, and the parent revision to establish why the code existed and which later transition superseded it.

A dead old implementation often leaves a dependency cone: helpers, imports, context fields, telemetry fields, tests, and constants referenced only from that dead block. Report the root dead path first, then its removable cone.

## 3. Separate dead code from reachable legacy behavior

Classify each finding:

- **Dead implementation:** no caller reaches it; usually SAFE after export/dynamic-use checks.
- **Reachable alternate route:** CLI, worker, smoke test, or operations facade still invokes the old engine; CAREFUL because behavior is public or operational.
- **Compatibility alias/branch:** determine the exact old consumer or persisted format it protects. If none exists, remove; otherwise require a migration/deprecation window.
- **Projection primitive:** a low-level FTS/read method may still be valid for integrity checks even if it must no longer serve as user-facing retrieval. Rename or narrow it rather than deleting blindly.

## 4. Audit hidden sentinel semantics

Pay special attention to inconspicuous differences such as `None` versus `[]`, omitted versus explicit defaults, or empty-string versus missing values. Compare normalization at every caller. If one surface converts omitted input while another passes it through, the same API may silently select different architectures.

Prefer one public semantic contract. If an internal caller needs “all types” or “skip routing,” require an explicit named policy or explicit value rather than a sentinel inherited from the old design.

## 5. Audit downstream response adoption

When the engine gains fields such as synthesized `information`, terminal `status`, citations, or evidence IDs, trace every serializer and cache publisher. A wrapper that still iterates only legacy summary rows can discard a valid body-only answer.

Run a minimal deterministic reachability probe:

1. Produce accepted canonical evidence without a directory-summary result.
2. Make the new engine return a valid synthesized answer and citations.
3. Assert the public tool and automatic/background serializer both expose useful output.

Do not treat `body_read_document_ids != []` or `sufficient=true` as success if model-visible output is empty.

## 6. Audit configuration and registry residue

For every advertised setting, constant, action name, and response field, locate a live runtime read or producer:

- A setting that is accepted, persisted, and tested but never read is a fake knob.
- A constant with no references is dead even when a similarly named config key exists.
- Registry actions referenced only by registry tests overstate the executable contract and may widen authorization.
- A response field populated only by a dead path is misleading compatibility telemetry.

Remove internal dead constants directly. For persisted config keys and documented response fields, use migration/deprecation unless compatibility is explicitly out of scope.

## 7. Check abstraction depth and durability

A persisted action should correspond to the meaningful work whose replay, provenance, and failure boundary matter. Flag a broad action callback that hides several external AI calls, canonical reads, judgments, and synthesis steps. If the controller records completion only after the callback returns, a crash can leave stage outcomes unaudited or replay-prone.

Possible remedies:

- persist each semantic stage as its own action;
- checkpoint validated stage output and prompt/source hashes before advancing;
- make replay/idempotency rules explicit for every external call and body read.

This is generally RISKY architecture work: report it, do not fold it into mechanical cleanup.

## 8. Apply Chesterton’s Fence

Before recommending removal, state the original purpose and whether it still applies. A compatibility normalizer backed by an old persisted default and migration tests is active migration machinery, not dead code. Recommend a sunset condition instead of immediate deletion.

## Reporting format

For each finding use:

```text
file:line -> problem -> concrete cost -> suggested fix | confidence | SAFE/CAREFUL/RISKY
```

Also report:

- exact callers and dynamic/export checks;
- history evidence establishing intent;
- deterministic reproduction output for reachable defects;
- tests run, separated from missing coverage;
- repository dirtiness and confirmation that unrelated files were not modified.

## Common pitfalls

- Declaring a lower-level search primitive obsolete merely because a new public engine exists.
- Searching only Python files and missing CLI docs, smoke scripts, package exports, or generated command registries.
- Counting references inside a dead method as evidence that its helpers are live.
- Removing a compatibility branch without checking persisted profiles or external import contracts.
- Reporting green tests as proof that alternate surfaces adopted the new architecture.
