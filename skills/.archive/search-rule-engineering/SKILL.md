---
name: search-rule-engineering
description: Build and verify web search extraction rules.
version: 1.0.0
author: Masía
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Search, Extraction, Browser Automation, Verification]
    related_skills: [web-ai-search]
---

# Search Rule Engineering

Build or repair CSS-backed rules for search-result and content extraction. The governing principle is evidence: persist only selectors that were exercised against the requested origin and returned the intended semantic block.

## When to Use

- A search engine rule returns empty, partial, or malformed result blocks.
- Direct crawling reaches robot verification and needs browser-backed inspection.
- A URL redirects to another origin or returns only a JavaScript application shell.
- A stored rule must be classified as directly runnable, browser-fallback-only, or unsuitable for CSS extraction.

Do not use this skill for choosing search terms, summarizing search results, or bypassing access controls.

## Rule-Type Boundary

Identify the required rule type before learning anything:

- `content`: selects one or more complete core-content containers for later parsing.
- `search_results`: selects repeated result records with the fields expected by the search planner.

A valid whole-page `content` selector does not prove that a structured `search_results` rule exists. Report the persisted type explicitly and never describe one as the other.

## Failure Classification

Classify the observed page before changing selectors:

1. **Selector boundary defect** — the expected results are present, but candidate selectors capture fragments. Prefer a stable whole result container over brittle leaf combinations.
2. **Robot verification** — the crawler is blocked, while the user's browser can load semantic results. A rule may be browser-fallback-only after browser-side validation.
3. **Transport failure** — neither crawler nor browser obtains the page. Do not infer a selector.
4. **Origin identity mismatch** — the requested engine redirects to another origin or homepage. Do not save the destination DOM under the requested engine.
5. **Dynamic shell** — the initial document contains controls but not result data. CSS-only extraction is unsuitable unless a rendered browser trial captures the completed result region.

## Procedure

1. **Freeze the target.** Record the exact URL, origin, path, query intent, language, and expected rule type. Completion criterion: the trial cannot silently switch domains or result verticals.
2. **Inspect without selectors.** Use the rule engine's selector-free crawl first. Check final URL, title, challenge/error markers, and whether semantic results are in the returned document. Completion criterion: the failure class above is known.
3. **Use browser fallback when required.** Navigate to the exact URL, confirm the expected page is loaded, then inspect bounded candidates with `document.querySelectorAll(...)`. Do not inspect cookies, storage, or unrelated page state. Completion criterion: the candidate is non-empty and contains the expected title, URL, and snippet or complete core content.
4. **Choose the semantic boundary.** Prefer the smallest stable selector that contains the complete intended unit. If repeated result blocks cannot be proven, store a whole-container `content` rule rather than pretending it is structured `search_results` extraction.
5. **Trial before persistence.** Run the candidate selector against the requested URL. Reject empty output, challenge pages, support/error pages, wrong-origin content, and pre-render shells. Completion criterion: selected blocks are semantically correct.
6. **Persist safely.** Create or update through the rule API, preserving origin/path scope and optimistic versioning. Mark whether execution is direct or browser-fallback-only.
7. **Re-run the stored rule.** Verification must exercise the persisted version, not just the browser expression. Report rule ID, version, rule type, selector, and execution mode. Completion criterion: the stored rule returns non-empty intended content or has a separately verified browser fallback obligation.

## Routing Guidance

- Prefer a directly executable static/HTML rule as the primary engine.
- Use independently verified browser-fallback rules only when direct crawling is challenged.
- Remove engines from the active pool when no positive trial exists; absence of a rule is safer than a speculative selector.
- Route computation tools and heavily dynamic applications through dedicated adapters rather than general web-result extraction.

## Pitfalls

- Do not combine individually plausible leaf selectors if none returns a complete result unit.
- Do not treat a browser-visible page as proof that the headless rule works; record fallback mode explicitly.
- Do not persist a rule after `crawl_failed` when browser validation also failed.
- Do not save a redirect destination's selectors under the requested origin.
- Do not mistake a dynamic client shell for computed result content.
- Do not claim structured result extraction from a whole-page content rule.
- Do not repeat the same blocked request unchanged; change the URL variant, route, or inspection method once, then stop without a positive trial.

## Verification Checklist

- Exact requested origin/path retained
- No CAPTCHA, verification, support, or error page selected
- Selector returns complete semantic blocks
- Stored rule was re-executed
- Rule type reported accurately
- Direct versus browser-fallback mode recorded
- No speculative rule persisted for an unverified page

Validated examples and selector-shape notes are in `references/verified-search-result-containers.md` (re-homed to the `web-retrieval-resilience` umbrella); revalidate them against the current DOM before reuse.
