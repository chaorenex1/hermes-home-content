# Standalone Memory Provider Context Migration Audit

Use this when a standalone memory plugin changes the structure, cadence, provenance, or persistence of model-visible context.

## 1. Trace the host boundary before the plugin

Read both sides of the integration:

```text
host turn start → provider on_turn_start → provider prefetch
host turn completion → sync_turn → queue_prefetch
provider internal queues/workers → durable publication → next-turn prefetch
```

Do not infer production reachability from a method merely existing on the plugin. Verify it is part of the host ABC/protocol or has a real host call site. Classify unmatched methods as compatibility residue or dead public surface, then either remove them or test their intended caller explicitly.

## 2. Distinguish semantic layers from transport fences

The host may strip provider-authored wrappers and add its own `<memory-context>` envelope. A requirement such as “exactly two model-visible layers” must state whether it means:

- two provider-owned semantic children inside the host fence; or
- literally no other host/builtin memory context.

For standalone plugins, the first is usually enforceable; the second may require core changes. Test the final host-composed API payload, not only the plugin renderer.

## 3. Account for persisted API sidecars and prompt caching

Some hosts persist the exact injected bytes in a user message's `api_content` so replay preserves the prompt prefix. A new renderer changes only future turns; historical turns retain old tags and old context by design.

Therefore define rollout acceptance as one of:

- all newly generated provider payloads use the new structure;
- a fresh/rotated session is globally clean; or
- historical sidecars are migrated only through an explicitly cache-safe host mechanism.

Never rewrite prior sidecars merely to make a tag search pass.

## 4. Check first-turn bootstrap separately

Post-turn refresh produces context for the next turn. If a removed synchronous path previously exposed stable identity/preferences on the first turn, define how a fresh profile gets an initial base context:

- host-projected stable sources without an AI call;
- precomputed profile artifact on source change; or
- an explicit cold-first-turn behavior.

Test accepted/profile data present with no pre-existing derived snapshot.

## 5. Reconcile host serialization with plugin concurrency

A host may submit `sync_turn` before `queue_prefetch` on one serialized executor while each provider method starts its own thread. This recreates a race below the host boundary. Trace ownership through the innermost workers.

For evidence-dependent pipelines, prefer one explicit sequence:

```text
completed-turn slicing
→ base refresh when due
→ accepted retrieval/materialization
→ dialectical stages when due
→ atomic publication
```

If `queue_prefetch` remains public, specify whether it triggers, joins, or becomes a no-op for that pipeline.

## 6. Audit cadence as durable state

For every cadence, require its own successful-publication watermark and tests for:

- first-run and off-by-one behavior;
- failure not consuming cadence;
- restart/session isolation;
- rapid overlapping turns rechecking due state after earlier jobs complete;
- source-version changes and whether they bypass cadence;
- stale supplement behavior when its base hash no longer matches.

A configured cadence with no runtime watermark/due path is a fake knob.

## 7. Treat configuration migration as semantic

Mapping an adaptive `max_rounds=N` to an exact `depth=N` changes behavior even if the integer is preserved. Record call-cost and latency impact, distinguish absent defaults from explicitly persisted defaults, and add a migration test showing the new execution count.

## 8. Validate plan executability mechanically

Before approval:

1. Map every acceptance criterion to a task and test.
2. Verify every `Modify:` path exists and every `Create:` path is intentional.
3. Parse the DAG and flag dependency-unordered tasks that modify the same file.
4. Ensure schema producers precede tasks that consume the new columns/tables.
5. Check recovery at every boundary: artifact staged, artifact published, run row written, job terminalized.
6. Verify rollback against both newer database schema and reused artifact paths.
7. Run tests through the intended interpreter and confirm imported module `__file__` points at the checkout.

## 9. Include built-in system-memory and identity sources

An external provider can be selected while the host still loads built-in `MEMORY.md` / `USER.md` stores and injects them into the system prompt. Verify all four conditions separately:

1. the external provider is selected;
2. built-in memory/profile injection flags are enabled or disabled;
3. the canonical built-in files are non-empty;
4. the host actually serializes their frozen snapshots into the model request.

A plugin-only two-layer renderer cannot satisfy a global two-layer acceptance criterion while these blocks remain reachable. Either narrow the criterion to provider-owned semantic children or add a generic host integration that suppresses only model-visible duplication while preserving any required built-in tool storage.

## 10. Keep SOUL projection coherent with the cached system identity

If the host loads SOUL into a session-cached system prompt, a cadence worker must not independently reread a newer SOUL and inject it as a dynamic identity card in the same session. That creates two authoritative identities with different hashes.

Use one explicit policy:

- bind the dynamic projection to the SOUL hash actually used to build this session's system prompt;
- defer a newer SOUL until the next session; or
- perform a host-owned cache-safe prompt rebuild and sidecar transition.

Test a mid-session SOUL file change and assert the model never sees mixed identity versions.

## 11. Freeze completed-turn identity before asynchronous dispatch

A mutable counter updated by `on_turn_start` is not a safe cadence watermark for a delayed `sync_turn`. The next user turn can advance it before the previous completion callback executes.

Prefer a frozen host-supplied completed-turn number/event id. If the host contract lacks one, use a provider-owned durable per-session completion sequence keyed by the completed exchange; do not reread a turn-start global in the background worker. Test by blocking the sync executor, starting turn N+1, then releasing turn N and verifying its job/receipt remains bound to N.

