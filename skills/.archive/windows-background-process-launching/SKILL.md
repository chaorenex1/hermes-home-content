---
name: windows-background-process-launching
description: "Launch durable hidden Windows processes safely."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [windows, background, subprocess, vbs, services, process-lifecycle]
    related_skills: [cross-platform-cli-launching, systematic-debugging]
---

# Windows Background Process Launching Skill

Use this skill when a Windows CLI, daemon, dashboard, gateway, or local service must run asynchronously without opening or flashing a console window. It covers launcher design, environment-derived executable resolution, safe process ownership checks, and runtime verification; it does not replace a real service manager when restart-at-boot or recovery policy is required.

## When to Use

- A user asks for a hidden or windowless Windows background launcher.
- A Scheduled Task or Startup-folder entry must start a console CLI silently.
- A launcher must follow a profile-local or relocatable installation root.
- A foreground command works, but double-click/startup execution flashes a console.
- A background smoke test must distinguish the newly launched process from an existing listener.

Do not use this skill for POSIX `systemd`, `launchd`, `nohup`, or `tmux` workflows.

## Prerequisites

- Confirm the requested executable and arguments in a foreground terminal first.
- Identify the authoritative installation-root environment variable, such as `HERMES_HOME`.
- Confirm whether the process is one-shot or long-lived.
- Decide whether the launcher needs only hidden execution or also boot persistence and restart policy.
- Check whether the target port or singleton resource is already owned before launching.

## How to Run

For a hidden user-launched process, prefer a `.vbs` launcher executed by `wscript.exe`:

```text
wscript.exe C:\path\to\launcher.vbs
```

Use Windows Task Scheduler for boot/logon persistence. Point the task at `wscript.exe` and pass the launcher path as its argument rather than scheduling a `.cmd` file directly.

See `references/hermes-dashboard-vbs.md` for a complete environment-derived Hermes Dashboard example and its verification recipe.

## Quick Reference

| Requirement | Preferred mechanism |
|---|---|
| No visible console | `WScript.Shell.Run command, 0, False` |
| Dynamic install root | Read process, user, then system environment at launch time |
| Safe path construction | `Scripting.FileSystemObject.BuildPath` |
| Spaces in executable path | Quote the executable token explicitly |
| Detached/asynchronous start | `bWaitOnReturn=False` |
| Missing prerequisite | Exit before launch with a concise actionable error |
| Startup persistence | Task Scheduler invoking `wscript.exe` |
| Runtime proof | Listener + command line + health endpoint + visible-window check |

## Procedure

### 1. Reproduce the foreground command

Run the exact executable and argv in a visible terminal. Confirm it reaches a stable ready state. Do not debug hidden execution and application startup simultaneously.

### 2. Resolve paths from the runtime environment

Read the installation root each time the launcher runs. Do not bake one user's absolute home directory into the launcher.

Use this precedence when the script may be launched by a shell, Explorer, or Task Scheduler:

1. process environment;
2. user environment;
3. system environment.

Fail explicitly if the variable is absent. Build the executable path from that root and verify the file exists before launch.

### 3. Use a GUI-subsystem launcher

Prefer `wscript.exe` plus VBScript for a truly hidden entry point. A `.cmd` or console PowerShell entry point can allocate or briefly flash a console before it hides its child.

Launch the console executable itself with window style `0`. Do not switch automatically to `pythonw.exe`: a console-less parent can cause console-subsystem descendants to allocate their own visible windows. A hidden console owned by the long-lived process is usually the more stable process tree.

### 4. Preserve argument boundaries

Construct the command so the executable path is quoted as one token. Keep static arguments literal and validate any user-controlled arguments before interpolation. Avoid broad shell evaluation merely to get redirection or path lookup.

### 5. Separate hidden launch from persistence

A hidden asynchronous launch is not a service contract. If the process must survive reboot, configure Task Scheduler with:

- a deterministic trigger;
- the intended user identity;
- `wscript.exe` as the program;
- the absolute `.vbs` path as the argument;
- an explicit working directory when the application depends on it;
- restart-on-failure behavior appropriate to the application.

### 6. Verify the real process

Use several independent facts rather than one status command:

1. identify every listener or process matching the requested resource;
2. inspect the owning process command line;
3. confirm the command line contains the dynamically resolved executable and intended argv;
4. call one health/status endpoint or equivalent protocol check;
5. enumerate visible top-level windows for the owning PID and require none.

When a port is already occupied, do not kill the first returned PID. Windows may have listeners associated with different local addresses or pre-existing companion services. Confirm executable path and argv before terminating anything.

## Pitfalls

- Hard-coding `C:\Users\name\...` instead of resolving the profile/install root.
- Assuming a variable present in the current shell is persisted into Explorer or Task Scheduler; check process/user/system scopes deliberately.
- Treating `--no-open` as hidden execution; it only prevents browser launch, not console creation.
- Using `.cmd` as the outermost scheduled entry point when zero console flash is required.
- Replacing a console interpreter with `pythonw.exe` without testing descendant console behavior.
- Declaring success because a process exists while its port or health endpoint is not ready.
- Declaring failure from one process-status helper while the requested protocol endpoint is healthy.
- Killing a port owner without matching its executable and arguments to the process created by the test.
- Re-running a launcher against an occupied singleton port and interpreting the hidden child’s quick exit as a launcher bug.
- Leaving application-startup errors entirely invisible; use preflight checks, application logs, or a health probe.

## Verification

A complete verification records:

- the launcher file exists at the requested location;
- the environment variable resolves to the expected root at runtime;
- the derived executable exists;
- `wscript.exe` accepts the script without a VBScript error;
- the long-lived process command line contains the expected executable and arguments;
- one application-level health check succeeds;
- the owner PID has no visible top-level windows;
- any pre-existing process or listener was preserved unless the user explicitly authorized replacement.

For test cleanup, terminate only the PID whose executable and argv match the launched fixture. If ownership cannot be proven, stop and report the conflict rather than widening the kill scope.
