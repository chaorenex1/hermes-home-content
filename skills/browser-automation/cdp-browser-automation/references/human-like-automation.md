---
name: cdp-human-like-automation
description: CDP-based human-like browser automation — anti-detection patterns, realistic viewport/UA setup, natural scrolling, and timing randomization.
---

# CDP 模拟人类用户自动化

> 通过 Chrome DevTools Protocol (CDP) 控制浏览器，模拟真实人类用户行为以避免反爬检测。

---

## 何时使用

当目标网站有反自动化检测（如 B站、小红书、各类电商平台），需要模拟真实用户行为时：

| 场景 | 方案 |
|------|------|
| 简单静态页面 | `web_fetch` 或 Hermes browser 工具 |
| 需要登录态 | Hermes browser 工具（自带登录态） |
| JS 渲染 + 轻度反爬 | CDP + 基础等待 |
| **强反爬/风控** | **CDP + 人类行为模拟**（本技能） |

---

## 核心原则

反检测的核心不是"隐藏自己是自动化"，而是"表现得像真实用户"。

### 人类行为特征

| 特征 | 自动化常见错误 | 人类行为模拟 |
|------|-------------|-------------|
| 视口 | 默认 800x600 或 headless | 真实分辨率 1920x1080 |
| 用户代理 | headless 标识 | 真实浏览器 UA |
| 鼠标轨迹 | 瞬间移动 | 曲线移动、随机停顿 |
| 滚动 | 瞬间跳转 | 平滑滚动、随机停顿 |
| 点击间隔 | 固定间隔 | 随机 1-5 秒间隔 |
| 页面停留 | 秒开秒关 | 阅读内容后操作 |

---

## 完整流程

### Step 1: 启动浏览器（Windows Edge）

```bash
# 关闭现有 Edge
cmd.exe //c "taskkill /F /IM msedge.exe /T" 2>/dev/null

# 用 Hermes background=true 启动（不要加 &）
# terminal(background=true, command='"/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" --remote-debugging-port=9222')

# 等待 3-5 秒
curl -s http://127.0.0.1:9222/json/version
```

**Windows 踩坑：**
- `Start-Process` 是 PowerShell 命令，在 `cmd.exe //c` 中不可用
- MSYS 中 `&` 后台运行会被 Hermes 拒绝，用 `background=true` 参数
- 路径格式：`"/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"`

### Step 2: 安装依赖

```bash
cd /c/Users/<user> && npm install ws
```

### Step 3: CDP 连接与配置

```javascript
const WebSocket = require('ws');
const http = require('http');

const PORT = 9222;
const BASE = `http://127.0.0.1:${PORT}`;

