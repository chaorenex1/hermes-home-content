---
name: file-backed-state-transactions
description: "Use when files are authoritative and databases track state."
version: 1.1.0
author: Masía
created_by: agent
---

# File-Backed State Transactions

Use when durable bodies live in files while SQLite or another database stores identities, logical paths, hashes, versions, lifecycle state, transaction journals, audit events, or rebuildable indexes.

## Authority contract

1. Declare exactly one content authority. If files are authoritative, normal reads, startup recovery, and projections must never reconstruct a missing or conflicting file from a compatibility body column.
2. Keep database rows metadata-only after migration. Compatibility body columns may be used only by an explicit, operator-visible migration with a frozen plan and backup.
3. Treat FTS, embeddings, summaries, and directory indexes as rebuildable projections. They may be deleted and regenerated from verified files.
4. Preserve deterministic host ownership. AI may propose content or operations, but file publication, version fences, rollback, and metadata transitions remain deterministic.

## Stable content/hash contract

Choose one representation and use it at every boundary:

- **Raw-byte authority:** hash the exact bytes that are atomically written and read. For UTF-8 text, open with `newline=""` or use `read_bytes()` so CRLF is not silently normalized.
- **Canonical-text authority:** normalize explicitly before both hashing and writing. Document the normalization and accept that source offsets and byte identity change.

Never hash an in-memory string before write and later verify it through universal-newline `read_text()`; on Windows, CRLF can become LF and produce a deterministic false conflict. Do not “fix” this by deleting CAS/content hashes. Hashes protect idempotency, optimistic concurrency, crash recovery, migration audit, and projection freshness.

Centralize exact source I/O in one helper and route source scans, transaction fences, staged-operation snapshots, accepted reads, rollback, and integrity checks through it. JSON journals/configuration may still use normal text reads when their byte identity is not the content fence.

## Transaction workflow

1. Acquire the profile-scoped writer lease.
2. Freeze logical paths, preimage existence, preimage hashes, expected versions, and after-image bytes.
3. Write staged files atomically and persist a pending journal before publication.
4. Re-read staged bytes using the same hash contract and verify every after-hash.
5. Recheck target existence/hash/version fences immediately before replace.
6. Preserve required backups, atomically publish, and verify target bytes.
7. Update source metadata only after every target is verified.
8. Mark the journal committed; retain failed records for audit.

On failure, never delete or overwrite a same-path file unless its exact bytes match the transaction-owned preimage or after-image. A file that drifted after planning belongs to another writer/operator and must survive for reconciliation.

## Multi-artifact durable jobs

When a job spans profile, session, supplement, stage-output, or prompt artifacts, preserve each file's independent identity. Use an `ArtifactRef` with scope, document ID, logical path, artifact schema version, source metadata version, and content hash; never collapse independently mutable files into one ambiguous `version`.

A resumable job also needs an immutable file-backed run manifest. Freeze the event watermark and generation, configured depth, exact input and expected-target refs, prompt/template revision and body ref, response-schema hash, per-stage output refs, Intent idempotency keys, side-effect refs, source transaction ID, publication after-images, and retry/deadline budget. A hash by itself is not a recovery payload.

Require durable Job-to-Intent uniqueness by generation/phase/slot. Recover source transactions before reconciling Jobs, Intents, Materializations, or Working Items. Cover the crash window after file publication but before SQL run/job terminalization; if exact after-images committed, finalize without rerunning AI.

Define whether “second recovery writes nothing” means the reconciler only or a fresh full startup. Full-startup no-op tests must include manifest/journal/artifact mtimes and require initialization writers to skip identical replacements.

Before promising rollback to old code, verify the old binary accepts the migrated database schema and the old reader accepts new same-path artifact schemas. Otherwise use side-by-side artifacts with an atomic pointer, a quiesced rollback window, or a forward-compatible reader. Never restore an old whole-database backup after new live writes.

See `references/multi-artifact-job-recovery.md` for the full run-manifest fields, Job↔Intent uniqueness rule, crash matrix, SQLite-body inventory, and rollback compatibility checks.

## Run-scoped authority across isolated Agent boundaries

When the Host intentionally runs an inner Agent in a fresh `contextvars.Context`, ambient provider bindings are not an authority channel. Preserve the isolation boundary and pass one Host-owned opaque run context instead: register a frozen binding/workflow under a fresh ID, forward only internal owner/purpose/token metadata through every real tool dispatch route, validate exact ownership and lifetime in the provider, and revoke in `finally`. Never recover authority from a model-visible job ID, thread identity, or singleton current-job variable.

