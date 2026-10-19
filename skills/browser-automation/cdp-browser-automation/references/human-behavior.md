---
name: cdp-human-behavior
description: CDP browser automation with human-like behavior simulation and real user data preservation. Supplements browser-automation-cdp for login-state-aware automation.
---

# CDP Human Behavior Simulation

> 在使用用户真实浏览器数据（保留登录态）的同时，模拟真实人类行为以避免反自动化检测。
> 补充 `browser-automation-cdp` 技能，专注行为模拟和登录态保持。

---

## 两种启动模式

| 模式 | 命令 | 登录态 | 窗口 | 用途 |
|------|------|--------|------|------|
| **真实数据模式**（推荐） | `--remote-debugging-port=9222`（省略 `--user-data-dir`） | ✅ 保留 | ✅ 可见 | 需要登录态的自动化 |
| **隔离模式** | `--remote-debugging-port=9222 --user-data-dir="C:\..."` | ❌ 无 | ❌ 可 headless | 匿名测试、爬虫 |

---

## 真实数据模式启动

```bash
# Windows - 使用用户真实数据（保留登录态）
cmd.exe //c "taskkill /F /IM msedge.exe /T"  # 先关闭现有 Edge
sleep 2

# 启动 CDP 浏览器（使用真实用户数据）
"/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" \
    --remote-debugging-port=9222 \
    --no-first-run \
    --no-default-browser-check \
    about:blank
```

**关键：** 省略 `--user-data-dir` 参数即可使用用户默认数据目录。

**bash/MSYS 环境注意：**
- 不要用 `&` 后台运行，使用 `terminal(background=true)`
- `taskkill` 需通过 `cmd.exe //c` 调用

---

## 人类行为模拟代码

### 1. 贝塞尔曲线鼠标移动

```javascript
async function humanMouseMove(ws, x1, y1, x2, y2) {
    const steps = 15 + Math.floor(Math.random() * 10);
    for (let i = 0; i <= steps; i++) {
        const t = i / steps;
        // 添加随机抖动模拟人类手部抖动
        const x = x1 + (x2 - x1) * t + Math.sin(t * Math.PI) * (Math.random() * 20 - 10);
        const y = y1 + (y2 - y1) * t + Math.sin(t * Math.PI) * (Math.random() * 20 - 10);
        await cdpSend(ws, 'Input.dispatchMouseEvent', {
            type: 'mouseMoved',
            x: Math.round(x),
            y: Math.round(y)
        });
        await sleep(20 + Math.random() * 30);  // 每步 20-50ms
    }
}
```

### 2. 人类点击模式

```javascript
async function humanClick(ws, x, y) {
    // 先移动鼠标到目标附近
    await humanMouseMove(ws, 100 + Math.random() * 200, 100 + Math.random() * 200, x, y);
    await sleep(100 + Math.random() * 200);  // 悬停 100-300ms
    
    // 按下
    await cdpSend(ws, 'Input.dispatchMouseEvent', {
        type: 'mousePressed',
        x: Math.round(x),
        y: Math.round(y),
        button: 'left',
        clickCount: 1
    });
    await sleep(50 + Math.random() * 100);  // 按住 50-150ms
    
    // 释放
    await cdpSend(ws, 'Input.dispatchMouseEvent', {
        type: 'mouseReleased',
        x: Math.round(x),
        y: Math.round(y),
        button: 'left',
        clickCount: 1
    });
}
```

### 3. 自然滚动

```javascript
async function humanScroll(ws, deltaY) {
    const steps = Math.abs(deltaY) / 50;
    for (let i = 0; i < steps; i++) {
        await cdpSend(ws, 'Input.dispatchMouseEvent', {
            type: 'mouseWheel',
            x: 500 + Math.random() * 200,  // 随机滚动位置
            y: 500 + Math.random() * 200,
            deltaX: 0,
            deltaY: deltaY > 0 ? 50 : -50
        });
        await sleep(100 + Math.random() * 200);  // 每步 100-300ms
    }
}
```

### 4. 随机延迟辅助

```javascript
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// 使用示例：随机等待 3-6 秒
await sleep(3000 + Math.random() * 3000);
```

---

## 完整脚本模板

见 `templates/human-behavior-template.js`

---

## 检测登录状态

```javascript
const isLoggedIn = await pageEval(ws, `
    !!(document.querySelector('.avatar') || 
       document.querySelector('[class*="user"]') ||
       document.querySelector('.login-tip') === null)
`);
```

---

## Windows 批处理脚本注意事项

1. **编码问题**：批处理文件需使用 ANSI 或 UTF-8-BOM 编码，否则中文会乱码
2. **避免 `&` 后台**：在 MSYS bash 中使用 `terminal(background=true)` 代替 `&`
3. **路径空格**：含空格路径需用引号包裹，如 `"C:\Program Files (x86)\..."`

---

## 与 browser-automation-cdp 的关系

```
browser-automation-cdp  ← 基础 CDP 连接、导航、提取
cdp-human-behavior      ← 本技能：行为模拟、登录态保持、反检测
```

使用时应先加载 `browser-automation-cdp`，再参考本技能的行为模拟部分。

---

*Created: 2026-06-29*
