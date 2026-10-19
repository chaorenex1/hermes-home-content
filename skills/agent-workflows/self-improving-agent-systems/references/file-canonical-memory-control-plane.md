# File-Canonical Memory Control Plane

Use this pattern when durable memory bodies live in Markdown or another filesystem document format and SQLite stores only metadata/control state.

## Authority contract

Establish authority before designing extraction, review, promotion, summaries, or recovery:

- Accepted memory documents are the canonical content.
- Quarantined candidates and reviewed operation plans are canonical staged files until accepted or rejected.
- SQLite stores identifiers, logical paths, hashes, versions, lifecycle/task state, audit links, and projection status—not authoritative memory bodies.
- Directory summaries, FTS, vectors, and loose metadata caches are derived projections and must be rebuildable from canonical files.
- Recovery may reconcile metadata/indexes from files; it must never overwrite canonical files from stale database content.

Do not infer this contract from the current implementation. Read the user/architecture contract first and report implementation disagreement explicitly.

## Candidate and review flow

```text
turn evidence
→ type routing
→ frozen file/directory/template snapshot
→ staged candidate files + version-fenced operation plan
→ independent reviewer reads actual staged files, before/after targets, and evidence
→ approve | revise | reject | exhausted
→ approved file transaction
→ metadata and projection reconciliation
```

Review retries remain bounded. Exhaustion is `rejected`, `blocked`, or `exhausted`; it is never approval. The commit must execute the exact staged content and plan hashes that were reviewed.

## File transaction protocol

A single atomic rename does not make a multi-file operation atomic. Use a durable journal:

1. Freeze every target logical path, content hash, and version.
2. Render and validate complete staged outputs before touching accepted files.
3. Write and fsync a `pending` manifest containing old/new hashes, backups, targets, and reviewed plan hash.
4. Recheck base hashes.
5. Back up old files and atomically replace each target using same-directory temporary files.
6. Read back and verify every result hash.
7. Mark the journal `committed`; on partial failure, retain enough evidence to roll back or finish deterministically.
8. Only after verified file commit, update SQLite metadata and enqueue summary/index rebuilds.

On startup, reconcile pending manifests:

- all targets at new hashes → complete metadata/projections;
- all targets at old hashes → retry safely;
- mixed hashes → deterministic rollback or continuation from the manifest;
- unknown drift → block, preserve evidence, and never guess.

## Directory summaries

Regenerate a directory summary from all current accepted descendants, not only files changed in the triggering operation. Include target directory, memory type, and logical document paths. Snapshot file hashes, release locks before the AI call, then reacquire and reject stale output if the snapshot changed. Summary files are derived navigation artifacts unless the architecture explicitly declares otherwise.

## Verification matrix

- Delete/rebuild SQLite metadata from canonical files without content loss.
- Corrupt or stale SQLite content cannot overwrite canonical documents.
- Crash after each multi-file transaction phase converges through recovery.
- Reviewer sees persisted staged bytes and exact target before/after states.
- Review exhaustion leaves accepted files unchanged.
- Summary/index deletion followed by rebuild yields equivalent navigation visibility.
- No LLM or network call holds the global writer lock.
