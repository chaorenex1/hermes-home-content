# Windows npm shims: shell success, direct child failure

## Symptom class

An npm-installed CLI works from Git Bash, PowerShell, or `cmd.exe`, while Python reports `FileNotFoundError: [WinError 2]` for an argv launch such as:

```python
subprocess.run(["codex", "--version"], shell=False)
```

The install hint may be misleading. npm commonly creates sibling launchers like:

```text
codex       # POSIX shell shim
codex.cmd   # Windows command wrapper
codex.ps1   # PowerShell wrapper, depending on npm version
```

Interactive shells apply their own command-resolution rules. A direct Windows child-process API is not guaranteed to reproduce that behavior for a bare extensionless name.

## Differential probe

Run the probe with the same Python executable and environment as the failing application:

```python
import os
import shutil
import subprocess

name = "codex"
resolved = shutil.which(name)
print("PATH present:", bool(os.environ.get("PATH")))
print("PATHEXT:", os.environ.get("PATHEXT"))
print("resolved:", resolved)

for executable in (name, resolved):
    if not executable:
        continue
    try:
        proc = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            stdin=subprocess.DEVNULL,
        )
        print(executable, proc.returncode, proc.stdout.strip(), proc.stderr.strip())
    except Exception as exc:
        print(executable, type(exc).__name__, str(exc))
```

Interpretation:

- bare name fails, resolved `.cmd` succeeds: launch-semantics defect;
- both fail and `resolved is None`: PATH/service environment or install-state defect;
- shell works but both Python paths fail: inspect wrapper runtime, command processor, quoting, architecture, and parent identity.

## Repair contract

1. Introduce one resolver at the boundary where the CLI path enters the process-launch layer.
2. Respect explicit configured paths; resolve only command names.
3. Use the resolved executable for preflight, version checks, real app-server/daemon startup, restart, and health checks.
4. Preserve argv boundaries; do not concatenate user-controlled arguments into a shell command.
5. Keep one error layer responsible for the install/remediation hint.
6. If the launcher accepts an environment override, resolve against its effective `PATH`, not implicitly against the parent's `os.environ`. For example, use `shutil.which(name, path=spawn_env.get("PATH"))`. Otherwise a caller that supplies a toolchain-specific or hardened PATH can silently run a different executable, and POSIX behavior can regress even while the Windows shim case succeeds.

## Independent review checks

When reviewing a shim-resolution patch, inspect the shared resolver implementation as well as the call-site diff. A mocked `shutil.which` plus mocked `run`/`Popen` proves argv construction, but not real wrapper execution or preservation of environment-based lookup semantics. Treat a reproducible executable-selection mismatch as a logic error; treat missing native integration coverage as a non-blocking suggestion when portable unit tests and credible real-platform smoke evidence both exist.

## Regression shape

Use two layers so the test suite stays portable without losing native proof.

Portable unit tests (run on every OS):

- monkeypatch the resolver lookup so `codex` resolves to a representative path such as `C:\\nvm4w\\nodejs\\codex.CMD`;
- capture argv at the exact `subprocess.run` preflight boundary and assert the resolved wrapper is used;
- capture argv independently at the `subprocess.Popen`/long-lived transport boundary and assert the same resolver policy is used there;
- retain a negative test for a genuinely absent command;
- when another test only owns sandbox/environment behavior, do not keep a brittle assertion that argv[0] must be the bare command.

Native-Windows integration test or local smoke:

- use the default bare command as application input, not an already-resolved path;
- confirm the version check succeeds;
- start the real long-lived child and complete one meaningful handshake or protocol response;
- optionally create a temporary `.cmd` wrapper and prepend its directory to a controlled PATH when a real package-manager install is unavailable.

Mock-only tests of the version parser are insufficient because they do not exercise executable resolution. Conversely, requiring a `.cmd` wrapper to execute on POSIX CI makes the regression platform-fragile; mock the resolution boundary there and keep real wrapper execution on Windows.

## Concrete evidence from the originating case

The shell reported `codex-cli 0.145.0`; `shutil.which("codex")` returned the npm `codex.cmd`; Python `subprocess.run(["codex", "--version"])` raised WinError 2; launching the returned `.cmd` path succeeded. This ruled out missing installation and PATH absence, isolating the Windows bare-name launch path. The application also duplicated its install hint in the low-level check and outer runtime-switch wrapper, demonstrating why remediation text should have a single owner.
