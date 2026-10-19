# browser_console 表达式集（Nexus Mods）

所有表达式通过 `browser_console(expression="...")` 在**当前页面**执行，返回 JSON 可序列化的值。
调用前必须先用 `browser_navigate` 打开目标 URL。

约定：

- `{d}` = 当前 game_domain（如 `skyrimspecialedition`），`{id}` = MOD ID。
- 表达式自包含：不依赖页面全局变量（除 Nexus 自身的 `RH_*` 函数）。
- 表达式可直接返回 Promise，工具会等待 resolve（已实测）。等待用 `S2`。
- 结构在 2026-10-18 对线上页面实测；站点改版后优先重跑对应表达式核对。

---

## S1 登录状态

判断依据（2026-10-18 实测）：访客页面也会渲染头像/账户菜单，**不能**用 `.avatar` / `.account-menu` 判断；首页未展开菜单时 DOM 里根本没有登录链接。最可靠的信号是 `/users/myaccount` 的 HTTP 状态：访客返回 **401**，登录返回 **200**。

```js
fetch('https://www.nexusmods.com/users/myaccount', { redirect: 'manual', credentials: 'include' })
  .then(function (r) {
    var signIn = document.querySelector('a[href*="auth/sign_in"]');
    var guestMenu = document.querySelector('a[href="/users/0"]');
    return {
      loggedIn: r.status === 200,
      status: r.status,
      signInLink: !!signIn,
      guestMenu: !!guestMenu,
      url: location.href
    };
  })
  .catch(function (e) {
    return { loggedIn: false, error: String(e), url: location.href };
  })
```

返回 Promise，`browser_console` 会等待 resolve。`signInLink` / `guestMenu` 只是辅助证据，不要单独当判据。

## S2 等待元素（页内轮询）

`browser_navigate` 返回后 Next.js 仍在渲染。用页内 Promise 轮询，比外部 sleep 稳。
`selector` 与 `timeout` 直接改字面量。超时上限建议 25000（browser 命令超时 30s）。

```js
new Promise(function (resolve) {
  var t0 = Date.now();
  var sel = '.mods-grid';
  var timeout = 20000;
  (function poll() {
    var el = document.querySelector(sel);
    if (el) return resolve({ ok: true, ms: Date.now() - t0 });
    if (Date.now() - t0 > timeout) return resolve({ ok: false, ms: Date.now() - t0 });
    setTimeout(poll, 300);
  })();
})
```

## S3 MOD 列表提取（Trending / 搜索共用）

页面：`/games/{d}/mods?sort=endorsements&timeRange=7&page=N` 或 `/games/{d}/mods?keyword=...`

```js
(function () {
  var mods = [];
  var grid = document.querySelector('.mods-grid');
  if (!grid) return { error: 'mods-grid not found', url: location.href, mods: [] };

  var tiles = grid.children;
  for (var i = 0; i < tiles.length; i++) {
    var tile = tiles[i];
    var titleEl = tile.querySelector('[data-e2eid="mod-tile-title"]');
    if (!titleEl) continue;

    var authorEl = tile.querySelector('[data-e2eid="user-link"]');
    var imgEl = tile.querySelector('img');
    var categoryEl = tile.querySelector('a[href*="categoryName"]');
    var timeEl = tile.querySelector('time');

    var href = titleEl.getAttribute('href') || '';
    var idMatch = href.match(/\/mods\/(\d+)/);
    var name = titleEl.textContent.trim();

    var allText = tile.innerText.split(String.fromCharCode(10));
    var endorsements = 'N/A', downloads = 'N/A', fileSize = 'N/A';
    var description = '', isAdult = false;

    for (var j = 0; j < allText.length; j++) {
      var text = allText[j].trim();
      if (text === 'Adult' || text.slice(-5) === 'Adult') { isAdult = true; continue; }
      if (text === 'Endorsements' && j + 1 < allText.length) { endorsements = allText[j + 1].trim(); j++; continue; }
      if (text === 'Downloads' && j + 1 < allText.length) { downloads = allText[j + 1].trim(); j++; continue; }
      if (text === 'File size' && j + 1 < allText.length) { fileSize = allText[j + 1].trim(); j++; continue; }
      if (text.length > 10 && j > 3 && j < allText.length - 4 &&
          text !== name && text !== endorsements && text !== downloads) {
        description = text;
      }
    }

    mods.push({
      id: idMatch ? idMatch[1] : 'unknown',
      name: name,
      author: authorEl ? authorEl.textContent.trim() : 'Unknown',
      category: categoryEl ? categoryEl.textContent.trim() : 'Unknown',
      uploadTime: timeEl ? timeEl.textContent.trim() : 'Unknown',
      uploadDate: timeEl ? timeEl.getAttribute('datetime') : 'Unknown',
      description: description,
      endorsements: endorsements,
      downloads: downloads,
      fileSize: fileSize,
      isAdult: isAdult,
      thumbnail: imgEl ? imgEl.src : null,
      url: href.indexOf('http') === 0 ? href : 'https://www.nexusmods.com' + href
    });
  }
  return { mods: mods, count: mods.length, url: location.href };
})()
```

