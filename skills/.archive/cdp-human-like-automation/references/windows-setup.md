# Windows CDP 浏览器自动化设置指南

> Windows 平台上启动 Edge/Chrome 进行 CDP 自动化的具体步骤和踩坑记录。

## 环境前提

- Hermes Agent 运行在 Windows 上
- 终端使用 bash/MSYS（git-bash），**不是 PowerShell 或 cmd**
- Node.js 已安装

## 启动 Edge 进行远程调试

### 正确流程

```bash
# 1. 关闭现有 Edge 进程
cmd.exe //c "taskkill /F /IM msedge.exe /T" 2>/dev/null

# 2. 等待进程完全退出
sleep 3

# 3. 使用 Hermes background=true 启动 Edge
# 在 Hermes 工具调用中：
# terminal(background=true, command='"/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" --remote-debugging-port=9222')

# 4. 检查端口是否可用
curl -s http://127.0.0.1:9222/json/version
```

### 常见错误

| 错误 | 原因 | 正确做法 |
|------|------|---------|
| `'Start-Process' is not recognized` | 在 cmd 中使用 PowerShell 命令 | 直接用 MSYS 路径启动可执行文件 |
| `Foreground command uses '&' backgrounding` | 在 MSYS 中使用 `&` 后台运行 | 使用 `terminal(background=true)` |
| `Port 9222 not available` | 浏览器未启动或端口被占用 | 检查进程，重启浏览器 |
| `MODULE_NOT_FOUND: ws` | 未安装 ws 模块 | `npm install ws` |

### 路径对照表

| 环境 | 路径格式 |
|------|---------|
| Windows 原生 | `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` |
| MSYS/Cygwin | `/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe` |
| PowerShell | `"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"` |

## 安装 ws 模块

```bash
# 在用户主目录安装
cd /c/Users/$USER && npm install ws

# 验证
node -e "require('ws')" && echo "ws OK"
```

## 验证 CDP 连接

```bash
# 检查浏览器信息
curl -s http://127.0.0.1:9222/json/version

# 列出所有标签页
curl -s http://127.0.0.1:9222/json/list
```

## 故障排查

### Edge 被其他程序占用端口

联想 Vantage 等软件可能占用 Edge 端口。解决：

```bash
# 查找占用端口的进程
netstat -ano | grep 9222

# 或查找 webview 进程
tasklist | grep msedge
```

### 浏览器启动后无法连接

1. 检查防火墙是否阻止了 9222 端口
2. 确保启动参数正确：`--remote-debugging-port=9222`
3. 尝试使用 `--user-data-dir` 指定独立 profile

### 中文路径问题

如果用户目录包含中文，某些 Node 模块可能有问题。建议：

```bash
# 在项目目录（英文路径）下安装和运行
cd /c/projects/cdp-automation
npm install ws
node script.js
```
