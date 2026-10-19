---
name: hermes-runtime-diagnostics
description: "Use when Hermes runtime and UI state disagree."
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, debugging, sessions, desktop, compression, events, cdp]
---

# Hermes Runtime Diagnostics

## Overview

Class-level evidence-first diagnostics for Hermes runtime disagreements across durable session state, Gateway/Desktop/TUI interaction lifecycle, context compression, provider continuation, registries, and the live Desktop renderer. Treat backend transition, persistence, event transport, process ownership, and UI rendering as separate claims.

Load `hermes-agent` and consult current Hermes documentation before changing configuration or runtime state.

## Scope First

Fix one active profile, Hermes home, owning process, session/interaction/workflow IDs, provider/model, frontend surface, and runtime revision. Correlate every log/database/UI fact to that scope. Never combine a direct CLI probe from one process with a Desktop claim from another.

## Interaction and UI Branch

Trace user action → handler → durable transition → emitted event → client reducer → rendered owner. Distinguish duplicate request IDs from duplicate mounts, accepted backend state from stale UI, and status events from transcript events. Test exact cardinality, event sequence, and response-to-clear behavior. The backend remains authoritative. See `references/hermes-interaction-debugging.md` and migrated interaction references.

## Context Lifecycle Branch

Separate trigger policy, summary backend, transcript transform, compression lease/rotation, durable persistence, next provider request, and visible surface. A successful auxiliary call or synthetic transform proves only its layer. Inspect privacy-safe metadata, preserve fail-closed drift guards, identify the first unhealthy layer, and verify one real post-compaction continuation before calling the system healthy. See `references/context-lifecycle-diagnostics.md` and migrated compression probes.

## Live Desktop DOM Branch

When source and running Desktop disagree, attach read-only to the app's declared development CDP port. This branch absorbs the former standalone Desktop DOM inspection workflow so runtime disagreement remains discoverable through one Hermes diagnostics class. Select the intended renderer target, project only small DOM/computed-style values, prefer stable `data-slot` selectors, and determine the winning CSS rule before editing. Never relaunch or kill the user's app merely to gain a port. CDP proves rendered facts, not aesthetics. See `references/desktop-dom-inspection.md`.

## Broad Log-Triage Branch

For an unscoped “check the logs” request, resolve the active `HERMES_HOME`, establish the latest owning-runtime startup as the cutoff, inspect the principal log tails together, and corroborate each active signature against current files or runtime state. When the same check request recurs, recover the previous run's baseline from session history and re-verify its claims instead of re-deriving the scope. Treat counts as window-scoped: each log's first-line timestamp bounds what it can prove (rotated/recreated files), and a signature is only 'active' when a re-count during the review shows it still growing. Treat named profiles, Desktop backends, Gateway adapters, MCP processes, and provider stores as separate scopes. Project privacy-safe fields rather than copying raw stdio lines, which may contain connection parameters. Diagnose stale update-marker loops and provider manifest/database mismatches without mutating state. Attribute a flood's emitter before blaming current code: walk the calling shell's parent chain (`cat /proc/$$/winpid`, then a `Get-CimInstance Win32_Process` walk up) to the hosting process and compare its start time against deploy/replace times — long-lived processes keep executing pre-redeploy code from memory, and their tracebacks cite deleted modules while linecache remaps the source lines shown to the current file at those old line numbers. `Hook '<X>' callback <fn> skipped after previous timeout or while still running` means the callback's bounded worker (default 30 s budget, ~60 s post-timeout suppression) is still running or recently timed out; the callback `__name__` identifies the registrant (a bare `callback` = an anonymous registration closure). A stuck worker skips that callback for the life of the process (only a restart clears it); plain suppression self-expires — expect sporadic bursts, and size impact from the callback's downstream output (e.g. persisted-metric lines) rather than assuming total loss. Prevent the class at source: a hot-path callback that performs blocking lock/SQLite work can exceed its bounded budget; each timeout opens the suppression window that silently drops later invocations in that process — bound the callback's blocking waits (short lock/sqlite timeouts, drop best-effort observations) instead of trusting the cap. See `references/log-triage-and-stale-marker-diagnosis.md`.

## Browser Toolset Auth Branch

`browser_*` failing with 403 (e.g. `Forbidden for url: http://localhost:9377/tabs`) while the Camofox daemon still answers `/health` is an auth mismatch, not a dead daemon: POST endpoints require `Authorization: Bearer <daemon CAMOFOX_API_KEY>` (GET stays open). Prove it with an unauthenticated vs authenticated `POST /tabs` (403 vs `{"error":"userId and sessionKey required"}`), read the required key from the daemon's env (`docker inspect <container>`), then append the matching `CAMOFOX_API_KEY=` to `<HERMES_HOME>/.env` (backup first, CRLF). The secret scope rebuilds from `.env` per prompt, so the fix lands on the next prompt in the same process — the current turn keeps its stale binding; do not restart the Gateway for this. A `click` on a slow navigation can return 500 while the action actually succeeded — check the tab URL (`GET /tabs?userId=...`) before reporting or retrying.

Rotating the key requires recreating the container (env cannot change in place): `docker stop/rm` then `docker run -d --name camofox-browser -p 9377:9377 -p 6080:6080 -v "<host>/.camofox:/home/node/.camofox" -e CAMOFOX_HOST=0.0.0.0 -e CAMOFOX_AUTH_MODE=auto -e CAMOFOX_API_KEY=<new> -e CAMOFOX_ALLOW_PRIVATE_NETWORK=true -e CAMOFOX_HEADLESS=virtual <image>`, otherwise replicating the original config (the image bakes PORT/PROFILES_DIR/NODE_ENV; default restart policy is `no`). Verify the daemon across three states (no auth → 403, old key → 403, new key → creates a tab), then rewrite `<HERMES_HOME>/.env` keeping CRLF and prove both sides carry the SAME value by comparing sha256 digests instead of printing the key. A fresh non-interactive probe (`build_profile_secret_scope` + `tools.browser_camofox.camofox_navigate/close`) verifies the client path in the same turn, when the interactive scope is still stale.

## Repair Discipline

For diagnosis-only requests, do not change thresholds, restart processes, rotate sessions, or edit source. For repair, make the smallest reversible change at the first unhealthy layer, restart only the owning process when necessary, and re-run the exact failing lifecycle plus targeted regression tests.

## Profile State and Marker Recovery

When a profile-local provider has a manifest/database mismatch, restore a validated whole-profile archive through the provider CLI rather than copying a loose database; then verify schema, projections, SQLite integrity, and one live provider read. When stale operation markers cause notification polling or log floods, preserve and move the complete marker set with bounded race handling, then prove the matching log count stops growing without restarting the gateway unnecessarily. See `references/profile-state-recovery.md`.

## Verification Checklist

- [ ] One profile/session/process/surface scope fixed.
- [ ] Log emitters attributed to a process generation (start time vs deploy cutoff) before code-level blame; stale long-lived processes flagged for restart.
- [ ] Durable transition and user-visible lifecycle separately verified.
- [ ] Test-generated warnings separated from live incidents.
- [ ] Compression layers reported independently.
- [ ] DOM/CDP inspection targeted the intended renderer.
- [ ] Privacy-safe metadata used; no credentials/message dumps exposed.
- [ ] Owning process and real continuation verified after repair.
