---
name: feishu-cli
description: "Install, configure, bind, and authenticate the Feishu/Lark CLI (lark-cli / @larksuite/cli) in an AI agent environment. Covers the Hermes-specific config bind flow, identity policy selection, OAuth device-code auth with QR code generation, bot-mode messaging for cron/non-interactive use, and troubleshooting. Triggers: 'install feishu cli', 'setup lark-cli', '飞书 CLI', 'lark-cli config', 'lark-cli auth', '飞书授权', 'lark-cli bind', '飞书通知', 'feishu notification', 'send feishu message', 'cron feishu'."
---

# Feishu/Lark CLI Setup & Configuration

## When to use

- First-time installation of `lark-cli` (`@larksuite/cli`) on this host
- Binding lark-cli to an AI agent's (Hermes/OpenClaw/Lark Channel) Feishu app credentials
- OAuth login / re-login / token refresh
- Troubleshooting auth or config issues

## Prerequisites

- **Node.js** (npm/npx) — required
- Go v1.23+ and Python 3 — only needed for source builds (npm global install does NOT need them)
- The user must have a Feishu/Lark account with access to an app (or the agent environment must already have one configured)

## Installation

```shell
# 1. Install the CLI globally
npm install -g @larksuite/cli

# 2. Install the CLI SKILL pack (required — adds lark-* domain skills)
npx -y skills add https://open.feishu.cn --skill -y
```

Verify: `lark-cli --version` (e.g. `1.0.65+`).

## Configuration: bind (NOT init) in agent contexts

### CRITICAL PITFALL — `config init --new` is refused inside agent environments

Running `lark-cli config init --new` in Hermes (or OpenClaw / Lark Channel) returns:

```
config init is refused inside hermes context
(would create a parallel app and shadow the existing hermes binding)
```

**Use `config bind` instead** to bind lark-cli to the agent's existing Feishu app:

```shell
lark-cli config bind --source hermes --identity <preset>
```

`--source` is auto-detected from env (`HERMES_HOME`, etc.), but pass it explicitly to be safe.

### Identity policy — MUST confirm with user BEFORE running bind

| Preset | What it does | When to use |
|---|---|---|
| `bot-only` (default) | Robot identity only. Cannot access personal calendar/mail/drive. | Safer default; user unsure. |
| `user-default` | Impersonates the user. Full access to personal resources. | User needs personal-resource access (calendar, mail, drive). |

> **Warning:** `user-default` means the AI acts in the user's name — reading/writing docs, searching messages, modifying calendars. Advise the user not to share the bot or add it to group chats.

**Always ask the user to choose** before running bind. Do not default silently.

### Switching identity later

If already bound and only the identity policy needs to change (same app), use:
```shell
lark-cli config strict-mode  # policy switch, no re-bind needed
```

## Authentication (OAuth device-code flow)

### Step 1: Start login in background

```shell
# Run in background — blocks up to 10 min waiting for user authorization
lark-cli auth login --recommend
```

The command prints a `verification_url` to stderr and blocks.

**PITFALL:** Do NOT run this in foreground with a short timeout — it needs up to 600s.
**PITFALL:** Do NOT open the auth URL via `browser_navigate` or any agent tool — the authorization MUST happen in the user's own browser.

### Step 2: Generate QR code for the user

```shell
# URL is a POSITIONAL ARGUMENT (not stdin)
lark-cli auth qrcode "<verification_url>" --output auth-qrcode.png
```

**PITFALL:** The URL must be passed as a positional argument. Piping via stdin fails with `accepts 1 arg(s), received 0`.

Output JSON includes `file_path`. Display the image to the user (image tag / inline / attachment).

### Step 3: Present to user

1. Output the verification URL **as-is** (do not URL-encode/decode, add spaces, or modify it — treat as opaque string)
2. Display the QR code image below the URL
3. Wait for the background auth process to complete (it auto-detects authorization)

### Alternative: non-blocking flow

If your harness only delivers the final message (not streaming):

```shell
# Get device code + URL without blocking
lark-cli auth login --no-wait --json

# After user completes auth in browser, resume polling:
lark-cli auth login --device-code <code>
```

