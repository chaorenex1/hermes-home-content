# Proxy Routing & Email Pool Troubleshooting

## Proxy architecture: which proxy goes where

```
Registration (register_phone.py)
  httpx → PROXY env → auth.openai.com
  PROXY = phonereg_proxy (must be local clash: http://127.0.0.1:7897)
  ❌ NOT the remote gateway directly — China can't reach gw.galdor.cc:6100 without clash

Finalize (finalize_phone.py)
  httpx → PROXY env → auth.openai.com  (same as registration)
  curl_cffi → ChainProxy → hop1(7897) → exit(711) → chatgpt.com  (session fetch only)

Plus checkout (plus_checkout.py / plus_activate.py step 1)
  curl_cffi → CHECKOUT_PROXY (phonereg_plus_proxy, JP) → chatgpt.com  (get 0元 eligibility)

Plus confirm (plus_activate.py step 4 — browser)
  Playwright → proxy (711 chain proxy local port) → chatgpt.com  (browser confirm)

Plus Stripe steps (plus_activate.py steps 3, 5)
  curl_cffi → payment proxy (711 chain) → api.stripe.com  (no Cloudflare, no Sentinel)
```

### Key insight: register/finalize do NOT use ChainProxy

`register_phone.py` and `finalize_phone.py` receive `PROXY` env and pass it directly to `httpx.AsyncClient(proxy=...)`. The Node-side `ChainProxy` is only used by:
- `_fetch_chatgpt_session_sync()` (finalize step 6)
- Plus activation (steps 1-5)

So for registration to work, `phonereg_proxy` must be reachable **directly** from the Python process. On a China host, that means the local clash inbound, NOT the remote residential gateway.

### Correct proxy config (this host)

| app_config key | Value | Why |
|---|---|---|
| `phonereg_proxy` | `http://127.0.0.1:7897` | Local clash, reaches auth.openai.com |
| `phonereg_session_chain_hop1` | `http://127.0.0.1:7897` | Chain proxy local entry |
| `phonereg_session_chain_exit` | `gw.galdor.cc:6100:ud50078:****` | 711 US residential, reaches chatgpt.com |
| `phonereg_plus_proxy` | `global.rotgb.711proxy.com:10000:...-JP:****` | 711 JP, for 0元 eligibility |
| `local_proxy` (DB + .env) | `http://127.0.0.1:7897` | Must match in both places |

### Diagnostic: 407 Proxy Authentication Required

```
[slot 5] ❌ [注册] 407 Proxy Authentication Required
```

**Root cause:** `phonereg_proxy` is empty → worker falls back to `proxy` (remote `gw.galdor.cc:6100`) → Python httpx tries to connect directly → China network can't reach it → 407.

**Fix:**
```bash
node -e "
require('./env-loader')();
const store = require('./mysql-store');
async function main() {
  await store.runExecute('INSERT INTO app_config (config_key, config_value) VALUES (?, ?) ON DUPLICATE KEY UPDATE config_value = ?',
    ['phonereg_proxy', 'http://127.0.0.1:7897', 'http://127.0.0.1:7897']);
  console.log('✅ phonereg_proxy set');
}
main().then(() => process.exit(0)).catch(e => { console.error(e.message); process.exit(1); });
"
```

### Diagnostic: verify proxy reachability

```bash
# Test clash can reach auth.openai.com (403 = CF challenge, which is fine for curl, curl_cffi will pass)
curl -x http://127.0.0.1:7897 -s -o /dev/null -w "HTTP %{http_code}\n" --max-time 10 https://auth.openai.com

# Test clash can reach chatgpt.com
curl -x http://127.0.0.1:7897 -s -o /dev/null -w "HTTP %{http_code}\n" --max-time 10 https://chatgpt.com
```
A 403 response means the proxy works (CF is challenging the curl TLS fingerprint). `curl_cffi` with `impersonate=chrome` will pass.

## Email pool troubleshooting

### AADSTS90023: No applicable permissions

```
[Graph] access token 失败: Graph token 失败: AADSTS90023: No applicable permissions were found for this user
[graph] 未收到新码，尝试 IMAP fallback
[IMAP/OTP] 轮询异常: User is authenticated but not connected.
```

