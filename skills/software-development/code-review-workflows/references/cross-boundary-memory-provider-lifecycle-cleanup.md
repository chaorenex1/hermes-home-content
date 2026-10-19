# Memory-provider lifecycle cleanup review probes

Use these probes when a plugin/provider registers global routes before completing its own lifecycle.

## Transactional registration invariant

Treat `register(ctx)` as a transaction, not an all-or-nothing call. A provider may:

1. register one or more global handlers successfully;
2. fail on a later registration or configuration statement;
3. fall back to another discovery/instantiation path;
4. later fail initialization.

Ownership metadata attached only after `register(ctx)` returns successfully is insufficient. The loader must retain the collector while the call is in flight and compare-and-deregister every handler it accumulated when registration raises, returns without a provider, or otherwise abandons that provider instance. Cleanup should use handler identity so it cannot delete a newer replacement.

## Verify the review artifact before reviewing it

When the user names a patch file as the review subject, hash it first (`sha256sum <patch>`) and read it end to end before forming findings. Report the digest in the verdict so a swapped or truncated artifact is detectable. If the user supplied an expected hash, a mismatch is itself the first finding — stop and report rather than reviewing the wrong bytes.

## Rollback-chain (tombstone) semantics

Once a registry supports restoring a *previous* entry on rollback, review the chain, not just the single step:

- **Identity, not handler equality, defines ownership.** Two registrations can share one handler callable; compare-and-delete must key on the entry object (`current is not expected_entry`), otherwise a rollback can delete a newer registration that reused the same handler.
- **Abandoned entries must stay tombstoned.** When a newer binding is active at rollback time, the older entry must be recorded as abandoned so a later rollback of the newer binding cannot resurrect it as its predecessor. Rollback must walk the predecessor chain, skipping any entry already in the abandoned set.
- **The chain walk needs a cycle guard** (`seen` set) — a malformed or cyclic lineage must terminate by restoring nothing, not loop.
- **Hashability prerequisite:** if entries are used as dict keys or set members (lineage map, tombstone set), verify the entry class does not define `__eq__`/`__hash__` in a way that breaks identity semantics. A plain class with `__slots__` and no `__eq__` keeps identity hash — that is the safe shape; a dataclass with `eq=True` would silently collapse distinct entries.

## Exception-type swallowing at loader boundaries

A cleanup-specific exception (e.g. `MemoryProviderToolCleanupError`) raised intentionally to signal "rollback failed, keep retry metadata" is still an `Exception` subclass. Any broad `except Exception: return None` wrapper in the load path will swallow it and lose the quarantine signal. The loader must re-raise the cleanup type *before* the generic handler (`except MemoryProviderToolCleanupError: raise` ahead of `except Exception`). Check every `try` in the load/initialize path for this ordering.

## Cleanup-failure quarantine pattern

When route cleanup itself fails, the safe shape is:

- the failed provider is removed from all routing/maps immediately (fail closed — never re-advertised);
- the provider is appended to a pending-cleanup list exactly once (identity check to avoid duplicates);
- the exception propagates (caller sees initialization failed);
- a retry pass runs at shutdown, re-clearing the list first so a retried failure re-appends and logs rather than silently dropping ownership.

Review the retry pass for: list-snapshot-before-clear, per-provider try/except that re-appends on failure, and error-type-only logging (no exception payloads with potential secrets).

## Focused regression shape

Build a temporary provider that:

- calls `ctx.register_tool(...)` successfully;
- raises immediately afterward;
- exposes a fallback `MemoryProvider` subclass whose `initialize()` also raises.

Load it through the real provider loader, add the returned provider to the real manager, invoke initialization, and assert both:

- the failed provider is absent from the manager; and
- the global registry has no entry for the registered tool.

A test where `register(ctx)` completes normally and only `initialize()` fails does not cover partial-registration rollback.

Complementary registry-level cases worth requiring:

- repeated registration of the same name followed by failure rolls back to the *original* pre-registration state, not an intermediate handler;
- a same-toolset replacement that fails restores the exact previous live handler (dispatch returns the original result);
- overlapping failed registrations: rolling back the older entry first leaves the newer active entry untouched, and the newer rollback then removes the route entirely;
- availability inspection (`discover_*`) must not register tools at all — assert the global registry has no entry after inspection of a provider whose `register(ctx)` binds one.

## Companion-patch reproducibility without mutating the checkout

When the worktree contains the intended unstaged Host changes and the index is the clean base:

```bash
git apply --check --cached /path/to/companion.patch
git diff -- path/one.py path/two.py | git patch-id --stable
git patch-id --stable < /path/to/companion.patch
```

The apply check proves the patch applies to the indexed baseline. Equal stable patch IDs prove the artifact represents the focused current diff. Also run `git diff --check` on both repositories.

When the patch is already applied to the working tree (a verification pass on a later iteration), confirm the host checkout is at the expected base commit (`git rev-parse HEAD`) and spot-verify that claimed anchor lines exist at the patched locations (e.g. the new `return existing` in `register()`, the new lineage fields in `__init__`). A patch hunk whose context no longer matches the checkout means you are reviewing against the wrong base.

## Atomic registration receipts

Do not infer registration success by reading the registry after `register()` or by comparing handler identity. Both are TOCTOU-prone, and a rejected cross-toolset registration can look successful when the pre-existing entry uses the same handler object. The transaction must return an atomic receipt containing the exact created entry plus its predecessor; cleanup owns only that created entry.

Regression probe: pre-register a tool under a different toolset with handler `h`, attempt a rejected shadow using the same `h`, then assert the collector records no ownership and cleanup leaves the original entry untouched.

## Cleanup failure must quarantine, not merely raise

Retaining rollback metadata and propagating a cleanup exception is insufficient when an outer optional-provider boundary catches the exception and continues. If exact rollback fails, atomically quarantine the expected entry by entry identity so every exposure path hides it: schema snapshots, name/toolset queries, `get_entry`, and direct dispatch. Preserve predecessor/ownership metadata for deterministic retry. A newer rebind must replace the quarantined entry without later restoring it.

Require tests proving:

- quarantine hides the handler and direct dispatch returns unknown-tool;
- retry restores the exact safe predecessor;
- a newer rebind survives cleanup of the quarantined entry.

Provider-manager admission is the same transaction. Rejection of a second provider, schema enumeration failure, route indexing failure, and initialization failure must each undo or quarantine tools registered before admission. Enumerate provider schemas once before publishing manager routes; a second call can fail or return different data.

## Immutable review artifacts

Hash a review artifact at both the beginning and end of a long-running review. If bytes change during review, discard the verdict and restart against the new digest. Prefer a copied/hash-pinned artifact so integration work cannot silently stale the audit.

## Read-only review hygiene

Do not use `python -m py_compile` in a strict read-only review because it can create or refresh ignored `__pycache__` artifacts. Prefer a non-writing parse/compile probe (for example, reading source and calling Python's built-in `compile(...)`) or rely on focused tests that import the modules. Report unavailable linters as a verification limit rather than installing or editing the environment during review.
