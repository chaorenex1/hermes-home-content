#!/usr/bin/env python3
"""
MO2 Manager — Mod Organizer 2 实例管理和插件开发工具

功能:
  list        列出所有 MO2 实例
  info        获取实例详细信息
  path        获取 MO2 安装路径
  create-plugin  从模板创建 MO2 插件
"""

import argparse
import configparser
import json
import os
import re
import sys
from pathlib import Path


# ── Constants ────────────────────────────────────────────

MO2_INSTANCE_ROOT = Path.home() / "AppData" / "Local" / "ModOrganizer"
NON_INSTANCE_DIRS = {"cache"}


# ── Helpers ──────────────────────────────────────────────

def parse_qt_bytearray(value: str) -> str:
    """解析 @ByteArray(...) 格式的 Qt 序列化字符串。"""
    if value.startswith("@ByteArray(") and value.endswith(")"):
        inner = value[len("@ByteArray("):-1]
        # 将 \\ 替换为 \
        inner = inner.replace("\\\\", "\\")
        return inner
    return value


def parse_qt_variant(value: str) -> str:
    """简化处理 @Variant(...) 格式。"""
    if value.startswith("@Variant("):
        return "<Variant>"
    return value


def resolve_path(path_str: str) -> str:
    """解析可能包含 Qt 序列化的路径字符串。"""
    path_str = parse_qt_bytearray(path_str)
    return path_str


# ── Instance Discovery ────────────────────────────────────

def get_instances() -> list[dict]:
    """获取所有 MO2 实例列表。"""
    if not MO2_INSTANCE_ROOT.exists():
        return []

    instances = []
    for d in sorted(MO2_INSTANCE_ROOT.iterdir()):
        if not d.is_dir() or d.name in NON_INSTANCE_DIRS:
            continue

        ini_path = d / "ModOrganizer.ini"
        exe_files = list(d.glob("Mod.Organizer-*.exe"))

        instances.append({
            "name": d.name,
            "path": str(d),
            "hasIni": ini_path.exists(),
            "hasExe": len(exe_files) > 0,
            "exeFiles": [str(f) for f in exe_files],
        })

    return instances


# ── Instance Details ──────────────────────────────────────

def parse_custom_executables(raw: dict) -> list[dict]:
    """解析 [customExecutables] 节的工具列表。"""
    size = int(raw.get("size", 0))
    executables = []
    for i in range(1, size + 1):
        binary = raw.get(f"{i}\\binary", "").replace("\\\\", "/").replace("\\", "/")
        wd = raw.get(f"{i}\\workingDirectory", "").replace("\\\\", "/").replace("\\", "/")
        exe = {
            "title": raw.get(f"{i}\\title", ""),
            "binary": binary,
            "arguments": raw.get(f"{i}\\arguments", ""),
            "workingDirectory": wd,
            "hide": raw.get(f"{i}\\hide", "false") == "true",
            "toolbar": raw.get(f"{i}\\toolbar", "false") == "true",
            "steamAppID": raw.get(f"{i}\\steamAppID", ""),
        }
        executables.append(exe)
    return executables


def parse_mo2_ini(filepath: Path) -> dict[str, dict]:
    """
    Parse a MO2 ModOrganizer.ini file into a dict of sections.
    Uses raw reading to avoid configparser backslash escaping issues
    (MO2 paths like <PATH_TO_STEAM_LIBRARY> get corrupted by default configparser).
    """
    sections: dict[str, dict] = {}
    current_section = None

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # Skip empty lines
            if not line.strip():
                continue
            # Section header
            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1]
                sections[current_section] = {}
                continue
            # Key=Value
            if "=" in line and current_section is not None:
                key, _, value = line.partition("=")
                sections[current_section][key] = value

    return sections


