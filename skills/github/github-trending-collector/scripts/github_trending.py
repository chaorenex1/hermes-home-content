#!/usr/bin/env python3
"""
GitHub Trending Data Collector
Scrapes trending repos (daily/weekly/monthly) and enriches with GitHub API data.
Uses `gh` CLI for API calls (reliable SSL on Windows).

Usage:
  python github_trending.py --period all          # Collect all periods (skip existing)
  python github_trending.py --period daily        # Collect daily only
  python github_trending.py --period all --force  # Force re-collect all

Data saved to ~/.hermes/github_trending_data/YYYY-M/
"""

import os
import sys
import json
import subprocess
import re
import time
import urllib.request
import urllib.error
from datetime import datetime
from bs4 import BeautifulSoup

# ── Config ──────────────────────────────────────────────────────────────────
DATA_DIR = os.path.expanduser("~/.hermes/github_trending_data")
TRENDING_URL = "https://github.com/trending?since={period}"
GITHUB_API = "https://api.github.com"
MAX_README_CHARS = 5000
API_DELAY = 0.5  # seconds between API calls to be gentle

# ── HTTP helpers ─────────────────────────────────────────────────────────────
def fetch_html(url):
    """Fetch HTML content via urllib (trending page only)."""
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    except Exception as e:
        sys.stderr.write(f"Error fetching {url}: {e}\n")
        return None

# ── GitHub API via gh CLI ────────────────────────────────────────────────────
def gh_api(endpoint, retries=3):
    """Call GitHub API via `gh api` CLI. Returns parsed JSON or None.
    
    Uses gh CLI instead of urllib because Windows Python's OpenSSL has
    intermittent TLS handshake failures against api.github.com.
    """
    for attempt in range(retries):
        try:
            result = subprocess.run(
                ["gh", "api", endpoint],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout)
            elif result.returncode != 0:
                sys.stderr.write(f"  gh api {endpoint} failed (attempt {attempt+1}): {result.stderr.strip()[:200]}\n")
        except subprocess.TimeoutExpired:
            sys.stderr.write(f"  gh api {endpoint} timed out (attempt {attempt+1})\n")
        except json.JSONDecodeError:
            sys.stderr.write(f"  gh api {endpoint} returned non-JSON (attempt {attempt+1})\n")
        except Exception as e:
            sys.stderr.write(f"  gh api {endpoint} error (attempt {attempt+1}): {e}\n")
        if attempt < retries - 1:
            time.sleep(2 * (attempt + 1))
    return None

