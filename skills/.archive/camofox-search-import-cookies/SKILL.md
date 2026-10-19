---
name: camofox-search-import-cookies
description: Use when testing or fixing camofox-search cookie import.
version: 1.0.0
platforms: [windows]
metadata:
  hermes:
    tags: [camofox, cookies, browser, windows, abe]
    related_skills: [browser-automation-cdp, cdp-browser-automation]
---

# camofox-search: Cookie Import

Goal: keep the user's local-browser logins available to camofox so `web_search` / `web_extract` / `camofox-search-advance` run authenticated. Tool: `camofox-search-import-cookies` (`detect` | `run`), importing into the plugin profile (`camofox_search`). The 72h scheduled job runs the same logic. Safe test order, source-browser choice, App-Bound Encryption blockers, verification, and incident recovery below.

## When to Use

- Testing or re-running the camofox-search cookie import (manually, or after the 72h job).
- `web_search` / `web_extract` don't carry the user's logins.
- Testing which sites the profile is actually logged into ("login state" report) — run `scripts/login_state_check.py` (see Login-state verification).
- An import reports 0 cookies, "nothing to import", or all-undecryptable stats.
- Any debugging that touches Edge/Chrome profile cookie stores on Windows (ABE blockers, locked DB, purge recovery).

## Hard rules (always)

1. Back up the source Cookies DB before ANY experiment on a real profile — even a "harmless" browser relaunch for a test. Save the sqlite file plus `-wal`/`-shm` siblings to scratch. It is the only recovery path if the store is purged, and it restores fully (recovery recipe in the reference file).
2. Never debug-launch the user's real profile. Any non-default `--user-data-dir` (junction to the same dir, or a copy) disables App-Bound Encryption; the browser then purges every `v20` cookie it cannot decrypt — silently, unrecoverably without rule 1. Test hypotheses on a copied fork profile; never the live one.
3. Restore-first, report always: if a session dropped cookies (row count collapses; only fresh `v10` rows remain), restore from the backup, verify counts, re-verify with a plain no-flag launch, then disclose the incident and backup paths in the result. Never bury it.
4. Counts, prefixes, and domain buckets only — cookie values are never printed.

## Source decision table

| Source state | Behavior | Action |
|---|---|---|
| Chromium store closed; values plaintext or `v10`/`v11` | File export decrypts via the Local State DPAPI key | `run` normally |
| All rows `v20` (app-bound) | File export → `exported: 0`, all undecryptable | rookie-cookies injection export (see ABE section); else Firefox source |
| Browser running, no debug port | Clean "profile is locked" error with CDP instructions | Expected; close the browser or accept |
| Debug browser on non-default dir | CDP export works but on ABE machines only sees post-launch cookies (`v20` purged) | Not a rescue for existing logins |
| Firefox profile present | Plaintext `cookies.sqlite` | Prefer as source |

## Procedure

1. `detect` → note profiles and `cdp` reachability.
2. Back up the chosen source's Cookies DB (rule 1).
3. `run` (optionally `dry_run: true`) → read `export.stats` (rows / exported / expired / filtered / undecryptable).
4. If `exported: 0` and `undecryptable == rows`: check value prefixes on the backup copy — `substr(encrypted_value,1,3)` per row. `v10`/`v11` = decryptable (a real bug to chase); `v20` = ABE machine (expected hard stop).
5. Non-dry `run` → require `verified: true` (`present_after >= accepted`; `present_after` counts pre-existing cookies too, so it can exceed `accepted`).
6. Independent check: run `scripts/login_state_check.py` (see Login-state verification below) — store summary plus live logged-in probes on login-walled sites. Counts/booleans only.

## Login-state verification ("is the profile logged in?")

Run `scripts/login_state_check.py` (invocation in its docstring: hermes-agent venv with the repo `plugin` dir and hermes-agent on `PYTHONPATH`). Read-only; counts/booleans only. Workflow it implements:

1. Store summary first — create a scratch tab, `client.get_tab_cookies(tab, uid)`: row count, domain buckets, and presence of each site's auth cookie name. This separates "domain never imported" (no rows at all) from "imported but not authenticated" (rows present, auth cookie name absent).
2. Live probe per site — navigate, poll `document.readyState == "complete"` (≤15 s), settle ~1.5 s, then evaluate a durable DOM/API discriminator: bilibili avatar (`.header-avatar-wrap,.bili-avatar`) vs `.header-login-entry`; github `meta[name="user-login"]` exists; google account link (`a[href*="myaccount.google.com"]`) and no `ServiceLogin`; x.com `/home` renders `[data-testid="SideNav_AccountSwitcher_Button"]`; zhihu `fetch('/api/v4/me')` status 200 vs 401.
3. Interpret: an auth cookie name absent for a domain that HAS other rows means the SOURCE browser was not logged in to that site — anonymous/anti-bot rows are written logged-out too (zhihu: `_xsrf`, `d_c0`, `assva*`, `SESSIONID`). This is not an import regression; don't re-import to "fix" it. Only a domain with zero rows points at an import gap.
4. Cleanup: close the scratch tab only, then confirm the profile's blank holder tab survived (`client.list_tabs(uid)`) — a context's last tab tears its browser window down.

## ABE machines (modern Edge/Chrome)

A pure file-decryption export cannot open an all-`v20` store — the app-bound key needs the browser's own Elevator COM, not just DPAPI. Tested working user-mode path: **rookie-cookies 0.6.0** (`pip install rookie-cookies`, cp311-abi3 wheel; no admin). Default `app_bound="injection_only"` spawns a suspended browser process and reflective-COM-injects into it to unwrap the v20 key, then decrypts a copy of the DB. Recipe:

