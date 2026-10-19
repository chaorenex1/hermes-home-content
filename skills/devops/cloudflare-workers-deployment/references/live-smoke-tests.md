# Live Smoke Tests for a Deployed Paste/File API

Use after `wrangler deploy` to prove the public origin serves the app and its upload/delete paths, not just that the Worker exists.

## Setup

```bash
BASE="https://app.example.com"
HOST="app.example.com"
# Only when local DNS returns a fake/sinkhole address:
EDGE_IP="172.67.150.10"   # any Cloudflare edge IP serves the zone by SNI
RESOLVE=(--resolve "$HOST:443:$EDGE_IP")
```

Use `"${RESOLVE[@]}"` in the commands below. Omit it when normal DNS reaches Cloudflare. Keep a browser User-Agent for HTML routes; many apps serve markdown or JSON to curl.

## 1. Page marker

```bash
curl "${RESOLVE[@]}" -sS -m 20 \
  -H 'User-Agent: Mozilla/5.0' \
  "$BASE/" | grep -aF '<title>Expected Title'
```

A 200 with an empty client shell is not proof. Assert a server-rendered marker when the app supports SSR.

## 2. Text upload

The exact field names depend on the app. For a Workers pastebin using the common `c`/`e`/`s`/`lang` form:

```bash
curl "${RESOLVE[@]}" -sS -m 30 -X POST \
  -F 'c=@/absolute/path/smoke.txt;type=text/plain;filename=smoke.txt' \
  -F 'e=1h' \
  -F 's=smoke-test-password' \
  -F 'lang=plaintext' \
  "$BASE/" \
  -o "$SCRATCH/smoke-resp.json" -w 'http:%{http_code}\n'
```

Read `url` and `manageUrl` from the JSON. Do not use a real user password for a smoke paste; create a disposable one.

## 3. Raw URL headers

```bash
curl "${RESOLVE[@]}" -sS -m 20 -D - -o /dev/null "$RAW_URL" \
  | grep -iE 'content-type|content-disposition|access-control-allow-origin'
```

Expect `text/plain` for the text paste. For an image, expect the image MIME, `Content-Disposition: inline`, and the CORS header the app promises.

## 4. Image upload

```bash
curl "${RESOLVE[@]}" -sS -m 30 -X POST \
  -F 'c=@/absolute/path/smoke.png;type=image/png;filename=smoke.png' \
  -F 'e=1h' -F 's=smoke-test-password' \
  "$BASE/" -o "$SCRATCH/smoke-image.json" -w 'http:%{http_code}\n'
```

Then check the raw URL headers again. An `image/png` response with `inline` proves the file is directly embeddable; `application/octet-stream` means filename/MIME inference is broken.

## 5. Metadata and delete

```bash
curl "${RESOLVE[@]}" -sS -m 20 "$BASE/m/$NAME"
curl "${RESOLVE[@]}" -sS -m 20 -X DELETE -o /dev/null -w 'delete:%{http_code}\n' "$MANAGE_URL"
curl "${RESOLVE[@]}" -sS -m 20 -o /dev/null -w 'after:%{http_code}\n' "$RAW_URL"
```

Expect the metadata JSON, then 200 on delete and 404 on the next read. Delete both the text and image smoke pastes.

## Pitfalls

- **Native curl on Windows does not translate MSYS `/tmp`**: write response files under a native scratch path (the Hermes scratch directory) or pipe to stdout. A missing output file after a successful HTTP status is usually a path issue.
- **A local TUN/VPN can return `198.18.x.x` for a new hostname**: TLS handshake failures then describe the local proxy, not the Worker. Use `--resolve` with a real Cloudflare edge address to isolate the deployment.
- **Certificate provisioning is not instant**: the custom-domain API may show the domain before the edge serves it. Retry the page marker after a short wait; do not redeploy on the first TLS error.
- **Do not leave smoke data**: delete the pastes and scratch files before reporting the deployment complete.
