# Cookie import and login-state verification (camofox-search)

Use when `web_search`, `web_extract`, or `camofox-search-advance` stop carrying the user's logins; when a cookie import reports 0 cookies, "nothing to import", or all-undecryptable stats; or when you must prove which sites the authenticated profile is actually logged into.

Tool: `camofox-search-import-cookies` (`detect` | `run`), importing into the plugin profile `camofox_search`. The 72h scheduled job runs the same code path.

## Hard rules

1. **Back up the source `Cookies` DB before ANY experiment on a real profile** — the sqlite file plus `-wal`/`-shm` siblings, into scratch. It is the only recovery path if the store is purged, and it restores fully.
2. **Never debug-launch the user's real profile.** Any non-default `--user-data-dir` (junction to the real dir, or a copy) disables App-Bound Encryption; the browser then silently purges every `v20` cookie it can no longer decrypt. Test hypotheses on a copied fork profile only.
3. **Restore first, report always.** If a session dropped cookies (row count collapses; only fresh `v10` rows remain), restore from the backup, verify counts, re-verify with a plain no-flag launch, then disclose the incident and backup paths. Never bury it.
4. **Counts, prefixes, and domain buckets only** — cookie values are never printed.

## Source decision table

| Source state | Behavior | Action |
|---|---|---|
| Chromium store closed; values plaintext or `v10`/`v11` | File export decrypts via the Local State DPAPI key | `run` normally |
| All rows `v20` (app-bound) | File export → `exported: 0`, all undecryptable | rookie-cookies injection export (below); else Firefox source |
| Browser running, no debug port | Clean "profile is locked" error with CDP instructions | Expected; close the browser or accept |
| Debug browser on non-default dir | CDP export works but on ABE machines sees only post-launch cookies (`v20` purged) | Not a rescue for existing logins |
| Firefox profile present | Plaintext `cookies.sqlite` | Prefer as source |

## Procedure

1. `detect` → note profiles and `cdp` reachability.
2. Back up the chosen source's `Cookies` DB (rule 1).
3. `run` (optionally `dry_run: true`) → read `export.stats` (rows / exported / expired / filtered / undecryptable).
4. If `exported: 0` and `undecryptable == rows`, check value prefixes on the backup copy: `substr(encrypted_value,1,3)` per row. `v10`/`v11` = decryptable (a real bug to chase); `v20` = ABE machine (expected hard stop).
5. Non-dry `run` → require `verified: true` (`present_after >= accepted`; `present_after` counts pre-existing cookies too, so it can exceed `accepted`).
6. Independent check with `scripts/camofox-login-state-check.py` (below).

## Login-state verification

`scripts/camofox-login-state-check.py` is read-only and prints counts/booleans only. Run it with the plugin runtime (hermes-agent venv, Python 3.11) and both the camofox-search repo `plugin` dir and the hermes-agent tree on `PYTHONPATH`.

1. **Store summary first** — create a scratch tab, read its cookies, report row count, domain buckets, and presence of each site's auth-cookie name. This separates "domain never imported" (no rows at all) from "imported but not authenticated" (rows present, auth cookie absent).
2. **Live probe per site** — navigate, poll `document.readyState == "complete"` (≤15 s), settle ~1.5 s, then evaluate a durable discriminator: bilibili avatar vs login entry; GitHub `meta[name="user-login"]`; Google account link with no `ServiceLogin`; x.com account-switcher `data-testid`; zhihu `fetch('/api/v4/me')` status 200 vs 401. Prefer identity meta/API discriminators over CSS guesses — avatar and `AppHeader` selectors are unreliable on current pages.
3. **Interpret:** an auth-cookie name absent for a domain that HAS other rows means the SOURCE browser was not logged in there — anonymous/anti-bot rows are written logged-out too (zhihu `_xsrf`, `d_c0`, `assva*`, `SESSIONID`). That is not an import regression; do not re-import to "fix" it. Only a domain with zero rows points at an import gap.
4. **Cleanup** — close the scratch tab only, then confirm the profile's blank holder tab survived; a context's last tab tears the browser window down.

## App-Bound Encryption (modern Edge/Chrome)

