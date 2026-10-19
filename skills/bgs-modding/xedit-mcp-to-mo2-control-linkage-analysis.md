# xedit-mcp 到 mo2-control 链路分析

## 概览

xedit-mcp 到 mo2-control 的链路是一个**间接的、分层的通信架构**，通过多个中间层连接：

```
Agent (Claude/Copilot)
    ↓ (MCP Protocol)
xedit-mcp (Node.js Server)
    ↓ (PowerShell)
xedit-client.ps1 (VFS Launcher Client)
    ↓ (命名管道 Named Pipe)
mo2-vfs-launcher.ps1 (VFS Launcher Server)
    ↓ (命名管道 Named Pipe)
mo2_agent_control.py (MO2 Python Plugin)
    ↓ (MO2 Python API)
MO2 Control Plane (C++ Plugin + Runtime)
    ↓ (直接 API 调用)
xEdit 或 MO2 进程
```

---

## 1. 第一层：xedit-mcp 服务器

**位置：** `tools/xedit-mcp/src/`

### 1.1 核心入口
- **文件：** `index.ts`
- **角色：** MCP 服务器的主入口，暴露 6 个意图工具给 Agent
- **关键工具：**
  - `xedit_session` — 获取会话信息
  - `xedit_find_record` — 查找记录
  - `xedit_read_record` — 读取记录
  - `xedit_inspect_conflicts` — 检查冲突
  - `xedit_list_capabilities` — 列出能力
  - `xedit_call(command, args)` — 原子透传

### 1.2 配置和初始化
**文件：** `launch.ts`

```typescript
interface LaunchOptions {
  moRoot: string;           // MO2 根目录
  mo2InstanceRoot?: string; // 分割布局时的实例目录
  script?: string;          // xedit-client.ps1 路径
}
```

**初始化流程：**
1. 解析 `BGS_MO2_ROOT` 环境变量或使用 `.artifacts/mo2` dev 沙箱
2. 定位 `xedit-client.ps1`（位于 `tools/mo2-vfs-launcher/`）
3. 启动 xEdit 守护进程：
   ```bash
   node dist/index.js
   ```
4. 通过名称管道等待就绪

### 1.3 守护进程适配器
**文件：** `daemon-adapter.ts`

**职责：** 将 MCP 工具调用翻译成 PowerShell 调用

**调用模式：**
```typescript
// xedit-mcp → PowerShell
pwsh -NoProfile -File xedit-client.ps1 automation call \
  --xedit-pid <pid> \
  --request-file <path> \
  --response-file <path> \
  --timeout-seconds 30
```

---

## 2. 第二层：xedit-client.ps1（VFS 启动客户端）

**位置：** `tools/mo2-vfs-launcher/xedit-client.ps1`

### 2.1 双重职能
xedit-client.ps1 既可以是**独立工具**，也可以是 **xedit-mcp 的传输层**

**主要脚本：**
```
xedit-client.ps1           (公共入口)
├── lib/xedit-client.common.ps1      (公共函数)
├── lib/xedit-client.session.ps1     (会话管理)
├── lib/xedit-client.launch.ps1      (启动逻辑)
└── lib/xedit-client.call.ps1        (自动化调用)
```

### 2.2 MO2 根目录解析
**优先级链：**
1. `$env:BGS_MO2_ROOT` — 最高优先级（用户安装）
2. `<project>/.artifacts/mo2` — dev 沙箱（若存在）

### 2.3 关键启动参数
```powershell
xedit-client.ps1 process launch `
  --launcher-path <PATH_TO_MO2_ALT>\...\xEdit.exe `
  --game-mode Fallout4 `
  --mo-profile Default `
  --mo2-root <PATH_TO_MO2_ALT> `
  --mo2-instance-root <optional>
```

### 2.4 IPC 通道建立
- **传输方式：** Windows 命名管道 (Named Pipe)
- **管道名称：** 实例特定（来自 MO2 PID）
- **协议：** JSON-RPC 2.0 over Named Pipe
- **通信目标：** `mo2-vfs-launcher.ps1`

---

## 3. 第三层：mo2-vfs-launcher.ps1（VFS 启动服务器）

**位置：** `tools/mo2-vfs-launcher/mo2-vfs-launcher.ps1`

### 3.1 命名管道服务器
**职责：** 
- 监听来自 xedit-client.ps1 的命名管道连接
- 转发请求到 MO2 控制平面
- 管理 MO2 进程生命周期

### 3.2 请求转发模式
```
xedit-client.ps1 (客户端)
    ↓ (Named Pipe: xedit.automation.call)