翻页：改 URL 的 `&page=N`（每页 20 条），不要点分页按钮。

## S4 MOD 详情

页面：`/{d}/mods/{id}`

⚠️ 页面里存在**隐藏的**「Please log in」模态，它的 `h1` 排在真实标题之前。必须用 `#pagetitle h1`。

```js
(function () {
  var titleEl = document.querySelector('#pagetitle h1') || document.querySelector('h1');
  var out = {
    pageTitle: titleEl ? titleEl.textContent.trim() : 'Unknown',
    version: 'Unknown', uploaded: 'Unknown', updated: 'Unknown',
    author: 'Unknown', uploader: 'Unknown',
    endorsements: 'N/A', uniqueDls: 'N/A', totalDls: 'N/A', totalViews: 'N/A',
    summary: '', isDownloaded: false, lastDownloaded: null
  };

  var hist = document.querySelector('.modhistory');
  if (hist) {
    var m = hist.textContent.trim().match(/You last downloaded a file from this mod on (.+)/);
    if (m) { out.isDownloaded = true; out.lastDownloaded = m[1]; }
  }

  var lines = document.body.innerText.split(String.fromCharCode(10));
  var keys = {
    'Version': 'version', 'Original upload': 'uploaded', 'Last updated': 'updated',
    'Created by': 'author', 'Uploaded by': 'uploader', 'Endorsements': 'endorsements',
    'Unique DLs': 'uniqueDls', 'Total DLs': 'totalDls', 'Total views': 'totalViews'
  };
  for (var i = 0; i < lines.length; i++) {
    var key = lines[i].trim();
    if (keys[key] && i + 1 < lines.length) out[keys[key]] = lines[i + 1].trim();
  }

  var about = document.querySelector('h2');
  var heads = document.querySelectorAll('h2');
  for (var h = 0; h < heads.length; h++) {
    if (heads[h].textContent.indexOf('About this mod') !== -1) {
      var ps = heads[h].parentElement.querySelectorAll('p');
      for (var p = 0; p < ps.length; p++) {
        var t = ps[p].textContent.trim();
        if (t.length > 10) { out.summary = t.slice(0, 1000); break; }
      }
      break;
    }
  }

  // 操作按钮存在性（登录后才有；访客为 false）
  var act = {};
  ['track', 'untrack', 'endorse', 'unendorse', 'vote', 'novote'].forEach(function (k) {
    act[k] = !!document.querySelector('li[id^="action-' + k + '-"]');
  });
  out.actionButtons = act;
  return out;
})()
```

## S5 Track / Endorse / Vote

状态判定 + 需要点击的目标，同一表达式返回。`kind` 取 `track` | `endorse` | `vote`，`mode` 取 `on`（只做正向）或 `toggle`。

```js
(function () {
  var kind = 'track', mode = 'on';
  var pairs = { track: ['track', 'untrack'], endorse: ['endorse', 'unendorse'], vote: ['vote', 'novote'] };
  var p = pairs[kind];
  function visible(sel) {
    var li = document.querySelector('li[id^="action-' + sel + '-"]');
    if (!li) return null;
    if (getComputedStyle(li).display === 'none') return null;
    var a = li.querySelector('a');
    return a ? a.textContent.trim() : null;
  }
  var on = visible(p[0]);   // Track / Endorse / Vote
  var off = visible(p[1]);  // Tracking / Endorsed / Voted
  var state = off ? 'active' : (on ? 'inactive' : 'not_found');
  var action = 'none';
  if (state === 'inactive') action = 'click_' + p[0];
  if (state === 'active' && mode === 'toggle') action = 'click_' + p[1];
  return { kind: kind, state: state, action: action, onText: on, offText: off };
})()
```

