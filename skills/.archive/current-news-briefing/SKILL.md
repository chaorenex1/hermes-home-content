---
name: current-news-briefing
description: Use when briefing today's news with verified recency.
version: 1.0.0
metadata:
  hermes:
    tags: [news, current-events, briefing, verification, citations]
    category: research
---

# Current News Briefing

Produce a concise, source-grounded briefing whose definition of “today” is explicit and whose recency claims are verified independently of search-result ranking.

## Trigger

Use for “today’s news,” daily digests, live/current-event roundups, or topic-specific current briefings. Pair with `grounded-citations` for citation ledgers and with domain skills where applicable.

## Non-negotiable invariants

1. **Establish the clock first.** Read the live date, time, timezone, and UTC offset with a system tool. Never infer “today” from conversation metadata or model knowledge.
2. **Define the cutoff.** State `截至 <local time>` and distinguish:
   - published today;
   - announced earlier but still developing today;
   - rumors or unconfirmed reports.
3. **Search snippets are discovery evidence, not body evidence.** A snippet may identify a candidate and its apparent timestamp, but detailed claims require the source page, official announcement, a reputable syndication, or a timestamped feed entry.
4. **Verify dates independently.** Search engines can surface stale pages, future-dated pages, generic topic pages, or generated summaries. Confirm publication time from the page metadata or a current RSS/Atom item before calling an item “today.”
5. **Prefer source quality over volume.** Official announcement for product facts; Reuters/AP/BBC or equivalent for independent reporting; specialist outlets for context. Label company benchmarks and forecasts as self-reported.
6. **Do not promote rumor into fact.** Use attributed language such as “据报道/尚未获公司确认,” and omit weak rumors unless they materially affect the briefing.

## Workflow

### 1. Set scope

Record topic, geography, reader timezone, cutoff time, and desired depth. For an unspecified Chinese-language request, use the host’s local timezone and include both Chinese and international sources.

### 2. Discover broadly in parallel

Run several independent queries covering:
- broad topic + today’s date;
- official company/newsroom domains;
- reputable wire services and major publications;
- Chinese and English wording when relevant;
- subtopics such as models, chips, regulation, funding, security, and applications.

Use RSS/Atom queries as a recency ledger when normal search results are noisy. Feed entries provide publisher, title, and publication timestamp; they still do not replace reading the article for detailed claims.

### 3. Build a candidate table

For every candidate capture:
- headline;
- publication timestamp and timezone;
- original publisher;
- canonical or stable URL;
- primary/secondary/rumor classification;
- whether the underlying event happened today or earlier;
- one-sentence significance.

Deduplicate syndicated copies by underlying event, not by headline wording.

### 4. Verify load-bearing claims

For product launches, fetch the official announcement and extract the date, availability, technical specifications, and limitations. For business, policy, security, or macroeconomic claims, require independent reporting. Cross-check disputed facts with a second source.

If an article body is inaccessible, either:
- cite only what the feed/snippet literally establishes (headline, publisher, timestamp), or
- use a reputable syndication carrying the same report.

Never invent details to fill an inaccessible page.

### 5. Rank and write

Rank by impact, novelty, evidence quality, and relevance—not by search position. A useful default structure is:
1. 5–8 key stories;
2. each with **what happened** and **why it matters**;
3. a short “today’s themes” synthesis;
4. a generated source list.

Keep “today’s new announcements” separate from “last 24–72 hours still developing.” Explicitly identify vendor-reported benchmarks.

### 6. Citation verification

Register URLs at retrieval time. Cite per sentence. Generate—not hand-type—the source block when a citation ledger is available. Before delivery, verify that every cited ID resolves to the intended URL and that every factual headline item has provenance.

## Failure handling

- If extraction fails, change method once: official page → syndication/feed → another reputable report. Do not loop on the same inaccessible page.
- If search results conflict on date or details, downgrade confidence and present the conflict explicitly.
- If current coverage is sparse, say so and provide fewer verified items rather than padding with old or speculative stories.

## Pitfalls

- Treating a generic topic page as a dated article.
- Calling an event “today” because it appears in today’s search results.
- Mixing announcement date with coverage date.
- Repeating several syndicated versions as separate stories.
- Reporting vendor benchmark numbers without attribution.
- Using opaque aggregator links when a stable canonical URL is available.
- Writing a polished narrative before the source/timestamp ledger exists.

## Verification checklist

- [ ] Live local date/time and timezone recorded.
- [ ] Cutoff disclosed.
- [ ] Every “today” item has a verified timestamp.
- [ ] Event date and article date are not conflated.
- [ ] Official product claims are labeled as vendor claims.
- [ ] Rumors are attributed or excluded.
- [ ] Duplicate events are merged.
- [ ] Citations and source URLs are mechanically checked where possible.

## References

- `references/daily-ai-news.md` — topic coverage matrix and source hierarchy for AI-news briefings.
