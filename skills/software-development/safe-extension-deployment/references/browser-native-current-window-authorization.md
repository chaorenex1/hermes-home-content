# Browser-native current-window authorization

Use this reference when a Chromium/Edge browser-provider extension must adopt the user's existing browser window only after an explicit human gesture.

## Security and protocol contract

1. **Treat the extension action as the authorization boundary.** Chromium exposes the `debugger` permission at extension installation and a warning after attach; it does not provide an extension-triggered per-attach Allow/Deny dialog. Never substitute desktop automation for the user's click.
2. **Separate transport enablement from claim authorization.** A connected Native Messaging transport is not authority to inspect or claim tabs. Keep a one-use authorization containing the clicked tab's `windowId` and creation time. Apply a short TTL (for example, 60 seconds), reject missing/expired authorization, and consume it synchronously **before the first asynchronous claim step**. This makes one gesture exactly one attempt and prevents concurrent requests from sharing it; any validation failure requires a fresh click.
3. **Claim exactly the clicked window.** Query tabs by the recorded `windowId`, not by whichever window is focused later. Filter to explicitly supported page schemes (`http:`, `https:`, and optionally `about:blank`); exclude browser-internal pages and Chromium-protected extension galleries even though their URLs use HTTPS (`chromewebstore.google.com`, legacy `chrome.google.com/webstore`, and `microsoftedge.microsoft.com/addons`). Preflight the full candidate set before mutating ownership: reject cross-task owners, duplicates, invalid target metadata, and tab-budget overflow.
4. **Use a task-scoped bridge contract.** A practical layering is a host-only pseudo-CDP method such as `Target.claimCurrentWindow` mapped to an extension operation such as `tabs.claimCurrentWindow`. Return target ID, random logical tab ID, positive generation, active state, and position for every claimed page. Install the returned bindings with an atomic same-task route replacement: first reject any target owned by another task, then revoke stale debugger/window routes for the authorized task and publish the new set. This lets a fresh human authorization recover from MV3 worker/route desynchronization without weakening cross-task isolation.
5. **Distinguish borrowed and created tabs.** Existing tabs adopted from the user's window are borrowed. Session cleanup must detach debugger sessions, delete extension/host ownership, and leave those tabs open. Tabs explicitly created by the agent remain closeable according to the configured lifecycle policy. An explicit user/tool `close` action may still close a selected borrowed tab.
6. **Fail closed after restart.** If a borrowed target or route disappears, require a fresh window authorization. Never silently recreate an existing user tab as an agent-owned tab to repair a stale manifest. A fresh authorization may atomically replace stale routes for the same task, but never routes belonging to another task.
7. **Queue consent events until transport is ready.** An extension-action handler can run before `connectNative()` finishes. Buffer the latest `Hermes.userGesture` event when no native port exists, flush it immediately after the port and listeners are installed, and then clear it. A fire-and-forget post against a null port silently loses re-consent.

## Opt-in automatic authorization

Per-window clicking is the safe default, but some operators explicitly accept installation/configuration as the authorization boundary and want first-use takeover without another gesture. Implement this as an explicit host setting (for example, `authorization_mode: click | auto`), never as an implicit migration:

1. Keep `click` as the default. In `auto`, document that last-focused-window takeover can select the wrong normal window if the operator changes focus at the wrong time.
2. Auto-connect Native Messaging transport independently of tab authority. A connected port alone must not let manual mode claim tabs.
3. Carry the opt-in through the full trusted path: validated profile config → tab manager claim parameters → task-scoped bridge → extension. Reject non-boolean protocol values and keep cross-task route conflicts fail-closed.
4. In the extension, permit a no-gesture claim only when the trusted request explicitly carries the auto flag. Resolve `chrome.windows.getLastFocused({windowTypes: ["normal"]})`, then run the same candidate preflight, protected-page filtering, ownership, budget, borrowed-tab, and cleanup rules as click mode.
5. Browser extension installation permission becomes the human authorization boundary in auto mode. Keep cloud-metadata and exact-origin Native Messaging floors unchanged.
6. After deploying a changed unpacked extension, reload it once from the browser's extension page. A materialized new service worker on disk is not evidence that the browser stopped running the old worker. The post-reload acceptance probe must claim without any extension-action click.

## Fake-IP DNS and inherited SSRF policy

