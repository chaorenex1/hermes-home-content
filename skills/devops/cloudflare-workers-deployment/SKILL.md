---
name: cloudflare-workers-deployment
description: "Use when deploying a Cloudflare Worker with Wrangler."
version: 1.0.0
author: Masia
license: MIT
metadata:
  hermes:
    tags: [cloudflare, workers, wrangler, deployment, devops]
    related_skills: [ssr-web-app-development, github]
---

# Cloudflare Workers Deployment

A Worker deploy is four operations, not one command: authenticate the right account, create or bind the account's resources, build the client with production values, then prove the custom domain serves the app. Most failures happen before or after `wrangler deploy`, so run each gate explicitly.

## When to Use

- First deploy of a Worker, or a deploy after a fork or rebrand.
- `wrangler whoami` reports an expired or missing token.
- A Worker needs a KV namespace, R2 bucket, or custom domain.
- A deploy succeeded but the live URL needs independent verification.

## Workflow

1. Preflight the account.
   - Use the project-local binary when a package-manager shim is unreliable: `node node_modules/wrangler/bin/wrangler.js whoami`.
   - A cached OAuth token can still be expired. The non-interactive error is `Not logged in. Your auth token has expired and could not be refreshed`.
   - Confirm the account ID and scopes; do not assume the token belongs to the account that owns the domain.

2. Log in with an IPv4 callback on Windows.
   - Run in a PTY: `node node_modules/wrangler/bin/wrangler.js login --callback-host 127.0.0.1`.
   - The default may bind the temporary callback server to `[::1]:8976` while the browser resolves `localhost` to `127.0.0.1`; the consent page then redirects to `localhost` and shows `localhost refused to connect`. The explicit IPv4 host fixes it.
   - In a container or remote session where the browser cannot reach the host port, use `wrangler login --device` or forward port 8976 to the host.
   - The consent page is a real account authorization. If an automated click is denied, ask the user to click **Authorize** in the opened browser and wait for their confirmation; do not retry a denied click.
   - Re-run `whoami` and confirm the account before creating resources.

3. Inventory before creating.
   - `wrangler kv namespace list`
   - `wrangler r2 bucket list`
   - `wrangler d1 list`
   - Match existing resources by title/name. Creating a second namespace or bucket because the list was not checked leaves the config pointing at one resource and the app at another.
   - A forked config usually carries the upstream author's D1 `database_id`. If that id is not in `wrangler d1 list`, the first deploy fails with `database not found`; create the database in this account and replace the id.

4. Create and bind resources.
   - `wrangler kv namespace create <title>` prints the new `id`.
   - Put that id in the existing binding in `wrangler.toml`; keep the binding name unchanged because the code imports it by name.
   - `wrangler r2 bucket create <name>`; the bucket name in `wrangler.toml` must match exactly.
   - `wrangler d1 create <name>` prints the new `database_id`; put it in `d1_databases[0].database_id`, then apply the schema with `wrangler d1 migrations apply <name> --remote` before the first deploy.
   - A template or fork often carries the upstream author's KV id. Replace it before the first deploy instead of deploying against a namespace that does not exist in this account.

5. Validate the deploy config.
   - `name` is the Worker name that will appear in the account.
   - `[[routes]]` with `pattern` and `custom_domain = true` attaches the hostname.
   - `DEPLOY_URL` must equal the public origin, including scheme and no trailing slash.
   - `[assets]` must point at the client output directory, and `run_worker_first` must match the app's routing model.
   - `workers_dev = false` means the custom domain is the only public entry point. Confirm the zone is active in the same Cloudflare account before deploying; a custom-domain route cannot attach a zone from another account.
   - The OAuth token may lack DNS-record read even when `zone:read` is present. After deploy, inspect `GET /accounts/{account_id}/workers/domains` for the hostname, service, and certificate rather than assuming DNS changes are visible.

6. Build production, then deploy.
   - Build the client in production mode first, for example `pnpm build:frontend`. A development build bakes `localhost` into `DEPLOY_URL` and API calls.
   - Verify the bundle contains the public origin and no local dev origin.
   - Run `wrangler deploy`, not `wrangler deploy --dry-run`, and record the printed version id and custom-domain line.
   - Rebuild after any `wrangler.toml`/`wrangler.jsonc` edit, not only after code edits: a vite plugin writes `dist/<worker>/wrangler.json` with the resolved binding ids and `wrangler deploy` follows that redirect. A stale `dist/` ships the previous `database_id` and fails with `database not found` while the config file looks correct.

7. Verify the live surface separately.
   - A local TUN/VPN may return a fake or sinkhole IP for a new hostname. `curl` then fails the TLS handshake even though the deployment is healthy. Do not diagnose the Worker from that error.
   - Resolve to a real Cloudflare edge address with `curl --resolve <host>:443:<cloudflare-ip> ...` and request the HTML with a browser User-Agent.
   - If the user's own browser must open the hostname, fix the local route instead of stopping at `--resolve`. A broad `DOMAIN-KEYWORD,<apex>,DIRECT` rule can catch the new subdomain and reset TLS; add an exact `DOMAIN,<fqdn>,<proxy-group>` above it in the client's rules profile and reload. Use `references/local-tun-routing.md`.
   - Assert the page title or a stable component marker, not just HTTP 200.
   - Exercise the real API: upload a text paste and an image, inspect `Content-Type`, `Content-Disposition`, and CORS, read metadata, delete the pastes, and confirm 404 afterward. Use `references/live-smoke-tests.md`.

8. Clean up.
   - Delete smoke-test pastes and scratch files.
   - Kill temporary forwarders and dev servers by process tree; confirm the port is closed.
   - Never print or commit the OAuth token, API token, or cookies.

