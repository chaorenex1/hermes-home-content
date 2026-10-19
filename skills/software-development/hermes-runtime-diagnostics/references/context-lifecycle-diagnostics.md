---
name: hermes-context-lifecycle-diagnostics
description: "Use when Hermes context compression or resume fails."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, context, compression, compaction, sessions, gateway, debugging]
    related_skills: [hermes-agent, hermes-interaction-debugging, systematic-debugging, privacy-safe-observability]
---

# Hermes Context Lifecycle Diagnostics

## Overview

Diagnose Hermes context-window failures without collapsing several independent systems into one verdict. A configured compressor, a reachable summary model, a correct message transform, and a successful live session rotation are separate claims and require separate evidence.

The core distinction is:

```text
trigger policy → summary backend → compaction transform → lease/rotation → durable transcript → next provider request
```

A green unit test or successful auxiliary-model call proves only its own layer. A live Desktop/Gateway session can still fail because its in-memory snapshot, durable transcript, context limit, or owning process differs from the tested path.

## When to Use

Use this skill when:

- `/compress` or `/compact` appears ineffective;
- automatic compression does not fire before provider overflow;
- a session repeatedly reports context length exceeded;
- compressed context is missing after resume;
- Desktop/Gateway behavior disagrees with a direct CLI or source-level probe;
- compression locks, lineage, active/compacted rows, or summary fallbacks need inspection;
- a user asks for a health check of Hermes compression or context lifecycle.

Do not use this skill for generic provider authentication setup without a context symptom; use `hermes-agent` provider troubleshooting instead. Do not edit source or config during a check unless the user also requested a repair.

## Health Layers

Treat each layer as an independent claim.

| Layer | Question | Sufficient evidence |
|---|---|---|
| Trigger policy | Should compression fire before the real provider ceiling? | Resolved context budget, threshold, absolute cap, output reservation, observed provider limit |
| Summary backend | Can the configured auxiliary model return usable content now? | One minimal real call through the compression task route |
| Transform | Does compaction shrink a transcript while preserving invariants? | Synthetic end-to-end `ContextCompressor.compress()` probe |
| Orchestration | Can the owning runtime acquire the session lease and publish a boundary? | Correlated live log + lock/lineage state |
| Persistence | Is the child/in-place transcript durable and resumable? | Active/compacted counts, child lineage, readback after rotation |
| Provider continuation | Does the next request fit and complete? | One post-compaction provider response with real usage |
| Surface | Does the user see the correct session/status? | Owning Desktop/TUI/Gateway state, not a different process |

Never report “compression works” from only one row of this table.

## Evidence-First Workflow

### 1. Bind the Scope

Identify the active Hermes home/profile, session ID, platform, model/provider, and process that owns the interaction. Record whether the check targets CLI, TUI, Desktop, or Gateway.

Completion criterion: every later log row, database row, and runtime probe can be attributed to the same scope. If scope is unknown, report that limitation instead of mixing evidence from different sessions.

### 2. Read the Effective Compression Contract

Use `hermes config get` for behavioral settings; do not hand-edit `config.yaml` while diagnosing.

Inspect at least:

- `compression.enabled`
- `compression.threshold`
- `compression.threshold_tokens`
- `compression.target_ratio`
- `compression.abort_on_summary_failure`
- `auxiliary.compression.provider`
- `auxiliary.compression.model`
- `model.context_length`
- any effective output-token reservation exposed by the running Agent

Compute the nominal trigger only after accounting for output reservation and any absolute threshold cap. Compare it with the **observed provider ceiling**, not the marketing/model-name ceiling.

Completion criterion: state whether the configured trigger is safely below, near, or above the provider limit. If the provider error does not disclose a limit, do not invent one; report the highest observed failing prompt and recommend a conservative bounded probe or explicit cap.

### 3. Probe the Summary Backend

Make one minimal real call through the `compression` auxiliary task route. Verify provider/model, stop reason, and non-empty content. Do not print credentials, request headers, raw provider payloads, or private transcript text.

A successful call proves routing and current reachability. It does not prove summary quality, transcript transformation, or persistence.

Completion criterion: record `provider/model`, success/failure class, and whether usable content was returned.

### 4. Exercise the Transform

Run a synthetic transcript through the real `ContextCompressor.compress()` path with:

- enough messages/tokens to create a compressible middle;
- a small test context budget;
- the configured summary task/model;
- `force=True` so the probe is independent of automatic-trigger timing;
- no real user transcript content.

Verify:

- before/after message and estimated-token counts;
- exactly one current compressed-summary handoff when expected;
- compressed-summary metadata is present;
- role alternation remains provider-valid;
- `compression_count` increments;
- `aborted`, fallback, and error fields are clean;
- no secrets or user content were included in the fixture.

Completion criterion: the transform shrinks materially and all invariants pass, or the exact failing layer is identified.

### 5. Run Bounded Regression Tests

Prefer focused tests that cover manual compression, metadata, focus handling, preflight gates, memory-context handoff, lineage, and lock-skip behavior. A broad `-k compress` sweep can be expensive and may include unrelated meanings of “compressed.”

If a broad run times out, do not count it as passed or failed. Record the timeout and run a smaller named subset to completion. Test logs may intentionally emit synthetic quota/auth/network warnings; correlate test session IDs and timestamps before treating warnings as production incidents.

Completion criterion: at least one named, relevant subset completes with a clear pass/fail result.

### 6. Inspect Live Lifecycle and Durable State

Read only metadata needed for diagnosis:

