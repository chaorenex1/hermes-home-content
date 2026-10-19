# Windows SQLite temporary-profile cleanup

## Symptom

A Python probe completes its database work and prints the expected result, but leaving `TemporaryDirectory()` raises:

```text
PermissionError: [WinError 32] ... memory.db
```

This is not a false failure. The functional operation succeeded, but the process still owns an open handle when deterministic cleanup begins.

## Tight reproduction

Use the real store/model path rather than opening and closing an isolated connection:

```python
from pathlib import Path
from tempfile import TemporaryDirectory

with TemporaryDirectory() as directory:
    model = Model(Path(directory))
    model.write_and_read(...)
    assert model.snapshot(...)
# Passing requires immediate deletion here while `model` still exists.
```

Keeping the model alive is intentional. The model should not require destruction or process exit to release per-operation SQLite connections.

## Root cause

Python's `sqlite3.Connection` context manager is a transaction manager: `__exit__` commits or rolls back. It does **not** close the connection. Therefore this shape is insufficient for deterministic lifetime management:

```python
with sqlite3.connect(path) as connection:
    ...
```

The leak can be masked on systems that permit deleting open files and exposed reliably on Windows.

## Correct ownership pattern

For a one-operation connection:

```python
from contextlib import closing

with closing(sqlite3.connect(path)) as connection, connection:
    connection.execute(...)
```

For read-only work:

```python
with closing(sqlite3.connect(path)) as connection:
    rows = connection.execute(...).fetchall()
```

A project-owned `_connect()` context manager with `finally: connection.close()` is preferable when many modules share the same policy.

## Session-specific failure that improved the rule

Introducing `from contextlib import closing` initially caused `TypeError: 'str' object is not callable` because the same function already had a local string named `closing` for an XML closing tag. Rename semantic data to `closing_tag` before calling the imported helper. This is why the umbrella workflow requires a collision search after adding lifecycle helpers.

## Verification recipe

1. Run the new cleanup test alone and observe the original `WinError 32` before the fix.
2. Replace every SQLite acquisition in the affected module with explicit closure.
3. Run the cleanup test plus read/write behavior tests.
4. Run the full suite and compile/lint checks.
5. Confirm the fix does not rely on `gc.collect()`, delayed deletion, retries, or ignored cleanup errors.

## Related tool-boundary lesson

If a search command reports an invalid regular expression, compile the intended pattern independently and inspect the exact transformed pattern in the tool error. A wrapper may normalize backslashes as path separators before the regex engine receives them. In that case, use simpler literal searches or split the query, and do not change repository code to compensate for a caller-layer transformation.
