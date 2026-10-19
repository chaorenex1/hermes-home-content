# Model-Facing Tool JSON Schema Contracts

Use this when an agent repeatedly emits arguments that the tool handler rejects even though the fields appear in the advertised tool schema.

## Core diagnosis

Treat the model-visible schema and runtime validator as two descriptions of one accepted payload language. A contract mismatch exists when JSON Schema accepts a payload that the handler rejects. Typical symptom: optional selector fields are globally advertised, but runtime permits them only for one discriminator value.

Do not weaken a correct fail-closed handler merely to silence warnings. Fix the advertised contract first.

## Conditional-selector pattern

For a discriminator such as `information_type`:

- The special branch uses `const` and requires its dependent selectors.
- The ordinary branch enumerates every other discriminator value and forbids those selectors with `not` plus `required` clauses.
- Keep the outer object closed with `additionalProperties: false`.
- Add plain field descriptions stating “required only for X; forbidden otherwise.” The condition is machine-enforced; the description helps the model choose correctly.
- If the schema already has a `oneOf` for another concern, such as create-versus-update, compose the selector rule under `allOf` rather than merging unrelated branches.

Retain runtime validation as a second safety boundary. JSON Schema guides and locally validates requests; handler checks preserve authority, stale-version, ownership, and TOCTOU rules.

## TDD matrix

Use the same Draft supported by the host, commonly Draft 2020-12. Test at least:

| Payload | Expected |
|---|---|
| ordinary discriminator, selectors omitted | valid |
| ordinary discriminator, either selector present | invalid |
| special discriminator, all selectors present | valid |
| special discriminator, either selector missing | invalid |
| unknown field | invalid |

Run this matrix for sibling read and write tools. A mismatch commonly exists in both because they copied the same flat property set.

## Verification sequence

1. Reproduce the exact warning from sanitized logs; record event sequence and error class, not private tool arguments.
2. Add a schema-level RED test showing the invalid combination is currently accepted.
3. Add the conditional schema and descriptions; keep handler rejection unchanged.
4. Run focused schema/dispatch tests, static checks, and the full suite.
5. Verify deployed source parity.
6. Before restarting a live agent host, wait boundedly for durable jobs to leave pending/running states; do not interrupt an in-flight phase merely to reload a schema.
7. Restart the host because tool schemas are normally frozen for a process/session.
8. Open a fresh agent session and request the affected tool naturally. Confirm the provider accepts the schema, the tool completes, and no former validation warning appears.
9. Run the provider/store integrity command after live background writes settle.

## Pitfalls

- A direct handler test cannot reveal that the schema taught the model an invalid call shape.
- A structural assertion that only checks property names does not prove cross-field semantics; validate representative payloads.
- Reusing an existing conversation can give a false negative because prompt/tool-schema caching preserves the old contract.
- Logging raw tool arguments to diagnose the mismatch can expose private content. Prefer discriminator names, error classes, counts, and a controlled local validator probe.
- A successful source test is not deployment evidence. Verify installed bytes and one new-session call.
