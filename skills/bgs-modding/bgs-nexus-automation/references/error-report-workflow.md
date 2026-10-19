# 错误报告工作流（MOD 用户 → MOD 作者）

## 适用范围

当用户要因为崩溃、卡死、掉帧、画面异常、安装失败等问题，向某个 Nexus MOD 作者提交报告时使用。报告默认发在 MOD 的 `?tab=posts` 评论区；排序列表、插件列表、崩溃日志、游戏截图等证据先上传 PastePass，再把链接写进评论。

本流程只负责“整理证据 + 生成评论 + 经用户确认后发布”。不负责替作者诊断，也不保证作者会回复。

## 语言

- Nexus 上发布的报告、评论、回复一律使用英语，即使 MOD 页是中文、用户用中文描述、作者用中文回复。
- Agent 与用户沟通时跟随用户的语言：用用户的语言解释步骤、确认内容、翻译作者回复。
- 用户用非英语描述症状时，把报告正文翻译成英语；插件名、日志行、URL、版本号保留原文。
- 作者用非英语回复时，向用户翻译；用户要公开发布的回复仍用英语。
- 如果用户坚持用中文发公开内容，停止自动发布，说明本流程只发布英语评论。

## 前置检查

1. 确认目标 MOD：`game_domain`、MOD ID、MOD 名称、MOD 版本、游戏版本。
2. 跑 `S1` 确认 Nexus 登录状态；未登录则先走 `SKILL.md` 的登录流程，不要继续写操作。
3. 打开 `/{d}/mods/{id}?tab=posts`，跑 `S10` 读置顶评论和最近评论，确认作者是否指定了报告格式、BUGS 页或外部 tracker。
4. 打开 Description 的 `S8`，看作者是否写了“如何报告问题”。作者规则优先于本模板。

如果作者明确要求用 BUGS 页、Discord、GitHub Issues 或其他 tracker，停止评论流程，按作者要求走对应入口；不要在评论区硬发。

## 1. 收集证据

### 1.1 症状与复现

先向用户确认以下内容，缺失的不要猜：

- 实际发生了什么，期望是什么；
- 在哪个地点、菜单、任务、战斗或读档后发生；
- 复现步骤，按 1/2/3 写；
- 频率：必现、偶发（几次中几次）、只发生一次；
- 最近改动：新装/更新/卸载了哪些 MOD，是否改过排序；
- 是否在干净存档/新存档复现；
- 游戏版本、MOD 版本、SKSE/加载器版本。

### 1.2 排序列表与插件列表

优先用 `bgs-mo2` 技能的 MO2 MCP：

- `mo2_session` / `mo2_machine_contract` 确认当前实例和 profile；
- `mo2_pluginlist` 取插件列表；
- `mo2_modlist` 取 MOD 列表；
- `mo2_profile_ini_get` / `get_state` 取 `profilePath`。

需要上传的文件在 `profilePath` 下：

| 文件 | 内容 | 报告里的标签 |
|---|---|---|
| `plugins.txt` | 已启用插件（`*` 开头） | Plugin list |
| `loadorder.txt` | 完整插件顺序 | Load order |
| `modlist.txt` | MOD 列表与启用状态（`+`/`-`） | Mod list |

如果 MO2 MCP 未绑定，用 `bgs-mo2` 的触发文件 `get_state` / `get_load_order`；再不行就让用户在 MO2 里右键 profile → Open folder，手动选择这三个文件。不要猜路径。

上传前用文本编辑器确认文件能正常显示；如果看到乱码，先另存为 UTF-8，不要上传二进制乱码。

### 1.3 崩溃日志

不要硬编码日志路径。先按当前游戏查 BGS KB：

```text
bgs_kb_query({
  query: "<game> crash logger log file location",
  domains: ["debugging"],
  games: ["<game>"]
})
```

- KB 有记录：按记录找最新一份与崩溃时间匹配的日志。
- KB 没有记录：让用户从已安装的崩溃记录器/日志目录里选最新文件，或直接提供路径。
- 多份日志时优先上传与本次崩溃时间最接近的一份；不要把所有历史日志一次性堆给作者。

