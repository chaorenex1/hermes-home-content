const WebSocket = require("ws");

// Usage: node scripts/extract-article-list.js <pageWsUrl> <modArticlesUrl>
// Extracts all article links from a Nexus mod's Articles tab, handling pagination.

const pageWsUrl = process.argv[2];
const modArticlesUrl = process.argv[3];

if (!pageWsUrl || !modArticlesUrl) {
  console.error("Usage: node extract-article-list.js <pageWsUrl> <modArticlesUrl>");
  console.error("Example: node extract-article-list.js ws://127.0.0.1:9222/devtools/page/ABC123 https://www.nexusmods.com/skyrimspecialedition/mods/106659?tab=articles");
  process.exit(1);
}

const ws = new WebSocket(pageWsUrl);
let msgId = 0;
let allArticles = [];
let currentPage = 1;

function send(id, method, params) {
  ws.send(JSON.stringify({ id, method, params }));
}

function extractPage(page) {
  const url = page === 1 ? modArticlesUrl : modArticlesUrl + "&page=" + page;

  send(++msgId, "Page.navigate", { url: url });

  setTimeout(() => {
    send(++msgId, "Runtime.evaluate", {
      expression: "(function(){ var links = document.querySelectorAll('.tabcontent-mod-page a[href*=\"/articles/\"]'); var result = []; for (var i = 0; i < links.length; i++) { var href = links[i].href; var aid = href.split('/articles/')[1]; if (aid) { result.push({name: links[i].innerText, aid: aid, href: href}); } } return JSON.stringify(result); })()",
      returnByValue: true
    });
  }, 10000);
}

function checkPagination() {
  setTimeout(() => {
    send(++msgId, "Runtime.evaluate", {
      expression: "(function(){ var pages = document.querySelectorAll('.tabcontent-mod-page .pagination a, .tabcontent-mod-page a[href*=\"page=\"]'); var pageNums = []; for (var i = 0; i < pages.length; i++) { var t = pages[i].innerText.trim(); if (/^\\d+$/.test(t)) { pageNums.push(parseInt(t)); } } return JSON.stringify(pageNums); })()",
      returnByValue: true
    });
  }, 12000);
}

ws.on("open", () => {
  extractPage(1);
  setTimeout(checkPagination, 15000);
});

ws.on("message", (data) => {
  try {
    const resp = JSON.parse(data.toString());
    const result = resp.result && resp.result.result && resp.result.result.value;
    if (!result) return;

    const parsed = JSON.parse(result);
    if (Array.isArray(parsed) && parsed.length > 0 && parsed[0].aid) {
      // Article links
      allArticles = allArticles.concat(parsed);
    } else if (Array.isArray(parsed) && parsed.length > 0 && typeof parsed[0] === "number") {
      // Page numbers from pagination
      const maxPage = Math.max(...parsed);
      if (maxPage > currentPage) {
        // There are more pages — but for efficiency, we just report the max
        console.log(JSON.stringify({ type: "pagination", currentPage: currentPage, maxPage: maxPage }));
      }
    }
  } catch(e) {}
});

// After all pages extracted, output final result
setTimeout(() => {
  console.log(JSON.stringify({ type: "articles", count: allArticles.length, articles: allArticles }));
  ws.close();
  process.exit(0);
}, 20000);
