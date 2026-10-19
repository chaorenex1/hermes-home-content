# Retiring an Obsolete Lifecycle Mode

Use this checklist when one trigger/worker architecture replaces another, such as moving from delayed or idle scheduling to per-event processing.

## 1. Prove the replacement boundary first

Add failing behavior tests before deleting production code:

- the new public class or callback exists;
- old scheduler/public symbols do not exist;
- the former trigger no longer creates checkpoints or work;
- the new trigger remains non-blocking and reaches the worker;
- unrelated queue overflow cannot suppress the new work path.

Negative API assertions are useful here. After bulk renames, reread them: a blind replace can turn `not hasattr(old_name)` into `not hasattr(new_name)` and create a contradictory test.

## 2. Remove the whole runtime topology

Inventory and delete all of these, not only the old entry hook:

- scheduler/checkpoint classes and serialization;
- timer construction, arming, cancellation, and callbacks;
- worker thread fields, names, startup methods, and shutdown joins;
- old callback kwargs and instance fields;
- retry/backoff limits and persisted states owned only by the old mode;
- new-input/session-switch cancellation logic specific to delayed work;
- generated build directories containing stale source copies.

Rename any still-valid general pipeline or test whose name encodes the retired mode. Do not leave a compatibility alias for a public runtime type that is supposed to be gone.

## 3. Migrate persisted configuration safely

Keep deprecated key names only in a small migration set. Normalize both paths:

1. On load, remove deprecated nested keys before unknown-key validation.
2. On save/update, strip those keys before merge and validation.
3. Write the normalized effective config atomically so the next read contains no deprecated fields.
4. Preserve unrelated nested values.

If a surviving setting has a new owner, wire it there and test its observable effect. Example: a former scheduler `queue_limit` may now size the per-event worker queue.

## 4. Distinguish similarly named subsystems

Do not remove every occurrence of words such as `idle`, `retry`, or `scheduler`. Verify ownership. Temporary-context idle expiry, finite-loop retries, and unrelated periodic observers may remain valid even when long-term-memory idle extraction is removed.

## 5. Replace obsolete tests, do not merely delete coverage

Delete tests that only freeze the retired implementation. Rename and retain tests for still-valid behavior such as evidence redaction, quarantine, bounded rounds, provenance, and safe output validation. Add a legacy-config normalization regression.

## 6. Verification

Run, in order:

1. focused absence/migration tests;
2. focused new-worker and pipeline tests;
3. the full suite;
4. `git diff --check`;
5. syntax/type/build checks used by the project;
6. a final repository search for old symbols, callback names, test filenames, and generated copies.

Remaining old names should be limited to explicit migration keys and negative assertions proving the removed API stays absent.