上传完整日志，不要只发截图。日志里可能包含 Windows 用户名路径；在评论里说明“日志含本地路径”，让用户决定是否先脱敏。不要静默改写日志内容。

### 1.4 游戏截图

- 优先使用用户已有的游戏截图文件。
- 需要现场截图时，用 `computer_use` 只截游戏窗口，或让用户按游戏截图键；不要截整个桌面。
- 截图里不能出现桌面、账号名、聊天窗口、浏览器标签、存档名等个人信息；必要时先裁剪。
- 视觉 bug 用 1–2 张图说明即可；不要用滤镜或编辑过的图冒充原始画面。

### 1.5 可选证据

按作者要求或问题类型补充：

- Papyrus / SKSE / 加载器日志；
- `systeminfo` 或 CPU/GPU/VRAM/RAM/Windows 版本；
- `ModOrganizer.ini`（先删掉个人信息和路径）；
- ENB/ReShade 配置；
- 最小复现用的 MO2 profile 导出。

不要上传密码、API Key、token、浏览器 cookie、包含个人信息的存档。

## 2. 脱敏

PastePass 链接是“有链接即可读”，不是私密分享。上传前检查：

- 截图裁掉桌面、用户名、聊天窗口；
- 日志/ini 里的账号名、邮箱、API Key、token、绝对路径是否需要处理；
- 不上传 `.env`、cookie、密码库、付费 MOD 文件；
- 评论里不写 `manageUrl`、密码、API Key。

是否保留日志里的真实路径由用户决定；作者有时需要精确路径定位问题。不要替用户做不可逆的删改。

## 3. 上传 PastePass

基础地址：`https://pastepass.chaorenex1.com`。完整 API 见 `pastepass` 技能。

```shell
BASE=https://pastepass.chaorenex1.com

# 文本证据：plugins.txt / loadorder.txt / modlist.txt / crash.log
curl -fsS -F 'c=@plugins.txt;type=text/plain' -F e=30d "$BASE" -o plugins.json
curl -fsS -F 'c=@loadorder.txt;type=text/plain' -F e=30d "$BASE" -o loadorder.json
curl -fsS -F 'c=@crash.log;type=text/plain' -F e=30d "$BASE" -o crash.json

# 截图
curl -fsS -F 'c=@screenshot.png;type=image/png' -F e=30d "$BASE" -o screenshot.json
```

- 过期时间默认用 `e=30d`；作者可能很久才回复时用 `e=90d`（上限 90d）。
- 单次请求上限 100MB；更大的包用 Web UI 或仓库里的 `pb` CLI。
- 解析 JSON，只把 `url` 写进评论；`manageUrl` 保存到本地临时报告文件，绝不写进评论。

```shell
node -e "const j=require('./plugins.json'); console.log(j.url)"
```

本地报告清单写到：

```text
%TEMP%/BGS-Nexus-automation/reports/<timestamp>.json
```

结构示例：

```json
{
  "game": "skyrimspecialedition",
  "mod": {"id": "266", "name": "SkyUI", "version": "5.2SE"},
  "createdAt": "2026-10-19T00:00:00Z",
  "artifacts": {
    "plugins": {"url": "https://pastepass.chaorenex1.com/xxxx", "manageUrl": "https://pastepass.chaorenex1.com/xxxx:...", "bytes": 1234},
    "loadorder": {"url": "https://pastepass.chaorenex1.com/yyyy", "manageUrl": "https://pastepass.chaorenex1.com/yyyy:...", "bytes": 2345},
    "crash": {"url": "https://pastepass.chaorenex1.com/zzzz", "manageUrl": "https://pastepass.chaorenex1.com/zzzz:...", "bytes": 3456},
    "screenshot": {"url": "https://pastepass.chaorenex1.com/aaaa", "manageUrl": "https://pastepass.chaorenex1.com/aaaa:...", "bytes": 4567}
  }
}
```

`manageUrl` 是删除/更新凭证，只存本地临时文件；作者确认或问题解决后用它删除证据。

## 4. 生成评论

