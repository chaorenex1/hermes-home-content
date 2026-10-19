# Live SQLite + File-Canonical Store Health Audit

Use this recipe for profile-local memory, curation, retrieval, and durable workflow stores whose SQLite database is live while background workers may still write.

## 1. Freeze the meaning, not the process

Do not copy a live database unless the user needs a forensic image. Open the original source read-only so WAL/journal state is interpreted by SQLite itself:

```python
from pathlib import Path
import sqlite3

db = Path(DB_PATH)
connection = sqlite3.connect("file:" + db.as_posix() + "?mode=ro", uri=True)
connection.row_factory = sqlite3.Row
```

Record:

- UTC observation time and database mtime
- `PRAGMA quick_check`
- `PRAGMA foreign_key_check`
- journal mode, page count, freelist count
- migration count/min/max and missing versions
- physical tables versus logical tables; exclude FTS shadow tables from domain counts

A changing mtime during the audit means the store is live. Take one final compact snapshot after diagnosis and use only that snapshot's counts in the headline.

## 2. Build a state matrix

For every logical table, collect row count plus low-cardinality distributions for columns such as:

```text
status, state, lifecycle, phase, decision, operation,
source_type, memory_type, job_kind, producer
```

Also collect `MIN`/`MAX` for timestamp columns and bounded recent metadata. Never dump body, prompt, transcript, evidence, rationale, token, or secret columns. For text-bearing columns, report only non-empty count and length statistics unless content inspection is explicitly required.

Group tables into independently judged layers:

| Layer | Typical evidence |
|---|---|
| Schema substrate | migrations, constraints, FKs, triggers |
| Canonical files | source metadata, file existence, hashes |
| Quarantine | evidence, candidates, rendered versions, claims |
| Accepted knowledge | accepted documents and immutable versions |
| Retrieval | intents, materializations, receipts, usage feedback |
| Session memory | active/stale/completed working items |
| Background work | jobs, loop runs/plans/events, transactions |
| Projections | FTS rows, summary rows, optional vector/Lance tables |

Do not compress these into one “healthy” flag. A database can be structurally healthy while candidate reads, accepted retrieval, or background extraction is broken.

## 3. Verify file-canonical authority

For each active source metadata row:

1. Resolve `storage_area + logical_path` below the profile-local source root.
2. Reject traversal or symlink escape before reading.
3. Require the file to exist.
4. Hash using the same byte/text contract used by the writer.
5. Compare against metadata.

Separately identify legacy rows with no active source metadata. A generic migration-gap query is:

```sql
SELECT item.<id>
FROM <legacy_table> AS item
LEFT JOIN source_file_metadata AS source
  ON source.document_id = item.<id>
 AND source.status = 'active'
WHERE source.document_id IS NULL;
```

Count gaps by artifact class: evidence, candidate, candidate version, accepted document, derived profile/session artifact, and directory summary. Non-empty legacy body columns do not make those rows readable in a file-canonical implementation; report them as compatibility residue. Normal public reads should fail closed rather than silently reconstructing authority from stale SQLite content.

## 4. Cross-check public reachability

Use at least one bounded application-level read for each claimed capability:

- status/count endpoint
- accepted tree/list
- candidate list, then candidate read if safe
- accepted search/read
- projection table listing or capability report

Compare the result to SQL. Important asymmetry: a status call may count metadata rows successfully while list/read fails because canonical source files are missing. Report both; never infer reachability from counts alone.

## 5. Diagnose staged hash-fence conflicts

When a staged write records an `after_hash` but verification reports a changed staged hash:

1. Read the failing transaction entry and its `after_hash`.
2. Find the source input without printing its body.
3. Compute hashes for:
   - exact raw string bytes (`text.encode('utf-8')`)
   - CRLF-to-LF normalized string
   - raw staged file bytes
   - text returned by the verification read path
4. Count `\r\n` and `\n` occurrences.
5. Trace the code that computes `after_hash`, writes the staged file, and rereads it.