mo2-vfs-launcher.ps1 (服务器)
    ↓ (Named Pipe: mo2-control-plane 内部)
mo2_agent_control.py (Python 插件)
```

### 3.3 引导文件
VFS 启动程序依赖以下运行时文件进行发现和活力检测：

**引导文件位置：** `.artifacts/mo2/plugins/Mo2AgentControl/bootstrap/runtime/`

```json
// endpoint.json
{
  "transport": "named-pipe",
  "endpoint": "local_instance_uuid",
  "mo2Pid": <PID>
}

// status.json
{
  "schemaVersion": 1,
  "state": "ok",
  "mo2Pid": <PID>
}

// capabilities.json
{
  "methods": [
    "system.ping",
    "system.capabilities",
    "launch.start",
    "launch.status",
    ...
  ]
}
```

---

## 4. 第四层：mo2_agent_control.py（MO2 Python 桥接）

**位置：** `tools/mo2-control-plane/live-bridge/mo2_agent_control.py`

### 4.1 MO2 Python 插件架构
**部署位置：** `<MO2_Root>/plugins/mo2_agent_control.py`

**职责：**
1. 启动时创建 `createPlugin()` 让 MO2 加载
2. 在命名管道上发布 JSON-RPC 端点
3. 转发 Agent 请求到 MO2 C++ 控制平面
4. 管理 MO2 运行时生命周期

### 4.2 关键接口
```python
class ErrorCode:
    INVALID_REQUEST = "invalid_request"
    METHOD_NOT_FOUND = "method_not_found"
    NOT_IMPLEMENTED = "not_implemented"
    INTERNAL_ERROR = "internal_error"
    MOD_NOT_FOUND = "mod_not_found"
    MO2_SHUTTING_DOWN = "mo2_shutting_down"
```

### 4.3 JSON-RPC 方法
**系统方法：**
- `system.ping` — 活力信号
- `system.capabilities` — 列出支持的方法
- `system.shutdown` — 关闭 MO2

**启动方法：**
- `launch.start` — 启动 xEdit 或其他工具
- `launch.status` — 查询启动状态
- `launch.wait` — 等待进程退出
- `launch.stop` — 停止进程

### 4.4 运行时文件发布
初始化时发布三个文件到 `Mo2AgentControl/bootstrap/runtime/`：
1. `endpoint.json` — 管道端点发现
2. `status.json` — MO2 进程状态
3. `capabilities.json` — 支持的方法列表

---

## 5. 第五层：MO2 C++ 控制平面

**位置：** `tools/mo2-control-plane/plugin/`

### 5.1 控制平面插件
**职责：**
- 实现 IPC 通信（命名管道）
- 拦截并处理 MO2 dialog 事件（Unlock、Exit Now 等）
- 启动 xEdit 或其他工具子进程
- 通过 MO2 Python API 与插件通信

### 5.2 启动流程
```cpp
// 伪代码：MO2 控制平面启动
MO2AgentControlPlugin::onInit()
  → 创建命名管道监听器
  → 等待 mo2_agent_control.py 连接
  → 发布 endpoint.json、status.json、capabilities.json
  → 进入事件循环
    → 监听对话框（Unlock、Exit Now）
    → 处理 launch.* JSON-RPC 请求
```

### 5.3 关键 Dialog 拦截
**自动处理的 Dialog：**
- "Unlock" — 自动点击
- "Exit Now" — 自动点击
- 进度条 — 等待完成

### 5.4 xEdit 启动流程
```
Agent 请求 → xedit_session
    ↓ (daemon-adapter 转换)
xedit-client.ps1 automation call
    ↓ (Named Pipe 请求)
mo2_agent_control.py (Python 插件)
    ↓ (Python → C++ 调用)
MO2 C++ 控制平面
    ↓ (IPC 启动)
ModOrganizer.exe -p <profile> run -e xEdit.exe
    ↓ (VFS 虚拟文件系统覆盖)
xEdit.exe 进程启动
    ↓ (xEdit Daemon Bridge)
xEditHookBridge.dll (启用自动化模式)
```

---

## 6. 完整调用链示例

### 场景：读取记录冲突信息

```
1. Agent 调用 xedit_inspect_conflicts('plugins.txt', 0x01234567)
   ↓
