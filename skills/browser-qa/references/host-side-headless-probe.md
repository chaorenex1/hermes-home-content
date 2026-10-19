# Host-side headless probe

Prove a deployed UI's layout and state when the host resolver is TUN/intercepted, the automation MCP is unavailable, or a bug report is visual ("the panel is covered"). Uses the installed Edge through `playwright-core`, so nothing is downloaded.

## Setup

```bash
mkdir -p "$TMPDIR/pw" && cd "$TMPDIR/pw"
npm init -y >/dev/null
npm i playwright-core@1 --no-audit --no-fund
```

`playwright-core` ships no browsers; `channel: "msedge"` (or `"chrome"`) reuses the installed one.

## Probe skeleton

```js
const { chromium } = require("playwright-core");
const fs = require("fs");
const SECRET = fs.readFileSync("C:/Users/<user>/.app-login-secret.txt", "utf8").trim().split(/\r?\n/).pop();

const browser = await chromium.launch({
  channel: "msedge",
  headless: true,
  args: ["--host-resolver-rules=MAP app.example.com <edge-ip>"],
});
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto("https://app.example.com/", { waitUntil: "networkidle", timeout: 45000 });

const input = page.locator("input").first();
if (await input.count()) { await input.fill(SECRET); await page.keyboard.press("Enter"); }
await page.waitForTimeout(2000);
// ... click into the state under test ...
await page.screenshot({ path: "shot.png" });
```

Keep the secret in a file, never in the script body or the transcript.

## Assert geometry, not vibes

Text snapshots miss overlap; the numbers catch it:

```js
const probe = await page.evaluate(() => {
  const el = document.querySelector(".fixed.inset-0");
  const r = el.getBoundingClientRect();
  const form = el.querySelector("form")?.getBoundingClientRect();
  return {
    parent: el.parentElement.tagName,
    overlay: { x: r.x, y: r.y, w: r.width, h: r.height },
    form: form && { x: form.x, w: form.width },
    viewport: { w: innerWidth, h: innerHeight },
  };
});
```

- `parent` must be `BODY` for a portal-rendered dialog; anything else means the dialog sits inside the app shell.
- `overlay.w === viewport.w` and `overlay.h === viewport.h`; a smaller overlay is trapped in a stacking context.
- The dialog's `x + w/2` should equal `viewport.w / 2` for a centered modal.

Run the probe at two widths (e.g. 1440 and 700) because panes switch between `absolute` and `static` at breakpoints; a layout can be correct at one and broken at the other.

## Common findings this probe proved

- A dialog mounted inside a `relative z-20` sidebar is painted under a sibling `z-30` pane; the overlay covers only the sidebar column. Fix by portaling the dialog to `document.body`.
- A `w-full` child combined with `md:basis-*` collapses instead of filling the pane; assert the rect rather than reading the class list.
- Cached data loss after a mutation (list empties, a field disappears) is invisible in the console; exercise the mutation, reload, and compare the rendered rows.
