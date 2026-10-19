# Subagent Lifecycle Replacement Boundary Audit

Use this when code appears to call `model.infer()`, `infer()`, or another AI-looking method and a migration proposes replacing it with a supervised subagent lifecycle.

## 0. Prefer the host plugin-LLM lane for bounded structured work

Before designing parent capabilities or tool isolation, classify whether the stage needs an agent at all. For one bounded, no-tools semantic decision, use the host-owned plugin LLM facade (`ctx.llm.complete_structured(...)`) rather than a child-agent lifecycle when the host provides it.

This lane is usually the correct fit for signal judges, routers, extractors, reviewers, synthesis, and adoption decisions because it:

- runs from provider-owned background workers without an active parent turn;
- performs a direct model completion and therefore exposes no agent tools;
- keeps provider/model/auth/fallback resolution host-owned;
- accepts a purpose-specific JSON Schema and returns `text` plus parsed JSON;
- supports a per-call timeout without creating a child handle or transcript lifecycle.

Use one registered purpose and one schema per semantic stage. A generic “JSON object” schema weakens the contract and lets unrelated stage outputs pass. Preserve deterministic domain checks after schema validation: candidate/version/hash binding, evidence/citation allowlists, source-span bounds, state transitions, and file/version fences.

When duplicate JSON keys matter, strictly decode the raw `result.text`, compare it to `result.parsed`, and fail if they differ. Treat `parsed is None`, malformed raw JSON, schema rejection, and raw/parsed mismatch as technical failures, never semantic rejection or approval.

A per-call timeout is not a whole-pipeline deadline: a sequence of router, extractor, reviewer, and synthesizer calls can consume the timeout independently. Define a separate durable job deadline and shutdown policy.

Some host subsystems load plugins through a reduced/fake context that lacks `ctx.llm`. Prefer fixing the host to inject the same identity-bound facade. A temporary compatibility path may construct the public facade with the exact plugin ID, but must not import private provider/auth internals.

Escalate to SubagentLifecycle only when the task genuinely needs multi-turn agent behavior, tools, child cancellation/status, or a child transcript.

## 1. Classify the current method before replacing it

Do not infer semantics from the method name. Trace its body and callbacks.

- **Transport call:** directly invokes a model/provider and returns model output. This is a candidate for lifecycle replacement.
- **Host orchestrator:** owns bounded rounds, validation, evidence/version fences, deterministic transitions, and persistence while calling a supplied reasoner/judge. Keep this host-owned; replace only the semantic callback.
- **Mixed method:** split deterministic orchestration from the single-call AI adapter before changing transport.

For every suspected callsite, record: entrypoint → thread/context owner → AI callback → output validator → terminal state transition → durable write.

## 2. Prove parent-context reachability on every lifecycle operation

A lifecycle may resolve authorization from an active parent turn via a `ContextVar` or equivalent turn-local binding.

- Check `launch`, `status`, `wait`, `result`, `cancel`, and `reconnect`; parent validation may happen on all of them, not only launch.
- New threads do not automatically inherit Python context variables. A provider-owned worker can therefore lose the active parent even when it was spawned during a turn.
- Launching in the parent and waiting in a generic worker is unsafe if handle access also requires the active parent context.
- Do not preserve or copy a live parent object beyond the turn unless the host API explicitly supports that lifetime. Prefer a host-issued background capability or a dedicated background-safe lifecycle service.

Classify each route independently: synchronous tool call, host callback, provider worker, prefetch worker, startup recovery, and shutdown recovery can have different parent reachability.

## 3. Separate prompt instructions from capability enforcement

A system prompt saying “do not call tools” is not tool isolation.

- Inspect how omitted and empty `allowed_toolsets`/`allowed_tools` values are interpreted. Some APIs treat both as “inherit the parent toolset.”
- Require an explicit zero-tool contract for JSON-only judges. If the lifecycle cannot express zero tools, record that as a host API prerequisite rather than claiming isolation.
- Verify child memory-provider initialization, inherited memory context, delegation notifications, completion hooks, and cost rollup. These are lifecycle side effects even when the child returns only JSON.

## 4. Align bounds and cancellation end to end

Validate the final rendered request, not individual pieces in isolation.

- Bound trusted goal/system instructions against the lifecycle goal limit.
- Bound serialized evidence/data against the context limit after all envelopes and templates are added.
- Bound expected structured output against the terminal-result limit.
- Use `wait(handle, timeout_seconds=...)`; on timeout request cooperative cancellation, perform one short terminal wait, and fail closed.
- Retain handles while work is active so shutdown can cancel them. A short provider-thread join does not cancel a lifecycle child.

Per-launch timeouts may be unsupported even when bounded `wait` is supported; do not confuse the two.

## 5. Reconcile lifecycle durability with durable jobs

In-process handles and durable application jobs are different abstractions.

- Determine retention duration and restart behavior for handles/results.
- If reconnect cannot survive process exit, keep the durable job/checkpoint as authority and define how an interrupted stage is retried or terminally failed.
- Startup recovery usually runs outside an active agent turn; prove it can obtain the required lifecycle authority before removing a direct host LLM fallback.
- Use stable, stage-specific correlation IDs such as `job_id + stage + round` to prevent duplicate launches without conflating distinct rounds.

## 6. Preserve deterministic terminal authority

The child should return bounded structured data only. Host code must continue to own:

- strict JSON/schema and duplicate-key validation;
- evidence/citation and candidate-version binding;
- conflict/version fences;
- state-machine transitions and retry quotas;
- promotion, rejection, snapshot writes, and projections.

Never let review exhaustion or malformed output silently authorize promotion. Exhaustion should remain rejected, blocked, or quarantined unless an explicit product policy says otherwise.

## Verification matrix

1. AST/exact search proves all production and test callsites; exclude generated/ignored mirrors.
2. Direct host-orchestrator tests still cover validation, round stopping, version conflicts, and persistence.
3. Real lifecycle integration—not a fabricated module—covers active-parent launch and verified terminal output.
4. Background worker tests cover missing/expired parent authority explicitly.
5. Timeout → cancel → terminal-state behavior is deterministic and event-driven.
6. Zero-tool enforcement is asserted from child construction, not prompt text.
7. Goal/context/result cap tests use fully rendered payloads.
8. Restart tests reconcile lost handles with durable jobs.
9. Stage metadata and correlation IDs distinguish router, extractor, reviewer, synthesizer, and round number.
10. Shutdown proves no paid child remains unsupervised after the provider returns.
