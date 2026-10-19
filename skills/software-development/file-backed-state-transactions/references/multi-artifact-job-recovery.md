# Multi-Artifact Job Recovery Audit

Use this checklist when a durable job reads or publishes several file-authoritative artifacts while SQLite tracks jobs, versions, intents, or receipts.

## 1. Artifact identity

Do not collapse independently mutable files into one ambiguous `version` field. Every persisted reference should freeze:

```text
ArtifactRef {
  profile_scope / session_scope,
  document_id,
  logical_path,
  artifact_schema_version,
  source_metadata_version,
  content_hash
}
```

Keep schema version separate from content revision. A compound snapshot should carry exact refs for every component (for example profile, session, and supplement), not only a hash of an in-memory DTO.

## 2. Durable run manifest

A resumable run needs an immutable, file-backed manifest containing at least:

- job kind, scope, stable turn/event watermark, generation, and configured depth;
- exact input artifact refs and expected target preimage refs;
- prompt template id/revision/hash and an immutable prompt-body ref;
- response-schema hash and per-stage input/output artifact refs;
- Accepted document/version/accepted-version refs, Working Set version/refs, and Materialization refs;
- Intent idempotency keys and phase/slot identities;
- source transaction id plus expected publication after-images;
- retry/deadline budget and recovery-algorithm version.

A hash alone is not a recovery payload. If an editable prompt changes after a crash, the old hash cannot reconstruct the request unless its body or immutable revision is retained.

## 3. Job-to-Intent idempotency

Use a durable uniqueness constraint such as:

```text
UNIQUE(job_id, generation, phase, retrieval_slot)
```

Derive Intent identity from the job/generation/phase/slot plus query hash, memory types, and Working Set version. Recovery must adopt the existing Intent rather than call a UUID-only `create_intent` again. Test crashes both after Intent creation and after Intent completion but before the Job checkpoint advances.

## 4. Publication and recovery order

Recover in dependency order:

1. Quiesce new workers and capture a cutoff.
2. Recover pending file transactions.
3. Verify artifact paths, raw-byte hashes, and metadata versions.
4. Reconcile Job, stage, Intent, Materialization, and Working Set state with CAS updates.
5. If a publication transaction committed but Job terminalization did not, verify the exact after-images and finalize without rerunning AI.
6. Resume only from the last complete stage whose payload, prompt, refs, deadlines, and expected versions still validate.
7. Start workers only after convergence.

Never infer success from a target file merely existing. It must match the transaction/run-owned after-image and publication receipt.

## 5. Crash matrix

Inject failures at all boundaries, not merely “before final commit”:

- after input artifact publication;
- after each stage output;
- after each target-file replace in a multi-file transaction;
- after source transaction commit but before run-row insertion;
- after run-row insertion but before Job terminalization;
- after Intent completion but before Job↔Intent checkpointing;
- after Job completion but before mirror/receipt update.

For every case assert: no synthetic success, no duplicate Intent/Materialization/Working Item, no overwrite of drifted files, and a second reconciliation pass is a no-op.

## 6. Define “zero writes” precisely

Distinguish:

- **reconciler-level no-op:** a second call changes no recovery-owned rows/files;
- **full-startup no-op:** a fresh process changes no database, manifest, journal, or artifact mtime.

The latter additionally requires initialization writers (for example manifest regeneration) to compare content and skip identical replaces. Tests should state which boundary they measure.

## 7. Migration and rollback compatibility

Before promising “restore old code,” check both fences:

- Does the old binary reject a newer SQLite schema?
- Can the old reader parse new artifact schemas written at the same paths?

If either answer is no, choose one of:

- side-by-side versioned artifacts plus an atomic pointer/cutover;
- a maintenance window where rollback occurs before reopening writers;
- a forward-compatible reader shipped before the writer migration.

Do not restore an old whole-database backup after accepting new live writes; that discards valid metadata and control state. Use migration-owned, hash-fenced rollback or explicitly require a quiesced cutoff.

## 8. SQLite body inventory

When the contract says “SQLite is metadata-only,” inventory every body-like column (`content`, `goal`, rendered text, summaries, payload JSON) and classify it as:

- canonical body — must live in a file;
- bounded ephemeral/control payload — explicitly allowed;
- rebuildable projection — disposable;
- legacy compatibility body — plan/apply/verify/scrub/rollback required.

A broad policy statement is not verified while an injection path still reads copied body text from SQLite.

## Minimum verification

- focused raw-byte/source-transaction tests;
- compound artifact CAS races across sessions/processes;
- Job↔Intent replay tests with uniqueness assertions;
- full crash matrix and second-pass no-op test;
- migration clone test plus rollback compatibility probe;
- `PRAGMA quick_check`, `PRAGMA foreign_key_check`, source integrity report, and public read-back;
- full suite and unchanged-worktree check for read-only audits.
