---
name: ssr-web-app-development
description: "Use when editing a server-rendered web UI."
version: 1.0.0
author: Masia
license: MIT
metadata:
  hermes:
    tags: [frontend, ssr, testing]
    related_skills: [browser-qa]
---

# SSR Web App Development

Server-rendered React fails quietly. A render-time exception is often caught by the page handler and replaced with a client-only shell, so the browser looks correct while SSR is gone. Treat SSR output as a separate deliverable and verify it every time a rendered component changes.

## When to Use

- A server-rendered component starts reading a new config or environment field.
- A page looks correct in a browser but the server HTML is only an empty shell.
- Adding a page, route, or interactive panel to a React SSR app.
- A share or file-upload panel must emit direct, HTML, and Markdown links.
- Adding SSR HTML regression coverage after a UI change.

## Workflow

1. Map the render path before editing.
   - Find the SSR entry (for example `worker/pages/index.ts`, `server/render.tsx`, a Next server component, or a framework route).
   - Read the exact props or config object passed into the component tree.
   - Find any `try/catch` around `renderToString`; that catch is where failures become an invisible CSR fallback.

2. Add every render-time config read to the SSR config object.
   - If a component starts reading `config.FIELD`, add `FIELD` to the server-side config literal. Adding it only to `wrangler.toml`, `.env`, or the client bundle is not enough.
   - Search the frontend for `config\.[A-Z_]+` after adding a field.
   - A missing field usually throws inside `.trim()`, `Number()`, or destructuring, not at the type checker.
   - Keep SSR and client values identical. A dev server that injects `localhost` while the client bundle was built with a public URL produces wrong links and API calls after hydration.

3. Prove SSR with a browser-like request.
   - `curl -s -H 'User-Agent: Mozilla/5.0' http://localhost:PORT/ | grep -F '<new heading>'`
   - Many apps serve markdown or JSON to curl; a browser UA is required for the HTML path.
   - A screenshot is not proof: CSR fallback renders the same UI.
   - Add a regression test asserting the HTML contains `<div id="root">` and a stable component marker.
   - React inserts `<!-- -->` between adjacent JSX text nodes. Assert a substring such as `256 MB`, not the joined sentence `256 MB per upload`.

4. Build in dependency order.
   - Build the client bundle before worker or SSR tests that read an SSR manifest.
   - Run typecheck, lint, tests, client build, and server/deploy dry-run as separate gates. A passing client build does not prove the SSR render runs.

5. Verify the client-only path separately.
   - SSR proof does not exercise upload, form, or API interactions.
   - For a local app tested through a Docker-hosted browser, load the `browser-qa` skill and its `local-dev-containerized-browser` reference.
   - For MSW + jsdom multipart XHR hangs, see `references/msw-jsdom-multipart.md`.

## References

- `references/msw-jsdom-multipart.md` - forcing the fetch path when MSW XHR multipart responses never dispatch `load`.
- `references/share-link-formats.md` - content-kind detection and the direct/HTML/Markdown embed matrix.
- `browser-qa` skill, `local-dev-containerized-browser` reference - page and API access plus file-upload simulation through a Docker-hosted browser.

## Pitfalls

- **Silent CSR fallback**: the handler catches the SSR error and returns a valid 200 shell. Only an HTML assertion detects it.
- **Narrow SSR config**: SSR entries often pass a hand-built subset of the runtime env. Every new UI field must be added there.
- **Build-time client config**: client values are baked at build time, server values are read at request time. Rebuild after changing a deploy URL or `define`.
- **Exact SSR text assertions**: React comments split interpolated text. Use `toContain` on a stable fragment.
- **Test timeout masking**: keep `waitFor` below the test timeout so failures name the missing element instead of timing out the test.

## Verification checklist

- [ ] Every new `config.*` read exists in the SSR config object
- [ ] Browser-UA curl shows the new marker in server HTML
- [ ] SSR regression test passes
- [ ] Client bundle built before SSR/worker tests
- [ ] Real browser exercised the client-only interaction
