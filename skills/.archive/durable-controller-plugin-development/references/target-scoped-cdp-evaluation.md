# Target-Scoped CDP Evaluation and Tab Parallelism

Use this reference when a local Browser Provider must run JavaScript or other CDP work concurrently across logical tabs.

## The isolation trap

`Target.activateTarget(targetId)` changes the browser's foreground page; it does **not** bind an `agent-browser --cdp` daemon to that target. Separate `AGENT_BROWSER_SOCKET_DIR` values isolate daemon sockets, but they do not prove page selection. In a real two-daemon/two-tab probe, both concurrent eval streams returned the same tab title even after activating different CDP targets.

Therefore:

- never remove a global browser lock and call the result "parallel" without a two-tab characterization test;
- do not treat a unique provider `session_name` as target isolation when Hermes invokes `agent-browser --cdp` without `--session`;
- distinguish browser foreground activation from exact CDP command routing.

## Reliable target-scoped evaluation

For direct JavaScript evaluation, route by the task-owned physical target:

1. Resolve `task_id` plus optional stable logical `tab_id` to the current `target_id`; default to the task's active tab and create one if none exists.
2. Validate tab ownership before any CDP command.
3. Connect to the supervisor's current healthy Browser WebSocket endpoint.
4. Call `Target.attachToTarget({targetId, flatten: true})`.
5. Send `Runtime.evaluate` with the returned top-level `sessionId`, `awaitPromise: true`, a bounded timeout, and `returnByValue: true`.
6. Parse `exceptionDetails`, unserializable values, and structured results explicitly.
7. Detach in `finally`.
8. Never return raw CDP URLs, browser UUIDs, or physical target IDs to the model.

The CDP client must support an optional top-level `sessionId` in request envelopes; putting it inside `params` is incorrect.

## Parallelism contract

- Different physical targets may execute concurrently.
- The same target is serialized with a per-tab/per-target lock so DOM mutations and navigations preserve order.
- Tab lookup and ownership checks may use a short metadata lock, but evaluation must occur after releasing that global metadata lock.
- During browser restart, wait for the supervisor to become healthy, then re-resolve the stable logical `tab_id` to the new generation's `target_id`; never reuse a stale physical ID.
- "Automatic tab parallelism" normally means one owned active tab per Hermes task. Parallel calls inside one task need explicit different `tab_id` values; silently cloning the current page changes page state and is not semantics-preserving.

## Security compatibility

Hermes already enforces browser-eval policy and output handling on its existing page-eval path. A standalone target-aware eval tool must not bypass those controls merely to gain precise routing.

Prefer a public host policy/redaction API. If the host exposes only private helpers, isolate them behind a small compatibility adapter, cover their presence and behavior in integration tests, and fail closed when the policy seam is unavailable. Keep expression size, timeout, and serialized-result size bounded. Treat arbitrary page JavaScript as having the page origin's authority, including access to logged-in DOM state.

Enforce policy in this order:

1. validate task/tab ownership, expression size, timeout, and host eval policy before opening an evaluation session;
2. pre-screen explicit private/internal URL literals even when Hermes itself is running on a local backend—the default-profile browser has logged-in user authority and local-backend SSRF relaxations are too broad for this tool;
3. attach to the exact target, then probe and reject an already-private current page **before** executing user JavaScript;
4. run `Runtime.evaluate` with bounded Promise timeout and `userGesture: false`;
5. recheck the current page URL after evaluation, then redact and bound the result;
6. detach in `finally` on success, policy rejection, timeout, or exception.

A post-evaluation URL check alone is not prevention: navigation, request, or exfiltration side effects have already happened. Literal pre-screening closes direct cases such as `location.href='http://127.0.0.1/'` and `fetch('http://localhost/')`; dynamically constructed network targets require a stricter deny policy or request interception if they are in scope. Add an ordering regression whose observable events are `expression-policy -> pre-url-policy -> user-evaluate -> post-url-policy`, plus a private-literal regression proving no attach/evaluate occurs.

## Existing browser tools versus a new eval tool

A target-aware `browser_eval` can be implemented wholly in the plugin and remain restart-aware by resolving the latest endpoint per call. That does **not** make the existing agent-browser-backed navigate/click/type/snapshot tools target-parallel. Full parallelism for those tools requires a target-aware host/agent-browser contract or separate plugin implementations; pre-tool `Target.activateTarget` hooks alone are insufficient.

## Cadence semantics

A profile synchronization interval controls when a new staging generation is copied. If active generations are promoted only on safe browser restart, changing the interval does not guarantee that the running browser consumes data that fresh. State the contract explicitly:

- initial copy occurs on first launch;
- periodic cadence creates staging snapshots;
- active data changes only at the next safe promotion/restart;
- do not force a browser restart merely to satisfy cadence unless the requirement explicitly defines a maximum active-data age.

## Verification matrix

Add deterministic tests for:

- default cadence and non-default config override;
- automatic active-tab resolution and explicit owned-tab selection;
- rejection of foreign-session tab IDs;
- exact `Target.attachToTarget` target and top-level `sessionId` propagation;
- two different tabs entering evaluation concurrently;
- same-tab FIFO serialization;
- Promise success, timeout, JavaScript exception, unserializable value, redaction, and output truncation;
- browser restart remapping stable logical IDs to new physical targets;
- plugin manifest/tool registration and wheel/sdist exposure.

The real-browser acceptance probe should create two pages with unique titles, run evaluations concurrently, and require the two result streams to remain distinct. A green single-tab eval test is not evidence of parallel isolation.
