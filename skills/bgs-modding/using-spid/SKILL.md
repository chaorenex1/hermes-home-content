---
name: using-spid
description: Use when creating, editing, debugging, or validating SPID (Spell Perk Item Distributor) _DISTR ini configuration files — triggers "SPID config", "_DISTR", "SPID distribution", "SPID 配置", "给NPC分发", "spell perk item distributor", "distribute items to NPCs". NOT for MO2 install, xEdit conflict resolution, or Papyrus scripting.
---

# Using SPID — Spell Perk Item Distributor

## 概述

本技能用于创建、编辑、调试和验证 SPID (Spell Perk Item Distributor) 的 `_DISTR.ini` 配置文件。SPID 是 powerofthree 开发的 SKSE 插件，在运行时分发法术(Spell)、技能(Perk)、物品(Item)、服装(Outfit)、关键词(Keyword)等表单给 NPC，不修改插件也不影响存档。

## 何时使用

- 用户要求创建或修改 `_DISTR.ini` 配置文件
- 需要将法术/技能/物品/服装等分发给特定 NPC
- 调试 SPID 分发不生效的问题
- 将 xEdit FormID 转换为 SPID 格式
- 验证 SPID 配置语法

## 何时不用

- MO2 安装/管理 MOD → 使用 `bgs-mo2` 相关技能
- xEdit 记录查看/冲突解决 → 使用 `xedit-automation`
- Papyrus 脚本编译 → 使用 `using-bgs-papyrus`
- 判断 MOD 是否应该加入模组包 → 使用 `evaluating-bgs-mods`

## 前置知识

完整语法参考: `references/spid-complete-reference.md`（基于 N 网文章整理）

## 工作流程

### 1. 理解需求

明确用户想要：
- 分发什么类型的表单？（Spell/Perk/Item/Outfit/Keyword/Faction/Skin/Shout/Package）
- 目标 NPC 是谁？（按名称/种族/阵营/等级/性别/位置等过滤）
- 概率/数量是多少？
- 是否需要互斥？（Exclusive Groups）
- 是否需要条件链接？（Linked Distribution）
- 是否死亡时触发？（On Death Distribution）

### 2. 查询 KB 获取最新信息

```text
bgs_kb_query({
  query: "SPID distribution _DISTR syntax form types filters",
  domains: ["install-planning", "load-order"],
  games: ["SkyrimSE"]
})
```

### 3. 编写配置

#### 基本语法

```ini
; 注释以分号开头
FormType = FormID|StringFilters|FormFilters|LevelFilters|TraitFilters|Count|Chance
```

#### 常用模板

**给特定 NPC 分发物品：**
```ini
Item = 0x800~MyMod.esp|NPCName1,NPCName2|NONE|NONE|NONE|1|100
```

**按种族分发法术：**
```ini
Spell = MyFireSpell|NONE|NordRace|NONE|NONE|NONE|50
```

**按阵营分发技能（带排除）：**
```ini
Perk = MyPerk|NONE|WhiterunGuardFaction,-CommanderCaius|NONE|NONE|NONE|100
```

**按等级分发物品（随机数量）：**
```ini
Item = 0x801~MyMod.esp|NONE|NONE|10/30|NONE|2-5|70
```

**仅女性 NPC：**
```ini
Outfit = 0x870~MyOutfits.esp|NONE|NONE|NONE|F|NONE|25
```

**给死亡 NPC 分发：**
```ini
DeathItem = DragonBone|ActorTypeDragon||||2-4
```

**使用 Exclusive Groups（互斥）：**
```ini
Item = CoolSword|NONE|NONE|NONE|NONE|NONE|50
Item = DecentAxe|NONE|NONE|NONE|NONE|NONE|50
ExclusiveGroup = Primary Weapon|CoolSword,DecentAxe
```

**使用 Linked Distribution（链接分发）：**
```ini
Item = MyCoolBow|NONE|NONE|NONE|NONE|1|70
LinkedItem = AmmoForBow|MyCoolBow|20
```

