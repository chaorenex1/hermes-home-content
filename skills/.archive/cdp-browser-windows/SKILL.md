---
name: cdp-browser-windows
description: CDP browser automation on Windows — Edge/Chrome remote debugging with real user profiles, login state preservation, and human-like behavior simulation.
---

# CDP Browser Automation on Windows

> Windows-specific CDP (Chrome DevTools Protocol) browser automation.
> Covers: real user data, login state, human-like behavior, batch file encoding pitfalls, and lifecycle management.

---

## When to Use

Use this skill when you need CDP automation on Windows with:
- **Real user login state** (not isolated profiles)
- **Visible browser windows** (not headless)
- **Human-like mouse/scroll behavior**
- **Proper process lifecycle** (start/stop without killing user's daily browser)

Prefer `web_fetch` for static pages. Use CDP only for JS-rendered sites, login-required sites, or interactive automation.

---

## Quick Start

### Start CDP Browser (Real User Data)

```powershell
# Kill existing Edge first (if any on port 9222)
cmd.exe //c "taskkill /F /IM msedge.exe /T"

# Start Edge with CDP, using REAL user data (keeps login state)
"/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" `
    --remote-debugging-port=9222 `
    --no-first-run `
    --no-default-browser-check `
    about:blank

# Verify
sleep 3; curl -s http://127.0.0.1:9222/json/version
```

**Key flags explained:**
| Flag | Purpose |
|------|---------|
| `--remote-debugging-port=9222` | Enable CDP |
| `--no-first-run` | Skip first-run wizard |
| `--no-default-browser-check` | Skip default browser prompt |
| *(no `--user-data-dir`)* | Use real user profile |
| *(no `--headless`)* | Window is visible |

### Stop CDP Browser (Port-Specific)

```powershell
# Stop ONLY the process using port 9222 (not all Edge)
for /f "tokens=5" %a in ('netstat -ano ^| findstr :9222 ^| findstr /V TIME_WAIT') do (
    taskkill /F /PID %a
)

# Verify
netstat -ano | findstr :9222 | findstr /V TIME_WAIT
# Should return nothing (or only TIME_WAIT which is normal)
```

---

## Windows Batch File Encoding Pitfall

**CRITICAL:** The `write_file` tool creates UTF-8 files. `cmd.exe` executing `.bat` files with UTF-8 encoding (especially with BOM or Chinese characters) will produce garbled output like:

```
'...' is not recognized as an internal or external command
'ho' is not recognized...
```

**Solutions:**
1. **Use `execute_code` with Python** to write ASCII-encoded batch files:
   ```python
   with open(r'C:\path\script.bat', 'w', encoding='ascii') as f:
       f.write(content)
   ```

2. **Use PowerShell** to create files with explicit encoding:
   ```powershell
   Set-Content -Path 'script.bat' -Value '@echo off' -Encoding ASCII
   ```

3. **Avoid Chinese characters** in batch files when possible

4. **Prefer direct command execution** over batch files in MSYS/bash environments

---

## Human-Like Behavior Simulation

### Mouse Movement (Bezier Curve)

```javascript
async function humanMouseMove(ws, x1, y1, x2, y2) {
    const steps = 15 + Math.floor(Math.random() * 10);
    for (let i = 0; i <= steps; i++) {
        const t = i / steps;
        const x = x1 + (x2 - x1) * t + Math.sin(t * Math.PI) * (Math.random() * 20 - 10);
        const y = y1 + (y2 - y1) * t + Math.sin(t * Math.PI) * (Math.random() * 20 - 10);
        await cdpSend(ws, 'Input.dispatchMouseEvent', {
            type: 'mouseMoved',
            x: Math.round(x),
            y: Math.round(y)
        });
        await sleep(20 + Math.random() * 30);
    }
}
```

### Natural Scrolling

```javascript
async function humanScroll(ws, deltaY) {
    const steps = Math.abs(deltaY) / 50;
    for (let i = 0; i < steps; i++) {
        await cdpSend(ws, 'Input.dispatchMouseEvent', {
            type: 'mouseWheel',
            x: 500 + Math.random() * 200,
            y: 500 + Math.random() * 200,
            deltaX: 0,
            deltaY: deltaY > 0 ? 50 : -50
        });
        await sleep(100 + Math.random() * 200);
    }
}
```

### Random Delays

```javascript
// Wait 3-6 seconds for JS rendering
await sleep(3000 + Math.random() * 3000);

// Pause between actions
await sleep(500 + Math.random() * 1000);
```

---

## Process Lifecycle Management

### Problem: TIME_WAIT Connections

After stopping a process, TCP connections enter `TIME_WAIT` state for 60-120 seconds:

```
TCP    127.0.0.1:2369    127.0.0.1:9222    TIME_WAIT    0
```

This is **normal** and should be ignored. Use `findstr /V TIME_WAIT` to filter them out.

### Problem: Child Processes

Edge spawns many child processes. `taskkill /F /PID <parent>` may leave children running.

**Robust stop sequence:**
```powershell
# 1. Try graceful stop of port-specific PID
for /f "tokens=5" %a in ('netstat -ano ^| findstr :9222 ^| findstr /V TIME_WAIT') do (
    taskkill /F /PID %a
)

# 2. Wait
ping -n 3 127.0.0.1 >nul

# 3. Verify
netstat -ano | findstr :9222 | findstr /V TIME_WAIT

# 4. If still active, force kill all Edge
if %errorlevel% equ 0 (
    taskkill /F /IM msedge.exe /T
    taskkill /F /IM msedgewebview2.exe /T
)
```

---

## MSYS/Bash Environment Quirks

| Command | Problem | Solution |
|---------|---------|----------|
| `taskkill /F` | Parsed as path | Use `cmd.exe //c "taskkill /F /IM msedge.exe /T"` |
| `timeout /t 3` | Conflicts with Linux `timeout` | Use `ping -n 4 127.0.0.1` in batch files |
| `start command &` | Backgrounding not supported | Use `terminal(background=true)` |
| `Start-Process` | Not available in cmd.exe | Use `start "" "path"` in batch, or direct execution |
| Paths with spaces | Parsing issues | Use MSYS `/c/Program Files/...` or quoted Windows paths |

---

## Real User Data vs Isolated Profile

| Approach | Flags | Pros | Cons |
|----------|-------|------|------|
| **Real user data** | No `--user-data-dir` | Keeps login state, cookies, extensions | Interferes with user's daily browser if they try to open Edge manually |
| **Isolated profile** | `--user-data-dir="C:\..."` | Clean slate, no interference | No login state, must log in manually |
| **Headless** | `--headless=new` | No UI, no interference | Less human-like, may trigger anti-bot |

**Recommendation:** For automation requiring login state, use real user data but schedule during user idle time. For testing/scraping, use isolated profile.

---

## Checking Login State

```javascript
const isLoggedIn = await pageEval(ws, `
    !!(document.querySelector('.avatar') || 
       document.querySelector('[class*="user"]') ||
       document.querySelector('.login-tip') === null)
`);
```

---

## References

- `references/windows-batch-encoding.md` — Batch file encoding issues and solutions
- `references/human-behavior-patterns.md` — Mouse/scroll/click simulation patterns

---

*Last updated: 2026-06-29*
