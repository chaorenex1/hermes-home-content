# Camofox profile model + local-browser cookie import (depth)

Verified against camofox-browser 2.4.8 (container `camofox-browser`, engine camoufox) and
Edge 155 on Windows. Read this when a plugin must browse with the user's logins, when adding a
cookie-import tool, or when tabs/contexts misbehave.

## Daemon session/profile model

- A plain tab (`POST /tabs {userId, sessionKey}`) runs in the user's CANONICAL profile, keyed
  `u:<base64url(utf16le userId)>`; session-scoped profiles (`s:user:sessionKey`, `p:…:signature`)
  appear only when proxy/geo overrides were established for that (userId, sessionKey).
- Profile directories persist on disk across `DELETE /sessions/:userId` (that call closes the
  context and clears only in-memory maps). Implication: cookies written into a profile survive
  process restarts and later sessions of the same userId.
- `DELETE /sessions/:userId` does NOT delete profile dirs; there is no daemon API to wipe one.
- `POST /tabs`: `userId` + `sessionKey` required (sessionKey groups tabs; the core Hermes
  `tools/browser_camofox.py` sends `listItemId`, the daemon accepts both). `url` optional and
  must be http(s) — `Blocked URL scheme: about:` otherwise, so blank tabs OMIT the field.
- `GET /tabs?userId=X` → `{running, tabs:[{tabId,targetId,url,title,listItemId}]}`; the UNFILTERED
  `GET /tabs` returns `[]` (it looks up tabs for `undefined`), so always filter by user when
  checking for leftovers.
- `DELETE /tabs/:tabId` needs `{userId}` in the JSON body (a DELETE with body — fine via
  `requests.delete(..., json=...)`).

## The holder-tab invariant (Camoufox quirk)

Closing a context's LAST tab destroys its browser window; afterwards every `Browser.newPage`
fails with HTTP 500 (`can't access property "delayedStartupPromise", window is null`) until the
context is closed. Algorithm for any per-call-tab design on a stable profile:

1. Before the work tab: if `GET /tabs?userId=` is empty, create a blank tab (the HOLDER).
2. Do the call's work, then close only the WORK tab; never the holder.
3. On a work-tab create failure, heal exactly once: `DELETE /sessions/:userId` → ensure holder →
   retry the create. More retries than one just burn latency.

The failure only shows up on the SECOND sequential call after a clean profile, so a repeat
create/close cycle belongs in the live smoke — a one-tab smoke passes and hides it.

## Cookie import endpoint contract

`POST /sessions/:userId/cookies` (JSON limit 512 KB):

- Body `{cookies: [...], tabId?: string}`; ≤500 cookies per request → batch larger sets.
- Each cookie needs non-empty `name`, string `value`, non-empty `domain`; optional `path`,
  `expires` (unix seconds; -1 session), `httpOnly`, `secure`, `sameSite` (only strict Playwright
  values pass).
- Without `tabId` the daemon requires a canonical profile with EXACTLY ONE active session
  (`409 No canonical profile` / `No active session` / `Ambiguous active sessions`) — pass the
  caller's own `tabId` and none of those checks apply.
- Response `{ok, userId, count}`; `count` is the browser-accepted number. Verify by reading
  back `GET /tabs/:tabId/cookies?userId=` and comparing `(domain, name)` keys.
- Never log or return cookie values: emit counts and skip reasons only.

## Exporting the USER's browser cookies (Windows)

Detect profiles by scanning standard roots: `%LOCALAPPDATA%` for Chromium family
(Chrome/Edge/Brave/Chromium/Vivaldi `…/User Data/<Profile>/Network/Cookies`), `%APPDATA%`
`Mozilla/Firefox/Profiles/*/cookies.sqlite`. Pick the most recently modified when told `auto`.

Chromium value decryption pipeline:

1. `Local State` → `os_crypt.encrypted_key` (base64) → strip the 5-byte `DPAPI` prefix →
   `CryptUnprotectData` (ctypes) → 32-byte AES-GCM key. A wrong-shape result means key trouble,
   not cookie trouble.