**排除特定 MOD 的所有 NPC：**
```ini
Spell = MySpell||-SomeOtherMod.esp
```

**部分名称匹配：**
```ini
Keyword = MyKeyword|*Guard|NONE|NONE|NONE
; 匹配所有名字中含 "Guard" 的 NPC
```

**组合条件（必须同时满足）：**
```ini
Outfit = MyOutfit|Whiterun+Guard|NONE|NONE|NONE|NONE|100
; 仅匹配同时有 Whiterun 和 Guard 的 NPC
```

### 4. FormID 转换

SPID 使用特殊的 FormID 格式。转换规则：

1. 在 xEdit 中获取 FormID
2. 基础游戏插件 (Skyrim.esm/DLC) → 直接使用，去前导零，加 `0x`
3. MOD 插件 ESP/ESM → 删前 2 位 + `~插件名.esp`
4. MOD 插件 ESL → 删前 5 位 + `~插件名.esl`

**示例：**
| 来源 | FormID | 结果 |
|------|--------|------|
| Skyrim.esm | 00012EB7 | `0x12EB7` |
| MyMod.esp | 0x00000800 | `0x800~MyMod.esp` |
| MyMod.esl | 0xFE0000800 | `0x800~MyMod.esl` |

> 优先使用 EditorID（如 `IronSword`）而非 FormID，因为 EditorID 在合并/ESL化时不变。

### 5. 验证配置

检查清单：
- [ ] 文件命名包含 `_DISTR` 后缀（如 `MyMod_DISTR.ini`）
- [ ] FormID 格式正确（基础游戏无 `~plugin`，MOD 插件有 `~plugin`）
- [ ] 管道符 `|` 数量正确（6 个管道符分隔 7 个字段）
- [ ] Filter 修饰符使用正确（单表达式只能用一种修饰符）
- [ ] Level Filter 只有一个 Level Expression
- [ ] ExclusiveGroup 语法正确
- [ ] 文件放在 `Data/` 目录下

### 6. 调试

常见问题排查：

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| 不分发 | FormID 格式错误 | 检查 FormID 转换 |
| 不分发 | 过滤器太严格 | 简化过滤条件测试 |
| 不分发 | 文件命名不含 _DISTR | 重命名文件 |
| 部分 NPC 未获得 | 被 Exclusive Group 阻止 | 检查互斥组逻辑 |
| 所有 NPC 都获得 | 过滤器为空或太宽 | 添加过滤条件 |
| ESL 插件 FormID 错误 | 删了 2 位而非 5 位 | ESL 需删 5 位 |

启用 SPID 日志：在 `Data/SKSE/Plugins/po3_SpellPerkItemDistributor.ini` 中设置日志级别。

### 7. 输出规范

完成配置后，提供：
- 完整的 `_DISTR.ini` 文件内容
- FormID 转换说明（如涉及）
- 推荐的 MO2 安装方式（新建空 MOD，将 ini 放入）
- 加载顺序建议（字母顺序决定优先级）

## 注意事项

- SPID 配置放在 `Data/` 目录，MO2 中通过 MOD 文件夹的 `Data/` 子路径提供
- 文件加载按字母顺序，想高优先级用 `AAA_` 前缀，低优先级用 `ZZZ_` 前缀
- SPID 分发不修改存档，随时可安全安装/卸载
- EditorID 比 FormID 更稳定，优先使用
- Keyword 会自动按依赖排序，无需手动排列
- SleepOutfit 和 Skin 不能用 `Form` 自动推断，必须显式指定
- 排除表达式(-X)始终以 AND 方式与正匹配组合：`A,B,-X` = `(A OR B) AND NOT X`

## 参考

- 完整语法参考: `references/spid-complete-reference.md`
- MOD 页面: https://www.nexusmods.com/skyrimspecialedition/mods/36869
- 文章页面: https://www.nexusmods.com/skyrimspecialedition/mods/36869?tab=articles
