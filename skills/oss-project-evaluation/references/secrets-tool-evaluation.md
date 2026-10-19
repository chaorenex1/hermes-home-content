# Secrets / credential tooling — evaluation axes

Companion to workflow steps 7–8. Covers the three axes this user drills in sequence:
security model → cross-platform → agent/automation fit. Verify fresh each time (asset
lists, flag sets, audit pages); never carry numbers or version claims between reviews.

## 1. Security model — group by the KEK / trust boundary

- OS keystore (Credential Locker/DPAPI, Keychain, Secret Service) — key protected by the
  login session; the strongest local model, and entries do NOT roam across machines.
- Passphrase + slow KDF (Argon2, scrypt) over an encrypted file/database.
- Hardware (YubiKey challenge-response, TPM, Secure Enclave) — check per-OS support.
- Wallet-style key file (age identity, secp256k1) — file is the secret; protect with ACLs.
- Cloud vault + local CLI — E2E encrypted server, session token locally, local machine
  never holds the master blob.
- Self-made scheme — judge harshly: where does the KEK's entropy come from? (checklist's
  public-material rule), which read paths are gated, what does "audited" point to.

## 2. Cross-platform — evidence procedure

- Per-OS support = the release asset matrix:
  `gh api repos/O/R/releases/latest --jq '.tag_name, (.assets[].name)'`.
  README "works everywhere" claims lose to the matrix; a single-OS asset list is an
  exclusion, and a missing arm64/legacy variant is worth one line when the user's
  machines differ.
- Asset presence ≠ component presence: to prove a specific binary ships in the target
  build (CLI next to the GUI), download that asset and list the archive
  (`python -c "import zipfile; print([n for n in zipfile.ZipFile('x.zip').namelist() ...])"`).
- Installer scripts: check the OS-detection branch (`uname -s` cases); no branch for the
  user's OS = manual install, include the real install path in the answer.
- `#[cfg(unix)]` / chmod hardening is a no-op on Windows — never repeat it as protection.
- Roaming taxonomy for multi-machine/multi-agent questions: file-based store (user syncs
  the file), repo-based (git carries ciphertext; per-secret files give smaller conflict
  granularity than a single opaque DB), service-based vault (server is the sync), OS
  keystore (no roaming). Name it explicitly; the user picks by need.

## 3. Agent / automation fitness — five axes

Non-interactive / no-echo injection / machine-readable / unlock model / ecosystem.

- Non-interactive: any GUI or TTY prompt (pinentry, password prompt, biometric) stalls a
  tool-calling agent. Verify from the repo's man-page source (`docs/man/*.adoc`, fetched
  raw) which prompt-suppression, stdin, keyfile or no-password flags exist — a missing
  non-interactive option is itself a finding.
- No-echo injection: prefer a subprocess-injection command that never prints the value —
  repo-encryption tools expose `exec-env`/`exec-file` subcommands, .env runners a `run --`
  prefix, pass-style stores an `env` subcommand, vault CLIs a get + session token. Know the
  caveats: child env vars are readable via `/proc/<pid>/environ` (or `ps eww`) for the
  child's lifetime; some implementations offer stdin or ramdisk-file alternatives.
- Machine-readable: script-mode flags (`show -o` style), JSON/`--raw` output, documented
  stable exit codes. Cite the doc line.
- Unlock model, map every candidate to one: sessionless (OS auto-unlock or key file —
  zero friction), agent-held session (unlock once, token in env, watch the timeout),
  per-call interactive (human use only). This decides where the agent sits in the flow.
- Ecosystem guardrails: official agent examples in the README; output redaction (a vendor
  shipping a [REDACTED] pattern for agent transcripts is a positive signal — name it and
  copy the pattern into wrappers); MCP servers via `gh search repos "<tool> mcp"` (most
  are hobby-grade — check stars); injected skill/rule files (READ them — some route the
  agent to plaintext reads, which is the opposite of a guardrail).

## Output shape

- Plain-text matrix, one row per tool, cells = evidence or a two-word verdict; group rows
  by mechanism (KEK source for security, roaming class for platform, unlock model for
  agent fit).
- State exclusions with the reason (single-OS assets, GUI-only unlock).
- End with a concrete pick for THIS machine (Windows + agent tool-calls) and an explicit
  "not installed / not end-to-end tested" line unless you actually ran it.