A pure file-decryption export cannot open an all-`v20` store: the app-bound key needs the browser's own Elevator COM, not just DPAPI. Verified user-mode path: **rookie-cookies 0.6.0** (`pip install rookie-cookies`, cp311-abi3 wheel; no admin). Default `app_bound="injection_only"` spawns a suspended browser, reflective-COM-injects into it to unwrap the key, then decrypts a copy of the DB.

1. Close the browser fully (verify `tasklist /FI "IMAGENAME eq msedge.exe"` is empty). A running browser share-locks `Network/Cookies` (WinError 32), and non-admin sessions have no VSS fallback.
2. `rows = rookie_cookies.read(browser="edge").as_list()` → dicts keyed `domain/expires/http_only/name/path/same_site/secure/value`. Use canonical browser ids (`edge`, `chrome`, `brave`); `"auto"` is not accepted by the Python API.
3. Export with `rookie_cookies.to_netscape(rows)`, or map keys directly to the importer (`http_only`→`httpOnly`, `same_site`→`sameSite`, `expires` int; session → -1) and reuse `import_cookies(...)`.
4. Baseline diagnostic: with the browser CLOSED, `app_bound="disabled"` returns `all N Chromium cookie row(s) were skipped` — that count is the `v20` total. Delete `v20` rows from the list before a baseline retry or every row fails with the same typed error.

Caveats: EDR may flag the injection; DBSC (`chrome-bound-session-credentials`) sessions are not implemented, so a decrypted cookie may not replay on high-security sites. Neither debug-port escape hatch works on the real profile. Viable sources: Firefox (plaintext), or the Edge policy `ApplicationBoundEncryptionEnabled=0` (future cookies become `v10`; existing `v20` survival is unverified — test on a fork first; it weakens local protection). Full mechanism, fork-test, and recovery: `references/chromium-app-bound-cookie-encryption.md`.

## Import batching, sync run, and daemon auth

- Import batching is count-AND-byte aware (500 cookies / 64 KiB wire bytes). The camofox daemon 413s bodies over ~100 KB, and 500 real Edge cookies measure ~115 KB — never revert to pure count-based batching.
- Deploy through `python scripts/install_dev_plugin.py --target-hermes-home <HERMES_HOME> --replace`, then restart the gateway from an EXTERNAL terminal — a session that runs the deploy is a child of the gateway and an in-session restart self-terminates it.
- Manual sync uses the same code path as the scheduled job. `PYTHONPATH=<HERMES_HOME>/hermes-agent` is mandatory; without it `hermes_yaml` is unimportable, the API key resolves empty, and you get a red-herring `HTTP 403 Check CAMOFOX_API_KEY`. Install optional deps (rookie-cookies) into `hermes-agent/venv` (Python 3.11), the real plugin runtime.
- If the daemon returns 403 on POST while `/health` still answers, the profile's `CAMOFOX_API_KEY` is missing or stale. Prove it with an unauthenticated vs authenticated `POST /tabs`, read the key from the daemon's env (`docker inspect`), append the matching value to `<HERMES_HOME>/.env` (backup, keep CRLF), and retry on the next prompt — the secret scope rebuilds per prompt in the same process.

## Pitfalls

- `WinError 32` while copying `Cookies` with the browser open is expected — it is what triggers the CDP fallback. Do not retry the copy.
- `undecryptable == rows` is ABE, not a broken tool — do not retry the import.
- Junction cleanup: `cmd /c rmdir <link>` removes only the link; never `rmtree` a junction path.
- `taskkill /F /IM msedge.exe` kills all Edge trees; use it only after the user's browser was closed. `msedgewebview2.exe` processes are unrelated WebView2 hosts — never kill them, never count them as Edge running.
- rookie-cookies runs require the browser fully closed and no `msedge.exe` leftovers afterwards.
- Chromium `creation_utc` is microseconds since 1601: `unix = creation_utc/1e6 - 11644473600`; use it to attribute rows to a session.
- A plain no-flag launch preserves `v20` stores (only genuinely expired rows pruned). Normal pruning is not damage.
- JS-heavy sites: evaluate only after `document.readyState == "complete"` plus a short settle; an evaluate issued right after navigate returns an empty/stale DOM.