def get_instance_info(name: str) -> dict | None:
    """获取指定实例的详细信息。"""
    ini_path = MO2_INSTANCE_ROOT / name / "ModOrganizer.ini"
    if not ini_path.exists():
        return None

    config = parse_mo2_ini(ini_path)

    result = {
        "name": name,
        "path": str(MO2_INSTANCE_ROOT / name),
        "general": {},
        "settings": {},
        "customExecutables": [],
        "recentDirectories": [],
        "servers": [],
        "plugins": {},
        "pluginBlacklist": [],
        "pluginPersistance": {},
        "dialogChoices": {},
        "widgets": {},
        "geometry": {},
        "instanceStats": {},
    }

    # ── General section ──
    if "General" in config:
        gen = config["General"]
        result["general"] = {
            "gameName": gen.get("gameName", ""),
            "gamePath": resolve_path(gen.get("gamePath", "")),
            "version": gen.get("version", ""),
            "selected_profile": resolve_path(gen.get("selected_profile", "")),
            "game_edition": gen.get("game_edition", ""),
            "first_start": gen.get("first_start", ""),
            "backup_install": gen.get("backup_install", ""),
        }

    # ── Settings section (all keys) ──
    if "Settings" in config:
        sets = config["Settings"]
        # Known boolean keys
        bool_keys = {
            "profile_local_inis", "profile_local_saves", "profile_archive_invalidation",
            "compact_downloads", "meta_downloads", "autohide_downloads",
            "check_for_updates", "use_prereleases", "center_dialogs",
            "show_change_game_confirmation", "show_menubar_on_alt",
            "double_click_previews", "display_foreign", "save_filters",
            "auto_collapse_on_hover", "autocheck_update_install",
            "endorsement_integration", "tracked_integration",
            "category_mappings", "hide_api_counter", "force_enable_core_files",
            "lock_gui", "archive_parsing_experimental", "offline_mode",
            "use_proxy", "use_custom_browser",
            "filter_regex", "regex_case_sensitive", "regex_extended",
            "filter_scroll_to_selection",
            "collapsible_separators_asc", "collapsible_separators_dsc",
            "collapsible_separators_conflicts_from", "collapsible_separators_conflicts_to",
            "collapsible_separators_per_profile",
            "colorSeparatorScrollbars",
            "collapsible_separators_icons_1", "collapsible_separators_icons_2",
            "collapsible_separators_icons_3", "collapsible_separators_icons_7",
        }
        parsed = {}
        for k, v in sets.items():
            if k in bool_keys:
                parsed[k] = (v.lower() == "true")
            else:
                parsed[k] = v
        result["settings"] = parsed

    # ── customExecutables ──
    if "customExecutables" in config:
        result["customExecutables"] = parse_custom_executables(
            config["customExecutables"]
        )

    # ── recentDirectories ──
    if "recentDirectories" in config:
        rd = config["recentDirectories"]
        size = int(rd.get("size", 0))
        dirs = []
        for i in range(1, size + 1):
            dirs.append({
                "name": rd.get(f"{i}\\name", ""),
                "directory": rd.get(f"{i}\\directory", ""),
            })
        result["recentDirectories"] = dirs

    # ── Servers ──
    if "Servers" in config:
        servers_raw = config["Servers"]
        size = int(servers_raw.get("size", 0))
        servers = []
        for i in range(1, size + 1):
            last_downloads = servers_raw.get(f"{i}\\lastDownloads", "")
            servers.append({
                "name": servers_raw.get(f"{i}\\name", ""),
                "premium": servers_raw.get(f"{i}\\premium", "") == "true",
                "lastSeen": servers_raw.get(f"{i}\\lastSeen", ""),
                "preferred": servers_raw.get(f"{i}\\preferred", "0"),
                "lastDownloads": last_downloads.split() if last_downloads.strip() else [],
            })
        result["servers"] = servers

    # ── Plugins ──
    if "Plugins" in config:
        plugins_raw = config["Plugins"]
        plugins = {}
        for k, v in plugins_raw.items():
            # Keys are like "Plugin Name\\setting"
            parts = k.split("\\", 1)
            if len(parts) == 2:
                plugin_name, setting = parts
                if plugin_name not in plugins:
                    plugins[plugin_name] = {}
                plugins[plugin_name][setting] = v
            else:
                plugins[k] = v
        result["plugins"] = plugins

    # ── pluginBlacklist ──
    if "pluginBlacklist" in config:
        bl = config["pluginBlacklist"]
        size = int(bl.get("size", 0))
        blacklist = []
        for i in range(1, size + 1):
            blacklist.append(bl.get(f"{i}\\name", ""))
        result["pluginBlacklist"] = blacklist

    # ── PluginPersistance ──
    if "PluginPersistance" in config:
        pp = config["PluginPersistance"]
        result["pluginPersistance"] = dict(pp)

    # ── DialogChoices ──
    if "DialogChoices" in config:
        result["dialogChoices"] = dict(config["DialogChoices"])

    # ── Widgets (key-value summary, skip @ByteArray values) ──
    if "Widgets" in config:
        widgets = {}
        for k, v in config["Widgets"].items():
            if v.startswith("@ByteArray("):
                widgets[k] = "<ByteArray>"
            else:
                widgets[k] = v
        result["widgets"] = widgets

    # ── Geometry (just list the keys, values are all binary) ──
    if "Geometry" in config:
        result["geometry"] = {"dialogCount": len(config["Geometry"])}

    # ── Instance stats ──
    instance_dir = MO2_INSTANCE_ROOT / name
    base_dir = instance_dir
    base_setting = result["settings"].get("base_directory")
    if base_setting:
        base_dir = Path(base_setting)

    mods_dir = base_dir / "mods"
    profiles_dir = base_dir / "profiles"
    downloads_dir = base_dir / "downloads"
    overwrite_dir = base_dir / "overwrite"
    logs_dir = instance_dir / "logs"

    mod_count = 0
    if mods_dir.exists():
        mod_count = len([d for d in mods_dir.iterdir() if d.is_dir()])

    profiles = []
    if profiles_dir.exists():
        profiles = sorted([d.name for d in profiles_dir.iterdir() if d.is_dir()])

    # Profile detail: parse each profile's ini/settings
    profile_details = []
    for pname in profiles:
        pd = {"name": pname}
        p_ini = profiles_dir / pname / "profiles.ini" if pname == "Default" else None
        # Try modlist.txt, plugins.txt, loadorder.txt
        for fn in ["plugins.txt", "loadorder.txt", "modlist.txt", "archives.txt"]:
            fp = profiles_dir / pname / fn
            if fp.exists():
                pd[fn.replace(".txt", "") + "Lines"] = sum(1 for _ in open(fp, "r", encoding="utf-8", errors="ignore"))
            else:
                pd[fn.replace(".txt", "")] = None
        profile_details.append(pd)

    exe_files = list(instance_dir.glob("Mod.Organizer-*.exe"))

    # Downloads count
    download_count = 0
    if downloads_dir.exists():
        download_count = len(list(downloads_dir.iterdir()))

    # Logs
    latest_log = None
    if logs_dir.exists():
        log_files = sorted(logs_dir.glob("*.log"), key=lambda f: f.stat().st_mtime, reverse=True)
        if log_files:
            latest_log = {
                "name": log_files[0].name,
                "mtime": log_files[0].stat().st_mtime,
            }

    result["instanceStats"] = {
        "modCount": mod_count,
        "profileCount": len(profiles),
        "profiles": profile_details,
        "hasExe": len(exe_files) > 0,
        "exePath": str(exe_files[0]) if exe_files else None,
        "modsDir": str(mods_dir),
        "profilesDir": str(profiles_dir),
        "downloadsDir": str(downloads_dir),
        "downloadCount": download_count,
        "overwriteDir": str(overwrite_dir),
        "latestLog": latest_log,
    }

    return result


