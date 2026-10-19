# Memory Provider Live-Binding Diagnostics

Use this when provider health appears green but Desktop/Gateway memory tools disagree with the provider's own CLI.

## Layered probe matrix

| Layer | Minimal evidence | What success proves | What it does not prove |
|---|---|---|---|
| Resolved config | Provider ID from supported config CLI | Selection is persisted/resolved | Owning process reloaded it |
| Discovery | `hermes doctor` provider check | Package/plugin is discoverable | Profile scope, file visibility, or tool compatibility |
| Provider storage | Read-only `status` + `verify` | Schema and storage invariants pass | Host binding or Agent-backed calls |
| Provider reads | `tree`, exact `read`, known-content `search` | Authoritative files are present and readable | Current session uses this root |
| Live direct tools | Session `kb_tree`, `kb_read`, `kb_search` | Current host process is bound to a readable scope | Agent execution contract |
| Live reasoning | One narrow `kb_reasoning` query with a known answer | Host Agent wrapper and plugin call signature cooperate | Background extraction health |
| Durable jobs | Counts by pending/running/failed/complete | Queue lifecycle is observable | Semantic quality of completed output |
| Repository tests | Clean-environment targeted/full tests | Current source behavior under test contracts | Installed runtime was reloaded |

## Interpretation rules

- CLI sees a known file, but live list/search/read is empty or missing: investigate profile root, active scope, plugin binding, and owning-process reload before touching storage.
- Direct file tools work, but reasoning fails on an unexpected argument or call signature: investigate host/plugin API drift; do not diagnose this as missing memory content.
- Storage verification passes while durable jobs remain failed, pending, or stuck running: report both facts. These are independent health dimensions.
- A provider ID may be retained for compatibility after the implementation changes. Inspect the provider manifest and current documentation before claiming that a similarly named database engine is actually used.
- Test collection errors are not product failures until the project environment is isolated. Hermes-hosted shells can inherit a host `PYTHONPATH` that shadows the repository's packages or loads wheels from another Python version.

## Bounded probe recipe

1. Record the resolved provider ID and the process/surface being tested.
2. Run provider `status` and `verify` read-only.
3. Choose one known authoritative path and one distinctive token.
4. Compare provider CLI `tree/read/search` with live `kb_tree/kb_read/kb_search`.
5. Run one narrow live reasoning query over that token.
6. Record job-state counts.
7. For source tests, print only `PYTHONPATH`, `VIRTUAL_ENV`, interpreter path, and `sys.path`; avoid dumping the whole environment because it may contain secrets.
8. Clear injected `PYTHONPATH` for the test command and use the project's declared environment. If dependencies are absent, synchronize from the project lock/config rather than borrowing the host runtime.
9. Report each layer separately as pass/fail; never collapse a mixed result into “provider works” or “provider is broken.”

## Example classification envelope

```text
config/discovery: pass
provider storage/read: pass
live direct tools: fail — scope/root mismatch evidence
live reasoning: fail — host/plugin call-contract evidence
job lifecycle: degraded — counts attached
source tests: pass/fail with clean-environment command and exact totals
```

This envelope keeps remediation focused and preserves evidence for deciding whether to reload the owning process, repair binding, adapt the plugin API, or fix queue/concurrency logic.
