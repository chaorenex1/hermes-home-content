---
title: Using SkyPatcher
name: using-skypatcher
version: 1.0.0
category: bgs-modding
description: 使用 SkyPatcher (Nexus #106659) 编写 INI 配置文件，通过运行时 patching 修改 Skyrim 游戏数据（NPC、武器、护甲、法术、Leveled List 等），无需创建 ESP 插件。触发词：skypatcher, sky patcher, runtime patcher, INI patch, 运行时补丁, 免ESP修改.
---

# Using SkyPatcher

## 概述

SkyPatcher (Nexus #106659) 是一个 SKSE 运行时 patcher，通过 INI 配置文件直接在游戏运行时修改数据，无需创建/维护 ESP 插件。支持 20 种 patcher 类型，覆盖武器、护甲、NPC、种族、法术等几乎所有游戏记录类型。

## 触发条件

当用户需要：
- 编写 SkyPatcher INI 配置文件
- 修改游戏数据但不想创建 ESP
- 对 NPC/武器/护甲/法术等做运行时 patch
- 理解 SkyPatcher 某个 patcher 类型的 filter 和 operation
- 排查 SkyPatcher 配置不生效的问题

## 前置检查

1. 确认目标 mod 环境已安装 SkyPatcher
2. 确认 `SKSE/Plugins/SkyPatcher.dll` 存在
3. 确认对应的 patcher 文件夹存在（如 `SKSE/Plugins/SkyPatcher/npc/`）

## 工作流

### 1. 确定 patcher 类型

根据要修改的数据类型，查阅 [完整参考文档](references/skypatcher-complete-reference.md) 的 "Patcher 类型速查表"，确定使用哪个 patcher。

### 2. 确定文件位置

```
SKSE/Plugins/SkyPatcher/<patcher_folder>/<my_mod_name>/<my_file>.ini
```

例如修改 NPC 武器伤害:
```
SKSE/Plugins/SkyPatcher/weapon/MyTweaks/iron_weapons.ini
```

### 3. 编写 INI 配置

遵循格式: `filter:operation1:operation2`

```ini
;注释以分号开头
filterByWeapons=Skyrim.esm|00012EB7:attackDamage=99:weight=0
```

### 4. 验证

- 检查 FormID 格式: `PluginName|FormID`
- 检查路径正确性
- 确认 INI 文件编码为 UTF-8
- 测试加载是否生效

## 关键规则

- **通用 INI** (如 `myfile.ini`): 始终加载
- **条件 INI** (如 `MyMod.esp.ini`): 仅当对应插件激活时加载
- **条件 INI 必须放子文件夹**: 避免 mod manager 覆盖
- **加载顺序 0-z**: 后加载的同名字段覆盖先加载的
- **多 patch 共存**: 只要不修改同一字段即可共存
- **mgefsToChange 用 null 跳过**: `mgefsToChange=FormID~null~10~null~null`
- **替换用 ~ 分隔**: `formsToReplace=旧~新`

## 完整参考

详细的 patcher 参数、filter 列表、operation 说明等请见：
[skypatcher-complete-reference.md](references/skypatcher-complete-reference.md)

## 来源

- Nexus Mods #106659: https://www.nexusmods.com/skyrimspecialedition/mods/106659
- Articles: https://www.nexusmods.com/skyrimspecialedition/mods/106659?tab=articles
- 作者: Zzyxzz
