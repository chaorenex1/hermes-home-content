# Feishu Drive Folder Management

GitHub Trending reports are organized in Feishu Drive using a hierarchical folder structure to prevent document clutter in the root directory. Documents are checked for duplicates before creation — existing docs with the same name are deleted first.

## Folder Hierarchy

```
Drive Root
└── GitHub Trending/          ← root folder (cached as "root")
    ├── 2026-7/               ← monthly subfolder (cached as "month_2026-7")
    │   ├── Github项目2026年7月5号热度    ← daily report doc
    │   └── Github项目2026年7月Week1热度  ← weekly report doc
    ├── 2026-6/
    │   └── ...
    └── 2026-8/
        └── ...
```

## Required OAuth Scopes

Folder operations require scopes NOT included in the default lark-cli auth:

| Operation | Command | Required Scopes |
|-----------|---------|-----------------|
| List folder contents | `drive files list --folder-token <token>` | `space:document:retrieve` |
| Create folder | `drive +create-folder --name <name>` | `drive:drive`, `space:folder:create` |
| Move doc to folder | `drive +move --file-token <id> --type docx --folder-token <token>` | `drive:drive` |
| Delete doc | `drive +delete --file-token <token> --type docx --yes` | `drive:drive` |

### Auth Command

```bash
lark-cli auth login \
  --scope "drive:drive" \
  --scope "space:folder:create" \
  --scope "space:document:retrieve"
```

This produces a verification URL + QR code for the user to authorize.

### CRITICAL: Do NOT use `drive +search`

`drive +search` requires `search:docs:read` scope, which is an **admin-managed scope** that cannot be self-authorized via OAuth device flow. Always use `drive files list --folder-token <token>` instead, which only needs `space:document:retrieve` (user-authorizable).

### Scope Split: user vs bot

- `user` identity: Can create folders, list folder contents, move docs, and delete docs after auth. This is the primary identity for all folder operations.
- `bot` identity: Needs `drive:drive` + `space:folder:create` app scopes applied at the Feishu developer console. The app ID is `cli_aac35ea82bf89bdb`. Bot identity is only used as a fallback for doc creation and IM notification.

## Local Token Cache

**File**: `~/.hermes/github_trending_data/feishu_folders.json`

```json
{
  "root": "Wx0FfkFMqlsWK6dXJbBcgSGpn6F",
  "month_2026-7": "TP0OfHy3glu7ZpdBh5bcBNGPnnd"
}
```

### Cache Logic (`ensure_folder()`)

