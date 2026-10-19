# Toolchain recipes (verified on this host)

Paths assume `<USER_HOME>`. Re-check versions before reuse; treat version numbers as the shape of the recipe, not a pin.

## REA (rea-agents MCP)

- Server entry: `npx -y rea-agents@6.1.0 mcp` in `config.yaml` under `mcp_servers`.
- Readiness probe: `npx -y rea-agents@<ver> doctor --json` (exit 1 while any required check fails).
- Checks and what they mean:
  - `node`: `engines` is `^22.19.0 || ^24.11.0 || >=26`. npx ignores `engines`, so an older Node still runs but is unsupported.
  - `host`: `win32 x64` is supported.
  - `ghidra`, `ghidra-version`, `ghidra-headless`, `ghidra-native_decompiler`, `ghidra-java`: need `GHIDRA_INSTALL_DIR` pointing at the extracted dir that contains `support/analyzeHeadless`.
  - `hopper`: macOS/Linux only, absent on Windows by design.
  - `ida-registration`: `REA_IDA_MCP_CONFIG`; IDA Free lacks idalib, so it does not satisfy this provider.
  - `skill:identity`: installed by `rea setup` (workflow docs), not a runtime requirement.
- The MCP process reads the environment at spawn. After `setx GHIDRA_INSTALL_DIR`, `binary_session` keeps reporting `GHIDRA_INSTALL_DIR is not set` until the gateway restarts.

### REA CLI workflow

- `rea analyze <path> --format json` returns the overview: provider id, segments, `procedure_count`, `string_count`, target sha256.
- `rea search <path> <pattern> --kind procedures|strings`; `rea decompile <path> --procedure <name|addr>`; also `function`, `xrefs`, `trace`, `providers`.
- A PE entry point is usually named `entry`; notepad's decompiles to a two-call stub calling `FUN_*` addresses.
- Cost model: every CLI invocation imports the target into a throwaway Ghidra project and runs full auto-analysis. A 400 KB PE took ~170 s here, and `--snapshot <file>` persists only ~8 KB of metadata (JSON), not the project, so the next command pays the same 170 s again.
- For many questions about one binary, keep one MCP `binary_session` open (open once, query repeatedly) instead of shelling out per query; that path needs the gateway restart above. Do not assume a snapshot makes the second call cheap.

## Ghidra (native analysis provider)

1. Release asset is a ~543 MiB zip; extract to `C:/Users/<user>/tools/ghidra_<ver>_PUBLIC`.
2. `setx GHIDRA_INSTALL_DIR C:\Users\<user>\tools\ghidra_<ver>_PUBLIC` (new processes only).
3. Smoke test (project dir must already exist, otherwise `project directory does not exist`):

```bash
cmd.exe /c '<install>\support\analyzeHeadless.bat C:/Users/<user>/tools/ghidra_projects testproj -import C:/Windows/System32/notepad.exe -noanalysis'
```

Expect `REPORT: Import succeeded`. `support/analyzeHeadless` (the bash script) can fail under git-bash with `Could not find or load main class LaunchSupport`; call the `.bat` through `cmd.exe` instead.

4. The README asks for JDK 21. The 12.1.x launcher accepted JDK 25 here and `doctor` graded `ghidra-java` healthy. Only install Temurin 21 if the launcher itself errors on the JVM version.

## Node via nvm-windows

- `nvm list` shows installed versions; `nvm root` shows where they live.
- If `nvm install <ver>` reports `not available`, the configured `node_mirror` index is stale. Download `https://nodejs.org/dist/v<ver>/node-v<ver>-win-x64.zip`, extract into `<nvm root>\v<ver>\`, then `nvm use <ver>`.
- `nvm use` flips the `nodejs` symlink; bash caches command paths, so run `hash -r` before trusting `node -v`. Use `which -a node` when nvm4w and a bundled runtime are both on PATH.

## Interactive-login CLIs (BaiduPCS-Go)

- Install: official `BaiduPCS-Go-v<ver>-windows-x64.zip`, extract the `.exe`, add its dir to user PATH.
- The agent stops at the login prompt; credentials go in the user's own terminal:
  - `BaiduPCS-Go login` (interactive)
  - `BaiduPCS-Go login -bduss=... -stoken=...`
  - `BaiduPCS-Go login -cookies="BDUSS=...; STOKEN=..."`
- In practice the sign-in can also be completed from browser cookies with `rookie_cookies` when the user cannot type credentials into the agent's PTY; see `browser-login-cookie-import` for the extraction and the `.pan.baidu.com` STOKEN rule. Never echo the cookie values.
- Unauthenticated state reads `who` -> `uid: 0`. After login verify with `who` and `quota`, not with a config file.
- Config file holds BDUSS in plaintext (default `~/.config/BaiduPCS-Go/`, overridable with `BAIDUPCS_GO_CONFIG_DIR`); never sync or print it.
