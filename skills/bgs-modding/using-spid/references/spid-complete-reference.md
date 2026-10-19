# SPID (Spell Perk Item Distributor) 完整参考文档

> 基于 N 网 ID 36869 — powerofthree 的 SPID MOD 使用文章
> 作者: sasnikol (powerofthree)
> 适用版本: SPID 7.3.1
> 原始文章地址: https://www.nexusmods.com/skyrimspecialedition/mods/36869?tab=articles

---

## 目录

1. [SPID: The Complete Reference](#1-spid-the-complete-reference)
2. [Outfit Distribution](#2-outfit-distribution)
3. [Exclusive Groups](#3-exclusive-groups)
4. [Linked Distribution](#4-linked-distribution)
5. [On Death Distribution](#5-on-death-distribution)
6. [FormIDs and You](#6-formids-and-you)

---

## 1. SPID: The Complete Reference

> 适用于 SPID 7.3.0，包含创建 SPID MOD 所需的全部知识。

### 1.1 通用分发信息

SPID 在运行时分发所有配置的表单(Form)，不影响已加载插件也不影响存档。每次启动游戏时 SPID 从头开始分发所有内容。可将 SPID 分发视为在加载顺序最后应用的"虚拟插件"。这使得 SPID MOD 可以随时安全安装/卸载，不会留下痕迹。

### 1.2 SPID 加载配置的顺序

1. 启动时 SPID 查找 Skyrim `Data/` 文件夹中所有文件名含 `_DISTR` 后缀的 ini 文件
2. 按字母顺序从 A 到 Z 排序并加载
3. 每个文件从上到下读取，保持每种表单类型的相对顺序（该顺序在分发时使用）

### 1.3 分发时机

分发是"懒加载"的：当 NPC 加载到世界中时（通常是单元加载时）触发。

### 1.4 分发顺序

SPID 按表单类型分别处理分发。各类型处理顺序为：

1. Spell
2. Perk
3. Item
4. Shout
5. Package
6. Keyword (额外按依赖排序)
7. Outfit
8. SleepOutfit
9. Faction
10. Skin

> Keywords 会额外排序，确保依赖其他 keyword 的 keyword 在依赖项之后分发。

### 1.5 语法

```
FormType = FormOrEditorID|StringFilters|FormFilters|LevelFilters|TraitFilters|CountOrPackageIndex|Chance
           required          required          optional        optional       optional       optional               optional
                                                                                          Default: Index=0; Count=1   Default: 100
```

可选部分可留空或标记为 `NONE`。

### 1.6 支持的表单类型 (Form Types)

| Form Type    | Signature                    | 说明                 |
|--------------|------------------------------|----------------------|
| Spell        | SPEL, LVSP                   | 法术                 |
| Perk         | PERK                         | 技能                 |
| Item         | ALCH, AMMO, ARMO, BOOK, INGR, KEYM, LVLI, MISC, SCRL, SLGM, WEAP | 可携带物品 |
| Shout        | SHOU                         | 龙吼                 |
| Package      | PACK, FLST*                  | AI包                 |
| Keyword      | KYWD                         | 关键词(可动态创建)   |
| Outfit       | OTFT                         | 服装                 |
| SleepOutfit  | OTFT                         | 睡眠服装             |
| Faction      | FACT                         | 阵营                 |
| Skin         | ARMO                         | 皮肤                 |

> *FormList 分发时必须只包含 Packages，否则游戏很可能崩溃。
> 可使用通用 `Form` 类型让 SPID 自动推断（但 SleepOutfit 和 Skin 无法推断）。

### 1.7 可分发表单标识 (Distributable Form)

表单可通过以下方式标识：

- **FormID**: 十六进制数如 `0x12345~MyPlugin.esp`（详见 FormIDs and You）
- **EditorID**: 文本标识符如 `ElvenMace` 或 `ImperialBow`

> EditorID 比 FormID 更稳定，因为合并/ESL化/压缩时不会改变。

### 1.8 过滤系统 (Filters)

所有 Filter 部分是**乘法关系**（AND），同一部分的表达式是**加法关系**（OR）。

#### 1.8.1 String Filters（字符串过滤）

```
Form = 0x12345|StringExpression1,StringExpression2,...
```

支持的匹配目标：
- NPC 名称 (Name)
- NPC 的 EditorID
- NPC 模板 (Template) 的 EditorID（可匹配所有继承者）
- NPC 的关键词 (Keywords，包括 SPID 分发的)
- NPC 种族的关键词 (Race Keywords)

**表达式修饰符**：

| 修饰符 | 说明 | 示例 |
|--------|------|------|
| `-` (排除) | 放在词前，排除匹配 | `-Guard` → 不匹配 Guard |
| `*` (部分匹配) | 放在词前，允许部分匹配 | `*Guard` → 匹配 "Whiterun Guard" |
| `+` (组合) | 放在词之间，要求全部匹配 | `Whiterun+Guard` → 必须同时有两者 |

> 排除表达式(-X)始终以 AND 方式应用：`A,B,-X` 意味着 `(A OR B) AND NOT X`。
> 单个表达式只能使用一种修饰符。

#### 1.8.2 Form Filters（表单过滤）

```
Form = 0x12345||FormExpression1,FormExpression2,...
```

支持的过滤表单类型：

| Form Type       | Signature | NPC 记录字段    |
|-----------------|-----------|-----------------|
| Combat Style    | CSTY      | ZNAM            |
| Class           | CLAS      | CNAM            |
| Faction         | FACT      | Factions        |
| Race            | RACE      | RNAM            |
| Outfit          | OTFT      | DOFT            |
| Perk            | PERK      | Perks           |
| Specific NPC    | NPC_      | FormID/EDID     |
| NPC's Template  | NPC_      | FormID/EDID     |
| Actor           | ACHR      | FormID/EDID     |
| Voice Type      | VTYP      | VTCK            |
| Known Spell     | SPEL      | Actor Effects   |
| Skin            | ARMO      | WNAM            |
| Editor Location | LCTN      | XLCN            |
| FormList        | FLST      | 递归查找        |

**表单表达式修饰符**：`-` (排除)、`+` (组合)，与 String Filters 相同规则。

> 排除表达式(-X)始终以 AND 方式应用。
> 还可只指定插件名匹配来自特定插件的 NPC：`||MyPlugin.esp`

#### 1.8.3 Level Filters（等级过滤）

```
Form = 0x12345|||LevelExpression,SkillExpression1,...
```

**重要**：只能指定一个 Level Expression，多个则只识别最后一个。

支持的值：

| 值           | 表达式                        |
|-------------|-------------------------------|
| Level       | min/max                       |
| Skill Level | skillIndex(min/max)           |
| Skill Weight| 同 Skill 但前缀 `w`           |

Skill Index (18 个技能)：OneHanded=0, TwoHanded=1, Marksman=2, Block=3, Smithing=4, HeavyArmor=5, LightArmor=6, Pickpocket=7, Lockpicking=8, Sneak=9, Alchemy=10, Speech=11, Alteration=12, Conjuration=13, Destruction=14, Illusion=15, Restoration=16, Enchanting=17

范围语法：
- 闭区间 `min/max`：匹配 min 到 max（含）
- 半开区间 `min` 或 `min/`：从 min 到无穷
- 精确值 `value/value`

#### 1.8.4 Trait Filters（特征过滤）

```
Form = 0x12345||||TraitExpression
```

支持的特征：Female, Male, Unique, Summonable, Child, Leveled, Player's Teammate, Dead

修饰符：`-`(排除)、`/`(组合)。特征支持混合修饰符。

示例：`F` (仅女性), `F/Unique` (女性且独特), `-Dead` (非死亡)

#### 1.8.5 模板 NPC 注意事项

模板 NPC 从其基础模板继承属性。Filter 始终检查最终合并后的 NPC。

对于非 Leveled NPC：
- Final NPC + Base template (直接父模板)

对于 Leveled NPC：
- Original NPC → Base leveled NPC → Base template

### 1.9 Count 或 Package Index

#### Item Count
当分发表单是 Item 时，表示添加数量。可指定范围随机：`2-4`。

#### Package Index
当分发表单是 Package 时，表示插入索引（从 0 开始）。

#### Package List Type
当分发表单是 FormList (Package) 时：

| # | Type                       | NPC 记录 |
|---|----------------------------|----------|
| 0 | Default Package List       | DPLT     |
| 1 | Spectator Override         | SPOR     |
| 2 | Observe Corpse Override    | OCOR     |
| 3 | Guard Warn Override        | GWOR     |
| 4 | Enter Combat Override      | ECOR     |

### 1.10 Chance（概率）

0 到 100 的十进制值。默认 100。可以非常小（如 0.0001）。

#### Deterministic Chance（确定性概率）

在概率值后加 `!`（如 `50!`）使其变为确定性：同一 Actor + 同一存档 = 始终相同结果。影响因素：目标 Actor、玩家角色、源条目。不同存档/不同 NPC 结果不同。

---

## 2. Outfit Distribution

> 适用于 SPID 7.2.0+

### 2.1 概述

SPID 7.2+ 实现了全新的 Per-Actor 服装分发系统。在 Skyrim 默认服装系统之上添加新层，跟踪单个 Actor 的服装，让游戏将其视为新的默认服装。

### 2.2 Per-Actor vs Per-NPC

- **Per-NPC (SPID 6.8.2)**: 同名 NPC 的所有实例使用相同服装
- **Per-Actor (SPID 7.2)**: 每个 NPC 实例可有自己独立的服装

### 2.3 服装解析优先级

分发按以下顺序，最后胜出：

1. Regular Distribution (`Outfit = ...`)
2. Linked Distribution (`LinkedOutfit = ...`)
3. On Death Distribution (`DeathOutfit = ...`)
4. On Death Linked Distribution (`LinkedDeathOutfit = ...`)

使用 `FinalOutfit = ...` 可防止 Linked Distribution 覆盖 Regular Distribution。

### 2.4 死亡 NPC 服装规则

死亡 NPC 原则上不能换装。SPID 仅在以下情况下允许给死亡 NPC 分发服装：
- NPC 存活时 (Regular Distribution)
- NPC 首次被发现死亡时 (Regular + On Death)
- NPC 正在死亡时 (On Death)
- NPC 被发现死亡、无 SPID 服装、且未被搜刮时 (Regular + On Death)

### 2.5 特殊行为

- **复活**: 复活 NPC 恢复 SPID 服装，即使在死亡时被搜刮
- **Disable/Enable**: 保留 SPID 服装
- **Recycleactor**: 恢复为默认服装，本会话内不再分发

### 2.6 兼容性

SPID 识别其他 MOD 使用 `SetOutfit` Papyrus 函数管理服装的情况（如 Simple Outfit System）。当检测到时暂停 SPID 服装，等 MOD 将服装重置回默认后自动恢复。

---

## 3. Exclusive Groups

> 适用于 SPID 7.0.0+

### 3.1 概述

Exclusive Groups 定义一组互斥的可分发表单，同一时间只能分发其中一个。按默认顺序首个通过所有过滤的条目会阻止同组其他条目。

也影响 Linked Distribution 和 On Death Distribution。

### 3.2 语法

```
ExclusiveGroup = GroupName|FormsList
```

- `GroupName`: 任意文本（不允许 `|`）
- `FormsList`: 逗号分隔的 FormID 或 EditorID 列表

### 3.3 修改已有 Exclusive Group

```
ExclusiveGroup = Only One Sword|SteelBattleaxe,-SteelSword
```

可引用已有组名，添加或移除表单（`-` 前缀移除）。

### 3.4 使用场景

替代大量临时关键词的写法。之前：
```ini
Keyword = GetsCoolSword|...|50
Keyword = GetsDecentAxe|-GetsCoolSword,...|50
Item = CoolSword|GetsCoolSword
Item = DecentAxe|GetsDecentAxe
```

之后：
```ini
Item = CoolSword|...|50
Item = DecentAxe|...|50
ExclusiveGroup = Primary Weapon|CoolSword,DecentAxe
```

---

## 4. Linked Distribution

> 适用于 SPID 7.0.0+

### 4.1 概述

Linked Forms 定义无条件分发，通过链接到其他可分发表单实现。当父条目被分发时，所有 Linked Forms 自动分发给同一 NPC。

非递归（不级联），受 Exclusive Groups 控制。

### 4.2 语法

```
LinkedFormType = FormOrEditorID|FormsList|CountOrPackageIndex|Chance
```

- 支持 `LinkedItem`, `LinkedOutfit`, `LinkedSpell` 等所有类型
- 可使用 `LinkedForm` 自动推断类型
- `FormsList` 不支持 `+` 和 `-` 修饰符

### 4.3 Scopes（作用域）

- **默认**: 仅链接同文件内的可分发表单
- **Global**: 使用 `GlobalLinkedFormType` 链接所有配置文件中的表单

### 4.4 Death 版本

```
LinkedDeathFormType = FormOrEditorID|FormsList|CountOrPackageIndex|Chance
GlobalLinkedDeathFormType = ...
```

### 4.5 示例

```ini
; 70% 概率给 Cool Bow
Item = MyCoolBow|NONE|NONE|NONE|NONE|1|70
; 同时给 20 支箭
LinkedItem = ArrowsForMyCoolBow|MyCoolBow|20
; 5% 概率额外给 10 支高级箭
LinkedItem = SuperbArrowsForMyCoolBow|MyCoolBow|10|5
; 用 Exclusive Group 确保只有一种箭
ExclusiveGroup = SingleArrowType|ArrowsForMyCoolBow,SuperbArrowsForMyCoolBow
```

---

## 5. On Death Distribution

> 适用于 SPID 7.1.0+

### 5.1 概述

仅在 NPC 死亡时触发的特殊分发。SPID 6 中称为 DeathItem，现已扩展到所有支持的 Distributable Form。

支持 Exclusive Groups 和 Linked Distribution。

### 5.2 语法

```
DeathFormType = FormOrEditorID|StringFilters|FormFilters|LevelFilters|TraitFilters|CountOrPackageIndex|Chance
```

### 5.3 示例

```ini
; 给濒死的龙添加龙骨
DeathItem = DragonBone|ActorTypeDragon||||2-4
; 标记 RIPDragon 关键词
DeathKeyword = RIPDragon|ActorTypeDragon
```

---

## 6. FormIDs and You

### 6.1 FormID 写入算法

在 `_DISTR` 文件中编写 FormID 的算法：

1. 在 xEdit 中获取 FormID
2. 如果插件是基础游戏插件（Skyrim.esm 或 DLC，**不包括 Creation Club**）→ 跳到步骤 5
3. **仅 MOD 插件**: ESP/ESM → 删除前 2 位（剩 6 位）；ESL(化) → 删除前 5 位（剩 3 位）
4. **仅 MOD 插件**: 在结果末尾追加 `~插件名.esp`（如 `~MyMod.esp`）
5. 删除所有前导零
6. 在前面加上 `0x`

### 6.2 示例

| 来源 | 原始 FormID | 插件类型 | 结果 |
|------|------------|---------|------|
| Skyrim.esm | 00012EB7 | base game | `0x12EB7` |
| Dragonborn.esm | 0401A9B0 | DLC | `0x401A9B0` |
| MyMod.esp (新表单) | 0x00000800 | ESP | `0x800~MyMod.esp` |
| MyMod.esp (覆盖) | 0x000012EB7 | ESP | `0x12EB7~MyMod.esp` |
| MyMod.esl | 0xFE0000800 | ESL | `0x800~MyMod.esl` |

---

## 附录：常见问题

### Q: 如何给特定 NPC 分发服装？
```ini
Outfit = 0x870~MyOutfits.esp|Vigdis,BergritteBattleBorn,Hilde
```

### Q: 如何确保 NPC 只获得一件物品？
使用 Exclusive Groups：
```ini
ExclusiveGroup = Give If Missing|YourItemID
```

### Q: 如何过滤特定位置？
使用 Form Filter 中的 Editor Location (LCTN)：
```ini
Outfit = MyOutfit||DwarvenLocationID
```

### Q: 排除某个 MOD 的所有 NPC？
```ini
Spell = MySpell||-ThatMod.esp
```

### Q: 给玩家 Teammate 分发？
```ini
Item = CoolSword|NONE|NONE|NONE|Player'steammate|NONE|50
```

---

## 参考链接

- MOD 页面: https://www.nexusmods.com/skyrimspecialedition/mods/36869
- 文章页: https://www.nexusmods.com/skyrimspecialedition/mods/36869?tab=articles
- 作者: powerofthree (sasnikol)
