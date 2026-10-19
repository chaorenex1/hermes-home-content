// cdp-batch-fetch.js — 通过 CDP 在已通过反爬挑战的页面上下文里批量 fetch 子页（可断点续抓）
// 依赖: npm install ws（脚本目录或其父目录有 node_modules/ws 即可）
// 用法: node cdp-batch-fetch.js <port> <list.json> <outDir> [batchSize=32] [concurrency=4]
//   list.json : JSON 数组；元素为相对路径（与当前标签页同站点）或绝对 URL
//   outDir    : 输出目录；文件名为元素 basename；已存在则跳过（断点续抓）
// 前置: 浏览器已用 --remote-debugging-port 启动，且有一个处于目标站点、挑战已通过的标签页。
//   挑战未过时先用轮询 document.title 等待（见 references/bulk-page-capture.md）。
const WebSocket = require('ws');
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = parseInt(process.argv[2] || '9222', 10);
const LIST = process.argv[3];
const OUT = process.argv[4];
const BATCH = parseInt(process.argv[5] || '32', 10);
const CONC = parseInt(process.argv[6] || '4', 10);
const BASE = 'http://127.0.0.1:' + PORT;

function httpGet(p) { return new Promise((res, rej) => { http.get(BASE + p, r => { let d = ''; r.on('data', c => d += c); r.on('end', () => { try { res(JSON.parse(d)); } catch (e) { rej(e); } }); }).on('error', rej); }); }
function wsConnect(url) { return new Promise((res, rej) => { const ws = new WebSocket(url, { maxPayload: 800 * 1024 * 1024 }); ws.on('open', () => res(ws)); ws.on('error', e => rej(e)); setTimeout(() => rej(new Error('WS timeout')), 15000); }); }
function cdpSend(ws, method, params, timeoutMs) {
    params = params || {}; timeoutMs = timeoutMs || 600000;
    return new Promise((res, rej) => {
        const id = Math.floor(Math.random() * 999999);
        const t = setTimeout(() => rej(new Error(method + ' timeout')), timeoutMs);
        const h = (data) => { const m = JSON.parse(data.toString()); if (m.id === id) { clearTimeout(t); ws.removeListener('message', h); m.error ? rej(new Error(method + ': ' + JSON.stringify(m.error))) : res(m.result); } };
        ws.on('message', h); ws.send(JSON.stringify({ id: id, method: method, params: params }));
    });
}
async function pageEval(ws, expression) { const r = await cdpSend(ws, 'Runtime.evaluate', { expression: expression, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error('Eval: ' + JSON.stringify(r.exceptionDetails).slice(0, 300)); return r.result.value; }

async function main() {
    if (!LIST || !OUT) { console.error('usage: node cdp-batch-fetch.js <port> <list.json> <outDir> [batchSize] [concurrency]'); process.exit(1); }
    fs.mkdirSync(OUT, { recursive: true });
    const all = JSON.parse(fs.readFileSync(LIST, 'utf8'));
    let todo = all.filter(f => !fs.existsSync(path.join(OUT, path.basename(f))));
    console.log('remaining:', todo.length, '/', all.length);
    if (!todo.length) { console.log('ALL DONE'); return; }

    const bi = await httpGet('/json/version');
    const bw = await wsConnect(bi.webSocketDebuggerUrl);
    const targets = (await cdpSend(bw, 'Target.getTargets')).targetInfos;
    const pt = targets.find(t => t.type === 'page' && /^https?:/.test(t.url || '')) || targets.find(t => t.type === 'page');
    if (!pt) { console.error('no usable page target — open the target site in this browser first'); process.exit(1); }
    const tw = await wsConnect('ws://127.0.0.1:' + PORT + '/devtools/page/' + pt.targetId);
    await cdpSend(tw, 'Runtime.enable');

    while (todo.length) {
        const chunk = todo.slice(0, BATCH);
        const expr = '(async function(){ var files = ' + JSON.stringify(chunk) + '; var out = []; var i = 0; '
            + 'async function worker(){ while (i < files.length) { var f = files[i++]; '
            + 'try { var r = await fetch(f, {credentials:"include"}); out.push({f: f, status: r.status, text: await r.text()}); } '
            + 'catch (e) { out.push({f: f, status: -1, err: String(e).slice(0, 200)}); } } } '
            + 'await Promise.all(Array.from({length: ' + CONC + '}, worker)); return out; })()';
        const results = await pageEval(tw, expr);
        let ok = 0; const fail = [];
        for (const r of results) {
            if (r.status === 200 && r.text && r.text.length > 100) { fs.writeFileSync(path.join(OUT, path.basename(r.f)), r.text, 'utf8'); ok++; }
            else fail.push(r.f + ':' + r.status);
        }
        console.log('batch ok:', ok, 'failed:', fail.length, fail.slice(0, 5).join(' | '));
        const before = todo.length;
        todo = all.filter(f => !fs.existsSync(path.join(OUT, path.basename(f))));
        if (todo.length >= before) { console.error('no progress in last batch; aborting'); break; }
        console.log('still remaining:', todo.length);
    }
    tw.close(); bw.close();
}

main().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
