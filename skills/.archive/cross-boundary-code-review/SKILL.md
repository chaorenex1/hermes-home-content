---
name: cross-boundary-code-review
description: "Use when reviewing fixes across plugin/Host boundaries."
version: 1.0.0
metadata:
  hermes:
    tags: [code-review, security-boundaries, concurrency, integration-testing, deployment]
    related_skills: [requesting-code-review, systematic-debugging, lifecycle-concurrency]
---

# Cross-Boundary Code Review

Review changes whose correctness depends on behavior outside one function or repository:
plugin/Host integrations, middleware-carried authority, tool registries, lifecycle hooks,
concurrent generators, companion patches, and installers.

## Trigger

Use this skill when a fix changes any of the following:

- a plugin exposing Host-owned tools or nested agents;
- authorization metadata carried through middleware, context variables, or dispatchers;
- a concurrency gate, worker pool, cancellation, or shutdown path;
- a companion patch that must be applied to another checkout;
- installer, backup, replacement, dry-run, or restart guidance;
- a security test that manually injects trusted context.

Use the general `requesting-code-review` skill for ordinary pre-commit checks. Apply this
skill as the deeper integration pass.

## Review Workflow

### 1. Establish review-only scope

If the user requested an independent review, do not edit, auto-fix, stage, commit, or
create repository artifacts. Read the diff, inspect necessary surrounding code, execute
read-only verification, and report findings with exact `path:line` references.

### 2. Pin the review target to the right worktree

When the parent task says \"review the current post-fix diff\", FIRST locate which
checkout carries the fix:

```bash
git worktree list
git -C <candidate> diff --stat -- <named files>
```