# ── Trending page parser ─────────────────────────────────────────────────────
def parse_trending_html(html_bytes):
    """Parse GitHub trending HTML and extract repo list."""
    html = html_bytes.decode("utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.find_all("article", class_="Box-row")
    
    repos = []
    for article in articles:
        h2 = article.find("h2")
        repo_path = None
        if h2:
            a = h2.find("a")
            if a:
                href = a.get("href", "").strip("/")
                if "/" in href:
                    repo_path = href
        
        if not repo_path:
            continue
        
        repo_name = repo_path.split("/")[-1]
        
        p = article.find("p")
        description = p.get_text(strip=True) if p else ""
        
        lang_span = article.find("span", itemprop="programmingLanguage")
        primary_lang = lang_span.get_text(strip=True) if lang_span else ""
        
        stars = 0
        forks = 0
        for link in article.find_all("a", href=True):
            href = link.get("href", "")
            text = link.get_text(strip=True).replace(",", "")
            if "/stargazers" in href:
                try: stars = int(text)
                except: pass
            elif "/forks" in href:
                try: forks = int(text)
                except: pass
        
        period_stars = 0
        for span in article.find_all("span"):
            text = span.get_text(strip=True)
            if "stars" in text:
                num = re.sub(r"[^\d]", "", text)
                try: period_stars = int(num)
                except: pass
        
        repos.append({
            "repo_name": repo_name,
            "repo_id": repo_path,
            "repo_url": f"https://github.com/{repo_path}",
            "short_description": description,
            "primary_language": primary_lang,
            "stars_trending": stars,
            "forks_trending": forks,
            "period_stars": period_stars,
        })
    
    return repos

# ── GitHub API enrichment ────────────────────────────────────────────────────
def calculate_language_percentages(langs):
    """Convert language byte counts to percentages."""
    total = sum(langs.values())
    if total == 0:
        return {}
    return {lang: round((bytes_count / total) * 100, 2) for lang, bytes_count in langs.items()}

def enrich_repo(repo):
    """Enrich a trending repo with GitHub API data via gh CLI."""
    repo_path = repo["repo_id"]
    
    # 1. Repo details
    details = gh_api(f"repos/{repo_path}")
    time.sleep(API_DELAY)
    
    if not details:
        # Fallback: use scraped data only
        owner_login = repo_path.split("/")[0]
        return {
            "repo_name": repo["repo_name"],
            "repo_id": repo_path,
            "repo_url": f"https://github.com/{repo_path}",
            "languages": {repo.get("primary_language", "Unknown"): 100.0} if repo.get("primary_language") else {},
            "stars": repo.get("stars_trending", 0),
            "forks": repo.get("forks_trending", 0),
            "short_description": repo.get("short_description", ""),
            "detailed_summary": "",
            "owner": {
                "login": owner_login,
                "github_id": None,
                "github_url": f"https://github.com/{owner_login}",
            },
            "topics": [],
            "homepage": "",
            "license": "",
            "created_at": "",
            "updated_at": "",
            "period_stars": repo.get("period_stars", 0),
        }
    
    # 2. Languages
    langs_raw = gh_api(f"repos/{repo_path}/languages")
    time.sleep(API_DELAY)
    languages = calculate_language_percentages(langs_raw) if langs_raw else {}
    
    # 3. README for detailed summary
    readme_data = gh_api(f"repos/{repo_path}/readme")
    time.sleep(API_DELAY)
    readme = ""
    if readme_data and "content" in readme_data:
        import base64
        try:
            readme = base64.b64decode(readme_data["content"]).decode("utf-8", errors="replace")
            if len(readme) > MAX_README_CHARS:
                readme = readme[:MAX_README_CHARS] + "\n... [truncated]"
        except:
            readme = ""
    
    # 4. Owner info
    owner_login = details.get("owner", {}).get("login", repo_path.split("/")[0])
    owner_details = gh_api(f"users/{owner_login}")
    time.sleep(API_DELAY)
    
    owner_id = None
    owner_html_url = f"https://github.com/{owner_login}"
    if owner_details:
        owner_id = owner_details.get("id")
        owner_html_url = owner_details.get("html_url", owner_html_url)
    else:
        owner_data = details.get("owner", {})
        owner_id = owner_data.get("id")
        owner_html_url = owner_data.get("html_url", owner_html_url)
    
    return {
        "repo_name": details.get("name", repo["repo_name"]),
        "repo_id": repo_path,
        "repo_url": details.get("html_url", f"https://github.com/{repo_path}"),
        "languages": languages,
        "stars": details.get("stargazers_count", repo.get("stars_trending", 0)),
        "forks": details.get("forks_count", repo.get("forks_trending", 0)),
        "short_description": details.get("description") or repo.get("short_description", ""),
        "detailed_summary": readme,
        "owner": {
            "login": owner_login,
            "github_id": owner_id,
            "github_url": owner_html_url,
        },
        "topics": details.get("topics", []),
        "homepage": details.get("homepage", ""),
        "license": (details.get("license") or {}).get("name", ""),
        "created_at": details.get("created_at", ""),
        "updated_at": details.get("updated_at", ""),
        "period_stars": repo.get("period_stars", 0),
    }

# ── File path helpers ────────────────────────────────────────────────────────
def get_data_dir(now=None):
    if now is None:
        now = datetime.now()
    year_month = f"{now.year}-{now.month}"
    dir_path = os.path.join(DATA_DIR, year_month)
    os.makedirs(dir_path, exist_ok=True)
    return dir_path

def get_daily_filepath(now=None):
    if now is None:
        now = datetime.now()
    return os.path.join(get_data_dir(now), f"{now.year}-{now.month}-{now.day}.json")

def get_weekly_filepath(now=None):
    if now is None:
        now = datetime.now()
    week_of_month = ((now.day - 1) // 7) + 1
    return os.path.join(get_data_dir(now), f"{now.year}-{now.month}-{week_of_month}.json")

def get_monthly_filepath(now=None):
    if now is None:
        now = datetime.now()
    return os.path.join(get_data_dir(now), f"{now.year}-{now.month}.json")

# ── Main collection logic ────────────────────────────────────────────────────
def collect_trending(period, output_path):
    """Collect trending repos for a period and save to file."""
    print(f"Fetching {period} trending from GitHub...")
    html_data = fetch_html(TRENDING_URL.format(period=period))
    if not html_data:
        print(f"  ERROR: Failed to fetch trending page for {period}")
        return False
    
    repos = parse_trending_html(html_data)
    print(f"  Found {len(repos)} trending repos")
    
    if not repos:
        print(f"  WARNING: No repos found for {period}")
        return False
    
    enriched_repos = []
    for i, repo in enumerate(repos):
        print(f"  [{i+1}/{len(repos)}] Enriching {repo['repo_id']}...", flush=True)
        enriched = enrich_repo(repo)
        enriched_repos.append(enriched)
    
    output = {
        "period": period,
        "collected_at": datetime.now().isoformat(),
        "total_repos": len(enriched_repos),
        "repos": enriched_repos,
    }
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"  Saved {len(enriched_repos)} repos to {output_path}")
    return True

def main():
    import argparse
    parser = argparse.ArgumentParser(description="GitHub Trending Data Collector")
    parser.add_argument("--force", action="store_true", help="Re-collect even if file exists")
    parser.add_argument("--period", choices=["daily", "weekly", "monthly", "all"], default="all")
    args = parser.parse_args()
    
    now = datetime.now()
    results = []
    
    periods_to_run = []
    if args.period == "all":
        periods_to_run = ["daily", "weekly", "monthly"]
    else:
        periods_to_run = [args.period]
    
    for period in periods_to_run:
        if period == "daily":
            path = get_daily_filepath(now)
        elif period == "weekly":
            path = get_weekly_filepath(now)
        elif period == "monthly":
            path = get_monthly_filepath(now)
        
        if os.path.exists(path) and not args.force:
            print(f"{period}: data already exists at {path} (use --force to re-collect)")
            results.append((period, True, path))
            continue
        
        print(f"\n=== {period.upper()} Trending → {path} ===")
        ok = collect_trending(period, path)
        results.append((period, ok, path))
    
    print("\n" + "="*60)
    print("COLLECTION SUMMARY")
    print("="*60)
    for period, ok, path in results:
        status = "OK" if ok else "FAILED"
        print(f"  {period:8s}: {status} → {path}")
    
    return 0 if all(ok for _, ok, _ in results) else 1

if __name__ == "__main__":
    sys.exit(main())
