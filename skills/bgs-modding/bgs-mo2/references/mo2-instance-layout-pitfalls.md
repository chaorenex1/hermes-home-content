# MO2 实例目录与 base_directory 分离布局

MO2 2.5+ 支持把实例数据（`ModOrganizer.ini`、`profiles/`、`mods/`、`downloads/`、
`overwrite/`）放在 `%LOCALAPPDATA%\ModOrganizer\<instance>` 目录，而程序文件
（`ModOrganizer.exe`、`plugins/`）放在 `base_directory`（通常是另一个磁盘位置）。

## 典型布局示例

```text
C:\Users\<user>\AppData\Local\ModOrganizer\juelunv5\
    Mod.Organizer-2.5.2.exe      ← 用这个 exe 启动，-p 指定 profile
    ModOrganizer.ini              ← 实例配置，含 base_directory / gamePath / selected_profile
    profiles/
    mods/
    downloads/
    overwrite/

<PATH_TO_MO2_INSTALL>\
    ModOrganizer.exe              ← 程序主 exe
    plugins/                      ← 插件目录（控制平面装到这里）
    dlls/
    Tools/
    Stock Game/                   ← 如果 MO2 用 stock game 模式
```

## 关键区别

| 用途 | 路径 |
|------|------|
| 启动 MO2 实例 | `%LOCALAPPDATA%\ModOrganizer\<instance>\Mod.Organizer-*.exe -p "Profile"` |
| 读取实例配置 | `%LOCALAPPDATA%\ModOrganizer\<instance>\ModOrganizer.ini` |
| 安装 Python 插件 | `<base_directory>\plugins\` |
| 设置 `lock_gui` | 修改实例目录的 `ModOrganizer.ini` |

## 为什么不能直接用 `base_directory\ModOrganizer.exe` 启动

如果 `base_directory` 下没有 `ModOrganizer.ini`，MO2 会进入首次启动/修复流程，
弹出 `Setup - Mod Organizer ...` 窗口，而不是加载已有实例。

实例目录里的 `Mod.Organizer-*.exe` 会读取同目录的 `ModOrganizer.ini`，从而正确
加载 `base_directory` 和其他实例设置。

## 安装控制平面时的注意点

`install-mo2-control-plane.ps1` 要求 `-MO2Root` 是包含 `ModOrganizer.ini` 和
`plugins/` 的目录。在分离布局中，这两个目录不在一起，所以脚本会失败：

```text
Missing ModOrganizer.ini: <PATH_TO_MO2_INSTALL>\ModOrganizer.ini
```

正确做法：

1. 手动复制 `tools/mo2-control-plane/live-bridge/mo2_agent_control.py` 到
   `<base_directory>\plugins\`。
2. 在实例目录的 `ModOrganizer.ini` 中确保 `[Settings]` 下有 `lock_gui=false`。
3. 用实例目录的 `Mod.Organizer-*.exe` 启动。

自动化脚本未来应接受 `-Mo2InstanceRoot` 和 `-Mo2PluginsRoot` 两个参数来支持这种
布局。

## 常见错误信息

| 错误 | 原因 |
|------|------|
| `MO2 root does not contain ModOrganizer.exe` | `start-mo2.ps1` 指向了实例目录 |
| `Missing ModOrganizer.ini` (install 脚本) | 安装脚本指向了 `base_directory` |
| `Setup - Mod Organizer version ...` 窗口 | 用 `base_directory` 的 exe 启动，找不到实例 ini |

## 检查清单

- [ ] 实例目录的 `ModOrganizer.ini` 存在，且 `base_directory` 指向目标 `plugins/` 所在目录
- [ ] `selected_profile` 指向的 profile 存在于实例目录的 `profiles/` 下
- [ ] `gamePath` 指向的 Stock Game 目录存在（若不存在，MO2 启动会失败）
- [ ] `plugins/mo2_agent_control.py` 已复制到 `base_directory\plugins\`
- [ ] `lock_gui=false` 已写入实例 `ModOrganizer.ini` 的 `[Settings]` 节
