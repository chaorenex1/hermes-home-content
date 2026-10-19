---
name: pastepass
description: Upload, fetch, or share files with PastePass.
version: 1.0.0
author: chaorenex1
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [pastepass, pastebin, file-sharing, curl]
    source: https://github.com/chaorenex1/pastepass/blob/main/doc/skill.md
    source_commit: cc18e71
    source_instance: https://pastepass.chaorenex1.com
    upstream: https://github.com/SharzyL/pastebin-worker
    installed_at: "2026-10-19"
---

# PastePass

PastePass is a curl-friendly pastebin at `https://pastepass.chaorenex1.com`.
Every operation is plain HTTP. Random paste names appear bare (for example
`abcd`); custom names are returned with a leading `~` (for example `~demo`).

## When to Use

Load this skill when the user asks to:

- upload or share text, an image, or a file and get a URL;
- create a short link for long command output, logs, or notes;
- fetch, inspect, update, or delete an existing PastePass paste;
- publish a small file on `https://pastepass.chaorenex1.com`;
- render a markdown paste through `/a/` or shorten a URL through `/u/`.

Set the base once per shell:

```shell
BASE=https://pastepass.chaorenex1.com
```

## Upload

```shell
curl -FsS -Fc='hello, world' "$BASE"        # text
curl -FsS -Fc=@file.png      "$BASE"        # file
<cmd> | curl -FsS -Fc=@-     "$BASE"        # stdin
```

A successful upload returns JSON similar to:

```json
{
  "url": "https://pastepass.chaorenex1.com/abcd",
  "manageUrl": "https://pastepass.chaorenex1.com/abcd:<password>",
  "expireAt": "2026-10-26T08:45:33.000Z",
  "sizeBytes": 8,
  "location": "KV"
}
```

Persist `manageUrl` immediately. It contains the only credential for updating
or deleting the paste, and it is returned only at creation time.

## Optional upload fields

| Field | Effect |
|---|---|
| `-Fn=<name>` | Custom name, at least 3 chars; URL is returned as `~name`. |
| `-Fe=<expire>` | Expiration such as `30m`, `12h`, or `14d`; a bare number means seconds. |
| `-Fs=<password>` | Set a specific management password. |
| `-Flang=<lang>` | Syntax highlighting language for the display page. |
| `-Fp=1` | Private mode: a 24-character unguessable random name. |

## Fetch

```shell
curl -fsS "$BASE/<name>"          # raw content
curl -OJ  "$BASE/~<name>"         # save using the server filename
curl -fsS "$BASE/m/<name>"        # JSON metadata
curl -fsSI "$BASE/<name>"         # headers only
```

Append `?a` for `Content-Disposition: attachment`, append `?mime=<mime>` to
override the response Content-Type, or append `.<ext>` to the path to set the
Content-Type by extension. For example:

```shell
curl -fsS "$BASE/~demo?a"                # download attachment
curl -fsS "$BASE/~demo?mime=text/markdown" # override MIME
curl -fsS "$BASE/~demo.txt"              # text/plain by extension
```

## Update and delete

```shell
curl -fsS -X PUT -Fc='new content' "$MANAGE"
curl -fsS -X DELETE "$MANAGE"
```

`PUT` accepts the same fields as upload. Supplying `e` recalculates expiration
from the update time; omitting `e` applies the deployment default (7 days,
verified 2026-10-19).

## Other URL forms

| Path | Purpose |
|---|---|
| `/d/<name>` | Display page with syntax highlighting; add `?lang=<lang>` to override. |
| `/a/<name>` | Render a markdown paste as HTML (GitHub-flavored Markdown + MathJax). |
| `/u/<name>` | Redirect to the URL stored in the paste (URL shortener); returns 302. |

## Limits

- Default expiration: `7d`. Maximum: `90d`. Expired pastes are deleted.
- Maximum stored paste size: `256M`.
- A single Cloudflare request body is capped at 100 MB. Files above that need
the web UI at `$BASE` or the
[`pb` CLI](https://github.com/chaorenex1/pastepass/tree/main/scripts), both of
which split large files automatically.
- The deployment converts `text/html` to `text/plain`; do not use it to host
executable HTML pages.
- Treat PastePass as ephemeral storage, not an archive or a secrets store.

## Pitfalls

- Losing `manageUrl` means losing the ability to update or delete the paste.
- A successful-looking `curl` without `-f` can still contain an HTTP error body;
  use `-fsS` in scripts.
- The manage URL embeds the password. Treat it as a secret.
- Updating without `e` resets expiry to the default 7 days, even if the original
  paste had a different expiration.
- Deleted or expired pastes return 404; do not assume an old link is permanent.

## Source and verification

- Canonical source: `https://github.com/chaorenex1/pastepass/blob/main/doc/skill.md`
- Source commit: `cc18e71`
- Live instance used as the base: `https://pastepass.chaorenex1.com`
- Upstream project: `https://github.com/SharzyL/pastebin-worker` (MIT)
- Installed into Hermes on 2026-10-19 and adapted by replacing the source
template's `{{BASE_URL}}` and limit placeholders with this deployment's values.
- Live verification on 2026-10-19: custom-name upload (`~skilldemo`), 1-hour
expiration, password, stdin upload with `-Flang=python`, raw fetch, metadata,
HEAD, `?a`, `?mime=text/markdown`, `.txt` extension, `PUT` update, private mode
(`p=1`, 24-character name), `/u/` 302 redirect, `DELETE`, and post-delete 404.
The 100 MB Cloudflare request cap and the >100 MB CLI/UI path were not exercised.

Detailed provenance, including source hashes, is in
[`references/provenance.md`](references/provenance.md).