Keep publication contracts deterministic at the same boundary: a multi-artifact Base generation must contain its complete required set, and a Dynamic generation must never activate as `completed` with zero artifacts. Verify both physical files and active metadata rows through a fresh-process production-path smoke test.

Do not add policy or length limits that the accepted API contract does not authorize. If the user explicitly removes named constraints, delete the constants plus dependent validators/tests, prove zero literal references, retain only unrelated accepted limits, and regenerate maintenance patches before verification.

See `references/isolated-agent-run-capabilities.md` for the architecture, dispatch coverage, security failures, test matrix, constraint-removal protocol, and Host/provider deployment evidence.

## Physical-layout flattening

When removing a lifecycle directory such as `accepted/`, keep the lifecycle label in metadata while mapping accepted logical paths directly below the authoritative root. Do not implement this as a one-line root substitution alone: a flattened root commonly also contains summaries, prompts, journals, history, and other provider state.

1. Add a red test that asserts the exact physical destination, not only the logical path returned by an API.
2. Enumerate the accepted top-level logical roots for default tree/search operations; never recursively scan the whole provider root.
3. Validate read, tree, and search paths against the same accepted topology as writes. Filter generated summary filenames from default accepted scans while preserving exact-path summary access.
4. Update every physical-path consumer together: direct file tools, metadata reconciliation, directory-summary source discovery, statistics writers, smoke scripts, and transaction target resolution.
5. Migrate the legacy directory under the profile writer lease. Preflight every source and target before moving anything; reject symlinks, unsupported files, and differing same-path targets. Identical duplicates may converge without rewriting the target.
6. Make the migration idempotent and crash-convergent. Persisted transaction entries should derive active targets from `storage_area + logical_path`, not trust an obsolete physical `target_path` captured under the old layout.
7. Verify that provider-internal Markdown and generated summaries are not exposed by default root tree/search after flattening.

See `references/flattening-authoritative-layouts.md` for the compact reproduction and migration checklist.

## Legacy body migration

Use four explicit phases: `plan`, `apply`, `verify`, `rollback`.

- Plan freezes source row IDs, body digests, target logical paths, expected absence, and database/profile backup identity without exposing bodies.
- Apply may materialize a compatibility body only when the target is absent. A pre-existing target without matching active metadata is a conflict even when its bytes happen to match; do not let SQLite silently claim file authority.
- Verify every file, active metadata row, reference edge, and high-level read API before scrubbing any compatibility body.
- Scrub bodies in a separate transaction only after the whole frozen batch passes. Recreate immutable triggers inside the same migration transaction when a compatibility column must be cleared.
- Rollback only when post-apply files and metadata still match the migration-owned after-images. Define backup retention separately from logical migration completion.

## TDD and verification

Use vertical slices:

1. RED: a real source transaction containing explicit CRLF fails its staged hash fence.
2. GREEN: exact write/read/verify preserves content and digest.
3. RED/GREEN: accepted-file scan produces the same content/hash as the source repository.
4. RED/GREEN: staged-operation snapshot and canonical accepted read preserve the same contract.
5. RED/GREEN: public create/update and rollback paths preserve exact content.

Then run:

- focused source-store and migration tests;
- recovery tests for pending, committed, failed, missing-stage, and drifted-target states;
- schema/foreign-key/quick-check validation;
- full suite and `git diff --check`;
- one real profile read-only verification, with bodies and secrets omitted from output.

See `references/windows-newline-hash-fences.md` for the compact CRLF reproduction, fix pattern, and migration cautions.

## Pitfalls

- SQLite connection context managers commit/rollback but may not close handles; close explicitly before temporary-profile cleanup.
- Do not mix normalized text hashes, raw-byte hashes, and semantic identity hashes under one undocumented helper.
- Do not turn a failed source transaction into synthetic success because a target file exists; verify transaction ownership and metadata publication.
- Do not clear all legacy bodies record-by-record before the frozen batch verifies; partial scrubbing destroys rollback authority.
- Do not run a migration against active writers without stopping them or establishing a lease/cutoff that excludes live work.
- Do not treat a projection hash mismatch as permission to overwrite the authoritative file from database content.
