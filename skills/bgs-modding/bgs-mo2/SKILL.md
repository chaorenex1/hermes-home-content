---
title: BGS-MO2
name: bgs-mo2
version: 2.3.0
category: software-development
author: Hermes Agent
description: MO2 完整管理 — 实例/Profile 查询、文件级控制、MO2 扩展通信、安全检查工作流、所有 IPlugin 子接口实现。
summary: MO2 管理 + 文件/IPluginList API 控制 + guard 安全检查 + IPlugin* 接口。
---

# BGS-MO2

### 触发文件路径跨平台

MO2 是原生 Windows 进程。`os.environ.get('TEMP')` 在 MSYS 中返回 `/tmp`，但 Windows 真实 TEMP 是 `C:\Users\<user>\AppData\Local\Temp`。**必须用** `Path.home() / "AppData" / "Local" / "Temp" / "mo2_control"`，两端一致。

### MO2 插件字节码缓存

更新 `.py` 后 MO2 可能不加载新代码：`rm -f "MO2路径/plugins/__pycache__/bgs_*"`

### INI 解析不能用 configparser

`configparser` 把路径 `\S` 当转义符吃掉。用原始行解析 `split("=", 1)`，然后 `replace("\\", "/")`。

### IPluginList 排序

| 方法 | 说明 |
|------|------|
| `setLoadOrder(list)` | 设置完整顺序，未列出的放最后 |
| `setPriority(name, int)` | 移动单个（仅 ACTIVE 有效） |
| `SortMechanism` | `NONE`/`LOOT`/`BOSS`/`MLOX` — 无直接 API |

### PluginState 枚举陷阱

| 值 | 状态 | 说明 |
|----|------|------|
| 0 | INACTIVE | 已禁用 |
| 1 | ACTIVE | 已启用 |
| 2 | (ALWAYS_ACTIVE) | Master/必需插件 — `setState(INACTIVE)` 只降到 1，无法禁用 |

> 对 state=2 的插件调用 `setState(INACTIVE)` 返回 `ok:True` 但实际只变成 1。MO2 依赖保护机制。

### delete_mod 注意事项

### Python Proxy tryInit=false → 所有 Python 插件静默失败

**症状**：MO2 启动后 Python 插件完全不加载。
**原因**：`PluginPersistance` 节中 `Python%20Proxy\tryInit=false` 阻止代理初始化。
**修复**：删除该行。对所有实例：
```bash
python -c "import re,pathlib;[ini.write_text(re.sub(r'.*Python.*tryInit.*\n?','',ini.read_text())) for d in pathlib.Path.home().glob('AppData/Local/ModOrganizer/*/') if (ini:=d/'ModOrganizer.ini').exists() and 'Python' in ini.read_text() and 'tryInit' in ini.read_text()]"
```

### 实例目录与 base_directory 分离导致启动失败

**症状**：`start-mo2.ps1` 报 `MO2 root does not contain ModOrganizer.exe`；或启动后
弹出 `Setup - Mod Organizer ...` 修复窗口、无法加载实例。
**原因**：MO2 2.5 可以把实例配置（`ModOrganizer.ini` + `profiles/`）放在
`%LOCALAPPDATA%\ModOrganizer\<instance>`，而 `base_directory` 指向另一个位置
（如 `<PATH_TO_MO2_INSTALL>`），`plugins/` 和 `ModOrganizer.exe` 在
`base_directory`。`start-mo2.ps1` 默认要求 exe 与 profiles 同目录，这种分离布局
会失败。
**修复**：
1. 找到实例目录：遍历 `%LOCALAPPDATA%\ModOrganizer\*` 中 `ModOrganizer.ini` 的
   `base_directory` 指向目标 MO2 根目录的条目。
2. 将控制平面安装到 `base_directory/plugins/`：
   ```powershell
   & "$HERMES_HOME/skills/bgs-modding/scripts/install-mo2-control-plane.ps1" -MO2Root "<base_directory>"
   ```
3. 若上一步因实例目录缺少 `ModOrganizer.ini` 则手动复制
   `tools/mo2-control-plane/live-bridge/mo2_agent_control.py` 到
   `<base_directory>/plugins/`，并确保实例目录的 `ModOrganizer.ini` 中
   `[Settings]` 下 `lock_gui=false`。
