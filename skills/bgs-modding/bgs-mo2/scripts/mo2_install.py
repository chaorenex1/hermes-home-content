#!/usr/bin/env python3
"""
MO2 Plugin Installer — 安装 BGS-MO2 扩展插件到所有 MO2 实例的 plugins 目录
用法:
  python mo2_install.py --list     # 列出所有 MO2 plugins 目录
  python mo2_install.py --all      # 安装到所有检测到的目录
  python mo2_install.py            # 安装到第一个检测到的目录
"""

import shutil
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
PLUGINS = {
    "bgs_mo2_control.py": SKILL_DIR / "scripts" / "bgs_mo2_control.py",
    "bgs_nexus_modpage.py": SKILL_DIR / "scripts" / "bgs_nexus_modpage.py",
    "bgs_preview.py": SKILL_DIR / "scripts" / "bgs_preview.py",
}
MO2_INSTANCE_ROOT = Path.home() / "AppData" / "Local" / "ModOrganizer"


def parse_mo2_ini(filepath: Path) -> dict:
    sections = {}; current_section = None
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1]; sections[current_section] = {}
                continue
            if "=" in line and current_section is not None:
                key, _, value = line.partition("=")
                sections[current_section][key] = value
    return sections


def find_all_mo2_plugins_dirs() -> list[Path]:
    """Find ALL MO2 plugins directories (nxmhandler + all instance base_directories)."""
    plugins_dirs = []

    # 1. From nxmhandler.ini
    nxm = MO2_INSTANCE_ROOT / "nxmhandler.ini"
    if nxm.exists():
        config = parse_mo2_ini(nxm)
        if "handlers" in config:
            handlers = config["handlers"]
            size = int(handlers.get("size", 0))
            for i in range(1, size + 1):
                exe = handlers.get(f"{i}\\executable", "")
                if exe:
                    exe = exe.replace("\\\\", "\\")
                    plugins = Path(exe).parent / "plugins"
                    if plugins.exists() and plugins not in plugins_dirs:
                        plugins_dirs.append(plugins)

    # 2. From ALL instance base_directories (even those without embedded exe)
    for d in sorted(MO2_INSTANCE_ROOT.iterdir()):
        if not d.is_dir() or d.name == "cache": continue
        ini = d / "ModOrganizer.ini"
        if not ini.exists(): continue
        config = parse_mo2_ini(ini)
        bd = config.get("Settings", {}).get("base_directory", "")
        if bd:
            plugins = Path(bd) / "plugins"
            if plugins.exists() and plugins not in plugins_dirs:
                plugins_dirs.append(plugins)

    # 3. Also check instance directories directly (portable installs)
    for d in sorted(MO2_INSTANCE_ROOT.iterdir()):
        if not d.is_dir() or d.name == "cache": continue
        plugins = d / "plugins"
        if plugins.exists() and plugins not in plugins_dirs:
            plugins_dirs.append(plugins)

    return plugins_dirs


def install_to(plugins_dir: Path) -> dict:
    """Install all plugins to target dir. Returns result dict."""
    results = []
    for name, src in PLUGINS.items():
        if not src.exists():
            results.append({"file": name, "ok": False, "error": "source not found"})
            continue
        dst = plugins_dir / name
        backup = None
        if dst.exists():
            backup = dst.with_suffix(".py.bak")
            shutil.copy2(dst, backup)
        shutil.copy2(src, dst)
        results.append({
            "file": name, "ok": True,
            "installed": str(dst),
            "backup": str(backup) if backup else None,
        })
    return {"ok": True, "pluginsDir": str(plugins_dir), "results": results}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Install BGS-MO2 plugins to MO2")
    parser.add_argument("--all", action="store_true", help="安装到所有检测到的 MO2 plugins 目录")
    parser.add_argument("--list", action="store_true", help="列出所有 MO2 plugins 目录")
    parser.add_argument("--target", "-t", help="指定目标目录")
    args = parser.parse_args()

    if args.list:
        dirs = find_all_mo2_plugins_dirs()
        if dirs:
            print(f"Found {len(dirs)} MO2 plugins director(ies):")
            for i, d in enumerate(dirs):
                print(f"  [{i}] {d}")
        else:
            print("No MO2 plugins directories found.")
        return

    if args.target:
        targets = [Path(args.target)]
    elif args.all:
        targets = find_all_mo2_plugins_dirs()
        if not targets:
            print("ERROR: No MO2 plugins directories found.", file=sys.stderr)
            sys.exit(1)
    else:
        targets = find_all_mo2_plugins_dirs()
        if not targets:
            print("ERROR: No MO2 plugins directories found.", file=sys.stderr)
            sys.exit(1)
        targets = targets[:1]  # Default: first only

    for t in targets:
        result = install_to(t)
        if result["ok"]:
            ok_count = sum(1 for r in result["results"] if r["ok"])
            print(f"✓ {t} ({ok_count}/{len(result['results'])} files)")
            for r in result["results"]:
                status = "✓" if r["ok"] else "✗"
                extra = f" (backup: {r.get('backup','')})" if r.get("backup") else ""
                print(f"   {status} {r['file']}{extra}")
        else:
            print(f"✗ {t}: failed")
    print(f"\n  Restart MO2 to activate plugins.")


if __name__ == "__main__":
    main()
