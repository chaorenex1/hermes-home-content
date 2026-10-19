---
name: hermes-secret-source-plugins
description: "Build/deploy Hermes secret-source plugins (gopass, vaults)."
version: 1.0.0
author: Masia
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, secrets, plugins, gopass, vault, password-manager]
    related_skills: [hermes-agent, hermes-web-provider-plugin]
---

# Hermes Secret Source Plugins

Build third-party secret-manager backends for Hermes. A working reference
implementation: `~/projects/gopass-source` (deployed at
`$HERMES_HOME/plugins/gopass`, plugin key `gopass`).

Developer guide (authoritative): `website/docs/developer-guide/secret-source-plugin.md`
in the hermes-agent tree; user guide: `website/docs/user-guide/secrets/index.md`.

## When to Use

- The user asks for a Hermes secret source / vault / password-manager plugin
  (gopass, Infisical, HashiCorp Vault, KeePassXC, OS keystore, ...).
- A secret-source plugin misbehaves: source not registered, values not applied
  at startup, missing provenance labels, or a plugin that loads nowhere.
- Installing, validating, or verifying a plugin under `$HERMES_HOME/plugins/`.

## Contract (what breaks others if violated)

- Subclass `agent.secret_sources.base.SecretSource`. It is the ONLY public
  import path — importing `agent.secret_sources._cache` or other underscore
  modules trips catalog rule 9 (private imports). `run_secret_cli`,
  `is_valid_env_name`, `classify_cli_error`, `coerce_float` are public.
- One required method: `fetch(cfg, home_path) -> FetchResult`. MUST NOT raise,
  MUST NOT prompt (startup is non-TTY; run_secret_cli closes stdin). Errors go
  in `result.error` + `result.error_kind` (ErrorKind enum).
- Class attrs: `name` (config key `secrets.<name>`, lowercase), `label`,
  `shape` (`mapped` outranks `bulk`), optional `scheme` (globally unique),
  `token_env_key` + `default_token_env` (auto-protects the bootstrap token var
  via `protected_env_vars`).
- The orchestrator (`agent.secret_sources.registry.apply_all`) owns ordering,
  precedence, conflicts, provenance — the source only fetches; never write
  `os.environ` yourself.
- Subprocesses: use `run_secret_cli(argv, allow_env=[...], extra_env={...},
  timeout=...)` — argv-only, minimal allowlisted child env, ANSI-scrubbed
  stderr, no color. Put user refs AFTER a `--` terminator. Base keep-list is
  `PATH/HOME/USERPROFILE/SYSTEMROOT/TMPDIR/TEMP/LANG/LC_ALL/XDG_*` — anything
  else (`GNUPGHOME`, `GOPASS_*`, `APPDATA`, `LOCALAPPDATA`) must ride
  `allow_env`.
- Validate with the conformance kit: subclass
  `tests.secret_sources.conformance.SecretSourceConformance` with a `source`
  fixture (hermes-agent checkout must be on sys.path).

## Plugin layout and enablement

- `$HERMES_HOME/plugins/<key>/{plugin.yaml, __init__.py, ...}`; `plugin.yaml`
  `kind: standalone`; `__init__.py` defines `register(ctx)` calling
  `ctx.register_secret_source(MySource())`. Relative imports work (package-style
  load); the loader probe is `hermes plugins validate <dir>` /
  `hermes plugins doctor <dir>`.
- **Plugin loading is OPT-IN**: a directory plugin only loads when its key is
  in `plugins.enabled` in config.yaml. `hermes plugins enable <key>` writes it
  and hot-reloads a running gateway ("nothing needs a session or restart" when
  the plugin only registers providers). Sources stay inert until
  `secrets.<name>.enabled: true`.
- Startup flow: `load_hermes_dotenv()` runs at import; after plugin discovery
  `_refresh_secret_sources_after_discovery` re-pulls when any registered
  plugin source `is_enabled(cfg)` — a first process still gets plugin
  backends (fail-open, idempotent).