4. 使用实例目录中的 `Mod.Organizer-*.exe` 启动，并指定 profile：
   ```powershell
   & "C:\Users\<user>\AppData\Local\ModOrganizer\<instance>\Mod.Organizer-2.5.2.exe" -p "Profile Name"
   ```
   不要用 `base_directory` 下的 `ModOrganizer.exe` 启动分离实例，否则 MO2 会找不到
   实例配置而进入 Setup/修复流程。

### 三分离布局（Tri-split）：实例 INI / 数据 / Exe 分别在不同目录

**症状**：`mo2_session` 绑定到实例目录时找不到 profiles（`modlist.txt` ENOENT），
绑定到 exe 目录时找不到 `ModOrganizer.ini`。
**原因**：三个位置分别存放不同内容：
- 实例 INI：`%LOCALAPPDATA%\\ModOrganizer\\<instance>\\ModOrganizer.ini`
- 数据（base_directory）：如 `<PATH_TO_MO2_INSTANCE>`，含 `profiles/`、`mods/`、`downloads/`
- Exe + plugins：如 `<PATH_TO_MO2_INSTALL>`，含 `ModOrganizer.exe` 和 `plugins/`

`base_directory` 指向数据目录，不指向 exe 目录。
**修复**：绑定 MO2 MCP 时，`mo2Root` 指向**实例 INI 目录**（含 `ModOrganizer.ini`），
`mo2InstanceRoot` 指向 **base_directory**（数据目录，含 profiles/mods）。
这是因为 MCP 绑定时需要读取 `ModOrganizer.ini`，而该文件在实例目录中。

```python
# Tri-split 绑定示例
mo2_session(
    mo2Root="C:\\Users\\<user>\\AppData\\Local\\ModOrganizer\\<instance>",  # INI 所在
    mo2InstanceRoot="<PATH_TO_MO2_INSTANCE>",                                          # profiles + mods
    profile="pbr"
)
```

**常见失败**：`mo2Root` 指向 base_directory → `ENOENT: ModOrganizer.ini`。
用 `mo2_machine_contract` 验证绑定后的 `profile_list_paths` 指向正确路径。

环境变量 `BGS_MO2_ROOT` 仍使用 **exe 目录**（xEdit client 需要找 ModOrganizer.exe）。

对于 `xedit_start`，在 tri-split 布局中需要同时传递 `moRoot` 和 `mo2InstanceRoot`：
```
moRoot:          "<PATH_TO_MO2_INSTALL>"  ← 控制平面 + xEdit
mo2InstanceRoot: "<PATH_TO_MO2_INSTANCE>"                       ← profiles + mods
```
详见 `xedit-automation` 技能。

### 写操作前检查

- **所有写操作前先调用 `guard` 和 `backup`**：保持实例/Profile 一致性，防止误改。
- 文件级回退仅用于插件 API 不可用的情况。
- **单命令锁**：`__processing` flag 保证一次只执行一个命令
## 安全协议（不可跳过）

1. 写操作前 `guard` 检查实例/Profile 一致性
2. 写操作前自动 `backup`
3. **所有操作优先通过 MO2 扩展 API，文件系统仅作回退**

---

## 脚本总览

> 注意：当前 `bgs-modding-superpowers` 发行包中**不包含** `scripts/mo2_manager.py`、
> `scripts/mo2_control.py` 或 `scripts/mo2_install.py`。这些早期 Python 入口已被
> PowerShell 启动器 + `mo2-control-plane` Python 插件取代。不要硬编码这些路径。

| 脚本 | 用途 |
|------|------|
| `scripts/start-mo2.ps1` | 以可见窗口启动指定 MO2 实例 |
| `scripts/install-mo2-control-plane.ps1` | 部署 `mo2_agent_control.py` 到 MO2 plugins |
| `scripts/run-mo2-mcp-acceptance.ps1` | MCP 验收测试 |
| `tools/mo2-control-plane/live-bridge/mo2_agent_control.py` | 实际 MO2 Python 插件 |
| `tools/mo2-control-plane/broker/` | PowerShell IPC 客户端 |

## 初始化安装（首次使用必须执行）