1. Close the browser fully (verify `tasklist /FI "IMAGENAME eq msedge.exe"` is empty) — a running browser share-locks `Network/Cookies` (WinError 32), the Python binding deliberately exposes no process-shutdown authorization, and non-admin sessions have no VSS/shadow-copy fallback.
2. `rows = rookie_cookies.read(browser="edge").as_list()` → dicts with keys `domain/expires/http_only/name/path/same_site/secure/value`. Use full canonical browser ids (`edge`, `chrome`, `brave`); a bare `"auto"` is NOT accepted by the Python API (`rc.profiles("<id>")` lists profiles).
3. Export for import: `rookie_cookies.to_netscape(rows)` (takes List[Dict], returns str; `#HttpOnly_` prefix rows are real cookies, not comments). Map keys to camofox export dicts: `http_only`→`httpOnly`, `same_site`→`sameSite`, `expires` int (session → -1), then reuse `import_cookies(client, user_id, cookies)` unchanged.
4. Verified on Edge 155: 1283/1283 rows v20; `app_bound="disabled"` baseline shows `ProviderFailed` per row; default run decrypted 1261 rows (~19 `invalid_octets` warnings, rest expired); spawned `msedge.exe` cleaned up; no admin needed. Baseline diagnostic trick: with the browser CLOSED, `app_bound="disabled"` returns `all N Chromium cookie row(s) were skipped` — that count is the v20 total. Delete v20 rows from the list before a baseline retry or every row fails again with the same typed error (the row-level `Failed to unseal` log spam is normal, one line per row).

Caveats: EDR may flag the injection (documented upstream); DBSC (`chrome-bound-session-credentials`) sessions are not implemented, so a decrypted cookie may not replay on high-security sites. Neither debug-port escape hatch works on the real profile — the default data dir refuses the port, and a junction/copy that satisfies the check kills ABE and purges the store. Viable sources: Firefox (plaintext, file path applies), or the Edge policy `ApplicationBoundEncryptionEnabled=0` (future cookies become `v10`; whether existing `v20` rows survive the flip is unverified — test on a fork first; it weakens local cookie protection). Full mechanism, fork-test and recovery recipes: `references/edge-chromium-cookie-encryption.md`.

## Integrated export (repo code) & live operations

`plugin/camofox_search/cookies.py` embeds the rookie path: `export_cookies` prefers rookie-cookies for Chromium whenever it is importable (any failure falls back to the built-in DPAPI/sqlite path; Firefox never uses it). `CAMOFOX_SEARCH_COOKIE_APP_BOUND` selects the recovery policy (`injection_only` default, `disabled`, `allow_elevated_fallback`); the optional dep is the `abe` extra in `pyproject.toml`. Import batching is count-AND-byte aware (500 cookies / 64 KiB wire bytes — see pitfalls).

Deploy: `python scripts/install_dev_plugin.py --target-hermes-home <HERMES_HOME> --replace` (hash-verified copy, old version backed up under backups/plugins/web/). Then restart the gateway from an EXTERNAL terminal (`hermes gateway restart`) — the interactive session that runs the deploy is a child of the gateway process, so an in-session restart self-terminates the session.

Manual sync run (same code path as the 72h cron job):

```bash
cd <HERMES_HOME>
PYTHONPATH="<HERMES_HOME>/hermes-agent" \
  "<HERMES_HOME>/hermes-agent/venv/Scripts/python.exe" \
  scripts/camofox_cookie_sync.py
```

Live acceptance (Edge 155, browser closed): `browser=edge profile=Default exported=1196 accepted=1196 batches=5 present_after=1247 verified=True`.

## Pitfalls

- `WinError 32` when copying Cookies while the browser runs is expected (exclusive lock) — it is what triggers the CDP fallback. Don't retry the copy.
- `undecryptable == rows` is ABE, not a broken tool — don't retry the import.
- Junction cleanup: `cmd /c rmdir <link>` removes only the link; never `rmtree` a junction path.
- `taskkill /F /IM msedge.exe` closes all Edge trees (including startup-boost leftovers); only use it when the user's browser was closed before the test.
- rookie-cookies runs need the browser fully closed AND no `msedge.exe` leftovers afterwards (the injection spawn cleans itself up); `msedgewebview2.exe` processes are unrelated WebView2 hosts, never kill them, never count them as Edge running.
- The camofox daemon 413s request bodies over ~100 KB (express json limit): a 500-cookie batch of real Edge data measures 115 KB — do not "fix" batching back to pure count-based. `cookies.import_cookies` splits by count (500) AND 64 KiB of wire bytes (`MAX_BATCH_BYTES`; `ensure_ascii` sizing matches what `requests` sends).
- Hand-running the sync script without `PYTHONPATH=<hermes-home>/hermes-agent` makes `hermes_yaml` unimportable → the API key silently resolves to empty → red-herring `HTTP 403 Check CAMOFOX_API_KEY`. Install optional deps (rookie-cookies) into `hermes-agent/venv` (Python 3.11), which is the real plugin runtime — not the `installs/.../environments/*/venv` that the hermes launcher shim points at.
- Chromium `creation_utc` = microseconds since 1601: `unix = creation_utc/1e6 - 11644473600`; use it to attribute rows to a session.
- A plain no-flag launch preserves `v20` stores (only genuinely expired rows pruned) — normal pruning is not damage.
- Login probes: prefer identity meta/API discriminators over CSS guesses — GitHub `img.avatar` and zhihu `.AppHeader*`/`img.Avatar` selectors are absent or unreliable on current pages; `meta[name="user-login"]` (github) and `z_c0` + `/api/v4/me` status (zhihu) are the durable checks.
- JS-heavy sites: evaluate only after `document.readyState == "complete"` (poll, ≤15 s) plus a ~1.5 s settle — an evaluate issued right after navigate returns an empty/stale DOM (header queries come back `null`).
