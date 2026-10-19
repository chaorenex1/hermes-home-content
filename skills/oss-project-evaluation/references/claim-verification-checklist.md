# Claim-verification checklist (adoption review)

Run these against the SOURCE, not the README. Each rule names the mechanism so you
spot the class of problem, not just one instance of it.

## Verification mechanics

- Fastest implementation check, no clone needed: `gh search code '<SYMBOL> repo:OWNER/REPO'`
  finds the constant/cipher/KDF in the source and yields a citable `path:line`. If it
  returns empty (indexing gaps happen), fetch the file directly:
  `gh api repos/OWNER/REPO/contents/<path> -H 'Accept: application/vnd.github.raw'` and
  grep locally — never re-run the identical search.
- CLI flag semantics (prompt behaviour, script mode, stdin/keyfile options) come from the
  repo's man-page source: list `docs/man/`, fetch the `.adoc` raw, grep
  `stdin|prompt|quiet|no-password`. Cite flags, not the marketing page.
- External pages (specs, security/audit pages): `curl -fsSL <url> -o page.html`, then
  `grep -ioE '(argon2[a-z]*|cure53|scrypt|...)' page.html | sort | uniq -c` — keyword
  counts on the raw page are quotable evidence, and this path also works when a
  page-extraction tool errors on the site. A 404 means the claim's real home is
  elsewhere — do not cite it.
- Audit/compliance claims: cite only from the vendor's audit page (naming firm AND
  scope) or the auditor's report. "Audited" in a README without a firm/scope is marketing.
- Keep fetched READMEs/pages in the scratch reads dir and cite file+line from there, so
  the user can reopen the exact evidence.

## Secrets / crypto (tools that store credentials)

- Find the KEK's entropy source. A key-encryption-key derived from PUBLIC material
  (e.g. SHA-256 of an SSH public key) is obfuscation, not encryption: whoever obtains
  the encrypted blob plus the public data decrypts it. Real guards derive from a secret
  only the user has (private-key signature, passphrase, OS keystore/DPAPI).
- Check every READ path for a gate. If one niche command demands a second factor while
  the bulk `get`-style command prints plaintext for any local caller, the security story
  is procedural, not technical — say exactly that.
- Enumerate what the process talks to: grep `https?://` across the source tree. Compare
  with "zero network" / "purely local" claims. Self-updaters, key-validation probes and
  any remote backend count as network.
- Localhost web UIs: check bind address, whether ANY token/origin check exists, and the
  response headers. An unauthenticated API that returns secret values with
  `Access-Control-Allow-Origin: *` is readable by any page the user has open while the
  server runs — a text/plain POST is a CORS-simple request, so no preflight stands in
  the way. "Binds to 127.0.0.1" is an address, not an access control.

## Supply chain

- `curl … | bash` installers and self-updates that re-run the installer: does anything
  verify a checksum or signature? If not, say so, and say what the installer does to
  the OS (removes entries, symlinks, PATH edits, data-dir moves).
- Where do release binaries come from — CI in the repo, and does the asset matrix match
  the claimed platform support?
- Asset presence ≠ component presence: to prove a specific binary ships inside a release
  archive (a CLI alongside a GUI), download the asset and list it
  (`python -c "import zipfile; ..."`) before citing it as evidence.

## Platform support (audit against the user's OS — Windows)

- Installer scripts: does target detection have a branch for the OS at all
  (`uname -s` cases listing only Linux/Darwin → Windows installs are manual).
- Permission handling: `chmod 0600` / `cfg(unix)` hardening is a no-op on Windows; files
  inherit NTFS ACLs, which is weaker than the docs imply. Report the no-op as a no-op.
- Integration paths hardcoded to `~/.<tool>`: on Windows the real location differs
  (Hermes lives at `%LOCALAPPDATA%\hermes`, active profile `default`). An agent-connector
  writing `~/.hermes/profiles/free/...` silently skips this machine — verify against the
  actual home layout before believing the feature works.
- A skill/manifest declaring `platforms: [linux, macos]` is a signal even when a Windows
  binary exists: the Windows path is untested.

## Maintenance health

- Distinct contributors, release cadence, commit subjects, open issues.
- Single maintainer + "it stores all your credentials" = bus-factor risk worth naming
  explicitly in the verdict.
- Interop/compatibility test fixtures (old-format round-trips) are a positive signal —
  mention them when present.