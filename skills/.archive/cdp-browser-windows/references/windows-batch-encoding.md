# Windows Batch File Encoding Issues

## Problem

The `write_file` tool creates UTF-8 encoded files. When `cmd.exe` executes `.bat` files with UTF-8 encoding (especially with BOM or Chinese characters), it produces garbled output:

```
'...' is not recognized as an internal or external command
'ho' is not recognized as an internal or external command
'o-first-run' is not recognized as an internal or external command
```

## Root Cause

- `cmd.exe` expects ASCII or ANSI encoding for batch files
- UTF-8 with BOM causes `cmd.exe` to misinterpret the BOM bytes as commands
- Chinese characters in UTF-8 get split into multiple bytes, each interpreted as separate commands

## Solutions

### 1. Python (Recommended)

```python
content = '''@echo off
echo Hello World
'''

with open(r'C:\path\script.bat', 'w', encoding='ascii') as f:
    f.write(content)
```

Use `execute_code` tool to run this Python script.

### 2. PowerShell

```powershell
Set-Content -Path 'script.bat' -Value '@echo off' -Encoding ASCII
Add-Content -Path 'script.bat' -Value 'echo Hello' -Encoding ASCII
```

### 3. Direct Command Execution (Avoid Batch Files)

Instead of creating batch files, execute commands directly:

```bash
# Good: Direct execution
cmd.exe //c "taskkill /F /IM msedge.exe /T"

# Bad: Creating and running batch file
# write_file creates UTF-8, causes encoding issues
```

## Best Practices

1. **Avoid Chinese characters** in batch files
2. **Use ASCII-only characters** for maximum compatibility
3. **Prefer direct execution** over batch files in automation scripts
4. **If batch files are necessary**, create them with explicit ASCII encoding via Python or PowerShell

## Example: Working vs Broken

### Broken (UTF-8 with Chinese)
```batch
@echo off
echo [1/3] 检查端口 9222...
```
Result: `...' is not recognized`

### Working (ASCII only)
```batch
@echo off
echo [1/3] Checking port 9222...
```
Result: `[1/3] Checking port 9222...`

---

*Last updated: 2026-06-29*
