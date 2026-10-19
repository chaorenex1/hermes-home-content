# BGS-Nexus-automation

Nexus Mods automation for Hermes Agent, built on the **built-in browser tools**
(`browser_navigate` / `browser_snapshot` / `browser_click` / `browser_type` / `browser_console`).
No CDP, no Node scripts, no Puppeteer/Playwright.

Works for every Nexus game via `game_domain`. `browser.camofox.user_id` is pinned to `camofox_search`,
so the browsing profile is stable and already carries a Nexus login (verified `chaorenex1`, Premium).
That profile is shared with the camofox-search backend; if its browser restarts, just re-navigate.

## Features

| # | Feature | Entry |
|---|---------|-------|
| 1 | Trending / search mods | `S3` after `/games/{d}/mods?...` |
| 2 | Mod details | `S4` |
| 3 | Track / Endorse / Vote | `S5` + `browser_click` |
| 4 | Tags / Gallery | `S6`, `S7` |
| 5 | Description accordion (requirements, translations, changelogs) | `S8` |
| 6 | Files list | `S9` |
| 7 | Posts (comments + nested replies) | `S10` |
| 8 | Bugs list / bug comments | `S11`, `S12` |
| 9 | Post comment | `S13` |
| 10 | Tracking Centre | `S14` |
| 11 | Download history | `S15` |
| 12 | MO2 API key (read-only) | `S16` |
| 13 | Download mod | Files tab → ref click → file lands in `~/.camofox/downloads` |
| 14 | Game search | `S17` |
| 15 | Batch | sequential only (no multi-tab API) |

`S1`–`S17` are the `browser_console` expressions in
[`references/browser-console-snippets.md`](references/browser-console-snippets.md).

## Prerequisites

- Hermes Agent with the built-in `browser` toolset
- Camofox browser container reachable (`camofox-browser`, profile mount `~/.camofox`)
- Nexus Mods account (required for tracking, endorsing, downloading, commenting)

## Quick Start

1. `browser_navigate("https://www.nexusmods.com/")`
2. Run `S1`; if not logged in, `browser_vault(action="save_login")` / `fill` fills the sign-in page, then re-check `S1`
3. Set `game_domain` (state file `%TEMP%/BGS-Nexus-automation/game-domain.json`)
4. `browser_navigate` the target URL → `S2` wait → run the matching `S<n>` extraction

## Architecture

- **Built-in browser only** — every page action is one of the `browser_*` tools; JS comes from `browser_console`
- **Page-side extraction** — each feature is a self-contained IIFE returning JSON
- **Shadow DOM aware** — download buttons live in `mod-download-modal`'s shadow root; they are clicked via snapshot refs
- **Downloads land on the mount** — camofox writes to `~/.camofox/downloads`, which is bind-mounted, so files appear directly at `~/.camofox/downloads` (no `docker cp`)

## Safety

- Never saves credentials, passwords, or API keys
- API key **creation** is refused — must be done manually on nexusmods.com
- Write operations (download, endorse, vote, comment) require explicit user confirmation
- All data is session-scoped

## Documentation

- Full specification: [SKILL.md](SKILL.md)
- Console snippets: [references/browser-console-snippets.md](references/browser-console-snippets.md)
- Browser-tool pitfalls: [references/browser-tool-pitfalls.md](references/browser-tool-pitfalls.md)
- DOM structure references: [references/](references/)

## License

Part of the Hermes Agent ecosystem by Nous Research.
