---
name: cdp-windows-workarounds
description: Windows MSYS environment workarounds for CDP browser automation — encoding, path, and process management pitfalls.
---

# CDP Windows/MSYS 环境 workaround 技能

> 补充 browser-automation-cdp 技能，专门解决 Windows + MSYS/bash 环境下使用 CDP 的坑。

---

## 何时使用

当你在 Windows 上通过 Hermes 终端（MSYS/bash）使用 CDP 浏览器自动化时，会遇到以下问题：
- 批处理文件编码问题
- 路径格式问题
- 命令冲突问题
- 后台进程启动问题

---

## 核心 workaround

### 1. 批处理文件编码（.bat 文件乱码）

**问题：** 用 `write_file` 或 `patch` 创建的 `.bat` 文件默认是 UTF-8 编码，在 `cmd.exe` 中执行会出现乱码（如 `'...' is not recognized`）。

**解决：** 用 Python 创建 ASCII 编码的批处理文件：
```python
content = '''@echo off
echo Hello World
'''
with open(r'C:\Users\...\script.bat', 'w', encoding='ascii') as f:
    f.write(content)
```

**或者** 直接用 `terminal` 工具执行命令，不依赖 `.bat` 文件。

---

### 2. MSYS 路径格式

**问题：** Windows 路径在 MSYS/bash 中需要转换。

**解决：** 使用 MSYS 风格路径：
```bash
# ✅ 正确：MSYS 路径
/c/Program\ Files\ \(x86\)/Microsoft/Edge/Application/msedge.exe

# ❌ 错误：Windows 路径在 bash 中
"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
```

---

### 3. 命令冲突：`timeout` vs `sleep`

**问题：** `timeout /t 3` 在 MSYS bash 中会被解析为 GNU `timeout` 命令（不同语义）。

**解决：** 在 `.bat` 文件中使用 `ping` 替代：
```batch
:: ✅ 正确：在 .bat 中替代 timeout
ping -n 4 127.0.0.1 >nul

:: ❌ 错误：在 MSYS 环境中冲突
timeout /t 3 /nobreak >nul
```

或者在 bash 中直接用 `sleep`：
```bash
sleep 3
```

---

### 4. 后台进程启动

**问题：** 在 bash 中用 `&` 启动后台进程会导致 foreground 命令错误。

**解决：** 使用 Hermes 的 `terminal(background=true)` 工具：
```json
{
  "background": true,
  "command": "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe --remote-debugging-port=9222"
}
```

**不要** 在命令末尾加 `&`：
```bash
# ❌ 错误：会导致 "Foreground command uses '&' backgrounding" 错误
msedge.exe ... &
```

---

### 5. 关闭 Edge 进程

**问题：** `taskkill` 在 bash 中需要特殊处理。

**解决：** 通过 `cmd.exe //c` 执行：
```bash
# ✅ 正确
cmd.exe //c "taskkill /F /IM msedge.exe /T"

# ❌ 错误：taskkill 会被解析为路径
taskkill /F /IM msedge.exe /T
```

---

### 6. 启动模式选择

| 模式 | 命令 | 适用场景 |
|------|------|----------|
| 真实用户数据（窗口可见） | `msedge.exe --remote-debugging-port=9222 --no-first-run --no-default-browser-check about:blank` | 需要登录态、保留用户设置 |
| 独立 profile（无头） | `msedge.exe --remote-debugging-port=9222 --user-data-dir="..." --headless=new about:blank` | 隔离环境、自动化测试 |

**推荐：** 除非明确需要隔离，否则使用真实用户数据模式（保留登录态）。

---

## 快速启动脚本（Python，跨平台）

```python
import subprocess
import time
import requests

def start_cdp_edge(use_real_profile=True, headless=False):
    """启动 CDP Edge 浏览器"""
    
    # 关闭现有 Edge
    subprocess.run(['cmd.exe', '//c', 'taskkill /F /IM msedge.exe /T'], 
                   capture_output=True)
    time.sleep(2)
    
    # 构建启动命令
    cmd = [
        r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        '--remote-debugging-port=9222',
        '--no-first-run',
        '--no-default-browser-check',
    ]
    
    if not use_real_profile:
        cmd.append('--user-data-dir=<PATH_TO_BROWSER_PROFILE>')
    
    if headless:
        cmd.append('--headless=new')
    
    cmd.append('about:blank')
    
    # 启动进程
    subprocess.Popen(cmd)
    time.sleep(3)
    
    # 验证端口
    try:
        r = requests.get('http://127.0.0.1:9222/json/version', timeout=5)
        return r.json()
    except:
        return None
```

---

## 常见错误速查

| 错误 | 原因 | 解决 |
|------|------|------|
| `'...' is not recognized` | 批处理文件 UTF-8 编码 | 用 ASCII 编码重建，或直接用命令行 |
| `Foreground command uses '&'` | 在 bash 中用 `&` 后台化 | 用 `terminal(background=true)` |
| `timeout: invalid time interval` | MSYS `timeout` 冲突 | 用 `ping` 或 `sleep` 替代 |
| `MODULE_NOT_FOUND` (ws) | 内置模块路径硬编码 | 自包含脚本 + `npm install ws` |
| `Port 9222 not available` | 端口被占用 | 先关闭现有 Edge 进程 |

---

## 相关技能

- `browser-automation-cdp` — 核心 CDP 自动化技能

---

*最后更新：2026-06-29*
*本次新增：批处理编码问题 / MSYS 路径格式 / timeout 冲突 / 后台进程启动 / 真实用户数据模式*
