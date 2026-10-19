# MO2 Plugin 开发陷阱

## 1. Python Proxy 静默禁用

**症状**：所有 .py 插件不加载，无任何错误日志。

**根因**：`ModOrganizer.ini` 的 `[PluginPersistance]` 中：
```
Python%20Proxy\tryInit=false
```
MO2 的 Python Proxy 在首次初始化失败后记录此标记，后续启动跳过所有 Python 插件。

**修复**：删除此行。检查命令：
```bash
grep "Python.*tryInit" "$HOME/AppData/Local/ModOrganizer/<instance>/ModOrganizer.ini"
```

---

## 2. PluginSetting 参数错误导致静默失败

**症状**：插件模块导入成功（`diag.txt` 写入），`__init__` 被调用，但 `init()` 从不执行。

**根因**：`settings()` 返回的 `PluginSetting` 对象参数签名不正确。MO2 不会记录错误，直接跳过 `init()` 调用。

**修复**：`settings()` 返回 `[]`。如需要 settings，参考 `mobase.PluginSetting` 文档确认正确签名。

```python
def settings(self) -> list:
    return []  # 安全默认值
```

---

## 3. TEMP 路径跨环境不匹配

**症状**：插件写入 `$TEMP/mo2_control/`，控制脚本读不到。

**根因**：bash/MSYS 环境 `$TEMP=/tmp`，Windows 原生进程 `%TEMP%=C:\Users\<user>\AppData\Local\Temp`。两个路径是不同目录。

**修复**：使用 `Path.home() / "AppData" / "Local" / "Temp"` 统一路径。

---

## 4. taskkill 不可靠

**症状**：`taskkill /F /IM ModOrganizer.exe` 返回成功但进程未停止。

**修复**：使用 PowerShell：
```bash
powershell -Command "Stop-Process -Name ModOrganizer -Force"
```

---

## 5. 插件重启后未加载新代码

**症状**：更新插件文件后重启 MO2，仍执行旧代码。

**原因**：
- MO2 可能在 `__pycache__/` 中缓存了 `.pyc`
- 文件写入与 MO2 启动存在竞态

**修复**：
1. 先写文件，后启动 MO2
2. 删除 `plugins/__pycache__/bgs_*` 缓存文件
3. 模块级写入 diag 标记确认新代码被导入

---

## 6. configparser 损坏 Windows 路径

**症状**：`ModOrganizer.ini` 中路径 `<PATH_TO_STEAM_LIBRARY>\...` 被解析为 `H:SteamLibrary...`（反斜杠消失）。

**根因**：`configparser.ConfigParser()` 默认开启插值，把 `\S`、`\c` 等当转义符。

**修复**：用原始行解析 `split("=", 1)`，然后 `replace("\\", "/")` 归一化。

## 7. 插件启动时文件 I/O 导致 MO2 卡死

**症状**：MO2 启动后界面无响应或加载极慢。

**根因**：插件在模块导入时或 `init()` 中同步写入文件。MO2 的虚拟文件系统（usvfs）此时可能未完全初始化，阻塞主线程。

**修复**：移除所有模块级和 `init()` 中的文件写入。诊断标记仅在调试时使用。

## 8. `organizer.refresh()` 阻塞 UI

**症状**：执行 `refresh_mod_list` 等命令后 MO2 界面短暂卡顿。

**根因**：`IOrganizer.refresh(True)` 触发完整文件系统扫描，同步阻塞 MO2 事件循环。

**修复**：使用 `QTimer.singleShot(500, callback)` 延迟到下一事件循环周期执行：
```python
def _safe_refresh(self):
    if not self.__pending_refresh:
        self.__pending_refresh = True
        QTimer.singleShot(500, self.__do_refresh)

def __do_refresh(self):
    self.__pending_refresh = False
    self.__organizer.refresh(True)
```

## 9. 队列机制不需要

**症状**：命令处理延迟或积压。

