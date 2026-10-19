# Readiness, providers, and host limits

## Answer readiness from the installed artifact

Three checks cover the whole question, in this order:

1. `node -v` against the package's `engines` field. Published `rea-agents`
   accepts `^22.19.0 || ^24.11.0 || >=26.0.0`. Outside that range the server can
   still start and answer, but it is unsupported and `doctor` classifies it
   `missing_dependency`. Fix by switching Node with the installed version
   manager; never substitute an older or differently patched rea build.
   When `nvm install <version>` cannot resolve the release (stale mirror
   index), drop the official `node-v<version>-win-x64.zip` into
   `<nvm root>\v<version>\node.exe` and run `nvm use <version>`. Follow with
   `hash -r` in git-bash: the shell caches the old `node` path and keeps
   reporting the previous version until the cache is dropped.
2. `npx -y rea-agents@<registered-version> doctor --json` for the host rows:
   `node`, `host`, `hopper`, `ghidra`, `ida-registration`, plus skill and
   registration entries. They live in `checks[]` on an audit-wide run and in
   `scope_checks[]` only once a scope flag narrowed the audit. `healthy: false`
   and exit code 1 are expected on a host that injects the MCP server by other
   means (Hermes declares it in its own `config.yaml`), so read the individual
   checks instead of the summary flag.
3. The live server's own view: MCP `binary_session` with `{}`, or CLI
   `capabilities --json`. A target-free `list_prompts` call is the cheapest
   proof that the registered server process answered at all.
   `result.provider.id` names the composite;
   `result.capabilities[].available`, `availability_code` and `reason` describe
   the running process. `open: false` only means no target is bound yet.

`doctor` prints the full tool catalog, roughly 2,400 lines, and `providers`
prints about 3,500; a capture that keeps head and tail truncates the part you
need, and neither belongs in a reply. Use `doctor --json` and reduce it:
`checks[]` carries `name`, `ok`, `classification`, `detail`, `remediation` in an
audit-wide run; `scope_checks[]` holds the smaller set when a scope flag
narrowed it; `providerInspections[]` carries `id`, `configured`, `available`
plus its own failing `checks[]`. `scripts/rea-readiness.py` performs that
reduction. When only text output is available, redirect and read the file:
`npx ... doctor > "$TMPDIR/rea-doctor.txt" 2>&1`. In git-bash `$TMPDIR` is
`/tmp`, which is `C:\Users\<user>\AppData\Local\Temp`; pass that native path to
file readers and searches, because ripgrep-backed tools cannot resolve
`/tmp/...`.

Run the registered version offline from its install instead of re-downloading:
`~/AppData/Local/npm-cache/_npx/*/node_modules/rea-agents` contains
`package.json` (engines, bin) and `scripts/rea.mjs`, so
`node scripts/rea.mjs doctor` and `node scripts/rea.mjs --help` exercise exactly
what the MCP entry runs.

## Three dependency layers

| Layer | Needed for | Notes |
|---|---|---|
| Node runtime with npm/npx | everything, including the MCP server | no account, no API key, no network after the first package fetch; analysis stays local |
| One deep provider | native binaries only | Ghidra, IDA or Hopper; once `open_binary` binds a provider there is no failure fallback, so an unavailable provider fails instead of silently switching |
| Per-target extras | firmware, Android, ELF layout or crash cores, browser/Electron runtime, process capture | caller-supplied and separate from REA itself |

No engine is required for static JavaScript/Electron trees, managed PE/CLI
metadata and CIL, EVM bytecode, artifact inventory and extraction, or PE header
facts. Do not tell a user that REA "needs Ghidra" for those targets.

## Deep provider prerequisites

Ghidra on Windows (experimental x64 lane):

- operator-installed Ghidra **12.1.x** (verified 12.1.4), already extracted;
  REA does not install or upgrade it, and its setup cannot supply a missing
  engine;