# ── MO2 Path Discovery ────────────────────────────────────

def get_mo2_paths() -> dict:
    """获取所有 MO2 安装路径。"""
    result = {
        "nxmHandlerPaths": [],
        "instanceExePaths": {},
        "primaryPath": None,
        "primaryExe": None,
        "pluginsPath": None,
    }

    # Strategy 1: Parse nxmhandler.ini
    nxm_path = MO2_INSTANCE_ROOT / "nxmhandler.ini"
    if nxm_path.exists():
        config = configparser.ConfigParser()
        config.read(nxm_path, encoding="utf-8")
        if "handlers" in config:
            handlers = dict(config["handlers"])
            size = int(handlers.get("size", 0))
            for i in range(1, size + 1):
                games_raw = handlers.get(f"{i}\\games", "")
                # Strip quotes and split by comma
                games = [g.strip().strip('"') for g in games_raw.split(",")]
                handler = {
                    "games": games,
                    "executable": handlers.get(f"{i}\\executable", "").replace("\\\\", "\\"),
                    "arguments": handlers.get(f"{i}\\arguments", ""),
                }
                result["nxmHandlerPaths"].append(handler)

    # Strategy 2: Instance embedded exes
    for d in MO2_INSTANCE_ROOT.iterdir():
        if not d.is_dir() or d.name in NON_INSTANCE_DIRS:
            continue
        exe_files = list(d.glob("Mod.Organizer-*.exe"))
        if exe_files:
            result["instanceExePaths"][d.name] = str(exe_files[0])

    # Strategy 3: Pick primary from nxmhandler
    if result["nxmHandlerPaths"]:
        primary_exe = result["nxmHandlerPaths"][0]["executable"]
        result["primaryExe"] = primary_exe
        result["primaryPath"] = str(Path(primary_exe).parent)
        result["pluginsPath"] = str(Path(primary_exe).parent / "plugins")

    return result


# ── Plugin Template Generation ─────────────────────────────