// 辅助函数
function httpGet(path) { /* ... */ }
function wsConnect(url) { /* ... */ }
function cdpSend(ws, method, params = {}) { /* ... */ }
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function main() {
    // 1. 获取浏览器信息
    const browserInfo = await httpGet('/json/version');
    
    // 2. 连接浏览器
    const browserWs = await wsConnect(browserInfo.webSocketDebuggerUrl);
    
    // 3. 创建标签页
    const target = await cdpSend(browserWs, 'Target.createTarget', { url: 'about:blank' });
    const tabWs = await wsConnect(`ws://127.0.0.1:${PORT}/devtools/page/${target.targetId}`);
    
    // 4. 启用 CDP 域
    await cdpSend(tabWs, 'Page.enable');
    await cdpSend(tabWs, 'Runtime.enable');
    await cdpSend(tabWs, 'Network.enable');
```

### Step 4: 模拟人类环境

```javascript
    // 设置真实视口
    await cdpSend(tabWs, 'Emulation.setDeviceMetricsOverride', {
        width: 1920,
        height: 1080,
        deviceScaleFactor: 1,
        mobile: false
    });
    
    // 设置真实用户代理（与浏览器一致）
    await cdpSend(tabWs, 'Emulation.setUserAgentOverride', {
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...'
    });
```

### Step 5: 导航并等待

```javascript
    // 导航
    await cdpSend(tabWs, 'Page.navigate', { url: 'https://target-site.com' });
    
    // 等待页面加载事件
    await new Promise((resolve) => {
        const handler = (data) => {
            const msg = JSON.parse(data.toString());
            if (msg.method === 'Page.loadEventFired') {
                tabWs.removeListener('message', handler);
                resolve();
            }
        };
        tabWs.on('message', handler);
        setTimeout(() => resolve(), 30000); // 超时保护
    });
    
    // 等待 JS 渲染（关键！）
    await sleep(6000 + Math.random() * 4000); // 6-10 秒随机
```

### Step 6: 模拟人类滚动

```javascript
    // 随机向下滚动
    await pageEval(tabWs, `
        window.scrollTo({ top: Math.random() * 500 + 200, behavior: 'smooth' });
        'scrolled';
    `);
    await sleep(2000 + Math.random() * 3000); // 2-5 秒停顿
    
    // 可能继续滚动或回滚
    if (Math.random() > 0.5) {
        await pageEval(tabWs, `
            window.scrollTo({ top: 0, behavior: 'smooth' });
            'scrolled back';
        `);
    }
```

### Step 7: 提取数据

```javascript
    const title = await pageEval(tabWs, 'document.title');
    const data = await pageEval(tabWs, `
        // 提取逻辑...
    `);
```

---

## 完整脚本模板

见 `templates/human-like-cdp.js` — 可直接复制使用的完整模板，包含：
- 完整的 CDP 连接流程
- 人类行为模拟函数（滚动、等待、Cookie 处理）
- 自适应内容提取
- 命令行参数支持：`node human-like-cdp.js https://example.com`

## 平台特定参考

- **Windows 设置**: 见 `references/windows-setup.md` — Edge 启动、ws 安装、路径问题、故障排查

---

## 反检测进阶技巧

### 1. 鼠标移动模拟

```javascript
async function moveMouse(ws, x, y) {
    await cdpSend(ws, 'Input.dispatchMouseEvent', {
        type: 'mouseMoved',
        x, y
    });
}

// 贝塞尔曲线移动
async function humanLikeMove(ws, fromX, fromY, toX, toY) {
    const steps = 10 + Math.floor(Math.random() * 10);
    for (let i = 0; i <= steps; i++) {
        const t = i / steps;
        const x = fromX + (toX - fromX) * t + (Math.random() - 0.5) * 20;
        const y = fromY + (toY - fromY) * t + (Math.random() - 0.5) * 20;
        await moveMouse(ws, x, y);
        await sleep(20 + Math.random() * 50);
    }
}
```

### 2. 随机化时间

```javascript
function randomDelay(min, max) {
    return sleep(min + Math.random() * (max - min));
}

// 使用
await randomDelay(1000, 3000); // 1-3 秒随机等待
```

### 3. 处理 Cookie 弹窗

```javascript
async function dismissCookies(ws) {
    try {
        const r = await pageEval(ws, `
            (function() {
                const buttons = document.querySelectorAll('button');
                for (const b of buttons) {
                    const text = (b.innerText || b.textContent || '').trim();
                    if (text === 'Deny' || text === '拒绝' || text.includes('Allow')) {
                        b.click();
                        return 'dismissed: ' + text;
                    }
                }
                return 'none';
            })()
        `);
        await sleep(2000);
    } catch(e) {}
}
```

---

## 平台特定注意事项

### B站
- 完全 JS 渲染，必须等 6-10 秒
- 视频卡片选择器：`.bili-video-card`, `.bili-video-card__title`
- API 有 wbi 签名，建议走 DOM 而非 API

### 小红书
- 强反自动化检测，需要完整人类行为模拟
- 建议先手动测试再自动化

---

## 故障排查

| 问题 | 原因 | 解决 |
|------|------|------|
| `MODULE_NOT_FOUND: ws` | 未安装 ws 模块 | `npm install ws` |
| `WS timeout` | 浏览器未启动或端口占用 | 检查端口，重启浏览器 |
| 页面空白 | JS 未渲染完成 | 增加等待时间到 8-10 秒 |
| 被检测为机器人 | 缺少人类行为模拟 | 添加滚动、随机等待、真实 UA |
| `Start-Process` 不可用 | 在 cmd 中使用 PowerShell 命令 | 改用 MSYS 路径直接启动 |

---

*最后更新：2026-06-29*