执行点击：`browser_click` 需要 ref。用 `browser_snapshot` 找 `li[id^="action-track-"]` 里的链接 ref（snapshot 中显示为 Track / Endorse / Vote 链接），点完后 `browser_navigate` 同一 URL 重新加载，再跑一次本表达式验证 `state` 是否翻转为 `active`。

已验证事实：`Input.dispatchMouseEvent`（旧 CDP 方案）不是必需的；`browser_click` 走真实输入事件，React 会收到。

## S6 标签

页面：`/{d}/mods/{id}`

```js
(function () {
  var tags = [].slice.call(document.querySelectorAll('ul.tags li a')).map(function (a) {
    var label = a.querySelector('.flex-label');
    var href = a.getAttribute('href') || '';
    return {
      name: label ? label.textContent.trim() : a.textContent.trim(),
      url: href.indexOf('http') === 0 ? href : 'https://www.nexusmods.com' + href
    };
  }).filter(function (t) { return t.name; });
  return { tags: tags };
})()
```

## S7 Gallery

```js
(function () {
  var gallery = [].slice.call(document.querySelectorAll('ul.thumbgallery li.thumb')).map(function (li) {
    var img = li.querySelector('img');
    return {
      type: 'image',
      url: li.getAttribute('data-src') || (img ? img.src : null),
      thumbnail: li.getAttribute('data-exthumbimage') || (img ? img.src : null)
    };
  }).filter(function (g) { return g.url; });

  var videos = [].slice.call(document.querySelectorAll('.gallery-video, iframe[src*="youtube"]'))
    .map(function (v) { return { type: 'video', url: v.src || v.getAttribute('data-src') }; });

  return { gallery: gallery.concat(videos) };
})()
```

## S8 Description 折叠区（dl.accordion）

页面：`/{d}/mods/{id}?tab=description`（或详情页默认 tab，页面已有 `dl.accordion`）

```js
(function () {
  var result = { accordion: {}, rawText: '' };
  var box = document.querySelector('div.tabcontent.tabcontent-mod-page[aria-live="assertive"]') ||
            document.querySelector('#description, .tab-description, .mod-description');
  if (box) result.rawText = box.innerText.slice(0, 10000);

  var dl = document.querySelector('dl.accordion');
  if (!dl) return result;

  var dts = dl.querySelectorAll('dt');
  for (var i = 0; i < dts.length; i++) {
    var dt = dts[i];
    var dd = dt.nextElementSibling;
    if (!dd || dd.tagName !== 'DD') continue;

    var heading = dt.textContent.trim();
    var entry = {
      heading: heading,
      isOpen: dd.style.display !== 'none' && !dd.classList.contains('hidden'),
      text: dd.textContent.trim().slice(0, 3000)
    };

    var req = dd.querySelector('main-file-requirements');
    if (req) {
      var raw = req.getAttribute('download-links');
      if (raw) { try { entry.requirements = JSON.parse(raw); } catch (e) { entry.requirementsRaw = raw.slice(0, 2000); } }
    }

    var tables = dd.querySelectorAll('table');
    if (tables.length) {
      entry.tables = [];
      for (var t = 0; t < tables.length; t++) {
        var rows = tables[t].querySelectorAll('tr'), table = [];
        for (var r = 0; r < rows.length; r++) {
          var cells = rows[r].querySelectorAll('td, th'), row = [];
          for (var c = 0; c < cells.length; c++) {
            var link = cells[c].querySelector('a[href*="/mods/"]');
            var text = cells[c].textContent.trim();
            if (link) {
              var m = (link.getAttribute('href') || '').match(/\/mods\/(\d+)/);
              row.push({
                text: text,
                modName: link.textContent.trim(),
                modId: m ? m[1] : null,
                modUrl: link.href
              });
            } else row.push(text);
          }
          table.push(row);
        }
        entry.tables.push(table);
      }
    }

    var lists = dd.querySelectorAll('ul, ol');
    if (lists.length) {
      entry.lists = [];
      for (var l = 0; l < lists.length; l++) {
        entry.lists.push([].slice.call(lists[l].querySelectorAll('li')).map(function (li) {
          return li.textContent.trim();
        }));
      }
    }

    result.accordion[heading] = entry;
  }
  return result;
})()
```

