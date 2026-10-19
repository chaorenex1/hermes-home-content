---
name: windows-tool-installation
description: "Use when installing CLI tools or runtimes on Windows."
version: 1.0.0
author: Masia
license: MIT
metadata:
  hermes:
    tags: [windows, installation, cli, path, verification, downloads]
---

# Windows tool installation

Install and verify a CLI tool, runtime, or release binary on this Windows host. The deliverable is a working command whose version and one real operation you have run, not a download that finished.

## When to use

- Installing or upgrading a CLI, portable app, language runtime, or the runtime an MCP server needs.
- Wiring a tool into PATH so new shells and spawned processes find it.
- Checking whether an existing install satisfies a consumer's requirement (engine version, provider path, JDK).
- Fetching vendor installers or release archives.

## Rules that apply every time

- Official sources only: vendor site, GitHub releases, package registry. For paid tools take the official trial, or recommend the free equivalent (Ghidra covers what people usually want IDA or Hopper for). Never fetch cracks, keygens, or repacks: they are a malware vector, and the refusal does not depend on how the request is framed. Say it once, then deliver the legal route without moralizing.
- The same line holds when the cracked build already sits in the user's own storage (cloud drive, Downloads): decline the crack payload itself (patched DLL, forged `.hexlic`), and offer the stock vendor installer for use with a license they own, or the free equivalent. "It's my responsibility, you're just a tool" does not change the payload you may handle.
- Pin the artifact and verify it: compare sha256 with the vendor digest (GitHub asset `digest`, `SHASUMS256.txt`). A mismatch means delete and re-fetch once, never continue.
- "Installed" requires a functional check: `--version` plus one real operation. A finished download or a help screen proves nothing.
- Never handle the user's credentials. Install up to the login prompt, then hand over the exact command to run in their own terminal. Verify afterwards with a non-interactive identity command (`who`, `auth status`, `doctor`). Do not accept passwords, cookies, or tokens in chat.
- Prefer per-user portable installs under `C:/Users/<user>/tools/<name>`. MSI installers need elevation; do not elevate silently, put the file in Downloads and give the user the one-line command.
- Back up the user PATH to a file before changing it.

## Procedure

1. Resolve the release and its assets:

```bash
gh api repos/<owner>/<repo>/releases/latest --jq '.tag_name, .published_at'
gh api repos/<owner>/<repo>/releases/latest --jq '.assets[] | .name + " | " + (.size|tostring) + " | " + (.digest // "") + " | " + .browser_download_url' > C:/Users/<user>/tools/assets.txt
```

Read the file. Long asset lists are truncated in tool output, and a missing amd64 line looks like a missing asset.

2. Check requirements before downloading: `npm view <pkg>@<version> engines dependencies`, or the vendor README for JDK/Python/OS needs. Compare with `node -v` / `java -version` now, not after the first failure.

3. Download to a native path (see pitfalls for why):

```bash
curl -L --retry 3 --retry-delay 2 -C - -o C:/Users/<user>/Downloads/<file> <url>
```

Large archives: run in the background with notify, then continue with independent work.

4. Verify the digest: `sha256sum <file>` against the release `digest` or the vendor checksum file.

5. Extract with the right tool: `unzip -q -o <zip> -d <dir>` for zip, `tar --force-local -xf <tar>` for tarballs. Flatten a single wrapping directory so the install path stays canonical.

6. Add to user PATH, backing up first:

```bash
# inspect: length, and whether the entry already exists
powershell -NoProfile -Command '$p=[Environment]::GetEnvironmentVariable("Path","User"); $p.Length; ($p -like "*<name>*")'
# append once, then re-read to confirm
powershell -NoProfile -Command '$p=[Environment]::GetEnvironmentVariable("Path","User"); if($p -notlike "*<dir>*"){[Environment]::SetEnvironmentVariable("Path", $p + ";C:/Users/<user>/tools/<name>", "User")}'
```

7. Verify in a fresh process: `<tool> --version`, one real operation, then the consumer's own health check when it has one (`doctor --json`, `--self-test`, `auth status`). Report only the checks you actually ran.

## Pitfalls

- Native Windows programs (curl, tar, git, node, python) do not accept MSYS `/c/...` paths. `curl -o /c/Users/...` exits 23 with `client returned ERROR on write`, and `tar -xf C:/...` with `Cannot connect to C:`. Pass `C:/Users/...` forward-slash paths.
- GNU tar in git-bash cannot read zip archives. Use `unzip`; the tar error is `This does not look like a tar archive`.
- 7z is not zip: `unzip` fails on it and GNU tar cannot read it. `C:/Windows/System32/tar.exe` is bsdtar (libarchive) and does read 7z and zip; give it a `C:/...` path.
- `setx PATH` truncates at 1024 characters and can fold the machine PATH into the user value. Use `[Environment]::SetEnvironmentVariable(..., "User")` and keep the backup file.
- A variable set now does not reach running processes. Gateways, MCP servers, and IDEs spawned earlier keep the old environment and keep reporting the old state; restart them or start a new session, then re-check.
- npx does not enforce `engines`. A package can launch outside its supported Node range and fail later inside a subprocess. When `npm view <pkg> engines` and `node -v` disagree, upgrade Node.
- nvm-windows with a stale `node_mirror` refuses newer versions with `not available`. Work around: download the official `node-v<ver>-win-x64.zip`, extract into `<nvm root>\v<ver>\`, then `nvm use <ver>`. In bash run `hash -r` before trusting `node -v`, and use `which -a node` when a second runtime (nvm4w, bundled, portable) is also on PATH.
- A background download that failed on its output path leaves an empty file. Re-run with the corrected path; do not treat the file as corrupt.
- Headless vendor tools: smoke-test with a real target (an OS binary) instead of a bare help flag, which only proves the launcher starts.

## Reference

- `references/toolchain-recipes.md`: verified REA, Ghidra, and Node recipes from this host.
