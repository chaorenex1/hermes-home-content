# Chromium cookie encryption on Windows (App-Bound Encryption era)

Applies to Edge/Chrome 127+; debug-port refusal on the default profile is 136+.

## Value formats (`cookies` table)

| Stored as | Meaning | Readable by |
|---|---|---|
| `value` column set | plaintext (all Firefox; a few Chromium rows) | anyone |
| `v10`/`v11` prefix | AES-256-GCM; key = `os_crypt.encrypted_key` (Local State), DPAPI-unwrapped, `DPAPI` header stripped; plaintext may carry a 32-byte binding prefix stripped after decrypt | user-mode file tools |
| `v20` prefix | app-bound encryption; key = `os_crypt.app_bound_encrypted_key` (`APPB\x01...`), dual-sealed (user + SYSTEM DPAPI); unwrap requires the elevation service validating the calling app | the browser only |

App-bound keys present + all rows `v20` = ABE active.

## The walls

1. User-mode tools can unwrap `encrypted_key` (so `v10` decrypts) but cannot unwrap the app-bound key (needs the SYSTEM half + elevation service) → `v20` rows unexportable from files.
2. `--remote-debugging-port` is ignored on the default user-data-dir. Exact stderr: `DevTools remote debugging requires a non-default data directory. Specify this using --user-data-dir.` The browser still starts normally; the port never opens.
3. Junction workaround and its cost: `cmd /c mklink /J <scratch>\EdgeDebugUD "<real User Data>"` then `--user-data-dir=<scratch>\EdgeDebugUD` passes the string check (port opens, real profile data used) — but a non-default data dir disables ABE, the store's `v20` rows become unreadable and the browser purges them (observed: full store → 0 rows; a later short session left only fresh `v10` rows). CDP `Network.getAllCookies` then shows only post-launch cookies. Net: debug-launching a real `v20` store destroys it.

## Verified behaviors

- Plain launch (no flags, default dir): `v20` store preserved; only expired rows pruned (single-digit-% shrinkage).
- Debug launch, non-default dir (junction or copy): `v20` purged; new cookies written as `v10`.
- File size is not a health signal after a purge: SQLite keeps free pages, so the DB can stay ~1.4 MB at 0 rows.
- `Network.getAllCookies` needs a page-level WebSocket (the browser-level one lacks the Network domain).

## Fork-test recipe (non-destructive)

1. `mkdir <scratch>\EdgeFork\Default\Network`
2. Copy from the BACKUP into it: `Local State`, `Default\Preferences`, `Default\Network\Cookies`.
3. Launch `msedge.exe --user-data-dir=<scratch>\EdgeFork --remote-debugging-port=9222 --enable-logging=stderr --v=1 about:blank` (stderr → file).
4. Poll `http://127.0.0.1:9222/json/version`; query a page target with `Network.getAllCookies`.
5. `taskkill /F /IM msedge.exe`; re-count rows in the fork's `Cookies` copy. Expected on an ABE profile: CDP saw only fresh cookies; the fork's `v20` rows are gone.
6. Cleanup: delete the fork dir; `cmd /c rmdir` any junction.

## Recovery recipe (a session purged a real store)

1. Confirm no `msedge.exe` is running (WebView2 processes are unrelated).
2. Back up the damaged DB for forensics; copy the pre-incident DB over `...\Network\Cookies`.
3. Remove a stale `<Cookies>-journal` (0-byte journals are inert); check for stray `-wal`/`-shm`.
4. Verify on the restored file: `select count(*)` + prefix distribution + size equals the pre-incident size.
5. Re-verify with a plain no-flag launch that the count survives (expired-row pruning only).
6. Report the incident with backup paths.

## Options when ABE blocks a transfer

- **Firefox as source:** `cookies.sqlite` is plaintext; the import tool's file path applies directly.
- **Edge policy** `ApplicationBoundEncryptionEnabled=0` (registry under `SOFTWARE\Policies\Microsoft\Edge`): new cookies become `v10`; whether existing `v20` rows survive the flip is unverified — test on a fork first. Disabling ABE weakens local cookie protection and is the user's call.
- **rookie-cookies injection** (browser closed, no admin): see `references/cookie-import-and-login-verification.md`.
