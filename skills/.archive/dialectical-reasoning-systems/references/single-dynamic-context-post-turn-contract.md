# Lagged Single Dynamic Context Contract

Use this reference when the host explicitly wants one completed turn to synthesize exactly one model-visible context for the next turn. This is a distinct contract, not a reduced dual-layer or query-aware offer design.

## Canonical lifecycle

```text
new session
  -> synchronously attempt one bootstrap dialectical call
  -> publish DynamicContext(source_turn=0, origin=session_init)
turn 1 prefetch
  -> read source_turn=0 only
turn N completes
  -> sync_turn(N) runs all retrieval/reasoning
  -> publish one final DynamicContext(source_turn=N, origin=completed_turn)
turn N+1 prefetch
  -> read source_turn=N only
```

The System Prompt remains session-stable. The provider's only model-visible dynamic semantic block is `<dynamic-context>` under the host's ordinary memory transport fence.

## Bootstrap once per logical session

Do not equate provider-object construction with logical session creation: gateways and agent caches may reconstruct a provider for an existing session.

Use a metadata-only control row with `UNIQUE(profile_scope, session_scope)` and a terminal bootstrap state such as `claimed | completed | failed`:

1. Insert `claimed` before the AI call.
2. Only the winning insert may call the bootstrap model.
3. Publish `source_turn=0` then mark `completed` on success.
4. Mark `failed` on handled failure.
5. Treat `claimed`, `completed`, and `failed` as already attempted; provider rebuilds and resumes do not retry.

This is at-most-once under crash, not guaranteed exactly-once. If the process dies after claim but before the call, the first turn has no bootstrap context and normal `sync_turn(1)` may still publish source turn 1.

Apply the same coordinator to `initialize()` and session-switch paths. New/reset/branch/compression session IDs receive independent claims; resume of an existing session does not. Rewind with the same session ID keeps the bootstrap claim and removes only future-turn output.

## Generation and delivery separation

`sync_turn()` owns all expensive or mutating work:

- bounded current-turn slicing;
- removal of injected `api_content`/memory blocks;
- internal Working Set reads;
- current Accepted retrieval;
- fixed-depth d1/d2/d3 execution;
- atomic final publication.

`prefetch()` is an O(1) read-only delivery adapter:

- no AI;
- no retrieval;
- no database/file mutation;
- no feedback;
- no fallback to older turns;
- return empty unless `stored.source_turn == current_turn - 1`.

`queue_prefetch()` is a no-op. Explicit search tools remain independent.

## Fixed depth

- Session bootstrap is one dedicated AI call and uses `completed_depth=0`; it never expands with `dialecticDepth`.
- Normal depth 1 executes d1; depth 2 executes d1+d2; depth 3 executes d1+d2+d3.
- Later stages receive the complete earlier structured outputs directly in memory.
- There is no `sufficient` early stop.
- Intermediate stages are not persisted or injected.

Strict previous-turn delivery is incompatible with a cadence that skips completed turns. Remove cadence knobs or redefine delivery as latest-successful; do not claim both semantics.

## Consistency without context hashes

Do not use content/input/prompt/output/stage/injection hashes or frozen prompt/evidence bundles for this path. Preserve only:

- one FIFO writer per session;
- monotonic `source_turn` publication;
- temp-file write plus atomic replace;
- profile/session scope isolation;
- read only fully published files.

Hashes belonging to other authority systems—accepted-file integrity, candidate review, source transactions, or profile-improvement preimages—are outside this deletion scope.

## Deliberately removed surfaces

When this contract replaces a layered/query-aware architecture, delete the whole obsolete dependency cone:

- base/profile/working/accepted public context renderers;
- query-time automatic retrieval intent/materialization;
- system-context side path;
- injection offers and receipts;
- adoption/usage feedback and counters;
- hash-bound dialectical jobs and stage checkpoints;
- legacy prompts/schemas/readers/tables/artifacts.

Dynamic output must not become raw evidence for long-term extraction, direct Accepted writes, or SOUL mutation. A later user correction is simply current-turn evidence for the next synthesis.

## Required tests

1. Fresh session attempts one bootstrap call and Turn 1 reads source 0.
2. Concurrent/rebuilt/resumed same session does not repeat bootstrap.
3. Bootstrap failure is fail-open; Turn 1 is empty and `sync_turn(1)` may publish source 1.
4. New/reset/branch/compression and rewind obey their session identity contract.
5. Each completed non-interrupted turn publishes at most one matching source turn.
6. Failed generation produces no current-turn context and does not fall back.
7. Prefetch has no AI/retrieval/write side effect.
8. Only `<dynamic-context>` is model-visible from the provider.
9. Explicit accepted search still works after automatic intent/materialization deletion.
10. Removed modules, prompts, tables, tags, feedback, and hashes are absent from source, wheel, and disposable runtime.
