---
name: using-bgs-kid
description: "Use when writing, reading, or debugging Keyword Item Distributor (KID) INI config files for Skyrim SE/AE/VR. Triggers: KID, Keyword Item Distributor, KID configuration, keyword distribution, add keyword to items."
---

# Using Keyword Item Distributor (KID)

## 概述

本技能用于编写、阅读、调试 [Keyword Item Distributor (KID)](https://www.nexusmods.com/skyrimspecialedition/mods/55728) 的配置 INI 文件。KID 是 powerofthree 开发的 SKSE 插件，在游戏启动时通过配置文件向物品动态分配关键词，无需占用 ESP/ESL 插件槽。

Full reference: `references/Nexus-55728-KID-reference.md`

## 触发条件

以下任一场景触发本技能：
- 用户需要**编写新的 KID INI 配置**
- 用户需要**阅读/理解**现有的 KID INI
- 用户询问 **KID 格式**、过滤器、traits 的用法
- MOD 安装后需要**创建配套的 KID 配置**来分配关键词
- 用户报告 **KID 关键词分配不生效**，需要调试
- 用户询问 "某个 MOD 需要 KID 吗" 或 "这个 MOD 怎么配置 KID"
- 用户在 `interpreting-mod-author-instructions` 中遇到 KID 依赖

## KID 配置文件格式速查

### 文件约定
- 位置：`Data/` 目录
- 命名：`*_KID.ini`（后缀 `_KID` 是强制约定）
- 内容格式：
```
Keyword = formID~esp(OR)keywordEditorID|type|strings,formIDs(OR)editorIDs|traits|chance
```

### 参数顺序

```
Keyword = KEYWORD_IDENTIFIER | TYPE | FILTERS | TRAITS | CHANCE
```

| 位置 | 参数 | 必填 | 说明 |
|------|------|------|------|
| 1 | Keyword | ✅ | FormID（`0x12345~Mod.esp`）或 EditorID |
| 2 | Type | ✅ | 目标物品类型（Weapon/Armor/Magic Effect/...） |
| 3 | Filters | ❌ | 字符串/FormID 过滤器，逗号分隔 |
| 4 | Traits | ❌ | 类型特定的特性过滤器（如 `H`, `-E`） |
| 5 | Chance | ❌ | 概率 0.0-100.0，默认 100 |

### 支持的 Type（物品类型）

```
Weapon, Armor, Ammo, Magic Effect, Potion, Scroll, Location,
Ingredient, Book, Misc Item, Key, Soul Gem, Spell, Activator,
Flora, Furniture, Race, Talking Activator, Enchantment
```

### 过滤器修饰符

| 修饰符 | 含义 | 示例 |
|--------|------|------|
| `X` | 精确匹配 | `Iron Sword` |
| `*X` | 部分匹配（包含 X） | `*Daedric` → 所有含 Daedric 的物品 |
| `-X` | 排除（不匹配 X） | `-Elven` → 排除所有精灵系 |
| `-*X` | 排除部分 | `-*Banded` → 排除含 Banded 的 |
| `A+B` | AND 组 | `ArmorHeavy+ArmorGauntlet` |
| `A+B, C+D` | OR 组 | 匹配 (A+B) 或 (C+D) |

### 常用 Traits

| 类型 | Trait | 含义 |
|------|-------|------|
| Magic Effect | `H` / `-H` | 敌对 / 非敌对 |
| Armor/Weapon | `E` / `-E` | 已附魔 / 未附魔 |
| Potion | `P` | 毒药 |
| Potion | `F` | 食物 |
| Book | `S` | 技能书/法术书 |

## 编写 KID 配置的标准流程

### 1. 明确需求

从 MOD 作者说明或用户需求中确认：
- 要给**哪些物品**添加关键词？（物品类型）
- 要添加**什么关键词**？（来自哪个 MOD？EditorID 是什么？）
- 是否需要**条件过滤**？（只给特定物品、排除某些物品）

### 2. 确定 Keyword 标识符

**优先级：EditorID > FormID**

```ini
; 推荐：使用 EditorID（可跨 MOD 兼容，不存在的关键词自动创建）
Keyword = MyCustomKeyword|Weapon|Iron Sword

; 备选：使用 FormID~esp（精确但依赖 MOD 加载）
Keyword = 0x12345~MyMod.esp|Weapon|Iron Sword
```

⚠️ 使用 EditorID 时若关键词不存在，KID 会**动态创建**。这意味着 `GetKeywordString` 可以查到它，但它不会出现在 CK/xEdit 的关键词列表中。

### 3. 选择 Type

确认物品属于哪种类型：
- 武器 → `Weapon`
- 护甲/服装 → `Armor`
- 法术效果 → `Magic Effect`
- 药水/食物/毒药 → `Potion`
- 书籍/卷轴/笔记 → `Book`

### 4. 编写过滤器

原则：**从宽到窄**。先用宽泛条件覆盖大部分物品，再用精确条件处理特殊物品。

```ini
; 宽泛：给某 MOD 所有武器
Keyword = MyKeyword|Weapon|MyMod.esp

; 精确：只给特定名称的物品
Keyword = MyKeyword|Weapon|Iron Sword, Steel Sword

; 排除：不给特定种类
Keyword = MyKeyword|Armor|NONE|-*Daedric
```

### 5. 添加 Traits（如需要）

```ini
; 只给非附魔的重型护甲
Keyword = MyKeyword|Armor|ArmorHeavy|-E

; 只给敌对法术效果
Keyword = MyKeyword|Magic Effect|NONE|H

; 只给食物不给毒药
Keyword = MyKeyword|Potion|NONE|F
```

### 6. 确定 Chance（如需要）

```ini
; 50% 概率分配
Keyword = MyKeyword|Weapon|Iron Sword|NONE|50

; 默认 100%（省略或写 NONE）
Keyword = MyKeyword|Weapon|Iron Sword
```

## 常见配置模式

### 模式 1：给整个 MOD 的物品添加关键词

```ini
; 给 MyArmorMod.esp 中所有 Armor 添加关键词
Keyword = MyArmorKeyword|Armor|MyArmorMod.esp
```

### 模式 2：按名称匹配特定物品

```ini
; 给所有名字含 "Iron" 的武器
Keyword = IronWeaponTag|Weapon|*Iron

; 给所有精灵系物品（排除）
Keyword = NotElven|Armor|NONE|-*Elven
```

### 模式 3：用 EditorID 创建新关键词

```ini
; 创建新关键词 "CCO_ArmorMaterial" 并分配给所有护甲
Keyword = CCO_ArmorMaterial|Armor|NONE
```

### 模式 4：组合条件

```ini
; 给非附魔、非魔族、带 ArmorCuirass 关键词的护甲
Keyword = MyKeyword|Armor|ArmorCuirass|-E
```

### 模式 5：多条目分发同一关键词到不同类型

```ini
; 同一个关键词分配给武器和护甲
Keyword = MyKeyword|Weapon|MyMod.esp
Keyword = MyKeyword|Armor|MyMod.esp
```

## 调试 KID 配置

### 检查日志

```
My Games/Skyrim Special Edition/SKSE/po3_KeywordItemDistributor.log
```

日志会报告：
- 成功分配的关键词及目标 FormID
- 解析失败的条目及原因
- v4.0.5+ 可开启 verbose logging

### 常见错误

| 问题 | 原因 | 解决 |
|------|------|------|
| 关键词未分配 | 文件名不符合 `*_KID.ini` 格式 | 检查文件名后缀 |
| 关键词未分配 | Type 大小写错误 | Type 区分大小写：`Weapon` 不是 `weapon` |
| 过滤器不生效 | FormID 未去前导零 | `0x12345` 不是 `0x00012345` |
| 所有物品都被分配 | 过滤器为空且没写 `NONE` | 第三个参数留空需显式写 `NONE` |
| AND 组不工作 | v4.0.0 之前不支持 AND 组内修饰符 | 升级到 >= 4.0.0 |

### 验证流程

1. 确认文件在 `Data/` 且命名为 `*_KID.ini`
2. 启动游戏到主菜单即可（KID 在启动时分配）
3. 打开日志检查分配结果
4. 在游戏中使用控制台或 `GetKeywordString` 验证关键词存在

## 与其他技能的关系

| 场景 | 使用的技能链 |
|------|-------------|
| 安装依赖 KID 的 MOD | `evaluating-bgs-mods` → `interpreting-mod-author-instructions` → 如需编写 KID 配置则触发本技能 |
| 需要给 MOD 物品添加自定义关键词 | 直接使用本技能 |
| KID 配置导致 CTD/冲突 | `diagnosing-bgs-problems` → 可能引用本技能的调试部分 |

## 参考

- 完整参考文档：`references/Nexus-55728-KID-reference.md`
- MOD 页面：https://www.nexusmods.com/skyrimspecialedition/mods/55728
- SKSE 日志：`My Games/Skyrim Special Edition/SKSE/po3_KeywordItemDistributor.log`
- 前置依赖：SKSE64, Address Library for SKSE Plugins, powerofthree's Tweaks