## Deploy pattern (user's convention)

- Repo at `~/projects/<name>/` mirroring camofox-search: `plugin/<key>/`,
  `scripts/install_dev_plugin.py` (validate, backup to
  `$HERMES_HOME/backups/plugins/`, copytree, SHA-256 verify), `tests/`,
  `pyproject.toml` with `[project.entry-points."hermes_agent.plugins"]`.
- Deploy: `python scripts/install_dev_plugin.py --target-hermes-home
  "$HERMES_HOME"` then `hermes plugins enable <key>`.
- Test env: scratch `uv venv` + pytest; PYTHONPATH includes the hermes-agent
  checkout (only `agent.secret_sources.base` + `registry` +
  `hermes_constants` are needed — stdlib-only). For REAL integration probes use
  `hermes-agent/.venv/Scripts/python.exe` (has dotenv/yaml), NOT the tools
  python (bare interpreter).

## Bundled plugin skills (standalone plugins)

- A native plugin (plugin.yaml) does NOT get its `skills/` dir auto-scanned —
  `register(ctx)` must call `ctx.register_skill(name, skill_md_path,
  description=..., frontmatter={...})` per skill (portable Agent-Plugin v1
  packages ARE auto-scanned; `hermes_cli/plugins_content.py` owns the ctx
  method). Copy camofox-search's `_register_skills`: `getattr(ctx,
  "register_skill", None)` guard, scan `<plugin>/skills/*/SKILL.md`, hand over
  the parsed frontmatter — the listing row uses what you pass, the file is not
  re-read for it.
- Qualified name = `<manifest name>:<skill dir name>`; appears in skills_list /
  skill_view / `/plugin:skill` slash commands while the plugin is enabled.
- `hermes plugins validate <dir>` runs register() in isolation and scans every
  bundled SKILL.md — a skill that mentions the gpg dir earns a cosmetic
  `gpg_dir_access` caution (still passes).
- Loader-level check without the gateway: temp HERMES_HOME + plugin copy +
  `discover_plugins()` → `manager.list_plugin_skills(key)`,
  `find_plugin_skill("key:skill")`, `get_plugin_skill_commands()` projection.

## Windows gotchas (hit in practice)

- The tools python dir under `%LOCALAPPDATA%\hermes\tools\python-*` displays
  redacted (`202****`); never retype it — resolve with
  `ls -d <HERMES_HOME>/tools/python-*/python.exe` and `cygpath -w`
  before handing paths to native tools (uv, gopass).
- MSYS gpg (git-for-windows `usr/bin/gpg.exe`) needs a POSIX-form GNUPGHOME
  (`/c/Users/...`); a native Gpg4win build needs the Windows form. Retry the
  other form on failure; pre-create the gnupg dir (gpg may not create it via
  the MSYS layer).
- Pass GNUPGHOME/GOPASS_CONFIG/GOPASS_HOMEDIR/APPDATA/LOCALAPPDATA through the
  source's `allow_env`; force `GOPASS_NO_NOTIFY=1`, `GOPASS_NO_REMINDER=1`,
  `CHECKPOINT_DISABLE=1`; with sync enabled add `GIT_TERMINAL_PROMPT=0` and
  `GCM_INTERACTIVE=never`.

## gopass facts (verified 1.17.3, Windows)

- `gopass show -o --nofuzzysearch [--nosync] -- <entry>` → password field,
  NO trailing newline. Key mode: `gopass show ... -- <entry> <key>` (no -o).
- Exit codes: missing entry/key rc=11 (docs claim 10; distinguish by stderr
  "not in the password store"/"key not found"); uninitialized store rc=6;
  `ls --flat <missing>` rc=10; unknown flag rc=1 + "Incorrect Usage: flag
  provided but not defined". An old gopass lacking `--nofuzzysearch`/`--nosync`:
  detect usage error once per fetch and drop both flags.
- `ls --flat <multi-segment-prefix>` renders the requested prefix's separators
  as backslashes on Windows (`hermes\live/PLAIN`) — normalize `\`→`/` before
  prefix matching and before using paths as references.
- `--` terminator works for show and ls; `setup --crypto gpgcli --storage fs
  --name X --email Y` is non-interactive (`--create` means create-team and
  needs `--team`); insert via stdin: `gopass insert -f entry`.
- Store location: `gopass config mounts.path` (write with a quoted value:
  `gopass config mounts.path '<HERMES_HOME>/gopass-source'`);
  `gopass setup --yes --crypto gpgcli --storage fs --name X --email Y`
  initializes at that mount root (`.gpg-id`, `.public-keys/`, store `config`).
- `mounts.path` is the store knob; `GOPASS_CONFIG`/`GOPASS_HOMEDIR` only move
  which config is read.
- gpg home: the git-for-windows MSYS gpg needs `GNUPGHOME` in POSIX form
  (`/c/...`) — native forms (`C:\...`, `C:/...`) mangle the homedir (verified
  with `gpgconf --list-dirs`). Hermes spawns gopass with no HOME, so set
  GNUPGHOME in the user environment AND in `$HERMES_HOME/.env` (dotenv loads
  before the first fetch; the plugin allowlist passes it through).
- Stale keyboxd dotfile locks (`~/.gnupg/public-keys.d/.#lk*`,
  `pubring.db.lock`) wedge every gpg call with "database_open ... waiting for
  lock (held by <pid>) ... Connection timed out" even with zero gpg processes:
  kill gpg-agent/keyboxd, move the lock files away.
