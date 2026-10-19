# Flattening Authoritative File Layouts

Use this reference when a logical lifecycle label (for example, `accepted`) must remain in metadata but should no longer appear as a physical directory.

## Tight reproduction

Create one accepted document through the public write API and assert both sides of the contract:

```python
write("/experiences/direct.md", "direct\n")
assert (root / "experiences" / "direct.md").read_bytes() == b"direct\n"
assert not (root / "accepted").exists()
```

Add a second red test before broadening the root:

1. Create an accepted document, a generated summary, and provider-internal Markdown containing the same search term.
2. Assert default tree/search returns only the accepted document.
3. Assert an exact internal path is rejected by the accepted-path topology validator.
4. Assert an exact generated-summary path remains readable when the API intentionally supports it.

## Why changing one root constant is insufficient

After flattening, the physical root may contain:

- accepted profile files and memory-type directories;
- generated `summary.md` and `detailed-summary.md` files;
- prompts, journals, staging, backups, history, databases, and manifests.

A default recursive scan of that root widens authority and can expose internal Markdown. Default discovery must enumerate allowed accepted roots (profile files plus known memory-type directories), then validate every returned logical path. Generated summary filenames must be filtered from accepted scans, not made inaccessible through their exact summary contract.

## Consumer inventory

Trace and update every code path that converts a logical path to a physical path:

- direct read/tree/search/write tools;
- accepted-document scanners and metadata reconcilers;
- summary source discovery and summary target handling;
- derived-statistics writers;
- transaction prepare/apply/recovery target resolution;
- backup/restore and smoke probes;
- startup reconciliation predicates;
- tests and operator documentation.

Keep `accepted` as a metadata kind or lifecycle state if that semantic distinction still exists. Remove only the redundant physical layer.

## Legacy flattening checklist

Under the profile writer lease:

1. Reject a symlinked legacy root, symlinked descendants, non-regular files, unsupported extensions, and paths outside the accepted topology.
2. Build the complete source→target operation set before moving any file.
3. Read exact bytes for comparison; do not use universal-newline text reads as the collision fence.
4. If a target is absent, atomically move the source on the same volume.
5. If a target is byte-identical, remove only the redundant legacy source and do not rewrite the target.
6. If a target differs, abort before publication and preserve both copies.
7. Verify every target byte-for-byte, remove empty legacy directories bottom-up, and rerun startup to prove idempotence.

Design for interruption between any two moves: a retry must recognize already-published targets and converge without treating them as foreign conflicts.

## Persisted transaction paths

Old transaction rows may contain physical `target_path` values rooted under the removed directory. Active apply/recovery logic should resolve the target from the durable semantic pair `storage_area + logical_path`. Treat a persisted physical path as historical/audit data unless its schema version explicitly guarantees the current layout.

Add recovery fixtures for pending transactions created before the layout change. Verify rollback preserves foreign drift and does not recreate the removed directory.

## Verification set

- focused physical-destination test;
- default tree/search authority-boundary test;
- exact summary access test;
- metadata scan/reconcile test;
- legacy move, identical-duplicate, differing-collision, symlink, and second-start no-op tests;
- pending-transaction recovery test across the old layout;
- full suite, changed-file lint, compile/type checks, and `git diff --check`.
