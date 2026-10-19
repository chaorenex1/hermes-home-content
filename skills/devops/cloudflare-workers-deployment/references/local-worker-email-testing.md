# Local Email Handler Testing

How to prove an inbound-mail Worker on the dev server, without deploying and without access to the real mailbox.

The vite plugin / miniflare dev server exposes an undocumented test route that feeds a raw message to the Worker's `email()` handler.

## Request shape

```bash
curl -sS -X POST \
  --data-binary @message.eml \
  "http://127.0.0.1:<port>/cdn-cgi/handler/email?from=sender@example.com&to=inbox@example.com"
```

- `?from=` is the envelope sender, `?to=` becomes `message.to`. The header `To:` inside the MIME body is what display-oriented parsers read; keep both consistent, or set them apart deliberately to test forwarding.
- The body is raw MIME (`--data-binary`, not `-d`) so CRLF and headers survive.

## Minimum viable message

```
From: Sender <sender@example.com>
To: inbox@example.com
Subject: test
Date: Mon, 01 Jan 2026 12:00:00 +0800
Message-ID: <test-1@example.com>
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8

body
```

`Message-ID` is mandatory. Without it the endpoint answers `Error: No Message-ID header set` and the handler never runs, which reads like a routing bug in your code.

## The verdict is in the database, not the status

`200 Worker successfully processed email` means the handler returned without throwing. A handler that calls `message.setReject(...)` still produces that same 200, so status codes prove nothing about acceptance.

Assert stored state instead: query the app's own list endpoints (or D1 directly) and check the rows.

| Case | Expected state |
|---|---|
| Registered address | exactly one new email row under that account |
| Unregistered address | no row, no account created |
| Foreign domain | no row (rejected at the domain gate) |
| Prefix-routed address (`support@` → another mailbox) | row under the routed account, `delivered_to` keeps the arriving address |
| Subaddress (`user+detail@`) | row under the folded `user@` account |
| Forwarded message with `X-Original-To:` pointing at a personal mailbox | row under the domain account, not the original mailbox |

Forwarding tests need the original recipient header, e.g. `X-Original-To: me@gmail.com` plus `To:` set to the delivery address; that is the case where “first non-empty recipient header wins” logic silently misroutes.

## Testing send / outbound paths locally

A `send_email` binding is remote-only. Locally, without `wrangler login`, calling it blocks until the HTTP client times out, so the endpoint looks hung rather than broken.

1. Remove the `send_email` block from the Wrangler config, restart the dev server.
2. Exercise validation and the missing-binding guard: invalid recipient → 400, empty subject → 400, valid input → 503 with an explicit “binding not configured” message.
3. Restore the block and confirm the restored config with `wrangler deploy --dry-run` after a build.
4. Report delivery as unverified unless it ran against the deployed Worker with Email Sending enabled for the zone.

## Cleanup

```bash
netstat -ano | grep ':<port>' | grep LISTEN     # find the PID
MSYS2_ARG_CONV_EXCL='*' taskkill /F /PID <pid>
rm -rf .dev.vars .wrangler dist
```