PLUGIN_TEMPLATES = {
    "tool": """# {PluginName} - MO2 Tool Plugin
# Auto-generated by BGS-MO2 skill

from pathlib import Path
import mobase
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMessageBox


class {ClassName}(mobase.IPluginTool):
    \"\"\"MO2 {Description}\"\"\"

    def __init__(self):
        super().__init__()
        self.__organizer: mobase.IOrganizer = None

    def init(self, organizer: mobase.IOrganizer) -> bool:
        self.__organizer = organizer
        return True

    def name(self) -> str:
        return \"{PluginName}\"

    def localizedName(self) -> str:
        return self.tr(\"{DisplayName}\")

    def author(self) -> str:
        return \"{Author}\"

    def description(self) -> str:
        return self.tr(\"{Description}\")

    def version(self) -> mobase.VersionInfo:
        return mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.ALPHA)

    def requirements(self) -> list:
        return [
            mobase.PluginRequirementFactory.gameDependency(\"{GameName}\")
        ]

    def settings(self) -> list:
        return []

    # IPluginTool
    def displayName(self) -> str:
        return self.tr(\"{DisplayName}\")

    def tooltip(self) -> str:
        return self.tr(\"{Description}\")

    def icon(self) -> QIcon:
        return QIcon()

    def display(self) -> None:
        # TODO: Implement your tool logic here
        QMessageBox.information(
            self._parentWidget(),
            self.tr(\"{DisplayName}\"),
            self.tr(\"Plugin loaded successfully!\")
        )

    def tr(self, value: str) -> str:
        return QCoreApplication.translate(\"{ClassName}\", value)


def createPlugin() -> {ClassName}:
    return {ClassName}()
""",

    "diagnose": """# {PluginName} - MO2 Diagnose Plugin
# Auto-generated by BGS-MO2 skill

import mobase
from PyQt6.QtCore import QCoreApplication


class {ClassName}(mobase.IPluginDiagnose):
    \"\"\"MO2 {Description}\"\"\"

    def __init__(self):
        super().__init__()
        self.__organizer: mobase.IOrganizer = None

    def init(self, organizer: mobase.IOrganizer) -> bool:
        self.__organizer = organizer
        return True

    def name(self) -> str:
        return \"{PluginName}\"

    def localizedName(self) -> str:
        return self.tr(\"{DisplayName}\")

    def author(self) -> str:
        return \"{Author}\"

    def description(self) -> str:
        return self.tr(\"{Description}\")

    def version(self) -> mobase.VersionInfo:
        return mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.ALPHA)

    def requirements(self) -> list:
        return [
            mobase.PluginRequirementFactory.gameDependency(\"{GameName}\")
        ]

    def settings(self) -> list:
        return []

    def activeProblems(self) -> list[int]:
        # Return problem IDs. Empty list = no problems.
        return []

    def shortDescription(self, key: int) -> str:
        return self.tr(\"Problem detected\")

    def fullDescription(self, key: int) -> str:
        return self.tr(\"Detailed description of the problem.\")

    def hasGuidedFix(self, key: int) -> bool:
        return False

    def startGuidedFix(self, key: int) -> None:
        pass

    def tr(self, value: str) -> str:
        return QCoreApplication.translate(\"{ClassName}\", value)


def createPlugin() -> {ClassName}:
    return {ClassName}()
""",

    "free": """# {PluginName} - MO2 Free Plugin
# Auto-generated by BGS-MO2 skill

import mobase
from PyQt6.QtCore import QCoreApplication


class {ClassName}(mobase.IPlugin):
    \"\"\"MO2 {Description}\"\"\"

    def __init__(self):
        super().__init__()
        self.__organizer: mobase.IOrganizer = None

    def init(self, organizer: mobase.IOrganizer) -> bool:
        self.__organizer = organizer
        # Access organizer API here
        return True

    def name(self) -> str:
        return \"{PluginName}\"

    def localizedName(self) -> str:
        return self.tr(\"{DisplayName}\")

    def author(self) -> str:
        return \"{Author}\"

    def description(self) -> str:
        return self.tr(\"{Description}\")

    def version(self) -> mobase.VersionInfo:
        return mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.ALPHA)

    def requirements(self) -> list:
        return []

    def settings(self) -> list:
        return []

    def tr(self, value: str) -> str:
        return QCoreApplication.translate(\"{ClassName}\", value)


def createPlugin() -> {ClassName}:
    return {ClassName}()
""",
}


def create_plugin(name: str, plugin_type: str, game: str, output: str,
                  author: str = "Hermes Agent",
                  description: str = None):
    """从模板创建 MO2 插件文件。"""
    if plugin_type not in PLUGIN_TEMPLATES:
        print(f"Error: Unknown plugin type '{plugin_type}'")
        print(f"Available: {', '.join(PLUGIN_TEMPLATES.keys())}")
        return False

    class_name = name.replace(" ", "").replace("-", "_").replace(".", "_")
    display_name = name
    if not description:
        description = f"MO2 plugin: {name}"

    template = PLUGIN_TEMPLATES[plugin_type]
    content = template.format(
        PluginName=name,
        ClassName=class_name,
        DisplayName=display_name,
        Description=description,
        Author=author,
        GameName=game,
    )

    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)

    filename = class_name + ".py"
    filepath = output_path / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Created plugin: {filepath}")
    print(f"Type: {plugin_type}")
    print(f"Game: {game}")
    print(f"\nTo install: copy {filename} to MO2 plugins directory")
    return True


# ── MO2 Launch ─────────────────────────────────────────────

import subprocess

