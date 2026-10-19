---
name: using-dsd
description: Use when creating, editing, debugging, or validating DSD (Dynamic String Distributor) JSON configuration files — triggers "DSD config", "DSD JSON", "DSD 配置", "Dynamic String Distributor", "text replacement", "translate string", "修改游戏文字", "字符串替换", "文本替换". NOT for MO2 install, xEdit conflict resolution, Papyrus scripting, or SPID form distribution.
---

# Using DSD — Dynamic String Distributor

## 概述

本技能用于创建、编辑、调试和验证 DSD (Dynamic String Distributor) 的 JSON 配置文件。DSD 是一个 SKSE 插件，在运行时动态覆盖、添加或修改游戏中的所有文本/字符串（如名称、描述、按钮文字等），不修改插件也不影响存档。

## 何时使用

- 用户要求创建或修改 DSD JSON 配置
- 需要替换游戏中任何记录的 FULL Name、DESC、对话等文本
- 翻译 MOD 的字符串而不修改原始 ESP
- 调试 DSD 替换不生效
- 写 MOD 需要运行时文本覆盖

## 何时不用

- MO2 安装/管理 MOD → 使用 `bgs-mo2` 相关技能
- 分发 Spell/Perk/Item/Outfit 等表单给 NPC → 使用 `using-spid`
- xEdit 记录查看/冲突解决 → 使用 `xedit-automation`
- Papyrus 脚本编译 → 使用 `using-bgs-papyrus`
- 判断 MOD 是否应该加入模组包 → 使用 `evaluating-bgs-mods`

## 前置知识

完整语法参考: `references/dsd-complete-reference.md`（基于 moddingforge.com 官方文档整理）

## 工作流程

### 1. 理解需求

明确用户想要：
- 替换什么文本？（FullName/Description/对话/消息框/GMST 等）
- 目标记录是什么？（FormID + 插件名）
- 需要哪种 `type` 专用化？
- 是否需要 `index`？（多字符串记录）
- 是否需要 `editor_id`？（GMST 记录）

### 2. 确定文件放置路径

```
Data/SKSE/Plugins/DynamicStringDistributor/<Plugin-Name>/<Filename>.json
```

规则：
- `<Plugin-Name>` = 要为其创建翻译/替换的目标插件名（大小写不敏感）
- 可以替换**不同于**文件夹名的插件中的字符串
- JSON 文件只在对应插件激活时加载
- `overwrite/` 文件夹优先级最高，在所有插件之后处理

### 3. 确定 type 类别

根据目标记录类型选择 `type` 字段：

#### EditorID 必需

| type | 说明 |
|------|------|
| `GMST DATA` | 游戏设置字符串，需提供 `editor_id` |

#### 无需 index

| type | 说明 |
|------|------|
| `XXXX FULL` | 任何记录的完整名称（如 `WEAP FULL`, `CELL FULL`, `REFR FULL`） |
| `XXXX DESC` | 任何记录的描述文本（如 `BOOK DESC`, `ALCH DESC`） |
| `NPC_ SHRT` | NPC 短名称 |
| `WOOP TNAM` | Word of Power 翻译 |
| `INFO RNAM` | INFO 记录的提示文本 |
| `BOOK CNAM` | 书籍正文 |
| `MGEF DNAM` | 魔法效果描述 |
| `REGN RDMP` | 区域地图名称 |
| `ACTI RNAM` | 激活器交互文本 |
| `FLOR RNAM` | 地板/交互文本 |

#### 需要 index

| type | 说明 | index 含义 |
|------|------|------------|
| `QUST CNAM` | 任务日志条目 | INDX - 阶段索引 + 条目索引 |
| `QUST NNAM` | 任务目标文本 | QOBJ - 目标索引 |
| `INFO NAM1` | 对话响应文本 | TRDT 中响应编号 |
| `MESG ITXT` | 消息框按钮文本 | 列表索引（从 0 开始，如 xEdit 中显示） |
| `PERK EPF2` | Perk 入口点片段 | EPF3 中片段索引 |
| `PERK EPFD` | Perk 入口点片段描述 | 列表索引（从 0 开始，**仅计 EPFD 字符串**） |

### 4. 编写 JSON 配置

#### 基本模板

```json
[
    {
        "form_id": "FormID|PluginName.esp",
        "type": "XXXX FULL",
        "string": "New text here"
    }
]
```

#### 各类型示例

**替换物品名称 (FULL)：**
```json
[
    {
        "form_id": "000133C6|Skyrim.esm",
        "type": "CELL FULL",
        "string": "New Location Name"
    },
    {
        "form_id": "000ACC37|Skyrim.esm",
        "type": "WEAP FULL",
        "string": "Iron Sword - Improved"
    }
]
```

**替换 GMST 字符串：**
```json
[
    {
        "form_id": "000D48B7|Skyrim.esm",
        "editor_id": "sCurrentLocation",
        "type": "GMST DATA",
        "string": "You are now in:"
    }
]
```

**替换对话 (INFO NAM1，需要 index)：**
```json
[
    {
        "form_id": "000E6C43|Skyrim.esm",
        "type": "INFO NAM1",
        "index": 2,
        "string": "新的对话句子"
    }
]
```

