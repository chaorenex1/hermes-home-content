@echo off
:: 启动 Edge CDP 浏览器（使用用户真实数据，保留登录态）
:: 修改自 browser-automation-cdp 技能，移除无头模式和独立用户目录

echo [1/3] 检查端口 9222...
netstat -ano | findstr :9222 >nul
if %errorlevel% equ 0 (
    echo 端口 9222 已被占用
    echo 如需重启，请先关闭占用端口的进程
    exit /b 1
)

echo [2/3] 启动 Edge CDP 实例（使用用户真实数据）...
start "" "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" ^
    --remote-debugging-port=9222 ^
    --no-first-run ^
    --no-default-browser-check ^
    about:blank

echo [3/3] 等待浏览器启动...
timeout /t 3 /nobreak >nul

curl -s http://127.0.0.1:9222/json/version >nul
if %errorlevel% equ 0 (
    echo CDP Edge 实例已启动！
    echo 调试端口: ws://127.0.0.1:9222
    echo 使用用户真实数据（包含登录态）
    echo 浏览器窗口可见
) else (
    echo 启动失败，请检查日志
    exit /b 1
)
