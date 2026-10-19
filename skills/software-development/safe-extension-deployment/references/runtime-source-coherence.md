# Runtime Source Coherence for Long-Lived Plugin Hosts

Use this when an installed plugin and its standalone CLI report different state even though they point at the same profile home.

## Diagnostic order

1. **Prove profile identity.** Compare the host-supplied profile home, the CLI's explicit/default home, and the provider's resolved storage root. Do not infer a path bug from different results alone.
2. **Prove source identity at three layers.** Record:
   - checkout source path and digest;
   - installed plugin path and digest;
   - live process start time and the module's runtime `__file__`/namespace when observable.
   Disk parity does not prove runtime parity: a long-lived Python process can retain a pre-deployment module in `sys.modules` after the installed files change.
3. **Compare old and current storage contracts.** Use Git history to check whether the cached version reads a legacy directory while the current CLI reads a migrated/flattened directory. An empty tool result from the old layout plus a populated current CLI is source skew, not necessarily a wrong home.
4. **Inspect initialization logs before tool behavior.** A provider may assign its home, then fail while loading legacy config. Verify whether the host removes the failed provider or continues advertising its tools.
5. **Audit discovery for side effects.** Status/config/dashboard inspection must not call plugin registration in a way that replaces live global tool handlers with a fresh uninitialized provider instance.

## Deterministic probes

- Compare process start time against installed source mtimes.
- Import the standalone CLI module and print its `__file__` without exposing secrets.
- Hash checkout and installed trees by relative path, excluding bytecode/caches.
- Run one bounded direct CLI list/read and one equivalent host tool call against the same home; compare counts/status, not private bodies.
- For a registry-based host, capture the handler's bound provider identity before and after provider discovery. Discovery must not change it.

## Root-cause pattern

```text
long-lived host caches plugin version N
→ version N+1 is copied to disk
→ standalone CLI imports N+1
→ host continues executing N
→ old layout/config validator disagrees with current files
→ provider initialization may fail or tools read the wrong root
```

A service restart is the immediate operational recovery. Do not recommend `importlib.reload()` as the small fix for a stateful provider: old instances, workers, context variables, and registered handlers can survive and mix versions.

## Fresh-process acceptance and recovery

1. **Treat the current conversation as immutable evidence, not a reload target.** Hermes keeps tool schemas and provider bindings stable for prompt caching. After replacing plugin files or restarting a host, an already-open conversation may continue calling its old bound instance. Verify with a genuinely fresh `hermes chat -q`/new Desktop session that calls the provider tool itself; a standalone CLI success is not host-path acceptance.
2. **Restart from an independent control process.** Hermes deliberately refuses `gateway restart` when `_HERMES_GATEWAY=1`. A child shell inherits that marker and is still inside the gateway execution context. Use the user-facing restart command or a separately launched shell outside the gateway process tree; if automation launches that independent shell, clear the inherited marker there and verify the old PID died and a new PID became healthy. Never weaken the self-restart guard.
3. **Probe the Host Agent API before adapting plugin calls.** Inspect the installed `PluginAgent.run` signature. If it supports toolsets but not exact `tools=`, use a supported toolset and enforce any narrower capability boundary in the provider with Host-owned `plugin_agent_context` metadata. For a read-only reasoning run, deny writes by authenticated purpose before general context-run parsing, then RED-test both the compatible call shape and a rejected write. Prompt text alone is not a capability boundary.
4. **Distinguish queue recovery from queue completion.** Provider startup may reset stale `running` and historical `failed` durable jobs to `pending`, so counts can temporarily look worse after a successful restart. Verify forward progress with job phase, `updated_at`, cleared error fields, and increasing completed count. Do not delete or synthesize terminal jobs merely to make status counts look clean.
5. **Keep proof layers separate in the report:** source tests, checkout↔installed manifest parity, service PID/status, fresh-session host tool output, and durable-queue progress. A pass at one layer does not substitute for another.

## Required hardening

1. **Deployment contract:** replacing plugin files must stop/drain the owning host first, or the installer must emit an explicit full-host restart requirement. Restart the process that imports the plugin (for a Desktop architecture this may be the embedded server, not merely a sibling gateway).
2. **Fail-closed activation:** if `initialize()` raises, do not retain the provider in routing tables, inject its tool schemas, or log it as activated.
3. **Side-effect-free inspection:** provider listing/config-schema discovery should use an inspection collector whose tool-registration methods are no-ops. Only runtime activation may register handlers.
4. **Runtime identity evidence:** expose or log a bounded plugin version/source digest at activation so disk/runtime skew is diagnosable without private content.

## Regression tests

- **Initialization failure:** a fake provider exposes a tool and then raises from `initialize()`. Assert no provider tools are advertised/routable and activation is reported failed.
- **Discovery stability:** initialize a provider whose tool result includes an in-memory instance token, run provider status/discovery, then assert the registered handler still targets the same initialized instance.
- **Source/layout migration:** fixture version N reads a legacy directory and version N+1 reads the canonical directory. Verify deployment requires a host restart and the fresh process reads only the canonical location.
- **Introspection isolation:** provider status/config endpoints can inspect availability and schemas without mutating the global registry generation or handler identities.

## Reporting

Report separately:

- profile-home correctness;
- checkout ↔ installed disk parity;
- installed disk ↔ live process identity;
- provider initialization success;
- foreground manager routing versus global/plugin-agent routing;
- immediate operational recovery versus durable code hardening.