**替换消息框按钮 (MESG ITXT，需要 index)：**
```json
[
    {
        "form_id": "00016837|Skyrim.esm",
        "type": "MESG ITXT",
        "index": 0,
        "string": "接受（新文字）"
    }
]
```

**替换任务目标 (QUST NNAM，需要 index)：**
```json
[
    {
        "form_id": "0004B2A1|Skyrim.esm",
        "type": "QUST NNAM",
        "index": 60,
        "string": "新的任务目标描述"
    }
]
```

**替换书籍正文 (BOOK CNAM)：**
```json
[
    {
        "form_id": "0001AD07|Skyrim.esm",
        "type": "BOOK CNAM",
        "string": "新的书籍文本内容..."
    }
]
```

**替换激活器文本 (ACTI RNAM)：**
```json
[
    {
        "form_id": "000A2C46|Skyrim.esm",
        "type": "ACTI RNAM",
        "string": "打开"
    }
]
```

### 5. JSON 字符串转义注意事项

JSON 必须符合 RFC 8259 标准。特别注意：
- 换行符使用 `\r\n`（Bethesda 游戏使用 Windows 风格换行）
- 双引号使用 `\"` 转义
- 反斜杠使用 `\\` 转义
- 特殊字体标签直接保留（如 `<font face='$HandwrittenFont'>`）

### 6. FormID 格式

`form_id` 字段格式：`"FormID|PluginName.esp"`

DSD 接受多种 FormID 写法：
- 完整 FormID: `050176CD`, `0x0176CD`, `0X0176CD`, `176CD`
- Light FormID (ESL): `FE0176CD`, `0x6CD`, `0X6CD`, `6CD`

推荐使用 `0x` 前缀的十六进制格式以保持一致性。

### 7. 加载顺序/优先级

冲突解决规则（按优先级升序）：
1. 按插件加载顺序：后加载的插件文件夹覆盖先加载的
2. 同插件文件夹内：按 JSON 文件名**字母顺序**覆盖
3. `overwrite/` 文件夹优先级最高，始终最后处理

> 建议：需要最高优先级时，将 JSON 放在 `overwrite/` 文件夹中。

### 8. 验证配置

检查清单：
- [ ] JSON 语法有效（可用在线 JSON 验证器）
- [ ] 文件放在正确路径 `Data/SKSE/Plugins/DynamicStringDistributor/<Plugin-Name>/`
- [ ] 对应插件在加载顺序中激活
- [ ] `form_id` 格式正确（`FormID|PluginName`）
- [ ] `type` 正确选择，且 `index`/`editor_id` 按要求提供
- [ ] 字符串中特殊字符正确转义（`\r\n`, `\"`, `\\`）
- [ ] 不使用已弃用的 `original` 字段（DSD ≥ 1.4.0）

### 9. 调试

常见问题排查：

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| 字符串未替换 | JSON 语法错误 | 用 JSON 验证器检查 |
| 字符串未替换 | `form_id` 格式错误 | 检查格式 `FormID\|PluginName` |
| 字符串未替换 | 对应插件未激活 | 确认加载顺序和激活状态 |
| 字符串未替换 | 文件夹名大小写？ | 大小写不敏感，但检查拼写 |
| 字符串未替换 | `type` 错误 | 确认选择了正确的 type |
| 被其他 MOD 覆盖 | 加载顺序冲突 | 将配置移到 `overwrite/` 或高优先级插件文件夹 |
| 多字符串记录替换错误 | 缺少或错误 `index` | 确认 index 编号（从 0 开始） |

启用调试日志：编辑 `Data/SKSE/Plugins/DynamicStringDistributor.ini`：
```ini
[Debug]
EnableDebugLog = true
EnableDebugInfo = true
```

- `EnableDebugLog=true`：记录文件解析过程和字幕信息
- `EnableDebugInfo=true`：在所有替换文本前添加 `[FormID|Plugin]` 前缀，方便查看是否被 DSD 修改

### 10. 自动化工具

- **xEdit 导出脚本 (DSD - Export plugins.pas)**：从 MOD 页面获取，可在 SSEEdit 中自动生成 DSD JSON 文件
- **SSE Auto Translator (SSE-AT)**：可翻译整个加载顺序

## 输出规范

完成配置后，提供：
- 完整的 JSON 文件内容
- 文件应放置的路径
- 推荐的 MO2 安装方式（新建空 MOD，将 JSON 放入对应路径）
- 优先级说明（如需要 `overwrite/` 文件夹）

## 注意事项

- JSON 文件仅在对应插件激活时加载
- 文件夹名大小写不敏感（`skyrim.esm` 和 `Skyrim.esm` 等效）
- 可以在文件夹 A 中替换插件 B 的字符串
- `original` 字段自 DSD 1.4.0 起已弃用，不要使用
- 字符串中的换行必须使用 `\r\n`
- 文件编码使用 UTF-8（JSON 标准）

## 参考

- 完整参考: `references/dsd-complete-reference.md`
- DSD 官方文档: https://moddingforge.com/docs/dsd/
- N 网页面: https://www.nexusmods.com/skyrimspecialedition/mods/138636
- GitHub: https://github.com/thirdeyeSauron/dynamic-string-distributor