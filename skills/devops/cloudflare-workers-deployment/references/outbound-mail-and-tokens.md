# Outbound Mail and API Tokens

Wiring a Worker app to send mail and to expose a token-authenticated API. These are the patterns that survive contact with a real deployment; the receive side lives in `email-routing-to-worker.md`.

## send_email binding

```jsonc
"send_email": [{ "name": "EMAIL", "remote": true }]
```

- The binding is always remote, so a local `wrangler dev` send waits until the client times out instead of failing fast. Locally you can only prove input validation and the missing-binding 503; prove a real send on the deployment.
- Configuration accepts the binding even when the domain is not onboarded for Email Sending. A green deploy is not proof that sending works.
- Access it defensively: `(env as Env & { EMAIL?: SendBinding }).EMAIL`; missing binding returns 503 with the remediation, not a crash.
- Validate recipients, subject, body, and reply-to **before** checking the binding. Otherwise a deployment without the binding reports every call as 503 and hides the 400s that would have caught bad input.
- `from` must be a mailbox the app already knows. Resolve it against the accounts table; never trust a `from` string from the request.
- Archive the message in the same table as inbound with `direction = 'out'` and `read = 1`, only after `send()` resolves. One mailbox view then shows both directions with no second table, and a failed send leaves no phantom row.
- A sent row without an inbound copy is delivery context, not a handler bug: send a second message before investigating (loop detection and MX timing both appear as a missing copy).

## Token table

| column | purpose |
|---|---|
| `token_hash` UNIQUE | hex SHA-256 of the plaintext; look up by hash, never compare strings |
| `token_prefix` | first ~12 chars for the UI so a human can tell tokens apart |
| `scopes` | `"send,read"` |
| `account_id` NULL | optional binding to one mailbox |
| `last_used_at` | updated on every authenticated request |

- Mint as `<prefix>_` + base64url(32 random bytes). Return the plaintext only in the create response; the list endpoint returns prefix and scopes, never the value.
- Keep a separate middleware for `/api/v1/*` bearer auth and make the cookie-session middleware `return next()` for that prefix. Mixing the two silently 401s external calls.
- Check the scope per route: a read-only token posting a message is 403, not 401.
- When `account_id` is set, `from` defaults to that mailbox, another mailbox is 403 on send, and reading another mailbox is 403.

## Verification matrix when handed a token

Never echo the token; keep it in a variable and aim requests at the API host.

1. no token and malformed token → 401
2. read route with the token → 200; send with a read-only token → 403
3. account-bound token used for another mailbox → 403 (both send and read)
4. `from` not in the accounts table → 404 with a message naming the address
5. empty subject / malformed recipient → 400
6. `limit=1` returns `has_more` and `next_cursor`; following the cursor returns the remainder with `has_more: false`
7. one real round trip: send from a registered address to a registered address on the same domain, then poll for the `direction: "in"` row
8. clean up the tokens and mailboxes you created; leave the user's own messages in place unless asked