`usedBy` 是懒加载，折叠区里只有标题和数量。完整列表走 API（页面内 fetch，带登录 cookie）：

```js
fetch('/api/games/' + gameId + '/mods/' + modId + '/required-by?show_adult_content=1')
  .then(function (r) { return r.text(); })
  .then(function (html) { return { status: 'ok', html: html.slice(0, 20000) }; })
```

`gameId` 从页面取：`(location.href.match(/\/games\/(\d+)/) || [])[1]`；拿不到时从 `<script>` 文本里搜 `gameId`。返回 HTML 表格，解析 `<tr>` 里的 `<a>`。

旧版按关键词用正则切分 `sections` 的做法已移除：折叠区本身就是结构化的，切分只会在多语言标题下产生重复内容。

## S9 Files 列表

页面：`/{d}/mods/{id}?tab=files`

站点已改版（2026-10-18 实测）：
- 自定义元素是 `mod-download-modal`（不是 `download-modal`），下载按钮渲染在它的 **shadow root** 里，页面 JS 查不到，只有 `browser_snapshot` 能看到。
- `file` 属性是 JSON：`{name, uid, category, downloadUrl, vortexDownloadUrl}`；`dependencies` / `requirements` 属性是 JSON 数组。
- `ul.stats` 的 class 变为 `stat-filesize` / `stat-uniquedls` / `stat-totaldls` / `stat-version`。
- ⚠️ `show-vortex-button` 的取值不可靠：同一页面上既读到过 `"false"` 又解析出 `true`。**可用性判断以 snapshot 里是否出现 `Mod manager download` / `Manual download` 按钮为准**，`hasModManager`/`hasManual` 只作参考。

```js
(function () {
  var root = document.getElementById('mod_files');
  if (!root) return { error: 'mod_files not found', url: location.href };

  function parseFiles(container) {
    if (!container) return [];
    var out = [];
    var dts = container.querySelectorAll('dt.file-expander-header');
    for (var i = 0; i < dts.length; i++) {
      var dt = dts[i];
      var dd = dt.nextElementSibling;
      if (!dd || dd.tagName !== 'DD') continue;

      var stats = {};
      var items = dt.querySelectorAll('ul.stats li');
      for (var s = 0; s < items.length; s++) {
        stats[items[s].className] = items[s].textContent.trim().replace(/\s+/g, ' ');
      }

      var modal = dd.querySelector('mod-download-modal');
      var file = null, dependencies = [], requirements = [];
      if (modal) {
        try { file = JSON.parse(modal.getAttribute('file') || 'null'); } catch (e) {}
        try { dependencies = JSON.parse(modal.getAttribute('dependencies') || '[]'); } catch (e) {}
        try { requirements = JSON.parse(modal.getAttribute('requirements') || '[]'); } catch (e) {}
      }

      var descEl = dd.querySelector('.files-description');

      out.push({
        id: dt.getAttribute('data-id'),
        name: dt.getAttribute('data-name'),
        version: dt.getAttribute('data-version'),
        sizeKB: dt.getAttribute('data-size'),
        uploadedEpoch: dt.getAttribute('data-date'),
        dependenciesCount: dt.getAttribute('data-dependencies-count'),
        uploaded: stats['stat-uploaddate'] || null,
        fileSize: stats['stat-filesize'] || null,
        uniqueDownloads: stats['stat-uniquedls'] || null,
        totalDownloads: stats['stat-totaldls'] || null,
        description: descEl ? descEl.textContent.trim() : '',
        hasModManager: !!modal && modal.getAttribute('show-vortex-button') === 'true',
        hasManual: !!modal,
        isPremium: !!modal && modal.getAttribute('is-premium') === 'true',
        fileUid: file ? file.uid : null,
        downloadUrl: file ? file.downloadUrl : null,
        vortexDownloadUrl: file ? file.vortexDownloadUrl : null,
        dependencies: dependencies,
        requirements: requirements
      });
    }
    return out;
  }

  return {
    mainFiles: parseFiles(document.getElementById('file-container-main-files')),
    optionalFiles: parseFiles(document.getElementById('file-container-optional-files')),
    oldFiles: parseFiles(document.getElementById('file-container-old-files'))
  };
})()
```

