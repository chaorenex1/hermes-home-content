# Keyword Item Distributor (KID) — 完整参考文档

> **Nexus Mods ID**: 55728  
> **游戏**: Skyrim Special Edition  
> **作者**: powerofthree  
> **版本**: 4.0.6  
> **URL**: https://www.nexusmods.com/skyrimspecialedition/mods/55728

---

## 1. 基本信息

| 属性 | 值 |
|------|-----|
| 名称 | Keyword Item Distributor (KID) |
| 当前版本 | 4.0.6 |
| 上传日期 | 30 Jun 2026 |
| 文件大小 | 10.0MB |
| Endorsements | 33,173 |
| Unique DLs | 1,548,539 |
| Total DLs | 5,947,208 |
| Total Views | 3,177,008 |
| 被引用 (usedBy) | 582 个 MOD |

---

## 2. 核心功能

SKSE 插件，在游戏启动时通过配置文件（`*_KID.ini`）向以下类型的物品动态分配关键词：

Weapon, Armor, Ammo, Magic Effect, Potion, Scroll, Location, Ingredient, Book, Misc Item, Key, Soul Gem, Spell, Activator, Flora, Furniture, Race, Talking Activator, Enchantment

---

## 3. 前置需求 (Requirements)

### 硬性依赖
- **SKSE64** (Skyrim Script Extender)
- Skyrim SE **1.5.39+** / Skyrim VR
- **Address Library for SKSE Plugins** (meh321)

### 可选/条件依赖
- **MergeMapper** — 推荐 VR 用户使用
- **powerofthree's Tweaks**
- **VR Address Library for SKSEVR** — VR 用户必需

---

## 4. 配置文件格式

### 文件约定
- 放置在 `Data/` 目录下
- 文件名后缀必须是 `_KID.ini`（例如 `MyMod_KID.ini`）

### 条目语法
```
Keyword = formID~esp(OR)keywordEditorID|type|strings,formIDs(OR)editorIDs|traits|chance
```

### 参数详解

#### 4.1 Keyword（关键词标识）

| 方式 | 格式 | 说明 |
|------|------|------|
| FormID | `0x12345~MyMod.esp` | 去掉前导零的 FormID；Skyrim/DLC 记录可省略 esp |
| EditorID | `MyKeywordName` | 若关键词不存在，KID 会动态创建（可用 `GetKeywordString` 查询） |

#### 4.2 Type（目标物品类型）

支持的类型列表：

```
Weapon          — 武器
Armor           — 护甲
Ammo            — 弹药
Magic Effect    — 魔法效果
Potion          — 药水
Scroll          — 卷轴
Location        — 地点
Ingredient      — 炼金材料
Book            — 书籍
Misc Item       — 杂项
Key             — 钥匙
Soul Gem        — 灵魂石
Spell           — 法术
Activator       — 激活器
Flora           — 植物
Furniture       — 家具
Race            — 种族
Talking Activator — 对话激活器
Enchantment     — 附魔
```

#### 4.3 Strings（字符串过滤器）

| 过滤方式 | 示例 | 说明 |
|----------|------|------|
| 物品名称 | `Iron Sword` | 精确匹配物品名 |
| 效果原型 (Archetype) | `Absorb` | 用于 Magic Effect/Spell/Enchantment/Scroll/Potion |
| Actor Value | `Destruction` | 用于 Book/Magic Effect/Spell/Enchantment/Scroll/Potion/Weapon |
| Nif 路径 | `*steelmace.nif` | 必须以 `.nif` 结尾；不支持 Armor |

#### 4.4 FormIDs/EditorIDs（指定物品）

| 方式 | 语法 | 说明 |
|------|------|------|
| 指定物品 (FormID) | `0x1234~MyMod.esp, 0x4567~MyMod.esp` | 逗号分隔 |
| 指定物品 (EditorID) | `MySwordID, MyArmorID` | 逗号分隔 |
| MOD 全部物品 | `MyMod.esp, MyOtherMod.esp` | 仅写 esp 名称 |

#### 4.5 过滤器修饰符 (Filter Modifiers)

| 修饰符 | 含义 |
|--------|------|
| `X` | 必须精确匹配 X |
| `*X` | 部分匹配 — name/editorID/keyword 包含 X |
| `-X` | 排除 — 必须不匹配 X |
| `-*X` | 排除部分 — 必须不包含 X |
| `A+B` | AND 组 — 必须同时匹配 A 和 B |
| `A+B, C+D` | 匹配组 A+B **或** 组 C+D |

多条目用逗号分隔，字符串和 FormID 过滤器可混合使用。

#### 4.6 Traits（物品特性过滤器）

按类型有不同的 traits，可用 `-` 前缀做反向匹配（如 `-H` = 所有非 hostile 的 magic effect）。

**Magic Effect traits（部分）:**
- `H` — Hostile（敌对）
- `-H` — 非敌对
- `E` — 有附魔效果的物品
- `-E` — 无附魔效果的物品

**Potion traits:**
- `P` — Poison（毒药）
- `F` — Food（食物）

**Book traits:**
- `S` — Skill/Spell Tome（技能书/法术书）

（完整的 Armor/Weapon/Ammo/Ingredient/Soul Gem/Spell/Furniture traits 详见 MOD 页面 spoiler 区域）

#### 4.7 Chance（概率）

- 范围: `0.0` ~ `100.0`
- 默认: 100（留空或 `NONE`）
- 固定概率，跨存档一致（某物品要么分配关键词，要么不分配）

---

## 5. 配置示例

