# Hermes Dashboard Hidden Launcher on Windows

This reference captures the reusable pattern for launching Hermes Dashboard from a profile-local Windows installation without a visible console. It is an example of the broader process-launching procedure in the parent skill, not a fixed machine-specific script.

## Runtime contract

- Launcher location: `$HERMES_HOME\gateway-service\Hermes_Dashboard.vbs`
- Install root: read `HERMES_HOME` at launch time
- Executable: `$HERMES_HOME\hermes-agent\venv\Scripts\hermes.exe`
- Working directory: `$HERMES_HOME\hermes-agent`
- Example argv: `dashboard --host 0.0.0.0 --port 9119 --no-open`
- Launch mechanism: `WScript.Shell.Run(..., 0, False)`

Binding to a non-loopback address is an application security decision, separate from hidden execution. Configure the Dashboard authentication provider before using the example argv on a reachable interface.

## Known-good VBScript shape

```vbscript
' Hermes Dashboard - hidden background launcher
Option Explicit

Dim shell, fso, hermes_home, hermes_exe, working_dir, command_line
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

hermes_home = Trim(shell.Environment("PROCESS").Item("HERMES_HOME"))
If Len(hermes_home) = 0 Then
  hermes_home = Trim(shell.Environment("USER").Item("HERMES_HOME"))
End If
If Len(hermes_home) = 0 Then
  hermes_home = Trim(shell.Environment("SYSTEM").Item("HERMES_HOME"))
End If

If Len(hermes_home) = 0 Then
  MsgBox "HERMES_HOME is not set.", vbCritical, "Hermes Dashboard"
  WScript.Quit 1
End If

working_dir = fso.BuildPath(hermes_home, "hermes-agent")
hermes_exe = fso.BuildPath(working_dir, "venv\Scripts\hermes.exe")

If Not fso.FileExists(hermes_exe) Then
  MsgBox "Hermes executable not found:" & vbCrLf & hermes_exe, _
    vbCritical, "Hermes Dashboard"
  WScript.Quit 2
End If

shell.CurrentDirectory = working_dir
command_line = """" & hermes_exe & _
  """ dashboard --host 0.0.0.0 --port 9119 --no-open"

shell.Run command_line, 0, False
```

Adapt the host, port, and application arguments to the requested deployment. Keep executable resolution and quoting unchanged unless the installation layout itself differs.

## Verification recipe

1. Confirm the target port is free, or inventory every existing listener before launch.
2. Run `wscript.exe <launcher-path>` or `cscript.exe //nologo <launcher-path>`.
3. Poll for readiness rather than assuming the asynchronous launcher is ready immediately.
4. Find the listener PID and inspect its command line.
5. Require the derived `hermes.exe` path and intended Dashboard arguments in that command line.
6. Request `/api/status` and require a successful HTTP response.
7. Enumerate visible top-level windows owned by the process PID; the list should be empty.

`cscript.exe` returning zero proves the VBScript was accepted, not that the Dashboard remained alive. The child may still exit because of an occupied port, missing authentication configuration, or another application-level startup refusal.

## Conflict-safe cleanup

Before terminating a smoke-test process, match all of the following:

- listener port and local address;
- executable path derived from the test `HERMES_HOME`;
- `dashboard` subcommand;
- expected host/port arguments.

Do not terminate an unmatched listener. Report the occupied resource and leave the existing process intact.
