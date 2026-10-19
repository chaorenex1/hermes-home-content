---
name: cross-platform-cli-launching
description: "Use when shell finds a CLI but child process cannot."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [subprocess, windows, cli, npm, pathext, portability, debugging]
    related_skills: [systematic-debugging, node-inspect-debugger]
---

# Cross-Platform CLI Launching

## Overview

Use this skill when an application launches another CLI and reports “not found,” even though the same command works in an interactive shell. Diagnose command resolution in the **actual parent runtime**, then normalize the executable before launch. Do not treat an install hint as proof that the binary is absent.

This class includes Python `subprocess`, Node `child_process`, service/gateway processes, npm-generated shims, PATH/PATHEXT differences, and shell-vs-direct process creation.

## Diagnostic Workflow

1. Reproduce both layers separately:
   - interactive shell: `<tool> --version`;
   - exact application primitive: the same `subprocess.run`, `Popen`, `spawn`, or `execFile` call used by the code.
2. Inspect resolution in the parent runtime, not only the shell:
   - Python: `shutil.which(name)`, `PATH`, and `PATHEXT`;
   - Node: `process.env.PATH`, `process.env.PATHEXT`, and the selected spawn API.
3. Identify the actual artifact: native executable, `.cmd`, `.bat`, `.ps1`, shell script, symlink, or package-manager shim.
4. Compare direct launch of the bare name with direct launch of the resolved absolute path.
5. Trace every launch site. A preflight check and the real long-lived subprocess must use the same resolver.
6. Separate environment defects from launch-semantics defects:
   - resolver returns nothing: PATH/service environment/install state;
   - resolver returns a wrapper but bare direct launch fails: platform command-resolution mismatch;
   - resolved absolute launch fails: wrapper runtime, quoting, permissions, or architecture.
7. Add one regression test that represents the platform wrapper shape, then implement the smallest shared resolver.

## Preferred Implementation Pattern

Resolve once, preserve argument boundaries, and pass an argv list:

```python
from pathlib import Path
import shutil


def resolve_cli(command: str) -> str:
    resolved = shutil.which(command)
    if resolved:
        return resolved
    if Path(command).is_file():
        return str(Path(command))
    raise FileNotFoundError(f"CLI executable not found: {command}")
```

Use the returned path for **both** version/preflight checks and the production process launch. If configuration allows an explicit executable path, resolve only bare names and preserve explicit paths.

Treat the launch environment's `PATH` as part of the executable-selection contract. If an API accepts `env=...`, do not resolve with an unqualified `shutil.which(name)` and then launch with a different child environment: that searches the parent `PATH`, can bypass the caller's overridden or hardened `env["PATH"]`, and changes normal POSIX `Popen(..., env=env)` behavior. Either resolve against the effective child path (`shutil.which(name, path=spawn_env.get("PATH"))`) or keep native lookup on platforms where pre-resolution is unnecessary. Add a regression test where parent and child PATH values select different fixtures.

On Windows, package managers commonly expose `.cmd`/`.bat` wrappers. Prefer launching the resolved wrapper directly when the runtime supports it. If the language runtime cannot execute that wrapper directly, invoke the platform command processor deliberately and safely rather than setting a broad `shell=True` default.

## Tight Reproduction

For a reusable bounded probe, run `python scripts/probe_cli_resolution.py <tool> -- --version` from the skill directory. It compares the bare launch with the `shutil.which` result without dumping the full PATH; pass `--path` before `<tool>` to test a child-specific PATH.

Python:

```python
import os, shutil, subprocess

print("PATH:", os.environ.get("PATH"))
print("PATHEXT:", os.environ.get("PATHEXT"))
print("resolved:", shutil.which("tool"))
subprocess.run(["tool", "--version"], check=True)
```

Then replace `"tool"` with the exact value returned by `shutil.which`. The differential result distinguishes PATH lookup from process-creation semantics.

## Verification

- Shell invocation succeeds or fails as recorded.
- The exact application launch primitive is reproduced.
- Resolver output is shown without exposing secrets.
- Preflight and production launch use the same resolver policy.
- Write separate RED tests for the preflight/version path and the real long-lived spawn; either path can remain broken independently.
- In portable unit tests, mock resolver output to a Windows `.cmd` path and capture the argv passed to `run`/`Popen`. Reserve executing a real `.cmd` wrapper for native-Windows integration tests.
- If an unrelated existing test asserted the literal bare executable, narrow it to the behavior it owns (subcommand, sandbox flags, environment) while keeping a dedicated resolver test strict about the absolute wrapper path.
- Real smoke tests must enter through the default bare command and confirm one meaningful protocol response/version; injecting an already-resolved path bypasses the resolver under test.

## Pitfalls

- Reinstalling a package before proving it is absent.
- Checking only `command -v`, `where`, or `which` and assuming the application launches commands identically.
- Using `shell=True` merely to inherit shell lookup; this changes quoting and injection boundaries.
- Fixing only the version check while leaving the actual app-server/daemon launch on the broken bare name.
- Hard-coding one machine’s global package path instead of resolving through the parent process environment.
- Calling every `FileNotFoundError` a PATH problem; direct process creation may not apply shell aliases, functions, or wrapper-extension rules.
- Duplicating install hints at multiple error-wrapping layers; preserve one root diagnostic plus one actionable remedy.

## Reference

See `references/windows-npm-shims.md` for the Windows npm `.cmd` differential probe and regression guidance.