```ini
; 给 Mysticism.esp 中所有 Magic Effect 添加 MysticismSpells 关键词
Keyword = MysticismSpells|Magic Effect|MysticismMagic.esp

; 给匹配的 Magic Effect 添加 NoviceDestruction，技能等级 20-25
Keyword = NoviceDestruction|Magic Effect|NONE|20(0/25)

; 给所有毒食物添加 PoisonousFood 关键词
Keyword = PoisonousFood|Potion|NONE|P,F

; 给所有非附魔重型护手（同时含 ArmorHeavy 和 ArmorGauntlet 关键词的 Armor）
Keyword = 0x1234~MyArmorMod.esp|Armor|ArmorHeavy+ArmorGauntlet|-E

; 按名称模糊匹配所有 bound arrow
Keyword = MysticalAmmo|Ammo|*Bound

; 给指定 FormID 的 Magic Effect 添加太阳伤害关键词
Keyword = MagicDamageSun|Magic Effect|0x02019C9D,0x0200A3BB,0x0200A3BC

; 给所有教授毁灭系法术的书添加关键词（方式一：用 AV）
Keyword = SpellTomeDestruction|Book|NONE|S,20
; 方式二：用字符串
Keyword = SpellTomeDestruction|Book|Destruction|S

; 给所有 Absorb 原型的 Magic Effect 添加 MagicAbsorb
Keyword = MagicAbsorb|Magic Effect|Absorb

; 按 Nif 路径匹配所有钢制钉头锤
Keyword = SteelMace|Weapon|*steelmace.nif
```

---

## 6. 文件列表

### Main File
| 文件 ID | 版本 | 大小 | 上传日期 |
|---------|------|------|----------|
| 770033 | 4.0.6 | 10.0MB | 30 Jun 2026 |

FOMOD 安装器。支持 SE 1.5.97 / VR 1.4.15 / AE 1.6+。

### Old Files（最近版本）
| 版本 | 大小 | 上传日期 | 备注 |
|------|------|----------|------|
| 4.0.5 | 10.0MB | 25 Jun 2026 | |
| 4.0.4 | 7.0MB | 25 Jun 2026 | |
| 4.0.3 | 9.4MB | 24 Jun 2026 | |
| 4.0.2 | 9.3MB | 24 Jun 2026 | |
| 4.0.1 | 9.4MB | 24 Jun 2026 | |
| 4.0.0 | 9.4MB | 24 Jun 2026 | 93% faster parsing |
| 3.4.0 | 8.3MB | 12 Mar 2024 | 1.1M unique DLs |
| 2.x 及更早 | — | — | 已过时 |

---

## 7. 权限 (Permissions)

| 权限类型 | 状态 |
|----------|------|
| 其他用户资产 | 全部属于作者，或来自自由使用的 modder 资源 |
| 上传权限 | ✅ 允许（需署名） |
| 修改权限 | ✅ 允许（需署名） |
| 转换权限 | ✅ 允许（需署名） |
| 资产使用 | ✅ 允许（需署名） |
| 付费 MOD 中使用 | ❌ **禁止** |
| 赚取 Donation Points | ✅ 允许 |
| Donation Points 系统 | ✅ 已加入 |

---

## 8. 更新日志 (Changelogs)

| 版本 | 日期 | 变更 |
|------|------|------|
| **4.0.6** | 30 Jun 2026 | 修复 AND mod 过滤器 + 普通过滤器同时使用时的关键词分配 |
| **4.0.5** | 25 Jun 2026 | 修复通配符过滤器排序；添加 verbose logging 配置项 |
| **4.0.4** | 25 Jun 2026 | 修复 None(-1) AV 的 entry validation；修复不同大小写的重复关键词创建；日志输出所有被分配关键词的表单 |
| **4.0.3** | 24 Jun 2026 | 修复所有正向过滤器失败时条目未被跳过的回归 |
| **4.0.2** | 24 Jun 2026 | 优化全局关键词查找；恢复部分字符串过滤器行为至 3.x 版本 |
| **4.0.1** | 24 Jun 2026 | 合并重复条目；修复关键词互依赖解析回归 |
| **4.0.0** | 24 Jun 2026 | **重大更新**：配置解析速度提升 93%；支持堆叠 `-` 和 `*` 修饰符（如 `-*Daedric`）；AND 组内支持修饰符；traits 支持小数和负数 |
| **3.4.0** | 12 Mar 2024 | 修复 spell school trait 不适用于 powers/lesser powers；修复首个加载关键词按 editorID 字母排序的 bug |

---

## 9. 调试与日志

- 日志文件路径: `My Games/Skyrim Special Edition/SKSE/po3_KeywordItemDistributor.log`
- v4.0.5+ 支持配置文件控制 verbose logging

---

## 10. 安装方式

标准 Mod Manager 安装（MO2 / Vortex）。FOMOD 安装器自动检测游戏版本。

---

## 11. 作者备注

- 基于 CommonLibSSE (Ryan/SniffleMan)
- INI 解析基于 SimpleINI
- 无额外文件贡献者
- 无额外权限说明

---

## 12. 关键类型速查

| 分类 | 内容 |
|------|------|
| **MOD 类型** | SKSE 插件 / 框架 / 关键词分配系统 |
| **作用时机** | 游戏启动时一次性分配 |
| **配置驱动** | INI 文件，无需 ESP/ESL 插件槽 |
| **版本兼容** | SE 1.5.97 / AE 1.6+ / VR 1.4.15 |
| **生态地位** | 582 个 MOD 依赖 — 核心基础设施级 MOD |
| **性能** | v4.0 起解析速度提升 93% |
| **稳定性** | 维护活跃（2026.06 仍在更新） |
