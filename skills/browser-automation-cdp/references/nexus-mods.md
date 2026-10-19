# Nexus Mods 抓取配方

> 通过 CDP 浏览器自动化抓取 Nexus Mods 页面数据。
> 本文档是 `browser-automation-cdp` 技能的参考附件。

---

## 目标页面

Skyrim Special Edition 首页（含 Trending Mods）：
`https://www.nexusmods.com/games/skyrimspecialedition`

通用游戏页格式：`https://www.nexusmods.com/games/{game_slug}`

---

## DOM 结构

### Mod 卡片（Trending / Latest Mods 列表）

Nexus Mods 使用 Tailwind CSS，mod 卡片选择器为：

```
[class*="group/mod-tile"]
```

每个卡片内提取：

| 数据 | 选择器 / 方式 |
|------|-------------|
| Mod ID | `tile.querySelector('a[href*="/mods/"]')` → href 中 `/mods/(\d+)` |
| Mod 名称 | `tile.querySelector('[class*="truncate"], [class*="text-body"], h3, a[class*="link"], [class*="line-clamp"]')` |
| 链接 | `a[href*="/mods/"]` 的 href |

### 去重

同一 mod 可能在列表中多次出现（image link + text link），按 `modId` 去重。

提取模板：
```javascript
JSON.stringify(
    Array.from(document.querySelectorAll('[class*="group/mod-tile"]')).map(tile => {
        const link = tile.querySelector('a[href*="/mods/"]');
        const href = link ? link.href : '';
        const modIdMatch = href.match(/\/mods\/(\d+)/);
        const modId = modIdMatch ? modIdMatch[1] : '';
        const nameEl = tile.querySelector('[class*="truncate"], [class*="text-body"], h3, a[class*="link"], [class*="line-clamp"]');
        const name = nameEl ? nameEl.innerText.trim().replace(/\s+/g, ' ') : '';
        return { modId, name, href };
    }).filter(m => m.modId && m.name)
)
```

---

## Mod 详情页

URL 格式：`https://www.nexusmods.com/skyrimspecialedition/mods/{modId}`

### 统计信息位置

统计信息在侧边栏/header区域，通过 `document.body.innerText` 全文正则提取最可靠（DOM 层级深且不稳定）：

```
Endorsements
311
Unique DLs
7,568
Total DLs
9,890
Total views
40,706
Version
1.0.3
```

正则提取：
```javascript
var text = document.body.innerText || '';

function extract(pattern) {
    var m = text.match(pattern);
    return m ? m[1].replace(/,/g, '').trim() : '';
}

var author = extract(/Created by\s*\n\s*(.+?)\n/);
var endorsements = extract(/Endorsements\s*\n\s*([\d,]+)/);
var uniqueDLs = extract(/Unique DLs\s*\n\s*([\d,]+)/);
var totalDLs = extract(/Total DLs\s*\n\s*([\d,]+)/);
var totalViews = extract(/Total views\s*\n\s*([\d,]+)/);
var version = extract(/Version\s*\n\s*([\d.]+[a-z]*)/);
```

### 无数据（新 mod）

新发布的 mod 统计显示 `--` 而非数字：
```
Unique DLs
--
Total DLs
--
Total views
--
```

**必须特殊处理**（否则正则返回空字符串）：
```javascript
if (!uniqueDLs) {
    var m = text.match(/Unique DLs\s*\n\s*(--)/);
    if (m) uniqueDLs = '0';
}
if (!totalDLs) {
    var m = text.match(/Total DLs\s*\n\s*(--)/);
    if (m) totalDLs = '0';
}
if (!totalViews) {
    var m = text.match(/Total views\s*\n\s*(--)/);
    if (m) totalViews = '0';
}
```

### 图片提取

Mod 图片存在于缩略图 gallery 中。URL 模式：

```
https://staticdelivery.nexusmods.com/mods/1704/images/thumbnails/{modId}/{modId}-{timestamp}-{hash}.png
https://staticdelivery.nexusmods.com/mods/1704/images/headers/{modId}_{timestamp}.jpg
https://staticdelivery.nexusmods.com/mods/1704/images/{modId}/{modId}-{timestamp}-{hash}.png
```

提取模板（缩略图转原图）：
```javascript
var modImg = '';
var imgs = document.querySelectorAll('img');
for (var k = 0; k < imgs.length; k++) {
    var src = imgs[k].src || '';
    if (src.includes('/mods/1704/images/thumbnails/')) {
        modImg = src.replace('/thumbnails/', '/');  // thumbnail → full size
        break;
    }
    if (src.includes('/mods/1704/images/headers/')) {
        modImg = src;
        break;
    }
    if (src.includes('/mods/1704/images/') && !src.includes('thumbnails') && imgs[k].width > 200) {
        modImg = src;
        break;
    }
}
```

### 描述（Description）

描述在 "About this mod" 标题之后，"Share" 或 "Requirements" 之前：

```javascript
var desc = '';
var idx = text.indexOf('About this mod');
if (idx > 0) {
    var after = text.substring(idx + 14);
    var endIdx = after.indexOf('Share');
    if (endIdx < 0) endIdx = after.indexOf('Requirements');
    if (endIdx < 0) endIdx = after.indexOf('Permissions');
    desc = (endIdx > 0 ? after.substring(0, endIdx) : after.substring(0, 600))
        .replace(/\n+/g, ' ').trim();
}
```

---

## Cookie 弹窗

Nexus Mods 首次访问弹出 Quantcast cookie 同意对话框。点击 "Deny" 按钮关闭：

```javascript
var btns = document.querySelectorAll('button');
for (var b of btns) {
    var t = b.innerText || b.textContent || '';
    if (t.trim() === 'Deny') { b.click(); return 'deny'; }
}
```

---

## 完整抓取流程

1. 启动 Edge CDP：`msedge.exe --remote-debugging-port=9222`
2. `npm install ws` 确保依赖可用
3. 创建自包含 Node.js 脚本（模板见 SKILL.md）
4. 导航到游戏首页 → `sleep(6000)` → 关闭 cookie
5. 滚动加载内容 → 提取所有 `[class*="group/mod-tile"]` → 去重
6. 逐个导航到 `/mods/{modId}` → `sleep(5000)` → 正则提取统计
7. 每个 mod 间隔 1.5-2s 避免触发速率限制
8. 结果写入 JSON 文件

---

## 速率限制

- 每个 mod 页之间建议间隔 ≥ 1500ms
- 22 个 mod 约需 2-3 分钟
- 未登录状态不会被封，但过快请求可能触发临时限制

---

*最后更新：2026-06-23 — Skyrim SE 实例验证*