## 12. Make feedback handoff durable and modify the real production module

Exact injection receipts do not make feedback crash-safe when the offered-context association exists only in an in-memory session dictionary. Prove `prefetch → restart → sync_turn` can resolve the same scoped receipt by session, completed event, query/context hash, and version.

During plan review, verify every planned `Modify:` feedback path exists and is imported by production. A nonexistent proposed module often results in a parallel implementation while the old subject kinds, counters, and in-memory offers remain live. Add tests for restart recovery, removal of legacy subject paths, and first-turn/system offers if they remain supported.

## 13. Preserve isolated Plugin Agent security while propagating provider authority

A host-managed plugin Agent may deliberately run inside a fresh `contextvars.Context` so it cannot inherit the foreground gateway session, delivery address, approval callback, or bypass state. If a provider wraps `ctx.agent.run()` in its own `ContextVar` bindings, that isolation also strips the provider binding. Trace the complete path:

```text
provider bind → PluginAgent.run → host fresh Context → tool-worker context copy
→ registry dispatch → provider tool handler
```

Do **not** repair this by replacing the host's fresh context with `copy_context()`: that restores provider state by also restoring security-sensitive ambient state. Prefer a bounded Host-owned per-run `tool_context` that is installed inside the fresh context, omitted from prompts/audit/logs, propagated by the existing tool-worker context bridge, and reset in `finally`.

When the provider binding is non-serializable, use a hybrid design:

1. Generate a cryptographically random, non-model-visible `context_run_id`.
2. Store the immutable binding/workflow in a provider registry under that ID with a lock.
3. Pass only the ID through the Host-owned plugin-run context together with Host-bound plugin identity and purpose.
4. At every provider tool entrypoint—including file tools and reads—validate plugin identity, exact purpose, token presence, and active registry membership, then re-enter the provider's existing context managers.
5. Remove the registry entry in `finally`; missing, foreign, expired, or replayed tokens fail closed with no singleton/current-job fallback.

A provider-only active-job registry is unsafe when reads or sibling tools do not carry a job ID, when parallel tool execution changes thread identity, or when overlapping runs make “the current job” ambiguous. Do not turn a prompt-visible durable job ID into the sole bearer capability. Durable store CAS/version checks remain necessary but do not identify which concurrent Agent run authorized the first tool call.

Required regression contract:

- host isolation remains intact for gateway/session/approval/bypass state;
- explicit plugin tool context is visible in sync and async runs but absent after return or exception;
- two barrier-synchronized runs and parallel tool workers never observe each other's token;
- provider write/read/file tools all restore the exact binding, with frozen reads staying frozen;
- wrong plugin, purpose, path, durable job ID, token, or replay is rejected;
- no token or payload appears in model prompts, result audit, or logs;
- older Hosts lacking the explicit API fail with a clear capability error rather than an insecure fallback.

Also test getter immutability: a shallow outer copy is insufficient if nested context data can be mutated between tool calls. Prefer an immutable structure or a bounded deep copy.

## 14. Audit provider discovery and initialization as one transaction

A discovery call is not side-effect-free merely because the inspection context ignores `register_tool()`. If discovery still imports the module and calls arbitrary `register(ctx)` code, it can construct Agent/LLM facades, rebind module-global runtimes, create threads/files, or mutate an already active provider. Distinguish and test three contracts:

1. **Metadata discovery** — no runtime registration callback; reads static metadata or a dedicated pure availability factory.
2. **Inspection construction** — if unavoidable, uses an explicit `inspection_only` context that plugins must honor before configuring AI runtimes, attaching Agents, starting workers, or registering hooks/tools.
3. **Active registration** — may bind global tools and runtime facades, but every binding must belong to a lifecycle transaction that can be rolled back.

Treat initialization as transactional across every state owner, not only the manager's provider list. Inventory:

```text
provider list + provider-owned tool routes
+ process-global tool registry entries and prior overridden handlers
+ successful sibling providers/resources
+ module-global runtime/facade bindings
```

If any provider fails initialization, fail-closed means successful siblings are shut down, all manager routes are cleared or restored to the pre-call snapshot, global tool registrations are removed or previous entries restored, and the caller cannot expose a half-initialized manager. Catch cleanup exceptions without masking the original initialization failure, but continue rollback.

Required deterministic probes:

- one provider fails after registering a global tool; a later agent/tool snapshot cannot see that tool;
- one provider succeeds and one fails; the manager ends empty, both are shut down as applicable, and no route survives;
- failed-provider `shutdown()` raises; rollback still converges and the initialization error remains primary;
- discovery after an active provider does not change global runtime/facade identity or emit file/thread/registry side effects;
- the production Agent constructor clears or never publishes the manager on failure.

A unit test that directly adds a fake provider to `MemoryManager` proves only manager-local cleanup. Pair it with a real loader/registry integration test and a subsequent-Agent snapshot test to catch process-global leakage.

## Report shape

Report:

```text
host lifecycle → provider lifecycle → model-visible payload
→ persisted sidecar/replay behavior → background ownership
→ artifact/version fences → concrete plan gap → exact task/test repair
```

Separate current verified behavior from target-plan conformance. A green current suite does not prove the proposed DAG, migration, or rollback is executable.
