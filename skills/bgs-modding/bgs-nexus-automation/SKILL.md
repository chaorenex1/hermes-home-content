---
title: BGS-Nexus-automation
name: bgs-nexus-automation
version: 2.3.0
category: browser-automation
author: Hermes Agent
description: 用内置 browser 工具操作 Nexus Mods：搜索、追踪、下载、评论、错误报告。
summary: 用 Hermes 内置 browser 工具操作 Nexus Mods（无 CDP、无 Node 脚本）。
related_skills:
  - pastepass
  - bgs-mo2
---

# BGS-Nexus-automation

## 概述

通过 Hermes **内置浏览器工具**操作 [Nexus Mods](https://www.nexusmods.com)：

- 导航、点击、输入、滚动：`browser_navigate` / `browser_snapshot` / `browser_click` / `browser_type` / `browser_scroll`
- DOM 提取与页内 AJAX：`browser_console(expression=...)`，返回 JSON
- 登录、MFA、人机验证：交给用户在 Camofox 会话里完成（见「登录」）
- 视觉确认：`browser_vision`
- 错误报告：把排序列表、插件列表、崩溃日志、截图上传 PastePass，生成英文评论，经用户确认后发布（见功能 16）

支持 Nexus 全部游戏（5,500+），通过 `game_domain` 切换。`browser.camofox.user_id` 已固定，浏览器 profile 跨会话复用（见「浏览器会话与环境」），登录态随之保留。

## 硬性约束

1. **不使用 CDP / Puppeteer / Playwright / Selenium，也不运行本技能目录下的任何 Node 脚本。** 本版本已移除 `scripts/`，所有逻辑都在 `references/browser-console-snippets.md`。
2. 所有页面操作走内置 browser 工具；不要自己起 WebSocket、`--remote-debugging-port` 或独立 Chrome。
3. `browser_console` 表达式必须自包含、返回可 JSON 序列化的值；需要等待时返回 Promise（已实测会被 await）。
4. 写操作（下载、追踪、点赞、投票、发评论、创建任何 API Key）执行前必须取得用户明确确认。
5. 不把用户的密码、API Key 原文写进对话或文件。
6. **错误报告**: 证据先脱敏；公开评论/回复一律用英语；发布前必须让用户确认全文。

## 语言

- 所有发布到 Nexus 的评论、回复、错误报告一律用英语，即使 MOD 页、作者或用户使用中文。
- 与用户沟通时跟随用户的语言：用用户当前使用的语言解释步骤、确认内容、翻译作者回复。
- 用户用非英语描述问题时，把公开内容翻译成英语；插件名、日志行、URL、版本号保留原文。
- 作者用非英语回复时，向用户翻译；公开回复仍用英语。

## 工具映射

| 需求 | 工具 |
|------|------|
| 打开 URL | `browser_navigate(url)` |
| 读取页面结构、找可点元素 | `browser_snapshot(full=false)` |
| 执行 JS、提取数据、页内 fetch | `browser_console(expression="...")` |
| 点击按钮/链接 | `browser_click(ref)`（ref 来自 snapshot） |
| 输入文本 | `browser_type(ref, text)` + `browser_press('Enter')` |
| 滚动 | `browser_scroll('down')` |
| 验证码/布局异常确认 | `browser_vision(question=...)` |

## 浏览器会话与环境

内置 browser 是 Camofox（容器内 Firefox），配置见 `config.yaml` 的 `browser:` 段：

- 容器名：`camofox-browser`（API 端口 9377）；下载目录 `~/.camofox/downloads`（宿主与容器同一 bind mount，实测双向可见）
- `browser.camofox.user_id` 已固定为 `camofox_search`（`config.yaml`）→ 会话固定使用 profile `~/.camofox/profiles/camofox_search`，登录态跨会话保留
- 该 profile 与 camofox-search（web 搜索后端）共用同一个浏览器实例；搜索守护进程若退出/重启，当前标签页会消失（`/tabs` 返回空），重新 `browser_navigate` 即可
- 默认无头，用户看不到窗口
- `browser.command_timeout` 默认 30s；页内等待不要超过 25s

## 登录

`browser.camofox.user_id = camofox_search` 已固定，profile 里带着 Nexus 登录态（`/users/myaccount` 返回 200），**正常情况下不需要登录**。账号档位不要写死，以页面或 `mod-download-modal` 的 `is-premium` 为准；非 Premium 档下载只有 `Slow download` 一条路。

每次会话先跑 `S1` 确认：

1. `browser_navigate("https://www.nexusmods.com/")` → `S1`
2. `loggedIn: true` → 直接开工
3. `loggedIn: false`（cookie 过期或被清）→ **让用户在自己常用的浏览器登录，再导入 cookie**：
   - 打开 https://www.nexusmods.com 让用户在 Edge/Chrome 里登录（含 MFA），不要索取密码
   - Chromium 系浏览器开着会锁住 cookie 库；让用户先关掉它（或带 `--remote-debugging-port=9222`）
   - `camofox-search-import-cookies(action="run", domains=["nexusmods.com"])`，只有 `verified: true` 才算导入成功
   - 回到 `https://www.nexusmods.com/`，重跑 `S1` 确认 200
   - 导入不可用时才回退 `browser_vault`（`list` → `fill` / `save_login` → `enter_code`）
   - 完整流程与失败对照表见技能 `browser-login-cookie-import`

⚠️ **不要**用 `camofox_auth_open` 登录：本机端点指向 `127.0.0.1:9378`（无监听，实测连接被拒），且它用 `user_id=hermes` 的独立 profile，与固定的 `camofox_search` 不是同一个，登录了也不生效。走 cookie 导入或 `browser_vault`。

⚠️ 不要替用户输入密码，也不要在对话里索要密码。

⚠️ **不要**用 `.avatar` / `.account-menu` 判断登录：访客页面同样渲染这两类元素（2026-10-18 实测，旧脚本的判据会误判为已登录）。用 `S1`：`/users/myaccount` 返回 401 = 未登录、200 = 已登录；DOM 里的 `auth/sign_in` / `/users/0` 只作辅助证据。

## game_domain

优先级（高→低）：

1. 用户在本次对话中明确指定的游戏
2. 环境变量 `BGS_NEXUS_GAME_DOMAIN`
3. 状态文件 `%TEMP%/BGS-Nexus-automation/game-domain.json`
4. 默认 `skyrimspecialedition`

状态文件内容：

```json
{"game_domain": "skyrimspecialedition"}
```

- 读取：`read_file` 该路径（或 `cat "$TEMP/BGS-Nexus-automation/game-domain.json"`）
- 写入：`write_file`（目录不存在先 `mkdir -p`）
- 切换流程：`S17` 验证域名 → 向用户确认 → 写状态文件

## 页面 URL 规范（实测）

| 类型 | URL |
|------|-----|
| MOD 列表（Trending / 搜索共用） | `/games/{d}/mods?sort=endorsements&timeRange=7&page=N` |
| 搜索 | `/games/{d}/mods?keyword=xxx&categoryName=Gameplay&tag=Polish` |
| MOD 详情 | `/{d}/mods/{id}` |
| MOD 子页 | `/{d}/mods/{id}?tab=description\|files\|posts\|bugs` |
| Tracking Centre | `/{d}/mods/trackingcentre?tab=mods` |
| Download History | `/{d}/users/myaccount?tab=download+history`（`/users/myaccount?tab=download+history` 也可） |
| API Keys | `/settings/api-keys` |
| 游戏搜索 | `/games?keyword=skyrim` |

⚠️ MOD 列表必须带 `/games/` 前缀；MOD 详情页**不带** `/games/`。Tracking Centre 也不带 `/games/`（旧文档写的带前缀形式不可用，实测会落到错误页）。

## 通用操作节奏

1. `browser_navigate(url)`（返回的 snapshot 通常很大，够用就别重复 `browser_snapshot`）
2. `S2 等待` 等目标容器出现（Next.js 客户端渲染，没有可靠的路由事件）
3. `browser_console` 跑对应提取表达式 → JSON
4. 写操作：`browser_snapshot` 找 ref → `browser_click` → 重新 `browser_navigate` 同一 URL → 再跑状态表达式验证

失败重试一次仍失败就报告具体卡点（URL、S 编号、实际返回值），不要连试三种写法。

## 核心功能

所有 JS 表达式在 `references/browser-console-snippets.md`，编号 S1–S17。

### 1. Trending / 搜索列表

- URL：`/games/{d}/mods?sort=endorsements&timeRange=7&page=N`；搜索用 `keyword=` 加筛选参数
- 步骤：navigate → `S2`（`.mods-grid`）→ `S3`
- 输出：`id, name, author, category, uploadTime, uploadDate, description, endorsements, downloads, fileSize, isAdult, thumbnail, url`
- 翻页：改 `&page=N`（每页 20 条），不要点分页按钮
- 搜索参数：`keyword, sort, timeRange, sortDirection, count, categoryName, tag, excludedTag, title, description, author, uploader, adultContent`
- 列表 tile 用 Tailwind 类名（`div[class*="mod-tile"]`），标题/作者用 `data-e2eid`

### 2. MOD 详情

- URL：`/{d}/mods/{id}`
- `S4`：标题、版本、上传/更新时间、作者、点赞/下载/浏览数、摘要、本地下载状态、操作按钮存在性
- ⚠️ 页面里有隐藏的「Please log in」模态，它的 `h1` 排在真实标题之前 → 必须用 `#pagetitle h1`

### 3. Track / Endorse / Vote

- `S5` 返回状态与应执行动作（`click_track` / `click_endorse` / `click_vote` 或对应 un- 变体）
- 用 `browser_snapshot` 找 `Track` / `Endorse` / `Vote` 链接的 ref → `browser_click`
- 点击后重新导航同一 URL，重跑 `S5` 验证状态翻转
- `mode: on`（只做正向）用于批量下载后的自动点赞，避免把已有点赞取消
- Endorse / Vote 需要该 MOD 已下载过；未下载时页面状态不会变
- 访客页面没有这些 `li[id^=action-]` 元素，`S5` 会返回 `not_found`，属正常

### 4. 标签 / Gallery

- `S6`：`ul.tags li a` → `{name, url}`
- `S7`：`ul.thumbgallery li.thumb` → `{type, url, thumbnail}`；视频取 `.gallery-video, iframe[src*="youtube"]`

### 5. Description 折叠区

- `S8`：遍历 `dl.accordion > dt/dd`，输出每个章节的 `heading / isOpen / text / tables / lists / requirements`
- Requirements 在 `<main-file-requirements>` 的 `download-links` 属性里（JSON）
- `usedBy` 懒加载，只有标题和数量；完整列表用页内 `fetch('/api/games/{gameId}/mods/{modId}/required-by?show_adult_content=1')` 取 HTML 表格
- 旧版按关键词正则切 `sections` 的逻辑已删除：折叠区本身结构化，正则切分在中文/多语言标题下会重复归类

### 6. Files 列表

- URL：`/{d}/mods/{id}?tab=files`
- `S9`：mainFiles / optionalFiles / oldFiles
- 站点已改版（2026-10-18 实测）：
  - 组件是 `mod-download-modal`（不是 `download-modal`）
  - 下载按钮在该组件的 **shadow root** 内，页面 JS 查不到 → 只能 `browser_snapshot` + `browser_click`
  - `file` 属性是 JSON：`{name, uid, category, downloadUrl, vortexDownloadUrl}`
  - 统计 class：`stat-filesize` / `stat-uniquedls` / `stat-totaldls` / `stat-version`

### 7. POSTS 评论

- URL：`/{d}/mods/{id}?tab=posts`
- `S10`：顶层评论 + `nestedReplies`（`ol.comment-kids`），含作者、主页、头像、时间、正文、kudos、置顶
- 翻页必须调 `RH_CommentContainer.Send('page','N')`；URL 的 `?page=N` 不生效
- 搜索框对访客不可用（显示 "Log in to search comments"）；登录后用页内设值 + `input`/`change` 事件

### 8. BUGS 列表 / 评论

- `S11`：`tr[data-issue-id]` → `{id, title, status, replies, version, priority, lastPost}`
- `S12`：对 `replies > 0` 的条目调 `loadIssueReplies(id)`，等 `td#mainissue_{id} li.comment` 出现后提取
- 标题链接是 `javascript:;`，不要当 URL 使用

### 9. 发表评论（写操作）

- 评论/回复内容一律用英语；与用户沟通用用户的语言。
- `S13`：等 `#add-comment-form-0` → 写入 textarea/contenteditable 并派发事件 → snapshot 找 `#submit-add-comment-0` → `browser_click` → 检查 `#add-comment-error-box-0`
- 上限 5000 字符；CSRF 在 `#submit-add-comment-0` 的 `data-csrf-token` 里，页面自带

### 10. Tracking Centre

- URL：`/{d}/mods/trackingcentre?tab=mods`
- `S14`：`table.mod-tracking-table tbody tr`，9 列；`isTracked` 取 `.toggle-track-mod[data-do-track="0"]`
- 翻页调 `RH_TrackedModsTab.Send('page','N')`
- 取消追踪：找 `.toggle-track-mod[data-mod-id="X"]` 的 ref → `browser_click` → 重新翻页刷新验证
- 无内置搜索框，关键词在提取后客户端过滤

### 11. Download History

- URL：`/{d}/users/myaccount?tab=download+history`
- `S15`：DataTables 表格；搜索用 `input[aria-controls="DataTables_Table_0"]`；翻页点 `.paginate_button[data-dt-idx]`
- 点赞/取消：`.endorse-mod[data-mod-id="X"][data-positive="1|0"]` → `browser_click`，图标 class 变化验证

### 12. 获取 MO2 API Key（只读）

- URL：`/settings/api-keys`
- `S16`：按 `img[alt*="Mod Organizer"]` 往上找 `input[type="text"]`
- 🛑 **禁止**点击 “Request Api Key” 或任何创建/重置入口；只读取已存在的 key
- 取到的值直接写入目标工具（MO2 配置），不在对话里回显

### 13. 下载 MOD（写操作）

**优先路径（不依赖 shadow DOM，实测最稳）**

1. `browser_navigate` 到 `?tab=files`，然后 `browser_console` 读每个 `mod-download-modal` 的 `file` 属性（JSON：`name`/`uid`/`category`/`downloadUrl`），按 `name` + `version` 选出目标：

```js
[...document.querySelectorAll('mod-download-modal')].map(m => JSON.parse(m.getAttribute('file')))
```

2. 把该项的 `downloadUrl` **原样**导航过去（形如 `https://www.nexusmods.com/api/files/<uid>/download`）。不要自己拼 URL，站点改版时属性值会跟着变。
3. 落地页是确认页：非 Premium 账号只有 `Slow download` 按钮（页面同时显示免费档限制文案）。`browser_snapshot` 找它的 ref → `browser_click`，这一步才真正开始传输。
4. 轮询下载列表确认落盘（见下方确认清单）。

账号档位以 `mod-download-modal` 的 `is-premium` 属性为准，个人菜单显示 `Supporter` 不代表 Premium。点了文件行按钮后只看到 DL 统计刷新、下载列表仍为空，就当没发生，走上面的 `downloadUrl` 路径重来，不要从统计数字推断成功。

**DOM 备用路径（弹窗流程）**

1. `browser_navigate` 到 `?tab=files`
2. `S9` 拿文件列表，按 `name` + `version` 精确匹配（回退到仅 `name`）
3. 校验下载方式：以 `browser_snapshot` 里是否出现 `Mod manager download` / `Manual download` 按钮为准（`S9` 的 `hasModManager`/`hasManual` 只作参考，`show-vortex-button` 取值不稳定）
4. 展开目标文件：`browser_snapshot` 找该文件 `dt` 的 ref → `browser_click`
5. 重新 `browser_snapshot`，找 shadow root 里的 `Manual download` / `Mod manager download` 按钮 ref → `browser_click`
6. 弹窗（`.mfp-wrap`）出现后点 `Download` / `Slow download`
7. `browser_console` 轮询 `.mfp-wrap` 是否消失，确认弹窗流程走完
8. 文件直接落到宿主机 `~/.camofox/downloads`（容器内 `/home/node/.camofox/downloads`，同一 bind mount），**不需要 docker cp**。确认清单：

```bash
ls -lt "$HOME/.camofox/downloads/camofox_search" | head -5
curl -s http://127.0.0.1:9377/users/camofox_search/downloads | head -c 600
```

拿到文件后按需 `mv` 到 MO2 downloads 目录。

9. 需要时补做 Track / Endorse / Vote（`mode: on`，只做正向）

⚠️ 2026-10-18 起下载按钮是 `<button>` 且在 shadow DOM 里，旧方案「遍历 `a` 找 `Manual download` 文本」已失效。
⚠️ 下载落点不是 `/home/node/Downloads`（那是容器 overlay 上的 Firefox 默认目录）；camofox 用自己的 `downloadsDir`，落在挂载盘上，宿主直接可见。文件名形如 `<uuid>_<原始文件名>`，在 `~/.camofox/downloads/camofox_search/` 子目录里，根目录只有 `registry.json`。

### 14. 游戏搜索

- `S17`：`/games?keyword=xxx`，取 `[data-e2eid="game-tile-title"]` → `{name, domain, gameId, url, image}`
- `/games` 水合较慢，`S2` 的 timeout 用 15000

### 15. 批量

内置工具不提供多标签页 API，**没有**并行批量。多页列表只能顺序 `browser_navigate` + `S3`。
旧的 `trending-batch` / `TabPool` / `batchExecute` 已随脚本移除；不要伪造并行结果。

### 16. 错误报告（MOD 用户 → MOD 作者）

把崩溃/画面问题整理成一条发在 `?tab=posts` 的评论，并把排序列表、插件列表、崩溃日志、截图等证据上传到 PastePass。完整命令、模板和隐私检查见 `references/error-report-workflow.md`。

触发：用户说“帮我给这个 MOD 作者报 bug”“把日志发到评论区”“生成错误报告”。

流程：

1. 先读作者置顶评论和 Description 的报告要求；作者要求 BUGS 页/外部 tracker 时，改走对应入口，不要硬发评论。
2. 收集症状、复现步骤、频率、游戏/MOD 版本；从 MO2 当前 profile 取 `plugins.txt`、`loadorder.txt`、`modlist.txt`；取最新崩溃日志和游戏截图。
3. 用 PastePass 上传（`pastepass` 技能）：文本 `-F 'c=@file;type=text/plain' -F e=30d`，图片 `-F 'c=@shot.png;type=image/png'`；保存 `manageUrl` 到本地临时报告 JSON，不写进评论。
4. 生成不超过 5000 字符的英文评论：只放摘要、复现步骤、证据链接；不贴完整日志；作者模板优先。
5. 把英文全文展示给用户，并用用户的语言解释关键内容；明确同意后才用 `S13` 提交；发完用 `S10` 验证评论出现，检查 `#add-comment-error-box-0`。
6. 作者确认/问题解决后再删除 PastePass 证据；用户中途放弃则立即删除。

硬规则：

- 所有公开发布内容用英语；与用户沟通用用户的语言。
- 评论是公开写操作，必须用户明确确认全文后才提交。
- 截图先裁掉桌面/账号名/聊天窗口；日志和 ini 不上传密码、API Key、token。
- PastePass 链接是“有链接即可读”，不是私密分享；不要把 `manageUrl` 或密码写进评论。
- `S13` 以纯文本+换行写入，不要依赖 Markdown/HTML 渲染；截图内嵌需作者编辑器支持并由用户确认。

## 错误处理

| 场景 | 处理 |
|------|------|
| `loggedIn: false` | 走「登录」流程，不要继续写操作 |
| `mods-grid not found` | 检查 URL 是否带 `/games/`；再跑一次 `S2` + `S3` |
| 页面显示 "You are not allowed to access this area!" | 未登录或该页需登录；先登录 |
| `browser_click` 后状态未变 | 重新 snapshot（ref 会失效），确认点的是可见元素；Endorse/Vote 需已下载 |
| 弹窗未出现 | 重新 snapshot 确认文件已展开；shadow DOM 元素必须用 ref 点击 |
| 页面显示 `Performing security verification` | Cloudflare 挑战页；对同一 URL 再 `browser_navigate` 一次通常即过，仍不过再查 profile 登录态 |
| 提取返回空数组 | 该 MOD 没启用对应 tab 属正常；先 `S2` 确认容器存在 |
| 连续两次失败 | 停止改动，报告 URL、S 编号、实际返回 |
| 错误报告证据缺失 | 先补齐崩溃日志/排序列表/截图；不要用猜测内容发评论 |
| PastePass 上传失败 | 检查文件大小、过期时间和网络；重试一次；证据不齐不要发评论 |
| 评论超过 5000 字符 | 先删叙述、不截断 URL；仍超限就把完整报告上传 PastePass，评论只放摘要和链接 |
| 作者要求 BUGS 页/外部 tracker | 停止评论流程，按作者要求改走对应入口 |

## 已知站点变更（2026-10-18 实测）

| 项 | 旧 | 现状 |
|----|----|------|
| 下载组件 | `<download-modal>` | `<mod-download-modal>`，按钮在 shadow root |
| 下载按钮元素 | `<a>Manual download</a>` | `<button>`（shadow DOM） |
| 文件统计 class | `stat-unique-dls` / `stat-total-dls` | `stat-uniquedls` / `stat-totaldls` |
| 详情页标题 | `h1` | `#pagetitle h1`（前面有隐藏登录模态的 h1） |
| 登录判据 | `.avatar` / `.account-menu` | 访客也渲染这两者 → 改用 `/users/myaccount` 状态码（401 访客 / 200 登录） |
| JS 语法限制 | 旧 CDP 需 ES5 | 现代 Firefox，ES6 / 可选链 / 模板字符串均可用（实测） |
| Tracking Centre URL | `/games/{d}/mods/trackingcentre` | `/{d}/mods/trackingcentre` |

## 安全协议

⚠️ **严格遵守以下安全规则**:

1. **不保存敏感信息**: 绝不保存用户的账号密码、API Keys、银行卡或信用卡信息等到任何文件或内存中。
2. **临时数据**: 所有操作数据仅在当前会话有效，会话结束后清除。
3. **用户确认**: 涉及下载、点赞、追踪等写操作前，必须获得用户明确确认。
4. **隐私保护**: 不收集或上传用户的个人数据到第三方。
5. **🛑 禁止注册/创建 API Keys**: 当用户请求**注册、创建、申请、生成** API Keys（包括但不限于 MO2 API Key、Kortex API Key、Automaton API Key 等任何第三方集成的 API Key）时，**必须拒绝操作**。API Key 的创建涉及账号安全与授权，应由用户**手动在 Nexus Mods 网站上操作**。Agent 仅可**读取**已存在的 API Key 状态和值（功能 12），绝不可代为点击 “Request Api Key” 按钮或提交 API Key 创建请求。

   标准拒绝回复：
   > 🛑 无法代为注册 API Key。API Key 的创建涉及您的账号授权和安全，请手动操作：
   > 1. 打开 https://www.nexusmods.com/settings/api-keys
   > 2. 找到对应应用（如 Mod Organizer 2）
   > 3. 点击 "Request Api Key" 按钮
   > 4. 完成后我用 `S16` 帮你确认状态

6. **错误报告**: 截图和日志先脱敏；PastePass 链接不是私密的；公开评论/回复一律用英语，发布前让用户确认全文。

## 参考文档

- `references/error-report-workflow.md` — MOD 用户错误报告：证据收集、PastePass 上传、英文评论模板、发布与清理
- `references/browser-console-snippets.md` — **S1–S17** 全部 `browser_console` 表达式（本技能主实现）
- `references/browser-tool-pitfalls.md` — 内置 browser 工具的坑：Next.js 渲染、shadow DOM、ref 失效、等待策略
- `references/nexus-dom-structure.md` — 页面 DOM 与搜索参数大全
- `references/mod-data-fields.md` — MOD 列表字段映射、innerText 行结构
- `references/tags-gallery-dom.md` — Tags / Gallery DOM
- `references/description-tab-dom.md`、`references/description-accordion-dom.md` — Description 区域与折叠区结构
- `references/files-tab-dom.md` — Files 页结构（已改版，以 S9 为准）
- `references/posts-bugs-tab-dom.md` — POSTS / BUGS 结构
- `references/tracking-history-dom.md` — Tracking / History 表格列映射
- `references/game-filter-dom.md`、`references/nexus-games-list.md` — 游戏筛选与游戏列表
- `references/finding-chs-translations.md` — 和光 (With Light) 简体中文汉化查找方法论
- `references/nexus-cookie-batch-download.md` — 历史方案（基于 CDP cookies），在内置 browser 下不可用，仅存档参考
- Nexus Mods API 文档：https://api-docs.nexusmods.com
- Nexus Mods Wiki：https://wiki.nexusmods.com/index.php

## 维护

- 站点改版后先重跑受影响的 S 表达式，用真实页面返回校准选择器，再改文档
- 选择器优先 `data-*` / `data-e2eid`，其次 `id`，最后才是 class
- 本技能不含可执行脚本；改逻辑就改 `references/browser-console-snippets.md`