def get_launch_options() -> list[dict]:
    """获取所有可启动的 MO2 选项列表（去重）。"""
    paths = get_mo2_paths()
    seen = set()
    options = []

    # Primary from nxmhandler
    primary = paths.get("primaryExe")
    if primary and Path(primary).exists():
        key = str(Path(primary).resolve())
        if key not in seen:
            seen.add(key)
            handler_info = paths["nxmHandlerPaths"][0] if paths["nxmHandlerPaths"] else {}
            options.append({
                "source": "primary",
                "label": "主安装 (nxmhandler)",
                "path": primary,
                "games": handler_info.get("games", []),
                "version": _detect_mo2_version(primary),
            })

    # Instance-embedded exes (unique, different from primary)
    for inst_name, exe_path in paths.get("instanceExePaths", {}).items():
        if not Path(exe_path).exists():
            continue
        key = str(Path(exe_path).resolve())
        if key in seen:
            continue
        seen.add(key)
        options.append({
            "source": "instance",
            "label": f"实例 '{inst_name}'",
            "path": exe_path,
            "instance": inst_name,
            "version": _detect_mo2_version(exe_path),
        })

    return options


def _detect_mo2_version(exe_path: str) -> str:
    """从文件名或 exe 属性推断 MO2 版本。"""
    name = Path(exe_path).name
    import re
    m = re.search(r"Mod\.Organizer-([\d.]+)\.exe", name)
    if m:
        return m.group(1)
    # If named just ModOrganizer.exe, try file version metadata
    if name.lower() == "modorganizer.exe":
        try:
            import subprocess as _sp
            result = _sp.run(
                ["powershell", "-Command",
                 f"(Get-Item '{exe_path}').VersionInfo.ProductVersion"],
                capture_output=True, text=True, timeout=5
            )
            ver = result.stdout.strip()
            if ver:
                return ver
        except Exception:
            pass
    # Try from parent directory's ModOrganizer.ini (instance)
    ini = Path(exe_path).parent / "ModOrganizer.ini"
    if ini.exists():
        config = parse_mo2_ini(ini)
        if "General" in config:
            return config["General"].get("version", "unknown")
    return "primary"