硬限制：Nexus 评论 5000 字符。报告正文用英语，只放摘要、复现步骤和链接，不要贴完整排序列表或整份日志。用户可以用中文描述，由 Agent 翻译成英语。

### 英文模板（唯一模板）

```text
[Bug report] <one-line symptom> | Game <version> | <mod name> <version>

What happens:
<1-3 lines: actual vs expected>

Steps to reproduce:
1. ...
2. ...
3. ...

Frequency: always / intermittent (x of y) / once
Recent changes: <new mods, updates, load-order changes>

Evidence:
- Load order: <pastepass url>
- Plugin list: <pastepass url>
- Crash log: <pastepass url>
- Screenshot: <pastepass url>

System: Windows <version>, CPU <model>, GPU <model> <VRAM>, RAM <GB>
```

规则：

- 所有公开发布内容一律用英语：报告正文、补充评论、对作者回复的回复。
- 用户用非英语描述时，Agent 翻译成英语报告；插件名、日志行、URL、版本号保留原文。
- 作者置顶/Description 有模板时，用作者的模板，不要另起格式。
- 不写“求修复”“救命”等空话；写清楚复现和证据。
- 不把 `manageUrl`、密码、API Key、邮箱写进评论。
- 截图链接不要伪装成 Markdown 图片；S13 以纯文本写入，Nexus 可能不渲染 Markdown/HTML。需要内嵌图片时，由用户在编辑器里手动插入并确认。

## 5. 确认并发布

1. 把最终英文评论全文原样展示给用户，并用用户的语言解释关键内容；明确问“是否发布这条公开评论”。
2. 只有用户明确同意后才继续；用户改字就改完再确认。
3. 导航到 `/{d}/mods/{id}?tab=posts`，跑 `S2` 等 `#add-comment-form-0`。
4. 用 `S13` 填内容。`content` 必须是合法 JS 字符串：由 agent 用 JSON 序列化生成，避免引号/换行破坏表达式。
5. `browser_snapshot` 找 `#submit-add-comment-0`，点击。
6. 3 秒后检查 `#add-comment-error-box-0`；再 `browser_navigate` 同一 URL，跑 `S10` 确认评论出现。
7. 如果发布成功但验证失败，先重新加载再判断，不要立刻重复提交，避免双发。

## 6. 清理

- 作者确认收到、问题解决或用户要求删除后，用本地报告 JSON 里的 `manageUrl` 对每个证据发 `DELETE`。
- 删除后确认 404，再删本地报告 JSON。
- 用户中途放弃发布：立即删除已上传证据，不要留在 PastePass。
- 作者要求保留证据时，保留到作者明确说可以删。

## 失败处理

| 情况 | 处理 |
|---|---|
| MO2 MCP 不可用 | 用 `bgs-mo2` 触发文件 `get_state`/`get_load_order`；再不行让用户手动选 profile 文件 |
| 找不到崩溃日志 | 先查 `bgs_kb_query`；仍找不到就让用户选最新日志，不要编造路径 |
| PastePass 上传失败 | 检查文件大小、过期时间和网络；重试一次；证据不齐不要发评论 |
| 评论超过 5000 字符 | 先删叙述，不截断 URL；仍超限就把完整报告上传 PastePass，评论只放摘要和链接 |
| 作者要求 BUGS 页/外部 tracker | 停止评论流程，按作者要求改走对应入口 |
| 登录失效 | 停止发布，先走登录流程 |
| 评论提交报错 | 显示 `#add-comment-error-message-0` 原文；不要盲目重试 |
| 发布后 S10 找不到评论 | 重新加载页面再查；确认没有双发后再决定是否重试 |

## 安全底线

- 所有公开发布内容用英语；与用户沟通用用户的语言。
- 公开评论是写操作，必须用户明确确认全文后才提交。
- PastePass 链接有 URL 即可读，不是私密分享。
- 截图先脱敏；日志中的个人信息由用户决定是否处理。
- 不上传密码、API Key、token、cookie、付费 MOD 文件。
- 不伪造日志、截图、系统信息或复现步骤；缺证据就写缺证据。