## S10 POSTS 评论

页面：`/{d}/mods/{id}?tab=posts`

```js
(function () {
  var keyword = '', page = '1';
  var root = document.getElementById('comment-container') ||
             document.querySelector('div.tabcontent-mod-page[aria-live="assertive"]');
  if (!root) return { error: 'comment-container not found', posts: [] };

  function extract(c) {
    var authorEl = c.querySelector('.comment-name a');
    var imgEl = c.querySelector('.comment-user img');
    var timeEl = c.querySelector('time');
    var textEl = c.querySelector('.comment-content-text');

    var content = '';
    if (textEl) {
      var clone = textEl.cloneNode(true);
      var brs = clone.querySelectorAll('br');
      for (var b = 0; b < brs.length; b++) brs[b].replaceWith('\n');
      content = clone.textContent.trim();
    } else {
      var cc = c.querySelector('.comment-content');
      if (cc) content = cc.textContent.trim();
    }

    var kudos = '0';
    var details = c.querySelectorAll('.comment-details ul li');
    for (var d = 0; d < details.length; d++) {
      var km = details[d].textContent.match(/(\d+)\s*kudos/i);
      if (km) { kudos = km[1]; break; }
    }

    var kids = c.querySelector('ol.comment-kids, .comment-replies, .replies');
    var nested = [];
    if (kids) {
      var ns = kids.querySelectorAll('li.comment');
      for (var n = 0; n < ns.length; n++) nested.push(extract(ns[n]));
    }

    return {
      id: c.id || '',
      author: authorEl ? authorEl.textContent.trim() : (imgEl ? (imgEl.getAttribute('title') || '').trim() : 'Unknown'),
      profileUrl: authorEl ? authorEl.href : '',
      avatarUrl: imgEl ? imgEl.src : '',
      date: timeEl ? timeEl.textContent.trim() : '',
      dateEpoch: timeEl ? timeEl.getAttribute('data-date') : null,
      content: content.slice(0, 2000),
      kudos: kudos,
      isSticky: c.classList.contains('comment-sticky'),
      replies: String(nested.length),
      nestedReplies: nested
    };
  }

  var posts = [];
  var all = root.querySelectorAll('li.comment');
  for (var i = 0; i < all.length; i++) {
    // 只取顶层：父级不是 li.comment
    var p = all[i].parentElement;
    if (p && p.closest('li.comment')) continue;
    posts.push(extract(all[i]));
  }

  if (keyword) {
    var kw = keyword.toLowerCase();
    posts = posts.filter(function (p) {
      return p.content.toLowerCase().indexOf(kw) !== -1 || p.author.toLowerCase().indexOf(kw) !== -1;
    });
  }

  var pages = [];
  var links = document.querySelectorAll('.pagination a');
  for (var k = 0; k < links.length; k++) {
    var onclick = links[k].getAttribute('onclick') || '';
    var m = onclick.match(/Send\('page',\s*'(\d+)'\)/) || (links[k].getAttribute('href') || '').match(/[?&]page=(\d+)/);
    if (m && pages.indexOf(m[1]) === -1) pages.push(m[1]);
  }

  return { posts: posts, count: posts.length, keyword: keyword, page: page, pagination: pages };
})()
```

翻页：URL 的 `?page=N` 不生效，必须调用页内 AJAX：

```js
(function () {
  if (window.RH_CommentContainer && window.RH_CommentContainer.Send) {
    window.RH_CommentContainer.Send('page', '2');
    return { sent: true };
  }
  return { sent: false };
})()
```

调用后用 `S2` 等 `li.comment` 重新出现，再跑提取。

## S11 BUGS 列表

页面：`/{d}/mods/{id}?tab=bugs`

