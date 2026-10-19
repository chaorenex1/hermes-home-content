# Native Browser Takeover Consent

Use this reference when a user asks Hermes to take over the already-running default Edge/Chrome profile and explicitly requires the authorization to appear as browser-native UI.

## Establish the authorization surface first

Before any takeover test, distinguish these non-equivalent surfaces:

1. chat/tool approval;
2. a plugin-created HTML or localhost consent page;
3. an extension popup/page;
4. Edge/Chrome's own extension-permission or active-debugging UI.

If the user requires (4), never substitute (1)-(3), and never click the native approval or revocation control on the user's behalf. The human decision is the acceptance evidence. If an incorrect synthetic consent tab was opened, close only that tab and remove its temporary server/files before continuing.

## Remote-debugging switches do not provide native consent

`--remote-debugging-port` and `--remote-debugging-pipe` do not produce an Allow/Deny takeover prompt. Since Chrome 136, both switches are ignored for the default Chrome data directory unless a non-standard `--user-data-dir` is supplied. A process command line may retain a remote-debugging flag while exposing no `DevToolsActivePort`, loopback listener, `/json/version`, or attachable WebSocket; verify the endpoint, not the argv.

Do not close/relaunch a user's browser merely to repeat the same attach attempt after both the profile marker and loopback-listener probes show no endpoint. A managed non-default profile remains the safe command-line CDP route.

Source: https://developer.chrome.com/blog/remote-debugging-port

## Native default-profile route: companion extension

The browser-native route for an existing default profile is a companion extension using `chrome.debugger`:

- declare the required `"debugger"` permission;
- address the exact page by `tabId` or `targetId`;
- call `chrome.debugger.attach(...)` and `chrome.debugger.sendCommand(...)` for allowed CDP domains;
- route events per debuggee/session;
- detach immediately on user cancellation, tab closure, DevTools takeover, or host shutdown.

`chrome.debugger` supports domains including Runtime, Page, DOM, Network, Input, Target, and others, but intentionally restricts the full CDP surface.

Source: https://developer.chrome.com/docs/extensions/reference/api/debugger

## What Chromium can and cannot prompt for

The `debugger` permission cannot be declared in `optional_permissions`. Therefore Chromium cannot show a fresh native optional-permission Allow/Deny prompt before every attach.

The realizable native consent model is:

1. browser-native permission warning/approval when the extension is installed or enabled with the required `debugger` permission;
2. browser-native active-debugging indicator/revocation surface while attached;
3. user cancellation reported through `chrome.debugger.onDetach` with `reason = "canceled_by_user"`.

A requirement for a browser-native Allow/Deny dialog before every attach is unsupported by current Chromium APIs. Do not fake it with a webpage. If per-takeover pre-authorization is mandatory, an extension-owned popup can ask first, but label it accurately as extension UI, not browser-native permission UI.

Source: https://developer.chrome.com/docs/extensions/reference/api/permissions

## Hermes integration shape

A Browser Provider that must keep the existing default profile needs a transport bridge rather than a raw remote-debugging port:

```text
Hermes tools
  <-> loopback/native-messaging broker
  <-> companion extension
  <-> chrome.debugger(tabId)
  <-> existing default-profile tab
```

The broker must preserve:

- explicit task/session to browser `tabId` ownership;
- per-tab command ordering and cross-tab concurrency;
- bounded payloads and timeouts;
- user cancellation as an immediate authorization revocation;
- no exposure of raw cookies, physical target IDs, extension secrets, or broker credentials;
- no agent-controlled click on native permission/revocation UI.

If Hermes still requires a `cdp_url`, the broker must implement and verify the required CDP transport contract; returning a fabricated or nonfunctional URL is not acceptable. A direct target-aware plugin tool may instead use an explicit extension RPC, but then its capability and limitations must be named honestly.

## Default-profile bridge hardening

A task-owned tab does **not** imply ownership of the containing browser window: a default-profile window may also contain unrelated user tabs. Never forward arbitrary `Browser.getWindowBounds` or `Browser.setWindowBounds` calls merely because the caller has a task capability. Bind any permitted read to a window ID obtained from that task's currently owned target and revalidate the task/target/generation in both the broker and extension. Prefer disabling `Browser.setWindowBounds` entirely for default-profile takeover; window mutation is only safe when the provider can prove the window is dedicated to the task.

Keep the authorization and routing maps explicit:

```text
task capability -> task_id -> logical tab_id -> physical target_id -> generation
```

Use a distinct random capability per task endpoint, keep Native Messaging connection capabilities in memory, and never persist either capability in tab/session manifests. On `canceled_by_user`, revoke every debugger session for that physical target immediately and require a new user gesture before restoring consent.

Two lifecycle races require dedicated regressions:

- `chrome.tabs.create()` may resolve before the page appears in `chrome.debugger.getTargets()`. Use a short bounded retry for the exact `tabId`; do not call target lookup with `undefined` and do not retry forever.
- MV3/extension or browser restart invalidates in-memory ownership and physical target IDs. Reconcile persisted logical tabs against live owned targets and recreate missing tabs with an incremented generation; never trust a stale physical ID merely because the logical manifest still exists.

A browser-launched Native Messaging host may not inherit the active Hermes profile's environment. The registered host manifest (or an equally explicit non-secret locator) must identify the profile-local native-host root so the host can find the correct rendezvous and secret. On systems with several registered browser families/profiles, validate loopback, secret length, and active port and select a live/current rendezvous deterministically. Keep the secret itself only under the canonical Hermes data root.

## Native-consent acceptance test

A valid human-in-the-loop test must:

1. use a disposable extension build or a clearly identified companion extension;
2. cause Edge/Chrome itself to display the installation/permission warning;
3. pause for the human to approve or deny—automation does not click;
4. after approval, attach only the named test tab;
5. verify one bounded command such as `Runtime.evaluate` on that tab;
6. show the browser's active-debugging indicator/revocation control;
7. have the human cancel and verify `onDetach` reports `canceled_by_user`;
8. remove the test extension and temporary artifacts afterward unless the user asked to keep them.

Do not count chat approval, a localhost page, a screenshot of custom HTML, a retained command-line flag, or a test that never receives the browser's native event as native-consent evidence.
