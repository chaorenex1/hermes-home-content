# Edge/Chrome v20 加密（App-Bound Encryption）

Cookie 导入失败绝大多数是这一层，不是工具坏了。以下均为 Edge 155 实测。

## 值前缀决定能不能解

Chromium 系 Cookies 表里 `encrypted_value` 的前 3 字节就是版本前缀：

| 前缀 | 含义 | 文件解密能否拿到明文 |
|---|---|---|
| 明文 | 很少见 | 能 |
| `v10` | 旧 DPAPI 加密 | 能（用 Local State 里的 DPAPI key） |
| `v11` | 同上，另一变体 | 能 |
| `v20` | App-Bound Encryption（ABE） | **不能**，需要浏览器自身的 Elevator COM |

查法（对备份副本执行，不要碰运行中的库）：

```python
import sqlite3
con = sqlite3.connect("file:cookies_backup.db?mode=ro", uri=True)
for prefix, n in con.execute("select substr(encrypted_value,1,3), count(*) from cookies group by 1"):
    print(prefix, n)
```

全是 `v20` + `undecryptable == rows` 就是 ABE 机器，纯文件解密无解。

## 可行路径：rookie-cookies（用户态）

需要浏览器**完全退出**（`tasklist | grep -i msedge` 为空）。运行中浏览器会独占锁 `Network/Cookies`（WinError 32，重试无用）。

```python
import rookie_cookies
rows = rookie_cookies.read(browser="edge").as_list()   # 浏览器 id 用 edge / chrome / brave
# 每项: {domain, name, value, path, expires, http_only, secure, same_site}
text = rookie_cookies.to_netscape(rows)                 # Netscape 格式；#HttpOnly_ 开头是真 cookie 不是注释
```

要点：

- 用完整规范浏览器 id（`edge` 而非 `msedge`），缩写会解析失败
- 导出后按 `domains` 过滤再导入，别整库搬
- 有 `invalid_octets` 警告是正常的（已过期/损坏行），按行跳过
- EDR 可能对注入报警——这是上游已知行为
- DBSC（`chrome-bound-session-credentials`）绑定的会话没有实现，解出来也可能不能重放；这类站点只能浏览器内登录

## 为什么不能“调试启动日常 profile”

Edge/Chrome ≥136 默认数据目录拒绝 `--remote-debugging-port`。用 junction 或复制把日常资料指到非默认目录能绕过，但**非默认 user-data-dir 会禁用 ABE**，浏览器随即把该 profile 里的 v20 cookie 全部当作无法解密而清空，且不可恢复。

结论：

- 想要 CDP 自动化 → 开独立 profile，在里面重新登录（那个 profile 的 cookie 从此就是 v10/明文）
- 想保留日常 profile 的登录 → 用本技能的 cookie 导入流程，不要动启动参数
- 万一已经动过：先看备份；没有备份就只能在站点重新登录

## 验证口径

导入后用**独立信号**验收，不要只看工具返回：

1. 工具侧：`verified: true` 且 `present_after >= accepted`（`present_after` 含导入前已存在的行，可能大于 accepted）
2. 站点侧：camofox 里重新打开目标页，跑登录判别式（接口状态码 / 身份 meta），必须变成已登录
3. 只读确认：打开一个只有登录后才能访问的页面（账户页、设置页），确认不是登录墙

## 常见错误信息对照

| 错误 | 真实原因 |
|---|---|
| `profile is locked ... WinError 32` | 浏览器在跑，Cookies 被独占 |
| `exported: 0` + `undecryptable == rows` | ABE，纯文件解密无解 |
| `HTTP 403 Check CAMOFOX_API_KEY` | 脚本环境缺 `PYTHONPATH`，API key 解析成空（假象） |
| `413 Payload Too Large` | camofox 请求体 ~100KB 上限；按字节分批，不要只按条数 |
