---
name: browser-qa
description: "Run automated post-deploy UI verification with a browser automation MCP (claude-in-chrome, Playwright, or Puppeteer): console-error and Core Web Vitals smoke checks, form and auth-flow interaction tests, screenshot visual regression across three breakpoints, and axe-core accessibility audits ending in a SHIP / DO-NOT-SHIP verdict. Use when testing a deployed feature on staging or preview, before shipping frontend changes, reviewing a frontend PR, or checking responsive layout and accessibility."
metadata:
  origin: ECC
---

# Browser QA — Automated Visual Testing & Interaction

## When to Use

- After deploying a feature to staging/preview
- When you need to verify UI behavior across pages
- Before shipping — confirm layouts, forms, interactions actually work
- When reviewing PRs that touch frontend code
- Accessibility audits and responsive testing

## How It Works

Uses the browser automation MCP (claude-in-chrome, Playwright, or Puppeteer) to interact with live pages like a real user.

### Local dev servers, deployed hostnames, and containerized browsers

When the browser runs in a container (camofox, a Playwright image, or any Docker-hosted browser), `http://localhost:PORT` points inside the container, not at the host. Open `http://host.docker.internal:PORT` for the page. The page may still call `http://localhost:PORT` from the client bundle, so it loads but uploads and API calls fail. Either rebuild the client with the reachable origin or run a temporary forwarder inside the browser container. Full recipe: `references/local-dev-containerized-browser.md`. Remove the forwarder and stop the dev server after the run, and take fresh screenshots after the final rebuild.

A deployed hostname can fail the same way when the host resolver returns a TUN/fake IP. Add a temporary `/etc/hosts` entry inside the browser container pointing the hostname at a real edge IP, verify with `dns.lookup`, then restart the container to clean up. For binary assets, assert status and headers with `fetch`/curl instead of navigating to the raw file; the same reference covers both. If the failure is in the host browser, the local Clash/Mihomo rule set may be sending the new subdomain through a broad `DIRECT` rule; use `cloudflare-workers-deployment`'s `local-tun-routing` reference to add an exact proxy rule, and do not report the site as broken from the local TLS failure alone.

### Host-side headless probe (no browser download)

When the host resolver fakes or blocks a deployed hostname, drive the installed Edge headlessly through `playwright-core` and let Chromium resolve the name itself. `playwright-core` needs no browser download, and `--host-resolver-rules` does what `curl --resolve` does for a real browser:

```js
const { chromium } = require("playwright-core");
const browser = await chromium.launch({ channel: "msedge", headless: true,
  args: ["--host-resolver-rules=MAP app.example.com 203.0.113.10"] });
```

Log in with the app's own secret, drive the state under test, screenshot each breakpoint, and dump geometry with `getBoundingClientRect()` plus `parentElement.tagName`. Recipe: `references/host-side-headless-probe.md`.

A screenshot of the user's own window is not a breakpoint sample: a docked devtools panel or a scaled window changes the CSS viewport, so a layout that looks collapsed there can be correct at 1440px. Reproduce at explicit widths (1440 / 768 / 375) and compare rects before changing any class.

### Stacking-context traps

A dialog rendered inside a `relative z-*` ancestor is trapped in that stacking context. A sibling pane with a larger `z-index` in another subtree paints over it, and the `fixed inset-0` overlay only covers that ancestor's column: the screenshot reads as "the dialog is squeezed behind the panel".

- Detect: the overlay's rect must equal the viewport and its parent must be `BODY`. A dialog narrower than the overlay, or an overlay whose width equals one column, is the bug.
- Fix: portal dialogs to `document.body` through one shared wrapper instead of rendering them inside the app shell or sidebar.
- The same probe catches flex sizing: at each claimed breakpoint, assert `position` and rect for panes that switch between `absolute` and `static` instead of trusting the class list.

When a query's response shape changes (array to object), exercise a mutation and reload as part of QA: `setQueryData` updaters written for the old shape blank the list or drop fields, and no console error reports it.

### Safety first — blast radius (run read-only by default)

Browser QA drives real auth and real user journeys, so treat the blast radius explicitly.
Default to **read-only**: never run a **mutating** journey (checkout, payment, delete,
mass-update) against a production URL — require an explicit opt-in **and** a staging/preview
URL. Use seeded **test credentials**, never real production logins, and **redact**
credentials/tokens/PII before saving any screenshot.

### Phase 1: Smoke Test
```
1. Navigate to target URL
2. Check for console errors (filter noise: analytics, third-party)
3. Verify no 4xx/5xx in network requests
4. Screenshot above-the-fold on desktop + mobile viewport
5. Check Core Web Vitals: LCP < 2.5s, CLS < 0.1, INP < 200ms
   (INP replaced FID in March 2024; thresholds per web.dev)
```

### Phase 2: Interaction Test
```
1. Click every nav link — verify no dead links
2. Submit forms with valid data — verify success state
3. Submit forms with invalid data — verify error state
4. Test auth flow: login → protected page → logout (test creds only, never prod)
5. Test critical user journeys (checkout, onboarding, search)
   — read-only by default; only exercise mutating journeys against staging
     with explicit opt-in (see "Safety first" above)
```

### Phase 3: Visual Regression
```
1. Screenshot key pages at 3 breakpoints (375px, 768px, 1440px)
2. Compare against committed baseline screenshots
   — no baseline ⇒ report INCONCLUSIVE, never a silent PASS
3. Flag layout shifts > 5px, missing elements, overflow
4. Check dark mode if applicable
```

### Phase 4: Accessibility
```
1. Run axe-core or equivalent on each page
2. Flag WCAG 2.2 AA violations (contrast, labels, focus order)
3. Verify keyboard navigation works end-to-end
4. Check screen reader landmarks
```

> Note: axe-core automatically covers roughly 30–40% of WCAG. A clean run is **necessary,
> not sufficient** — keyboard nav, focus order, and a screen-reader pass still need a manual
> check. Don't report "accessible" from an automated pass alone.

## Output Format

```markdown
## QA Report — [URL] — [timestamp]

### Smoke Test
- Console errors: 0 critical, 2 warnings (analytics noise)
- Network: all 200/304, no failures
- Core Web Vitals: LCP 1.2s ✓, CLS 0.02 ✓, INP 89ms ✓

### Interactions
- [✓] Nav links: 12/12 working
- [✗] Contact form: missing error state for invalid email
- [✓] Auth flow: login/logout working

### Visual
- [✗] Hero section overflows on 375px viewport
- [✓] Dark mode: all pages consistent

### Accessibility
- 2 AA violations: missing alt text on hero image, low contrast on footer links

### Verdict: SHIP WITH FIXES (2 issues, 0 blockers)
# verdict ∈ SHIP / SHIP WITH FIXES / DO NOT SHIP; use INCONCLUSIVE if no visual baseline
```

## Integration

Works with any browser MCP:
- `mChild__claude-in-chrome__*` tools (preferred — uses your actual Chrome)
- Playwright via `mcp__browserbase__*`
- Direct Puppeteer scripts

Pair with `/canary-watch` for post-deploy monitoring.