2. xedit-mcp.tools.inspect-conflicts 验证参数和规则
   ↓
3. daemon-adapter 序列化为 JSON 请求
   ↓
4. 写入临时文件：
   {
     "command": "records.conflict_status",
     "args": { "file": "plugins.txt", "formId": "01234567" }
   }
   ↓
5. 调用 xedit-client.ps1:
   pwsh xedit-client.ps1 automation call \
     --xedit-pid 5432 \
     --request-file request.json \
     --response-file response.json \
     --timeout-seconds 30
   ↓
6. xedit-client.ps1 → xedit-client.call.ps1
   ↓
7. 发送命名管道请求到 mo2-vfs-launcher.ps1
   ↓
8. mo2-vfs-launcher.ps1 转发到 mo2_agent_control.py 的命名管道
   ↓
9. Python 插件 → MO2 C++ 控制平面 IPC 调用
   ↓
10. C++ 控制平面 → xEdit.exe 进程（通过 DLL hook）
    ↓
11. xEdit 执行 records.conflict_status，写入响应文件
    ↓
12. 响应沿链路返回：
    response.json → xedit-client.ps1 → daemon-adapter
    ↓
13. xedit-mcp 解析响应，生成信封结果
    ↓
14. Agent 接收结果：
    {
      "ok": true,
      "tool": "xedit_inspect_conflicts",
      "data": { "conflict": "caConflict", ... }
    }
```

---

## 7. 关键配置点

### 7.1 MCP 服务器注册
**文件：** `.mcp.json`

```json
{
  "mcpServers": {
    "xedit": {
      "command": "node",
      "args": ["${CLAUDE_PLUGIN_ROOT}/tools/xedit-mcp/dist/index.js"]
    },
    "mo2": {
      "command": "node",
      "args": ["${CLAUDE_PLUGIN_ROOT}/tools/mo2-mcp/dist/index.js"]
    }
  }
}
```

### 7.2 环境变量
- `BGS_MO2_ROOT` — MO2 安装根目录
- `BGS_XEDIT_CLIENT_SCRIPT` — xedit-client.ps1 替代路径
- `XEDIT_MCP_INTEGRATION` — 启用集成测试
- `BGS_MCP_DIAG` — 启用诊断模式

### 7.3 文件布局
```
<MO2_Root>/
├── ModOrganizer.exe
├── plugins/
│   ├── Mo2AgentControl/              (C++ 插件)
│   │   ├── bootstrap/
│   │   │   └── runtime/
│   │   │       ├── endpoint.json
│   │   │       ├── status.json
│   │   │       └── capabilities.json
│   │   └── harness/
│   │       └── (harmless .cmd 工具用于测试)
│   └── mo2_agent_control.py          (Python 桥接)
└── Stock Game/
    └── Fallout 4/
        └── Tools/
            └── OpenCodeXEdit/
                ├── xEdit.exe
                └── xEditHookBridge.dll
```

---

## 8. 分层通信特点

### 8.1 分离的关注点
| 层级 | 技术 | 职责 | 协议 |
|-----|------|------|------|
| MCP 服务器 | TypeScript/Node | 意图工具 + 规则检查 | MCP/stdio |
| 启动客户端 | PowerShell | xEdit 进程管理 | Shell + Named Pipe |
| 启动服务器 | PowerShell | IPC 路由 | Named Pipe |
| Python 桥接 | Python 3 | MO2 事件循环集成 | Named Pipe JSON-RPC |
| C++ 控制平面 | C++ | 进程控制 + Dialog 拦截 | IPC + Win API |
| xEdit 守护进程 | Pascal/AutoHotkey | 实际编辑操作 | Named Pipe |

### 8.2 非阻塞设计
- xedit-mcp 不阻塞 Agent
- xedit-client.ps1 异步启动 xEdit（60-180 秒启动时间）
- 响应返回 PID/工件而非等待完成
- Agent 可立即继续后续操作

### 8.3 错误处理
链路上每一层都有独立的错误处理：
1. **xedit-mcp**：规则拒绝 (state_violation, invalid_request)
2. **xedit-client.ps1**：启动失败、超时
3. **Python 插件**：MO2 API 错误、方法未找到
4. **C++ 控制平面**：IPC 错误、Dialog 超时
5. **xEdit**：命令失败、文件锁定

---

## 9. 与 mo2-mcp 的关系

### 9.1 并行的 MCP 服务器
```
xedit-mcp          mo2-mcp
   ├─ xedit_*      ├─ mo2_session
   ├─ xedit_call   ├─ mo2_status
   └─ ...          ├─ mo2_modlist
                   ├─ mo2_pluginlist
                   └─ ...
