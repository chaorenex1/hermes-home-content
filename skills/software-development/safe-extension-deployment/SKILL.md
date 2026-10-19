---
name: safe-extension-deployment
description: "Safely deploy a standalone local extension or plugin into a live agent installation with tests, atomic swap, backups, rollback, and runtime verification."
version: 1.0.0
author: Hermes Agent
created_by: agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [deployment, plugins, rollback, sqlite, verification, atomic]
---

# Safe Extension Deployment

## Use when

Use for a locally developed standalone plugin, extension, adapter, or automation package that must replace an installed copy while preserving runtime state and restoring service afterward. This skill is for real deployments, not just copying files into a test fixture.

For Hermes-specific commands, consult the authoritative Hermes documentation and the `hermes-agent` skill. Do not modify bundled or hub-installed skills to capture a local deployment procedure.

## Safety invariants

1. **Keep source and target separate.** Reject a deployment where the source directory resolves to the installed target.
2. **Validate identity before copying.** Require an entrypoint and manifest; validate the manifest's declared name and the target directory name against the expected plugin identity.
3. **Copy through a sibling staging directory.** Validate the staged manifest before replacing the live directory.
4. **Use same-filesystem atomic rename/swap.** Rename the old target to a rollback sibling, then rename the stage into the target. Never delete the only working copy first.
5. **Back up state before the swap.** Back up the existing plugin tree and any controller/state database. For SQLite, use the SQLite backup API rather than a raw file copy so committed WAL state is included.
6. **Verify after the swap.** Re-read the deployed manifest and compare a cryptographic digest to source. On any error after moving the prior target, restore it and remove the incomplete stage. A verifier's exit code is not the gate: require its positive success marker, because a missing-host/no-op path can exit 0 without checking anything.
7. **Do not silently preserve build/test artifacts.** Exclude VCS folders, bytecode, and both common pytest cache spellings: `.pytest_cache` and `.pytest-cache`.
8. **Restore the runtime only after deployment verification.** Stop/drain the service, deploy, verify artifact and backup, ensure the extension is enabled, start the service, and verify the process is healthy.
9. **Prove runtime source coherence.** Matching checkout and installed-file hashes do not prove a long-lived host is executing those bytes. Compare process start time with deployed mtimes, identify the importing process, and require a full restart after replacement. Enumerate every process running the host's serve command before declaring the restart done: a service stop can leave an older tree alive on replaced code and still holding a port. When CLI and host disagree against the same profile, separate home resolution from cached-module source skew before changing paths. See `references/runtime-source-coherence.md` and the stale-tree check in `references/hermes-standalone-plugin.md`.
10. **Preserve an explicit browser authorization policy.** For a browser extension that adopts an existing user window, keep Native Messaging connectivity separate from window-claim authority, release borrowed tabs without closing them, and keep one-use human click authorization as the default. If the operator explicitly requests automatic takeover, expose it as an opt-in profile setting, treat installation/configuration as the authorization boundary, select only the last-focused normal window, and retain task ownership, protected-page filtering, and metadata/SSRF safety floors. Verify the materialized manifest key/ID/allowed-origin triad from a fresh runtime. See `references/browser-native-current-window-authorization.md`.
11. **Deploy a published revision when the task bundles commit, push, and deploy.** Commit and push first, then deploy the committed tree; confirm the remote ref matches `HEAD` (`git ls-remote origin <branch>`) instead of trusting the push output, and cite the commit in the deployment report. The installed plugin tree is not a git repository, so an uncommitted deployment cannot be rebuilt or audited later: source and installed copy diverge with no record of which bytes went live.

## Workflow

### 1. Inspect before changing anything

- Locate the source checkout, installed target, runtime service, manifest, entrypoint, and persistent state files.
- Diff the installed plugin's file set against the source checkout before diagnosing or claiming live behavior: an installed copy can lag the source by whole modules (new modules missing, previously removed ones still present). A finding read from the source tree is a repository finding, not a runtime finding; redeploy and restart before live verification.
- Confirm the plugin is currently detected by the host and record its enabled/version status.
- Check the source worktree before editing. Preserve unrelated changes; do not reset, clean, commit, or push unless the user explicitly asks.
- For an unversioned local plugin (`0.0.0`, no remote/release channel), define “latest” as the selected source tree and compare checkout↔installed relative-path digests. If they are identical, avoid a no-op replacement and restart; prove runtime coherence from process start time, installed mtimes, and a fresh provider smoke instead.
- When the user explicitly requests a rebuildable profile SQLite reset—especially when Windows holds the database open—follow `references/live-sqlite-reset.md`: back up with SQLite’s backup API, terminalize old leases under the writer lock, replace pages in place from a clean current-schema database, then run status before verify.

### 2. Test-first a newly discovered deployment gap

When the current deployment tooling mishandles an artifact or failure mode:

1. Add one focused test that demonstrates the desired externally visible behavior.
2. Run it and capture the expected failure.
3. Make the smallest production change.
4. Re-run the focused test, then the full source test suite.

Examples of deployment behavior worth testing:

- Dry run validates inputs and does not mutate the target.
- The deployed plugin excludes cache directories and bytecode.
- Backup contains the prior plugin and a queryable SQLite state snapshot.
- A post-swap validation failure restores the prior plugin and leaves no stage/rollback directory.

### 3. Make source-checkout tooling deployable without deploying

When the task is to repair deployment tooling but explicitly prohibits a live deployment:

1. Work only in the named source checkout; do not edit the installed plugin to make its own deploy script pass.
2. Put the deployment utility under the source checkout (for example, `scripts/deploy_plugin.py`) and derive its default `--source` from the script location, not from the installed target or current working directory.
3. Make the target default explicit from the host application home plus the expected plugin name. Keep the source/target resolved-path inequality validation.
4. Add fixture-based tests for default resolution and `deploy(..., dry_run=True)` non-mutation. The test must verify that dry run creates neither a stage nor a backup and leaves the target bytes unchanged.
5. State plainly that no deploy command was run. A fixture dry-run is deployment-tool verification, not a live deployment.

### 4. Preflight with a dry run

The deploy command should print at least:

- expected plugin name;
- source and installed manifest digests;
- whether the manifests are the same/different;
- a clear statement that dry run made no changes.

Dry run must validate the source, target identity, manifest, entrypoint, and database path without creating backup or stage output.

### 5. Deploy live

Sequence the dependent actions; do not parallelize them:

1. Check provider/controller status for nonterminal work before stopping or restarting the host. If any durable job is `running`, `claimed`, or otherwise nonterminal, wait for bounded quiescence or explicitly report the deployment blocked; a clean service drain can still terminalize an application job mid-phase. Detect whether the deployment command itself is running under the service being replaced; never ask that process to restart its own parent.
2. Stop or drain the service from an independent control shell and verify it is no longer running. Re-check the provider store after the drain and do not proceed silently if a formerly active job became failed.
3. Run the deployment script, which creates the backup before the atomic directory swap.
4. Record the exact backup path from the command output.
5. Verify the installed manifest digest equals the source digest.
6. Verify the backup plugin exists; open the backed-up SQLite database and run `PRAGMA integrity_check` when applicable.
7. Confirm expected caches are absent from the installed target.
8. Enable the plugin only if it is disabled; do not grant optional privileged tool-override permissions unless the user explicitly requests that capability.
9. Start or restart the service from a shell outside that service's process tree, then independently verify the running process plus the host-reported enabled state.
10. Run provider status/initialization first, then provider integrity verification as a dependent step. Do not parallelize these when status initialization can reconcile derived metadata; a verifier racing reconciliation can report a false transient mismatch. Runtime-process health is not sufficient when an in-flight durable job was interrupted during restart.

### 6. Report compactly with evidence

Use this final format:

1. **outcome** — completed, rolled back, or blocked.
2. **changed files** — only files changed in source.
3. **RED evidence** — command, exit code, expected failure (when behavior changed).
4. **GREEN evidence** — focused tests, full suite, dry-run, and real deployment commands/results.
5. **acceptance mapping / unresolved risks** — source/target separation, backup location and integrity, exact manifest digest match, artifact exclusions, enabled/runtime status, and any deliberately ungranted privilege.

Do not claim an active runtime is healthy solely because the command exited successfully; report the actual runtime status command result.

## Implementation notes

- Prefer a standard-library deployment utility where practical so deployment does not depend on the installed plugin being importable.
- Use a unique timestamp/token for stage, rollback, and backup directory names.
- Keep rollback handling narrow: remove the newly moved target only after a failed post-swap check, restore the prior directory when present, and clean the uninstalled stage.
- Backup folders are operational recovery artifacts. Keep them out of the deployable plugin tree.

## Hermes Memory-Provider CLI Registration

A standalone memory provider can expose `hermes <provider> ...` without a core patch. Hermes discovers CLI commands only for the active `memory.provider` and imports `<plugin>/cli.py` before the provider module.

1. In `<plugin>/cli.py`, expose `register_cli(subparser)` and treat its argument as the already-created `argparse.ArgumentParser` for `hermes <provider>`. Build nested verbs directly with `subparser.add_subparsers(...)`. Also expose `<provider>_command(args)`; Hermes discovers that function and wires it as the handler after `register_cli` returns.
2. Do **not** call `PluginContext.register_command()`, `register_cli_command()`, or a custom registry method from `register_cli`. Those APIs register different surfaces; using them against the argparse object produces an empty top-level command or `AttributeError` during CLI construction.
3. Resolve the active profile inside the handler with `hermes_constants.get_hermes_home()`; do not require a separate `--hermes-home` flag on the host CLI path. Keep a standalone `python -m ... --hermes-home` entry point if it is useful for diagnostics.
4. Add a contract test that constructs a real `ArgumentParser`, adds the provider parser, calls `register_cli(provider_parser)`, and parses at least two nested verbs. This catches registry/parser confusion without loading the host.
5. Test the actual extension boundary in a temporary `HERMES_HOME`: copy the plugin to `plugins/<provider>`, write `memory.provider: <provider>` to `config.yaml`, call `plugins.memory.discover_plugin_cli_commands()`, build the returned parser, and execute a harmless verb such as `status`.
6. Do not hard-code the provider in Hermes core. The generic memory-provider CLI discovery already handles the active-provider gate and relative imports.