```js
(function () {
  var keyword = '';
  var out = [];
  var rows = document.querySelectorAll('tr[data-issue-id]');

  for (var i = 0; i < rows.length; i++) {
    var row = rows[i];
    var titleEl = row.querySelector('a.issue-title');
    var statusEl = row.querySelector('td.table-bug-status span');
    var cells = row.querySelectorAll('td');
    var title = titleEl ? titleEl.textContent.trim() : (cells[0] ? cells[0].textContent.trim() : '');
    if (!title) continue;
    if (keyword && title.toLowerCase().indexOf(keyword.toLowerCase()) === -1) continue;

    out.push({
      id: row.getAttribute('data-issue-id') || row.id.replace('issue_', ''),
      title: title,
      status: statusEl ? statusEl.textContent.trim() : (cells[1] ? cells[1].textContent.trim() : ''),
      replies: cells[2] ? cells[2].textContent.trim() : '0',
      version: cells[3] ? cells[3].textContent.trim() : '',
      priority: cells[4] ? cells[4].textContent.trim() : '',
      lastPost: cells[5] ? cells[5].textContent.trim() : '',
      url: null
    });
  }
  return { bugs: out, count: out.length, keyword: keyword };
})()
```

标题链接的 `href` 是 `javascript:;`，不要当 URL 用（因此固定 `url: null`）。

## S12 BUG 评论详情

先跑 S11 拿到 `id` 与 `replies`，对 `replies > 0` 的逐个展开：

```js
(function () {
  var id = 1096938;
  if (typeof window.loadIssueReplies === 'function') {
    window.loadIssueReplies(id);
    return { loaded: true, id: id };
  }
  return { loaded: false, id: id };
})()
```

等待 2–3 秒（或轮询 `td#mainissue_{id} li.comment`），再提取：

```js
(function () {
  var id = 1096938;
  var host = document.getElementById('mainissue_' + id);
  if (!host) return { id: id, comments: [] };

  var out = [];
  var items = host.querySelectorAll('li.comment');
  for (var i = 0; i < items.length; i++) {
    var li = items[i];
    var authorEl = li.querySelector('.comment-name a');
    var imgEl = li.querySelector('.comment-user img');
    var timeEl = li.querySelector('.comment-content time');
    var statusEl = li.querySelector('.status-premium, .status-supporter, .status-staff, .status-moderator');
    var contentEl = li.querySelector('.comment-content');
    var content = '';
    if (contentEl) {
      var clone = contentEl.cloneNode(true);
      var drop = clone.querySelectorAll('time, .comment-reply');
      for (var d = 0; d < drop.length; d++) drop[d].remove();
      content = clone.textContent.trim();
    }
    out.push({
      author: authorEl ? authorEl.textContent.trim() : '',
      profileUrl: authorEl ? authorEl.href : '',
      avatarUrl: imgEl ? imgEl.src : '',
      date: timeEl ? timeEl.textContent.trim() : '',
      dateAttr: timeEl ? timeEl.getAttribute('datetime') : '',
      userStatus: statusEl ? statusEl.textContent.trim() : 'member',
      content: content.slice(0, 3000)
    });
  }
  return { id: id, comments: out };
})()
```

## S13 发表评论（写操作）

页面：`/{d}/mods/{id}?tab=posts`

1. 用 `S2` 等 `#add-comment-form-0`。
2. 写入内容（WYSIWYG 需要事件同步）：

```js
(function () {
  var content = '写在这里';
  var ta = document.getElementById('add-comment-post-0');
  if (ta) {
    ta.value = content;
    ta.dispatchEvent(new Event('input', { bubbles: true }));
    ta.dispatchEvent(new Event('change', { bubbles: true }));
  }
  var ce = document.querySelector('#add-comment-form-0 .wysibb-body');
  if (ce) {
    ce.innerHTML = content.replace(/</g, '&lt;').replace(/\n/g, '<br>');
    ce.dispatchEvent(new Event('input', { bubbles: true }));
  }
  return { filled: !!ta || !!ce, length: content.length };
})()
```

3. `browser_snapshot` 找到 `A#submit-add-comment-0`（文本 Submit）→ `browser_click`。
4. 3 秒后检查结果：

