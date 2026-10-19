# Email Routing to a Worker

How inbound mail actually reaches a Worker, and how to prove it. Configure it through the zone API, not the dashboard, when a Wrangler OAuth token is already available.

## 1. Read the current state before changing it

```bash
# zone id
curl -s -H "Authorization: Bearer $TOK" \
  'https://api.cloudflare.com/client/v4/zones?name=example.com'

# is routing on, and what does the zone already do with mail
curl -s -H "Authorization: Bearer $TOK" \
  'https://api.cloudflare.com/client/v4/zones/$ZONE/email/routing'
curl -s -H "Authorization: Bearer $TOK" \
  'https://api.cloudflare.com/client/v4/zones/$ZONE/email/routing/rules'
curl -s -H "Authorization: Bearer $TOK" \
  'https://api.cloudflare.com/client/v4/zones/$ZONE/email/routing/rules/catch_all'
```

`rules` lists literal/custom addresses; catch-all is a separate endpoint. A zone can have Email Routing `enabled: true` and still discard everything: catch-all `enabled: false` with an action `drop`, and no custom rules. Check MX too (`doh.pub` or any DoH endpoint works when the host resolver is intercepted) — no MX means nothing is delivered at all.

Where the token comes from: Wrangler's OAuth token lives in `~/.wrangler`/`%APPDATA%/xdg.config/.wrangler/config/default.toml` as `oauth_token`. Read it into a variable and use it as a Bearer token; never echo it. Scopes are per-login: `email_routing` write may be present while DNS read is not, so a 403 on one endpoint is a scope gap, not a broken API.

## 2. Route to the Worker

Catch-all (every address at the domain):

```bash
curl -s -X PUT -H "Authorization: Bearer $TOK" -H 'content-type: application/json' \
  "https://api.cloudflare.com/client/v4/zones/$ZONE/email/routing/rules/catch_all" \
  -d '{"name":"App inbound","enabled":true,"matchers":[{"type":"all"}],
       "actions":[{"type":"worker","value":["<worker-script-name>"]}]}'
```

Literal address (only one mailbox reaches the Worker):

```bash
curl -s -X POST -H "Authorization: Bearer $TOK" -H 'content-type: application/json' \
  "https://api.cloudflare.com/client/v4/zones/$ZONE/email/routing/rules" \
  -d '{"name":"Support","enabled":true,
       "matchers":[{"type":"literal","field":"to","value":"support@example.com"}],
       "actions":[{"type":"worker","value":["<worker-script-name>"]}]}'
```

`value` is the Worker script name, not its URL or route. Read the rule back after the write; a 200 does not prove the action stuck.

## 3. Decide what the handler does with unknown recipients

Catch-all delivers every address, including ones no user ever registered. If the handler inserts a row for any recipient, the domain becomes an open mail collector. Reject unknown recipients in `email()` (`message.setReject(...)`) or keep catch-all off and use literal rules.

State the trade-off out loud when you switch catch-all on: mail to unregistered addresses now produces an SMTP rejection (a bounce for the sender) instead of the previous silent drop.

## 4. Prove delivery end to end

1. Register one address in the app (the recipient must already exist if the handler rejects unknowns).
2. Send from the Worker's own `send_email` binding to that same address.
3. Poll the app's inbox API for a `direction: "in"` row for up to ~30s.

The self-send exercises both directions in one step: Email Sending accepts the message, the MX hands it back, Email Routing calls the Worker, the Worker stores it. A sent row without an inbound copy means delivery or loop detection, not a broken handler — send a second message before investigating. Delete the test mailbox and any tokens afterwards.
