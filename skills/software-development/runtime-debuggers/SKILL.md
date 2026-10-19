---
name: runtime-debuggers
description: "Debug Python and Node runtimes with live breakpoints."
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [debugging, python, nodejs, debugpy, cdp, breakpoints]
---

# Runtime Debuggers

## Overview

Class-level workflow for live breakpoint debugging of Python and Node.js processes. Use this after establishing a tight reproduction with systematic debugging and when logs alone cannot expose the relevant stack, scope, closure, or runtime state.

## Runtime Branches

- **Python/debugpy:** load `references/python-debugpy.md` for launch, attach, breakpoint, stack, and variable-inspection procedures.
- **Node/V8 inspector:** load `references/node-inspect-debugger.md` for `node inspect`, `--inspect-brk`, Chrome DevTools Protocol automation, profiles, and heap snapshots.

## Shared Workflow

1. Fix the exact target process, runtime, source revision, workdir, and reproduction command.
2. Prefer launch-paused mode when startup code matters; attach only to a positively identified running PID.
3. Bind debugger listeners to loopback unless an isolated remote-debugging channel is explicitly required.
4. Set one breakpoint on the smallest failing path and confirm the source mapping and target PID before interpreting values.
5. Inspect stack, locals, closures, and one falsifiable hypothesis at a time; do not patch code merely to collect state if the debugger can expose it.
6. Resume or terminate cleanly so no target remains paused and no debugger listener remains exposed.
7. Convert the confirmed root cause into an automated regression test and verify the fix outside the debugger.

## Pitfalls

- Source maps and generated files can make a breakpoint appear to hit the wrong line.
- Parent-process debugging does not automatically attach to children or workers.
- A debugger attached to the wrong PID can produce convincing but irrelevant evidence.
- Exposing inspector/debugpy ports beyond loopback permits powerful runtime control.

## Verification

- [ ] Target PID/runtime/revision positively identified.
- [ ] Breakpoint hit the intended source location.
- [ ] Observed state confirmed or falsified a stated hypothesis.
- [ ] Target resumed or terminated and listener cleaned up.
- [ ] Root cause covered by a non-debugger regression test.
