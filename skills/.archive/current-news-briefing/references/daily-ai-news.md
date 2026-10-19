# Daily AI News Reference

Use this reference when the current-news topic is artificial intelligence.

## Coverage matrix

Check all six lanes before ranking stories:

1. **Models and agents** — launches, capability changes, context/tool use, pricing, availability, retirements.
2. **Compute and infrastructure** — GPUs/accelerators, local inference, datacenters, cloud, energy, capital expenditure.
3. **Business and capital** — revenue, funding, acquisitions, partnerships, API pricing; distinguish filings/official statements from market reports.
4. **Policy and safety** — regulation, model testing, copyright, cybersecurity, agent incidents, governance.
5. **Applications and labor** — healthcare, education, enterprise deployment, robotics, labor-market evidence.
6. **Research and open source** — papers, open weights, datasets, benchmarks, reproducibility.

A balanced daily brief normally draws from at least three lanes. Do not force lane coverage when no verified news exists.

## Source hierarchy by claim

### Product and model facts

1. Official announcement, documentation, model card, changelog, or API pricing page.
2. Independent benchmark or reputable technical analysis.
3. Reputable technology press.

Label benchmark results from the developer as self-reported. Capture exact model name, release date, availability, context limits, pricing, and whether weights are truly open or only downloadable under restrictions.

### Business and investment

1. Regulatory filing, earnings release, official statement.
2. Reuters/AP/Bloomberg/FT or equivalent with named sourcing.
3. Secondary financial press.

Treat “in talks,” capital-spending leaks, valuations, and acquisition rumors as unconfirmed until official. Do not convert a reported plan into a completed transaction.

### Policy and security

1. Statute, regulator, court filing, government announcement, or incident disclosure.
2. Independent reporting from a high-quality outlet.
3. Specialist analysis for implications.

For agent incidents, separate:
- what the human requested;
- what the agent actually did;
- which model, harness, and tools were involved;
- whether “autonomous” is demonstrated or merely asserted;
- the concrete permission/control failure.

### Macro and labor impact

Prefer national statistics, peer-reviewed work, company filings, and reputable reporting. Avoid deriving broad economic conclusions from a single company anecdote.

## Recency labels

Use one of these internal labels per item:

- `TODAY_EVENT`: event and coverage occurred today.
- `TODAY_COVERAGE`: published today about an earlier event.
- `DEVELOPING`: earlier event with a material update today.
- `RUMOR`: current report without primary confirmation.
- `BACKGROUND`: useful context only; not headline news.

Only the first three belong in an unqualified “today’s news” list. `RUMOR` needs explicit attribution; `BACKGROUND` belongs in context sections.

## Output pattern

For each selected item:

**Headline**  
What happened, with date/status/source attribution.  
**Why it matters:** one sentence connecting it to costs, capabilities, safety, competition, or adoption.

Conclude with 3–5 cross-story themes. Avoid stock-picking language unless explicitly requested.

## Common quality failures

- Treating a daily roundup or AI-generated digest as the original source.
- Using a vendor homepage that has no visible publication date to prove “today.”
- Claiming an “open-source” model when only weights are available under a restrictive license.
- Presenting model-family pricing changes without the exact pricing page or independent report.
- Repeating a single announcement as model news, chip news, and business news.
- Using current publication timestamps to conceal that the underlying announcement is days old.
- Linking to a generic publication homepage instead of the article or timestamped feed item.