```

### 9.2 共享的基础设施
- 都使用 MO2 控制平面命名管道
- 都依赖 `.artifacts/mo2/` 开发沙箱
- 都通过 `mo2_agent_control.py` 连接

### 9.3 独立的管道
- **xedit-mcp**：专门针对 xEdit 自动化
- **mo2-mcp**：针对 MO2 本身的管理和检查

---

## 10. 关键文件交叉引用

### xedit-mcp → mo2-vfs-launcher
```typescript
// tools/xedit-mcp/src/launch.ts
const launchArgs = [
  'process', 'launch',
  '--launcher-path', opts.xeditPath,
  '--game-mode', opts.gameMode,
  '--mo-profile', opts.moProfile,
  '--mo2-root', opts.moRoot,
  '--mo2-instance-root', opts.instanceRoot,
];
execSync(`pwsh -NoProfile -File "${xeditClientScript}" ${launchArgs.join(' ')}`);
```

### mo2-vfs-launcher → mo2_agent_control
```powershell
# tools/mo2-vfs-launcher/lib/xedit-client.call.ps1
$namedPipeClient = New-Object System.IO.Pipes.NamedPipeClientStream(
  ".",                           # localhost
  "mo2-control-$mo2Pid",        # 实例特定的管道名
  [System.IO.Pipes.PipeDirection]::InOut
)
$namedPipeClient.Connect(30000)  # 30 秒超时
Write-PipeMessage $namedPipeClient $request
```

### mo2_agent_control → MO2 C++
```python
# tools/mo2-control-plane/live-bridge/mo2_agent_control.py
def on_ipc_request(method, params):
    if method == 'launch.start':
        return mo2cpp_launch_start(params)
    elif method == 'records.conflict_status':
        return query_xedit_via_mo2cpp(params)
    # ...
```

---

## 11. 部署检查清单

为了验证整个链路：

```powershell
# 1. 验证环境
$env:BGS_MO2_ROOT = '<PATH_TO_MO2_ALT>'

# 2. 启动 MO2 + 控制平面
Start-Process "<PATH_TO_MO2_ALT>\ModOrganizer.exe" -ArgumentList "-p Default"
Start-Sleep -Seconds 10

# 3. 验证引导文件
Test-Path "<PATH_TO_MO2_ALT>\plugins\Mo2AgentControl\bootstrap\runtime\status.json"
Test-Path "<PATH_TO_MO2_ALT>\plugins\Mo2AgentControl\bootstrap\runtime\endpoint.json"

# 4. 测试 xedit-client.ps1
pwsh -NoProfile -File "tools/mo2-vfs-launcher/xedit-client.ps1" `
  process launch `
  --launcher-path "<PATH_TO_MO2_ALT>\Stock Game\Fallout 4\Tools\OpenCodeXEdit\xEdit.exe" `
  --game-mode Fallout4 `
  --mo-profile Default

# 5. 验证 xedit-mcp 连接
node "tools/xedit-mcp/dist/index.js"
```

---

## 12. 性能特点

### 12.1 启动延迟
- **xEdit 首次启动：** 60-180 秒（包括 VFS 初始化）
- **xEdit 缓存启动：** 10-30 秒
- **命名管道往返：** < 1 秒
- **工具调用往返（脚本）：** 2-5 秒

### 12.2 可扩展性
- **单 xEdit 实例：** 支持多个并发工具调用
- **多 MO2 实例：** 通过实例特定的管道名隔离
- **长运行会话：** 支持通过保活（keepalive）机制

---

## 总结

xedit-mcp 到 mo2-control 的链路是一个**多层异构系统**：

1. **上层（Agent 侧）：** 类型安全的 MCP 工具，规则检查和审计
2. **中层（IPC 侧）：** PowerShell 脚本处理 Windows VFS 复杂性
3. **下层（MO2 侧）：** Python 插件 + C++ 控制平面实现实际的进程控制

这种分层设计提供了：
- **清晰的关注点分离**
- **强大的错误边界**
- **可测试的各层次**
- **灵活的部署选项**

链路的关键是通过**Windows 命名管道**的 JSON-RPC 2.0 协议进行的**同步通信**，确保了 Agent 和底层系统的松耦合。
