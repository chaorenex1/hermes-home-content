# Verified Search Result Containers

These are session-specific examples of selector shapes that passed a positive trial. They are evidence for the method, not permanent DOM guarantees. Reinspect the live page before updating or reusing a rule.

## Google Search

Tested URL shape:

```text
https://www.google.com/search?gbv=1&hl=en&q={query}
```

Verified core-content selector:

```css
#search
```

Why this shape worked: candidate result-level selectors did not consistently contain complete records, while `#search` selected one non-empty semantic result region containing headings, destination links, snippets, and result modules. The stored rule was browser-validated because direct extraction encountered automated-traffic verification.

Classification: whole-container `content` rule; browser fallback may be required. Do not describe it as repeated structured `search_results` extraction.

## Google Hong Kong

Tested URL shape:

```text
https://www.google.com.hk/search?gbv=1&hl=en&q={query}
```

Verified core-content selector:

```css
#search
```

Browser inspection returned one non-empty result region with result headings and links. Direct extraction remained challenge-sensitive.

Classification: whole-container `content` rule; browser fallback may be required.

## DuckDuckGo HTML

Tested URL shape:

```text
https://duckduckgo.com/html/?q={query}
```

Verified core-content selector:

```css
#links
```

The persisted rule was re-executed successfully and returned result titles, destination domains, snippets, dates, advertisements, and navigation content without fallback. This is the strongest example of a directly runnable HTML search rule from the session.

Classification: directly executable whole-container `content` rule.

## Startpage

Tested URL shape:

```text
https://www.startpage.com/sp/search?query={query}
```

Verified result-region selector:

```css
main .w-gl
```

Verified pagination selector:

```css
main nav[aria-label="more search results"]
```

Browser inspection returned ten result headings plus pagination controls. Direct extraction encountered verification, so the rule was classified as browser-fallback-only.

Classification: result-region `content` rule with a separate pagination block; browser fallback may be required.

## Reuse Gate

Before reusing any selector above:

1. Navigate to the exact current URL and confirm the final origin.
2. Verify the page is not a challenge, error, support, or homepage redirect.
3. Run `document.querySelectorAll(...)` for the candidate selector.
4. Confirm selected blocks contain the expected semantic fields.
5. Trial and re-run the persisted rule.
6. Report `content` versus `search_results` accurately.