```js
(function () {
  var errBox = document.getElementById('add-comment-error-box-0');
  var errMsg = document.getElementById('add-comment-error-message-0');
  var visible = errBox && getComputedStyle(errBox).display !== 'none';
  return { posted: !visible, error: visible && errMsg ? errMsg.textContent.trim() : null };
})()
```

限制：5000 字符；CSRF token 在 `#submit-add-comment-0` 的 `data-csrf-token` 里，不需要手动处理。

## S14 Tracking Centre

页面：`/{d}/mods/trackingcentre?tab=mods`
（实测正确路径；带 `/games/` 前缀的形式不可用）

```js
(function () {
  var query = '';
  var out = [];
  var table = document.querySelector('table.mod-tracking-table');
  if (!table) return { error: 'tracking table not found', mods: [], url: location.href };

  var kw = query.toLowerCase();
  var rows = table.querySelectorAll('tbody tr');
  for (var i = 0; i < rows.length; i++) {
    var cells = rows[i].querySelectorAll('td');
    if (cells.length < 9) continue;

    var link = cells[0].querySelector('a[href*="/mods/"]');
    var name = link ? link.textContent.trim() : cells[0].textContent.trim();
    if (!name) continue;
    if (kw && (name + ' ' + cells[2].textContent + ' ' + cells[3].textContent).toLowerCase().indexOf(kw) === -1) continue;

    var m = link ? link.href.match(/\/mods\/(\d+)/) : null;
    var btn = cells[8].querySelector('.toggle-track-mod');

    out.push({
      name: name,
      id: m ? m[1] : '',
      author: cells[2].textContent.trim(),
      category: cells[3].textContent.trim(),
      version: cells[4].textContent.trim(),
      lastUpload: cells[5].textContent.trim(),
      lastDownload: cells[6].textContent.trim(),
      isTracked: btn ? btn.getAttribute('data-do-track') === '0' : false,
      trackingStatus: cells[8].textContent.trim(),
      url: link ? link.href : ''
    });
  }

  var pages = [];
  var pag = document.querySelectorAll('.pagination a[onclick*="Send"]');
  for (var p = 0; p < pag.length; p++) {
    var t = pag[p].textContent.trim();
    if (t && !isNaN(parseInt(t, 10))) pages.push(t);
  }

  var current = document.querySelector('.pagination .page-selected');
  return { mods: out, count: out.length, page: current ? current.textContent.trim() : '1', pagination: pages, query: query };
})()
```

翻页 / 取消追踪：

```js
// 翻页
(function () { if (window.RH_TrackedModsTab && window.RH_TrackedModsTab.Send) { window.RH_TrackedModsTab.Send('page', '2'); return { sent: true }; } return { sent: false }; })()

// 取消追踪（data-mod-id 处填 MOD ID）
(function () {
  var el = document.querySelector('.toggle-track-mod[data-mod-id="151502"]');
  if (!el) return { found: false };
  el.scrollIntoView({ block: 'center' });
  var r = el.getBoundingClientRect();
  return { found: true, doTrack: el.getAttribute('data-do-track'), x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) };
})()
```

拿到坐标后优先用 `browser_snapshot` 找同一链接的 ref 再 `browser_click`；没有 ref 时用坐标点击。

## S15 Download History

页面：`/{d}/users/myaccount?tab=download+history`（站点菜单里的实际链接）

搜索（DataTables 内置）：

```js
(function () {
  var input = document.querySelector('input[aria-controls="DataTables_Table_0"]');
  if (!input) return { found: false };
  input.focus();
  input.value = 'skyui';
  input.dispatchEvent(new Event('input', { bubbles: true }));
  input.dispatchEvent(new Event('change', { bubbles: true }));
  input.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', bubbles: true }));
  return { found: true };
})()
```

翻页（`data-dt-idx`）：

```js
(function () { var b = document.querySelector('.paginate_button[data-dt-idx="3"]'); if (b) { b.click(); return { clicked: true }; } return { clicked: false }; })()
```

列表提取：

