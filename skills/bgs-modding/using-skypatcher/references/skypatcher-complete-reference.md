# SkyPatcher 完整参考文档

> **来源**: [SkyPatcher - Nexus Mods #106659](https://www.nexusmods.com/skyrimspecialedition/mods/106659?tab=articles)
> **作者**: Zzyxzz
> **类型**: SKSE 运行时 Patcher，通过 INI 配置文件修改游戏数据，无需 ESP

---

## 一、通用信息 (General Information)

### 1.1 文件夹结构

```
Data/
└── SKSE/
    └── Plugins/
        ├── SkyPatcher.dll
        ├── SkyPatcher.ini
        └── SkyPatcher/                  ← INI 文件放置于此
            ├── ammo/
            ├── armor/
            ├── npc/
            ├── race/
            ├── weapon/
            └── ...                      ← 按 patcher 类型
```

> INI 文件根据类型放入对应文件夹。可在各分类下自由创建子文件夹，例如：
> `SKSE/Plugins/SkyPatcher/npc/myModFolder/bandits/myfile.ini`

### 1.2 INI 文件类型

| 类型 | 命名格式 | 说明 |
|------|----------|------|
| 通用 | `someIniFile.ini` | 始终加载 |
| 条件 | `Skyrim.esm.ini` / `SomeMod.esp.ini` | 仅当对应插件在 load order 中激活时才加载 |

> **注意**：条件 INI 必须放在独立子文件夹中，避免被 mod manager 覆盖。
>
> ❌ 坏: `npc/myModFolder/Skyrim.esm.ini`（两个 mod 共享同一路径）
> ✅ 好: `npc/myModFolder/ModA/Skyrim.esm.ini` + `npc/myModFolder/ModB/Skyrim.esm.ini`

### 1.3 加载顺序与冲突

- INI 文件按字母顺序 0-z 加载
- 后加载（z）覆盖先加载（m）的同名字段
- 多个 INI 可同时操作同一对象的不同字段，不会冲突
- add/remove 操作天然不冲突

### 1.4 Patch 字符串结构

```
Filter 部分 : Operation 部分
```

格式: `filterByXXX=...:operationKey=value`

- `Filter` — 筛选要 patching 的对象
- `Operation` — 对筛选出的对象执行的操作
- 复数形式的 filter（如 `filterByWeapons`, `filterByKeywords`）可接受多个值，逗号分隔
- 多个操作间用 `:` 连接

示例:
```ini
filterByWeapons=Skyrim.esm|00012EB7, Skyrim.esm|00013790:attackDamage=99:weight=0:keywordsToAdd=myMod.esp|20000223
```

### 1.5 FormID 与 EditorID

SkyPatcher 同时支持 **FormID** 和 **EditorID**（部分操作例外）。

**不支持 EditorID 的操作**:
- NPC Patcher: `objectsToAdd`, `factionsToAdd`
- Outfit Patcher: `formsToReplace`

示例:
```ini
filterByAmmos=IronArrow:weight=0.5
filterByAmmos=Skyrim.esm|1397D:weight=0.5
```

### 1.6 注释

以 `;` 开头:
```ini
;这是注释
```

---

## 二、Patcher 类型速查表

| # | Patcher 类型 | 文件夹 | 核心功能 |
|---|-------------|--------|----------|
| 1 | Weapon | weapon/ | 武器属性、模型、声音、附魔 |
| 2 | Armor | armor/ | 护甲属性、槽位、模型、附魔 |
| 3 | NPC | npc/ | NPC 属性、技能、外观、物品栏 |
| 4 | Race | race/ | 种族属性、身高体重、技能加成 |
| 5 | Race Hook | raceHook/ | 种族攻击数据（Attack Data） |
| 6 | Leveled List | leveledlist/ | 等级列表增删改 |
| 7 | Container | container/ | 容器物品增删改 |
| 8 | FormList | formlist/ | FormList 增删改 |
| 9 | Outfit | outfit/ | 套装增删改 |
| 10 | Spell | spell/ | 法术属性、Magic Effect、消耗 |
| 11 | Scroll | scroll/ | 卷轴属性、Magic Effect |
| 12 | Enchantment | enchantment/ | 附魔属性、Magic Effect |
| 13 | Alchemy/Ingestible | alchemy/ | 药剂/食物属性、效果 |
| 14 | Ingredient | ingredient/ | 炼金材料属性、效果 |
| 15 | Magic Effect | magiceffect/ | 魔法效果底层属性 |
| 16 | Constructible Object | constructibleobject/ | 锻造配方修改 |
| 17 | Location | location/ | 地点属性、音乐、关键词 |
| 18 | Cell | cell/ | 单元格光照、雾效、水体 |
| 19 | Encounter Zone | encounterzone/ | 遭遇区域等级范围 |
| 20 | Reference | reference/ | 引用对象禁用 |

---

## 三、各 Patcher 详细配置

### 3.1 Weapon Patcher (weapon/)

#### Filters
| Filter | 说明 | 逻辑 |
|--------|------|------|
| `filterByModNames` | 按 mod 筛选 | 逗号分隔，可与其他 filter 组合 |
| `filterByWeapons` | 按 FormID 指定武器 | 逗号分隔 |
| `filterByWeaponsExcluded` | 排除武器 | 逗号分隔 |
| `filterByKeywords` | 按关键词（AND） | 逗号分隔 |
| `filterByKeywordsOr` | 按关键词（OR） | 逗号分隔 |
| `filterByKeywordsExcluded` | 排除关键词 | 逗号分隔 |
| `filterByEditorIdContains` | EditorID 包含（AND） | 逗号分隔 |
| `filterByEditorIdContainsOr` | EditorID 包含（OR） | 逗号分隔 |
| `filterByEditorIdContainsExcluded` | EditorID 排除 | 逗号分隔 |
| `hasPlugins` | 用户需有这些插件（AND） | 逗号分隔 |
| `hasPluginsOr` | 用户需有这些插件（OR） | 逗号分隔 |
| `filterByFirstPersonModelOr` | 第一人称模型筛选 | 逗号分隔 |
| `filterBySkills` | 武器技能筛选 | `onehanded/twohanded/marksman` 等 |
| `filterByAnimationTypeOr` | 动画类型筛选 | `onehandsword/bow/crossbow` 等 |
| `restrictToFlags` | 限制标志 | 目前仅 `boundweapon` |
| `restrictToSkills` | 限制技能类型 | 逗号分隔 |

> `filterByWeapons/Excluded`, `filterByKeywords/Or/Excluded`, `filterByHasAmmoFromWeaponList` 彼此独立（非 AND）

#### Operations
| Operation | 说明 | 示例 |
|-----------|------|------|
| `fullName` | 改名（`~...~` 包围） | `fullName=~神剑~` |
| `attackDamage` | 设置攻击力 | `attackDamage=35` |
| `attackDamageMult` | 攻击力乘数 | `attackDamageMult=1.5` |
| `attackDamageToAdd` | 攻击力加法 | `attackDamageToAdd=35` |
| `critDamage` | 设置暴击伤害 | `critDamage=12` |
| `critPercentMult` | 暴击倍率乘数 | `critPercentMult=2.5` |
| `critDamageSetToBase` | 暴击=基础伤害 | `critDamageSetToBase=true` |
| `critDamageToAdd` | 暴击伤害加法 | `critDamageToAdd=6` |
| `critDamageMult` | 暴击倍率乘法 | `critDamageMult=1.25` |
| `bashDamage` | 设置格挡伤害 | |
| `weight` | 设置重量 | `weight=1.5` |
| `weightMult` | 重量乘数 | |
| `value` | 设置价值 | `value=45` |
| `valueMult` | 价值乘数 | |
| `speed` | 设置速度 | |
| `speedMult` | 速度乘数 | |
| `reach` | 设置攻击范围 | |
| `rangeMin` | 最小射程 | |
| `rangeMax` | 最大射程 | |
| `stagger` | 设置硬直 | |
| `enchantAmount` | 附魔充能量 | |
| `model` | 替换模型（FormID） | `model=Skyrim.esm\|3DE2A` |
| `modelFirstPerson` | 第一人称模型 | |
| `equipSound` | 装备音效 | `equipSound=null` 清除 |
| `unequipSound` | 卸下音效 | |
| `attackFailSound` | 攻击失败音效 | |
| `impactDataSet` | 冲击数据集 | |
| `templateWeapon` | 模板武器 | |
| `altBlockMaterialType` | 格挡材质类型 | |
| `blockBashImpactDataSet` | 格挡冲击数据集 | |
| `equipSlot` | 装备槽位 | |
| `weaponHitType` | 命中类型 | `normal/dismember/explode/no` |
| `soundLevel` | 声音等级 | `loud/normal/silent/veryloud/quiet` |
| `animationType` | 动画类型 | `onehandsword/dagger/axe/mace/bow/...` |
| `skillType` | 技能类型 | `onehanded/twohanded/marksman/block/...` |
| `objectEffect` | 对象效果 | `objectEffect=null` 清除 |
| `keywordsToAdd` | 添加关键词 | |
| `keywordsToRemove` | 移除关键词 | |
| `mirrorWeapon` | 镜像武器（复制外观+数据） | `mirrorWeapon=Skyrim.esm\|000139B9` |
| `minX/minY/minZ` | 对象边界 | |
| `maxX/maxY/maxZ` | 对象边界 | |

**武器动画类型**: `handtohandmelee, onehandsword, onehanddagger, onehandaxe, onehandmace, twohandsword, twohandaxe, bow, staff, crossbow`

**武器技能类型**: `onehanded, twohanded, marksman, block, smithing, heavyarmor, lightarmor, pickpocket, lockpicking, sneak, alchemy, speechcraft, alteration, conjuration, destruction, illusion, restoration, enchanting`

**mirrorWeapon 复制内容**: 模型(世界+第一人称)、所有音效、动画数据、远程数据、冲击数据、格挡材质、装备槽位、图标

---

### 3.2 Armor Patcher (armor/)

#### Filters
| Filter | 说明 |
|--------|------|
| `filterByModNames` | 按 mod 筛选 |
| `filterByArmors` | 按 FormID 指定护甲 |
| `filterByArmorsExcluded` | 排除护甲 |
| `filterByArmorTypes` | 类型: `heavy, light, clothing` |
| `filterByArmorTypesExcluded` | 排除类型 |
| `filterByKeywords/Or/Excluded` | 关键词筛选 |
| `filterByBipedSlots/Or/Excluded` | Biped 槽位筛选 |
| `filterByEditorIdContains/Or/Excluded` | EditorID 筛选 |
| `filterByNameContains/Or/Excluded` | 名称包含 |
| `filterByArmorAddons/Or/Excluded` | Armor Addon 筛选 |
| `hasPlugins/hasPluginsOr` | 插件检测 |
| `restrictToBipedSlots` | 限制到特定槽位 |
| `restrictToKeywords` | 限制到特定关键词 |

> `filterByArmors/Excluded` 和 `filterByKeywords/Or/Excluded` 彼此独立

#### Operations
| Operation | 说明 |
|-----------|------|
| `fullName` | 改名 |
| `damageResist` | 护甲值 |
| `damageResistMultiply` | 护甲值乘数 |
| `damageResistMatch` | 匹配另一护甲的护甲值 |
| `dwMatch` | 匹配护甲值+重量 |
| `objectEffect` | 附魔/对象效果（`null` 清除） |
| `enchantAmount` | 附魔充能量 |
| `weight/value` | 重量/价值 |
| `weightMult/valueMult` | 重量/价值乘数 |
| `armorType` | 类型: `lightarmor/heavyarmor/clothing` |
| `mirrorArmor` | 镜像护甲 |
| `modelMatch` | 模型匹配 |
| `templateArmor` | 模板护甲 |
| `armorAddonsToAdd/ToRemove` | Armor Addon 增删 |
| `clearArmorAddons` | 清除所有 Armor Addon |
| `bipedSlotsToAdd/ToRemove` | Biped 槽位增删 |
| `keywordsToAdd/ToRemove` | 关键词增删 |
| `setFlags/removeFlags` | 标志: `nonplayable, shield` |
| `minX/Y/Z, maxX/Y/Z` | 对象边界 |
| `pickUpSound/putDownSound` | 捡起/放下音效 |
| `equipSlot` | 装备槽位 |
| `altBlockMaterialType` | 格挡材质类型 |
| `blockBashImpactDataSet` | 格挡冲击数据集 |

**mirrorArmor 复制内容**: Biped模型数据、Armor Addon、世界模型、物品栏图标、捡起/放下音效、装备槽位、格挡冲击数据集、格挡材质类型、护甲值和价值

#### Biped Slot Index
```
0=Head  1=Hair  2=Body  3=Hand  4=Forearms  5=Amulet  6=Ring  7=Feet
8=Calves  9=Shield  10=Tail  11=LongHair  12=Circlet  13=Ears
14=ModMouth  15=ModNeck  16=ModChestPrimary  17=ModBack  18=ModMisc1
19=ModPelvisPrimary  20=DecapitateHead  21=Decapitate  22=ModPelvisSecondary
23=ModLegRight  24=ModLegLeft  25=ModFaceJewelry  26=ModChestSecondary
27=ModShoulder  28=ModArmLeft  29=ModArmRight  30=ModMisc2  31=FX01
```

---

### 3.3 NPC Patcher (npc/)

#### Filters
| Filter | 说明 |
|--------|------|
| `filterByModNames` | 按 mod 筛选 |
| `filterByNpcs` | 按 FormID 指定 NPC |
| `filterByNpcsExcluded` | 排除 NPC |
| `filterByRaces` | 按种族 |
| `filterByDefaultOutfits` | 按默认套装 |
| `filterByKeywords/Or/Excluded` | 关键词筛选 |
| `filterByEditorIdContains/Or/Excluded` | EditorID 筛选 |
| `filterByFactions/Or/Excluded` | 阵营筛选 |
| `filterByClass/filterByClassExclude` | 职业筛选 |
| `filterByPCLevelMult` | PC等级乘数标志 |
| `filterByAutoCalc` | 自动计算标志 |
| `filterByEssential` | 重要NPC标志 |
| `filterByProtected` | 受保护标志 |
| `filterByUnique` | 唯一标志 |
| `filterByGender` | `male/female` |
| `filterByLevel` | 等级筛选（支持范围 `< > <= >=`） |
| `restrictToSkeletonPath` | 限制骨架路径 |
| `filterNameContains/Or/Excluded` | 名称包含 |
| `filterByVoiceTypesOr` | 语音类型（OR） |
| `restrictToGender` | `male/female` |
| `restrictToMaleModelContains` | 限制男性模型路径包含 |
| `restrictToSkill` | 限制技能范围 `skill~min~max` |

> `filterByNpcs/Excluded`, `filterByRaces`, `filterByKeywords/Or/Excluded` 彼此独立

#### Operations

**外观**
| Operation | 说明 |
|-----------|------|
| `fullName` | 改名 |
| `race` | 改变种族 |
| `voiceType` | 语音类型 |
| `outfitDefault` | 默认套装 |
| `outfitSleep` | 睡眠套装 |
| `class` | 职业 |
| `skin` | 皮肤（`null` 清除） |
| `weight` | 体重 |
| `height` | 身高 |
| `level` | 等级 |
| `deathItem` | 死亡物品（`null` 清除） |

**属性 (changeStats)**
| Operation | 说明 |
|-----------|------|
| `health/stamina/magicka` | 直接设置 |
| `calcHealth/calcStamina/calcMagicka` | 基于职业+属性权重计算 |
| `healthMult/staminaMult/magickaMult` | 乘法 |
| `healthBonus/staminaBonus/magickaBonus` | calc 模式下的额外加成 |
| `levelRange` | `levelRange=25~100` 等级范围插值 |

**技能 (changeSkills)**
```
alchemy, alteration, block, conjuration, destruction, enchanting,
heavyarmor, illusion, lightarmor, lockpicking, marksman, onehanded,
pickpocket, restoration, smithing, sneak, speechcraft, twohanded
```

**标志 setFlags/removeFlags**: `female, essential, ischargenfacepreset, respawn, autocalcstats, unique, doesntaffectstealthmeter, pclevelmult, usestemplate, calcforalltemplates, protected, norumors, summonable, doesntbleed, bleedoutoverride, oppositegenderanims, simpleactor, loopedscript, noactivation, loopedaudio, isghost, invulnerable`

**模板标志 setTemplateFlags/removeTemplateFlags**: `traits, stats, factions, spells, aidata, aipackages, unused, basedata, inventory, script, aidefpacklist, attackdata, keywords, copiedtemplate`

**其他**
| Operation | 说明 |
|-----------|------|
| `perksToAdd` | 添加 Perk |
| `spellsToAdd/ToRemove` | 法术增减 |
| `levSpellsToAdd/ToRemove` | 等级法术增减 |
| `shoutsToAdd/ToRemove` | 龙吼增减 |
| `keywordsToAdd/ToRemove` | 关键词增减 |
| `factionsToAdd=FormID=rank` / `factionsToRemove` | 阵营增减 |
| `objectsToAdd=FormID=count` | 物品添加 |
| `addOnceToInventory=FormID~count` | 添加（不重复） |
| `objectsToReplace=旧~新` | 替换物品 |
| `objectsToRemove` | 移除物品 |
| `removeInventoryObjectsByKeywords` | 按关键词移除 |
| `removeInventoryObjectsByCount=FormID~count` | 按数量移除 |
| `clearInventory=true` | 清空物品栏 |
| `setRandomVisualStyle=FormList~chance~copyVoice` | 随机外观 |
| `addRandomVisualStyle` | 添加外观样式 |
| `copyVisualStyle` | 复制外观 |
| `setAggression` | `calmed/unaggressive/aggressive/veryaggressive/frenzied` |
| `setAssistance` | `helpsnobody/helpsallies/helpsfriends` |
| `setConfidence` | `cowardly/cautious/average/brave/foolhardy` |
| `setMood` | `neutral/angry/fear/happy/sad/surprised/puzzled/disgusted` |
| `setMorality` | `anycrime/violenceagainstenemy/propertycrimeonly/nocrime` |
| `aggressionRadiusBehavior` | true/false |
| `aggressionRadiusRanges` | `attack~1000, warn~2000` |

---

### 3.4 Race Patcher (race/)

#### Filters
| Filter | 说明 |
|--------|------|
| `filterByModNames` | 按 mod 筛选 |
| `filterByRaces/Excluded` | 种族筛选 |
| `filterByKeywords/Or/Excluded` | 关键词筛选 |
| `filterByMaleModelContains` | 男性模型路径包含 |
| `filterByFemaleModelContains` | 女性模型路径包含 |
| `filterByVoiceTypeOr` | 语音类型（OR） |

#### Operations

| Operation | 类型 | 说明 |
|-----------|------|------|
| `heightMale/Female` | 设置 | 身高 |
| `weightMale/Female` | 设置 | 体重 |
| `baseMass` | 设置 | 基础质量 |
| `baseMassMult` | 乘数 | 基础质量乘数 |
| `baseCarryweight` | 设置 | 基础负重 |
| `baseCarryweightMult` | 乘数 | 负重乘数 |
| `startingHealth/Stamina/Magicka` | 设置 | 起始属性 |
| `startingHealth/Stamina/MagickaMult` | 乘数 | 起始属性乘数 |
| `regenHealth/Stamina/Magicka` | 设置 | 再生速率 |
| `regenHealth/Stamina/MagickaMult` | 乘数 | 再生乘数 |
| `damageUnarmed` | 设置 | 徒手伤害 |
| `damageUnarmedMult` | 乘数 | 徒手伤害乘数 |
| `reachUnarmed` | 设置 | 徒手范围 |
| `reachUnarmedMult` | 乘数 | 徒手范围乘数 |
| `accelerationRate/decelerationRate` | 设置 | 加/减速率 |
| `accelerationAngularRate` | 设置 | 角加速度 |
| `aimAngleTolerance` | 设置 | 瞄准角度容差 |
| `skin` | 设置 | 皮肤（FormID） |
| `keywordsToAdd/ToRemove` | 修改 | 关键词 |
| `spellsToAdd/ToRemove` | 修改 | 法术 |
| `levSpellsToAdd/ToRemove` | 修改 | 等级法术 |
| `shoutsToAdd/ToRemove` | 修改 | 龙吼 |

---

### 3.5 Race Hook Patcher (raceHook/)

> ⚠️ 与普通 Race Patcher 不同，INI 文件放在 `raceHook/` 文件夹

#### Filters
与 Race Patcher 相同（`filterByRaces`, `filterByKeywords` 等）

#### Operations (攻击数据)
| Operation | 说明 |
|-----------|------|
| `attackDataToAdd` | 添加攻击数据（必须含 `key=`） |
| `attackDataToRemove` | 按事件名移除（如 `attackstart`） |
| `attackDataToChange` | 修改攻击数据 |

**AttackData 参数**:
```
key=attackStart~damagemult=1~attackchance=1~attackspell=null~
attackangle=0~strikeangle=50~staggeroffset=0~attacktype=null~
knockdown=0~recoverytime=0~staminamult=1
```

默认值: `damageMult=1, attackChance=1, attackSpell=null, attackAngle=0, strikeAngle=50, staggerOffset=0, attackType=null, knockDown=0, recoveryTime=0, staminaMult=1, flags=none`

**AttackData flags**: `ignoreweapon, bashattack, powerattack, chargeattack, rotatingattack, continuousattack, overridedata`

---

### 3.6 Leveled List Patcher (leveledlist/)

#### Filters (Item)
| Filter | 说明 |
|--------|------|
| `filterByLLs` | 指定 Leveled List |
| `noFilterLL=true` | 不筛选（影响所有） |
| `filterByEditorIdContains/Or/Excluded` | EditorID 筛选 |

#### Filters (NPC)
| Filter | 说明 |
|--------|------|
| `filterByLLNPCs` | 指定 NPC Leveled List |
| `noFilterLLNPC=true` | 不筛选 |

#### Operations
| Operation | 说明 | 格式 |
|-----------|------|------|
| `addToLLs` | 添加条目 | `FormID~level~count` |
| `addOnceToLLs` | 添加（不重复） | `FormID~level~count` |
| `removeFromLLs` | 移除条目 | `FormID` 或 `FormID~level~count`（支持 `< > <= >=` 高级清理） |
| `removeObjectsByKeyword` | 按关键词移除 | |
| `objectMultCount` | 数量乘数 | `FormID~multiplier` 或全局 `1.5` |
| `formsToReplace` | 替换 | `旧FormID~新FormID`（仅FormID） |
| `chanceNone` | 空概率设置 | |
| `chanceGlobal` | 空概率全局变量 | |
| `clear=yes` | 清空所有条目 | |
| `calcForLevel=true` | 标志 | |
| `calcEachItem=true` | 标志 | |
| `calcForLevelAndEachItem=true` | 标志 | |
| `calcUseAll=true` | 标志 | |
| `clearFlags=true` | 移除所有标志 | |

> 同一时间只能设置一个 calc 标志

---

### 3.7 Container Patcher (container/)

#### Filters
| Filter | 说明 |
|--------|------|
| `filterByContainers` | 指定容器 |
| `filterByEditorIdContains/Or/Excluded` | EditorID 筛选 |

#### Operations
| Operation | 说明 | 格式 |
|-----------|------|------|
| `addToContainers` | 添加物品 | `FormID~count`（支持LL，但可能CTD） |
| `addOnceToContainers` | 添加（不重复） | `FormID~count` |
| `removeFromContainers` | 移除物品 | `FormID` |
| `removeContainerObjectsByCount` | 按数量移除 | `FormID~count` |
| `removeContainerObjectsByKeywords` | 按关键词移除 | |
| `objectMultCount` | 数量乘数 | `FormID~multiplier` |
| `replaceInContainers` | 替换物品 | `旧~新` |
| `clear=true` | 清空 | |

---

### 3.8 Spell Patcher (spell/)

#### Filters
| Filter | 说明 |
|--------|------|
| `filterBySpells/Excluded` | 法术筛选 |
| `filterByKeywords/Or/Excluded` | 关键词 |
| `filterByMgefs/Or/Excluded` | Magic Effect 筛选 |
| `filterByEditorIdContains/Or/Excluded` | EditorID |
| `restrictToCastingType` | `concentration/constanteffect/fireandforget/scroll` |
| `filterByFlags/Or/Excluded` | 法术标志筛选 |

**Spell Flags**: `costoverride, fooditem, extendduration, pcstartspell, instantcast, ignoreloscheck, ignoreresistance, noabsorb, nodualcastmods`

#### Operations
| Operation | 说明 |
|-----------|------|
| `fullName` | 改名 |
| `setFlags/removeFlags` | 法术标志 |
| `baseCost` | 基础消耗 |
| `halfCostPerk` | 半价 perk |
| `castType` | 施法类型 |
| `chargeTime` | 充能时间 |
| `keywordsToAdd/ToRemove` | 关键词 |
| `mgefsToAdd` | 添加 Magic Effect: `FormID~Magnitude~Duration~Area~sortFirst` |
| `mgefsToChange` | 修改 Magic Effect: `FormID~Mag~Dur~Area~Mult`（`null`=跳过） |
| `mgefsToChangeAdd` | 修改+加法 |
| `mgefsToRemove` | 移除 Magic Effect |
| `clear=true` | 清除所有效果 |

---

### 3.9 Scroll Patcher (scroll/)

与 Spell Patcher 几乎相同。Filters 使用 `filterByScrolls`。额外支持:
- `model` — 设置卷轴模型
- `alternateTexturesToAdd/ToRemove/Clear` — 纹理集操作
- `weight/value`, `weightMult/valueMult`

---

### 3.10 Enchantment Patcher (enchantment/)

与 Spell Patcher 结构相同。Filters 使用 `filterByEnchs`。额外支持:
- `enchantmentAmount` — 附魔强度
- `baseCost` — 基础消耗
- `chargeTime` — 充能时间

---

### 3.11 Alchemy/Ingestible Patcher (alchemy/)

Filters 使用 `filterByAlchs`。额外 filter: `filterByAlternateTextures`。
与 Spell Patcher 操作相同，额外支持: `model`, `alternateTexturesToAdd/ToRemove/Clear`。

---

### 3.12 Ingredient Patcher (ingredient/)

Filters 使用 `filterByIngs`。结构与 Alchemy Patcher 相同。

---

### 3.13 Magic Effect Patcher (magiceffect/)

#### Filters
| Filter | 说明 |
|--------|------|
| `filterByModNames/Excluded` | mod 筛选/排除 |
| `filterByMgefs/Excluded` | Magic Effect 筛选 |
| `filterByKeywords/Or/Excluded` | 关键词 |
| `filterByEditorIdContains/Or/Excluded` | EditorID |
| `filterByArchetypes` | 原型筛选 |
| `restrictToCastingType` | 施法类型限制 |
| `restrictToDeliveryType` | `aimed/self/targetactor/targetlocation/touch` |
| `restrictToAreaEffects` | 仅区域效果 |
| `restrictToDetrimentalEffects` | 仅减益效果 |
| `restrictToActorValue` | Actor Value 限制 |
| `restrictToResistType` | `resistdisease/resistfire/resistfrost/resistmagic/resistshock` |
| `filterBySounds` | 音效筛选（搜索所有 sound slot） |
| `effectShadersExcluded` | 排除 Effect Shader |
| `modNamesLastOverriddenExcluded` | 最后覆盖 mod 排除 |

#### Operations
| Operation | 说明 |
|-----------|------|
| `fullName` | 改名 |
| `minimumSkillLevel` | 最小技能等级 |
| `spellmakingCastingTime` | 法术制造施法时间 |
| `spellmakingArea` | 法术制造区域 |
| `baseCost` | 基础消耗 |
| `skillUsageMult` | 技能使用乘数 |
| `enchantArt` | 附魔艺术（FormID） |
| `projectile` | 弹射物（FormID） |
| `castingType` | 施法类型 |
| `enchantShader` | 附魔着色器（`null` 清除） |
| `castingArt` | 施法艺术（FormID） |
| `impactDataSet` | 冲击数据集（FormID） |
| `hitShader` | 命中着色器 |
| `perkToApply` | 应用 perk（`null` 清除） |
| `setFlags/removeFlags` | 标志 |
| `keywordsToAdd/ToRemove` | 关键词 |
| `removeEdgeGlow` | 移除边缘发光 |
| `soundsToChange` | 音效更换: `FormID~slot, null~slot` |

**Sound slots**: `drawsheathe, charge, readyloop, release, castloop, hit`

**Magic Effect Flags**: `hostile, recover, detrimental, snaptomesh, nohitevent, dispelwithkeywords, noduration, nomagnitude, noarea, fxpersist, goryvisuals, hideinui, norecast, poweraffectsmagnitude, poweraffectsduration, painless, nohiteffect, nodeathdispel`

**Archetypes**: `absorb, accumulatemagnitude, valuemodifier, script, dispel, curedisease, dualvaluemodifier, calm, demoralize, frenzy, disarm, commandsummoned, invisibility, light, darkness, nighteye, lock, open, boundweapon, summoncreature, detectlife, telekinesis, paralysis, reanimate, soultrap, turnundead, guide, werewolffeed, cureparalysis, cureaddiction, curepoison, concussion, valueandparts, stagger, peakvaluemodifier, cloak, werewolf, slowtime, rally, enhanceweapon, spawnhazard, etherealize, banish, spawnscriptedref, disguise, grabactor, vampirelord`

---

### 3.14 Constructible Object Patcher (constructibleobject/)

#### Filters
| Filter | 说明 |
|--------|------|
| `filterByCobjs/Excluded` | 配方筛选 |
| `filterByIngredients/Or/Excluded` | 材料筛选 |
| `filterByWorkBenchKeywords` | 工作台关键词筛选 |
| `filterWorkbenchKeywordsExcluded` | 排除工作台 |
| `filterByEditorIdContains/Or/Excluded` | EditorID |
| `filterByKeywords/Or/Excluded` | 创建的物品关键词（filter） |

#### Operations
| Operation | 说明 |
|-----------|------|
| `workbenchKeyword` | 设置工作台（`null` 清除） |
| `count` | 创建数量 |
| `countMult` | 创建数量乘数 |
| `createdObject` | 设置创建的物品 |
| `addToCobjs=FormID~count` | 添加材料 |
| `removeFromCobjs=FormID` | 移除材料（所有实例） |
| `removeFromCobjsByCount=FormID~count` | 按数量移除材料 |
| `changeCobjsCount=FormID~count` | 修改材料数量（`null`=全部） |
| `changeCobjsCountByMult` | 材料数量乘数 |
| `replaceInCobjs=旧~新` | 替换材料 |
| `clear=true` | 清空所有材料 |
| `keywordsToAdd/ToRemove` | 关键词（作用于创建的物品） |
| `restrictToKeywords` | 限制条件（创建的物品关键词） |

---

### 3.15 FormList Patcher (formlist/)

| Operation | 说明 |
|-----------|------|
| `filterByFormLists` | 指定 FormList（不使用 filter 影响所有） |
| `formsToAdd` | 添加 Form |
| `formsToRemove` | 移除 Form |
| `formsToReplace=旧=新` | 替换 Form（仅 FormID） |
| `clear=true` | 清空 |

---

### 3.16 Outfit Patcher (outfit/)

| Operation | 说明 |
|-----------|------|
| `filterByOutfits` | 指定套装（不用 filter 影响所有） |
| `filterByForms/Or/Exclude` | 按包含的物品筛选 |
| `formsToAdd` | 添加物品 |
| `formsToRemove` | 移除物品 |
| `formsToReplace=旧=新` | 替换物品（仅 FormID） |
| `clear=true` | 清空 |

---

### 3.17 Location Patcher (location/)

#### Filters
| Filter | 说明 |
|--------|------|
| `filterByLocations` | 地点 FormID（逗号分隔，至少一个匹配） |
| `filterByLocationsExcluded` | 排除地点 |
| `filterByKeywords/Or/Excluded` | 关键词筛选 |
| `filterByMusicType` | 按 BGSMusicType |
| `filterByParentLocation` | 按父地点 |
| `filterByUnreportedCrimeFaction` | 按 unreportedCrimeFaction |
| `filterByModNames` | mod 筛选 |
| `filterByEditorIdContains/Or/Excluded` | EditorID 筛选 |

#### Operations
| Operation | 说明 |
|-----------|------|
| `fullName=~名称~` | 改名 |
| `keywordsToAdd/ToRemove` | 关键词增减 |
| `musicType` | 设置/清除音乐（`null` 清除） |
| `unreportedCrimeFaction` | 设置/清除犯罪派系 |
| `parentLocation` | 设置/清除父地点 |

---

### 3.18 Cell Patcher (cell/)

#### Filters
- `filterByCells` — CELL FormID

#### Operations
| Operation | 说明 |
|-----------|------|
| `fogNear/fogFar/fogPower/clipDist` | 雾效参数 |
| `directionalXY/Z` | 定向环境光方向 |
| `ambientRed/Green/Blue` | 环境光颜色 |
| `directionalRed/Green/Blue` | 定向光颜色 |
| `specularRed/Green/Blue` | 镜面反射光颜色 |
| `fogRed/Green/Blue` | 雾颜色 |
| `lightingTemplate` | 光照模板（`null` 清除） |
| `acousticSpace` | 声学空间（`null` 清除） |
| `musicType` | 音乐类型（`null` 清除） |
| `imageSpace` | 图像空间（`null` 清除） |
| `skyRegion` | 天空区域（`null` 清除） |
| `encounterZone` | 遭遇区域（`null` 清除） |
| `waterHeight` | 水面高度 |
| `waterType` | 水体类型（`null` 清除） |
| `skipRecordByLightingTemplateFromMod` | 跳过特定mod的光照模板 |
| `skipRecordByModNameContains` | 跳过名称包含特定字符串的mod |

---

### 3.19 Encounter Zone Patcher (encounterzone/)

#### Filters
| Filter | 说明 |
|--------|------|
| `filterByEncounterZones` | 遭遇区域 FormID |
| `filterByEncounterZonesExcluded` | 排除 |
| `filterByModNames` | mod 筛选 |
| `filterByEditorIdContains/Or/Excluded` | EditorID 筛选 |

#### Operations
| Operation | 说明 |
|-----------|------|
| `minLevel` | 设置最小等级 |
| `minLevelAdd` | 最小等级 + N |
| `minLevelMult` | 最小等级 × N |
| `maxLevel` | 设置最大等级 |
| `maxLevelAdd` | 最大等级 + N |
| `maxLevelMult` | 最大等级 × N |
| `location` | 设置/清除 Location（`null` 清除） |

---

### 3.20 Reference Patcher (reference/)

#### Filters
- `filterByRefs` — 指定 Reference FormID

#### Operations
| Operation | 说明 |
|-----------|------|
| `disable=true` | 禁用 Reference（NPC 除外） |

---

## 四、通用 Filter 汇总

| Filter | 说明 |
|--------|------|
| `filterByModNames` | mod 筛选（AND） |
| `filterByKeywords` | 关键词筛选（AND） |
| `filterByKeywordsOr` | 关键词筛选（OR） |
| `filterByKeywordsExcluded` | 排除关键词 |
| `filterByEditorIdContains` | EditorID 包含（AND） |
| `filterByEditorIdContainsOr` | EditorID 包含（OR） |
| `filterByEditorIdContainsExcluded` | EditorID 排除 |
| `filterByXXX` | 直接 FormID 筛选（各 Patcher 专用） |
| `filterByXXXExcluded` | 直接 FormID 排除 |

---

## 五、通用 Operation 汇总

| Operation | 说明 |
|-----------|------|
| `fullName=~名称~` | 改名 |
| `keywordsToAdd` | 添加关键词 |
| `keywordsToRemove` | 移除关键词 |
| `mgefsToAdd` | 添加 Magic Effect: `FormID~Magnitude~Duration~Area` |
| `mgefsToChange` | 修改 Magic Effect: `FormID~Mag~Dur~Area~Mult`（`null`=跳过） |
| `mgefsToChangeAdd` | 修改+加法 |
| `mgefsToRemove` | 移除 Magic Effect |
| `weight/value` | 重量/价值设置 |
| `weightMult/valueMult` | 重量/价值乘数 |
| `clear=true` | 清空 |
| `setFlags/removeFlags` | 标志设置 |

---

## 六、FormID 格式

```
PluginName|FormID
```

示例:
- `Skyrim.esm|00012EB7` (Iron Sword)
- `myMod.esp|223` (短格式，可用但推荐完整 FormID)
- `IronArrow` (EditorID，部分操作支持)

> 建议从 xEdit/Creation Kit 复制完整 FormID

---

## 七、配置示例

### 修改铁武器
```ini
filterByWeapons=Skyrim.esm|00012EB7, Skyrim.esm|00013790:attackDamage=99:weight=0:keywordsToAdd=myMod.esp|20000223
```

### 给所有 NPC 添加 perk
```ini
perksToAdd=SkyValor.esp|1D8A,SkyValor.esp|3DE9
```

### 修改玩家生命值
```ini
filterByNpcs=Skyrim.esm|7:changeStats=health=250
```

### 种族属性修改
```ini
filterByRaces=Skyrim.esm|D53:baseMass=1.2:baseCarryweight=999:startingHealth=250:regenHealth=1.5
```

### 护甲值翻倍（头部装备）
```ini
filterByBipedSlots=0,1:damageResistMultiply=2
```

### 禁用特定 Reference
```ini
filterByRefs=JKs Skyrim.esp|D61,JKs Skyrim.esp|D6D:disable=true
```

### 镜像武器外观
```ini
filterByWeapons=Skyrim.esm|13988:mirrorWeapon=Skyrim.esm|000139B9
```

### 修改法术 Magic Effect
```ini
filterBySpells=Skyrim.esm|366BF:mgefsToChange=Skyrim.esm|397E~null~10~null~null
```

### 向 Leveled List 添加物品
```ini
filterByLLs=myTestESP.esp|00001733:addToLLs=Skyrim.esm|4822~1~1
```

### 禁用自动计算属性
```ini
filterByRaces=Skyrim.esm|000131E8:levelRange=1~30:changeStats=health=625~900,calcStamina=10,calcMagicka=10:setPcLevelMult=false=50:setAutoCalcStats=false
```