1. Check `feishu_folders.json` for a cached token under the cache key (e.g., `"root"`, `"month_2026-7"`).
2. If cached → return token immediately (no API call).
3. If not cached → list parent folder contents via `drive files list` and look for a matching subfolder by name.
4. If found → use existing token (don't create).
5. If not found → create folder via `drive +create-folder`.
6. Save token to cache file.

### Cache Invalidation

If a folder is deleted manually in Feishu Drive, the cached token becomes stale. The `drive +move` call will fail with an error. To fix:

```bash
rm ~/.hermes/github_trending_data/feishu_folders.json
# Next run will re-list and re-create folders
```

## CRITICAL: `docs +create --parent-token` Does NOT Work

**Verified 2026-07-05:** The Feishu API accepts the `--parent-token` parameter in `docs +create` (it appears in `--dry-run` output as `parent_token` in the request body), but the created document is **NOT** actually placed inside the specified folder. Three test documents created with `--parent-token` all landed in Drive root.

This is a **Feishu API-level limitation**, not a lark-cli bug. The `--parent-token` parameter is accepted but silently ignored by the document creation endpoint.

### The Reliable Pattern: Create-Then-Move

```python
# Step 1: Create doc WITHOUT --parent-token
result = run_lark_cli([
    "docs", "+create",
    "--as", identity,          # "user" first, "bot" fallback
    "--title", title,
    "--content", f"@{tmp_name}",
])
doc_id = result["data"]["document"]["document_id"]
doc_url = result["data"]["document"]["url"]

# Step 2: Move doc into target folder
if parent_token and doc_id:
    move_result = run_lark_cli([
        "drive", "+move",
        "--as", identity,
        "--file-token", doc_id,
        "--type", "docx",
        "--folder-token", parent_token,
    ])
    if move_result and move_result.get("ok"):
        print(f"  📁 Moved to folder: {parent_token}")
    else:
        print(f"  ⚠️ Move to folder failed, doc remains in root")
```

## Duplicate Document Check (delete-before-create)

Before creating a new document, check if a doc with the same name already exists in the target folder. If found, delete it first to prevent duplicates accumulating across re-runs.

```python
# Check for existing doc with same name
existing_doc = find_child_by_name(parent_token, title, child_type="docx")
if existing_doc:
    print(f"  🗑️ Found existing doc '{title}', deleting...")
    delete_file_by_token(existing_doc, file_type="docx")
    print(f"  ✅ Deleted old doc: {existing_doc}")
```

### Key Functions

```python
def list_folder_contents(folder_token, dry_run=False):
    """List files/folders inside a Feishu Drive folder.
    Uses drive files list API (requires space:document:retrieve scope).
    Returns list of {name, token, type} dicts.
    """
    args = ["drive", "files", "list", "--folder-token", folder_token, "--page-size", "200"]
    result = run_lark_cli(args, dry_run=dry_run)
    if not result or not result.get("ok"):
        return []
    return result.get("data", {}).get("files", [])


def find_child_by_name(folder_token, name, child_type=None, dry_run=False):
    """Find a child file/folder by name inside a Feishu Drive folder.
    Returns child token or None.
    """
    files = list_folder_contents(folder_token, dry_run=dry_run)
    for f in files:
        if f.get("name") == name:
            if child_type is None or f.get("type") == child_type:
                return f.get("token")
    return None


def delete_file_by_token(file_token, file_type="docx", dry_run=False):
    """Delete a file/folder in Feishu Drive by token."""
    args = ["drive", "+delete", "--file-token", file_token, "--type", file_type, "--yes"]
    result = run_lark_cli(args, dry_run=dry_run)
    return bool(result and result.get("ok"))
```

## Implementation in feishu_report.py

### `create_feishu_doc()` full flow

```python
def create_feishu_doc(analysis, dry_run=False):
    content = build_feishu_doc_content(analysis)
    title = f"Github项目{analysis['display_label']}热度"
    date_str = analysis.get("date_str", "")

    # 1. Ensure folder hierarchy: GitHub Trending / {year-month} /
    parent_token = ensure_report_folder(date_str, dry_run=dry_run)

    # 2. Check for existing doc with same name — delete before creating
    if parent_token:
        existing_doc = find_child_by_name(parent_token, title, child_type="docx")
        if existing_doc:
            delete_file_by_token(existing_doc, file_type="docx")

    # 3. Create doc (WITHOUT --parent-token — it doesn't work)
    for identity in ["user", "bot"]:
        result = run_lark_cli(["docs", "+create", "--as", identity,
                               "--title", title, "--content", f"@{tmp_name}"])
        if result and result.get("ok"):
            doc_id = result["data"]["document"]["document_id"]

            # 4. Move doc into target folder (create-then-move pattern)
            if parent_token and doc_id:
                run_lark_cli(["drive", "+move", "--as", identity,
                              "--file-token", doc_id, "--type", "docx",
                              "--folder-token", parent_token])
            return {"url": doc_url, "id": doc_id}
```

### Graceful Degradation

If folder management fails (missing scopes, deleted folders, API errors), the document is still created — just in the Drive root instead of the organized folder. This ensures the pipeline never blocks on folder issues.

## lark-cli Commands Reference

```bash
# List folder contents (requires space:document:retrieve scope)
lark-cli drive files list --folder-token <token> --page-size 200

# Create a folder in root (requires drive:drive + space:folder:create scopes)
lark-cli drive +create-folder --name "GitHub Trending"

# Create a folder in a parent folder
lark-cli drive +create-folder --name "2026-7" --folder-token <parent_token>

# Move a document into a folder (THE RELIABLE WAY to organize docs)
lark-cli drive +move --file-token <doc_id> --type docx --folder-token <folder_token>

# Delete a document (requires --yes to skip confirmation)
lark-cli drive +delete --file-token <token> --type docx --yes

# NOTE: docs +create --parent-token <token> does NOT work —
# the API accepts the parameter but does not place the doc in the folder.
# Always use drive +move after creation.

# NOTE: drive +search requires search:docs:read scope (admin-managed).
# Do NOT use it. Use `drive files list` instead.
```