```js
(function () {
  var table = document.querySelector('#DataTables_Table_0, table.datatable');
  if (!table) return { error: 'history table not found', mods: [] };

  var out = [];
  var rows = table.querySelectorAll('tbody tr');
  for (var i = 0; i < rows.length; i++) {
    var cells = rows[i].querySelectorAll('td');
    if (cells.length < 6) continue;
    var link = cells[0].querySelector('a[href*="/mods/"]');
    var name = link ? link.textContent.trim() : cells[0].textContent.trim();
    if (!name) continue;
    var m = link ? link.href.match(/\/mods\/(\d+)/) : null;

    var endorsed = false;
    var svg = cells[5].querySelector('svg');
    if (svg && svg.className && svg.className.baseVal) endorsed = svg.className.baseVal.indexOf('endorse-active') !== -1;

    out.push({
      name: name,
      id: m ? m[1] : '',
      lastDownloaded: cells[1].textContent.trim(),
      uploader: cells[2].textContent.trim(),
      category: cells[3].textContent.trim(),
      updated: cells[4].textContent.trim(),
      isEndorsed: endorsed,
      url: link ? link.href : ''
    });
  }

  var info = document.querySelector('.dataTables_info');
  var pages = [];
  var btns = document.querySelectorAll('.dataTables_paginate .paginate_button[data-dt-idx]');
  for (var b = 0; b < btns.length; b++) {
    var t = btns[b].textContent.trim();
    if (t && !isNaN(parseInt(t, 10))) pages.push(t);
  }
  return { mods: out, count: out.length, pagination: { info: info ? info.textContent.trim() : '', pages: pages } };
})()
```

点赞 / 取消点赞：`<a class="endorse-mod" data-positive="1|0" data-mod-id="...">`。用 snapshot 找 ref → `browser_click`，然后重新翻页刷新列表验证图标 class。

## S16 获取 MO2 API Key（只读）

页面：`/settings/api-keys`

⚠️ 只读取已存在的 key；**禁止**点击 “Request Api Key”。

```js
(function () {
  var out = { mo2: null, totalKeyInputs: 0 };
  var imgs = document.querySelectorAll('img');
  for (var i = 0; i < imgs.length; i++) {
    var alt = imgs[i].alt || '';
    if (alt.indexOf('Mod Organizer') === -1 && alt.indexOf('MO2') === -1) continue;
    var node = imgs[i];
    for (var up = 0; up < 10 && node; up++) {
      node = node.parentElement;
      if (!node) break;
      var inputs = node.querySelectorAll('input[type="text"]');
      if (inputs.length) {
        out.mo2 = { name: alt, keys: [] };
        for (var k = 0; k < inputs.length; k++) {
          var label = inputs[k].closest('label');
          out.mo2.keys.push({
            label: label ? label.textContent.trim().slice(0, 50) : '',
            hasValue: !!inputs[k].value,
            length: (inputs[k].value || '').length
          });
        }
        break;
      }
    }
    break;
  }
  out.totalKeyInputs = document.querySelectorAll('input[type="text"]').length;
  return out;
})()
```

需要交付 key 值给调用方时，再单独取 `value`，并且只写入目标工具，不回显到对话里。

## S17 游戏搜索

页面：`/games?keyword={encoded}`

```js
(function () {
  var titles = document.querySelectorAll('[data-e2eid="game-tile-title"]');
  var games = [];
  for (var i = 0; i < titles.length; i++) {
    var a = titles[i];
    var href = a.href;
    var domain = href.split('/games/')[1] || '';
    var img = null, node = a.parentElement;
    for (var d = 0; d < 5 && node && !img; d++) { img = node.querySelector('img'); node = node.parentElement; }
    var image = img ? img.src : '';
    var gameId = '';
    var segs = image.split('/');
    for (var s = 0; s < segs.length; s++) { if (segs[s] === 'v2' && s + 1 < segs.length) { gameId = segs[s + 1]; break; } }
    games.push({ name: a.textContent.trim(), domain: domain, gameId: gameId, url: href, image: image });
  }
  var countMatch = document.body.innerText.match(/(\d+)\s+results?/);
  return {
    keyword: new URLSearchParams(location.search).get('keyword') || '',
    totalResults: countMatch ? parseInt(countMatch[1], 10) : games.length,
    returnedCount: games.length,
    games: games
  };
})()
```

注意：`/games` 搜索页的 RSC 水合比 mod 列表慢，先跑 `S2`（selector 用 `[data-e2eid="game-tile-title"]`，timeout 15000）。
