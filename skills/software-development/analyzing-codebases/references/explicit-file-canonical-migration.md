# Explicit Migration from SQLite Bodies to Canonical Files

Use this when a file-canonical application still has legacy body text in SQLite and normal reads correctly fail with `migration_required`. This is an operator migration, not startup reconciliation: database bodies are a one-time source only, never runtime repair authority.

## Required lifecycle

Implement four explicit phases with durable, body-free artifacts:

1. **Plan** — read-only inventory and precondition capture.
2. **Apply** — create-only file publication, metadata commit, read-back, then body clearing.
3. **Verify** — independent source, metadata, schema, and audit validation.
4. **Rollback** — restore a pre-apply backup only when the post-apply state has not drifted.

A useful state machine is:

```text
planned -> applying -> files_committed -> bodies_cleared -> verified
                         |                    |
                         +-> recover/resume <-+
verified + no drift -> rolled_back
```

## Plan contract

The plan must be explicit about the expected cardinality by artifact class. If the operator expects 14 evidence and 14 candidates, apply must refuse 13+14 or 14+15 rather than silently broadening the migration.

For every eligible row record:

- stable record ID, source table and body column;
- artifact kind, storage area, canonical logical path, title, and source type;
- UTF-8 body SHA-256 plus character/byte counts;
- a row-snapshot hash over all migration-relevant metadata;
- destination precondition (`absent`, `already_migrated`, or `conflict`);
- active source-metadata precondition;
- sequence and disposition.

Never put bodies in `plan.json`, receipts, journals, or normal diagnostics. Do not confuse a domain-level `content_hash` with the file-body SHA-256: evidence IDs may hash classification/provenance, and candidate hashes may include evidence IDs/type/path. Compute the file hash directly from the exact bytes that will be published.

## Eligibility and authority rules

| Current state | Required behavior |
|---|---|
| Body non-empty, metadata absent, destination absent | Eligible; SQLite body may be used once to create the file |
| Destination exists, metadata absent | Conflict; preserve the file, do not bind it, overwrite it, or clear the DB body |
| Metadata and file already agree exactly | Already migrated; do not use the DB body; read back before clearing residue |
| Metadata exists but file is missing/hash-mismatched | Conflict; never repair canonical files from SQLite |
| Body empty and file/metadata missing | Irrecoverable migration gap |
| Row, metadata, or destination changed after planning | Stale plan; fail closed |

The key rule is: **a legacy DB body may be used only when the canonical destination is absent.** A pre-existing file outranks SQLite even when it differs or has no metadata; it requires separate reconciliation.

## Apply ordering

1. Stop or quiesce the owning service; acquire its cross-process writer lock.
2. Require no unrelated pending source transaction.
3. Create a complete pre-apply profile backup at a new external path and hash it.
4. Re-read every planned row and revalidate row/body hashes, path safety, metadata collisions, symlinks, and destination preconditions.
5. Stage all exact UTF-8 bodies and persist a pending journal.
6. Publish with **create-only** semantics. Do not use `os.replace()` for an absent-only migration because it can overwrite a file created after the fence check. Use a same-volume exclusive primitive (`O_CREAT|O_EXCL`, an exclusive hard link, or an equivalent no-replace rename) and fail closed if unavailable.
7. Verify every file from disk; only then publish source metadata with the actual file hash and version.
8. Read every artifact through the same hash/path-verified API used by production.
9. Under one `BEGIN IMMEDIATE`, recheck the read-back fence, clear only the planned rows, restore any temporarily removed immutability trigger exactly, write the migration control state, and commit.
10. Perform post-commit file/metadata/body/trigger/integrity verification and atomically write a body-free receipt.

Never use a broad `UPDATE ... WHERE body != ''`; update exact planned IDs after revalidating the row snapshots. SQLite DDL is transactional, so temporarily dropping an immutable-update trigger can be safe only inside the same explicit transaction, with rollback tests proving the trigger survives failure.

## Crash and idempotency seams

Design retries around these durable boundaries:

- **Before file commit:** recover/terminalize the pending transaction, then re-plan or retry.
- **After some creates:** remove only files proven to be owned by the transaction; never delete a newer/manual file.
- **After files+metadata but before body clearing:** rerun should classify items as already migrated, read them back, and finish clearing.
- **After body clearing but before receipt:** verify the canonical files and control rows, then reconstruct the same receipt without rewriting files.
- **Repeated apply of a verified plan:** return the same verified outcome with no writes.

For first-write recovery, `target hash == after_hash` alone is insufficient ownership proof: another writer may have created identical bytes. Also inspect whether the staged file was consumed, an applied marker, or a durable ownership token before deleting a target.

## Rollback contract

A reversible migration necessarily retains a temporary preimage backup. Record its hash in the receipt and define a retention/destruction policy.

Automatic rollback should:

1. require explicit confirmation and the exact receipt/backup;
2. verify a full post-apply profile fingerprint or equivalent semantic fence;
3. refuse if any later file or database state has changed;
4. restore the complete pre-apply profile while the service is stopped;
5. verify schema integrity, expected legacy rows, and expected migration gaps.

Do not perform a selective rollback after drift: restoring old SQLite bodies or deleting canonical files can erase later legitimate state.

## Audit artifact minimum

Use metadata-only migration and item records (SQLite and/or signed/hash-fenced JSON) containing:

- schema/version, migration ID, plan hash, expected class counts;
- precondition and postcondition fingerprints;
- source transaction ID and backup archive hash;
- per-item record ID, logical path, row snapshot hash, body hash, disposition, and clear timestamp;
- trigger SQL hashes, quick-check/foreign-key summaries;
- state transitions, timestamps, bounded failure reason.

The artifact must prove what happened without reproducing private bodies.

## Verification and test matrix

Cover at least:

- exact expected counts and a non-mutating plan;
- successful multi-class migration and production-API read-back before clearing;
- destination present before plan and appearing after plan;
- row/body/metadata drift after plan;
- same-content destination race without overwrite or recovery deletion;
- crash before publish, mid-publish, after metadata, and before/after body clear;
- trigger restoration on DDL/DML failure;
- idempotent replay and receipt reconstruction;
- body-free plan/journal/receipt;
- rollback success and rollback refusal after drift;
- UTF-8 multibyte and CRLF/raw-byte hashing behavior;
- final `quick_check`, foreign keys, source integrity, zero migration gaps, and zero legacy body residue.

## Audit pitfalls

- A diagnostic named `verify` may still initialize schema or rewrite a manifest. Trace its call path before claiming read-only behavior; implement true verification with SQLite `mode=ro` and pure filesystem reads.
- A bounded issue list can truncate migration gaps. Query exact class counts independently before planning.
- Hashing text through universal-newline `read_text()` can disagree with raw staged bytes on Windows. Use one explicit byte contract end to end, or prove the batch contains no carriage returns before relying on text hashing.
- Generic source transactions that support replacements are not automatically safe for absent-only migration; add and test a create-only mode.