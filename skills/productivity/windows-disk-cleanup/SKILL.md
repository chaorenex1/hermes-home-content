---
name: windows-disk-cleanup
description: "Analyze disk space and clean up the user home directory on Windows — scan directory sizes, classify cleanup targets by safety, and execute prioritized deletion. Use when the user asks to 'clean up disk', 'free up space', '分析目录', '清理空间', 'what's taking up space', or '磁盘满了'."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [disk-cleanup, disk-space, windows, cleanup, storage, maintenance]
prerequisites:
  commands: [powershell]
---

# Windows Disk Space Analysis & Cleanup

Analyze disk space usage on Windows and execute prioritized cleanup of caches, build artifacts, crash dumps, and stale project files.

## When to Use

- User asks to analyze disk usage or free up space
- "清理磁盘", "空间不够了", "磁盘满了", "what's taking up space"
- User wants to know what can be safely deleted
- Post-project cleanup of build artifacts and dependencies

## Critical: Use PowerShell for Directory Sizing

**Python `os.walk` and git-bash `du` both time out on Windows** when scanning large directory trees (e.g., Documents with 100+ GB across thousands of files). They walk the tree sequentially in Python/MSYS space and hit the 5-min wall.

**Always use PowerShell `Get-ChildItem`** — it runs natively in the Windows kernel and completes in seconds for the same tree:

```powershell
# Get top-level directory sizes (fast — completes in seconds)
Get-ChildItem 'C:\Users\<user>' -Directory -Force | ForEach-Object {
    $s = (Get-ChildItem $_.FullName -Recurse -File -Force -ErrorAction SilentlyContinue |
          Measure-Object -Property Length -Sum).Sum
    [PSCustomObject]@{Name=$_.Name; SizeGB=[math]::Round($s/1GB,2)}
} | Sort-Object SizeGB -Descending | Select-Object -First 25 | Format-Table -AutoSize
```

For project-level analysis (node_modules, target, .git sizes, last commit dates), see `references/project-audit-recipe.md`.

## Cleanup Priority System

Classify cleanup targets by risk level. Present them to the user as a table, then ask for confirmation on scope before executing.

### P0 — Safe Immediate Delete (no confirmation needed per-item)

| Target | Typical Path | Why Safe |
|--------|-------------|----------|
| JVM crash dumps | `~/java_error_in_*.hprof` | Post-crash heap dumps, never useful after diagnosis |
| Crash logs | `~/java_error_in_*.log`, `~/replay_pid*.log` | Crash diagnostic logs |
| Old SQL dumps | `~/_*_dump.sql` | One-time database exports |
| `nul` file | `~/nul` | Accidentally created Windows reserved name |
| NVIDIA ShadowPlay recordings | `~/Videos/NVIDIA/` | Auto-recorded gameplay footage |

### P1 — Cache Cleanup (rebuildable, high yield)

| Target | Path | Cleanup Method |
|--------|------|---------------|
| npm cache | `AppData\Local\npm-cache` | `npm cache clean --force`, then `rm -rf` residual |
| pnpm store | `AppData\Local\pnpm` | `pnpm store prune` (may remove 0 — store may be elsewhere) |
| JetBrains old version caches | `AppData\Local\JetBrains\<IDE><old-version>` | Delete old version dirs when newer version exists |
| NVIDIA DXCache | `AppData\Local\NVIDIA\DXCache` | Shader cache, rebuilt on next game launch. Some files may be locked by running processes — delete what you can, leave the rest |
| Old Downloads installers | `~/Downloads/*.exe`, `*.msi`, `*.zip` | Delete after confirming user no longer needs them |

**Pitfall:** `npm cache clean --force` often leaves 2-3 GB of residual. Follow up with `rm -rf AppData/Local/npm-cache/*` to fully clear.

### P2 — App-Specific Caches (confirm with user)

| Target | Path | Notes |
|--------|------|-------|
| Cities Skylines II | `AppData\LocalLow\Colossal Order` | Can be very large (25+ GB) |
| JianyingPro (剪映) | `AppData\Local\JianyingPro` | Draft + cache, clean from app if possible |
| baidu | `AppData\Roaming\baidu` | Baidu software cache |
| KuGou8 | `AppData\Roaming\KuGou8` | Music player cache |

### P3 — Project-Level Cleanup (requires user decision per project)

This is the highest-yield category. For a projects directory (e.g., `~/Documents/aduib-app`):

1. **Scan each project** for: total size, node_modules size, target/ size, .git size, last git commit date, git remote URL
2. **Classify** into:
   - **Build artifacts** (`target/`, `dist/`, `build/`) — safe to delete, `cargo build` / `npm run build` rebuilds
   - **Dependencies** (`node_modules/`) — safe to delete, `npm install` / `pnpm install` rebuilds
   - **Model files** (`ckpt/`, `*.safetensors`, `*.pt`) — large but need re-download, confirm with user
   - **Sidecar binaries** (`src-tauri/.sidecar-cache/`, `src-tauri/binaries/`) — downloaded tools like ffmpeg, rebuilt by build script
   - **Empty/dead projects** (no source files, no git remote, no recent commits) — candidate for full deletion
3. **Present summary** with sizes and last-modified dates
4. **Ask user** for scope confirmation via `clarify` tool
5. **Execute** in parallel where possible

## Execution Workflow

1. **Scan** top-level directory sizes with PowerShell (see script above)
2. **Drill down** into large directories (AppData, Documents, Videos)
3. **Identify** crash dumps and large files at home root (`ls -la`)
4. **Classify** all targets into P0/P1/P2/P3
5. **Present** summary table with sizes and risk levels
6. **Ask** user which priority levels to execute (use `clarify` with choices)
7. **Execute** P0 immediately, P1 in parallel, P2/P3 after confirmation
8. **Verify** by re-scanning the cleaned directories
9. **Report** total space freed with before/after comparison

## Common Windows Space Hogs

Locations that commonly consume large amounts of space, in priority order:

```
~/Documents/<project-dir>/          # Projects with target/ or node_modules/
~/AppData/Local/Programs/           # Installed IDEs (IntelliJ, PyCharm, etc.)
~/AppData/Local/JetBrains/          # IDE caches (multiple versions!)
~/AppData/Local/npm-cache/          # npm cache (can be 10+ GB)
~/AppData/Local/pnpm/               # pnpm store
~/AppData/Local/NVIDIA/DXCache/     # Shader cache
~/AppData/LocalLow/                 # Game caches (Cities Skylines, etc.)
~/AppData/Roaming/JetBrains/       # IDE config + plugins
~/Videos/NVIDIA/                    # ShadowPlay recordings
~/java_error_in_*.hprof             # JVM crash dumps (can be 5+ GB each)
~/Downloads/                       # Old installers
~/.gradle/                          # Gradle cache
~/.cargo/                           # Rust cargo cache
~/.bun/                             # Bun runtime
```

## What NOT to Delete

- `NTUSER.DAT*` — Windows registry hive (system file)
- `AppData/Local/Programs/` — installed applications (unless uninstalling)
- `.ssh/` — SSH keys
- `.gitconfig` — Git configuration
- `Documents/My Games/` — game save files
- `Documents/Tencent Files/` — QQ chat history
- `.hermes/` — Hermes Agent installation

## Reference Files

- `references/project-audit-recipe.md` — PowerShell script for auditing a projects directory (sizes, node_modules, target, .git, last commit, git remote)
- `references/windows-space-hogs.md` — Detailed breakdown of common Windows space-consuming locations and safe cleanup methods
