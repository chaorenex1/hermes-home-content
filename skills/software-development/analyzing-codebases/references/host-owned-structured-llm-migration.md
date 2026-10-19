# Host-Owned Structured LLM Migration Audit

Use this reference when replacing a lifecycle/subagent or raw chat-completion path with a plugin facade that returns both raw text and parsed structured data.

## Contract inventory

Read the implementation and tests and record:

- exact keyword-only arguments (`instructions`, singular/plural input parameter, JSON mode/schema, timeout, purpose, system prompt);
- result fields (`text`, `parsed`, `content_type`, usage/audit metadata);
- whether malformed JSON returns a sentinel such as `parsed=None` or raises;
- whether schema mismatch raises, returns a sentinel, or is provider-only;
- whether schema validation depends on an optional local package;
- whether timeout is a request timeout, per-attempt timeout, or whole-workflow deadline;
- whether purpose affects routing or only logs/audit;
- where trusted instructions and untrusted payload blocks appear in the final messages.

Never infer these semantics from method names.

## Compatibility trace

Trace the full boundary:

```text
production loader/context
  -> host-owned facade injection
  -> plugin registration/configuration
  -> structured call
  -> parsed-result gate
  -> compatibility return adapter
  -> existing strict parser
  -> domain-specific validator
```

A common blocker is a legacy loader that invokes `register(ctx)` with a fake collector exposing only registration methods. A normal plugin context may have `ctx.llm` while that collector does not. Prove the exact production loader injects the facade; test-only injection is not production reachability.

Prefer a host-side collector injection bound to the known plugin identity. Do not make the plugin instantiate the host facade merely to compensate for an incomplete loader context.

## Fail-closed result handling

For a JSON-object contract:

1. Make one structured call.
2. If the call raises a schema or provider error, propagate/classify it without issuing a second paid call.
3. If `parsed is None` or the parsed value is not the required top-level type, fail closed.
4. If downstream code already performs stricter parsing, return the original raw text after the parsed gate rather than re-serializing the parsed object.

The last rule preserves evidence such as duplicate keys. Ordinary JSON parsing may accept `{"x":1,"x":2}` with last-value-wins; serializing the parsed mapping permanently removes the duplicate-key evidence that a strict downstream parser could reject.

## Schema boundary

A supplied JSON schema can have three different effects:

1. prompt guidance;
2. provider response-format hint;
3. local post-response validation.

Prove each independently. If local validation is optional or dependency-gated, the schema is not a reliable enforcement boundary. Keep an unconditional plugin-side top-level check and retain domain validators. Use a generic object schema only for the common envelope; do not replace heterogeneous per-call semantic validators with one weak shared schema.

## Call-site inventory and schema extraction

Before proposing a structured migration, enumerate the current call graph syntactically. For Python, parse the target file with `ast`, collect calls to both the public runtime function and local wrappers, and print `line:end_line`, callee, and enclosing function. Run a second pass that treats each function's parameters as candidate callees and records direct invocations such as `classifier(...)`, `judge(...)`, or `ai_runtime(...)`; inspect callable attributes such as `self._runner(...)` separately. Use repository search afterward to read each producer, parser, validator, and consumer. This avoids missing multiline calls or confusing an imported symbol with a production call.

Classify every discovered callback before putting it in migration scope:

| Class | Meaning |
|---|---|
| production AI | reached from the real loader/provider with an AI-backed default or configured dependency |
| optional AI seam | production callsite exists, but the callback may be `None` or test-injected |
| deterministic callback | executor, phase hook, or fixed judge; not an LLM output contract |
| test-only seam | supplied only by tests; not proof of production integration |
| dead/legacy | syntactic call exists but no tracked production caller reaches its enclosing method |

When the user excludes adapter/runtime files, exclude their callsites from the inventory but still read them as wiring evidence. Report the distinction explicitly. Also record callback-envelope behavior: some seams accept raw objects, some expect JSON text, and some accept a wrapper such as `{"final":"<json>"}` while rejecting the logically equivalent direct object.

