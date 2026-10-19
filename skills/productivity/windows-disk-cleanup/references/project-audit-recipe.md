# Project Directory Audit Recipe

PowerShell script for auditing a directory of multiple projects (e.g., `~/Documents/aduib-app`).
Produces a table showing total size, node_modules size, .git size, last commit date, and git remote for each project.

## Full Audit Script

```powershell
$base = "C:\Users\<user>\Documents\<project-dir>"
$projects = Get-ChildItem $base -Directory -Force
$results = @()
foreach ($p in $projects) {
    $path = $p.FullName

    # Total size
    $totalSize = (Get-ChildItem $path -Recurse -File -Force -ErrorAction SilentlyContinue |
                  Measure-Object -Property Length -Sum).Sum

    # node_modules sizes (may be nested at multiple levels)
    $nmSize = 0
    $nmDirs = Get-ChildItem $path -Directory -Recurse -Force -ErrorAction SilentlyContinue -Filter "node_modules"
    foreach ($nm in $nmDirs) {
        $nmSize += (Get-ChildItem $nm.FullName -Recurse -File -Force -ErrorAction SilentlyContinue |
                    Measure-Object -Property Length -Sum).Sum
    }

    # .git size
    $gitSize = 0
    $gitDir = Join-Path $path ".git"
    if (Test-Path $gitDir) {
        $gitSize = (Get-ChildItem $gitDir -Recurse -File -Force -ErrorAction SilentlyContinue |
                    Measure-Object -Property Length -Sum).Sum
    }

    # target/ size (Rust builds)
    $targetSize = 0
    $targetDirs = Get-ChildItem $path -Directory -Recurse -Force -ErrorAction SilentlyContinue -Filter "target"
    foreach ($t in $targetDirs) {
        $targetSize += (Get-ChildItem $t.FullName -Recurse -File -Force -ErrorAction SilentlyContinue |
                        Measure-Object -Property Length -Sum).Sum
    }

    # Last modified file (proxy for activity)
    $lastFile = Get-ChildItem $path -Recurse -File -Force -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTime -Descending | Select-Object -First 1
    $lastMod = if ($lastFile) { $lastFile.LastWriteTime.ToString("yyyy-MM-dd") } else { "N/A" }

    # Git remote + last commit
    $remote = ""
    $lastCommit = ""
    try {
        $remote = (git -C $path remote -v 2>$null | Select-Object -First 1)
        $lastCommit = (git -C $path log -1 --format="%ai" 2>$null)
        if ($lastCommit) { $lastCommit = $lastCommit.Substring(0,10) }
    } catch {}

    # Source file count (determines if project has real code)
    $srcFiles = (Get-ChildItem $path -Recurse -File -Force -ErrorAction SilentlyContinue |
                 Where-Object { $_.Name -match "\.(rs|ts|tsx|js|jsx|py|go|java|vue)$" } |
                 Measure-Object).Count

    $results += [PSCustomObject]@{
        Name = $p.Name
        TotalGB = [math]::Round($totalSize/1GB, 2)
        NmGB = [math]::Round($nmSize/1GB, 2)
        GitMB = [math]::Round($gitSize/1MB, 0)
        TargetGB = [math]::Round($targetSize/1GB, 2)
        LastCommit = $lastCommit
        LastMod = $lastMod
        SrcFiles = $srcFiles
        Remote = $remote
    }
}
$results | Sort-Object TotalGB -Descending | Format-Table -AutoSize
```

## Classification Decision Tree

After getting the audit table, classify each project:

```
IF TotalGB == 0 AND SrcFiles == 0 AND no Remote:
    → Empty/dead project → candidate for full directory deletion

IF has target/ (Rust) AND target/ > 0.5 GB:
    → Delete target/ — cargo build rebuilds it
    → Especially common in Tauri projects: src-tauri/target/

IF has node_modules/ AND node_modules/ > 0.1 GB:
    → Delete node_modules/ — npm install rebuilds it

IF has large model files (ckpt/, *.safetensors, *.pt) AND total > 1 GB:
    → Confirm with user — these need re-download

IF has .sidecar-cache/ or binaries/ in src-tauri/:
    → These are downloaded tools (ffmpeg, demucs, etc.)
    → Safe to delete, build script re-downloads

IF has .git/ > 500 MB:
    → Large git history. Don't delete .git/, but note it.
    → Consider `git gc --aggressive --prune=now` instead

IF LastCommit > 6 months ago AND no Remote:
    → Stale local-only project → candidate for full deletion (confirm with user)
```

## Speed Notes

- This script completes in ~90 seconds for 43 projects totaling 86 GB
- Python `os.walk` equivalent times out at 5 minutes for the same tree
- The bottleneck is `Get-ChildItem -Recurse` on directories with many small files (node_modules, target)
- For directories with 100k+ files, individual `Get-ChildItem` calls per subdirectory are faster than one giant `-Recurse`
