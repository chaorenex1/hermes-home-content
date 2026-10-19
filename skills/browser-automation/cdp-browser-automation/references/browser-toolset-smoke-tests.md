# Browser Toolset Smoke-Test Matrix

Use this when validating a browser tool integration end-to-end. Select the route from the requested browser ownership before testing capabilities.

## Route selection

| Requested target | Default route | First proof |
|---|---|---|
| User's current browser window or authorized existing tabs | `system-browser`: `browser_tabs` + `browser_eval` | `browser_tabs(action="list")` returns the bound session, borrowed tabs, and active tab |
| Anonymous/disposable browser or isolated fixture | Generic browser tools only after the ownership canary passes | A distinct run-owned target/session is observed and no borrowed system-browser target changes |
| Native browser chrome or extension permission UI | Background `computer_use`, escalating only when the driver reports it is needed | Fresh app-scoped capture identifies the exact native window |

Do not choose by tool-name similarity, apparent launch features, or success flags. Generic `browser_*` tools and `system-browser` tools may use different sessions, or may converge on the same underlying target; prove ownership directly.

## Ownership canary for generic or isolated tools

Run this before treating generic browser tools as disposable when a system-browser session may already exist:

1. List current system-browser tabs. Record the original active tab, each borrowed `target_id`, and enough URL/title state to restore and verify without exposing private content in the report.
2. Prefer explicit isolated-session or run-owned-target metadata from the generic tool. If none exists and mutation risk is acceptable for a smoke test, open a harmless run-owned canary tab with the current-browser tab manager and make it active before the first generic navigation. This is a recovery aid, not proof that the generic tool will honor the active tab.
3. Navigate to a deterministic public fixture, request a snapshot, and capture the snapshot's top `frame_id` or equivalent target identity.
4. List system-browser tabs again. Isolation passes only when the generic target is distinct from every borrowed target and no borrowed tab's URL/title changed. A top `frame_id` equal to a borrowed `target_id`, or any borrowed-tab navigation, means shared-target operation.
5. On shared-target evidence, separate capability results from ownership results: successful DOM input or vision does not make isolation pass. Stop consequential interaction on the borrowed page; restore its prior URL using the least destructive reversible action, verify restoration through its explicit stable tab ID, close only the run-owned canary tab, and restore the original active tab.
6. If the tool exposes no target identity and system-browser state cannot be cross-checked, report isolation as unproven rather than inferring it from the process name or UI appearance.

If changing a borrowed page would be unacceptable, do not run a navigation-based canary; require an explicitly identified isolated profile/session first.

## Current-window smoke test

1. List tabs and record `session_id`, the original `active_tab_id`, and borrowed status. Do not print private page content.
2. Run a read-only `browser_eval` on the original active tab with its explicit stable `tab_id`. Verify title, URL, ready state, and `method: target_cdp`.
3. Open one harmless temporary tab, such as `https://example.com/`, and record its returned `tab_id`.
4. Switch to that exact temporary tab, evaluate a deterministic heading/title, and verify the result belongs to that tab.
5. Close only the temporary tab.
6. Explicitly switch back to the original active tab; do not rely on browser close-tab fallback behavior.
7. List tabs again. Verify the temporary tab is absent, all borrowed tabs remain, and the original active tab is restored.

This path proves control of the user's authorized current browser window without modifying existing page state. Never close borrowed tabs or expose cookies, tokens, private DOM, or unrelated tab contents.

## Isolated-browser capability matrix

Use this matrix only after the ownership canary passes for the intended isolated route. If the canary fails, record isolation as failed and do not continue the matrix on a borrowed target merely to accumulate capability passes.

Suggested fixtures:

- Interactive controls: `https://www.selenium.dev/selenium/web/web-form.html`
- Long page with visible images: `https://www.selenium.dev/`

| Capability | Exercise | Direct verification |
|---|---|---|
| Navigate | Open the interactive fixture | Returned URL and title match |
| Snapshot | Request accessibility state | Expected heading and controls have refs |
| Type | Enter a unique non-secret marker | Console evaluation reads back the exact value |
| Press | Send `Tab` from the text field | `document.activeElement` changes as expected |
| Click | Toggle a box, then submit the harmless form | Checkbox state changes; confirmation heading appears |
| Scroll | Scroll the long fixture | `window.scrollY > 0` and max scroll is positive |
| Back | Return after form submission or link navigation | URL and heading are restored |
| Console | Evaluate a small object and separately read logs/errors | Structured value and buffers are readable |
| Vision | Capture with annotations | Controls are recognizable and refs align |
| Images | Enumerate the image-bearing fixture | At least one URL/alt entry matches a visible image |

## Result reporting

Name the tested route explicitly. Report capability-level pass/fail, direct evidence, cleanup/restoration state, and any isolated blocker. Do not equate a success flag with verified behavior. Retry once only when the second attempt changes the fixture, input, or verification method; stop after an identical deterministic failure.