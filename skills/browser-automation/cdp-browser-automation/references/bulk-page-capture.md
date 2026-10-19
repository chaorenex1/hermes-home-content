# 反爬门后的批量页面捕获（Cloudflare / SPA 站点）

场景：web_fetch / curl 得到 403 + `Just a moment...` / `请稍候…`；站点是 SPA，正文由 JS 渲染或按需加载。

## 1. 过挑战
- 用独立 profile 的真实 Edge 实例（不碰用户日常浏览器）：
  `"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --user-data-dir="<PATH_TO_BROWSER_PROFILE>"`
  起好后先 `curl -s http://127.0.0.1:9222/json/version` 确认就绪。
- 打开目标 URL，轮询等待通过（不要固定 sleep）：

```javascript
let title = '';
for (let i = 0; i < 40; i++) {
    await sleep(2000);
    title = await pageEval(tw, 'document.title');
    const rs = await pageEval(tw, 'document.readyState');
    if (title && !/Just a moment|请稍候/i.test(title) && rs !== 'loading' && i >= 2) break;
}
```

- 通过后，同一浏览器上下文内的 fetch / 导航不再触发挑战；后续抓取复用同一标签页。

## 2. 逆向子页 URL 规律
- `document.querySelectorAll('[onclick]')` → 正则 `loadfile\('([^']+)'\)`（或站点自己的路由函数），得到内容片段文件名与层级。
- 或收 `querySelectorAll('a')` 的 href。
- 内容渲染在 iframe 时：直接抓 iframe 的片段 URL —— 片段通常是含 <head> 的完整 HTML，可直接解析。
- SPA 片段文件名常含压缩层级（如 `tutorial-13-41001.html` = 13-4-10-01）；从 TOC 提取全量清单后再抓。

## 3. 批量 fetch + 断点续抓
在已过挑战的页面上下文里并发执行：

```javascript
const expr = `(async function(){
    var files = ${JSON.stringify(chunk)};
    var out = []; var i = 0;
    async function worker(){
      while (i < files.length) {
        var f = files[i++];
        var r = await fetch(f, {credentials:'include'});
        out.push({f: f, status: r.status, text: await r.text()});
      }
    }
    await Promise.all([worker(), worker(), worker(), worker()]);
    return out;
})()`;
```

- 批大小 32、并发 4 实测稳定（244 个子页 4 次调用抓完；逐页导航需数十分钟）。
- `new WebSocket(url, {maxPayload: 800*1024*1024})`，避免数百 KB 的页面被截断。
- 结果在 Node 侧按 basename 落盘；每次循环过滤已存在文件 → 天然断点续抓。
- 若某一轮 todo 数量不下降立即中止，避免死循环。
- 现成脚本：`scripts/cdp-batch-fetch.js`（用法 `node cdp-batch-fetch.js <port> <list.json> <outDir> [batch=32] [conc=4]`）。

## 4. HTML 片段 → 可读文本
- `<pre>` 内的换行由 `<br/>` 表示：先 `for br: br.replace_with('\n')` 再 `get_text()`。
- 双语站点常见成对节点（如 `class="DE_eng"` / `DE_zh_cn`）——按需保留一种。
- 先删除 script/style/ins/iframe/广告 div/语言选择器，再抽取正文。
- 图片保留 `[img:文件名]` 占位；代码块用围栏（```）保留原文，不要改写标签/属性名。
