# Browser-Native Current-Window Hardening

Use this reference when a Manifest V3 extension adopts an existing Chromium window after a human clicks the extension action.

## Authorization invariants

1. Keep transport connectivity separate from claim authority. A connected Native Messaging port is not permission to inspect or control tabs.
2. Bind each user gesture to the exact `windowId` where the action was clicked and give it a short TTL.
3. Consume the pending authorization synchronously, before the first `await` in the claim path. Validation or discovery failure still consumes it. This prevents concurrent requests from sharing one click.
4. Exclude browser-internal pages; claim only explicitly supported web schemes.
5. Reject the whole claim before mutating ownership if any candidate belongs to another task.

## MV3 and route-recovery contract

MV3 workers and native transports can restart independently. Extension-side owner maps and host-side route registries can therefore disagree.

On a fresh human authorization:

1. Validate all returned target/logical-ID/generation bindings first.
2. Preflight every target against routes owned by other tasks.
3. Atomically remove stale routes, debugger sessions, window bindings, and canceled-consent markers for the same task.
4. Install the newly authorized bindings as one replacement.
5. Never allow a fresh claim to replace another task's route, and never leave a partial replacement after conflict.

This makes reauthorization recover from stale same-task routes without weakening cross-task isolation. If seamless service-worker suspension recovery is required, use browser-session-scoped state such as `chrome.storage.session`; do not persist one-use authority across browser restarts.

## Native Messaging user-gesture delivery

`connectNative()` is asynchronous. Calling a fire-and-forget sender immediately afterward can lose the gesture because the port is still null.

- Keep one pending user-gesture event while disconnected.
- Flush it immediately after `chrome.runtime.connectNative()` succeeds and listeners are registered.
- Clear it only after posting.
- Keep this queue bounded; do not turn it into an unbounded backlog of ordinary CDP events.

## Borrowed-tab lifecycle

Tabs adopted from the user's window are borrowed, not created assets.

- Session cleanup detaches debugger sessions and releases ownership without closing borrowed tabs.
- Tabs created by the agent retain the configured close-on-session-end behavior.
- If an explicit `close` operation closes borrowed tabs, document that public contract and test it separately from session cleanup.
- Missing borrowed targets after restart require a fresh human authorization; do not silently recreate them as new tabs.

## Tests that pin the safety model

- One gesture cannot satisfy two concurrent claim requests.
- Reauthorization can replace stale same-task routes even when target IDs are reused.
- Reauthorization cannot replace a different task's routes.
- Borrowed session cleanup emits release, not close.
- A stale borrowed manifest requires fresh authorization and does not create replacement tabs.
- Generated service-worker JavaScript passes `node --check`.

## Built-in `browser_*` routing contract

A plugin-specific `browser_tabs`/`browser_eval` success does not prove that Hermes' built-in page tools use the adopted window. Treat these as separate seams.

1. Select the provider explicitly (`browser.cloud_provider: system-browser`). For a local attached provider, set `browser.auto_local_for_private_urls: false`; otherwise Fake-IP DNS or a private-address classification can silently send `browser_navigate` and all follow-up tools to a `task::local` isolated Chromium sidecar. If current-window-only behavior is required, also keep the provider's managed fallback disabled.
2. Register pre/post hooks for every built-in page tool (`navigate`, `snapshot`, `click`, `type`, `scroll`, `back`, `press`, `get_images`, `vision`, and `console`). The pre-hook must ensure the native route, claim/restore the task session, activate the selected owned target, and serialize attached-CDP interactions.
3. Fail closed in the pre-hook. Return `{"action": "block", "message": "..."}` when current-window binding fails; do not merely raise. Hermes treats plugin hook exceptions as non-fatal and may continue into the core browser tool's local fallback.
4. Switching logical tabs invalidates accessibility refs. Activate first, then take a fresh snapshot before any ref-based interaction.
5. Treat a tool's `success: true` as delivery evidence, not semantic evidence. Verify the resulting URL, DOM state, focus, scroll position, or element value after consequential interactions.

## Agent-browser over `chrome.debugger` compatibility

`agent-browser --cdp` behaves like a general flat-session CDP client, while Chromium's extension debugger API permits only one debugger attachment per tab. The bridge must translate between those models.

- Accept omitted CDP `params` as `{}`. Parameterless commands such as `Page.enable` are valid and may omit the field entirely; reject explicit non-object values.
- Allow only the required target-scoped CDP domains, but ensure the list covers the commands used by accessibility snapshots, input, navigation, screenshots, runtime evaluation, network state, and lifecycle waits.
- Reuse one extension-side `chrome.debugger.attach({tabId})` per owned tab. Multiple `Target.attachToTarget(flatten=true)` calls receive unique bridge session IDs that reference the same extension attachment.
- Reference-count detach: removing one bridge session must not call `chrome.debugger.detach` while another bridge session still uses the underlying extension attachment. Detach only after the last reference or on tab/task release.
- Fan every extension event out to every bridge session sharing the extension attachment, rewriting `sessionId` for each recipient. Sending `Page.loadEventFired` to only the first bridge session causes navigation waits to time out even though `Page.navigate` succeeded.
- An `Inspector.detached` event revokes every bridge session sharing that extension attachment and preserves the user-canceled consent marker when applicable.
- Browser-level lifecycle methods (`Target.*`, `Browser.*`) remain host-handled and task-authorized; target-domain commands require a valid flat session.

## End-to-end current-window acceptance

Run this after the final source edit and from the runtime that will remain active:

1. Verify effective configuration, then restart every long-lived process that caches provider or routing settings. Restarting Gateway does not reload an already-running CLI/Desktop agent process.
2. Claim the intended current window and record the original borrowed-tab set.
3. Create one agent-owned temporary tab in that window, activate it, and run built-in `browser_navigate` followed by a fresh snapshot. Use a normal `https:` test page for broad command coverage; `about:blank` variants can have extension-access edge cases.
4. Build a harmless form in the temporary page, then exercise snapshot, type, press, click, scroll, console/eval, image enumeration, back, and screenshot/vision as applicable. Verify actual DOM values, active element, button/result state, scroll position, URL/history state, and image count rather than trusting command status alone.
5. Confirm provider evidence reports native extension/current-window mode and managed fallback is false. Check runtime logs for absence of `::local` or local-sidecar creation.
6. Close only the temporary agent-created tab, release the session, and prove all original borrowed tabs remain open.

Keep the acceptance broker alive for the whole probe. A disposable smoke process may overwrite the Native Messaging rendezvous and then exit, leaving an older live agent disconnected; either run the probe through the final long-lived runtime or restart that runtime after the probe. On Windows agent-browser, keep JavaScript passed to direct `eval` commands on one line when possible; multiline image-enumeration expressions have produced deterministic `Unexpected end of input` failures even though the equivalent one-line console expression succeeds.

## Windows live-deployment recovery

A running Native Messaging host can lock the installed launcher during atomic replacement.

1. Run the deployment dry-run and confirm source/target identity.
2. Identify the exact tracked native-host process and verify there is no active claimed task.
3. Stop only that process, then run the atomic deployment immediately from the same control shell.
4. Verify installed-source hashes and the enabled plugin version.
5. Materialize the extension from a fresh process importing the installed copy, then verify the manifest key, derived extension ID, and native-host `allowed_origins` still agree.
6. Run a fresh native probe: without a new click it must fail closed; the final success probe still requires the human to click in the target window.
