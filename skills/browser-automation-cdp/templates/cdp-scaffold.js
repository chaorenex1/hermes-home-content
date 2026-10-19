const WebSocket = require('ws');
const http = require('http');
const fs = require('fs');

// ═══════════════════════════════════════════════
// CDP Self-Contained Script Template
// Usage: node this-script.js
// Prereq: npm install ws
// Ensure Edge is running with: --remote-debugging-port=9222
// ═══════════════════════════════════════════════

const PORT = 9222;
const BASE = `http://127.0.0.1:${PORT}`;

// ── HTTP helpers ──────────────────────────────
function httpGet(path) {
    return new Promise((resolve, reject) => {
        http.get(`${BASE}${path}`, r => {
            let d = ''; r.on('data', c => d += c);
            r.on('end', () => { try { resolve(JSON.parse(d)); } catch(e) { reject(e); } });
        }).on('error', reject);
    });
}

// ── WebSocket helpers ─────────────────────────
function wsConnect(url) {
    return new Promise((resolve, reject) => {
        const ws = new WebSocket(url);
        ws.on('open', () => resolve(ws));
        ws.on('error', e => reject(e));
        setTimeout(() => reject(new Error('WS timeout')), 15000);
    });
}

// ── CDP command (fire-and-forget with response) ─
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

// ── Evaluate JS in page context ───────────────
async function pageEval(ws, expression) {
    const result = await cdpSend(ws, 'Runtime.evaluate', { expression, returnByValue: true });
    if (result.exceptionDetails) throw new Error(`Eval: ${JSON.stringify(result.exceptionDetails)}`);
    return result.result.value;
}

// ── Sleep ─────────────────────────────────────
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ── Dismiss cookie/GDPR popup ─────────────────
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
        if (r !== 'none') await sleep(2000);
    } catch(e) {}
}

// ═══════════════════════════════════════════════
// MAIN — customize below
// ═══════════════════════════════════════════════

async function main() {
    // 1. Connect to browser
    const browserInfo = await httpGet('/json/version');
    console.log(`Browser: ${browserInfo.Browser}`);
    const browserWs = await wsConnect(browserInfo.webSocketDebuggerUrl);

    // 2. Create new tab
    const target = await cdpSend(browserWs, 'Target.createTarget', { url: 'about:blank' });
    const tabWsUrl = `ws://127.0.0.1:${PORT}/devtools/page/${target.targetId}`;
    const tabWs = await wsConnect(tabWsUrl);

    // 3. Enable domains
    await cdpSend(tabWs, 'Page.enable');
    await cdpSend(tabWs, 'Runtime.enable');

    // 4. Navigate
    console.log('Navigating...');
    await cdpSend(tabWs, 'Page.navigate', { url: 'https://example.com' });
    await sleep(6000);  // wait for JS rendering

    // 5. Dismiss cookie popup
    await dismissCookies(tabWs);

    // 6. Extract data
    const title = await pageEval(tabWs, 'document.title');
    console.log(`Title: ${title}`);

    // 7. Cleanup
    tabWs.close();
    browserWs.close();
    console.log('Done.');
}

main().catch(err => { console.error('FATAL:', err.message); process.exit(1); });
