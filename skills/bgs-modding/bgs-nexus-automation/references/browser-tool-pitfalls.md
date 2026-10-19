# 内置 browser 工具的坑（Nexus Mods）

本文件取代旧的 `cdp-pitfalls.md`。旧文档里的 WebSocket 层级、`Runtime.evaluate` 参数、ES5 限制都随 CDP 实现一起作废；下面只保留在内置 browser 工具下仍然成立、或新出现的问题。

实测环境：Camofox 容器内 Firefox 152，`browser.headed=false`，页面为 Next.js 客户端渲染。

---

## 1. Next.js 渲染：navigate 返回 ≠ DOM 就绪

`browser_navigate` 返回的 snapshot 可能已经包含内容，也可能只有骨架屏。不要假设已渲染。

- 等待用页内 Promise 轮询（`browser-console-snippets.md` 的 S2），不要用固定 sleep 猜时间
- MOD 列表 hydration 通常 1–3s；`/games` 游戏搜索页更慢（用 15s 超时）
- 没有可靠的 `load` / `domContentLoaded` 信号可用：`browser_navigate` 本身不暴露事件

## 2. Tailwind 类名不能当选择器

`.mod-tile` 不存在；实际类名是 `group/mod-tile relative` 这类含 `/` 和空格的字符串。

```js
document.querySelectorAll('.mod-tile')          // ❌ 0 个
document.querySelectorAll('[class*="mod-tile"]') // ✅
document.querySelector('.mods-grid').children    // ✅ 容器 + 子元素遍历
```

优先用 `data-e2eid`（`mod-tile-title` / `user-link` / `game-tile-title`），它们比 class 稳定。

## 3. shadow DOM：JS 查不到，snapshot 能

`mod-download-modal` 的下载按钮渲染在 shadow root 里。页内 `querySelector('button')` 找不到，`document.querySelectorAll('#mod_files button')` 返回 0。

- 必须 `browser_snapshot` 拿到 ref，再 `browser_click(ref)`
- 不要试图用 `el.click()` 或 `dispatchEvent` 绕过：跨 shadow 边界拿不到元素
- 同理，`Mod manager download` / `Manual download` 现在是 `<button>`，不是 `<a>`；按标签名筛选的旧逻辑会漏

## 4. snapshot 里的 ref 会失效

导航、AJAX 刷新、accordion 展开都会重建 DOM，旧 ref 指向的节点被替换。

- 每次点击前重新 `browser_snapshot`
- 点击后不要复用上一轮 ref
- 找不到目标元素时先确认它是否在折叠区（`dd` 默认收起），展开后再 snapshot

## 5. React 写操作要真实输入

`element.click()` 对 Nexus 的 React 组件不稳定；`browser_click` 走真实指针事件，是当前可用路径。
输入框如果不是普通 `input`（例如 `contenteditable` 的 WYSIWYG），用页内设值 + `input`/`change` 事件同步。

## 6. 访客页面具有欺骗性

未登录时页面仍然渲染账户菜单、头像占位、`Sign out` 链接，甚至还有**隐藏的**「Please log in」`h1`。

- 登录判断：用 `S1` 的 `/users/myaccount` 状态码（401 访客 / 200 登录）。DOM 里的 `auth/sign_in`、`/users/0` 只在菜单已渲染时出现，只能当辅助证据
- 标题：用 `#pagetitle h1`，不要用 `document.querySelector('h1')`
- 访客访问 Tracking Centre 会得到「You are not allowed to access this area!」，不是 404

## 7. URL 结构不对称

| 页面 | 前缀 |
|------|------|
| MOD 列表 / 游戏首页 | `/games/{d}/...` |
| MOD 详情 / 子 tab | `/{d}/mods/{id}` |
| Tracking Centre | `/{d}/mods/trackingcentre` |
| Download History | `/{d}/users/myaccount?tab=download+history` |

把 MOD 列表写成 `/{d}/mods` 会被重定向到首页或具体 MOD；把 Tracking Centre 写成 `/games/{d}/mods/trackingcentre` 落不到正确页面（实测）。搜索一律走 URL 参数，不要操作 React 搜索框。

## 8. 数据提取的已知噪音

- `isAdult`：`"Adult"` 会和分类文本粘在一起（`"ArmourAdult"`），用 `includes('Adult')` 或行尾匹配
- MOD 列表 tile 里前几个子节点不是 tile（`grid.children` 混有分隔/占位），必须 `if (!titleEl) continue`
- 评论正文里的 `<br>` 要转成换行再取 `textContent`，否则整段粘成一行
- `usedBy` 折叠区只有 "Loading..."，真实列表在 `/api/games/{gameId}/mods/{modId}/required-by`
- snapshot 的无障碍树会合并或省略表格列：tracking 表格在 snapshot 里只显示 7 列，DOM 实际有 9 个 `td`。列映射和结构判断必须用 DOM 计数（`thead th`、`row.querySelectorAll('td').length`），不要因为 snapshot 少列就断定选择器写错了

## 9. 下载落点：挂载盘直接可见

camofox 的 `downloadsDir` = `$CAMOFOX_DOWNLOADS_DIR` 或 `~/.camofox/downloads`，而整个 `~/.camofox` bind mount 到宿主，所以文件下完就在 `~/.camofox/downloads`，**不需要 `docker cp`**（实测容器内写入宿主立即可见）。

- 容器内路径：`/home/node/.camofox/downloads`
- `/home/node/Downloads` 是 overlay 上的 Firefox 默认目录，空的，不要用
- 核对：`ls -lt "$HOME/.camofox/downloads" | head`
- API 也能列：`curl -s http://127.0.0.1:9377/users/camofox_search/downloads`
- Nexus 会改写文件名，以目录里的实际文件名为准

## 10. 登录态与 profile 固定

`browser.camofox.user_id` 已固定为 `camofox_search`，profile 固定为 `~/.camofox/profiles/camofox_search`，Nexus 登录态跨会话保留（实测 `/users/myaccount` 200，账号 `chaorenex1`）。

- 该 profile 同时被 camofox-search（web 搜索后端）使用，两者共用同一个浏览器实例
- 搜索守护进程退出/重启时标签页会消失：`browser_console` 报 400 或 `/tabs` 为空 → 重新 `browser_navigate` 即可，不用重建 profile
- 不设 `browser.camofox.user_id` 时 Hermes 每会话生成 `hermes_<10hex>`，登录态不跨会话；设了就用固定 profile
- 核对当前会话真的用上了固定 profile：`docker logs --tail 40 camofox-browser | grep -o '"userId": *"[^"]*"' | sort | uniq -c`，再看 `ls -ldt ~/.camofox/profiles/*/ | head -3` 的最新目录
- 想确认某个 profile 是否已登录，不必开浏览器：只读打开 `~/.camofox/profiles/<userId>/cookies.sqlite`，查 `moz_cookies` 里目标域名的会话 cookie
- `camofox_auth_open` 用的是 `user_id=hermes` 的独立 profile，且本机端点指向 9378（无监听）→ 登录了也不会作用到浏览会话。用 `browser_vault` 在页面上填账号

## 11. 页内表达式写法

- 直接返回对象/数组，工具会序列化；返回 Promise 会被 await（实测）
- 等待封顶 20–25s，`browser.command_timeout` 默认 30s
- ES6 可用（`const`、箭头函数、可选链、模板字符串实测均通过），但 snippet 统一用 `var` + `function`，减少跨版本摩擦
- 大结果集（60 条 MOD、整页评论）一次返回没问题；不要把 `document.body.innerHTML` 整体回传
