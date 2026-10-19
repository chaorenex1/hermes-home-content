# DSD (Dynamic String Distributor) 完整参考文档

> 基于 moddingforge.com 官方文档整理
> 作者: thirdeyeSauron
> 适用版本: DSD ≥ 1.4.0
> 官方文档: https://moddingforge.com/docs/dsd/
> N 网: https://www.nexusmods.com/skyrimspecialedition/mods/138636
> GitHub: https://github.com/thirdeyeSauron/dynamic-string-distributor

---

## 目录

1. [概述](#1-概述)
2. [JSON 配置文件](#2-json-配置文件)
3. [JSON 加载顺序](#3-json-加载顺序)
4. [JSON 格式详情](#4-json-格式详情)
5. [Type 专用化](#5-type-专用化)
6. [自动化工具](#6-自动化工具)
7. [设置](#7-设置)
8. [API 参考汇总](#8-api-参考汇总)

---

## 1. 概述

**Dynamic String Distributor (DSD)** 是一个 SKSE 插件，允许 MOD 作者和用户在运行时动态覆盖、添加或修改游戏中所有文本/字符串（名称、描述、按钮文字等）。

### 1.1 核心特性

- **插件独立**：翻译和文本替换不依赖 ESP/ESL/ESM 文件，减少冲突和版本不匹配
- **JSON 配置**：使用 JSON 文件，游戏启动时一次性解析
- **MergeMapper 支持**：兼容合并后的插件

### 1.2 与 SPID 的区别

| 特性 | SPID | DSD |
|------|------|-----|
| 分发内容 | 表单 (Spell/Item/Perk...) | 文本字符串 |
| 配置文件格式 | INI (`_DISTR.ini`) | JSON |
| 目标 | NPC (由过滤器确定) | 记录 (由 FormID 确定) |
| 冲突解决 | 字母顺序 | 插件加载顺序 + 字母顺序 + overwrite |

---

## 2. JSON 配置文件

### 2.1 文件路径

```
Data/SKSE/Plugins/DynamicStringDistributor/<Plugin-Name>/<Filename>.json
```

示例:
```
Data/SKSE/Plugins/DynamicStringDistributor/Skyrim.esm/MyCustomStrings.json
```

### 2.2 路径规则

| 规则 | 说明 |
|------|------|
| 替换目标 | 可以在文件夹 A 中替换插件 B 的字符串 |
| 大小写 | 文件夹名大小写**不敏感** (`skyrim.esm` = `Skyrim.esm`) |
| 激活条件 | JSON 文件仅在对应插件**激活**时加载 |
| overwrite | `overwrite/` 文件夹是保留名称，总是在最后处理，最高优先级 |

---

## 3. JSON 加载顺序

冲突系统类似 ESP/ESL/ESM 插件加载顺序：

### 3.1 优先级规则（从低到高）

1. **插件加载顺序**：后加载的插件文件夹覆盖先加载的
2. **同文件夹内字母顺序**：Z > A（后字母覆盖前字母）
3. **overwrite 文件夹**：优先级最高，始终最后处理

### 3.2 示例

```
; 以下按优先级从低到高排列：
Data/SKSE/Plugins/DynamicStringDistributor/Skyrim.esm/AAA_Base.json      ; 最低
Data/SKSE/Plugins/DynamicStringDistributor/Skyrim.esm/ZZZ_Patch.json     ; 覆盖 AAA_Base
Data/SKSE/Plugins/DynamicStringDistributor/MyPatch.esp/MyText.json       ; 覆盖 Skyrim.esm
Data/SKSE/Plugins/DynamicStringDistributor/overwrite/ZZZZ.json           ; 最高优先级
```

---

## 4. JSON 格式详情

### 4.1 基本结构

DSD 配置是一个 JSON **数组**，包含多个修改字符串的对象。

```json
[
    {
        "form_id": "FormID|PluginName.esp",
        "type": "XXXX FULL",
        "string": "New text"
    }
]
```

### 4.2 字段规范

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `form_id` | String | ✅ | 记录标识。格式: `"FormID\|PluginName.esp"` |
| `type` | String | ✅ | 字符串类型（见 [Type 专用化](#5-type-专用化)） |
| `string` | String | ✅ | 替换文本 |
| `editor_id` | String | ❌ | EditorID（仅 GMST 等类型需要） |
| `index` | Integer | ❌ | 多字符串记录的精确定位 |
| `original` | String | ❌ | ⚠️ 自 DSD **1.4.0** 起已弃用！ |

### 4.3 FormID 格式

`form_id` 字段接受多种写法：

| 格式 | 示例 | 插件类型 |
|------|------|---------|
| 完整十六进制 | `050176CD` | Full |
| 0x 前缀 | `0x0176CD` | Full |
| 0X 前缀 | `0X0176CD` | Full |
| 简写 | `176CD` | Full |
| Light 完整 | `FE0176CD` | ESL |
| Light 0x | `0x6CD` | ESL |
| Light 简写 | `6CD` | ESL |

> **推荐**：使用 `0x` 前缀格式以保持与 xEdit 一致。

### 4.4 JSON 转义规则

必须符合 [RFC 8259](https://datatracker.ietf.org/doc/html/rfc8259) 标准：

| 字符 | 转义 |
|------|------|
| 换行 | `\r\n` (Bethesda 游戏使用 Windows CRLF) |
| 双引号 | `\"` |
| 反斜杠 | `\\` |
| Tab | `\t` |

**示例** — 包含特殊字符的书籍文本：
```json
{
    "form_id": "0001AD07|Skyrim.esm",
    "type": "BOOK CNAM",
    "string": "<font face='$HandwrittenFont'>\r\nDelvin,\r\n\r\nIngredients:\r\n- 4 cups Bone Dust\r\n- 1 cup Salt\r\n- 1 flask of \"Netch\" Jelly\r\n\r\n- Glover Mallory"
}
```

---

## 5. Type 专用化

### 5.1 分类概览

```
type 字段分类:
├── EditorID 必需
│   └── GMST DATA
├── 无需 index
│   ├── XXXX FULL (任何记录)
│   ├── XXXX DESC (任何记录)
│   ├── NPC_ SHRT
│   ├── WOOP TNAM
│   ├── INFO RNAM
│   ├── BOOK CNAM
│   ├── MGEF DNAM
│   ├── REGN RDMP
│   ├── ACTI RNAM
│   └── FLOR RNAM
└── 需要 index
    ├── QUST CNAM  (INDX - 阶段索引 + 条目索引)
    ├── QUST NNAM  (QOBJ - 目标索引)
    ├── INFO NAM1  (响应编号)
    ├── MESG ITXT  (列表索引，从0开始)
    ├── PERK EPF2  (EPF3 片段索引)
    └── PERK EPFD  (列表索引，从0开始)
```

### 5.2 EditorID 必需 — GMST DATA

游戏设置 (Game Setting)。需要 `editor_id` 字段指定具体的 GMST。

```json
{
    "form_id": "000D48B7|Skyrim.esm",
    "editor_id": "sCurrentLocation",
    "type": "GMST DATA",
    "string": "新的位置显示文字"
}
```

### 5.3 无需 index — FULL / DESC

#### XXXX FULL — 任何记录的完整名称

将 `XXXX` 替换为目标记录类型：

```json
{ "form_id": "000133C6|Skyrim.esm", "type": "CELL FULL", "string": "新地点名" },
{ "form_id": "000ACC37|Skyrim.esm", "type": "WEAP FULL", "string": "新武器名" },
{ "form_id": "0004D0F4|Skyrim.esm", "type": "REFR FULL", "string": "新引用名" },
{ "form_id": "0003FA35|Skyrim.esm", "type": "DIAL FULL", "string": "新对话主题" }
```

常见 FULL 类型：
`ALCH`, `AMMO`, `ARMO`, `BOOK`, `CELL`, `DIAL`, `FLOR`, `FURN`, `INGR`, `KEYM`, `LCTN`, `MISC`, `NPC_`, `QUST`, `REFR`, `SCRL`, `SLGM`, `SPEL`, `WEAP`, `WRLD` 等。

#### XXXX DESC — 任何记录的描述文本

```json
{ "form_id": "...", "type": "BOOK DESC", "string": "新的书籍描述..." },
{ "form_id": "...", "type": "ALCH DESC", "string": "新的药剂描述..." },
{ "form_id": "...", "type": "SPEL DESC", "string": "新的法术描述..." }
```

#### NPC_ SHRT — NPC 短名称

```json
{
    "form_id": "0001347B|Skyrim.esm",
    "type": "NPC_ SHRT",
    "string": "Roman"
}
```

#### WOOP TNAM — Word of Power 翻译

```json
{
    "form_id": "000252C3|Skyrim.esm",
    "type": "WOOP TNAM",
    "string": "力量"
}
```

#### INFO RNAM — INFO 记录提示文本

```json
{
    "form_id": "000E40D3|Skyrim.esm",
    "type": "INFO RNAM",
    "string": "新的提示文本"
}
```

#### BOOK CNAM — 书籍正文

```json
{
    "form_id": "0001AD07|Skyrim.esm",
    "type": "BOOK CNAM",
    "string": "新的书籍正文..."
}
```

#### MGEF DNAM — 魔法效果描述

```json
{
    "form_id": "000E40D3|Skyrim.esm",
    "type": "MGEF DNAM",
    "string": "<mag>% Disease Resistance."
}
```

#### REGN RDMP — 区域地图名称

```json
{
    "form_id": "...",
    "type": "REGN RDMP",
    "string": "新的地图区域名"
}
```

#### ACTI RNAM — 激活器交互文本

```json
{
    "form_id": "000A2C46|Skyrim.esm",
    "type": "ACTI RNAM",
    "string": "Open"
}
```

#### FLOR RNAM — 地板/交互文本

```json
{
    "form_id": "000176CD|Skyrim.esm",
    "type": "FLOR RNAM",
    "string": "Interact"
}
```

### 5.4 需要 index — 多字符串记录

#### QUST CNAM — 任务日志条目

`index` = INDX 阶段索引 + 条目索引

```json
{
    "form_id": "...|...",
    "type": "QUST CNAM",
    "index": 10,
    "string": "新的日志条目"
}
```

#### QUST NNAM — 任务目标文本

`index` = QOBJ 目标索引 (从 0 开始)

```json
{
    "form_id": "0004B2A1|Skyrim.esm",
    "type": "QUST NNAM",
    "index": 60,
    "string": "找到上古卷轴"
}
```

#### INFO NAM1 — 对话响应文本

`index` = TRDT (Response Data) 中的响应编号

```json
{
    "form_id": "000E6C43|Skyrim.esm",
    "type": "INFO NAM1",
    "index": 2,
    "string": "新的对话选项文本"
}
```

#### MESG ITXT — 消息框按钮文本

`index` = 列表索引（从 0 开始，如 xEdit 中显示的顺序）

```json
{
    "form_id": "00016837|Skyrim.esm",
    "type": "MESG ITXT",
    "index": 0,
    "string": "确认"
}
```

#### PERK EPF2 — Perk 入口点片段

`index` = EPF3 中的片段索引

```json
{
    "form_id": "...|...",
    "type": "PERK EPF2",
    "index": 0,
    "string": "新的入口点描述"
}
```

#### PERK EPFD — Perk 入口点片段描述

`index` = 列表索引（从 0 开始）。⚠️ **仅计 EPFD 字符串**，其他条目不计入此顺序。

```json
{
    "form_id": "...|...",
    "type": "PERK EPFD",
    "index": 0,
    "string": "新的片段描述"
}
```

---

## 6. 自动化工具

### 6.1 xEdit 导出脚本

`DSD - Export plugins.pas` 可从 MOD 页面获取。在 SSEEdit (xEdit) 中加载，可自动从插件文件生成 DSD JSON 文件。适用于将现有翻译/字符串补丁 MOD 快速转换为 DSD 格式。

### 6.2 SSE Auto Translator (SSE-AT)

可批量翻译整个加载顺序。支持与 DSD 集成输出。

---

## 7. 设置

配置文件路径: `Data/SKSE/Plugins/DynamicStringDistributor.ini`

```ini
[Debug]
; 启用详细日志（文件解析过程、字幕信息）
EnableDebugLog = false

; 在所有替换文本前添加 [FormID|Plugin] 前缀
; 方便排查字符串是否被 DSD 修改
EnableDebugInfo = false
```

- 所有设置在游戏启动时生效
- 调试完成后记得关闭以提升性能

---

## 8. API 参考汇总

### 8.1 完整示例集

```json
[
    {
        "form_id": "000D48B7|Skyrim.esm",
        "editor_id": "sCurrentLocation",
        "type": "GMST DATA",
        "string": "You are in:"
    },
    {
        "form_id": "000133C6|Skyrim.esm",
        "type": "CELL FULL",
        "string": "Riverwood (汉化)"
    },
    {
        "form_id": "000ACC37|Skyrim.esm",
        "type": "WEAP FULL",
        "string": "铁剑"
    },
    {
        "form_id": "0001AD07|Skyrim.esm",
        "type": "BOOK DESC",
        "string": "一本关于锻造的书"
    },
    {
        "form_id": "000E40D3|Skyrim.esm",
        "type": "MGEF DNAM",
        "string": "<mag>% 疾病抗性。"
    },
    {
        "form_id": "000A2C46|Skyrim.esm",
        "type": "ACTI RNAM",
        "string": "打开"
    },
    {
        "form_id": "000E6C43|Skyrim.esm",
        "type": "INFO NAM1",
        "index": 2,
        "string": "我接受这个任务。"
    },
    {
        "form_id": "0004B2A1|Skyrim.esm",
        "type": "QUST NNAM",
        "index": 60,
        "string": "前往寒落山脉"
    },
    {
        "form_id": "00016837|Skyrim.esm",
        "type": "MESG ITXT",
        "index": 0,
        "string": "确认购买"
    }
]
```

### 8.2 快速参考卡片

| 想修改... | type | 需要 index? | 需要 editor_id? |
|-----------|------|------------|-----------------|
| 物品名称 | `WEAP FULL` / `ARMO FULL` 等 | ❌ | ❌ |
| 对话主题 | `DIAL FULL` | ❌ | ❌ |
| 对话内容 | `INFO NAM1` | ✅ 响应编号 | ❌ |
| 书籍正文 | `BOOK CNAM` | ❌ | ❌ |
| 书描述 | `BOOK DESC` | ❌ | ❌ |
| 任务目标 | `QUST NNAM` | ✅ 目标索引 | ❌ |
| 任务日志 | `QUST CNAM` | ✅ 阶段索引 | ❌ |
| 消息框按钮 | `MESG ITXT` | ✅ 按钮索引 | ❌ |
| 魔法效果 | `MGEF DNAM` | ❌ | ❌ |
| 激活器文字 | `ACTI RNAM` | ❌ | ❌ |
| 游戏设置 | `GMST DATA` | ❌ | ✅ |
| NPC 短名 | `NPC_ SHRT` | ❌ | ❌ |
| 龙吼词 | `WOOP TNAM` | ❌ | ❌ |
| 区域地图 | `REGN RDMP` | ❌ | ❌ |
| Perk 片段 | `PERK EPF2` | ✅ 片段索引 | ❌ |
| Perk 片段描述 | `PERK EPFD` | ✅ EPFD序号 | ❌ |

### 8.3 调试清单

```
□ JSON 语法有效（用 jsonlint.com 或 vs code 验证）
□ 文件在正确路径 Data/SKSE/Plugins/DynamicStringDistributor/<Plugin-Name>/
□ 对应插件在加载顺序中激活
□ form_id 格式: "FormID|PluginName.esp"
□ type 选择正确
□ GMST 类型提供了 editor_id
□ 多字符串类型提供了正确的 index（从 0 开始）
□ 字符串特殊字符已转义 (\r\n, \", \\)
□ 未使用已弃用的 original 字段
□ 如需调试，已开启 EnableDebugLog = true
```

---

## 参考链接

- 官方文档: https://moddingforge.com/docs/dsd/
- N 网页面: https://www.nexusmods.com/skyrimspecialedition/mods/138636
- GitHub: https://github.com/thirdeyeSauron/dynamic-string-distributor
- JSON RFC 8259: https://datatracker.ietf.org/doc/html/rfc8259
- UESP 表单类型列表: https://en.uesp.net/wiki/Skyrim_Mod:Mod_File_Format
