# Isolated Agent run-capability bridge

Use this pattern when an outer provider owns a durable job, an inner Agent is intentionally run inside a fresh/empty `contextvars.Context`, and model tools must remain bound to the exact outer job.

## Failure signature

- The provider binds a job/workflow with `ContextVar`s before `Agent.run()`.
- The Host deliberately invokes the Agent through a new empty Context to prevent gateway IDs, delivery routing, approvals, or other ambient authority from leaking inward.
- Tool calls reach the provider, but its ambient binding is absent. Writes fail as “no active job,” or worse, read/file boundaries silently fall back to live unrestricted state.

A same-context unit test will miss this. Reproduce through `contextvars.Context().run(...)` or the real Host runner.

## Secure bridge

1. Preserve the empty Context boundary. Never replace it with `copy_context()` merely to recover provider state.
2. Before the Agent run, the provider creates a fresh opaque run ID and registers a frozen `(plugin/provider owner, purpose/workflow, binding)` record in a lock-protected active-run registry.
3. Pass only internal tool context to the Host. It must not enter the prompt, model-visible tool arguments, result/audit envelopes, or ordinary logs.
4. Inside the fresh Context, the Host installs a Host-owned ContextVar containing the plugin owner, purpose, and opaque tool context.
5. Every real tool dispatch route must forward the Host-owned context: direct provider/memory dispatch, global registry dispatch, sequential execution, and copied-context parallel workers. Testing only a synthetic handler is insufficient.
6. The provider resolves the opaque ID and validates exact owner, exact purpose, and active lifetime before restoring the frozen binding/workflow.
7. Register before invocation and revoke unconditionally in `finally`. Never infer authority from thread ID, a singleton “current job,” or a model-visible durable `job_id`.

## Publication invariants

- A multi-artifact Base generation activates only when the complete frozen required set is staged. Assert both physical files and database artifact rows.
- A Dynamic generation must not publish `completed + 0 artifacts`. Use an explicit `no_change` contract if no-change publication is required; otherwise leave the prior generation active.
- Prompt/schema/store requirements must agree on artifact count and target names. A store-only guard prevents corruption but can still make the Agent fail every run if the prompt requests fewer artifacts.

## Test matrix

- Host empty-Context isolation remains intact while explicit tool context is visible.
- Context is absent after normal return and exception.
- Actual registry/provider path reaches the bound job, not just a manually constructed envelope.
- Wrong owner, mismatched purpose, malformed context, stale/replayed run ID, and wrong job/path fail closed.
- Two concurrent same-purpose runs cannot cross-bind.
- Frozen reads do not fall back to live provider state.
- File-memory authority remains restricted through the isolated boundary.
- Required profile artifacts exist physically and appear in one active complete generation.
- Logs contain completion evidence but not opaque context payloads.

## Contract-correction discipline

Do not invent API length or policy limits merely because a reviewer suggests “bounded” metadata. Apply only limits accepted by the governing contract. When the user explicitly removes named constraints:

1. delete the constants;
2. delete dependent validators/helpers and rejection tests;
3. literal-search source, tests, documentation, and generated maintenance patches until the names have zero hits;
4. retain unrelated accepted bounds;
5. regenerate companion patches/artifacts and re-run focused tests.

Record the deliberately accepted residual risk rather than silently restoring the rejected restriction under another name.

## Deployment evidence

When the provider and Host must change together, keep a source-controlled companion Host patch. Regenerate it from only the relevant Host files, verify it with `git apply --check` (or reverse-check against the modified tree), and run Host plus provider suites independently. Deploy the provider with a timestamped backup and compare source/deployed digests. Finish with a fresh-process smoke test that crosses the actual Host runner and registry and verifies physical artifacts plus active database rows.

If the Host refuses an in-process self-restart, do not bypass the guard. Report the reload boundary precisely; use a fresh subprocess for end-to-end verification and require the normal external runtime restart for the already-running process.