Build one row per logical purpose:

| Evidence | Record |
|---|---|
| Call site | file:line, enclosing function, wrapper/direct call |
| Runtime identity | literal `purpose` currently passed; separately, the caller's logical role |
| Transport parser | raw-text handling, duplicate-key behavior, root-type requirement |
| Accepted root | schema versions, exact required keys, extra-field policy |
| Nested shapes | field types, bounds, enums, defaults, legacy/early-return branches |
| Dynamic fences | round, ID, version, hash, evidence allowlist, checkpoint/path |
| Consumer | downstream parser/renderer/state transition |
| Proposed schema | dynamic `const`/`enum`, required sets, `additionalProperties` |
| Retained validator | semantic checks the schema cannot safely replace |

Do not infer the output contract from prompt prose. Compare four surfaces independently:

1. fields the prompt tells the model to emit;
2. fields the validator actually requires or permits;
3. fields the consumer indexes or renders;
4. fields tests characterize.

Flag mismatches such as a prompt enum rejected by the validator, validator-required fields omitted from the prompt, prompted fields that are ignored, permissive nested extras beneath a closed root, and a `skip` branch accepted before normal validation. Resolve these before making the structured schema authoritative.

### Schema design rules

- Prefer one schema per logical purpose even when all callers currently share one literal purpose.
- Bind request-owned values with dynamic `const`: round, checkpoint/session IDs, candidate IDs and versions, content hashes, target paths, and exact schema version.
- Bind evidence and routing allowlists with dynamic `enum`; keep membership/correlation post-validation where one field must belong to another field's array.
- Set `additionalProperties: false` at every object layer intended to be closed. Record current permissiveness if tightening is a behavior change.
- Model boolean/array and verdict/feedback dependencies with `oneOf` where supported.
- For a validator equivalent to `payload == expected`, use `{ "const": expected }`. If root `const` is unsupported, generate field-level `const` and ordered `prefixItems`; retain the equality validator either way.
- Check the deployed provider's supported JSON Schema subset (`const`, `oneOf`, `if/then`, `not`, `prefixItems`) before relying on those keywords.
- Keep post-validation for cross-array totals, deduplication by one object field, source-span offsets, evidence-to-claim relationships, computed IDs, template/body parsing, stale ownership/version/hash checks, and TOCTOU fences.

A concise audit report should lead with the literal-purpose count, then list logical purposes with exact structures and validators, followed by drift findings, migration order, and unsupported-keyword risks.

## Minimal TDD matrix

### New RED tests

1. **Exact call contract** — one structured call with exact input block, JSON object/schema request, timeout, temperature, and namespaced purpose; raw chat completion is never called.
2. **Unparseable result** — non-empty text plus `parsed=None` fails closed, with one call total.
3. **Schema failure** — facade raises validation error; error propagates and no retry/fallback call occurs.
4. **Trust separation** — trusted template/system instructions stay in the system channel; conversation or document content appears only in untrusted input blocks.
5. **Registration boundary** — plugin registration reads only the host facade required by the new contract and does not touch the retired lifecycle service.
6. **Production collector injection** — the real legacy provider loader gives its collector a facade bound to the provider/plugin identity.

### Green characterization tests to retain

- existing prompt/purpose/system-prompt input limits;
- duplicate-key rejection and top-level object checks;
- domain-specific closed-key and value validation;
- public adapter return type expected by all existing callers;
- one-call/no-paid-retry behavior.

Do not replace all old tests mechanically. Delete tests that assert the retired architecture, adapt tests that assert stable behavior, and retain strict-parser regressions.

## Reporting format

Report:

1. current route and target route;
2. exact facade signature and result semantics;
3. injection/reachability blocker;
4. minimal RED matrix and green regressions;
5. compatibility boundary, including raw-text preservation;
6. unresolved dependency or deployment decisions.
