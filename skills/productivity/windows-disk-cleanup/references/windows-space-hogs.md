# Windows Space Hogs — Detailed Breakdown

Common locations on Windows that consume large amounts of disk space, with safe cleanup methods.

## Home Root Large Files

### JVM Crash Dumps (`.hprof`)
- **Path:** `~/java_error_in_*.hprof`
- **Size:** 2-6 GB each
- **Safe to delete:** Yes, always. These are heap dumps from JVM crashes (IntelliJ, PyCharm, RustRover, etc.)
- **Command:** `rm -f ~/java_error_in_*.hprof`

### JVM Crash Logs
- **Path:** `~/java_error_in_*.log`, `~/replay_pid*.log`
- **Size:** 0.3-0.6 MB each
- **Safe to delete:** Yes

### Old Database Dumps
- **Path:** `~/_<ip>_<port>_<date>_dump.sql`
- **Size:** 10-50 KB each
- **Safe to delete:** Yes, one-time exports

## AppData\Local

### npm-cache
- **Path:** `AppData\Local\npm-cache`
- **Typical size:** 5-15 GB
- **Cleanup:** `npm cache clean --force`
- **Pitfall:** `npm cache clean --force` often leaves 2-3 GB residual. Follow up with `rm -rf AppData/Local/npm-cache/*`
- **Safe to delete:** Yes, fully rebuildable

### pnpm store
- **Path:** `AppData\Local\pnpm\store`
- **Typical size:** 5-10 GB
- **Cleanup:** `pnpm store prune`
- **Pitfall:** `pnpm store prune` may report "Removed 0 files" because the store path may differ from where projects reference packages. Check actual size after prune.
- **Safe to delete:** Yes

### JetBrains IDE Caches
- **Path:** `AppData\Local\JetBrains\<IDE><version>\`
- **Typical size:** 1-6 GB per version
- **Cleanup:** Delete old version directories (e.g., `PyCharm2025.1` when `PyCharm2025.2` exists)
- **Safe to delete:** Yes, caches are rebuilt when the IDE starts

### NVIDIA DXCache
- **Path:** `AppData\Local\NVIDIA\DXCache`
- **Typical size:** 3-8 GB
- **Safe to delete:** Yes, shader cache rebuilt on next game launch
- **Pitfall:** Some `.nvph` files may be locked by running processes (games, GPU-accelerated apps). `rm -rf` will report "Device or resource busy" for these — delete what you can, leave the locked ones.

### NVIDIA GLCache
- **Path:** `AppData\Local\NVIDIA\GLCache`
- **Typical size:** <100 MB
- **Safe to delete:** Yes

### Installed Programs
- **Path:** `AppData\Local\Programs\<app>`
- **Typical size:** 0.5-5 GB per app
- **Safe to delete:** NO — these are installed applications. Use the app's uninstaller or Windows Settings > Apps.

## AppData\Roaming

### JetBrains Config
- **Path:** `AppData\Roaming\JetBrains`
- **Typical size:** 5-10 GB
- **Safe to delete:** Partially — old version config dirs can be deleted, but current version config contains settings and plugins

### Code (VS Code)
- **Path:** `AppData\Roaming\Code`
- **Typical size:** 3-5 GB
- **Safe to delete:** Partially — `Cache/`, `CachedData/`, `CachedExtensions/` can be deleted

## AppData\LocalLow

### Colossal Order (Cities Skylines II)
- **Path:** `AppData\LocalLow\Colossal Order`
- **Typical size:** 20-30 GB
- **Safe to delete:** Yes if not playing the game — contains workshop content and cache

## Videos

### NVIDIA ShadowPlay
- **Path:** `Videos\NVIDIA`
- **Typical size:** 10-50 GB
- **Safe to delete:** Yes, auto-recorded gameplay footage. Check if user wants to keep any.

## Project Directories

### Rust `target/` directories
- **Path:** `<project>/target/` or `<project>/src-tauri/target/`
- **Typical size:** 1-30 GB per project
- **Safe to delete:** Yes — `cargo build` rebuilds completely
- **Note:** Tauri projects have `src-tauri/target/` which can be extremely large (32 GB observed)

### node_modules/
- **Path:** `<project>/node_modules/`
- **Typical size:** 0.1-3 GB per project
- **Safe to delete:** Yes — `npm install` / `pnpm install` rebuilds
- **Note:** Can be nested at multiple levels in monorepos. Use `find -type d -name "node_modules" -prune -exec rm -rf {} +` for bulk deletion.

### Tauri sidecar cache
- **Path:** `<project>/src-tauri/.sidecar-cache/` and `<project>/src-tauri/binaries/`
- **Typical size:** 0.5-1 GB
- **Safe to delete:** Yes — build script re-downloads ffmpeg/demucs etc.

### ML model checkpoints
- **Path:** `<project>/ckpt/`, `*.safetensors`, `*.pt`, `*.bin`
- **Typical size:** 1-10 GB
- **Safe to delete:** Technically yes, but requires re-download. Always confirm with user.

## Cleanup Order (by yield and safety)

1. Rust `target/` directories (highest yield, safest)
2. JVM `.hprof` crash dumps (large, zero risk)
3. node_modules/ directories (high yield, safe)
4. npm cache (large, safe)
5. NVIDIA DXCache + ShadowPlay recordings (large, safe)
6. JetBrains old version caches (medium yield, safe)
7. ML model files (high yield, needs confirmation)
8. Empty/dead project directories (low yield, tidies up)