- winget installs gopass to `%LOCALAPPDATA%\gopass\gopass.exe` without PATH —
  append `%LOCALAPPDATA%\gopass` to the user PATH (keep REG_EXPAND_SZ) or pin
  `secrets.gopass.binary_path`.

## Migrating/rotating .env credentials into the store

- Migration shape used in practice: parse with python-dotenv `dotenv_values`
  (last assignment wins), select credential-shaped keys
  (`_KEY|_TOKEN|_SECRET|_PASSWORD|_AUTH`…), `gopass insert -f hermes/<NAME>`
  with the value on stdin, then `show -o` readback-compare IN MEMORY — never
  print values; back up `.env` first (`.env.bak-gopass-migrate-<ts>`).
- Only single-line values work: the plugin reads the password field (first
  line), so a multiline .env value would be served truncated — exclude and
  report instead of migrating.
- Keep bootstrap vars (GNUPGHOME …) OUT of the store: the fetch needs them
  before gopass can decrypt anything.
- Enable the source via the CLI, not hand edits: `hermes config set
  secrets.gopass_folder.folder hermes` (+ `.binary_path` absolute pin, +
  `.enabled true`). `hermes config check` actually exercises the sources and
  prints e.g. `gopass folder: applied 13 secrets` — a free live E2E.
- After enabling, the folder source overrides same-named .env values
  (override_existing default true) — rotating a credential means updating the
  STORE, not .env; leave stale .env lines as offline fallback at most.

## Verification ladder

1. Offline: pytest (unit + conformance kit), fake `run_secret_cli` script list
   (recorded argv/allow_env/extra_env).
2. Live E2E: `scripts/live_e2e_check.py` — scratch passphrase-less key
   (`%no-protection` param file) + isolated store + real fetch assertions.
3. Platform: `hermes plugins validate <dir>` and `hermes plugins doctor <dir>`.
4. Startup probe (the real thing): temp HERMES_HOME with `plugins.enabled:
   [<key>]` + config.yaml `secrets:` block + .env bootstrap vars; script does
   `load_hermes_dotenv(hermes_home=...)` → `discover_plugins()` → assert
   `os.environ` values and `get_secret_source(var)` provenance.

## Pitfalls after cleanup

- Exported env vars in the terminal session PERSIST across calls — after an
  E2E cleanup, unset GOPASS_SOURCE_LIVE/GNUPGHOME/... or live pytest runs
  against a deleted store and errors in fixtures (looks like a regression).
