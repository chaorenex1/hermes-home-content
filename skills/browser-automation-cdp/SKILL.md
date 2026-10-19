---
name: browser-automation-cdp
description: CDP browser automation via Edge/Chrome remote debugging — navigate, click, extract JS-rendered DOM, and handle cookie popups.
---

# Browser Automation Skill

> 通过用户已登录的浏览器（Edge/Chrome）执行自动化任务。
> 核心技术：CDP（Chrome DevTools Protocol），通过 WebSocket 与浏览器通信。

---

## 何时使用

优先用 `web_fetch`。以下情况才需要 CDP 自动化：

| 场景 | 是否需要 CDP |
|------|------------|
| 静态 HTML 页面 | ❌ `web_fetch` 即可 |
| JS 渲染的页面（如 B站） | ✅ 需要 |
| 需要登录态的网站（已登录在你的浏览器里） | ✅ 需要 |
| 需要交互（点击、填表、滚动） | ✅ 需要 |
| 网站有反爬/风控 | ⚠️ 可能失败 |

---

## 架构概览

```
Agent（我）
    ↓ require('./cdp-automation.js')
cdp-automation.js（连接管理器 + 浏览器抽象类）
    ↓ WebSocket (HTTP → CDP)
用户 Windows 浏览器（Edge:9222 / Chrome:9223）
    ↓ 执行 JS / 读 DOM / 点击
目标网站（bilibili / 小红书 / Nexus Mods 等）
```

---

## 快速开始

### 1. 确保浏览器 remote debugging 已开启

**Edge（端口 9222）：**
```powershell
# 方式 A（已失效）：Edge/Chrome ≥136 起，日常默认数据目录不接受调试端口，端口不会打开
# 方式 B：独立 profile（推荐）
Start-Process "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --user-data-dir="<PATH_TO_BROWSER_PROFILE>"
```

**⚠️ Edge/Chrome ≥136（实测 Edge 155）默认数据目录拒绝调试端口**：进程输出 `DevTools remote debugging requires a non-default data directory. Specify this using --user-data-dir.`，浏览器照常启动但端口不打开。用 junction 指向同一目录能绕过该检查，但后果严重：非默认数据目录会禁用 App-Bound Encryption（ABE），浏览器随即静默清空该 profile 全部 v20 cookie——除非事先拷贝过 Cookies 数据库，否则不可恢复。要登录态就在隔离 profile 里登录；绝不要对日常 profile 做调试启动，动手前先备份其 Cookies 文件。

**Chrome（端口 9223）：**
```powershell
Start-Process "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9223
```

**bash/MSYS 环境注意：**
`taskkill /F` 在 bash 中会被解析为路径，需用 `cmd.exe //c "taskkill /F /IM msedge.exe /T"`。启动 Edge 用 `"/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" --remote-debugging-port=9222 &`。

### 2. 确认 ws 模块可用

内置 `cdp-automation.js` 硬编码了 Linux 路径的 `require('ws')`。在 Windows 上推荐**自包含脚本**方式：在项目目录 `npm install ws`，直接写原生 CDP 脚本（见下方模板），不依赖内置模块。

### 3. 在任务中调用（内置模块方式）

```javascript
const { edge, chrome } = require('./browser-automation/cdp-automation.js');

await edge.goto('https://目标网站.com');
const data = await edge.eval(`document.title`);
```

---

## 自包含 CDP 脚本模板（Windows 推荐）

当内置模块因 ws 路径问题不可用时，使用以下自包含模板。首先确保 `npm install ws` 已完成。

```javascript
const WebSocket = require('ws');
const http = require('http');
const fs = require('fs');

const PORT = 9222;
const BASE = `http://127.0.0.1:${PORT}`;

function httpGet(path) {
    return new Promise((resolve, reject) => {
        http.get(`${BASE}${path}`, r => {
            let d = ''; r.on('data', c => d += c);
            r.on('end', () => { try { resolve(JSON.parse(d)); } catch(e) { reject(e); } });
        }).on('error', reject);
    });
}

function wsConnect(url) {
    return new Promise((resolve, reject) => {
        const ws = new WebSocket(url);
        ws.on('open', () => resolve(ws));
        ws.on('error', e => reject(e));
        setTimeout(() => reject(new Error('WS timeout')), 15000);
    });
}