```powershell
# 1. 确认 MO2 安装根目录（包含 ModOrganizer.exe 的目录）
# 2. 部署控制平面 Python 插件
& "$HERMES_HOME/skills/bgs-modding/scripts/install-mo2-control-plane.ps1" -MO2Root "<MO2_Root>"

# 3. 启动 MO2（可见窗口）
& "$HERMES_HOME/skills/bgs-modding/scripts/start-mo2.ps1" -MO2Root "<MO2_Root>" -Profile "Default"
```

如果 MO2 采用“实例目录”与“base directory”分离的布局（实例 `.ini` 和 profiles
在 `%LOCALAPPDATA%\ModOrganizer\<instance>`，而 `ModOrganizer.exe` 和 `plugins/`
在 `base_directory`），应把控制平面安装到 `base_directory` 的 `plugins/`，把
`lock_gui=false` 写到实例目录的 `ModOrganizer.ini`，并用实例目录中的
`Mod.Organizer-*.exe` 启动。详见 `references/mo2-instance-layout-pitfalls.md`。

**plugins 目录检测逻辑**：nxmhandler.ini→executable→plugins/，所有实例 base_directory→plugins/，实例内嵌 plugins/。

**安装的扩展**：`bgs_mo2_control.py`（核心控制 IPC）。

## 已实现的 IPlugin 子接口

| 接口 | 插件文件 | 核心方法 |
|------|---------|----------|
| `IPlugin` (base) | 全部 | name/author/description/version/init/settings/localizedName/requirements/enabledByDefault/master |
| `IPluginTool` | bgs_mo2_control | display/displayName/tooltip/icon |
| `IPluginModPage` | bgs_nexus_modpage | pageURL/useIntegratedBrowser/handlesDownload/icon |
| `IPluginPreview` | bgs_preview | supportedExtensions/genFilePreview/genDataPreview/supportsArchives |
| `IPluginRequirement` | (工具类) | check(organizer) → Problem\|None |

## 扩展触发命令

```
get_state → {profileName, profilePath, gameName, basePath, modsPath, appVersion, modCount, pluginCount}
get_load_order → [{name, loadOrder, active}, ...]
query_plugin → {name, state, priority, loadOrder, origin, masters, isMaster, isLight, ...}
query_mod → {modid, version, newestVersion, category, installationFile, pageurl, fileTree, pluginStates, ...}
refresh_mod_list → organizer.refresh()
launch_executable → organizer.startApplication()
create_mod → organizer.createMod()
create_separator → organizer.createMod(name + "_separator")
delete_mod → modList.getMod(name) → modList.removeMod(mod)
set_mod_active / set_mod_priority → modList API
set_plugin_state / set_plugin_priority / set_load_order → pluginList API
```

### query_mod 实现细节

通过 `IModInterface` API 返回完整信息，无需读文件：
- `mod.nexusId()` → modid
- `mod.version()` / `mod.newestVersion()` → VersionInfo
- `mod.url()` → Nexus 页面 URL
- `mod.installationFile()` → 安装文件路径
- `mod.fileTree()` → IFileTree 递归遍历获取文件列表
- 自动查找 mod 内所有 .esp/.esm/.esl 并查询 IPluginList 状态

### mod_info / query_mod / delete_mod — 名必须精配（fuzzy match 不存在）

MO2 MCP 的 `mod_info`、`query_mod`、`delete_mod` 等按名查找的工具**不支持模糊匹配**。传入的名必须与 `modlist.txt` 中的 mod 文件夹名完全一致（大小写敏感）。

**常见失败模式**：用插件名（如 `unofficial skyrim special edition patch.esp`）搜 mod → `mod_not_found`。正确做法是先用 `mo2_modlist` 找到确切的 mod 名（如 `Unofficial Skyrim Special Edition Patch`），再用那个名调用。

`modList.getMod(name)` 使用 MO2 **内部名**，可能与显示名不同。如果 `getMod` 返回 None，用 `query_mod` 确认 mod 的实际 name 字段。

## 常用命令

