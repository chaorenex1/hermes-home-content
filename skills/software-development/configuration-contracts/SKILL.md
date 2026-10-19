---
name: configuration-contracts
description: Safely evolve profile-local configuration schemas, migrations, validation, and runtime wiring with regression evidence.
version: 1.0.0
author: Masia
license: MIT
---

# Configuration Contracts

Use for configuration schema additions, migration, validation, persistence, or runtime-wiring audits in stateful applications.

## Contract to preserve

A setting is complete only when all four links exist:

1. A documented/default schema field.
2. Type, range, and cross-field validation.
3. A safe persistence/merge path that preserves unrelated user choices.
4. A concrete runtime read that changes the owning behavior, with a regression test.

A field that merely serializes is not implemented. A field that is read but can silently violate a safety invariant is not safe.

## Workflow

1. **Inventory the contract.** List every top-level and nested default field. Trace each to validation, save/load migration, and its runtime consumer. Mark no-runtime-reference fields as defects unless they are deliberately rejected safety toggles.
2. **Test first.** Add a failing test for each changed behavior. For nested configuration, save non-default values, apply a partial update to the same section, then assert sibling settings survive and reload matches the saved effective configuration.
3. **Merge deliberately.** Use a one-level deep merge for known configuration sections. Do not use a bare top-level `dict.update()` when an update may contain a partial nested object. Leave malformed non-object updates for validation to reject.
4. **Handle legacy state on every public write path.** Migrate deprecated keys in memory before validation on both profile load and direct save/update input. Test these separately: (a) read an old persisted file and normalize it, and (b) submit the deprecated key directly to the public writer and verify the canonical replacement is persisted while the old key disappears. Saving an unrelated key after loading an old file does not prove write-input compatibility. If a persisted profile is already invalid under the new schema and blocks the writer, make the smallest authorized schema-valid repair, then invoke the normal atomic writer once to normalize defaults and remove deprecated keys.
5. **Wire runtime behavior.** Read settings at the narrowest owner: scheduler limits in the scheduler, retrieval limits in the retriever, projection gates in the projection controller, and lifecycle switches in the provider. Preserve hard safety invariants at the shared boundary. For sibling cadence/depth settings, require separate due/execution evidence; a shared configuration section is not proof that every field is live.
6. **Treat safety fields explicitly.** If a requested setting would disable append-only audit, expected-version checks, mandatory review, or durable loop evidence, either implement a precisely bounded safe policy or reject the unsafe value in validation. Do not leave it accepted-but-inert.
7. **Verify both scopes.** Run focused schema/config tests, the affected subsystem tests, and one real-profile load/normalization probe. Redact configuration content if it might contain secrets.
8. **Retire obsolete lifecycle modes end-to-end.** When a trigger/worker architecture is replaced, remove the old scheduler topology—not only its entry hook—including timers, worker fields, callbacks, shutdown joins, retry/backoff state, public symbols, tests, and generated build copies. Preserve only a bounded load/save migration that strips deprecated persisted keys and rewrites normalized configuration. See `references/retiring-obsolete-lifecycle-mode.md`.
9. **Model independent budgets independently.** When two layers or stages must have separate budgets, define two exact persisted keys, defaults, validators, migration behavior, and runtime reads. Add a non-default test with unequal values and prove exhausting or truncating one layer cannot spend, clip, or silently override the other layer's allowance.
10. **Align model-facing tool schemas with runtime validators.** Treat the advertised JSON Schema and the handler validator as one acceptance language. Encode cross-field rules—such as selectors that are required for one discriminator value and forbidden for all others—with conditional branches plus explicit field descriptions. Add Draft 2020-12 valid/invalid matrix tests, audit sibling read/write tools for the same mismatch, and run one fresh-agent semantic probe after deployment; an existing cached session may retain the old tool schema. See `references/model-tool-json-schema.md`.
11. **Keep provider metadata scoped to the model route.** When one custom provider serves several models with different windows or capabilities, persist metadata in the provider's per-model map and ensure a global override does not mask it. Probe the endpoint first, fall back to the application's provider-aware resolver, preserve explicit existing values, and use the official atomic config writer for nested keys that a dotted-path CLI cannot address safely. See `references/hermes-custom-provider-model-metadata.md`.

## Runtime-wiring audit

For each configured field, record:

| Field | Default | Validator | Runtime owner | Observable effect | Test |
|---|---|---|---|---|---|

Do not infer a runtime owner from matching string names. Prove a path from `load_config` to the behavior-changing branch.

## Pitfalls

- Fresh temporary-profile tests miss backward-compatibility and partial-update loss.
- A validation ceiling and a larger persisted default can brick all config loads after upgrade; probe an existing profile before release.
- Compatibility aliases must synchronize in both load and save paths.
- Dotted-path config setters may split literal identifiers containing `.` (for example model IDs); inspect the setter before using it for keyed maps, and prefer the official atomic writer when the key cannot be escaped.
- Avoid treating a safety-critical setting as ordinary feature configuration. A rejected unsafe value is better than an accepted no-op.
- Do not print entire live configuration files as evidence; report only the keys and values needed to diagnose the contract.

## References

- `references/profile-config-migration.md` — concise migration and verification recipe for nested profile settings.
- `references/model-tool-json-schema.md` — conditional tool-argument schemas, semantic test matrix, cache-safe deployment, and fresh-agent verification.
- `references/hermes-custom-provider-model-metadata.md` — per-model context metadata, discovery precedence, atomic nested writes, and secret-safe verification for named Hermes custom providers.
