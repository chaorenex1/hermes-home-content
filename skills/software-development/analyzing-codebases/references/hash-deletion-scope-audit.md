# Hash Deletion-Scope Audit for File-Canonical Systems

Use this when a cleanup proposes removing “text hashes” from a file-backed store. The goal is to eliminate only redundant or misleading hashes without weakening integrity, optimistic concurrency, crash recovery, idempotency, dedupe, or audit provenance.

## 1. Inventory by semantics, not spelling

Search source, schema/migrations, tests, docs, artifacts, and history for `hash`, `digest`, `checksum`, SHA names, and generic helpers such as `_fingerprint` or `_digest`. Build this matrix:

```text
file:line → stored/transient name → exact hash input → producer → consumers
→ persisted compatibility surface → purpose → DELETE/RETAIN/RENAME
```

Classify each occurrence into one of these families:

| Family | Typical names | Default verdict |
|---|---|---|
| Canonical-file integrity | `content_hash`, `source_sha256` | RETAIN |
| Optimistic concurrency / CAS | `before_hash`, `expected_file_hash`, `base_*_hash` | RETAIN |
| Staged after-image / crash recovery | `after_hash`, backup pre/post hashes | RETAIN |
| Version or plan binding | `candidate_content_hash`, `plan_hash`, `snapshot_hash` | RETAIN |
| Idempotency / dedupe | `dedupe_key`, `idempotency_key`, canonical identity digest | RETAIN |
| Query/context staleness | `query_hash`, `context_hash`, `goal_hash` | RETAIN |
| Prompt/model provenance | `template_sha256`, `prompt_hash`, reviewer/candidate hashes | RETAIN |
| Projection freshness | `source_snapshot_hash`, `last_indexed_hash` | RETAIN; often RENAME |
| Privacy-preserving identifiers | scope hashes, reason hashes, stable record IDs | RETAIN |
| Feature hashing | local hash embeddings | OUT OF SCOPE |
| Unreferenced helper or exact alias | dead helper, duplicate artifact field | DELETE only after proof |

Do not infer redundancy from a common name. A source transaction's `before_hash` and a review artifact's duplicate `before_hash` can have completely different safety roles.

## 2. Prove the byte/text contract

For every file-boundary hash, record all four operations:

1. producer input and normalization;
2. writer mode (`bytes`, `newline=None`, `newline=""`, etc.);
3. verifier read mode;
4. persisted hash algorithm/version.

A deterministic false conflict occurs when the producer hashes raw CRLF text, the writer preserves CRLF, and the verifier uses universal-newline text reading:

```python
import hashlib, io

original = "A\r\nB\r\n"
sink = io.BytesIO()
writer = io.TextIOWrapper(sink, encoding="utf-8", newline="")
writer.write(original)
writer.flush()
staged = sink.getvalue()
verified = io.TextIOWrapper(io.BytesIO(staged), encoding="utf-8", newline=None).read()
assert hashlib.sha256(original.encode()).digest() == hashlib.sha256(staged).digest()
assert hashlib.sha256(original.encode()).digest() != hashlib.sha256(verified.encode()).digest()
```

This is a representation mismatch, not evidence that the concurrency hash should be deleted.

Choose and name one contract:

- **Raw-byte contract:** hash bytes, write bytes, verify bytes. Exact byte changes, including line endings, are conflicts. Existing text-normalized metadata usually needs migration.
- **Canonical-text contract:** decode strict UTF-8, normalize `CRLF` and lone `CR` to `LF`, encode UTF-8, then hash/write/verify that representation. Line-ending-only changes are intentionally equivalent.

Do not combine contracts under an unversioned `content_hash` field.

## 3. Handle legacy pending journals before migration

A historical journal may contain mixed semantics in one entry, for example:

```text
before_hash = hash(read_text(existing_file))       # newline-normalized
at prepare time
after_hash  = hash(raw_input_text.encode('utf-8')) # pre-write CRLF preserved
```

Changing the current helper does not repair those rows. Before switching contracts:

1. enumerate pending/nonterminal transactions;
2. inspect journal schema/version and producer history;
3. define a compatibility verifier for each legacy version;
4. recover, commit, or terminalize legacy rows under the writer lock;
5. only then emit a new journal version carrying an explicit `hash_contract` value.

For legacy staged files, compare both raw staged bytes and canonicalized text against the persisted `after_hash` to identify the producer contract. Never silently delete or overwrite a target when the contract cannot be proven.

## 4. Safe deletion candidates

A hash is safe to delete only when all are true:

- exact repository and history searches show no live caller, dynamic lookup, SQL query, serializer, tool schema, or external artifact consumer;
- it is not used by recovery, rollback, stale-write detection, dedupe, uniqueness, or provenance;
- persisted rows/artifacts have a versioned reader or migration path;
- deleting it does not collapse two distinct identities;
- a focused regression proves the same stale/tampered input is still rejected elsewhere.

Common safe cases:

- an unexported helper with zero callers;
- a duplicate field in a versioned JSON artifact that is exactly derived from another retained field, after new writers stop emitting it and old readers remain compatible.

Common unsafe “redundancy” claims:

- “version already exists” — a database version does not detect manual filesystem edits;
- “plan hash already exists” — it may protect the plan object but not the live target file;
- “metadata has content hash” — journal before/after hashes are needed before metadata commit and during crash recovery;
- “the text is stored elsewhere” — file-canonical systems intentionally keep only integrity metadata in SQLite.

## 5. Naming cleanup

Prefer names that reveal the input contract and purpose:

```text
content_hash                 → source_text_sha256 / source_bytes_sha256
candidate content_hash       → candidate_identity_digest or candidate_dedupe_hash
directory summary hash       → source_snapshot_hash
SOUL/profile base hash       → base_profile_text_sha256
generic _hash helper         → sha256_canonical_json / sha256_canonical_text / sha256_bytes
```

Rename database columns only with migration and compatibility evidence. A code-layer semantic alias can land before a physical schema rename.

## 6. Regression gates

Minimum focused matrix:

- LF, CRLF, mixed CRLF/LF, lone CR, empty final line, non-ASCII;
- create and update transactions;
- actual manual content edit still conflicts;
- explicit policy for line-ending-only edits;
- staged-file tampering;
- crash after the first file of a multi-file commit;
- restart recovery with backup present and absent;
- same-path concurrent transaction preserves the newer committed file;
- legacy pending-journal compatibility;
- candidate promotion and staged operation plans;
- directory-summary target and source-snapshot fences;
- prompt templates continue using their intended raw-byte contract;
- metadata, version rows, projections, and public reads agree on the retained canonical source hash.

Check test history as well as current tests. If concurrency/recovery tests were deleted, report the deletion commit and restore equivalent coverage before changing hash fields.

## 7. Report format

Lead with the deletion boundary:

```text
DELETE: exact dead helpers / versioned duplicate aliases
RETAIN: integrity, CAS, recovery, idempotency, dedupe, snapshots, provenance
RENAME: semantically misleading but live fields
MIGRATE: persisted fields whose representation contract changes
```

Then provide the matrix, root-cause evidence, recommended contract, compatibility plan, passing/missing tests, and unresolved policy question: **Does a line-ending-only change count as a file change?**