Subagent sessions usually land in the PRIMARY checkout (e.g.
`C:\...\hermes\hermes-agent`), while the fix may be in a linked worktree
(e.g. `.worktrees/kanban-review-handoffs`). Reviewing the primary tree against a
worktree fix yields inverted verdicts (\"ACP fields still present\" when already removed).
Confirm the named files exist and the diff matches the described fix before proceeding.

### 3. Trace the complete capability path

Follow the operation end to end:

1. schema or capability registration;
2. toolset or route selection;
3. Host/Plugin boundary;
4. every sequential and parallel dispatcher — when a patch injects context/authority
   kwargs into tool dispatch, grep for EVERY reachable `handle_tool_call(` / `dispatch(`
   callsite, including secondary routers (background-review routers, image/side-channel
   routers). Patching only the primary memory/registry branches leaves the same
   authority gap open on the unpatched sibling branches;
5. metadata/context propagation;
6. final authorization check;
7. protected operation.

Do not accept a downstream guard until every upstream route demonstrably supplies the
trusted context it expects.

### 4. Test absent and malformed authority

For authorization metadata, inspect all three states:

- valid and authenticated;
- malformed or stale;
- absent because a companion patch, middleware layer, or context propagation step is
  missing.

The absent case must not silently become authorized. If compatibility requires an
external Host patch, initialization or installation should verify that capability before
exposing the dependent operation.

Treat every model-reachable fan-out capability as another authority boundary. A nested
Agent may call a delegation tool whose child executes in one or more fresh executor
threads. Trace ContextVars and fail-closed approval policy through the child constructor,
batch executor, per-child executor, and any background dispatcher; construction under the
right context does not prove that `child.run()` inherits it. If propagation is not
explicit, test whether the child can reach an arbitrary-code tool or a dangerous shell
operation after the policy silently returns to its default value.

For JSON-carried authority or correlation envelopes, require strict normalization rather
than merely a successful `json.dumps` round trip: reject NaN/Infinity, non-string nested
keys, silent key collisions, and unbounded payloads. Validate and serialize one immutable
snapshot; walking an arbitrary `Mapping` and later calling `dict(value)` is a TOCTOU gap.
Prefer concrete JSON containers or a recursive one-pass snapshot.

A fresh `contextvars.Context()` also clears host-owned profile/home overrides. Reinstall
the active profile home inside the isolated run while deliberately clearing session,
delivery, and approval state. A session-row `profile_name` label is not runtime profile
binding; validate profile IDs through the Host's canonical profile contract.

### 5. Audit transactional registration lifecycles

Treat plugin/provider registration as a transaction. A `register(ctx)` call can bind one
or more global routes and then raise before returning the provider or attaching ownership
metadata. Review every abandonment path: rejected admission, schema enumeration/indexing
failure, registration exception, no provider returned, fallback instantiation,
initialization failure, and shutdown failure.

Do not infer success from a post-registration registry read or handler equality. Require an
atomic registration receipt containing the exact created entry and predecessor; a rejected
shadow can reuse the pre-existing handler and otherwise look successful. Roll back by exact
entry identity. If rollback itself fails and an outer optional-provider boundary continues,
quarantine that entry across schema/name queries and direct dispatch while preserving retry
metadata. A test where registration succeeds and only initialization fails does not cover
partial-registration leakage.

### 6. Review deployment as part of security

A companion patch is part of the security boundary, not optional documentation.
Verify that the primary/default install path:

- links to and applies or checks the patch;
- identifies compatible upstream versions or uses `git apply --check`;
- requires process restart when modules are resident;
- fails closed when the patch is absent;
- explains replacement and backup behavior.

Documentation hidden in an unreferenced subdirectory does not secure the default path.

### 7. Audit concurrency invariants

Check the invariant at every layer, not only the local pool size:

- Is the semaphore shared by every caller that claims to share a budget?
- Can wrapper replacement temporarily create two independent budgets?
- Does shutdown wake or strand waiters?
- Are cancellation and sibling failures bounded?
- Can a same-path write change content while a filename-only snapshot remains equal?

For generated summaries or indexes, fence content with hashes, revisions, or a suitable
lock. A path-list comparison cannot detect same-path mutation.

### 8. Demand integration-grade regression tests

A security unit test that manually passes a trusted envelope proves only the guard. Add
or require tests that exercise:

- the public/nested caller through the real Host runner;
- sequential and parallel dispatcher paths;
- missing, malformed, stale, and valid context;
- an attempted protected operation;
- shutdown/cancellation overlap where relevant;
- concurrent same-path content mutation;
- installer dry-run output versus actual destination/backup behavior.

### 9. Audit tool-schema trust boundaries

For any fix that removes a dangerous parameter from a model-facing tool, verify ALL
four layers — removing the schema key alone is insufficient:

1. **Schema** — the key is gone from every model-visible schema (static schema AND
   any `dynamic_schema_overrides` builder). Grep the serialized schema text, not just
   the diff hunks.
2. **Registry handler** — the model-dispatch lambda no longer forwards the key to the
   implementation function.
3. **Strip function** — nested/per-task arrays (e.g. `tasks: [{...}]`) have a
   `_strip_model_hidden_*_fields`-style guard with the key in the hidden set, so a
   model cannot smuggle the parameter inside a nested object the schema still allows.
4. **Trusted path preserved** — the implementation function's Python signature still
   accepts the parameter, and operator/config callers (CLI flags, config files,
   host-constructed kwargs) still reach it. Removing the parameter from the
   implementation breaks legitimate operator use and is a regression, not a fix.

Also check every model-facing dispatcher (e.g. an `AIAgent._dispatch_<tool>` method
in the agent runtime that bypasses the registry lambda) — each dispatch site needs
the forwarding removal too.

See `references/tool-schema-trust-boundary-review.md` for a worked recipe with
verification commands.

### 10. Verify without overstating

Run focused tests, non-writing syntax/compile checks, and diff hygiene checks. In a strict
review-only task, avoid `python -m py_compile` because it can create or refresh ignored
`__pycache__` artifacts. Attempt the full suite when practical. If collection, baseline,
or tool-availability problems block a check, report the exact command and exit code
separately; do not convert focused green tests into a whole-suite claim.

For a companion patch represented by unstaged Host changes over a clean index, hash the
artifact before reading it and again before issuing the verdict; any drift invalidates the
review. Then verify it without mutating the checkout: run `git apply --check --cached
<patch>`, and compare `git patch-id --stable` for the focused Host diff and artifact. Equal
IDs prove the artifact represents the reviewed diff; the cached apply check proves it
applies to the indexed baseline.

Dirty worktree variant: when the Host worktree carries the patch PLUS unrelated changes,
the whole-worktree `patch-id` will NOT match the artifact — do not report that as a patch
mismatch. Prove containment instead: `git apply --check --reverse <patch>` succeeds only
when every hunk of the patch is already present in the worktree (subset proof); combine it
with `git apply --check --cached <patch>` to show the artifact still applies to the
indexed baseline. Alternatively, diff only the patch's files and compare `patch-id` on
that focused diff.

Before trusting either check, locate the real Host source root and confirm the target
revision: `pip show hermes-agent` reports the Location (on this Windows host,
`%LOCALAPPDATA%\hermes\hermes-agent`), and `git rev-parse HEAD` there must equal the
upstream revision the patch was cut against. Verifying against a different checkout or
revision proves nothing about deployment safety.

## Finding Format

Order findings by severity. Each finding should contain:

- severity and concise title;
- exact `path:line` location;
- the reachable failure or exploit path;
- why existing tests do not cover it;
- the smallest safe remediation direction.

Then list commands actually run, exit codes, and unresolved verification limits.

## Pitfalls

- Reviewing only changed lines and missing the dispatcher that controls reachability.
- Treating a manual companion patch as safely installed without a runtime/preflight check.
- Assuming ContextVars cross thread pools without an explicit propagation test.
- Calling a tool "read-only" because writes are rejected after exposure; the fail-open
  behavior when metadata is absent still matters.
- Checking source filenames after generation but not source hashes.
- Trusting dry-run text without comparing it to the real branch.
- Tracking registered handlers only after `register(ctx)` returns; partial registration
  can leak routes before ownership metadata is attached.
- Running verification commands that write ignored caches during a strict read-only review.
- Auto-fixing during an independent review-only request.
- Reviewing a patch artifact without hashing it first; report the SHA-256 in the verdict.
- Accepting single-step rollback; predecessor chains need tombstones, a cycle guard, and
  entry-identity (not handler-equality) ownership — plus a hashability check when entries
  are dict keys/set members.
- Letting a broad `except Exception` swallow a cleanup-specific exception that carries
  retry/quarantine semantics; the specific type must be re-raised first.

## References

- `references/security-context-propagation.md` — condensed review probes for Host-carried
  plugin authority, companion patches, and read-only nested-agent boundaries.
- `references/memory-provider-lifecycle-cleanup.md` — transactional registration rollback,
  focused leak reproduction, companion-patch identity checks, and read-only verification hygiene.
