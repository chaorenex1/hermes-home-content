# Watch Sources, Contracts, and Blueprint Names

Absorbed from the former standalone `competitor-news-monitor` and `product-price-monitor` skills.

## Automation blueprints and state files

| Watch kind | Blueprint | Contract file |
|---|---|---|
| Company / competitor news | `competitor-watch` | `$HERMES_HOME/competitor-watches/<watch-slug>.json` |
| Price / availability | `price-watch` | `$HERMES_HOME/price-watches/<watch-slug>.json` |

One slug per contract; never let one file carry two watch kinds.

## Identity fields to freeze before scheduling

- **Company watch:** canonical name, domains, products, aliases, geography, language, requested event categories, cadence, audience, materiality threshold. A candidate article must be accept/rejectable from this record alone.
- **Price watch:** source URL/provider, listing or product ID, variant, quantity, location, dates, travelers/guests, membership/login assumptions, condition, seller, acceptable substitutes, currency, all-in vs pre-tax basis, max price, availability rule, shipping, refundability, class/cabin, cooldown, notification destination, synthetic examples with deterministic alert decisions.

## Source routes

| Need | Route |
|---|---|
| Official newsroom, blog, changelog, pricing page | `web_extract` on the exact URL |
| Feeds, releases, version history | `rss-feeds` (optional skill: `hermes skills install official/research/rss-feeds`) |
| Stateful feed watching | `blogwatcher` (optional) |
| Community sentiment, complaints, workarounds | `reddit-reading` (`search`, `thread`; optional, official/social-media) |
| Broad discovery | `web_search` → `web_extract` |
| Regulator / investor relations | filings and IR pages directly |

Community reports are evidence that users *report* something, not that it is true — pair with a primary source or label as sentiment. Report per-route coverage gaps rather than silently narrowing to what worked.

## Tick job prompt

```
cronjob(action="create", schedule="every monday 9am",
        prompt="Load target-watches-and-briefings and run the tick for the watch contract at ~/.hermes/competitor-watches/<watch-slug>.json.",
        deliver=<user destination>)
```

Pick a cadence that respects rate limits and site terms (competitor/day-plus, price/6h are reasonable starting points).

## Price-watch specifics

- Normalize to an all-in price and keep the source currency; convert only with a timestamped rate.
- Exclude volatile page metadata from the comparison; store the last good observation and the last alert fingerprint.
- Alert copy carries terms, refundability, and uncertainty and never claims inventory is reserved.
- Recovery counts as a change worth alerting on when the user asked for it.

## Company-watch specifics

- Score directness, source authority, novelty, customer/market impact, strategic relevance, and confidence against the frozen threshold; keep measured facts separate from interpretation.
- Job postings are weak supporting evidence, never proof of a product decision.
- The watchlist, event categories, and materiality rule must not drift between ticks.
