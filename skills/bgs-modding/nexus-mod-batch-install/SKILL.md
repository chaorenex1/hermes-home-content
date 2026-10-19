---
name: nexus-mod-batch-install
description: Search, download, install Nexus mods via MO2 with metadata.
version: 0.1.0
author: Hermes
platforms: [windows]
metadata:
  hermes.tags:
    - BGS
    - Modding
    - Nexus
    - MO2
---

# Nexus Mod Batch Install

Searches Nexus Mods for a keyword, finds mods not yet installed in MO2,
locates matching和光 (With Light) Simplified Chinese translations, downloads
all files via the Nexus CDN, installs through MO2 MCP (plan/apply), and
updates `meta.ini` with mod IDs, versions, categories, and N网 links.

Does NOT handle FOMOD installers or mods requiring interactive install choices.

## When to Use

- "下载 N网 MOD 并安装到 MO2"
- "搜索XX开头的MOD并下载汉化"
- "批量下载并安装 MOD"
- User wants mods + matching CHS translations installed via MO2

## Prerequisites

- MO2 MCP bound (`mo2_session`) with `permission_ceiling: full-control`
- CDP Chrome on port 9222 with Nexus login session active
- `nexus-automation.js` skill scripts available
- MO2 downloads directory known (typically `<base>/downloads`)

## How to Run

1. Use `browser_navigate` or CDP scripts to search Nexus for mod keyword
2. Use `mcp_bgs_mo2_mcp_mo2_modlist` to check installed mods
3. For each uninstalled mod, find translations on its Nexus page
4. Download via `execute_code` using Nexus API + cookies → MO2 downloads
5. Install via `mo2_install` (plan → apply for each mod)
6. Update metadata via `execute_code` writing `meta.ini` directly

## Procedure

### 1. Search Nexus for Mods

```
cd <skill-dir> && node scripts/nexus-automation.js search "KEYWORD" excludedTag=Translation count=50
```

### 2. Check MO2 for Existing Mods

Use `mcp_bgs_mo2_mcp_mo2_modlist` → filter by mod name prefix.

### 3. Find CHS Translations

For each uninstalled mod, get its description page to read the Translations
accordion table:

```
node scripts/nexus-automation.js description <modId>
```

Look for Mandarin entries with "With Light" or "和光" in the name. Verify
by checking the translation mod's description for confirmation.

### 4. Download Files

Extract Nexus cookies from CDP browser, then use the Nexus API to download:

```python
import urllib.request, urllib.parse, json

# Get download link
url = f"https://api.nexusmods.com/v1/games/{game}/mods/{mod_id}/files.json"
req = urllib.request.Request(url, headers={"apikey": API_KEY})
files = json.loads(urllib.request.urlopen(req).read())["files"]

# Pick MAIN file
main = next(f for f in files if f["category_name"] == "MAIN")

# Get CDN URL
dl_api = f"https://api.nexusmods.com/v1/games/{game}/mods/{mod_id}/files/{main['file_id']}/download_link.json"
cdn_url = json.loads(urllib.request.urlopen(urllib.request.Request(dl_api, headers={"apikey": API_KEY})).read())[0]["URI"]

# URL-encode path and download with cookies
parsed = urllib.parse.urlparse(cdn_url)
encoded = parsed._replace(path=urllib.parse.quote(parsed.path, safe='/-_.=')).geturl()
req = urllib.request.Request(encoded, headers={"Cookie": cookie_str})
content = urllib.request.urlopen(req).read()
```

Save to `<PATH_TO_MO2_INSTANCE>/downloads/<name>-<modid>.<ext>`.

### 5. Install via MO2

For each mod, use plan → apply:

```
mcp_bgs_mo2_mcp_mo2_install(archive_path, mod_name, mode="plan", profile="pbr")
# → returns plan_id + lease_token
mcp_bgs_mo2_mcp_mo2_install(archive_path, mod_name, mode="apply", plan_id, lease_token, profile="pbr")
```

Install bodies first (gui_bottom), then CHS translations on top. Each apply
invalidates other plans sharing the same lease — apply one at a time.

### 6. Update Metadata

Write `meta.ini` directly via `execute_code`:

```python
import configparser
config = configparser.ConfigParser()
config.read(meta_path)
config['General'].update({
    'gamename': 'SkyrimSE',
    'modid': str(mod_id),
    'version': version,
    'category': '43',        # Followers & Companions
    'nexuscategory': '96',   # Nexus category ID
    'nexusfilestatus': '1',
    'repository': 'Nexus',
    'notes': f'https://www.nexusmods.com/skyrimspecialedition/mods/{mod_id} | 和光汉化',
})
```

MO2 local category IDs are in `<mo2Root>/categories.dat`. Common: 43=Followers & Companions.

## Pitfalls

- **CDP browser disconnects**: Chrome on port 9222 may close. Re-run `init-browser.js`.
- **API key 403**: The MO2 API key from `/settings/api-keys` may not work for direct Nexus API calls. Fall back to cookie-based CDN downloads.
- **Plan lease conflicts**: Parallel `mo2_install plan` calls share a lease token. Apply serially; re-plan after each apply.
- **Category not showing**: Set BOTH `category` (MO2 local ID from categories.dat) AND `nexuscategory` (Nexus ID). Local ID 43 = Followers & Companions for Skyrim SE.
- **configparser whitespace**: Python's configparser adds spaces around values. MO2 tolerates this.

## Verification

After install, verify with:

```
grep -i "MOD_PREFIX" "<PATH_TO_MO2_INSTANCE>/profiles/pbr/modlist.txt" | wc -l
```

Should show expected mod count with `+` prefix (enabled).
