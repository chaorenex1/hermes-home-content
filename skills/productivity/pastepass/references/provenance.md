# PastePass skill provenance

- Source document: `https://github.com/chaorenex1/pastepass/blob/main/doc/skill.md`
- Source commit: `cc18e71` (`chore: bind PastePass KV namespace`; the document is unchanged from the preceding rebrand commit `a7dbd9d`)
- Source git blob hash (`git hash-object doc/skill.md`): `ea57841fd5be121feba533a5b72489a1fd491ee7`
- Source SHA-256: `64a3a3cb49cf16bf0df671b9b25b1e0a22835edafd84f22eadd0dc7b4f63eca1`
- Retrieved and installed: 2026-10-19
- Live base: `https://pastepass.chaorenex1.com`
- Upstream project: `https://github.com/SharzyL/pastebin-worker` (MIT)

## Adaptation

This Hermes skill is a copy of the source document, adapted for the deployed
instance:

- `{{BASE_URL}}` was replaced with `https://pastepass.chaorenex1.com`.
- `{{DEFAULT_EXPIRATION}}` was replaced with `7d` from `wrangler.toml`.
- `{{MAX_EXPIRATION}}` was replaced with `90d` from `wrangler.toml`.
- `{{R2_MAX_ALLOWED}}` was replaced with `256M` from `wrangler.toml`.
- The `pb` CLI link points to the fork's `main` branch.
- The source hashes and live verification notes were added.

The upstream document templates `{{BASE_URL}}`, so it is not copied verbatim.

## Live verification

Verified against the live deployment on 2026-10-19:

- Upload with `-Fn=skilldemo`, `-Fe=1h`, `-Fs=...` returned `~skilldemo` and
  `expirationSeconds: 3600`.
- Stdin upload (`-Fc=@-`) with `-Flang=python` returned the body and
  `X-PB-Highlight-Language: python` on HEAD.
- Raw fetch, `/m/` metadata, and `HEAD` returned the expected content and headers.
- `?a` returned `Content-Disposition: attachment`.
- `?mime=text/markdown` returned `Content-Type: text/markdown`.
- `~skilldemo.txt` returned `Content-Type: text/plain`.
- `PUT` updated the content; omitting `e` reset expiry to 7 days.
- `-Fp=1` returned a 24-character random name.
- `/u/<name>` returned 302 with the stored URL in `Location`.
- `DELETE` returned 200; a subsequent fetch returned 404.

Not exercised: the 100 MB Cloudflare single-request cap and the >100 MB CLI/UI
upload path. Those limits are documented in the source and deployment config.

## Maintenance

If the canonical source changes, diff it against this skill before updating the
body. Preserve this provenance file and record the new commit hash and date in
both places. Do not silently overwrite the verification notes.