```bash
# 查询
python scripts/mo2_manager.py list                        # 标记当前实例
python scripts/mo2_manager.py info auto                   # 自动检测 → mo2LiveState
python scripts/mo2_manager.py profile auto                # 自动检测 Profile
python scripts/mo2_control.py guard "实例" "Profile"       # 安全检查
python scripts/mo2_control.py query-plugin "实例" "插件名"  # 单插件详情
python scripts/mo2_control.py load-order "实例"            # 完整加载顺序

# 写操作（需先 guard + backup，全部走 MO2 扩展 API）
python scripts/mo2_control.py backup "实例" "Profile"
python scripts/mo2_control.py create-mod-api "实例" "名称"
python scripts/mo2_control.py create-separator "名称"              # plugin API
python scripts/mo2_control.py set-mod-active "名称" true           # plugin API
python scripts/mo2_control.py set-plugin-state "esp" false         # plugin API
python scripts/mo2_control.py reorder-mod "实例" "Profile" 0 5     # plugin API
python scripts/mo2_control.py reorder-plugin "实例" "Profile" 0 5  # plugin API
python scripts/mo2_control.py refresh "实例"
python scripts/mo2_control.py set-load-order "实例" '["a.esp","b.esp"]'
python scripts/mo2_control.py launch-game "实例" "SKSE"

# 扩展安装（见上方「初始化安装」）
python scripts/mo2_install.py --all                  # 安装到所有目录
python scripts/mo2_install.py --list                 # 仅列出
```

## 触发文件 IPC（直接查询运行中的 MO2）

当 `mo2_manager.py auto` 或 `mo2_control.py` 因分离布局等原因无法定位实例时，
直接用触发文件与插件通信：

```python
import json, time
from pathlib import Path
from datetime import datetime

TRIGGER_DIR = Path.home() / "AppData" / "Local" / "Temp" / "mo2_control"

# 清理旧文件
for f in ["command.json", "command.lock", "result.json"]:
    (TRIGGER_DIR / f).unlink(missing_ok=True)

# 写入命令
cmd = {"command": "get_state", "timestamp": datetime.now().isoformat()}
(TRIGGER_DIR / "command.json").write_text(json.dumps(cmd), encoding="utf-8")

# 轮询结果（插件每 3s 轮询一次）
for i in range(20):
    time.sleep(0.5)
    rf = TRIGGER_DIR / "result.json"
    if rf.exists():
        result = json.loads(rf.read_text(encoding="utf-8"))
        print(json.dumps(result, indent=2, ensure_ascii=False))
        break
```

支持的命令：`get_state`, `get_load_order`, `query_plugin`, `query_mod`, `set_plugin_state`,
`set_load_order`, `create_mod`, `delete_mod`, `refresh_mod_list` 等（见 `bgs_mo2_control.py` 的 `__execute`）。

**适用场景**：`mo2_manager.py` 自动检测失败（分离布局、exe 与 INI 不在同目录等）。

## 故障排除

**MCP 传输层问题（ClosedResourceError 等）**：见 `references/mcp-connectivity-issues.md`。

详见 `references/mo2-plugin-pitfalls.md`，关键条目：

| 症状 | 检查 |
|------|------|
| 所有 Python 插件不加载 | `grep "Python.*tryInit" ModOrganizer.ini` — 删除该行 |
| 插件导入但不执行 init | `settings()` 返回 `[]`，不要构造 PluginSetting |
| taskkill 无效 | 用 `powershell Stop-Process -Name ModOrganizer -Force` |
| TEMP 路径不同步 | 统一用 `Path.home()/AppData/Local/Temp/` |
| 新旧代码混跑 | 删 `plugins/__pycache__/bgs_*` 再重启 |
| Named-pipe 返回空响应 | 双插件冲突：`bgs_mo2_control.py` 和 `mo2_agent_control.py` 同时存在。禁用旧版：`mv bgs_mo2_control.py bgs_mo2_control.py.disabled`，清缓存后重启 |

## 参考文档

- MO2 Python Plugin API: https://www.modorganizer.org/python-plugins-doc/autoapi/mobase/index.html
- `references/mo2-api-reference.md` — 完整 API 速查（所有接口方法表、PluginState 枚举、陷阱）
- `references/mo2-meta-conventions.md` — meta.ini 字段约定：本地 category ID 对照表（43=Followers）、gamename 格式（SkyrimSE）、离线安装后需补全的字段、configparser 批量编辑示例
- `references/mo2-plugin-pitfalls.md` — 故障排除速查
- `references/mo2-instance-layout-pitfalls.md` — 实例目录与 `base_directory` 分离布局的坑
- `references/collecting-mod-esp-pairs.md` — 从 MO2 批量收集本体+汉化 ESP 配对的工作流（CN mod 匹配、ESP 提取、复制）
