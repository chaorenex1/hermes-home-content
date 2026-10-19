const WebSocket = require('ws');
const http = require('http');

const PORT = 9222;
const BASE = `http://127.0.0.1:${PORT}`;

// ============ 辅助函数 ============

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
function randomDelay(min, max) { return sleep(min + Math.random() * (max - min)); }

// ============ 人类行为模拟 ============

async function setupHumanLikeEnvironment(tabWs) {
    console.log('[Setup] 设置真实视口和用户代理...');
    await cdpSend(tabWs, 'Emulation.setDeviceMetricsOverride', {
        width: 1920,
        height: 1080,
        deviceScaleFactor: 1,
        mobile: false
    });
    await cdpSend(tabWs, 'Emulation.setUserAgentOverride', {
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36 Edg/149.0.0.0'
    });
}

async function humanLikeScroll(tabWs) {
    console.log('[Human] 模拟滚动...');
    await pageEval(tabWs, `
        window.scrollTo({ top: Math.random() * 500 + 200, behavior: 'smooth' });
        'scrolled';
    `);
    await randomDelay(2000, 5000);
    
    if (Math.random() > 0.5) {
        await pageEval(tabWs, `
            window.scrollTo({ top: 0, behavior: 'smooth' });
            'scrolled back';
        `);
        await randomDelay(1000, 3000);
    }
}

async function dismissCookies(tabWs) {
    try {
        const r = await pageEval(tabWs, `
            (function() {
                const buttons = document.querySelectorAll('button');
                for (const b of buttons) {
                    const text = (b.innerText || b.textContent || '').trim();
                    if (text === 'Deny' || text === '拒绝' || text.includes('Allow') || text.includes('同意')) {
                        b.click();
                        return 'dismissed: ' + text;
                    }
                }
                return 'none';
            })()
        `);
        console.log(`[Cookie] ${r}`);
        await sleep(2000);
    } catch(e) {}
}

// ============ 主流程 ============

async function main() {
    const targetUrl = process.argv[2] || 'https://www.bilibili.com';
    console.log(`🚀 启动人类行为模拟浏览: ${targetUrl}\n`);

    // 1. 获取浏览器信息
    console.log('[1/6] 获取浏览器信息...');
    const browserInfo = await httpGet('/json/version');
    console.log(`  浏览器: ${browserInfo.Browser}`);

    // 2. 连接浏览器
    console.log('[2/6] 连接浏览器...');
    const browserWs = await wsConnect(browserInfo.webSocketDebuggerUrl);
    console.log('  ✅ 已连接');

    // 3. 创建标签页
    console.log('[3/6] 创建标签页...');
    const target = await cdpSend(browserWs, 'Target.createTarget', { url: 'about:blank' });
    const tabWs = await wsConnect(`ws://127.0.0.1:${PORT}/devtools/page/${target.targetId}`);
    console.log(`  标签页: ${target.targetId}`);

    // 4. 启用 CDP 域
    await cdpSend(tabWs, 'Page.enable');
    await cdpSend(tabWs, 'Runtime.enable');
    await cdpSend(tabWs, 'Network.enable');

    // 5. 设置人类环境
    console.log('[4/6] 设置人类环境...');
    await setupHumanLikeEnvironment(tabWs);
    console.log('  ✅ 视口 1920x1080, 真实 UA');

    // 6. 导航
    console.log('[5/6] 导航到目标页面...');
    await cdpSend(tabWs, 'Page.navigate', { url: targetUrl });
    
    // 等待加载
    await new Promise((resolve) => {
        const handler = (data) => {
            const msg = JSON.parse(data.toString());
            if (msg.method === 'Page.loadEventFired') {
                tabWs.removeListener('message', handler);
                resolve();
            }
        };
        tabWs.on('message', handler);
        setTimeout(() => resolve(), 30000);
    });
    console.log('  ✅ 页面加载完成');

    // 7. 等待 JS 渲染（关键！）
    console.log('  等待 JS 渲染...');
    await randomDelay(6000, 10000);

    // 8. 处理 Cookie 弹窗
    await dismissCookies(tabWs);

    // 9. 模拟人类滚动
    await humanLikeScroll(tabWs);

    // 10. 提取数据
    console.log('[6/6] 提取页面信息...');
    const title = await pageEval(tabWs, 'document.title');
    const url = await pageEval(tabWs, 'window.location.href');
    console.log(`\n📄 标题: ${title}`);
    console.log(`🔗 URL: ${url}`);

    // 提取视频/内容（根据页面自适应）
    const contentInfo = await pageEval(tabWs, `
        (function() {
            const videos = document.querySelectorAll('.bili-video-card, [class*="video-card"], .video-item');
            const links = document.querySelectorAll('a[href*="/video/"]');
            return {
                videoCards: videos.length,
                videoLinks: links.length,
                bodyText: document.body.innerText.substring(0, 200)
            };
        })()
    `);
    console.log(`📊 视频卡片: ${contentInfo.videoCards}, 视频链接: ${contentInfo.videoLinks}`);

    console.log('\n✅ 任务完成！');
    console.log('按 Ctrl+C 结束，或保持运行...');
    
    // 保持连接
    await sleep(30000);
    
    tabWs.close();
    browserWs.close();
}

main().catch(err => { console.error('❌ FATAL:', err.message); process.exit(1); });