## Hermes browser-provider backend completion gate

A standalone browser backend is not complete when its provider class or unit tests pass. Front-load the deployable extension boundary: create the manifest, root registration entrypoint, package entrypoint, and one disposable-`HERMES_HOME` discovery test before spending the remaining budget on platform internals. Then verify provider selection and one real `browser_*` plus tab-lifecycle smoke after the final source edit.

When the requirement is “all browser tools use the user's current window,” interpret it literally: the entire built-in `browser_*` family must route through the adopted attached-CDP target, not merely plugin-owned `browser_tabs` and `browser_eval`. Disable automatic isolated-sidecar routing for that provider, make the page-tool pre-hook return a block directive on binding failure, and verify post-action DOM/URL state in a temporary agent-created tab. See `references/browser-native-current-window-hardening.md`.

Keep plugin discovery and registration side-effect free. Defer extension materialization, native-host registration, bridge startup, and browser setup UI to one idempotent first-use path reached by provider session creation, custom browser handlers, and pre-tool hooks. Test registration and first-use behavior independently.

When removing browser-profile synchronization, delete its full configuration/runtime/protocol/discovery closure rather than only its timer. Move managed fallback to a fresh isolated path so a legacy copied profile cannot be reused; leave legacy artifacts untouched unless destructive cleanup is explicitly authorized.

Important lifecycle constraint: Hermes treats a provider-returned `cdp_url` as an attached CDP backend and does not use the provider's `session_name` as an `agent-browser --session`. Multi-tab or per-task target ownership therefore needs an explicit plugin tool/hook contract and host-path verification; a plausible provider metadata dict is not evidence that tab switching reaches subsequent built-in browser operations.

See `references/hermes-browser-provider-backend.md` for the provider contract, side-effect-free registration with first-browser-operation extension bootstrap, managed-profile/process invariants, multi-tab seam, and final verification matrix. See `references/lazy-browser-extension-and-profile-decoupling.md` for the TDD and migration checklist for lazy setup and complete profile-sync removal. When adopting an existing user window, follow `references/browser-native-current-window-authorization.md` for one-use human authorization, stable extension identity, task-scoped claims, borrowed-tab lifecycle, and the real-browser acceptance gate.

## Reference

- `references/hermes-browser-provider-backend.md` — build and verify local headed CDP browser-provider backends, including multi-tab integration.
- `references/browser-native-current-window-authorization.md` — implement and verify click-default or explicitly automatic current-window takeover, stable extension identity, task-scoped claims, borrowed-tab release, and Fake-IP SSRF policy integration.
- `references/browser-native-current-window-hardening.md` — harden one-use claims, MV3/native route recovery, borrowed-tab cleanup, Windows launcher swaps, and the full built-in `browser_*` → attached-CDP bridge (parameterless commands, shared debugger attachments, event fan-out, fail-closed routing, and real current-window acceptance).
- `references/lazy-browser-extension-and-profile-decoupling.md` — defer extension setup to first browser use and remove profile synchronization without reusing legacy copied-profile artifacts.
- `references/hermes-standalone-plugin.md` — verified command sequence and artifact checklist for a Hermes user plugin deployment on Windows.
- `references/hermes-memory-provider-cli.md` — active-provider CLI discovery, profile resolution, and runtime verification.
- `references/hermes-memory-provider-recovery-and-sdk-upgrades.md` — distinguish provider code, SDK, and profile state; recover file-authoritative stores, clear stale lifecycle markers, and verify SDK upgrades end to end.
- `references/live-sqlite-reset.md` — reset a rebuildable live SQLite control/projection store under Windows open-handle constraints using backup, writer-lock lease terminalization, in-place page replacement, reconciliation, and contamination-safe verification.
- `references/model-tool-contract-release-gate.md` — exact public-name, schema-language, full target-registry, line-operation, installed-parity, and fresh-agent acceptance matrix for model-facing plugin tools.
- `references/runtime-source-coherence.md` — diagnose CLI/host disagreement caused by cached plugin code, fail-open initialization, or side-effectful discovery; includes fresh-session host acceptance, safe external restart, Host Agent API compatibility, durable-queue recovery, deterministic probes, and regression tests.
