---
name: gopass-source-manage
description: "Use when managing the gopass store that backs Hermes secrets (HERMES_HOME/gopass-source): install gopass and initialize the store on Windows, add or rotate entries, wire secrets.gopass bindings in config.yaml, or debug startup fetch failures (BINARY_MISSING / AUTH_FAILED / REF_INVALID)."
---

# gopass-source Manage Skill

Operate the gopass password store that the Hermes **gopass secret-source
plugin** (this plugin's parent directory) reads provider credentials from at
process startup. The store lives at `HERMES_HOME/gopass-source`, and decryption
goes through the local `gopass` CLI + the user's GPG agent — Hermes never
handles passphrases. This skill covers install / environment / initialize, the
day-to-day gopass command guide, and the gopass ↔ Hermes startup contract.

## When to use

- Add, rotate, or remove a secret Hermes should read from gopass.
- Set up or repair a machine: install gopass, fix the GPG home, initialize the store.
- A startup log shows gopass source errors — `BINARY_MISSING`, `AUTH_FAILED`,
  `REF_INVALID`, `NOT_CONFIGURED` — or `gopass: applied N secrets` looks wrong.
- Change `secrets.gopass` / `secrets.gopass_folder` bindings in `config.yaml`.

## Ground truth (verify before acting)

```bash
echo "$HERMES_HOME"            # Windows default: C:\Users\<user>\AppData\Local\hermes
gopass config mounts.path      # expect: <HERMES_HOME>/gopass-source
gopass recipients              # the store's recipient key (its .gpg-id)
gopass ls --flat               # existing entries
```

- Store root: `HERMES_HOME/gopass-source` (`.gpg-id`, `.public-keys/`,
  `config`, then `<entry>.gpg` files).
- gopass config file: `%APPDATA%\gopass\config` (edit via
  `gopass config <key> <value>`).
- Binary (winget): `%LOCALAPPDATA%\gopass\gopass.exe`; the user `PATH` must
  contain `%LOCALAPPDATA%\gopass` (winget does not add it).
- GPG home: `C:\Users\<user>\.gnupg`, pinned through
  `GNUPGHOME=/c/Users/<user>/.gnupg` (POSIX form — required, see 1.2).

## 1. Install, environment, initialize (Windows)

### 1.1 Install the gopass binary

```bash
winget install gopass.gopass
```

Winget installs to `%LOCALAPPDATA%\gopass\gopass.exe` and does **not** touch
`PATH`. Add `%LOCALAPPDATA%\gopass` to the **user** PATH (idempotent), keeping
the registry value type `REG_EXPAND_SZ`:

```powershell
$k = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Environment', $true)
$raw = $k.GetValue('Path', '', [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
if ($raw -notlike '*gopass*') {
  $k.SetValue('Path', ($raw.TrimEnd(';') + ';%LOCALAPPDATA%\gopass'),
              [Microsoft.Win32.RegistryValueKind]::ExpandString) }
$k.Close()
```

Alternatively pin `secrets.gopass.binary_path` in config.yaml and skip PATH.
Verify in a **new** shell: `gopass --version` → `gopass 1.17.3`.

### 1.2 Fix the GPG home — the part that breaks non-TTY fetches

Hermes fetches at startup without a TTY: the key must be usable without a
passphrase prompt (passphrase-less key, or an already-unlocked agent).

**Windows trap:** Hermes spawns gopass with a minimal environment (no `HOME`;
only the `run_secret_cli` base + plugin allowlist). The git-for-windows `gpg`
used here then resolves `GNUPGHOME` **only if it is set**, and it must be the
MSYS/POSIX form — a `C:\...` or `C:/...` value is mangled into a bogus homedir
(verified) and decryption fails with confusing errors. Set it in both places —
each covers a different launch context:

1. User environment (covers any context, all new processes):
   `GNUPGHOME=/c/Users/<user>/.gnupg` (REG_SZ — `setx GNUPGHOME /c/Users/<user>/.gnupg`
   or the `HKCU\Environment` registry value).
2. `HERMES_HOME/.env` line: `GNUPGHOME=/c/Users/<user>/.gnupg` — covers the
   Hermes process chain even when it was launched with a stale environment;
   `load_hermes_dotenv()` loads it before the first secret fetch.

**Stale gpg locks:** a leftover keyboxd lock set (`.#lk*` files,
`pubring.db.lock` under `~/.gnupg/public-keys.d/`) can wedge every gpg call
with `waiting for lock (held by <pid>) ... Connection timed out` even with no
gpg process running. Fix: kill `gpg-agent.exe` / `keyboxd.exe`, then move the
stale lock files away.

### 1.3 Create the store key (passphrase-less, batch)

```bash
cat > /tmp/keyparams <<'EOF'
%no-protection
Key-Type: eddsa
Key-Curve: ed25519
Key-Usage: sign,cert
Subkey-Type: ecdh
Subkey-Curve: cv25519
Subkey-Usage: encrypt
Name-Real: <name>
Name-Email: <email>
Expire-Date: 0
%commit
EOF
gpg --batch --pinentry-mode loopback --passphrase '' --generate-key <keyparams-file>
gpg --list-secret-keys      # confirm
```

`%no-protection` = no passphrase, which unattended startup fetches require (a
passphrase-protected key only works while its agent cache is warm — not
reliable across restarts). Skip this step when a suitable key already exists.

### 1.4 Initialize the store at the Hermes location

```bash
gopass config mounts.path '<HERMES_HOME>/gopass-source'   # tilde = user home
gopass setup --yes --crypto gpgcli --storage fs --name <name> --email <email>
gopass recipients        # → 0x… - <name> <email>
gopass ls                # initialized; an empty store prints just its name
```

`setup` writes `.gpg-id` into the mount root — that is what makes
`HERMES_HOME/gopass-source` *the* store. Round-trip smoke test (exactly the
`show` shape the plugin runs):

```bash
printf 'first\n---\nuser: alice\n' | gopass insert -f hermes/verify
gopass show -o --nofuzzysearch --nosync -- hermes/verify    # → first   (no trailing newline)
gopass show --nofuzzysearch --nosync -- hermes/verify user  # → alice
gopass rm -f hermes/verify
```

## 2. gopass operations guide

| Task | Command |
|---|---|
| Add / overwrite (pipeline-safe) | `printf '%s\n' "$VALUE" \| gopass insert -f <entry>` (or any stdin body) |
| Structured entry | first line = password, then a `---` line, then `key: value` lines |
| Read password only | `gopass show -o -- <entry>` |
| Read one field | `gopass show -- <entry> <key>` |
| List | `gopass ls --flat [<folder>]` |
| Delete | `gopass rm -f <entry>` / `gopass rm -r <folder>` |
| Rename / copy | `gopass mv <old> <new>` / `gopass cp <old> <new>` |
| Generate | `gopass generate -n 32 <entry>` |
| Recipients | `gopass recipients`, `gopass recipients add <key-id>`, then `gopass sync` |
| Git sync | `gopass git remote add origin <url>`; `gopass sync` |

Non-interactive scripting: always add `--nofuzzysearch --nosync` and put `--`
before entry refs (`-- <entry> [key]`). The plugin does exactly this.

Exit codes: `6` = store not initialized; `10` / `11` = entry (or `ls` prefix)
not found; `11` = retrieve/decrypt failure; `1` + "Incorrect Usage" = unknown
flag (older gopass rejects `--nofuzzysearch`/`--nosync` — drop them); `7` =
git (sync) failure.

Windows quirks: `ls --flat <multi-segment prefix>` may render separators as
`\` (`hermes\live/PLAIN`) — normalize before parsing. Winget installs need a
fresh shell for PATH.

## 3. gopass ↔ Hermes

The plugin (key `gopass`, deployed at `$HERMES_HOME/plugins/gopass`) provides
two secret sources, both **disabled by default**:

```yaml
secrets:
  gopass:                          # mapped: explicit ENV_VAR -> entry[#key]
    enabled: true
    env:
      OPENAI_API_KEY: hermes/openai
      SMTP_USER: gopass://email/smtp#user
  gopass_folder:                   # bulk: every entry under a folder
    enabled: true
    folder: hermes                 # hermes/FOO -> env var FOO
```

Per-source options: `binary_path`, `config_path` (pins `GOPASS_CONFIG`),
`sync` (default false → `--nosync`, so startup never waits on a remote),
`command_timeout_seconds` (default 30), `override_existing` (default true — a
vault value beats a stale `.env` line).

Startup flow: `.env` loads → plugin sources register → one
`gopass show -o --nofuzzysearch [--nosync] -- <entry> [key]` per binding →
`apply_all` merges: mapped outranks bulk; the first claim wins a contested var
(conflicts are warned, never silently clobbered); applied values carry
provenance (`(from gopass)`). Fetch failures are non-fatal: per-reference
problems become warnings, an all-failed fetch surfaces one source error with an
actionable hint, and an empty resolved value is never applied.

Child process: allowlisted environment only (`PATH`, `HOME`, `USERPROFILE`,
`GNUPGHOME`, `GOPASS_*`, `APPDATA`, `LOCALAPPDATA`, …); `GOPASS_NO_NOTIFY`,
`GOPASS_NO_REMINDER`, `CHECKPOINT_DISABLE` forced; stdin closed (a prompting
helper fails fast — never assume a TTY). The store is read-only for Hermes:
only `show` / `ls` run.

After changing `.env`, config bindings, or the plugin: **restart Gateway /
Desktop** — sources are fetched at process startup, and a running process
keeps its values. New sessions and processes pick everything up on their next
start.

## Common failures

| Symptom | Cause / fix |
|---|---|
| `gopass CLI was not found on PATH` (`BINARY_MISSING`) | PATH lacks `%LOCALAPPDATA%\gopass` (needs a fresh shell) — or pin `binary_path` |
| `could not decrypt` / `AUTH_FAILED` | Key locked or GPG-home mismatch: verify `GNUPGHOME` is the POSIX form in user env **and** `.env`; `gopass show <entry>` in a terminal must succeed without a prompt |
| `store is not initialized` (`NOT_CONFIGURED`) | `gopass config mounts.path` wrong, or the store was never `setup` — see 1.4 |
| `X is not in the password store` (`REF_INVALID`) | Typo in the binding; `gopass ls --flat` shows what exists |
| gpg `waiting for lock ... timed out` | Stale keyboxd locks — see 1.2 |
| Source enabled but `env` empty | `NOT_CONFIGURED` warning each startup; add bindings or disable |

## Verification (acceptance checks)

1. `gopass show -o --nofuzzysearch --nosync -- <entry>` prints exactly the
   stored value (no trailing newline).
2. Round-trip test from 1.4 — proves key + store + CLI without Hermes.
3. Plugin level: `hermes plugins show gopass` (or validate/doctor) plus, on a
   restarted process, the startup line `gopass: applied N secrets` and
   `(from gopass)` provenance in the agent's environment.
4. Full-chain probe (production shape): temp HERMES_HOME with
   `plugins.enabled: [gopass]`, a `secrets.gopass` block, and `.env` carrying
   `GNUPGHOME` → `load_hermes_dotenv()` → `discover_plugins()` → assert the env
   values and provenance. `scripts/live_e2e_check.py` covers the same path
   against a scratch store.

Never paste secret values into chat, logs, or commits — reference entries by
path only, and feed values to `gopass insert` through stdin.