**解决方案**：单命令处理模式 — `__processing` 锁保证一次只执行一个命令，新命令在下一个 poll 周期处理：
```python
def __tick(self):
    if self.__processing: return
    if not command.json.exists(): return
    self.__processing = True
    try: execute(cmd); write result.json
    finally: self.__processing = False
```

## 11. PluginState 枚举值

`mobase.PluginState` 有三个值：

| 值 | 含义 | `setState` 行为 |
|---|------|-----------------|
| 0 | INACTIVE | 可设置 |
| 1 | ACTIVE | 可设置 |
| 2 | ALWAYS_ACTIVE | master 或被其他插件依赖 — `setState(name, INACTIVE)` 返回成功但不生效（降为 ACTIVE） |

`Skyrim.esm`、`Update.esm` 等官方 master 始终为 2。依赖它们的普通插件也可能为 2。查询用 `str(pl.state(name))` 获取字符串形式。

## 12. 文件锁防多会话冲突

`command.json` 是共享资源。CLI 写 + 插件读存在竞态。

**锁机制**：`command.lock` 标记文件。
- CLI 的 `send_trigger`：写前等锁释放（最多 10s），写后立即释放
- 插件的 `__tick`：处理前检查锁，30s 超时自动破锁，处理完后释放

```python
# CLI side
lock_file.touch()  # acquire
write command.json
lock_file.unlink()  # release

# Plugin side
if lock_file.exists():
    if time.time() - lock.stat().st_mtime > 30:
        lock.unlink()  # stale
    else:
        return  # skip
lock.touch()
try: process; write result.json
finally: lock.unlink()
```

## 13. 架构规则：MO2 扩展 API 优先

所有写操作必须先尝试 MO2 扩展 API（`send_trigger`），失败才回退文件系统。

```python
def op_xxx(instance, name, ...):
    result = send_trigger("xxx_command", instance, ...)
    if result.get("ok"):
        return result
    return _op_xxx_fs(instance, name, ...)  # fallback
```

| 操作 | 主路径（trigger） | 回退 |
|------|-------------------|------|
| 启禁 MOD | `set_mod_active` | `_op_set_mod_enabled_fs` |
| 启禁 Plugin | `set_plugin_state` | `_op_set_plugin_enabled_fs` |
| MOD 排序 | `set_mod_priority` | `_op_reorder_mod_fs` |
| Plugin 排序 | `set_plugin_priority` | `_op_reorder_plugin_fs` |
| 创建分隔符 | `create_separator` | `_op_create_separator_fs` |
| 查询 MOD | `query_mod` | `_op_query_mod_fs` |

## 14. IOrganizer.startApplication args 剥离 (2026-07-02)

**症状**：通过 `startApplication(path, args)` 启动 xEdit，子进程收不到 `-SSE` 等标志，xEdit 回退到注册表检测（报 Fallout 4 错误）。

**根因**：`startApplication` 第一个参数是文件路径时，忽略第二个 `args` 参数。传入已配置的可执行文件**标题**（如 `"xEdit64"`）时使用 INI 预存参数，但仍忽略调用时传入的 `args`。

**解决方案**：调用前动态修改 INI 中对应标题的 `arguments=` 行，追加需要的参数（如 `-automation-serve`），调用 `startApplication(title, [], ...)`，完成后恢复原参数。

**INI 路径斜杠不一致**：`organizer.basePath()` 返回 `\` 分隔路径，但 MO2 INI 存储 `/` 分隔路径。比较前用 `.replace("\\", "/").lower()` 归一化。

**INI `\title=` endswith 匹配失败**：`22\title=xEdit` 以数字索引开头，`endswith("\title=xEdit")` 不匹配。用 `in` 加 guard 代替。

**CREATE_NO_WINDOW 移除**：`start_subprocess_launch` 原设置 `creationflags=CREATE_NO_WINDOW` 导致子进程无 GUI。已移除。

详见 `xedit-automation` 技能 `references/xedit-launch-pitfalls.md`。
