# HTML→PDF Report Pipeline (replaces generate_ppt.js)

The report generation pipeline was migrated from PptxGenJS (.pptx → LibreOffice → PDF) to HTML/CSS (generate_html.py → html2pdf.js → PDF) on 2026-07-05 at the user's explicit request.

## Architecture

```
analysis JSON → generate_html.py → self-contained HTML → html2pdf.js → PDF
                                     (Linear dark theme)    (puppeteer-core + Edge)
```

## generate_html.py

Python script that reads an analysis JSON and produces a self-contained HTML file with embedded CSS (no external assets except Google Fonts CDN for Inter/JetBrains Mono).

### Design System: Linear Dark Theme

Based on the `popular-web-designs` skill's Linear.app template:

- Background: `#08090a` (near-black with cool undertone)
- Panel: `#0f1011`, Surface: `#191a1b`, Elevated: `#28282c`
- Text: `#f7f8f8` (primary), `#d0d6e0` (secondary), `#8a8f98` (tertiary)
- Accent: `#5e6ad2` (brand indigo), `#7170ff` (violet), `#828fff` (hover)
- Borders: `rgba(255,255,255,0.05)` to `rgba(255,255,255,0.08)` (semi-transparent white)
- Font: Inter with `font-feature-settings: "cv01", "ss03"` (Linear's signature OpenType alternates)
- Language colors: GitHub Linguist hex values (same as `generate_ppt.js`)

### Page Layout (1280×720px per page)

Each `.page` div uses:
```css
.page {
  width: 1280px;
  height: 720px;       /* FIXED height, NOT min-height */
  overflow: hidden;     /* prevents content from creating extra pages */
  padding: 40px 56px;
  page-break-after: always;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}
```

### Slide Structure (6 pages for 18 repos)

| Page | Content | Key CSS |
|------|---------|----------|
| 1 (Cover) | GitHub Octocat SVG + title + 3 stat cards | `.cover` with `justify-content: center`; `.cover-content` with `flex: 1` for vertical centering |
| 2 (Overview) | Dual bar charts (language Top 10 + categories) | `.chart-grid` 2-col grid; `.bar-track` + `.bar-fill` width % |
| 3-5 (Projects) | 6 project cards per page (2-col × 3-row) | `.cards-grid` with `gap: 12px`; `.project-card` with `min-height: 140px; max-height: 165px` |
| 6 (Summary) | 18-row ranking table | `td padding: 3px 10px; font-size: 11px; line-height: 1.3` |

### Card Layout (per project)

```
┌─────────────────────────────────┐
 │ project_name        ⭐ 156.7k  │
 │ @owner · owner/repo  +973 今日 │
 │                                 │
 │ 中文一句话描述                    │
 │ 核心能力描述...                   │
 │                                 │
 │ [🔥 热度] [AI/Agent生态]  ● Shell │
 └─────────────────────────────────┘
```

- Left accent bar (3px) colored by language
- Project name: 15px, `white-space: nowrap; text-overflow: ellipsis; max-width: 220px`
- Star count: gold (`#f2cc60`)
- Period stars: green (`#3fb950`)
- Badges: pill-shaped, color-coded (orange for hot, violet for AI category)
- Language tag: colored dot + name

### Pagination Logic (Python)

```python
CARDS_PER_PAGE = 6
card_pages = []
current_page_cards = ""
for i, r in enumerate(repos):
    card_html = f"""<div class="project-card">...</div>"""
    current_page_cards += card_html
    if (i + 1) % CARDS_PER_PAGE == 0 or i == len(repos) - 1:
        card_pages.append(current_page_cards)
        current_page_cards = ""
```

Then iterate `card_pages` to generate one `.page` div per batch.

## html2pdf.js

Node.js script using `puppeteer-core` (NOT `puppeteer` — no bundled Chromium, uses system Edge browser).

### Browser Detection

```javascript
const candidates = [
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
];
```

### PDF Generation

```javascript
const browser = await puppeteer.launch({
  headless: 'new',
  executablePath,
  args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
});

const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 720 });
await page.goto(`file:///${htmlPath}`, { waitUntil: 'networkidle0', timeout: 30000 });
await page.evaluate(() => document.fonts.ready);  // Wait for Google Fonts

await page.pdf({
  path: pdfPath,
  width: '1280px',
  height: '720px',
  printBackground: true,
  margin: { top: 0, right: 0, bottom: 0, left: 0 },
});
```

### Dependencies

```bash
# Node.js (already installed)
npm install -g puppeteer-core   # or available as system module

# System browser (already installed — Edge on Windows)
# No puppeteer Chromium download needed

# Python (for generate_html.py — already installed)
# No additional Python packages needed (stdlib only: json, sys, os)

# For QA: PyMuPDF (already installed for pdf2img.py)
```

## Key Differences from generate_ppt.js

| Aspect | generate_ppt.js (old) | generate_html.py + html2pdf.js (new) |
|--------|----------------------|---------------------------------------|
| Output format | .pptx → .pdf (via LibreOffice) | .html → .pdf (via puppeteer-core + Edge) |
| Layout engine | PptxGenJS (absolute positioning in inches) | CSS Grid + Flexbox (responsive, declarative) |
| Text truncation | Manual JS substring + font size reduction | CSS `text-overflow: ellipsis` (native) |
| Page control | Slide count = explicit | CSS `height: 720px; overflow: hidden` per `.page` div |
| Design system | GitHub Dark (`#0D1117`) | Linear Dark (`#08090a`) |
| Icons | Octicons SVG→PNG→base64 (sharp) | Inline SVG (no preprocessing) |
| Dependencies | pptxgenjs, react-icons, react, sharp, LibreOffice | puppeteer-core, system Edge (minimal) |
| Rendering fidelity | LibreOffice introduces inconsistencies (wrap:false, autoFit) | Edge renders HTML/CSS natively (pixel-perfect) |

## QA Pipeline

1. Generate HTML: `python3 generate_html.py <analysis.json> <output.html>`
2. Render PDF: `node html2pdf.js <output.html> <output.pdf>`
3. Convert to images: `python3 pdf2img.py <output.pdf>` (PyMuPDF, 1920×1080 at 150 DPI)
4. Visual QA: `vision_analyze` on slide JPGs (check card count, table rows, overflow, centering)
5. Fix CSS → regenerate → re-verify

### Common QA Issues and Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| Extra blank page | `min-height` allows content overflow | Use `height: 720px; overflow: hidden` |
| Only 4 cards visible (expected 6) | Card `min-height` too large (220px) | Reduce to `min-height: 140px; max-height: 165px`; reduce gap to 12px |
| Table rows missing (only 4 of 18) | `td padding: 8px 16px` too large | Reduce to `padding: 3px 10px; font-size: 11px; line-height: 1.3` |
| Cover content not centered | Absolute-positioned footer interferes with flex centering | Wrap content in `.cover-content` div with `flex: 1; display: flex; justify-content: center` |
| Google Fonts not loaded | `waitUntil: 'networkidle0'` alone may fire before fonts | Add `await page.evaluate(() => document.fonts.ready)` |