function cdpSend(ws, method, params = {}) {
    return new Promise((resolve, reject) => {
        const id = Math.floor(Math.random() * 999999);
        const timeout = setTimeout(() => { reject(new Error(`${method} timeout`)); }, 30000);
        const handler = (data) => {
            const msg = JSON.parse(data.toString());
            if (msg.id === id) {
                clearTimeout(timeout);
                ws.removeListener('message', handler);
                if (msg.error) reject(new Error(`${method}: ${JSON.stringify(msg.error)}`));
                else resolve(msg.result);
            }
        };
        ws.on('message', handler);
        ws.send(JSON.stringify({ id, method, params }));
    });
}

async function pageEval(ws, expression) {
    const result = await cdpSend(ws, 'Runtime.evaluate', { expression, returnByValue: true });
    if (result.exceptionDetails) throw new Error(`Eval: ${JSON.stringify(result.exceptionDetails)}`);
    return result.result.value;
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function main() {
    const browserInfo = await httpGet('/json/version');
    const browserWs = await wsConnect(browserInfo.webSocketDebuggerUrl);

    const target = await cdpSend(browserWs, 'Target.createTarget', { url: 'about:blank' });
    const tabWsUrl = `ws://127.0.0.1:${PORT}/devtools/page/${target.targetId}`;
    const tabWs = await wsConnect(tabWsUrl);

    await cdpSend(tabWs, 'Page.enable');
    await cdpSend(tabWs, 'Runtime.enable');

    // Navigate and wait for JS rendering
    await cdpSend(tabWs, 'Page.navigate', { url: 'https://example.com' });
    await sleep(6000);

    // Dismiss cookie popup if present
    await dismissCookies(tabWs);

    // Extract data
    const data = await pageEval(tabWs, `document.title`);
    console.log('Title:', data);

    tabWs.close();
    browserWs.close();
}

main().catch(err => { console.error('FATAL:', err.message); process.exit(1); });
```

---

## 通用 CDP 模式

### Cookie / GDPR 弹窗处理

多数欧洲网站首次访问会弹出 cookie 同意对话框，需先关闭再提取数据：

```javascript
async function dismissCookies(ws) {
    try {
        const r = await pageEval(ws, `
            (function() {
                var btns = document.querySelectorAll('button');
                for (var b of btns) {
                    var t = b.innerText || b.textContent || '';
                    if (t.trim() === 'Deny') { b.click(); return 'deny'; }
                }
                for (var b of btns) {
                    var t = b.innerText || b.textContent || '';
                    if (t.includes('Allow selection')) { b.click(); return 'save'; }
                }
                return 'none';
            })()
        `);
        await sleep(2000);
    } catch(e) {}
}
```

### `className` 陷阱：SVG 元素

`el.className?.substring()` 在 SVG 元素上会抛 `TypeError: el.className?.substring is not a function`，因为 SVG 元素的 `className` 是 `SVGAnimatedString` 而非普通字符串。

**安全写法：**
```javascript
var cls = (el.className && typeof el.className === 'string') ? el.className : '';
```

### 从页面文本中提取密集统计信息

当页面 DOM 不规则但 `innerText` 包含结构化数据时，直接在全文上跑正则比逐元素查询更可靠：

```javascript
var text = document.body.innerText || '';
function extract(pattern) {
    var m = text.match(pattern);
    return m ? m[1].replace(/,/g, '').trim() : '';
}
var endorsements = extract(/Endorsements\s*\n\s*([\d,]+)/);
var downloads = extract(/Total DLs\s*\n\s*([\d,]+)/);
// 处理 "--" 占位符（无数据时）
if (!downloads) {
    var m2 = text.match(/Total DLs\s*\n\s*(--)/);
    if (m2) downloads = '0';
}
```

---

## API 参考

### `browser.goto(url)`
导航到指定 URL，等待页面加载完成（Page.loadEventFired + 额外 2s 等待 JS 渲染）。

```javascript
await edge.goto('https://space.bilibili.com/151190274/video');
```

### `browser.eval(script)`
在页面上下文执行 JavaScript，返回结果。

```javascript
const r = await edge.eval(`document.title`);
```

### `browser.click(selector)`
点击匹配选择器的第一个元素。通过计算元素中心坐标后用 `document.elementFromPoint` 模拟点击。

### `browser.screenshot()`
截图当前页面，返回 PNG base64 字符串。

### `browser.wait(ms)`
显式等待 JS 渲染或网络请求。

### `browser.tabs()`
获取所有标签页列表。

---

## 平台踩坑经验

### B站
- 选择器：视频卡片 `.upload-video-card`，标题 `.bili-video-card__title`
- B站页面完全 JS 渲染，`web_fetch` 拿到的是空壳
- API 有 wbi 签名保护，必须走 DOM

### 小红书（Xiaohongshu）
- 有强反自动化检测，建议先测试再自动化

### Minimax
- Next.js SPA 路由，直接 `Page.navigate` 到深层路径会 404，需先进已知可用子页面再用 JS 点击导航

### Nexus Mods
详细 DOM 结构和抓取配方见 `references/nexus-mods.md`。要点：
- 页面用 Tailwind 类名，mod 卡片选择器：`[class*="group/mod-tile"]`
- Mod ID 从链接提取：`a[href*="/mods/"]` → `/mods/(\d+)`
- 统计信息在 `innerText` 中格式为 `Endorsements\n311\nUnique DLs\n7,568`
- 新 mod 的 DL/Views 显示 `--`（需处理为 "0"）
- 图片 thumbnail URL 去掉 `/thumbnails/` 即为原图

---

## 已知限制

### 内置模块 ws 路径为 Linux 硬编码
`cdp-automation.js` 的 `require('/home/yeying233/.npm-global/.../ws')` 在 Windows 上会报 `MODULE_NOT_FOUND`。推荐使用自包含脚本模板（见上方）。

### CDP 连接复用问题
同一端口只能有一个 WebSocket 连接。任务失败导致连接残留时需重启浏览器。

### 等待时间不够
JS 密集型页面有时需要 8-10s 等待。

### Edge 被联想 Vantage 占用端口
杀掉 `msedgewebview2.exe` 实例再启动日常 Edge。

### HTTP-only Cookie / 读取全部 cookie
`document.cookie` 拿不到 `HttpOnly` cookie。要读含 HttpOnly 的全部 cookie，走 CDP：
`Network.getAllCookies` 只能在 **page 级** WebSocket 上执行——`/json/version` 给的 browser 级 ws
在当前 Chromium 上返回 `'Network.getAllCookies' wasn't found`。用 `/json/list` 取第一个
`type:"page"` 的 `webSocketDebuggerUrl`；没有页面时 `PUT /json/new?about:blank` 新建再取。
返回项是 Playwright 格式（`sameSite` 为字符串；"None" 且非 secure 的丢弃该字段）。
浏览器运行期间其 Cookies SQLite 被独占锁定（读文件 WinError 32，重试无效）——CDP 是运行中浏览器
唯一可行的读 cookie 途径；浏览器关闭时可直接拷贝数据库文件再解析。

**需要把登录态搬进 camofox**（而不是在本地浏览器里自动化）时走另一条路：让用户在自己浏览器登录，
再 `camofox-search-import-cookies` 导入。完整流程见技能 `browser-login-cookie-import`，
v20 / App-Bound 加密细节见其 `references/abe-edge-chromium.md`。

**现代 Edge/Chrome 的 v20（app-bound）cookie 用户态读不了**：解密需 elevation service 参与，只有浏览器自身能取明文。且 CDP 读到的是**当前会话**的 cookie 库——非默认 user-data-dir（含 junction 绕法）会禁用 ABE 并清空存量 v20 行（见“快速开始”的警告）。动手前先拷贝 Cookies 文件兜底；值永远不得打印。

---

## 模块文件位置

```
C:\Users\<user>\AppData\Local\hermes\skills\browser-automation-cdp\
├── cdp-automation.js    ← 核心模块（内置，Linux 路径）
├── SKILL.md             ← 本文件
└── references/
    └── nexus-mods.md    ← Nexus Mods 抓取配方
```

---

*最后更新：2026-06-23*
*本次新增：自包含脚本模板 / Cookie 弹窗处理 / className SVG 陷阱 / innerText 正则提取模式 / Nexus Mods 参考文档*
