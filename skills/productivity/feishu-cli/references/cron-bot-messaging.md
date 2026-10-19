# Bot-mode messaging for cron jobs

## Discovery (2026-07-15)

`lark-cli` supports two identity modes for sending messages:

| Mode | Auth | Interactive? | Cron-safe? |
|------|------|-------------|------------|
| `--as bot` | Tenant access token (app secret from keychain) | No | **Yes** |
| `--as user` (default) | User OAuth token | Yes (browser) | No (token expires) |

## Key insight: bot mode to user-id

Bot mode with `--user-id` (not `--chat-id`) auto-resolves the bot-user DM chat. This works even when the bot isn't in a group chat.

```shell
# Works — bot sends DM to user
lark-cli im +messages-send --as bot --user-id "ou_78b988b1124cfb7ee183428be8b0a40d" --text "hello"

# Fails with 230002 — bot not in this group
lark-cli im +messages-send --as bot --chat-id "oc_3c5c6fab489a36b22bbe39d8b4f6da52" --text "hello"
```

Error code 230002 = "Bot/User can NOT be out of the chat."

## Getting the user-id

```shell
lark-cli whoami
# → onBehalfOf.openId: "ou_78b988b1124cfb7ee183428be8b0a40d"
```

## Cron job integration pattern

```yaml
# In cron job prompt, use this pattern:
lark-cli im +messages-send --as bot --user-id "ou_xxx" \
  --content '{"text":"📋 **Title**\n\n- item 1\n- item 2"}' \
  --msg-type post
```

- No auth step needed in the cron prompt
- Tenant access token is refreshed automatically by lark-cli using the app secret
- `--msg-type post` enables markdown-like formatting in the content JSON

## Config requirements

The app must be configured with `appSecret` (stored in keychain):

```json
{
  "appId": "cli_aac35ea82bf89bdb",
  "appSecret": { "source": "keychain", "id": "appsecret:cli_aac35ea82bf89bdb" },
  "brand": "feishu",
  "defaultAs": "user"
}
```

Bot mode works regardless of `defaultAs` — `--as bot` overrides.

## Related: skill maintenance cron (2026-07-15)

Example of a complete cron job using bot-mode Feishu notification:

- Job ID: `733e88892284`
- Schedule: weekly Monday 09:00 CST
- Pattern: scan skills → analyze → generate plan → notify via bot mode
- Plan destination: `<HERMES_HOME>/plans/skill-maintenance-YYYYMMDD.md`