- a **full JDK 21 or newer** selected by `JAVA_HOME`; the adapter runs the
  packaged Java `HeadlessScript`, so Python and PyGhidra are not prerequisites;
- `GHIDRA_INSTALL_DIR` pointing at the extracted release directory, and
  optionally `REA_ANALYSIS_PROVIDER=ghidra` to pin the provider;
- admission limited to explicit native x86, x86-64, ARMNT/Thumb-2, ARM64 PE
  application or DLL, or a raw NMOS 6502 image with a caller-supplied entry;
  managed images are rejected, and the read-only boundary excludes database
  mutations and annotations;
- cold import can outlast a short client timeout: the provider startup deadline
  is 330 s and `REA_GHIDRA_STARTUP_TIMEOUT_MS` raises it for large binaries.

Install and prove the engine before reporting readiness:

1. Take the release zip from the project's GitHub releases and compare its
   sha256 with the asset digest
   (`gh api repos/NationalSecurityAgency/ghidra/releases/latest --jq '.assets[].digest'`),
   not with a remembered checksum.
2. Extract with `unzip`. GNU tar cannot read a zip at all, and it treats a `C:`
   prefix as a remote host, so `--force-local` changes only the error message.
3. Prove the launcher outside REA: create the project directory first, then run
   `cmd.exe /c 'C:\path\ghidra_12.1.4_PUBLIC\support\analyzeHeadless.bat
   C:/path/projects test -import C:/Windows/System32/notepad.exe -noanalysis'`.
   A bare `cmd //c` in git-bash opens an interactive shell instead of running
   the batch file, and the `-import` step is what proves the JVM and classpath
   rather than just printing the usage banner.
4. `setx GHIDRA_INSTALL_DIR "C:\path\to\ghidra_12.1.4_PUBLIC"`, then restart
   the agent. A running MCP server keeps its spawn-time environment, so
   `binary_session` still reports `GHIDRA_INSTALL_DIR is not set` until that
   restart, even after `doctor` shows `ghidra` healthy.
5. The README asks for JDK 21; a newer full JDK (verified 25) also passes the
   launcher and the `ghidra-java` check. Do not downgrade `JAVA_HOME` on the
   README alone.

Never source a cracked IDA or Hopper build: they are common malware carriers,
and free Ghidra covers the Windows native lane. IDA Free cannot back the REA IDA
provider because it ships neither idalib nor the SDK.

IDA: pass the original input with `provider_id: "ida"`, never an `.idb`/`.i64`
database, and point `REA_IDA_MCP_CONFIG` at the upstream IDA MCP registration
JSON. Hopper is macOS-only (`HOPPER_LAUNCHER_PATH`, or setup-installed with
explicit approval).

## Host limits are availability facts, not defects

- macOS-only: Mach-O inspection, plist parsing, Apple asset catalogs, Swift
  demangling, native UI observation and scenario capture, `observe_native_calls`
  (LLDB). Elsewhere these return `available: false` with
  `availability_code: unsupported_host`; no installation changes that.
- Linux-only paths: firmware extraction and region inspection (Unblob 26.6.x or
  Binwalk), offline ELF layout and recorded crash cores (pwntools), native
  mitmproxy capture. Android class/method inspection expects a full JDK and
  headless JADX on Linux or macOS.
- Process capture needs a Linux/macOS PTY.
- Browser and website work needs a Chrome-family browser; Playwright's cached
  Chromium under `%LOCALAPPDATA%\ms-playwright` is what browser and Electron
  scenarios drive, and an installed Edge covers the ordinary browser case.

## Report the answer in layers

State first what is verified live (the server answered, which operations are
available), then each missing layer with its exact variable and value. Keep
`unsupported_host`, `missing_dependency` and `runtime_unavailable` distinct:
the first is platform, the second is an install, the third is a failed native
invocation that a later request may retry. Never present unconfigured client
registrations as broken tooling, and never claim native analysis works because
an engine name appears in the composite provider.
