#!/usr/bin/env python3
"""
跨平台 CDP Edge 启动脚本
处理 Windows MSYS 环境的特殊问题
"""

import subprocess
import time
import sys
import json
import urllib.request


def is_port_open(port=9222):
    """检查 CDP 端口是否可用"""
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/json/version', timeout=5) as r:
            return json.loads(r.read().decode())
    except:
        return None


def kill_edge():
    """关闭所有 Edge 进程"""
    print("[1/3] Stopping existing Edge processes...")
    result = subprocess.run(
        ['cmd.exe', '//c', 'taskkill /F /IM msedge.exe /T'],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("  Edge processes stopped")
    time.sleep(2)


def start_edge(use_real_profile=True, headless=False, port=9222):
    """
    启动 CDP Edge 浏览器
    
    Args:
        use_real_profile: True=使用真实用户数据（保留登录态），False=独立目录
        headless: True=无头模式，False=可见窗口
        port: CDP 调试端口
    """
    # 检查端口是否被占用
    print(f"[2/3] Checking port {port}...")
    existing = is_port_open(port)
    if existing:
        print(f"  Port {port} already in use by: {existing.get('Browser', 'unknown')}")
        return existing
    
    print(f"[3/3] Starting Edge CDP instance...")
    
    # 构建命令
    cmd = [
        r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        f'--remote-debugging-port={port}',
        '--no-first-run',
        '--no-default-browser-check',
    ]
    
    if not use_real_profile:
        cmd.append(r'--user-data-dir=<PATH_TO_BROWSER_PROFILE>')
    
    if headless:
        cmd.append('--headless=new')
    
    cmd.append('about:blank')
    
    # 启动进程
    subprocess.Popen(cmd)
    
    # 等待启动
    print("  Waiting for browser to start...")
    for _ in range(10):
        time.sleep(1)
        info = is_port_open(port)
        if info:
            print(f"  [OK] CDP Edge started!")
            print(f"  Browser: {info.get('Browser', 'unknown')}")
            print(f"  WebSocket: {info.get('webSocketDebuggerUrl', 'N/A')}")
            print(f"  Profile: {'real user data' if use_real_profile else 'isolated'}")
            print(f"  Window: {'headless' if headless else 'visible'}")
            return info
    
    print("  [FAIL] Failed to start CDP Edge")
    return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Start CDP Edge browser')
    parser.add_argument('--real-profile', action='store_true', default=True,
                        help='Use real user profile (keeps login state)')
    parser.add_argument('--isolated', action='store_true',
                        help='Use isolated profile (no login state)')
    parser.add_argument('--headless', action='store_true',
                        help='Run in headless mode')
    parser.add_argument('--port', type=int, default=9222,
                        help='CDP port (default: 9222)')
    parser.add_argument('--kill', action='store_true',
                        help='Kill existing Edge before starting')
    
    args = parser.parse_args()
    
    if args.kill:
        kill_edge()
    
    use_real = not args.isolated
    info = start_edge(
        use_real_profile=use_real,
        headless=args.headless,
        port=args.port
    )
    
    if info:
        print("\n--- CDP Connection Info ---")
        print(json.dumps(info, indent=2))
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())
