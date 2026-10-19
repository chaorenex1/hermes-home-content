---
name: process-launching-workflows
description: "Use when launching CLIs or background processes safely."
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [subprocess, cli, windows, background, pathext, lifecycle]
---

# Process Launching Workflows

## Overview

Class-level guide for reliable child-process launching: resolve CLIs in the actual parent/child environment, preserve argv boundaries, handle package-manager wrappers, and launch durable hidden Windows processes with ownership-aware verification.

## CLI Resolution Branch

When a shell finds a CLI but an application cannot, reproduce the exact `subprocess`/`spawn` primitive, inspect PATH/PATHEXT in the actual parent and effective child environment, identify native executable versus wrapper, and compare bare launch with the resolved absolute artifact. Use one shared resolver for preflight and production launch. Avoid broad `shell=True`; preserve argv boundaries. See `references/cross-platform-cli-launching.md` and the migrated npm-shim probe/script.

## Windows Hidden Background Branch

When resolution works but a Windows daemon/dashboard/gateway must run asynchronously without console flash, prefer a GUI-subsystem launcher such as `wscript.exe` with a quoted VBScript wrapper. Resolve install roots from process/user/system environment at runtime, verify prerequisites, and separate hidden launch from Task Scheduler boot persistence/restart policy. See `references/windows-background-process-launching.md` and the Hermes Dashboard example.

## Shared Workflow

1. Confirm executable, argv, workdir, environment, one-shot/long-lived shape, and required ownership resource such as a port.
2. Reproduce the foreground command before debugging hidden/background behavior.
3. Resolve against the effective child environment; preserve explicit configured paths.
4. Launch with the host process API and bounded monitoring; do not shell-background.
5. Verify process command line, listener/resource ownership, application health, and expected UI/window state.
6. Clean up only a PID whose executable and argv match the launched fixture.

## Verification Checklist

- [ ] Exact parent launch primitive reproduced.
- [ ] Parent and child PATH/PATHEXT differences checked.
- [ ] Preflight and production use one resolver policy.
- [ ] Argument boundaries preserved without unnecessary shell evaluation.
- [ ] Long-lived process proved by ownership plus health, not PID existence alone.
- [ ] Cleanup affected only a proven run-owned process.
