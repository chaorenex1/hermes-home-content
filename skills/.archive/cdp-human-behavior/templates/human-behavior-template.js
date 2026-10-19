const WebSocket = require('ws');
const http = require('http');

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

// ========== 人类行为模拟函数 ==========

async function humanMouseMove(ws, x1, y1, x2, y2) {
    const steps = 15 + Math.floor(Math.random() * 10);
    for (let i = 0; i <= steps; i++) {
        const t = i / steps;
        const x = x1 + (x2 - x1) * t + Math.sin(t * Math.PI) * (Math.random() * 20 - 10);
        const y = y1 + (y2 - y1) * t + Math.sin(t * Math.PI) * (Math.random() * 20 - 10);
        await cdpSend(ws, 'Input.dispatchMouseEvent', {
            type: 'mouseMoved',
            x: Math.round(x),
            y: Math.round(y)
        });
        await sleep(20 + Math.random() * 30);
    }
}

async function humanClick(ws, x, y) {
    await humanMouseMove(ws, 100 + Math.random() * 200, 100 + Math.random() * 200, x, y);
    await sleep(100 + Math.random() * 200);
    await cdpSend(ws, 'Input.dispatchMouseEvent', {
        type: 'mousePressed',
        x: Math.round(x),
        y: Math.round(y),
        button: 'left',
        clickCount: 1
    });
    await sleep(50 + Math.random() * 100);
    await cdpSend(ws, 'Input.dispatchMouseEvent', {
        type: 'mouseReleased',
        x: Math.round(x),
        y: Math.round(y),
        button: 'left',
        clickCount: 1
    });
}

async function humanScroll(ws, deltaY) {
    const steps = Math.abs(deltaY) / 50;
    for (let i = 0; i < steps; i++) {
        await cdpSend(ws, 'Input.dispatchMouseEvent', {
            type: 'mouseWheel',
            x: 500 + Math.random() * 200,
            y: 500 + Math.random() * 200,
            deltaX: 0,
            deltaY: deltaY > 0 ? 50 : -50
        });
        await sleep(100 + Math.random() * 200);
    }
}

// ========== 主流程 ==========

async function main() {
    console.log('[1/6] 获取浏览器信息...');
    const browserInfo = await httpGet('/json/version');
    console.log(`  浏览器: ${browserInfo.Browser}`);
    
    console.log('[2/6] 连接浏览器 WebSocket...');
    const browserWs = await wsConnect(browserInfo.webSocketDebuggerUrl);
    console.log('  ✅ 已连接');

    console.log('[3/6] 创建新标签页...');
    const target = await cdpSend(browserWs, 'Target.createTarget', { url: 'about:blank' });
    const tabWsUrl = `ws://127.0.0.1:${PORT}/devtools/page/${target.targetId}`;
    const tabWs = await wsConnect(tabWsUrl);

    console.log('[4/6] 启用 CDP 域...');
    await cdpSend(tabWs, 'Page.enable');
    await cdpSend(tabWs, 'Runtime.enable');
    await cdpSend(tabWs, 'Network.enable');
    console.log('  ✅ Page, Runtime, Network 已启用');

    console.log('[5/6] 设置真实用户代理和视口...');
    await cdpSend(tabWs, 'Emulation.setDeviceMetricsOverride', {
        width: 1920,
        height: 1080,
        deviceScaleFactor: 1,
        mobile: false
    });
    await cdpSend(tabWs, 'Emulation.setUserAgentOverride', {
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36 Edg/149.0.0.0'
    });
    console.log('  ✅ 视口 1920x1080, 真实用户代理已设置');

    console.log('[6/6] 导航到目标网站...');
    await cdpSend(tabWs, 'Page.navigate', { url: 'https://example.com' });
    
    // 等待页面加载
    console.log('  等待 Page.loadEventFired...');
    await new Promise((resolve) => {
        const handler = (data) => {
            const msg = JSON.parse(data.toString());
            if (msg.method === 'Page.loadEventFired') {
                tabWs.removeListener('message', handler);
                resolve();
            }
        };
        tabWs.on('message', handler);
        setTimeout(() => {
            tabWs.removeListener('message', handler);
            resolve();
        }, 30000);
    });
    console.log('  ✅ 页面加载完成');

    // 模拟人类行为
    console.log('  模拟人类: 等待 JS 渲染...');
    await sleep(3000 + Math.random() * 3000);

    console.log('  模拟人类: 鼠标移动和滚动...');
    await humanMouseMove(tabWs, 200, 200, 800, 400);
    await sleep(500 + Math.random() * 1000);
    await humanScroll(tabWs, 500);
    await sleep(1000 + Math.random() * 2000);
    await humanScroll(tabWs, -300);
    await sleep(500 + Math.random() * 1000);
    console.log('  ✅ 行为模拟完成');

    // 获取页面信息
    const title = await pageEval(tabWs, 'document.title');
    const url = await pageEval(tabWs, 'window.location.href');
    console.log(`\n标题: ${title}`);
    console.log(`URL: ${url}`);

    // 检查登录状态（根据目标网站调整选择器）
    const isLoggedIn = await pageEval(tabWs, `
        !!(document.querySelector('.avatar') || 
           document.querySelector('[class*="user"]') ||
           document.querySelector('.login-tip') === null)
    `);
    console.log(`登录状态: ${isLoggedIn ? '可能已登录' : '未登录或无法检测'}`);

    console.log('\n✅ 任务完成！');
    
    // 保持连接或关闭
    await sleep(30000);
    tabWs.close();
    browserWs.close();
}

main().catch(err => { console.error('FATAL:', err.message); process.exit(1); });