**Root cause:** The Outlook pool email's `refresh_token` was obtained with a scope that doesn't include `Mail.Read`. When the code tries to exchange it for a Graph access token with `scope=https://graph.microsoft.com/.default`, Azure AD rejects it. IMAP fallback also fails because Microsoft disabled basic IMAP for consumer Outlook accounts.

**This is a data quality issue**, not a code bug. The finalize worker will auto-retry with a different pool email, but if many emails have bad tokens, every finalize stalls for 60s (IMAP timeout) before failing.

### Checking pool email health

```bash
node -e "
require('./env-loader')();
const store = require('./mysql-store');
async function main() {
  const rows = await store.runQuery('SELECT lifecycle_status, registered, is_active, COUNT(*) as cnt FROM pool_emails GROUP BY lifecycle_status, registered, is_active ORDER BY cnt DESC');
  for (const r of rows) console.log('lifecycle=' + (r.lifecycle_status||'(null)') + ' registered=' + r.registered + ' active=' + r.is_active + ' → ' + r.cnt);
}
main().then(() => process.exit(0)).catch(e => { console.error(e.message); process.exit(1); });
"
```

### pool_emails table schema

| Column | Type | Notes |
|---|---|---|
| `email` | varchar(255) | Outlook email address |
| `password` | varchar(512) | Email password |
| `client_id` | varchar(128) | Azure app client_id for OAuth |
| `refresh_token` | text | OAuth refresh token (needs Mail.Read scope) |
| `registered` | tinyint(1) | 1=already bound to an OpenAI account |
| `in_use` | tinyint(1) | 1=currently locked by a worker |
| `is_active` | tinyint(1) | 1=available for use |
| `lifecycle_status` | varchar(32) | null=未处理, 已激活=nurtured |
| `protocol` | varchar(16) | IMAP protocol type |

### Fix options for bad pool emails

1. **Replace the refresh_token** — re-authenticate the Outlook account with `Mail.Read` / `Mail.ReadWrite` scope and update the `refresh_token` column
2. **Mark inactive** — `UPDATE pool_emails SET is_active=0 WHERE email='bad@outlook.com'`
3. **Batch validate** — loop through all available emails, try to get a Graph token, mark failures as inactive

### CRITICAL: mark bad emails inactive immediately

`reservePoolEmail()` selects `ORDER BY id ASC LIMIT 1` — the lowest-ID available email is always picked first. If bad emails have lower IDs than good ones (common when old batch is 11309-11327 and new purchase is 11328+), finalize will **loop forever on the same dead email**, each iteration wasting ~60s on IMAP timeout. After a health check identifies bad emails, immediately disable them:

```javascript
// ❌ Does NOT work — mysql2 doesn't expand arrays in IN (?)
await store.runExecute('UPDATE pool_emails SET is_active = 0 WHERE id IN (?)', [badIds]);

// ✅ Loop per-ID instead
for (const id of badIds) {
  await store.runExecute('UPDATE pool_emails SET is_active = 0 WHERE id = ?', [id]);
}
```

### Fixing prematurely "正常" products stuck without token

If a phone's status was set to "正常" but `token` / `session_json` is NULL (finalize failed mid-way after email binding), the finalize loop won't re-claim it (it only claims `status='待codex'`). Manual fix:

```javascript
await store.runExecute("UPDATE product_assets SET status='待codex' WHERE registration_phone='+13863541818'");
```

The finalize loop will pick it up on the next tick (5s interval when idle).

## Server restart checklist (Windows)

After changing `.env` or `app_config` proxy values:

1. Kill the Node server process (check by port: `netstat -ano | grep ":23000 "`)
2. `taskkill //F //PID <pid>` (Windows taskkill via git-bash uses `//F //PID`)
3. Relaunch: `HEADFUL=1 node server.js` (use `pty=true` + `background=true` in Hermes terminal)
4. Wait for `http://localhost:23000` in output

`.env` changes require full restart (no hot-reload). `app_config` DB changes are read live by the worker (no restart needed for config value changes, but restart for `.env` changes).
