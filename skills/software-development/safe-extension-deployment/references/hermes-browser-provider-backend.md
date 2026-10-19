# Hermes local browser-provider backend reference

Use this reference when a standalone Hermes plugin launches a local headed Chromium-family browser and returns its CDP endpoint through the Browser Provider registry. Re-check the live Hermes source and official docs before implementation; this records stable integration seams and verification gates, not a substitute for current signatures.

## Extension boundary first

A directory plugin needs a valid `plugin.yaml` and root `__init__.py` with `register(ctx)`. A distributable package additionally needs a `hermes_agent.plugins` entry point. For a browser backend, the manifest should declare `kind: backend` and its `provides_browser_providers`; declare any plugin-owned tab tool and hooks too.

User-installed backends are opt-in. Verify both plugin enablement and explicit `browser.cloud_provider` selection in a disposable `HERMES_HOME`; registration in a unit-test fake does not prove discovery or routing.

## BrowserProvider lifecycle contract

Implement the current `agent.browser_provider.BrowserProvider` ABC:

- `name`: stable config key.
- `display_name`: setup/picker label.
- `is_available()`: cheap, side-effect-free check only. Do not launch a browser or make network calls here because discovery and setup UIs call it repeatedly.
- `create_session(task_id)`: start or attach to a healthy browser and return at least `session_name`, legacy key `bb_session_id`, concrete browser `cdp_url`, and `features`.
- `close_session(session_id)`: release the provider session without raising.
- `emergency_cleanup(session_id)`: best-effort process-exit cleanup and must not raise.

A local persistent backend may keep one process per Hermes profile while treating provider sessions as logical tab ownership. Preserve the ABC's cleanup behavior explicitly rather than silently leaking every logical session.

## Lazy native-extension bootstrap

When the backend depends on a local unpublished browser extension, keep plugin discovery and registration side-effect-free. Registration and `is_available()` may construct objects and advertise providers/tools, but they must not materialize extension files, write native-messaging registration, start a broker, or open the user's browser. Discovery can run repeatedly and before the user has chosen the provider.

Route every model-visible browser entrypoint to one thread-safe, idempotent `ensure_running(task_id)` seam. This includes provider `create_session()`, plugin-owned tab/eval tools, and pre-hooks for built-in page tools. The first actual browser operation should:

1. materialize the profile-local extension bundle and native-host artifacts;
2. register the exact browser-family native host;
3. start the authenticated loopback bridge and publish its rendezvous;
4. wait briefly for an already-enabled extension;
5. only when still disconnected, open the browser-native extensions page at most once and fail the triggering operation with the exact unpacked-extension path and consent instructions.

Keep the bridge alive after this expected incomplete-setup result so a later tool call can connect without re-registering. Mark the install page as opened only after the opener succeeds, allowing a later browser operation to retry a transient launch failure. If the extension is already connected, never open the install page. Preserve an explicit setup CLI for operators and dry runs, but do not call it implicitly from registration.

Use a vertical regression fence:

- RED: register against a fake runtime whose `initialize()` counter must remain zero; confirm the old eager implementation fails this test.
- GREEN: verify registration still publishes the provider, tools, and hooks.
- First-operation path: call `ensure_running()` with an injected disconnected bridge and assert materialization, native-host registration, one install-page open, exact-path error, and idempotent bridge startup; separately cover an already-connected bridge.
- Run the full suite, syntax checks, and `git diff --check`, and update user-facing install timing text.

Do not merely catch and log eager setup failures during registration. That still performs the forbidden side effects and moves user consent to discovery time rather than the first explicit browser operation.

## Pip-free copied-plugin native-host launcher

When a directory plugin is installed by copying into `$HERMES_HOME/plugins/<name>` rather than by installing a wheel, generate the native-messaging launcher inside the staged plugin directory before the atomic swap. On Windows, `pip._vendor.distlib.scripts.ScriptMaker` can produce the required `.exe` launcher without installing the package; on POSIX it produces the executable script. A stock entry-point wrapper is insufficient: when Chromium launches it from an unrelated working directory, the copied plugin root is not necessarily on `sys.path`. Embed bootstrap code that inserts `Path(sys.argv[0]).resolve().parent` before importing the native-host module, and verify the launcher after the staging directory has been renamed to its final target.

Keep the package `__init__.py` lazy enough that importing the native-host submodule does not eagerly import Hermes-only provider modules. Prefer the plugin-local launcher in runtime resolution before PATH/adjacent-interpreter fallbacks. The acceptance smoke must launch it from an unrelated working directory under the installer-selected Python, require the expected no-origin exit, and then verify disposable-`HERMES_HOME` plugin discovery. Preserve the prior copied plugin under a verified backup outside `$HERMES_HOME/plugins`; Hermes recursively scans category-depth plugin directories, so a backup containing `plugin.yaml` under `plugins/.backups/<name>` can be discovered as a duplicate plugin and then removed or enabled by plugin-management commands. Exclude tests, VCS data, caches, bytecode, and build artifacts. On Windows, if the live process holds a directory handle that blocks whole-directory rename, permit a bounded in-place fallback only after the external backup hash-verifies; replace files atomically one by one, delete stale files, verify the full target tree, and restore from backup on any failure.

## Critical attached-CDP seam

