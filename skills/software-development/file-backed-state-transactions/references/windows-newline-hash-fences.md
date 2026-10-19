# Windows Newline Hash Fences

## Failure signature

A transaction hashes a Python string containing CRLF, writes it with newline preservation, then verifies the staged file through universal-newline text reading:

```text
prepare: SHA256(content.encode("utf-8")) where content contains \r\n
write:   open(..., newline="") preserves \r\n
verify:  Path.read_text() converts \r\n to \n
result:  staged hash fence changed
```

This is a deterministic representation mismatch, not concurrent modification or a broken SHA-256 implementation.

## Minimal RED probe

Use the real repository/transaction API in a temporary profile, not only two in-memory strings:

```python
content = "line one\r\nline two\r\n"
metadata = repository.write(SourceWrite(..., content=content))
stored_metadata, stored_content = repository.read(document_id)
assert stored_content == content
assert stored_metadata.content_hash == sha256(content.encode("utf-8")).hexdigest()
```

Before the fix, the write should fail at staged verification. This proves the test exercises the transaction boundary.

## Raw-byte-preserving fix

Centralize source reads:

```python
def read_source_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()
```

Use the same helper for:

- preimage/before-hash reads;
- staged after-hash verification;
- published target verification;
- source metadata reads;
- rollback ownership checks;
- integrity scans;
- accepted-file projections;
- staged-operation snapshots;
- public accepted create/read/rollback paths.

Keep normal `read_text()` for JSON journals only when their byte identity is not a transaction fence.

## Integration checks

A source-store-only fix is incomplete if another layer rescans accepted files with universal-newline normalization and rewrites metadata from a different digest. Add separate RED/GREEN slices for:

1. source transaction round trip;
2. accepted-file scanner content/hash;
3. staged operation target snapshot;
4. accepted store canonical read;
5. public accepted write and rollback.

## Migration caution

Do not change the hash contract while recoverable pending transactions exist unless the migration understands the old contract. First inventory pending journals/transactions and either finish them under the old algorithm or explicitly version recovery logic.

For legacy SQLite bodies, migrate only through a frozen plan. Verify every file and metadata row before clearing any body. Pre-existing files without active metadata are conflicts; SQLite must not silently overwrite or adopt them.
