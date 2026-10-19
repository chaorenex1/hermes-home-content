# Managed Local Browser Provider Lifecycle

Use this reference when a Hermes plugin owns a desktop Chromium process, exposes loopback CDP, copies user browser state into an isolated profile, or maps logical agent sessions to browser tabs.

## Architecture invariants

1. **Never expose browser-wide command-line CDP from the user's live default profile.** Modern Chromium rejects remote-debugging flags on the default data directory, and bypassing that boundary would expose credentials. For a process-owned CDP route, discover the default browser executable and source profile but launch with a distinct managed `--user-data-dir`. If the requirement is to control selected tabs in the existing default profile, use the browser-native `chrome.debugger` companion-extension route in `native-browser-takeover-consent.md`; do not treat its task-scoped bridge as a raw browser-wide endpoint.
2. **Treat the source profile as read-only.** Synchronize only `source -> staging generation -> active/previous`. Never copy back. Do not overwrite the active generation while Chromium is running, and never promote an incomplete staging tree.
3. **Bind CDP to loopback.** Use `--remote-debugging-address=127.0.0.1`, discover the dynamic port from the managed profile's `DevToolsActivePort`, and validate the resulting browser WebSocket URL before publishing it.
4. **Own only the process you launched.** Hold a profile-local interprocess lock. Terminate through the retained process handle after checking ownership metadata; never kill by executable/process name. Graceful plugin shutdown sets a stopping flag before terminating so the monitor cannot relaunch the browser.
5. **Separate logical and physical tab identity.** Persist stable plugin `tab_id` values and remap them to transient CDP `target_id` values after every browser generation. Session ownership must prevent one task from closing another task's tabs.

## Vertical TDD slices

Build these slices one at a time, red then green:

1. Config and profile-local data root resolution.
2. Platform-specific default-browser discovery with injected registry/subprocess/plist readers.
3. Staged profile copy, atomic promotion, and one rollback generation.
4. Minimal CDP request client and loopback endpoint validation.
5. Window minimization through `Browser.getWindowForTarget` -> `Browser.setWindowBounds(windowState=minimized)` -> `Browser.getWindowBounds` verification.
6. Logical tabs: list/open/switch/close, cross-session ownership, limits, and session manifests.
7. Supervisor: launch, health probe, unexpected-exit restart, bounded backoff/circuit breaker, and shutdown suppression.
8. Interprocess owner/attacher behavior. A second Hermes process should reuse a healthy endpoint and must not launch or kill a second browser.
9. Restart recovery: restore URLs/order/active tab while retaining stable logical IDs and replacing CDP target IDs.
10. Plugin packaging/registration: provider, tool, hooks, manifest, entry point, and local discovery.

Include regressions for two lifecycle edge cases:

- A failed restart attempt must leave the monitor able to try again; do not let `process=None` silently stop the retry loop.
- Closing the final logical session should create an unowned `about:blank` keeper before closing its last owned page, so Chromium does not exit merely because the final window vanished.

If the source profile is locked during first-run copying, defer the copy and create an empty managed profile so the provider remains usable; periodic staging can retry later. Log the deferment without logging profile contents, cookies, or complete sensitive URLs.

## Hermes plugin naming and local discovery

Keep three names distinct:

- manifest plugin name, e.g. `browser-system-browser` — used by `hermes plugins enable`;
- Browser Provider name, e.g. `system-browser` — used by `browser.cloud_provider`;
- Python entry point, e.g. `system-browser = system_browser:register`.

`hermes plugins install` accepts Git identifiers/URLs rather than arbitrary local directories. For a local discovery test, copy the checkout to a disposable `<HERMES_HOME>/plugins/<directory>`, enable the **manifest name**, set the provider name in config, and query discovery in a fresh process. Do not test against the active profile.

A directory plugin needs root `plugin.yaml` and root `__init__.py`; a wheel needs the `hermes_agent.plugins` entry point. Include both root files in the sdist manifest. If pytest imports the repository root as top-level `__init__`, make the directory entry point tolerate an empty `__package__` and fall back to the installed package import.

## Disposable end-to-end smoke

Use a temporary `HERMES_HOME` and precreate `system-browser/profiles/active` as an empty directory so the smoke does not copy the user's source profile. Disable profile sync for the smoke.

Verify in one bounded run:

1. discover and enable the plugin by manifest name;
2. resolve the Browser Provider and registered tab tool;
3. launch the actual default Chromium executable headed;
4. confirm `Browser.getVersion` succeeds and window bounds report `minimized`;
5. dispatch tab list/open/switch/close through Hermes' real Tool Registry;
6. terminate the managed browser externally;
7. observe a new healthy CDP endpoint and stable logical tab IDs after restoration;
8. stop the runtime and ensure the temporary directory can be removed.

Do not expose the full CDP UUID or copied profile content in user-facing reports. A loopback host, browser product/version, minimized state, tab counts, and changed endpoint generation are sufficient evidence.

## Packaging acceptance

Run the full test suite after the last edit, then:

- compile package and root entrypoint;
- run `git diff --check`;
- build wheel and sdist without silently downloading new dependencies;
- inspect wheel entry points and archive members;
- assert no bytecode/cache files are packaged;
- assert sdist contains `plugin.yaml`, root `__init__.py`, README, and `pyproject.toml`;
- perform disposable Hermes discovery and real Tool Registry dispatch;
- commit only after the worktree is clean of generated artifacts.

Report native platform coverage honestly. Windows success does not prove macOS/X11/Wayland behavior; pure Wayland window minimization may be unavailable even when CDP navigation works. Copied Chromium profiles may also lose some app-bound encrypted cookies or credentials.