2. Blob `v10`/`v11` → AES-256-GCM: nonce = bytes 3:15, ciphertext+tag = 15:.
3. Plaintext → UTF-8. When that fails, modern Chromium/Edge prepends 32 BYTES OF BINDING DATA
   before the value (`pt[32:].decode()` — verified 41/41 on Edge 155). Strip, never keep.
4. `v20` (app-bound) is not decryptable outside the browser — count and skip. Legacy blobs (no
   version prefix) are raw DPAPI payloads.
5. Copy `Cookies` + `-wal` + `-shm` to a temp dir FIRST and open the COPY read-write (read-only
   WAL replay is fussy). Expired rows and `(domain, path, name)` duplicates are dropped.

Mapping to Playwright cookie dicts: chromium `samesite` -1/0/1/2 → absent/None/Lax/Strict,
firefox `sameSite` 0/1/2 → None/Lax/Strict; drop `sameSite` for `None` on a non-secure cookie
(Playwright rejects it); `expires_utc` 0 (or firefox expiry ≤0) → `-1`.

Locked database: a RUNNING Chromium-family browser locks `Cookies` with a denying share mode —
`shutil.copy2` raises `PermissionError WinError 32` persistently (measured 30/30 over 30 s), not
just during writes. Retry once, then raise a distinct error whose message names the lock, the
browser, and both outs (close it, or use a CDP-enabled browser). Never force-kill the user's
browser.

CDP fallback (works while the browser runs, needs `--remote-debugging-port=9222`):

- Reachability probe: `GET http://127.0.0.1:<port>/json/version`.
- Cookie reads need a PAGE-level websocket: `GET /json/list` → first `type:"page"` target's
  `webSocketDebuggerUrl`; if no page exists, `PUT /json/new?about:blank` returns one. The
  BROWSER-level ws (from `/json/version`) answers `'Network.getAllCookies' wasn't found` on
  current Chromium.
- Then `Network.getAllCookies` on the page ws (`websockets.sync.client.connect`); returned
  entries are already Playwright-shaped (`sameSite` as strings, `expires` unix or -1).
- Keep ports configurable (env, comma-separated) and default to 9222.

## Scheduled refresh job pattern

- Ship the job logic as `scripts/<name>.py` in the repo AND have the installer copy it to
  `$HERMES_HOME/scripts/` (that directory is what relative cron `script` names resolve to).
- The script imports the DEPLOYED plugin (`sys.path.insert(0, <home>/plugins/web)` then
  `import <pkg>.<module>`), resolves the home from its own path, runs under the Hermes venv
  python, prints a one-line value-free summary, and exits non-zero with a `FAILED:` line on
  trouble.
- Cron job: `no_agent=true` + `script=<name>.py` + schedule (+ `deliver` per the profile's
  convention, usually `local`). stdout is delivered verbatim; non-zero exit records an error
  alert with stdout; empty stdout sends nothing.
- Verify wiring by firing once (`cronjob run`) and reading `last_status` / `last_error` from
  `cronjob list`: a script that cannot succeed yet (e.g. source locked) is still proven wired.
- A source that is locked every time the job fires means the cadence, not the job, is wrong —
  offer the user the catch-up variant (fire often, import only when older than the window).

## Testing recipe

- Build tiny SQLite fixtures with the REAL table shapes (`cookies(host_key, name,
  encrypted_value, path, expires_utc, is_secure, is_httponly, samesite)`; firefox
  `moz_cookies`). Encrypt v10 fixtures with `AESGCM` using a synthetic 32-byte key and
  monkeypatch the key loader — do NOT touch the real DPAPI path in tests.
- Include a fixture whose plaintext has the 32-byte prefix and one bare value: both must decode.
- Fake clients must mirror every method the code path uses (`create_tab`, `list_tabs`,
  `close_tab`, `set_cookies`, `get_tab_cookies`); a missing one turns into an AttributeError on
  a shard you did not run.
- Reset ALL fake-client knobs in the fixture (including class-level flags): one test that leaves
  a leaked class flag makes unrelated later tests fail with confusing counts.
- `uv`-created venvs have no `pip`: add deps with
  `uv pip install -p .venv/Scripts/python.exe <pkg>`.
