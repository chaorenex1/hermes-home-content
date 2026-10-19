# lark-cli on Hermes: Session Transcript & Quirks

Recorded from a real install on Windows 10 (MSYS/bash shell, Hermes desktop GUI).

## Environment

- Host: Windows 10, the operator
- Shell: git-bash / MSYS (NOT PowerShell)
- Node v24.9.0, npm 11.6.0, Go 1.25.5, Python 3.11.15
- Hermes profile: default

## Install commands (actual output)

### npm install

```
$ npm install -g @larksuite/cli
added 7 packages in 5s
```

### npx skills add

```
$ npx -y skills add https://open.feishu.cn --skill -y
# Installs ~20+ lark-* skills (lark-slides, lark-task, lark-vc, lark-wiki,
# lark-workflow-meeting-summary, lark-workflow-standup-report, etc.)
# Symlinked into: Claude Code, OpenClaw, Hermes Agent, Qoder, Qwen Code
# Universal: Codex, Cursor, Gemini CLI, GitHub Copilot, Kimi Code CLI +12 more
│  Done!  Review skills before use; they run with full agent permissions.
```

## config init --new — REFUSED in Hermes

```
$ lark-cli config init --new
{
  "ok": false,
  "error": {
    "type": "config",
    "subtype": "not_configured",
    "message": "config init is refused inside hermes context (would create a parallel app and shadow the existing hermes binding)",
    "hint": "see `lark-cli config bind --help` to bind lark-cli to the Agent's existing app instead. Pass --force-init only if the user explicitly wants a separate app in this workspace."
  }
}
```

**Fix:** `lark-cli config bind --source hermes --identity <preset>`

## config bind — success output

```
$ lark-cli config bind --source hermes --identity user-default
⚠️ 你正在从应用身份切换到用户身份 —— 切换后 AI 将以你的名义在飞书中执行所有操作...
配置成功！lark-cli 已可在 Hermes 中使用。
{
  "app_id": "cli_aac35ea82bf89bdb",
  "config_path": "<USER_HOME>\\.lark-cli\\hermes\\config.json",
  "identity": "user-default",
  "ok": true,
  "replaced": false,
  "workspace": "hermes"
}
```

## auth login — device-code flow

### Background launch

```
$ lark-cli auth login --recommend   # background, blocks up to 10 min
在浏览器中打开以下链接进行认证:
  https://accounts.feishu.cn/oauth/v1/device/verify?flow_id=...&user_code=XXXX-XXXX

[AI agent] 此命令最长阻塞约 10 分钟...
等待用户授权...
```

### QR code generation

```
# CORRECT — URL as positional arg:
$ lark-cli auth qrcode "https://accounts.feishu.cn/oauth/v1/device/verify?..." --output auth-qrcode.png
{"file_path":"<USER_HOME>\\auth-qrcode.png","ok":true}

# WRONG — piping via stdin:
$ lark-cli auth qrcode --output ... <<< "https://..."
{"ok":false,"error":{"message":"accepts 1 arg(s), received 0"}}
```

## web_extract failure on feishu.cn

```
web_extract("https://open.feishu.cn/document/...")
→ error: "Tavily extract failed: _ssl.c:999: The handshake operation timed out"

browser_navigate(same URL)
→ (empty page), element_count: 0

curl -fsSL "<url>"   # WORKS — returns clean markdown
```

## Key takeaways

1. **Always use `config bind`, never `config init --new`** in agent environments
2. **Always confirm identity policy with user** before bind (bot-only vs user-default)
3. **Auth login must be backgrounded** — foreground with short timeout fails
4. **QR code URL is a positional arg** — not stdin, not a flag
5. **Auth URL is opaque** — never modify it (no URL encoding/decoding)
6. **curl > web_extract** for feishu.cn content — SSL issues with Tavily/browser