def launch_mo2(index: int = 0) -> dict:
    """启动指定的 MO2 实例。index 是 launch options 列表中的索引。"""
    options = get_launch_options()
    if not options:
        return {"error": "未找到任何 MO2 安装", "launched": False}
    if index < 0 or index >= len(options):
        return {"error": f"无效索引 {index}，共 {len(options)} 个选项", "launched": False}

    target = options[index]
    exe_path = target["path"]

    if not Path(exe_path).exists():
        return {"error": f"文件不存在: {exe_path}", "launched": False}

    try:
        # DETACHED_PROCESS: MO2 独立运行，不随本进程退出
        subprocess.Popen(
            [exe_path],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            cwd=str(Path(exe_path).parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {
            "launched": True,
            "path": exe_path,
            "label": target["label"],
            "version": target.get("version", "unknown"),
            "instance": target.get("instance"),
        }
    except Exception as e:
        return {"error": str(e), "launched": False}

def get_profile_info(instance_name: str, profile_name: str) -> dict | None:
    """获取指定实例的 Profile 详细信息。"""
    ini_path = MO2_INSTANCE_ROOT / instance_name / "ModOrganizer.ini"
    if not ini_path.exists():
        return None

    config = parse_mo2_ini(ini_path)

    # Determine profile directory
    base_dir = MO2_INSTANCE_ROOT / instance_name
    if "Settings" in config:
        bd = config["Settings"].get("base_directory")
        if bd:
            base_dir = Path(bd)

    profile_dir = base_dir / "profiles" / profile_name
    if not profile_dir.exists():
        return None

    result = {
        "instance": instance_name,
        "profile": profile_name,
        "path": str(profile_dir),
        "files": {},
        "summary": {},
    }

    # ── plugins.txt ──
    plugins_path = profile_dir / "plugins.txt"
    if plugins_path.exists():
        lines = plugins_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        plugins_enabled = []
        plugins_disabled = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("*"):
                plugins_enabled.append(line[1:])
            else:
                plugins_disabled.append(line)
        result["files"]["plugins.txt"] = {
            "path": str(plugins_path),
            "enabledCount": len(plugins_enabled),
            "disabledCount": len(plugins_disabled),
            "totalCount": len(plugins_enabled) + len(plugins_disabled),
            "enabled": plugins_enabled,
            "disabled": plugins_disabled,
        }

    # ── loadorder.txt ──
    lo_path = profile_dir / "loadorder.txt"
    if lo_path.exists():
        lines = lo_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        loadorder = [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]
        result["files"]["loadorder.txt"] = {
            "path": str(lo_path),
            "count": len(loadorder),
            "order": loadorder,
        }

    # ── modlist.txt ──
    modlist_path = profile_dir / "modlist.txt"
    if modlist_path.exists():
        lines = modlist_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        mods_enabled = []
        mods_disabled = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("+"):
                mods_enabled.append(line[1:])
            elif line.startswith("-"):
                mods_disabled.append(line[1:])
            else:
                mods_enabled.append(line)
        result["files"]["modlist.txt"] = {
            "path": str(modlist_path),
            "enabledCount": len(mods_enabled),
            "disabledCount": len(mods_disabled),
            "totalCount": len(mods_enabled) + len(mods_disabled),
            "enabled": mods_enabled,
            "disabled": mods_disabled,
        }

    # ── archives.txt ──
    archives_path = profile_dir / "archives.txt"
    if archives_path.exists():
        lines = archives_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        archives = [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]
        result["files"]["archives.txt"] = {
            "path": str(archives_path),
            "count": len(archives),
            "archives": archives,
        }

    # ── lockedorder.txt ──
    lock_path = profile_dir / "lockedorder.txt"
    if lock_path.exists():
        content = lock_path.read_text(encoding="utf-8", errors="ignore")
        locked = [l.strip() for l in content.splitlines() if l.strip() and not l.strip().startswith("#")]
        result["files"]["lockedorder.txt"] = {
            "path": str(lock_path),
            "count": len(locked),
            "locked": locked,
        }

    # ── initweaks.ini ──
    ini_tweaks_path = profile_dir / "initweaks.ini"
    if ini_tweaks_path.exists():
        import configparser as cp
        c = cp.ConfigParser()
        c.read(ini_tweaks_path, encoding="utf-8")
        tweaks = {}
        for section in c.sections():
            tweaks[section] = dict(c[section])
        result["files"]["initweaks.ini"] = {
            "path": str(ini_tweaks_path),
            "tweaks": tweaks,
        }

    # ── settings.ini (profile-level) ──
    settings_ini_path = profile_dir / "settings.ini"
    if settings_ini_path.exists():
        import configparser as cp
        c = cp.ConfigParser()
        c.read(settings_ini_path, encoding="utf-8")
        prof_settings = {}
        for section in c.sections():
            prof_settings[section] = dict(c[section])
        result["files"]["settings.ini"] = {
            "path": str(settings_ini_path),
            "settings": prof_settings,
        }

    # ── Config files (non-backup game/profile INIs etc.) ──
    import re
    backup_pattern = re.compile(r"\.\d{4}_\d{2}_\d{2}_\d{2}_\d{2}_\d{2}$")

    config_files = []
    backup_files = []

    for f in sorted(profile_dir.iterdir()):
        if not f.is_file():
            continue
        if f.name in {
            "plugins.txt", "loadorder.txt", "modlist.txt",
            "archives.txt", "lockedorder.txt", "initweaks.ini", "settings.ini"
        }:
            continue

        # Check if this is a backup (has date suffix)
        stem = f.stem  # e.g., "loadorder.txt" from "loadorder.txt.2026_05_31_15_07_32"
        if backup_pattern.search(f.name):
            backup_files.append({
                "name": f.name,
                "size": f.stat().st_size,
                "mtime": f.stat().st_mtime,
            })
        else:
            entry = {
                "name": f.name,
                "size": f.stat().st_size,
                "mtime": f.stat().st_mtime,
            }
            # Read content for text-based config files
            if f.suffix.lower() in {".ini", ".txt", ".cfg", ".json", ".toml"}:
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    # For INI files, parse sections
                    if f.suffix.lower() == ".ini":
                        import configparser as cp
                        c = cp.ConfigParser()
                        c.read(f, encoding="utf-8")
                        entry["sections"] = {}
                        for section in c.sections():
                            entry["sections"][section] = dict(c[section])
                    else:
                        lines = content.splitlines()
                        entry["lines"] = len(lines)
                        entry["content"] = content[:5000]  # Cap at 5KB
                except Exception:
                    entry["content"] = "<binary or unreadable>"
            elif f.stat().st_size < 1024:  # Small binary, show hex
                try:
                    entry["hexPreview"] = f.read_bytes()[:64].hex()
                except Exception:
                    entry["content"] = "<binary>"
            else:
                entry["content"] = "<binary, too large>"
            config_files.append(entry)

    if config_files:
        result["files"]["_configFiles"] = config_files
    if backup_files:
        result["files"]["_backups"] = backup_files

    # ── Summary ──
    result["summary"] = {
        "enabledPlugins": result["files"].get("plugins.txt", {}).get("enabledCount", 0),
        "disabledPlugins": result["files"].get("plugins.txt", {}).get("disabledCount", 0),
        "loadOrderEntries": result["files"].get("loadorder.txt", {}).get("count", 0),
        "enabledMods": result["files"].get("modlist.txt", {}).get("enabledCount", 0),
        "disabledMods": result["files"].get("modlist.txt", {}).get("disabledCount", 0),
        "archives": result["files"].get("archives.txt", {}).get("count", 0),
        "lockedPlugins": result["files"].get("lockedorder.txt", {}).get("count", 0),
        "hasIniTweaks": "initweaks.ini" in result["files"],
        "hasProfileSettings": "settings.ini" in result["files"],
        "configFilesCount": len(config_files),
        "backupFilesCount": len(backup_files),
    }

    return result

def main():
    # Query running MO2 for live state (via subprocess, more reliable than import)
    import sys as _sys, subprocess as _sp, json as _json

    def _query_mo2_live() -> dict | None:
        """Query running MO2 plugin for live state. Returns dict or None."""
        try:
            script = str(Path(__file__).resolve().parent / "mo2_control.py")
            r = _sp.run([_sys.executable, script, "state", "."],
                       capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                data = _json.loads(r.stdout)
                if data.get("ok"):
                    return data["state"]
        except Exception:
            pass
        return None

    _live_state = _query_mo2_live()
    _live_instance = _live_state.get("basePath", "") if _live_state else ""
    _live_profile = _live_state.get("profileName", "") if _live_state else ""

    # Resolve instance name from live basePath
    def _resolve_from_live(base_path: str) -> str:
        if not base_path:
            return ""
        for d in sorted(MO2_INSTANCE_ROOT.iterdir()):
            if not d.is_dir() or d.name in NON_INSTANCE_DIRS:
                continue
            ini = d / "ModOrganizer.ini"
            if not ini.exists():
                continue
            config = parse_mo2_ini(ini)
            bd = config.get("Settings", {}).get("base_directory", "")
            instance_base = str(MO2_INSTANCE_ROOT / d.name)
            if bd and bd.replace("\\", "/") == base_path.replace("\\", "/"):
                return d.name
            if base_path.replace("\\", "/").startswith(str(instance_base).replace("\\", "/")):
                return d.name
        return base_path

    _live_instance_name = _resolve_from_live(_live_instance)

    parser = argparse.ArgumentParser(
        description="MO2 Manager — Mod Organizer 2 实例管理和插件开发",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python mo2_manager.py list
  python mo2_manager.py info "juelunv5"
  python mo2_manager.py info --all
  python mo2_manager.py path
  python mo2_manager.py create-plugin MyPlugin --type tool --game "Skyrim Special Edition"
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="命令")

    # list
    list_parser = subparsers.add_parser("list", help="列出所有实例")
    list_parser.add_argument("--verbose", "-v", action="store_true",
                             help="显示详细信息")

    # info
    info_parser = subparsers.add_parser("info", help="获取实例详情")
    info_parser.add_argument("name", nargs="?", help="实例名（省略则 --all）")
    info_parser.add_argument("--all", action="store_true", help="所有实例")

    # path
    subparsers.add_parser("path", help="获取 MO2 安装路径")

    # launch
    launch_parser = subparsers.add_parser("launch", help="启动 MO2 管理器")
    launch_parser.add_argument("--list", action="store_true",
                               help="列出可启动的 MO2 选项")
    launch_parser.add_argument("index", nargs="?", type=int, default=None,
                               help="启动第 N 个选项（0=第一个）")

    # profile
    prof_parser = subparsers.add_parser("profile", help="获取 Profile 详细信息")
    prof_parser.add_argument("instance", help="实例名")
    prof_parser.add_argument("profile", nargs="?", help="Profile 名（省略则列出所有）")

    # create-plugin
    cp_parser = subparsers.add_parser("create-plugin", help="创建插件模板")
    cp_parser.add_argument("--list-templates", action="store_true",
                           help="列出可用模板")
    cp_parser.add_argument("name", nargs="?", help="插件名称")
    cp_parser.add_argument("--type", "-t", default="tool",
                           choices=list(PLUGIN_TEMPLATES.keys()),
                           help="插件类型")
    cp_parser.add_argument("--game", "-g", default="Skyrim Special Edition",
                           help="目标游戏")
    cp_parser.add_argument("--author", "-a", default="Hermes Agent",
                           help="作者名")
    cp_parser.add_argument("--description", "-d", help="插件描述")
    cp_parser.add_argument("--output", "-o", default=".",
                           help="输出目录")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "list":
        instances = get_instances()
        active_instance = _live_instance_name
        active_profile = _live_profile

        if args.verbose:
            result = []
            for inst in instances:
                entry = dict(inst)
                if active_instance and inst["name"] == active_instance:
                    entry["active"] = True
                    entry["activeProfile"] = active_profile
                result.append(entry)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            for inst in instances:
                exe_mark = " [EXE]" if inst["hasExe"] else ""
                active_mark = ""
                if active_instance and inst["name"] == active_instance:
                    active_mark = f" ← 当前 ({active_profile})" if active_profile else " ← 当前"
                print(f"  {inst['name']}{exe_mark}{active_mark}")
            print(f"\n  Total: {len(instances)} instance(s)")

    elif args.command == "info":
        if getattr(args, "all", False) or not args.name:
            instances = get_instances()
            all_info = []
            for inst in instances:
                info = get_instance_info(inst["name"])
                if info:
                    all_info.append(info)
            print(json.dumps(all_info, indent=2, ensure_ascii=False))
        else:
            info = get_instance_info(args.name)
            if info:
                if _live_state:
                    info["mo2LiveState"] = {
                        "instance": _live_instance_name,
                        "profile": _live_profile,
                        "game": _live_state.get("gameName", ""),
                        "appVersion": _live_state.get("appVersion", ""),
                        "modCount": _live_state.get("modCount", 0),
                        "pluginCount": _live_state.get("pluginCount", 0),
                        "isCurrent": (_live_instance_name == args.name),
                    }
                print(json.dumps(info, indent=2, ensure_ascii=False))
            else:
                print(f"Instance '{args.name}' not found", file=sys.stderr)
                sys.exit(1)

    elif args.command == "path":
        paths = get_mo2_paths()
        if _live_state:
            paths["mo2LiveState"] = {
                "instance": _live_instance_name,
                "profile": _live_profile,
                "game": _live_state.get("gameName", ""),
            }
        print(json.dumps(paths, indent=2, ensure_ascii=False))

    elif args.command == "launch":
        options = get_launch_options()
        if args.list:
            if not options:
                print("未找到任何 MO2 安装")
            else:
                for i, opt in enumerate(options):
                    games_str = ", ".join(opt.get("games", [])) if opt.get("games") else ""
                    extra = f" ({games_str})" if games_str else ""
                    print(f"  [{i}] {opt['label']} v{opt['version']}{extra}")
                    print(f"      {opt['path']}")
        elif args.index is not None:
            result = launch_mo2(args.index)
            if result["launched"]:
                print(f"已启动: {result['label']} (v{result['version']})")
                print(f"路径: {result['path']}")
            else:
                print(f"启动失败: {result.get('error', 'unknown')}", file=sys.stderr)
                sys.exit(1)
        else:
            # No index, no --list: auto-launch if only one, otherwise list
            if len(options) == 0:
                print("未找到任何 MO2 安装", file=sys.stderr)
                sys.exit(1)
            elif len(options) == 1:
                result = launch_mo2(0)
                if result["launched"]:
                    print(f"已启动唯一 MO2: {result['label']} (v{result['version']})")
                else:
                    print(f"启动失败: {result.get('error', 'unknown')}", file=sys.stderr)
                    sys.exit(1)
            else:
                # Multiple options: list and tell user to pick
                print(f"发现 {len(options)} 个 MO2 安装，请选择：")
                for i, opt in enumerate(options):
                    games_str = ", ".join(opt.get("games", [])) if opt.get("games") else ""
                    extra = f" ({games_str})" if games_str else ""
                    print(f"  [{i}] {opt['label']} v{opt['version']}{extra}")
                    print(f"      {opt['path']}")
                print(f"\n使用 'launch <索引号>' 启动指定实例")

    elif args.command == "profile":
        profile_name = args.profile
        # Auto-detect profile from running MO2 if not specified
        if not profile_name and _live_profile:
            profile_name = _live_profile

        if profile_name:
            info = get_profile_info(args.instance, profile_name)
            if info:
                if _live_state:
                    info["mo2LiveState"] = {
                        "instance": _live_instance_name,
                        "profile": _live_profile,
                        "isCurrent": True,
                    }
                print(json.dumps(info, indent=2, ensure_ascii=False))
            else:
                print(f"Profile '{profile_name}' not found in instance '{args.instance}'",
                      file=sys.stderr)
                sys.exit(1)
        else:
            # List all profiles for the instance
            instance_info = get_instance_info(args.instance)
            if instance_info:
                active_profile = _live_profile
                for p in instance_info["instanceStats"]["profiles"]:
                    mark = " ← 当前" if (active_profile and p["name"] == active_profile) else ""
                    print(f"  {p['name']}{mark}")
                    for k, v in p.items():
                        if k != "name":
                            print(f"    {k}: {v}")
                print(f"\n  Total: {instance_info['instanceStats']['profileCount']} profile(s)")
            else:
                print(f"Instance '{args.instance}' not found", file=sys.stderr)
                sys.exit(1)

    elif args.command == "create-plugin":
        if args.list_templates:
            print("Available templates:")
            for t in PLUGIN_TEMPLATES:
                print(f"  {t}")
            return
        create_plugin(
            name=args.name,
            plugin_type=args.type,
            game=args.game,
            output=args.output,
            author=args.author,
            description=args.description,
        )


if __name__ == "__main__":
    main()