Current-window adoption and page-evaluation policy are separate acceptance gates. TUN/proxy DNS commonly maps public hostnames into reserved ranges such as `198.18.0.0/15`, so a strict `ipaddress.is_global` check can reject every real page even though takeover itself succeeded.

- Keep a strict plugin mode as the default.
- Offer an explicit `inherit` mode that follows Hermes' global private-URL policy instead of imposing a second stricter resolver check. Use the preferred global toggle (`security.allow_private_urls`) rather than inventing a second unrestricted bypass.
- Even in inherited/allow-private mode, preserve the non-negotiable `is_always_blocked_url` floor for cloud metadata and link-local credential endpoints. Apply it both to the current page URL and URL literals decoded from JavaScript expressions.
- Verify the policy independently: a representative public hostname that resolves into the proxy Fake-IP range should pass, while `169.254.169.254` and metadata hostnames must still fail.
- Do not report a claimed window as a failed takeover merely because every borrowed page is separately blocked by evaluation policy. Prove takeover via borrowed-tab bindings and prove transport evaluation with a temporary `about:blank` tab if necessary; close only that created probe tab.

## Stable extension identity

Native Messaging authorization is a three-part identity contract:

- the extension manifest's public `key`;
- the extension ID derived from that key;
- the native-host `allowed_origins` entry.

Verify all three against the **materialized deployed artifact**, not only the source template. A source template can contain the correct key while a long-lived process rewrites the extension directory from stale imported code. After an atomic plugin swap, materialize with a fresh process, reload the unpacked extension, restart the long-lived host, and then verify the observed extension ID and Native Messaging connection.

## Verification ladder

1. RED/GREEN tests for the extension authorization state, claim protocol, bridge binding validation, multi-tab manifest creation, borrowed-tab release, and fresh authorization after stale targets.
2. Materialize the extension and run `node --check` on the generated service worker.
3. Run the focused suite, full suite, package build, source-to-installed digest comparison, and installed plugin version/enabled checks.
4. Perform one real browser acceptance probe from a fresh runtime:
   - start the authenticated broker **before** asking the user to click, and keep it listening longer than the UI round-trip;
   - while waiting, retry only the missing/expired-authorization claim result at a bounded interval; do not consume a click before the broker is ready;
   - ask the user to click the extension action in the intended normal-web-page window;
   - verify the claim returns existing tabs marked `borrowed`, and that protected store/internal targets were excluded;
   - evaluate a harmless constant in an allowed claimed tab; if every existing public page is separately rejected by Hermes' URL/SSRF policy, do not weaken that policy—record the takeover evidence and verify CDP evaluation in a temporary `about:blank` task tab instead;
   - end the session, confirm borrowed tabs remain open, and close only the temporary agent-created probe tab.

An error such as “authorization expired” or “window is not authorized” proves that the real request reached the fail-closed gate, but it is **not** evidence that the successful human-authorized claim path completed. Report that distinction explicitly.

## Pitfalls

- Do not click the extension action with `computer_use`; that defeats the human-authorization requirement.
- Do not treat Native Messaging connectivity or the Chromium debugger warning bar as claim authorization.
- Do not ask the user to click before the acceptance broker is already listening. Human switching time can exceed a short claim TTL; the verifier should wait and consume the next fresh click, not rely on the user returning to the terminal quickly.
- Do not call the newly deployed plugin through an already-running process and assume it loaded the replacement bytes; stale module state can rematerialize an old extension bundle. Reload the unpacked extension after materialization so the browser is not still executing an old service worker.
- On Windows, the native-host executable can remain locked after a probe. Enumerate and stop only the tracked native-host process, verify it is gone, then retry the atomic deployment; do not kill the user's browser.
- Do not close all claimed targets on session teardown. Track provenance (`borrowed` versus agent-created) in the task manifest and map borrowed cleanup to a release operation.
- Do not weaken Hermes URL/SSRF policy merely because a proxy/TUN setup maps public names into a non-global fake-IP range. Keep takeover verification and page-evaluation policy evidence separate, and use `about:blank` only as a harmless transport probe when needed.
- Do not automate silent installation of an unpublished local extension as the normal consumer path. Unpacked loading is a development workflow; store installation is the browser-native consumer workflow, while enterprise force-install policy is a separate administrative model.
