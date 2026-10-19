# Context-isolated capability registry audit

Use when a Host intentionally clears caller `ContextVar` state but must carry a bounded, Host-controlled capability to provider/plugin tools.

## Contract checklist

1. **Bound the complete envelope.** Validate and byte-limit every field—identity, purpose, and nested tool context—not only the token payload. Format-only regexes are not size bounds. Measure the final serialized envelope.
2. **Keep model arguments separate.** Inject capability metadata as an internal dispatch kwarg, never into the model-visible tool schema or argument object. Return deep copies where handlers must not mutate Host state.
3. **Cover every real dispatch route.** Trace sequential provider routing, concurrent `_invoke_tool`, and generic registry dispatch. Confirm worker-thread context propagation or pass the envelope explicitly.
4. **Bind authorization dimensions.** Resolve an unpredictable token against a registry entry that binds plugin identity, purpose, owner/run, workflow, and any persistence binding. Reject malformed, inactive, foreign-plugin, wrong-purpose, and wrong-owner uses fail-closed.
5. **Separate map safety from lease semantics.** An `RLock` around registration, lookup, and removal prevents dictionary races; it does not revoke an object already returned by lookup. Decide whether authorization-at-start is sufficient or whether cleanup must wait for in-flight leases / make each side effect re-check active state.
6. **Always clean up.** Register in a context manager and remove in `finally`. Test normal return, exception, cancellation/timeout, and replay after exit. Bound active entries or add expiry if a run can be abandoned without unwinding.
7. **Preserve deterministic persistence fences.** Model receipts and JSON Schema are not the final authority. Re-check required artifact sets, non-empty generation rules, frozen targets, version preconditions, and file boundaries at activation/write time.

## Verification matrix

| Case | Required evidence |
|---|---|
| Empty ContextVar isolation | Provider succeeds only through explicit Host metadata; caller/provider ContextVars remain isolated |
| Sequential path | Real provider handler receives the envelope |
| Concurrent path | Worker receives the same run capability without cross-run bleed |
| Registry path | Actual registered provider handler—not a synthetic capture lambda—resolves the token |
| Stale token | A new call after run exit is rejected |
| Foreign identity/purpose | Active token with mismatched identity or purpose is rejected |
| Parallel runs | Same-purpose runs cannot swap bindings |
| Teardown race | Contract documents and tests in-flight behavior during deregistration |
| Bound enforcement | Oversized identity, purpose, nested context, and whole envelope fail before dispatch |
| End-to-end | Host facade → empty-context runner → production dispatch → provider resolver → persistence boundary |

## Review pitfall

Component tests can all pass while the production bridge remains unproved. A fake agent that manually creates the envelope and a Host test that sends it to a synthetic handler verify two halves, not their composition. Require one test crossing the actual Host/provider route whenever correctness depends on identity derivation, registry ownership, or dispatcher precedence.
