---
name: browser-login-cookie-import
description: Use when a site needs login - import browser cookies.
version: 1.0.1
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [browser, cookies, login, camofox, abe]
    related_skills: [browser-automation-cdp, bgs-nexus-automation]
---

# 登录墙：借用户浏览器 cookie

## When to Use（何时使用）

任何站点要求登录，而 camofox 里的会话是未登录状态时。不要代用户输密码，也不要停在「请你自己登录一下」；按下面五步走完。

典型触发：页面出现 Sign in / 需要登录才能看内容、接口返回 401/403、操作按钮点了只弹登录框。

## 核心思路

用户在**自己常用的浏览器**（Edge/Chrome/Firefox）里完成登录（含 MFA、验证码），再用 `camofox-search-import-cookies` 把这些 cookie 导进 camofox 的同一个 profile，agent 的 `browser_*` 工具随即带上登录态。

- 导入目标默认 `user_id=camofox_search`，与本机 `browser.camofox.user_id` 一致 → 导入即生效，无需重启
- 工具只返回数量与跳过原因，**永不打印 cookie 值**
- 生产路径不需要用户把密码交给 agent

## 五步流程

1. **确认未登录**，用站点的判别式（不要用「有头像」这种弱信号），例如：
   - Nexus：`fetch('/users/myaccount')` → 401 未登录 / 200 已登录
   - GitHub：`/settings/profile` 或 `meta[name="user-login"]`
   - 通用：`fetch('/api/me', {credentials:'include'})` 的 status
2. **让用户在自己浏览器里登录该站**（给他 URL 和目标站点名）。这一步之后不要追问密码。
3. **导入**（只导需要的域，避免把全站 cookie 都搬进来）：

```text
camofox-search-import-cookies(action="run", domains=["example.com"])
```

   - 先 `action="detect"` 看有哪些 profile、CDP 是否可用（profile 目录 + 最近修改时间）
   - Chromium 系浏览器**开着时会独占锁住 Cookies 文件**（WinError 32）。两条路：请用户关掉该浏览器；或让浏览器带 `--remote-debugging-port=9222` 启动（此时走 CDP 导出，不用关）
   - `dry_run=true` 只看导出统计（rows / exported / expired / filtered / undecryptable），不写入
4. **读结果**：`verified: true` 且 `present_after >= accepted` 才算导入成功。`exported: 0` 且 `undecryptable == rows` 是 ABE（见下），不是工具坏了。
5. **回到 camofox 验证**：重新打开目标页，跑第 1 步的判别式，必须拿到已登录结果；再做一次真实只读操作（例如读取账户页）。不要用「导入成功」代替站点验证。

## 判别式选择

优先页面自带、随登录态变化的稳定信号，按可靠性排序：

1. 只有登录后才有权限的**接口状态码**（最可靠，Nexus 的 `/users/myaccount` 401/200）
2. `<meta name="user-login">` 之类身份元数据（GitHub）
3. 账户菜单里的退出链接、用户名文本
4. 头像图片：最弱，很多站点访客也渲染占位头像

JS 重的站点先等 `document.readyState === 'complete'`（轮询 ≤15s）再加 ~1.5s，再取判别式；navigate 后立刻取值会拿到空 DOM。

## 实测基准（2026-10-19，Edge 155）

关闭 Edge 后 `run(domains=["nexusmods.com"], browser="edge")`：

```text
rows 1286 · exported 10 · expired 0 · filtered 1257 · undecryptable 19 · key_error 0
sent 10 · accepted 10 · present_after 1238 · verified true
→ camofox 回查：/users/myaccount 200，页面 “Welcome back”
```

`undecryptable: 19`（全库）不影响目标域导入；`filtered` 大是域过滤生效。

## 失败对照表

| 现象 | 原因 | 处理 |
|---|---|---|
| `profile is locked ... WinError 32` | 浏览器在运行，独占 Cookies | 请用户关闭该浏览器；或改用 CDP 9222 导出 |
| `exported: 0`，`undecryptable == rows` | 现代 Edge/Chrome 的 v20 App-Bound 加密 | 关掉浏览器后重跑（工具会走 rookie-cookies）；仍失败则换 Firefox 源 |
| `filtered` 很大、`exported` 很小 | 域过滤或 cookie 已过期 | 检查 `domains` 拼写（后缀匹配）；让用户重新登录一次 |
| 导入成功但站点仍显示未登录 | 该域没有 auth cookie（源浏览器本来就没登录），或被 DBSC 绑定会话拒收 | 让用户确认在自己的浏览器里**确实**处于登录状态；DBSC 站点（高安全）无解，改用浏览器内登录 |
| CDP 9222 不可达 | 浏览器没带调试端口 | 不要为了这个去改日常 profile（见硬规则），让用户关浏览器即可 |

## 硬规则

1. **cookie 值永不打印**，只报数量、域、前缀、跳过原因。
2. **绝不调试启动日常 profile**：任何非默认 `--user-data-dir`（含 junction 指向同一目录）会禁用 App-Bound Encryption，浏览器会静默清空该 profile 的全部 v20 cookie。要自动化就用独立 profile 重新登录，或就走本流程。
3. 动手前若要在真实 profile 上做实验，先把 `Network/Cookies` 连同 `-wal`/`-shm` 备份到 scratch。
4. 不要把用户密码、2FA 码写进对话或文件；不代用户在登录页输入密码。
5. 只导入需要的域；全量导入会把无关站点的会话也带进 camofox。

## 直接喂 CLI（不走 camofox）

目标是个命令行工具而不是浏览器时，别装扩展：Hermes venv 自带 `rookie_cookies`，Edge 关闭后
`rookie_cookies.read(browser="edge", profile="Default", include_expired=True, app_bound="injection_only")`
能把 v20（App-Bound）解出来，无需管理员。`snapshot.as_list()` 每行有 name/domain/value，只打印长度，不打印值。

实测坑（BaiduPCS-Go）：只拼 `BDUSS` + `.passport.baidu.com` 的 `STOKEN` 时 `who`/`quota` 正常，
但 `ls /` 返回 `-6 请重新登录`；换成 `.pan.baidu.com` 的 `STOKEN` 立刻可用。同名的多域 cookie 要按域的用途挑。

用完把 cookie DB 副本删掉；Windows 上被 sqlite 句柄占住时，进程退出后才会释放。

## 定时同步

automation 里有一个每 3 天跑的 cookie 同步任务；用户在本地浏览器新登录了站点后，手动跑一次 `action="run"` 即可，不必等定时任务。

## 参考

- `references/abe-edge-chromium.md`：Edge/Chrome v20 加密、rookie-cookies 导出细节、验证过的统计口径
