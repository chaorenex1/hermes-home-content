const WebSocket = require("ws");

// Usage: node scripts/extract-one-article.js <pageWsUrl> <articleUrl>
// Extracts a single Nexus article's title and body via CDP.

const pageWsUrl = process.argv[2];
const articleUrl = process.argv[3];

if (!pageWsUrl || !articleUrl) {
  console.error("Usage: node extract-one-article.js <pageWsUrl> <articleUrl>");
  console.error("Example: node extract-one-article.js ws://127.0.0.1:9222/devtools/page/ABC123 https://www.nexusmods.com/skyrimspecialedition/articles/6085");
  process.exit(1);
}

const ws = new WebSocket(pageWsUrl);
let msgId = 0;

function send(id, method, params) {
  ws.send(JSON.stringify({ id, method, params }));
}

ws.on("open", () => {
  send(++msgId, "Page.navigate", { url: articleUrl });

  setTimeout(() => {
    send(++msgId, "Runtime.evaluate", {
      expression: "(function(){ var article = document.querySelector('#mainContent article'); var pageTitle = document.querySelector('#pagetitle h1') || document.querySelector('h1'); var title = pageTitle ? pageTitle.innerText.trim() : document.title; var content = article ? article.innerText : 'NO_ARTICLE'; return JSON.stringify({title: title, url: window.location.href, content: content.substring(0, 30000)}); })()",
      returnByValue: true
    });
  }, 10000);
});

ws.on("message", (data) => {
  try {
    const resp = JSON.parse(data.toString());
    if (resp.result && resp.result.result && resp.result.result.value) {
      console.log(resp.result.result.value);
      setTimeout(() => { ws.close(); process.exit(0); }, 500);
    } else if (resp.error) {
      console.error("CDP_ERROR:", JSON.stringify(resp.error));
      setTimeout(() => { ws.close(); process.exit(1); }, 500);
    }
  } catch(e) { }
});

setTimeout(() => { console.log("TIMEOUT"); process.exit(1); }, 25000);
