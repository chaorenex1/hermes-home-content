# GitHub Trending Page Structure & API Reference

## Trending HTML Structure

GitHub trending pages (`https://github.com/trending?since={daily|weekly|monthly}`) render repos as `<article class="Box-row">` elements.

### Key elements per article:

| Data | Selector | Notes |
|------|----------|-------|
| Repo path | `h2 > a[href]` | href = `/owner/repo-name` |
| Description | `p` | Plain text, may be empty |
| Primary language | `span[itemprop="programmingLanguage"]` | Single language name |
| Stars | `a[href*="/stargazers"]` | Text contains comma-separated number |
| Forks | `a[href*="/forks"]` | Text contains comma-separated number |
| Period stars | `span` containing "stars today/week/month" | e.g. "718 stars today" |

### BeautifulSoup extraction:

```python
from bs4 import BeautifulSoup

soup = BeautifulSoup(html, "html.parser")
articles = soup.find_all("article", class_="Box-row")

for article in articles:
    h2 = article.find("h2")
    a = h2.find("a")
    repo_path = a.get("href", "").strip("/")  # "openai/codex-plugin-cc"
    repo_name = repo_path.split("/")[-1]     # "codex-plugin-cc"
    
    p = article.find("p")
    description = p.get_text(strip=True) if p else ""
    
    lang_span = article.find("span", itemprop="programmingLanguage")
    language = lang_span.get_text(strip=True) if lang_span else ""
    
    # Stars & forks
    for link in article.find_all("a", href=True):
        href = link.get("href", "")
        text = link.get_text(strip=True).replace(",", "")
        if "/stargazers" in href:
            stars = int(text)
        elif "/forks" in href:
            forks = int(text)
```

## GitHub API Endpoints Used

All called via `gh api` subprocess (NOT urllib on Windows):

| Endpoint | Returns | Key Fields |
|----------|---------|------------|
| `repos/{owner}/{repo}` | Repo details | `name`, `full_name`, `html_url`, `description`, `stargazers_count`, `forks_count`, `owner.login`, `owner.id`, `owner.html_url`, `topics`, `homepage`, `license.name`, `created_at`, `updated_at` |
| `repos/{owner}/{repo}/languages` | Language bytes | `{"JavaScript": 295541, "Python": 10000}` — raw byte counts, convert to percentages |
| `repos/{owner}/{repo}/readme` | README | `content` field is base64-encoded; `encoding: "base64"` |
| `users/{login}` | Owner details | `id`, `login`, `html_url`, `type` (User/Organization) |

### Language percentage calculation:

```python
langs_raw = {"JavaScript": 295541, "Python": 10000}
total = sum(langs_raw.values())  # 305541
percentages = {lang: round((bytes / total) * 100, 2) for lang, bytes in langs_raw.items()}
# {"JavaScript": 96.73, "Python": 3.27}
```

### README decoding:

```python
import base64
readme_data = gh_api(f"repos/{repo_path}/readme")
content = base64.b64decode(readme_data["content"]).decode("utf-8", errors="replace")
# Truncate to 5000 chars for storage
if len(content) > 5000:
    content = content[:5000] + "\n... [truncated]"
```

## Windows SSL Issue — Technical Detail

### Symptom

`urllib.request.urlopen("https://api.github.com/...")` fails on Windows with:
```
ssl.SSLError: [SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1016)
ssl.SSLError: [SSL: WRONG_VERSION_NUMBER]
ssl.SSLError: _ssl.c:999: The handshake operation timed out
```

### Root Cause

Windows Python's bundled OpenSSL has intermittent TLS negotiation issues with `api.github.com`. The TLS handshake sometimes fails mid-negotiation, causing `UNEXPECTED_EOF_WHILE_READING` or timeout. This does not affect `github.com` (the trending page) — only `api.github.com`.

### Fix

Use `gh api` as a subprocess. The Go-based `gh` CLI uses its own TLS stack (not Python's OpenSSL), which handles the handshake correctly:

```python
import subprocess, json

def gh_api(endpoint, retries=3):
    for attempt in range(retries):
        try:
            result = subprocess.run(
                ["gh", "api", endpoint],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            pass
        if attempt < retries - 1:
            import time; time.sleep(2 * (attempt + 1))
    return None
```

### Alternative (if gh unavailable)

Use `requests` with a custom SSL adapter, but `gh api` is simpler and already authenticated.

## Hermes Terminal Token Redaction

The Hermes `terminal` tool automatically redacts GitHub OAuth tokens (`gho_...`) in output. When `gh auth token` is called via terminal, the output appears as `gho_6L...427S` (truncated with `...`), making it impossible to capture the real token into a Python variable.

### Workaround

Never extract the token — call `gh api` directly from Python as a subprocess. The `gh` CLI uses its own credential store and doesn't need the token passed explicitly.
