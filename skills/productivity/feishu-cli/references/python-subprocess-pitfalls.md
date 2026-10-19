# lark-cli from Python subprocess: Windows Pitfalls

Recorded from a real Feishu integration project (GitHub Trending → Feishu reports) on Windows 10.

## Pitfall 1: `.CMD` shim — Python subprocess can't find `lark-cli`

On Windows, `lark-cli` is installed as a `.CMD` shim (`lark-cli.CMD`), not a bare executable. Python's `subprocess.run(["lark-cli", ...])` fails with `WinError 2: 系统找不到指定的文件`.

### Fix: Resolve full path with `shutil.which()`

```python
import shutil

def find_lark_cli():
    path = shutil.which("lark-cli")
    if path:
        return path
    candidates = [
        os.path.expanduser("~/AppData/Roaming/npm/lark-cli.cmd"),
        "C:\\nvm4w\\nodejs\\lark-cli.cmd",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "lark-cli"

lark_exe = find_lark_cli()
result = subprocess.run([lark_exe, "docs", "+create", ...], capture_output=True, text=True, timeout=120)
```

`shutil.which("lark-cli")` returns `C:\nvm4w\nodejs\lark-cli.CMD` — pass that full path to subprocess.

## Pitfall 2: `--content @file` requires relative paths

The `lark-cli docs +create --content @filepath` flag rejects absolute paths:

```
--content: invalid file path: --file must be a relative path within the current directory
```

### Fix: Write temp file to CWD, reference by filename only

```python
tmp_name = f"_content_{os.getpid()}.xml"
tmp_path = os.path.join(os.getcwd(), tmp_name)
with open(tmp_path, "w", encoding="utf-8") as f:
    f.write(content)
# lark-cli accepts: @_content_12345.xml
```

## Pitfall 3: User identity missing `im:message.send_as_user` scope

`im +messages-send --as user` fails if the user OAuth token lacks `im:message.send_as_user`.

### Fix: Fall back to bot identity with `--user-id`

Bot identity can send messages but requires explicit `--user-id` (recipient open_id). Get it from `lark-cli whoami --json`:

```python
whoami = run_lark_cli(["whoami", "--json"])
user_open_id = whoami["onBehalfOf"]["openId"]

for identity in ["user", "bot"]:
    result = run_lark_cli([
        "im", "+messages-send",
        "--as", identity,
        "--user-id", user_open_id,
        "--markdown", text,
    ])
    if result and result.get("ok"):
        return True
```

## Pitfall 4: `npm root -g` needs `shell=True` in subprocess

`npm` is a `.CMD` shim on Windows. Use `shell=True`:

```python
npm_root = subprocess.run(
    ["npm", "root", "-g"],
    capture_output=True, text=True, timeout=10,
    shell=True
).stdout.strip()
```

## Pitfall 5: Embedded skill reading requirement

`lark-cli docs --help` says agents MUST read embedded skills before using commands:
- `lark-cli skills read lark-doc` — main docs workflow
- `lark-cli skills read lark-doc references/lark-doc-xml.md` — XML format rules
- `lark-cli skills read lark-doc references/lark-doc-create.md` — create workflow
- `lark-cli skills read lark-im` — IM workflow

## Pitfall 6: `--text` vs `--markdown` vs `--content` for IM messages

**Verified on 2026-07-05 via mobile + desktop screenshots. User corrected 5+ times.**

The three content flags for `im +messages-send` behave very differently:

| Flag | msg_type | Multi-line rendering | Use case |
|------|----------|---------------------|----------|
| `--text` | `text` | **Collapses to title-only** — `\n` not rendered as line breaks | Single-line plain text only |
| `--markdown` | `post` | **UNRELIABLE — also collapses to title-only** on some Feishu clients, even though API returns full content | **AVOID for multi-line messages** |
| `--content` + `--msg-type post` | `post` | **Full multi-line rendering** with title support | **THE ONLY RELIABLE METHOD for multi-line messages** |

### What happened

A GitHub Trending notification script sent multi-line plain-text content (project stats, categories, project lists, doc links).

1. `--text`: Collapsed to single-line title on both mobile and desktop — only the first line visible.
2. `--markdown`: Initially appeared to work, but on subsequent sends **also collapsed to title-only** on the user's Feishu client. The API response showed full content (`msg_type: post`, all lines present in JSON), but the Feishu client rendered only the first line as a title preview. This is a **client-side rendering issue** — the data is correct but the display collapses it. User explicitly rejected `--markdown` 5+ times.
3. `--content` + `--msg-type post` with each line as a **separate content element** renders correctly and reliably.

### Root cause

`--markdown` wraps everything as a single `{"tag":"md","text":"line1\nline2\nline3"}` element. The Feishu client may collapse this to a title preview. `--content` with `--msg-type post` lets you split each line into a separate `[{"tag":"text","text":"line"}]` element, which the client renders reliably.

### Recommendation (USER VERIFIED)

- **Default: `--content` + `--msg-type post`** for ANY multi-line message
- **`--text`** only for single-line plain text (log lines, status pings)
- **`--markdown`** — AVOID for multi-line; unreliable rendering in some Feishu clients. User explicitly demanded `--content + 完整 post JSON` and rejected `--markdown` 5+ times.

### Correct pattern: each line as separate content element

```python
def build_post_json(title, text):
    """Build Feishu post JSON — each line is a separate content element."""
    lines = text.strip().split("\n")
    content = []
    for line in lines:
        if not line.strip():
            continue
        if line.startswith("http"):
            content.append([{"tag": "a", "text": line, "href": line}])
        else:
            content.append([{"tag": "text", "text": line}])
    return {"zh_cn": {"title": title, "content": content}}

# Send:
post_json = build_post_json("报告标题", text)
lark_cli("im", "+messages-send", "--as", "bot", "--user-id", ou_xxx,
         "--msg-type", "post",
         "--content", json.dumps(post_json, ensure_ascii=False))
```

> **Key insight:** Putting `\n`-separated text into a single `"text"` element does NOT work reliably. Each line MUST be a separate `[{"tag":"text","text":"..."}]` array in the content matrix. URL lines use `{"tag":"a","text":"url","href":"url"}`. Title goes in `title` field only — do NOT repeat it as the first content line.

## Pitfall 7: `docs +create --parent-token` does NOT place docs in folders

**Verified 2026-07-05.** The Feishu document creation API (`docs_ai/v1/documents`) accepts a `parent_token` parameter, and `lark-cli docs +create --parent-token <folder_token>` passes it in the request body (confirmed via `--dry-run`). However, the created document is **NOT** placed inside the specified folder — it always lands in the user's root Drive.

This is a **Feishu API-level limitation**, not a lark-cli bug.

### Fix: Create-then-move pattern

```python
# Step 1: Create doc without --parent-token
result = run_lark_cli([
    "docs", "+create", "--as", "user",
    "--title", title, "--content", f"@{tmp_name}",
])
doc_id = result["data"]["document"]["document_id"]

# Step 2: Move doc into target folder
run_lark_cli([
    "drive", "+move", "--as", "user",
    "--file-token", doc_id, "--type", "docx",
    "--folder-token", folder_token,
])
```

The `drive +move` API is the **only reliable way** to relocate a document into a folder after creation.

## Verified Working Configuration

- lark-cli: v1.0.65, installed at `C:\nvm4w\nodejs\lark-cli.CMD`
- Identity: user-default (both bot and user ready)
- Missing scope: `im:message.send_as_user` (use bot fallback for IM sends)
- User open_id: resolvable via `lark-cli whoami --json` → `onBehalfOf.openId`