Typical deterministic Windows failure:

```text
producer: sha256(original CRLF text)
writer: preserves CRLF
verifier: Path.read_text() performs universal-newline conversion
result: sha256(LF-normalized text) != persisted after_hash
```

The repair contract is not “retry.” Choose one representation and apply it everywhere:

- byte contract: hash bytes, write bytes, verify bytes; or
- text contract: normalize newlines before both hashing and writing, and use the same normalization on read.

Add regression coverage with LF-only, CRLF-only, mixed-newline, non-ASCII, and restart/recovery cases.

## 6. Interpret empty and nonterminal state carefully

- Optional projection available + empty accepted source + empty projection + no retry error = healthy empty projection.
- Accepted sources exist + empty projection = projection reachability defect.
- Historical `planning`, `pending`, or `retryable` rows with old timestamps are nonterminal residue until a recovery/ownership rule proves they remain runnable.
- A terminal child job plus a still-pending session checkpoint is a lifecycle convergence gap.
- Retrieval intent completion with zero materializations may be valid when the accepted store is empty; receipts should then show no accepted references.

### Empty accepted store despite apparently completed extraction

When accepted files remain empty while background jobs report success, trace the pipeline backward from promotion instead of treating `completed` as semantic success:

1. Count accepted files, accepted-version rows, promotion events, rendered candidate versions, current-format candidates, legacy candidates, and evidence files independently. A zero at the first candidate/version seam proves review and promotion never had input.
2. Join durable jobs to evidence by stable message/event identity, then compare job creation times with candidate creation times. `completed jobs + persisted evidence + no newer candidates` isolates the defect to extraction output validation or candidate persistence—not signal gating or promotion.
3. Read persisted checkpoint/result status and candidate counts. Distinguish `completed_empty`, `rejected`, `retryable`, and `promoted`; do not accept a worker's generic `completed` flag when its returned domain result says `rejected`.
4. Audit checkpoint cardinality. If the job ID is event/type scoped but the checkpoint key is only session scoped, later lanes overwrite earlier outcomes and make failure ratios unknowable. Use event/job identity or a durable per-job table as the authoritative record.
5. Compare the producer prompt, host JSON Schema, and runtime validator as one contract. Every operation literal must agree, and conditional operations must require the fields the validator later consumes. A schema that requires only an operation discriminator can admit structurally incomplete candidates that are then rejected after a paid model call.
6. Preserve a bounded, content-free rejection code and stage outcome. A generic `output_rejected` without the validator class/field cannot distinguish invalid operation, missing field, wrong type, stale evidence, or source-span failure; never persist raw model/user bodies merely to improve diagnostics.
7. Treat status-only APIs as substrate evidence. A candidate count can succeed while candidate list/read fails because canonical files or rendered versions are absent. Exercise one bounded public read before calling the candidate/review layer reachable.

Also inspect orchestration wrappers for hard-coded `state_changed=true` or `decision=done`; these can make evidence capture look like successful candidate extraction even when candidate IDs are empty.

## 7. Keep cursor ownership explicit in audit scripts

Do not execute nested queries on the same `sqlite3.Cursor` that is driving an outer `for row in cursor.execute(...)` loop. The second `execute()` replaces the cursor's active result set, so the outer loop may silently stop after one row and return a plausible but false aggregate.

Use one of these safe shapes:

```python
outer_rows = connection.execute(OUTER_SQL).fetchall()
for row in outer_rows:
    related = connection.execute(INNER_SQL, (row["id"],)).fetchall()
```

or allocate a separate cursor for the nested lookup. If this bug is discovered after reporting a count, rerun the complete affected aggregation; do not patch the number mentally.

## 8. Report format

Lead with one overall verdict, then a compact layer table:

```text
substrate → canonical files → quarantine/review → accepted store
→ retrieval/session memory → background jobs → projections
```

For each layer give: counts, direct evidence, status, and exact blocker. End with repair order and verification gates. Keep raw private content out of the report.