- session source, parent, start/end state, and message count;
- active vs compacted/inactive message counts;
- compression failure/cooldown/anti-thrash fields;
- compression lock count/holder metadata;
- parent/child lineage and whether a live child is uniquely adoptable;
- correlated log events for overflow, lease abort, rotation, fallback, and post-compression usage.

Do not query or print message bodies unless the user explicitly needs content-level analysis and privacy permits it.

Interpret common shapes:

- **Summary probe passes; transform passes; live session fails** → orchestration, persistence, runtime skew, or stale snapshot.
- **Provider overflows below nominal trigger** → effective context contract is wrong or the threshold is too late.
- **“Changed before lease acquisition”** → fail-closed data-loss protection fired. This is not a successful compression; determine why the caller snapshot was stale and whether the next attempt reloads durable messages.
- **Durable-length abort is silent to callers.** The pre-lease length abort in `compress_context` (`agent/conversation_compression.py`, `durable_parent` length check) returns the input list object WITHOUT setting `_compression_skipped_due_to_lock` and without emitting attempt telemetry. Every caller distinguishes lock-skip via `compression_skipped_due_to_lock(agent)`; a durable-length abort therefore falls into the generic no-op branch: preflight arms the insufficient-progress blocker, and the overflow/413 handlers conclude “Cannot compress further” → `compression_exhausted` → possible gateway auto-reset. If the caller never reloads its in-memory snapshot from the DB, the same abort can re-fire every attempt — a non-progressing safe abort. Audit shape and recovery contract: `references/durable-length-abort-audit.md`.
- **No lock exists now** → only proves no current holder. It does not disprove an earlier race.
- **Active rows remain high; no compacted rows/child boundary** → compression did not commit.
- **Compaction committed; next real prompt remains over threshold** → incompressible system/tool overhead or ineffective summary; inspect real usage and anti-thrash state.

Completion criterion: identify the first layer where evidence changes from healthy to unhealthy.

### 7. Separate Verdict from Repair

For a check-only request, stop after the health matrix and do not silently change thresholds, restart processes, or rotate sessions.

For a repair request, use the smallest reversible intervention:

1. Correct the effective context/trigger contract when it is demonstrably late.
2. Repair stale-snapshot reload/merge or owning-process skew when live rotation is the failing layer.
3. Preserve fail-closed behavior; never bypass lease drift by publishing an older snapshot.
4. Verify one real post-compaction provider response and durable resume.

Completion criterion: every claimed healthy layer has direct evidence, and every remaining risk is explicit.

## Trigger-Safety Rule

The safe trigger must leave room for:

```text
system prompt + tool schemas + preserved tail + summary handoff + requested output + provider variance
```

Therefore `threshold = advertised_context × ratio` is not sufficient by itself. Prefer an explicit `compression.threshold_tokens` when a custom gateway exposes a smaller or variable ceiling than the model metadata. Do not choose an exact cap from a single truncated error; establish a supported provider limit or use a conservative value with a post-change probe.

## Reporting Contract

Lead with one of:

- **Healthy** — every required layer passed, including a live post-compaction request;
- **Partially healthy** — core transform works but one live lifecycle layer fails;
- **Unhealthy** — summary/transform cannot produce a safe handoff;
- **Inconclusive** — missing scope or evidence prevents attribution.

Then provide a compact matrix with evidence and blockers. Distinguish tests from live production/session evidence. State whether any source, config, session, or process was modified.

For a reusable probe recipe and privacy-safe SQL/log checks, load `references/compression-health-check.md`.

## Common Pitfalls

1. **Config-only success.** `compression.enabled=true` proves no runtime behavior.
2. **Aux-only success.** A summary model returning `OK` does not prove compaction or rotation.
3. **Synthetic-only success.** A direct compressor probe bypasses lease, persistence, and frontend ownership.
4. **Mirrored-log overcounting.** The same event may appear in error and stdio logs; count an authoritative stream or deduplicate by timestamp/session/message.
5. **Test-warning confusion.** Failure-path tests deliberately log fake auth, quota, timeout, and malformed-response errors. Exclude the test run’s session/time window before diagnosing production.
6. **Late nominal threshold.** A large configured context window can defer compression beyond a custom gateway’s real ceiling.
7. **Unsafe race “fix.”** Removing the durable-length guard can lose newer messages. Reload or reconcile; never publish the stale snapshot.
8. **No-op ambiguity.** `compress_context` returns the input list object for lock-skip, durable-length abort, breaker/cooldown, empty-transcript refusal, and engine no-op. Only lock-skip sets `_compression_skipped_due_to_lock`; only a real compaction returns a different object. When auditing a no-op, check which abort path fired (log line + flag state) before concluding compression is broken.
9. **Lock-state overclaim.** Zero current locks does not explain earlier lease contention or snapshot drift.
10. **Private evidence leakage.** Report counts, states, and bounded error classes—not message bodies, credentials, endpoints, or raw payloads.
11. **Timeout mislabeling.** A timed-out broad suite is incomplete, not green or red; run a bounded subset to completion.

## Verification Checklist

- [ ] Active profile/session/platform/process scope is fixed.
- [ ] Effective trigger policy is compared with observed provider behavior.
- [ ] Compression auxiliary route returns usable content or a classified failure.
- [ ] Synthetic transform verifies shrinkage, metadata, alternation, and no fallback.
- [ ] A focused regression subset completes.
- [ ] Live logs are separated from test-generated warnings.
- [ ] Durable active/compacted rows, locks, and lineage are checked without message bodies.
- [ ] The first unhealthy lifecycle layer is identified.
- [ ] Verdict distinguishes core health from live-session health.
- [ ] The report states whether anything was modified.
