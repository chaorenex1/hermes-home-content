# Model-Tool Contract Release Gate

Use this gate when a plugin exposes model-facing read/write tools whose accepted arguments depend on an enum discriminator, operation mode, target registry, or versioned file state.

## Acceptance matrix

Test the contract at four layers; none substitutes for another.

### 1. Advertised capability surface

- Assert the exact public tool names from the provider's real schema list.
- Assert retired names are absent from source registration and the installed provider. If update moved from a separate tool into `mode="update"`, test that distinction explicitly.
- Compare read and write enums exactly. Aggregates such as a rendered context may be read-only while their leaf artifacts are writable.

### 2. JSON Schema language

- Validate schemas with the host's supported draft.
- For discriminator-dependent selectors, cover ordinary-without-selectors, ordinary-with-selectors, special-with-all-selectors, and special-with-missing-selector.
- For create/update unions, assert create requires its destination and content, while update requires destination, expected version, and a bounded operation list.
- Enumerate operation discriminator values and required fields; do not merely assert that an `operations` property exists.

### 3. Temporary-profile behavior

Exercise real storage and activation, not mocks:

1. Create every base/profile target from the frozen registry and verify the returned path/version.
2. Activate, then read every information type back through the public read tool.
3. For hierarchical dynamic state, traverse the full section × leaf Cartesian product, write each leaf, read each leaf, and verify the aggregate renderer emits exactly one outer fence with every expected heading.
4. Publish version 1, stage version 2 with insert + replace + delete in one immutable-preimage operation list, activate, and read back the exact final text and version.
5. Keep stale-version, stale-line, wrong-path, unknown-field, and unauthorized-target rejection tests.

### 4. Installed-runtime evidence

- Load schemas from the actual installed plugin rather than an unrelated same-named package on `sys.path`; use an explicit file-location package shell when names can collide with a third-party distribution.
- Compare cryptographic digests for the owning modules and report full-plugin drift separately from the tested surface.
- Start a fresh agent process/session after schema changes because existing sessions may retain cached tool definitions.
- Confirm one natural tool call completes without the former validation warning, then run provider/store integrity checks after background writes settle.

## Release evidence table

| Contract | Minimum evidence |
|---|---|
| Public names | provider schema-name set + retired-name absence |
| Information registry | exact read/write enum equality |
| Payload grammar | JSON Schema valid/invalid matrix |
| Create semantics | every authorized target created and activated |
| Update semantics | insert/replace/delete + versioned read-back |
| Aggregate semantics | full leaf product + one rendered aggregate fence |
| Installed parity | owning-module digests + installed schema inspection |
| Regression safety | focused tests, full suite, static checks |

## Pitfalls

- A handler can be strict while its schema teaches the model an invalid payload. Preserve the handler and repair the schema.
- A schema can be correct while registration still exposes a retired tool name. Inspect the provider's final schema list.
- A passing leaf test does not prove the aggregate renderer covers the whole registry; test the Cartesian product.
- Source tests do not prove installed bytes. Conversely, an unrelated full-plugin drift should not invalidate evidence that the owning modules match—report both and synchronize before release.
- Package-qualified test helpers can resolve to another checkout's regular `tests` package when the local directory is only a namespace package. Check `tests.__file__`; add a local package marker or avoid ambiguous package-qualified helper imports before trusting collection failures.
