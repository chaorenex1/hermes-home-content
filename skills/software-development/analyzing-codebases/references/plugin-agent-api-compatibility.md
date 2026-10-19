# Plugin Agent API Compatibility Audit

Use this when a standalone plugin calls a host-owned Agent facade and unit tests pass despite a live `unexpected keyword argument` failure.

## Evidence sequence

1. Record the plugin repository's initial dirty baseline and the host checkout's baseline separately. In concurrent workspaces, fingerprint the scoped callsite before and after probes.
2. Read the installed facade implementation and inspect the runtime signature. Compare both the committed host version and the working tree when the host checkout is dirty.
3. Trace the full call path: plugin registration/injection → plugin wrapper or concurrency proxy → facade call → host validation → runner. Confirm whether wrappers transform arguments or merely forward `**kwargs`.
4. Reproduce through the real installed facade or its host-provided deterministic test constructor. Record whether the underlying runner was called; a rejected keyword should fail before execution.
5. Inspect host history to establish the compatibility fence. If the facade did not exist in older versions and used one keyword from inception, do not invent a dual-version shim for an undocumented spelling.

## Test-fake completeness fence

A fake defined as `run(self, **kwargs)` cannot detect signature drift. The smallest RED regression should either:

- use the host's real facade with a deterministic runner, or
- define a strict keyword-only fake matching the public facade and deliberately omit `**kwargs`.

Assert both the positive public keyword and absence of the invalid one. Keep a separate integration test at the loader/injection seam when practical.

## Tool names versus toolsets

Do not treat exact tool names as toolset names. Before replacing `tools=` with `toolsets=`:

1. Read host toolset resolution and registry membership.
2. Resolve the proposed toolset to its actual tools.
3. Compare that set with the plugin's declared authority boundary.

A minimal keyword correction may restore execution while silently broadening authority—for example, a read-only reasoning workflow may receive a toolset that also contains a write tool. Report this separately from the signature mismatch.

When exact read-only selection is required but the host facade scopes only by toolset, choose an explicit contract:

- split read and write tools into separate plugin toolsets and update write-capable callers, or
- add an exact-tool allowlist to the host facade and establish a minimum compatible host version.

Do not catch a broad `TypeError` and retry with another keyword: an internal `TypeError` after execution could trigger a duplicate paid Agent run.

## Host-bound authority metadata must fail closed

A keyword fix can make the Agent run while silently widening authority. This is especially dangerous when a broader toolset includes write tools and the plugin relies on host-bound `purpose`, `plugin_id`, or `tool_context` metadata to reject them.

1. Compare the host's **committed** facade and dispatch path with its working tree. A green probe against an uncommitted host change does not establish a deployable plugin contract.
2. Trace metadata end to end: facade normalization → runner/context variable → every tool-dispatch path → plugin handler. Verify the model cannot supply or alter the authorization metadata.
3. Run two deterministic temporary-directory probes:
   - current-host probe: the real strict facade supplies the expected purpose and a write attempt is denied without creating a file;
   - metadata-loss probe: a signature-compatible host omits the provider-only context and attempts the same write. The operation must still be denied, or the change is fail-open.
4. If direct top-level writes must remain available when no Agent context exists, absence of metadata cannot safely distinguish a user call from an older or miswired Agent host. Prefer a dedicated read-only toolset or exact-tool allowlist so the write tool is never exposed. Otherwise land and version-fence the host metadata change as a coordinated dependency and state the minimum compatible host version.
5. Add a regression at the real facade or loader seam. A permissive `run(**kwargs)` fake can prove argument spelling but cannot prove metadata propagation or authority preservation.

Treat a missing-metadata write success as a security/authority blocker even when focused tests and the current working host are green.

## Report format

Report:

`host context → wrapper/proxy → exact facade signature → failing plugin keyword → runner-called verdict → toolset expansion → smallest RED test → minimal functional fix → authority-preserving fix`

Separate verified current behavior, historical compatibility evidence, security/authority caveats, and unsupported-version uncertainty.