In current Hermes `tools.browser_tool`, a session carrying `cdp_url` is invoked through `agent-browser --cdp <url>`. Hermes intentionally does **not** combine `--cdp` with `--session`; recent `agent-browser` versions otherwise create a local browser and ignore the attached endpoint.

Consequences:

1. Do not treat provider `session_name` as proof of per-task tab isolation.
2. If the existing model-visible browser tools do not expose tab lifecycle, register one bounded plugin tool such as `browser_tabs` with closed actions `list|open|switch|close`.
3. Before a built-in page operation, activate the task's owned target. If pre/post hooks are used to serialize target activation around the built-in call, test the real hook dispatcher and guarantee lock release on every error path.
4. Switching targets invalidates accessibility snapshot refs. Return that fact explicitly.
5. Exercise the real wrapper: open two tabs, switch, run `browser_snapshot` or `browser_navigate`, and prove the operation reached the selected target. Raw CDP unit tests alone do not close this seam.

`agent-browser tab` supports stable tab IDs inside its own session model, but attached-CDP routing still needs host-path verification; do not infer Hermes task isolation from the CLI feature list.

## Managed profile and CDP security

Chrome 136+ ignores `--remote-debugging-port`/`--remote-debugging-pipe` against the default Chrome data directory unless a non-standard `--user-data-dir` is provided. Launch a dedicated managed profile. Reference: <https://developer.chrome.com/blog/remote-debugging-port>.

Required invariants:

- Resolve the active profile home through `get_hermes_home()`; never hard-code `~/.hermes`.
- Keep plugin code under the plugin directory and runtime data under a dedicated profile-local root.
- Bind remote debugging to loopback only; validate any returned WebSocket URL before storing or connecting.
- Use an interprocess lock so concurrent Hermes processes attach to one profile-owned browser instead of launching competing writers.
- Track process ownership by more than a process name. Stop only the run-owned process/profile.
- Remove a stale `DevToolsActivePort` before launch, wait boundedly for the new file, and verify the browser endpoint with a real CDP command.

Do not promise that copying files preserves every authenticated session. Windows App-Bound Encryption, macOS Keychain, and Linux secret stores can make cookies or credentials non-portable even when a file copy succeeds.

## Safe periodic user-data import

Never copy into the profile that a live browser is using. Use generation directories:

```text
profiles/active
profiles/previous
profiles/staging/<generation>
```

Copy source data one-way into staging, exclude locks and volatile caches, write a completion marker, and leave `active` untouched. Promote only after the owned browser has fully exited: rotate `active` to `previous`, move the complete staging generation to `active`, and roll back if the second move fails. A source browser can hold SQLite/LevelDB files; a failed or partial staging copy must not be promoted.

Keep logical tab manifests outside the browser profile so a promoted user-data generation does not erase tab ownership or recovery metadata.

## Headed minimization

Prefer the browser's own CDP Browser domain:

1. `Target.getTargets` or `Target.createTarget`.
2. `Browser.getWindowForTarget`.
3. `Browser.setWindowBounds` with `windowState: minimized`.
4. `Browser.getWindowBounds` and require the observed minimized state.

The window APIs are experimental, so preserve `--start-minimized` and an OS-specific owned-window fallback where strict Tier-1 support requires it. Verify real Windows, macOS, Linux X11, and Linux Wayland runs rather than claiming parity from mocked platform detectors.

## Restart and shutdown state machine

Use one bounded supervisor:

```text
stopped -> starting -> healthy -> backoff -> starting
                         |
                         +-> stopping -> stopped
```

- Browser death while Hermes owner is alive triggers exponential backoff with a failure-window circuit breaker.
- Hermes shutdown sets the stopping flag and stop event before terminating the browser; cleanup must not race into a restart.
- A non-owner process may attach to the owner endpoint, but takeover and endpoint refresh must be tested against the host's cached browser-session behavior.
- Persist only bounded operational state. Redact CDP URLs in logs and never log cookies, page bodies, or profile secrets.

## Vertical TDD and final verification

Useful deterministic slices:

1. fixed profile-local data root and config validation;
2. default-browser discovery per OS using injected registry/command readers;
3. staging copy leaves active untouched, then atomic promote/rollback;
4. real RFC6455 request against a local fake CDP server;
5. stable tab IDs, ownership, close-last replacement, and restart remapping;
6. unexpected exit restarts while shutdown suppresses it;
7. two supervisors share one interprocess owner;
8. provider metadata and cleanup semantics;
9. real plugin discovery, registry selection, and tool/hook registration.

Before reporting completion, run the gates **after the final source edit**:

- focused tests and complete project suite;
- syntax/static checks and `git diff --check`;
- build the wheel and inspect archive members for manifest/package data and excluded caches;
- disposable-`HERMES_HOME` plugin install/enable/list plus explicit provider selection;
- host-level create/close session smoke;
- real headed default-browser launch, loopback CDP health, minimized-window verification;
- two-tab switch followed by a built-in browser operation on the selected tab;
- external browser termination followed by bounded automatic restart and tab recovery;
- Hermes shutdown followed by proof that no restart occurred.

Do not spend the final tool budget only on internal modules. Checkpoint the manifest, root entrypoint, package metadata, and discovery smoke early so a forced stop cannot leave a collection of green components that is not yet a loadable plugin.
