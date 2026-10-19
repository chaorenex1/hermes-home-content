# Hermes Plugin Verification Matrix

Use this reference when validating a standalone Hermes plugin checkout against an installed profile. The goal is to separate source correctness, deployment identity, host integration, runtime behavior, and release artifacts instead of treating one green test command as proof of all five.

## 1. Establish the verification boundary

Record the repository status before testing and do not repair unrelated dirty paths during a verification-only task. Identify:

- plugin manifest and `register(ctx)` entrypoint;
- host-facing CLI module and model-tool registrations;
- disposable-home smoke scripts;
- canonical test, lint, compile, and build commands;
- installed plugin root and active provider selection.

Report source-tree, installed-tree, and host-runtime results separately.

## 2. Prove deployed-source identity

Compare the deployed plugin tree with the checkout by relative path and SHA-256 while excluding caches and bytecode. A plugin being listed as enabled proves discovery, not that the intended revision is deployed.

Required evidence:

- active provider/config selection;
- plugin-manager status;
- source file count versus installed file count;
- zero missing, extra, or hash-different files;
- one public read-only tool call through the running host.

Do not confuse `import <plugin-name>` with host plugin loading when a third-party package has the same import name. Resolve the installed plugin path directly or use the host plugin manager.

## 3. Verify CLI registration at both layers

Test both the plugin's direct operator CLI and the host command:

1. Direct module/console entrypoint `--help`, `status`, and `verify`.
2. Host `hermes <plugin> --help` and at least one real subcommand.
3. Invoke the host-discovered `setup_fn` against a real `argparse.ArgumentParser` in a focused probe.

For current Hermes plugin CLIs, `register_cli(subparser)` receives an argparse parser and must add its arguments/subparsers. It is not the same contract as `PluginContext.register_cli_command(...)`. A direct CLI can be healthy while host dispatch silently builds an empty command after a setup-signature mismatch.

## 4. Treat canonical test collection as a release gate

Run the documented command exactly before using workarounds. If collection fails, inspect interpreter and module identity:

```python
import sys, tests
print(sys.executable)
print(getattr(tests, "__file__", None))
print(list(getattr(tests, "__path__", [])))
```

A repository-local `tests/` directory without `__init__.py` is a namespace package. An installed regular `tests` package can win resolution and break imports such as `tests.support`. The durable fixes are to make the local test package explicit or use imports that do not depend on an ambiguous top-level package.

A temporary `sys.modules["tests"]`/`__path__` injection is diagnostic only: it can prove the underlying suite is green, but it does not make the documented command pass. Report such a result as **conditional green**, not full success.

## 5. Exercise disposable runtime paths

Use a temporary `HERMES_HOME` to verify:

- install/discovery;
- provider initialization and shutdown;
- one complete host callback or memory turn;
- authoritative file read/search/write behavior;
- stale-write or optimistic-concurrency fencing;
- backup/restore when supported;
- restart/recovery and context-cadence behavior when relevant.

A live profile read-only status/verify check complements but does not replace the disposable smoke.

## 6. Separate lint debt from change provenance

Run the full documented lint command. If it fails, check whether each failing file belongs to the current diff. Report both facts:

- the release gate is red for the current tree;
- whether the active change introduced the findings.

Do not hide baseline lint failures by narrowing the official command, but a changed-files-only pass may be included as secondary evidence.

## 7. Inspect clean and dirty build behavior

List wheel members and compare the packaged plugin paths against current source paths. Verify package data, entry points, and absence of bytecode/caches.

Setuptools may reuse `build/lib`; deleted modules can survive there and be copied into a new wheel. Therefore:

1. Inspect any existing distributable artifact independently.
2. Build once from a clean temporary copy that excludes `.git`, `build`, `dist`, egg-info, and caches.
3. If a normal in-place build differs from the clean build, classify it as a release-process contamination risk and require cleaning `build/` before publication.

A clean wheel should have exact source-member parity: zero missing and zero extra plugin files.

## 8. Final verdict format

Use a compact matrix with these independent outcomes:

- **deployment identity**;
- **live host registration**;
- **direct operator CLI**;
- **host CLI dispatch**;
- **canonical tests**;
- **conditional diagnostic tests**;
- **disposable smoke**;
- **lint/compile/diff checks**;
- **clean artifact**;
- **dirty-build contamination risk**.

Lead with `pass`, `partial`, or `fail`. Do not collapse “core runtime works” and “release gates are green” into one claim. Include exact evidence and state whether verification changed tracked files.
