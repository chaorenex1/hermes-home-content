# Email Pool Management

The `finalize` phase (phase 2) requires Outlook emails with valid OAuth2 `refresh_token` + `client_id` to receive OpenAI OTP codes via Microsoft Graph API. This doc covers purchasing, importing, and health-checking the email pool.

## hotmail007.com purchasing

The project integrates [hotmail007.com](https://hotmail007.com) API for buying Outlook emails. Client: `hotmail007.js`.

### Config keys (app_config table)
- `hotmail007_client_key` — API key (required)
- `hotmail007_api_base` — defaults to `https://gapi.hotmail007.com`

### API endpoints
```
GET /api/user/balance?clientKey=xxx           → check balance
GET /api/mail/getStock?mailType=outlook       → check stock count
GET /api/mail/getMail?clientKey=xxx&mailType=outlook%20Trusted&quantity=5  → buy
```

### Mail types (stock varies)
| Type | Stock (typical) | Quality | Price |
|---|---|---|---|
| `outlook` | 0-2 (often empty) | Low — may lack Graph permissions or be banned | cheaper |
| `hotmail` | 0 (often empty) | Same | cheaper |
| `outlook Trusted` | 25000+ | **High** — has Graph permissions, not banned | ~0.02 each |
| `hotmail Trusted` | 17000+ | High | ~0.02 each |

**Recommendation: always buy `outlook Trusted`** — regular outlook/hotmail emails frequently have `AADSTS90023` (no permissions) or `AADSTS70000` (service abuse / banned by Microsoft).

### Buying programmatically
```javascript
// Node.js — uses project's hotmail007.js client
require('./env-loader')();
const store = require('./mysql-store');
const h = require('./hotmail007');
async function buy(quantity, mailType = 'outlook Trusted') {
  const key = String((await store.runQuery('SELECT config_value FROM app_config WHERE config_key = ?', ['hotmail007_client_key']))[0]?.config_value || '');
  const accounts = await h.buyMail({ clientKey: key, mailType, quantity });
  for (const a of accounts) {
    await store.upsertPoolEmail({
      email: a.email, password: a.password,
      clientId: a.clientId, refreshToken: a.refreshToken,
      mailType, source: 'hotmail007'
    });
  }
  console.log(`Bought ${accounts.length} emails`);
}
```

### Buy response format
Each account is a string: `Account:Password:Refresh_token:Client_id`
Parsed by `hotmail007.js` → `{email, password, refreshToken, clientId}`

## Importing emails manually

### Three formats supported by `parseMailTxtImport()` in `mysql-store.js`

**Format 1: `----` separator (recommended, with OAuth2)**
```
email@outlook.com----password----client_id----refresh_token
```

**Format 2: colon separator (with OAuth2)**
```
email:password:refresh_token:client_id
```
Note: refresh_token can contain colons; the parser takes first 2 as email:password, last 1 as client_id, middle as refresh_token.

**Format 3: tab/space separator (email + password only, NO OAuth2)**
```
email@outlook.com	password
```
These CANNOT be used for finalize (no Graph API access). Only useful for IMAP (which Microsoft has mostly disabled).

### Import API
```
POST /api/admin/pool-emails/import
Body: { text: "...", source: "manual"|"hotmail007", longevity: ""|"长效"|"短效" }
```
Or via admin UI: 「邮箱管理」page → paste content or select file.

## Batch email pool health check

When finalize stalls on email OTP, run a batch health check to identify dead emails before they waste more time.

### What it checks
For each `pool_emails WHERE is_active=1 AND registered=0`:
1. POST to `https://login.microsoftonline.com/common/oauth2/v2.0/token`
2. Body: `client_id`, `grant_type=refresh_token`, `refresh_token`, `scope=https://graph.microsoft.com/.default`
3. If `access_token` returned → ✅ healthy
4. If error → categorize and mark inactive

### Common failure modes
| Error code | Meaning | Fix |
|---|---|---|
| `AADSTS90023` | refresh_token lacks Mail.Read scope | Replace email (buy new from hotmail007) |
| `AADSTS70000` | Account in service abuse mode (banned by MS) | Replace email; prefer `outlook Trusted` |
| `AADSTS50034` | Account doesn't exist | Replace email |

### Health check script (Python 3.12 + curl_cffi)
```python
import json
from curl_cffi import requests

# Load pool emails from DB (via Node one-liner, saved to JSON file)
with open('pool_emails.json') as f:
    emails = json.load(f)

good, bad = [], []
for e in emails:
    r = requests.post(
        'https://login.microsoftonline.com/common/oauth2/v2.0/token',
        data={
            'client_id': e['client_id'],
            'grant_type': 'refresh_token',
            'refresh_token': e['refresh_token'],
            'scope': 'https://graph.microsoft.com/.default',
        },
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        impersonate='chrome', timeout=20,
        proxies={'http': 'http://127.0.0.1:7897', 'https': 'http://127.0.0.1:7897'},
    )
    j = r.json()
    if j.get('access_token'):
        good.append(e['id'])
    else:
        err = j.get('error_description', '')[:80]
        bad.append((e['id'], e['email'], err))
```

### Marking bad emails inactive
```javascript
// Node.js — mark a list of email IDs as inactive
await store.runExecute('UPDATE pool_emails SET is_active = 0 WHERE id IN (?)', [badIds]);
```

## pool_emails table schema

Key columns:
- `email` (unique key)
- `password`
- `client_id` — OAuth2 app client ID
- `refresh_token` — OAuth2 refresh token (Graph API)
- `is_active` (1=available, 0=disabled)
- `registered` (1=already used for OpenAI registration, 0=available)
- `in_use` (1=currently locked by a worker)
- `source` — `hotmail007` | `manual`
- `lifecycle_status` — null | 已激活 | 封禁 | 养号中 | etc.
- `mail_type` — e.g. `outlook Trusted`

### Querying available count
```sql
SELECT COUNT(*) FROM pool_emails WHERE is_active=1 AND registered=0 AND in_use=0;
```

## OTP retrieval flow (finalize phase 2)

1. **Graph API (preferred)**: `_outlook_fetch_otp_graph()` in `gpt-5-5/gpt.py`
   - Uses `client_id` + `refresh_token` to get Graph access_token
   - Calls `GET /v1.0/me/messages` with `known_ids` exclusion (baseline dedup)
   - `email_snapshot()` before bind-email to record existing email IDs → prevents receiving stale OTP

2. **IMAP fallback**: `protocol_oauth_lib/imap_otp.py`
   - Microsoft has mostly disabled basic IMAP (`User is authenticated but not connected`)
   - This fallback is effectively dead for most accounts
