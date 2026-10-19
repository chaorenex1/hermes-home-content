# Security-context propagation review probes

Use these probes when a nested/plugin Agent receives a broad toolset and relies on
Host-carried metadata to restrict one operation.

## Capability trace

1. Identify every tool exposed by the selected toolset; do not rely on prose claiming a
   subset when the registry contains more.
2. Trace the nested call through each registry, memory-provider router, sequential
   executor, parallel executor, middleware wrapper, and final handler.
3. At each hop, verify the authority envelope is copied without becoming model-controlled,
   logged as sensitive payload, or lost at a thread/task boundary.
4. Inspect final authorization behavior for valid, malformed, stale, and absent envelopes.
   Missing context must not fall through to public authority.

## Companion-patch deployment probe

When correctness depends on a separate Host patch:

- confirm the main installer or README links it;
- run `git apply --check` against the supported Host revision;
- verify the plugin refuses initialization or dependent capability exposure when the Host
  lacks the patch;
- require a full process restart if imported modules remain resident;
- test the default documented install path, not only a developer-patched checkout.

Patch identity and patched-worktree tests prove artifact completeness, not deployment safety.
A matching stable patch ID still leaves a security gap when the normal plugin installer can
activate the dependent capability on an unpatched Host. Treat a manual document in an
unlinked `patches/` directory as insufficient unless the default install flow explicitly
requires that step.

Identity-check procedure: `sha256sum` the artifact first and quote the hash in the verdict;
locate the real Host root (`pip show hermes-agent` → Location) and confirm
`git rev-parse HEAD` equals the revision the patch targets; then `git apply --check
--cached <patch>`. If the Host worktree is dirty (patch already applied alongside unrelated
changes), `git diff | git patch-id --stable` will NOT equal the artifact's patch-id — use
`git apply --check --reverse <patch>` as the subset proof that every hunk is present in the
worktree instead of rejecting on the patch-id mismatch.

Dispatch-coverage probe: when the patch forwards an authority envelope via injected kwargs,
enumerate every dispatch callsite that can reach the same providers — e.g.
`grep -n 'handle_tool_call(' agent/*.py` — and confirm the envelope is added on each branch
(memory router, provider tool router, tool registry, background-review router, image
router). An unpatched sibling branch still dispatches the protected tool without the
envelope, so the downstream fail-closed guard sees "absent" authority exactly as if the
patch were missing.

## Metadata-loss execution probe

Add a deterministic temporary-directory probe for the older or miswired Host path:

1. expose a toolset containing both the intended read tools and a mutating sibling tool;
2. use a signature-compatible fake Host runner that executes the mutating tool but omits
   the provider-only context/authority kwargs;
3. invoke the public nested-Agent capability through its real provider wrapper;
4. assert that the operation is denied and the target file/database remains unchanged.

If the write succeeds, report a blocker even when the current patched Host passes all tests.
The smallest fail-closed compatibility fence is often to require a new Host-owned argument
or capability token at the plugin callsite: an older Host then rejects the call before the
Agent runs. Alternatives are an installer-enforced patch/version check or a runtime
capability handshake. A purpose-only downstream guard is not enough when absent metadata
falls through to ordinary top-level authority.

## Regression test shape

Prefer an end-to-end test that:

1. starts the real plugin Agent/Host runner with the restricted purpose;
2. allows the model/tool loop to see the broad toolset;
3. attempts the protected mutating tool;
4. asserts the provider denies it and no filesystem/database mutation occurs;
5. repeats through parallel dispatch when the Host supports concurrent tools;
6. verifies missing or malformed Host context fails closed.

A provider unit test that calls the handler with a handcrafted trusted envelope is useful
but insufficient: it validates the guard, not propagation.

## Delegated-child ContextVar probe

A nested Agent's own sequential and parallel tool executors can be correct while a
model-reachable delegation tool still drops authority. Audit every thread/task boundary
created after the delegation call:

1. child construction;
2. batch fan-out executor;
3. per-child timeout/run executor;
4. detached/background runner;
5. the child's own parallel tool executor.

ContextVars do not cross fresh threads unless the submit site captures and installs the
context. Wrapping only the child's tool executor is insufficient if `child.run()` itself
starts in an empty context. For each route, assert both the provider metadata and the
noninteractive approval policy inside the final handler.

Use an exploit-oriented regression: start the real nested/plugin Agent with delegation
available, delegate to a child, and have that child attempt both an arbitrary-code tool
and a dangerous shell operation. Run with process yolo enabled and with approval mode off;
the nested no-human policy must still deny both. Also assert the child provider handler
receives the original immutable plugin envelope. If safe propagation is impractical,
remove delegation from the nested Agent's exposed toolsets.

## Fresh-Context profile binding probe

A deliberate `contextvars.Context()` sandbox clears *all* caller ContextVars, including host-owned profile/home overrides. Isolation must selectively reinstall the active profile home inside the fresh Context while still clearing session IDs, delivery addresses, approval state, and user-controlled authority. A `profile_name` field that only labels a session row does not bind runtime configuration, credentials, plugins, or storage.

Test with a named-profile home override: the nested runner must observe the same resolved profile home as its caller, while session and approval ContextVars remain isolated. Validate profile IDs with the Host's canonical profile normalizer/validator rather than reusing a purpose or URL regex.

## Strict JSON-envelope probe

A JSON round trip is not automatically strict normalization. Python's default encoder accepts NaN and Infinity, and nested non-string mapping keys may be coerced to strings, including collisions. Validation and serialization must operate on one immutable snapshot: walking an arbitrary stateful `Mapping` and later calling `dict(value)` is a TOCTOU bug because the two reads can return different data. Prefer accepting only concrete JSON containers or recursively snapshot each item exactly once before validating that snapshot.

For security/correlation envelopes:

- serialize with `allow_nan=False` or perform an equivalent finite-number walk;
- recursively require documented key types and reject post-coercion collisions;
- deep-copy at the Host boundary so handlers cannot mutate shared context;
- bound depth/encoded size/container count when normalization repeats per tool call;
- test malformed, cyclic, non-finite, colliding-key, oversized, deeply nested, and stateful/custom Mapping payloads.

## Concurrent generation probe

For summary/index generation, capture source path plus hash or revision before generation.
After the Agent returns and before publishing, compare both identity and content revision.
A test should update an existing source in place during generation and assert the stale
result is rejected.

## Installer probe

For replacement installers, compare dry-run and real branches for:

- destination;
- backup location and naming;
- overwrite refusal;
- ignore patterns;
- restart guidance;
- rollback behavior after partial failure.