## Secrets and Inbound Mail for a New Worker

- Set secrets after the first successful deploy: a Worker that does not exist yet has no secret surface, and `wrangler secret list` fails with `worker not found`. A later `secret put` creates a new version on its own.
- Generate a secret the human can actually use, keep it out of the transcript, and make it usable: 32 random bytes as base64url → write to a file outside the repo → `wrangler secret put SECRET < temp.txt` → delete the temp copy. Report the file path, never the value.
- A Worker with an `email()` handler receives nothing until Email Routing points at it. Catch-all with a `worker` action is the usual wiring, and the API recipe plus the proof-by-self-send loop lives in `references/email-routing-to-worker.md`.

A Worker that both receives and sends mail needs the outbound side wired separately: `send_email` binding, validation before the capability check, outbound archiving with `direction = 'out'`, and token-scoped read/send APIs. Use `references/outbound-mail-and-tokens.md`.

## Local Verification Before Deploy

A dry-run proves the bundle; it does not prove the Worker. Run the changed paths against a local server first.

1. Build before any Wrangler config check. A vite-plugin project injects `assets`, so `wrangler deploy --dry-run` reads the generated redirect (`dist/<worker>/wrangler.json`). With no `dist/`, it fails complaining that the `assets` property is missing the required `directory` property — a stale-build error, not a config bug.
2. Apply D1 migrations locally: `wrangler d1 migrations apply <database_name> --local`. New columns and tables must exist before the dev server writes rows; re-running is a no-op.
3. Put dev secrets in `.dev.vars` (gitignored), then start the server on IPv4: `npx vite --host 127.0.0.1 --port <port> --strictPort`. Without `--host`, Vite listens on `[::1]` and `curl http://localhost:<port>` is refused on Windows.
4. Drive the real API with a cookie jar after authenticating through the app's own endpoint, and assert status codes plus the stored rows. A 200 from a local proxy is not proof of behavior.
5. Exercise the Worker's `email()` handler through miniflare's test endpoint — recipe and traps in `references/local-worker-email-testing.md`.
6. Tear down: kill the dev server by PID (`netstat -ano | grep :<port>`, then `taskkill /F /PID <pid>`), delete `.dev.vars`, `.wrangler`, and `dist`. Test accounts otherwise persist in local D1 and surprise the next run.

## Pitfalls

- **IPv6 callback mismatch**: a browser on IPv4 can fail the OAuth callback while Wrangler listens only on `[::1]:8976`. Use `--callback-host 127.0.0.1`.
- **Expired cached token**: `wrangler whoami` can fail non-interactively even though a token file exists. Log in in a PTY; do not treat the file's presence as authentication.
- **Dev build deployed**: production and development builds bake different `DEPLOY_URL` and page titles. Rebuild after any config change and check the bundle.
- **Inherited resource ids**: a fork or template may carry another account's KV id. Replace it and create the R2 bucket in the current account.
- **Custom domain hides workers.dev**: adding a `routes` entry with `custom_domain: true` flips `workers_dev` off automatically, so the workers.dev URL printed by an earlier deploy stops serving. Verify the custom hostname from then on.
- **No workers.dev fallback**: with `workers_dev = false`, a broken custom domain leaves no alternate URL. Confirm the zone and certificate before declaring the deploy live.
- **Local fake IP**: Mihomo/TUN or another resolver can return `198.18.x.x`; a local TLS failure is not proof the Worker is down. Verify through a Cloudflare edge IP.
- **Broad local DIRECT rule**: a `DOMAIN-KEYWORD,<apex>,DIRECT` rule can override a new subdomain and reset TLS. Add an exact proxy rule above it; see `references/local-tun-routing.md`.
- **Placeholder contact values**: a rebrand cannot infer a support mailbox. Mark it as a placeholder and report it; do not present an invented address as working.
- **Secret before the Worker exists**: `wrangler secret put` and `wrangler secret list` need a deployed Worker. Deploy first, set the secret, confirm with `wrangler secret list`.
- **Code deployed before its migration**: a Worker that inserts a new column fails every write until `wrangler d1 migrations apply <database_name> --remote` has run. Migrate first, then deploy.
- **`send_email` blocks locally**: the binding is remote, so without `wrangler login` a local send waits until the client times out. Temporarily remove the binding to assert input validation and the missing-binding 503, restore it, and confirm the restored config with a dry-run. Never report sending as verified from a local run.
- **`email()` HTTP 200 is not acceptance**: miniflare answers `Worker successfully processed email` even when the handler called `setReject`. Assert the effect in D1 or through the app API, never the status line.

## Verification Checklist

- [ ] `wrangler whoami` shows the intended account
- [ ] KV namespace and R2 bucket exist and match `wrangler.toml`
- [ ] Production client bundle contains the public origin, not localhost
- [ ] `wrangler deploy` printed the version id and custom domain
- [ ] Custom domain returns the app marker with valid TLS through a real edge IP
- [ ] Text and image upload, metadata, delete, and post-delete 404 all pass
- [ ] Temporary pastes, files, forwarders, and dev servers are gone

## References

- `references/live-smoke-tests.md` - exact curl sequence for proving a deployed paste/file API and its headers.
- `references/local-tun-routing.md` - fix a host browser that resolves a new hostname to a TUN fake IP and hits a broad DIRECT rule.
- `references/local-worker-email-testing.md` - drive a Worker `email()` handler locally through miniflare, with the MIME template and the verdict-by-database rule.
- `references/email-routing-to-worker.md` - point a zone's Email Routing (catch-all or literal addresses) at a Worker and prove inbound delivery end to end.
- `references/outbound-mail-and-tokens.md` - `send_email` binding, outbound archiving, hashed scoped tokens, and the request matrix for verifying a handed-over token.
