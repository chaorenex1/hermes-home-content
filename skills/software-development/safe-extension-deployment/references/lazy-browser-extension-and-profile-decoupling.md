# Lazy Browser-Extension Setup and Profile-Sync Removal

Use this pattern when a browser-provider plugin must avoid setup side effects during discovery/registration or must stop copying a user's browser profile.

## Registration-to-first-use migration

1. Trace all setup entrypoints: plugin `register`, provider `create_session`, custom browser handlers, pre-tool hooks, and supervisor `ensure_running`.
2. Add a RED test proving registration advertises providers/tools/hooks without calling initialization, opening browser UI, writing extension artifacts, or registering native hosts.
3. Remove only the eager registration call. Keep one idempotent `ensure_running` path that materializes the extension, registers the native host, starts the bridge, and opens setup UI on the first real browser operation.
4. Verify both halves independently: registration is side-effect free; the first provider/tool operation still performs setup and returns actionable consent instructions when the extension is disconnected.
5. Keep browser-native consent as the authorization boundary; do not replace it with enterprise force-install policy or profile/debug launch flags.

## Removing profile synchronization completely

Build a closure inventory before editing:

- config keys/defaults/validation;
- source-profile discovery fields and OS-specific profile-root lookup;
- snapshot/staging/promote implementations and markers;
- monitor timers, pending snapshot state, restart-time promotion;
- protocol/facade forwarding methods;
- tests, docs, package metadata, and runtime artifact paths.

Delete the whole reachable closure, not only the timer. Retaining `source_user_data_dir`, snapshot protocols, or config knobs leaves misleading capability and privacy surface.

Replace the copy/snapshot manager with the smallest isolated-profile owner needed by an explicit managed fallback: create one dedicated directory and expose only `ensure_active()`.

On upgrades, do not reuse the legacy synchronized `profiles/active` path: it may contain a copied real profile. Point the new fallback at a fresh path such as `managed-profile/`. Leave old `active/staging/previous` artifacts untouched unless the user explicitly authorizes destructive cleanup; ignoring them is reversible and prevents accidental reuse.

## TDD and verification

- RED: assert removed config attributes are absent and registration performs zero initialization.
- RED: pre-create a legacy synced profile and assert the new manager chooses a different empty path.
- GREEN: focused config/profile/provider/supervisor tests.
- Final: full test suite, compile/static check, diff check, and a repository search showing no production references to source-profile, snapshot, staging, promotion, or sync symbols.
- Treat DOM `snapshot` APIs and `async` text as unrelated search hits; classify matches rather than bulk-deleting by substring.