**Do NOT** run `--no-wait` and `--device-code` in the same turn — each restart invalidates the previous device code.

### Step 4: Verify

```shell
lark-cli auth status
```

## Sending messages (two identity modes)

### Bot mode (`--as bot`) — non-interactive, cron-safe

Uses the app's tenant access token (stored in keychain via `appSecret`). **No user OAuth required.**
Works in cron jobs, background tasks, and any non-interactive context.

```shell
# Send to a user's DM (bot must be in the user's contact list / have prior DM)
lark-cli im +messages-send --as bot --user-id "ou_xxx" --text "message"

# Send to a group chat (bot must be a member)
lark-cli im +messages-send --as bot --chat-id "oc_xxx" --text "message"

# Multi-line rich content — one content element per line
lark-cli im +messages-send --as bot --user-id "ou_xxx" \
  --msg-type post \
  --content '{"zh_cn":{"title":"Title","content":[[{"tag":"text","text":"line 1"}],[{"tag":"text","text":"line 2"}]]}}'

# Dry-run to validate request shape before sending
lark-cli im +messages-send --as bot --user-id "ou_xxx" --text "test" --dry-run
```

**PITFALL:** `--as bot` sending to `--chat-id` fails with code 230002 ("Bot/User can NOT be out of the chat") when the bot hasn't been added to that group chat. Use `--user-id` for DM — it auto-resolves the bot-user DM chat.

**PITFALL:** `--as user` needs a valid OAuth token (`lark-cli auth status`). In cron/non-interactive sessions, prefer `--as bot` — it doesn't expire as long as the app secret is valid.

### User mode (`--as user`) — interactive, needs OAuth

Requires prior `lark-cli auth login`. Suitable for interactive sessions where the user can complete browser authorization, but **not suitable for cron jobs** (token expires, refresh requires browser interaction).

Get your own user ID: `lark-cli whoami` → `onBehalfOf.openId`

### Message format reference

| Flag | What it sends | Use case |
|------|------|----------|
| `--text` | `msg_type=text` | One-line notices only — multi-line collapses to title-only on some clients. |
| `--markdown` | One auto-wrapped `md` element | Unreliable for multi-line; do NOT use for digests or reports. |
| `--content` + `--msg-type post` | Caller-built post JSON | The reliable multi-line method: one content element per line, title in `title`. |
| `--content '{"text":"..."}'` + `--msg-type text` | JSON text | Programmatic single-line text. |

**Multi-line rule:** each line must be its own `[{"tag":"text","text":"..."}]` element — `\n` inside one element does not render as separate lines. URL lines use `[{"tag":"a","text":"<url>","href":"<url>"}]`. Put the title in the `title` field only; do not repeat it as the first content line. Validate the request shape with `--dry-run` before sending.

### Checking bot reachability

```shell
# Verify bot can reach a user
lark-cli im +messages-send --as bot --user-id "ou_xxx" --text "test" --dry-run
# Check auth state
lark-cli whoami
```

## Web content extraction pitfall

`web_extract` (Tavily) and `browser_navigate` may fail on `open.feishu.cn` URLs with SSL timeout / empty page. Fall back to `curl`:

```shell
curl -fsSL "https://open.feishu.cn/document/..." | head -200
```

## Reference

- Official guide: https://open.feishu.cn/document/no_class/mcp-archive/feishu-cli-installation-guide.md
- Capability guide: https://open.larkoffice.com/document/mcp_open_tools/feishu-cli-let-ai-actually-do-your-work-in-feishu.md
- Config location (Hermes): `~/.lark-cli/hermes/config.json`
- `references/install-on-hermes.md` — real install transcript, config bind output, auth flow, QR code generation, web_extract failures
- `references/python-subprocess-pitfalls.md` — calling lark-cli from Python subprocess on Windows: `.CMD` shim resolution, `@file` relative path requirement, IM scope fallback, `npm root -g` with `shell=True`
- `references/cron-bot-messaging.md` — bot-mode messaging for cron/non-interactive use: `--as bot` to `--user-id`, error 230002 pitfall, cron integration pattern, config requirements
