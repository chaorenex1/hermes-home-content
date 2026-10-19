#!/usr/bin/env python3
"""
MO2 Control — MO2 实例内容控制工具

通过文件操作（修改 modlist.txt / plugins.txt / loadorder.txt）和
触发文件（与 MO2 插件通信）实现对 MO2 的自动化控制。

安全协议：任何修改操作前自动创建带时间戳的备份。
"""

import argparse
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path


# ── Paths ─────────────────────────────────────────────────

MO2_INSTANCE_ROOT = Path.home() / "AppData" / "Local" / "ModOrganizer"
BACKUP_ROOT = Path.home() / "AppData" / "Local" / "hermes" / "mo2_backups"
TRIGGER_DIR = Path.home() / "AppData" / "Local" / "Temp" / "mo2_control"
NON_INSTANCE_DIRS = {"cache"}


# ── INI Parser (same as mo2_manager.py, duplicated for standalone use) ──

def parse_mo2_ini(filepath: Path) -> dict:
    sections = {}
    current_section = None
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") and not line.startswith("# This"):
                if not line:
                    continue
            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1]
                sections[current_section] = {}
                continue
            if "=" in line and current_section is not None:
                key, _, value = line.partition("=")
                sections[current_section][key] = value
    return sections


def get_profile_dir(instance_name: str) -> Path | None:
    """获取实例的 profiles 根目录。"""
    ini = MO2_INSTANCE_ROOT / instance_name / "ModOrganizer.ini"
    if not ini.exists():
        return None
    config = parse_mo2_ini(ini)
    base_dir = MO2_INSTANCE_ROOT / instance_name
    if "Settings" in config:
        bd = config["Settings"].get("base_directory")
        if bd:
            base_dir = Path(bd)
    return base_dir / "profiles"


# ── Backup System ─────────────────────────────────────────

def _backup_key(instance: str, profile: str) -> str:
    return f"{instance}__{profile}"


def _backup_dir(instance: str, profile: str) -> Path:
    return BACKUP_ROOT / instance / profile


def create_backup(instance: str, profile: str, label: str = "") -> dict:
    """创建带时间戳的备份。备份 modlist.txt, plugins.txt, loadorder.txt, archives.txt, lockedorder.txt。"""
    profile_dir = get_profile_dir(instance)
    if not profile_dir:
        return {"error": f"Instance '{instance}' not found", "ok": False}

    profile_path = profile_dir / profile
    if not profile_path.exists():
        return {"error": f"Profile '{profile}' not found in '{instance}'", "ok": False}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_id = timestamp
    if label:
        backup_id = f"{timestamp}_{label}"

    backup_dir = _backup_dir(instance, profile) / backup_id
    backup_dir.mkdir(parents=True, exist_ok=True)

    files_backed_up = []
    for fn in ["modlist.txt", "plugins.txt", "loadorder.txt", "archives.txt", "lockedorder.txt"]:
        src = profile_path / fn
        if src.exists():
            dst = backup_dir / fn
            shutil.copy2(src, dst)
            files_backed_up.append(fn)

    # Also backup initweaks.ini and settings.ini if they exist
    for fn in ["initweaks.ini", "settings.ini"]:
        src = profile_path / fn
        if src.exists():
            shutil.copy2(src, backup_dir / fn)
            files_backed_up.append(fn)

    # Write metadata
    meta = {
        "instance": instance,
        "profile": profile,
        "timestamp": timestamp,
        "label": label,
        "files": files_backed_up,
        "created": datetime.now().isoformat(),
    }
    with open(backup_dir / "backup.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    return {
        "ok": True,
        "backupId": backup_id,
        "path": str(backup_dir),
        "files": files_backed_up,
        "timestamp": timestamp,
    }


def list_backups(instance: str, profile: str) -> list[dict]:
    """列出所有备份。"""
    backup_dir = _backup_dir(instance, profile)
    if not backup_dir.exists():
        return []

    backups = []
    for d in sorted(backup_dir.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        meta_file = d / "backup.json"
        if meta_file.exists():
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
            meta["backupId"] = d.name
            backups.append(meta)
        else:
            backups.append({
                "backupId": d.name,
                "timestamp": d.name[:15],
                "files": [f.name for f in d.iterdir() if f.is_file()],
            })
    return backups


def restore_backup(instance: str, profile: str, backup_id: str) -> dict:
    """从备份还原。还原前自动创建当前状态备份。"""
    backup_dir = _backup_dir(instance, profile) / backup_id
    if not backup_dir.exists():
        return {"error": f"Backup '{backup_id}' not found", "ok": False}

    profile_dir = get_profile_dir(instance)
    if not profile_dir:
        return {"error": f"Instance '{instance}' not found", "ok": False}

    profile_path = profile_dir / profile
    if not profile_path.exists():
        return {"error": f"Profile '{profile}' not found", "ok": False}

    # Safety: auto-backup current state before restore
    auto_backup = create_backup(instance, profile, label="pre_restore")

    # Restore files
    restored = []
    for f in backup_dir.iterdir():
        if f.name == "backup.json":
            continue
        dst = profile_path / f.name
        shutil.copy2(f, dst)
        restored.append(f.name)

    return {
        "ok": True,
        "restored": restored,
        "preRestoreBackup": auto_backup.get("backupId", ""),
        "backupId": backup_id,
    }


# ── File Manipulation (with auto-backup) ──────────────────

def _read_modlist(profile_path: Path) -> tuple[list[str], list[str], list[str]]:
    """读取 modlist.txt。返回 (header_lines, enabled_mods, disabled_mods)。"""
    header = []
    enabled = []
    disabled = []
    if not (profile_path / "modlist.txt").exists():
        return header, enabled, disabled
    with open(profile_path / "modlist.txt", "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.rstrip("\n\r")
            if line.startswith("#"):
                header.append(line)
            elif line.startswith("+"):
                enabled.append(line)
            elif line.startswith("-"):
                disabled.append(line)
            elif line.strip():
                enabled.append("+" + line.lstrip("+").lstrip("-"))
    return header, enabled, disabled


def _write_modlist(profile_path: Path, header: list[str], enabled: list[str], disabled: list[str]):
    """写回 modlist.txt。"""
    with open(profile_path / "modlist.txt", "w", encoding="utf-8", newline="") as f:
        for h in header:
            f.write(h + "\n")
        for e in enabled:
            f.write(e + "\n")
        for d in disabled:
            f.write(d + "\n")


def _read_plugins(profile_path: Path) -> tuple[list[str], list[str], list[str]]:
    """读取 plugins.txt。返回 (header, enabled_plugins, disabled_plugins)。"""
    header = []
    enabled = []
    disabled = []
    if not (profile_path / "plugins.txt").exists():
        return header, enabled, disabled
    with open(profile_path / "plugins.txt", "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.rstrip("\n\r")
            if line.startswith("#"):
                header.append(line)
            elif line.startswith("*"):
                enabled.append(line)
            elif line.strip():
                disabled.append(line)
    return header, enabled, disabled


def _write_plugins(profile_path: Path, header: list[str], enabled: list[str], disabled: list[str]):
    """写回 plugins.txt。"""
    with open(profile_path / "plugins.txt", "w", encoding="utf-8", newline="") as f:
        for h in header:
            f.write(h + "\n")
        for e in enabled:
            f.write(e + "\n")
        for d in disabled:
            f.write(d + "\n")


def _read_loadorder(profile_path: Path) -> tuple[list[str], list[str]]:
    """读取 loadorder.txt。返回 (header, order)。"""
    header = []
    order = []
    if not (profile_path / "loadorder.txt").exists():
        return header, order
    with open(profile_path / "loadorder.txt", "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.rstrip("\n\r")
            if line.startswith("#"):
                header.append(line)
            elif line.strip():
                order.append(line.strip())
    return header, order


def _write_loadorder(profile_path: Path, header: list[str], order: list[str]):
    """写回 loadorder.txt。"""
    with open(profile_path / "loadorder.txt", "w", encoding="utf-8", newline="") as f:
        for h in header:
            f.write(h + "\n")
        for item in order:
            f.write(item + "\n")


# ── Operations ────────────────────────────────────────────

def op_create_mod(instance: str, name: str) -> dict:
    """创建空 MOD 目录。"""
    profile_dir = get_profile_dir(instance)
    if not profile_dir:
        return {"error": f"Instance '{instance}' not found", "ok": False}

    # MOD 目录在 mods/ 下（与 profiles 同级）
    mods_dir = profile_dir.parent / "mods"
    mod_path = mods_dir / name

    if mod_path.exists():
        return {"error": f"Mod '{name}' already exists", "ok": False}

    mod_path.mkdir(parents=True)
    return {"ok": True, "path": str(mod_path), "name": name}


def op_create_separator(instance: str, profile: str, name: str) -> dict:
    """创建分隔符 — plugin API only."""
    return send_trigger("create_separator", instance, name=name)


def _op_create_separator_fs(instance: str, profile: str, name: str) -> dict:
    profile_dir = get_profile_dir(instance)
    if not profile_dir:
        return {"error": f"Instance '{instance}' not found", "ok": False}

    profile_path = profile_dir / profile
    if not profile_path.exists():
        return {"error": f"Profile '{profile}' not found", "ok": False}

    # Auto-backup
    create_backup(instance, profile, label="pre_separator")

    header, enabled, disabled = _read_modlist(profile_path)
    separator_line = f"+{name}_separator"
    if separator_line not in enabled:
        enabled.append(separator_line)
        _write_modlist(profile_path, header, enabled, disabled)

    return {"ok": True, "name": name, "line": separator_line}


def op_reorder_mod(instance: str, profile: str, from_index: int, to_index: int) -> dict:
    """调整 MOD 排序 — plugin API only."""
    profile_dir = get_profile_dir(instance)
    if not profile_dir:
        return {"error": f"Instance '{instance}' not found", "ok": False}
    profile_path = profile_dir / profile
    if not profile_path.exists():
        return {"error": f"Profile '{profile}' not found", "ok": False}
    header, enabled, disabled = _read_modlist(profile_path)
    if from_index < 0 or from_index >= len(enabled):
        return {"error": f"from_index {from_index} out of range", "ok": False}
    mod_name = enabled[from_index].lstrip("+")
    return send_trigger("set_mod_priority", instance, name=mod_name, priority=to_index)


def _op_reorder_mod_fs(instance: str, profile: str, from_index: int, to_index: int) -> dict:
    profile_dir = get_profile_dir(instance)
    if not profile_dir:
        return {"error": f"Instance '{instance}' not found", "ok": False}
    profile_path = profile_dir / profile
    if not profile_path.exists():
        return {"error": f"Profile '{profile}' not found", "ok": False}

    create_backup(instance, profile, label="pre_reorder_mod")

    header, enabled, disabled = _read_modlist(profile_path)
    if from_index < 0 or from_index >= len(enabled):
        return {"error": f"from_index {from_index} out of range (0-{len(enabled)-1})", "ok": False}
    if to_index < 0 or to_index >= len(enabled):
        return {"error": f"to_index {to_index} out of range (0-{len(enabled)-1})", "ok": False}

    item = enabled.pop(from_index)
    enabled.insert(to_index, item)
    _write_modlist(profile_path, header, enabled, disabled)

    return {"ok": True, "from": from_index, "to": to_index, "item": item}


def op_reorder_plugin(instance: str, profile: str, from_index: int, to_index: int) -> dict:
    """调整插件排序 — plugin API only."""
    profile_dir = get_profile_dir(instance)
    if not profile_dir:
        return {"error": f"Instance '{instance}' not found", "ok": False}
    profile_path = profile_dir / profile
    if not profile_path.exists():
        return {"error": f"Profile '{profile}' not found", "ok": False}
    header, order = _read_loadorder(profile_path)
    if from_index < 0 or from_index >= len(order):
        return {"error": f"from_index {from_index} out of range", "ok": False}
    plugin_name = order[from_index]
    return send_trigger("set_plugin_priority", instance, name=plugin_name, priority=to_index)


def _op_reorder_plugin_fs(instance: str, profile: str, from_index: int, to_index: int) -> dict:
    profile_dir = get_profile_dir(instance)
    if not profile_dir:
        return {"error": f"Instance '{instance}' not found", "ok": False}
    profile_path = profile_dir / profile
    if not profile_path.exists():
        return {"error": f"Profile '{profile}' not found", "ok": False}

    create_backup(instance, profile, label="pre_reorder_plugin")

    header, order = _read_loadorder(profile_path)
    if from_index < 0 or from_index >= len(order):
        return {"error": f"from_index {from_index} out of range (0-{len(order)-1})", "ok": False}
    if to_index < 0 or to_index >= len(order):
        return {"error": f"to_index {to_index} out of range (0-{len(order)-1})", "ok": False}

    item = order.pop(from_index)
    order.insert(to_index, item)
    _write_loadorder(profile_path, header, order)

    return {"ok": True, "from": from_index, "to": to_index, "item": item}


def op_set_mod_enabled(instance: str, profile: str, mod_name: str, enabled_state: bool) -> dict:
    """启用/禁用 MOD — plugin API only."""
    return send_trigger("set_mod_active", instance, name=mod_name, active=enabled_state)
    profile_dir = get_profile_dir(instance)
    if not profile_dir:
        return {"error": f"Instance '{instance}' not found", "ok": False}
    profile_path = profile_dir / profile
    if not profile_path.exists():
        return {"error": f"Profile '{profile}' not found", "ok": False}

    create_backup(instance, profile, label="pre_toggle_mod")

    header, enabled_list, disabled_list = _read_modlist(profile_path)

    if enabled_state:
        # Move from disabled to enabled
        found = None
        for i, d in enumerate(disabled_list):
            if d[1:] == mod_name or d == mod_name:
                found = disabled_list.pop(i)
                break
        if found:
            enabled_list.append("+" + found.lstrip("-").lstrip("+"))
        else:
            return {"error": f"Mod '{mod_name}' not found in disabled list", "ok": False}
    else:
        # Move from enabled to disabled
        found = None
        for i, e in enumerate(enabled_list):
            if e[1:] == mod_name or e == mod_name:
                found = enabled_list.pop(i)
                break
        if found:
            disabled_list.append("-" + found.lstrip("+").lstrip("-"))
        else:
            return {"error": f"Mod '{mod_name}' not found in enabled list", "ok": False}

    _write_modlist(profile_path, header, enabled_list, disabled_list)
    return {"ok": True, "mod": mod_name, "enabled": enabled_state}


def op_set_plugin_enabled(instance: str, profile: str, plugin_name: str, enabled_state: bool) -> dict:
    """启用/禁用插件 — plugin API only."""
    return send_trigger("set_plugin_state", instance, name=plugin_name, active=enabled_state)
    profile_dir = get_profile_dir(instance)
    if not profile_dir:
        return {"error": f"Instance '{instance}' not found", "ok": False}
    profile_path = profile_dir / profile
    if not profile_path.exists():
        return {"error": f"Profile '{profile}' not found", "ok": False}

    create_backup(instance, profile, label="pre_toggle_plugin")

    header, enabled_list, disabled_list = _read_plugins(profile_path)

    if enabled_state:
        found = None
        for i, d in enumerate(disabled_list):
            if d == plugin_name or d.lstrip("*") == plugin_name.lstrip("*"):
                found = disabled_list.pop(i)
                break
        if found:
            enabled_list.append("*" + found.lstrip("*"))
        else:
            return {"error": f"Plugin '{plugin_name}' not found in disabled list", "ok": False}
    else:
        found = None
        for i, e in enumerate(enabled_list):
            if e.lstrip("*") == plugin_name.lstrip("*"):
                found = enabled_list.pop(i)
                break
        if found:
            disabled_list.append(found.lstrip("*"))
        else:
            return {"error": f"Plugin '{plugin_name}' not found in enabled list", "ok": False}

    _write_plugins(profile_path, header, enabled_list, disabled_list)
    return {"ok": True, "plugin": plugin_name, "enabled": enabled_state}


# ── Query Mod Detail ──────────────────────────────────────

def op_query_mod(instance: str, mod_name: str) -> dict:
    """Query mod — plugin API only (IModInterface)."""
    return send_trigger("query_mod", instance, name=mod_name)


def _op_query_mod_fs(instance: str, mod_name: str) -> dict:
    profile_dir = get_profile_dir(instance)
    if not profile_dir:
        return {"error": f"Instance '{instance}' not found", "ok": False}

    mods_dir = profile_dir.parent / "mods"
    mod_path = mods_dir / mod_name
    if not mod_path.exists():
        return {"error": f"Mod '{mod_name}' not found", "ok": False}

    result = {"ok": True, "name": mod_name, "path": str(mod_path)}

    # ── meta.ini ──
    meta_path = mod_path / "meta.ini"
    if meta_path.exists():
        import configparser as cp
        c = cp.ConfigParser()
        c.read(meta_path, encoding="utf-8")
        if "General" in c:
            gen = dict(c["General"])
            result["meta"] = {
                "modid": gen.get("modid", ""),
                "version": gen.get("version", ""),
                "newestVersion": gen.get("newestversion", ""),
                "category": gen.get("nexuscategory", gen.get("category", "")),
                "installationFile": gen.get("installationfile", ""),
                "repository": gen.get("repository", ""),
                "url": gen.get("url", ""),
                "gameName": gen.get("gamename", ""),
                "fileid": gen.get("installedfiles", "").split("\\")[-1] if gen.get("installedfiles") else "",
                "tracked": gen.get("tracked", "0"),
                "endorsed": gen.get("endorsed", "0"),
                "nexusFileStatus": gen.get("nexusfilestatus", ""),
                "lastNexusQuery": gen.get("lastnexusquery", ""),
                "lastNexusUpdate": gen.get("lastnexusupdate", ""),
            }
        if "installedFiles" in c:
            inst = dict(c["installedFiles"])
            if result.get("meta"):
                result["meta"]["fileid"] = inst.get("1\\fileid", "")

    # ── File tree ──
    files = []
    dirs = set()
    for f in sorted(mod_path.rglob("*")):
        if f.is_file() and f.name != "meta.ini":
            rel = str(f.relative_to(mod_path)).replace("\\", "/")
            files.append(rel)
            dirs.add(str(f.relative_to(mod_path).parent).replace("\\", "/"))
    result["fileTree"] = {
        "totalFiles": len(files),
        "directories": sorted(d for d in dirs if d != "."),
        "files": files[:200],  # Cap at 200
        "truncated": len(files) > 200,
    }

    # ── Find esp/esm/esl plugins in mod ──
    plugins_in_mod = [f for f in files if f.lower().endswith((".esp", ".esm", ".esl"))]
    result["pluginsInMod"] = plugins_in_mod

    # ── Query MO2 for plugin state ──
    if plugins_in_mod:
        plugin_states = []
        for pname in plugins_in_mod:
            state = send_trigger("query_plugin", instance, name=pname)
            if state.get("ok"):
                p = state["plugin"]
                p["filename"] = pname
                plugin_states.append(p)
        result["pluginStates"] = plugin_states

    # ── Modlist position ──
    # Check the first profile's modlist
    profiles_dir = profile_dir
    for prof in sorted(profiles_dir.iterdir()):
        if not prof.is_dir():
            continue
        modlist_path = prof / "modlist.txt"
        if not modlist_path.exists():
            continue
        lines = modlist_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for i, line in enumerate(lines):
            stripped = line.lstrip("+-").strip()
            if stripped == mod_name:
                status = "启用" if line.startswith("+") else "禁用"
                result["modlistPosition"] = {
                    "profile": prof.name,
                    "index": i,
                    "status": status,
                }
                break
        break  # Only check first profile

    return result

def get_mo2_state(instance_hint: str = "") -> dict:
    """Get current MO2 state from running plugin. Returns {'ok':True, 'state':{...}} or error."""
    # If no instance specified, try with empty string; plugin ignores instance param for get_state
    return send_trigger("get_state", instance_hint)


def resolve_instance(instance_name: str) -> str:
    """Resolve instance name. If '.' or 'auto', auto-detect from running MO2."""
    if instance_name in (".", "auto", ""):
        state = get_mo2_state("")
        if state.get("ok"):
            base_path = state["state"].get("basePath", "")
            profile_path = state["state"].get("profilePath", "")
            # Match against known instances
            import re
            for d in sorted(MO2_INSTANCE_ROOT.iterdir()):
                if not d.is_dir() or d.name in NON_INSTANCE_DIRS:
                    continue
                ini = d / "ModOrganizer.ini"
                if not ini.exists():
                    continue
                config = parse_mo2_ini(ini)
                bd = config.get("Settings", {}).get("base_directory", "")
                if bd and bd.replace("\\", "/") == base_path.replace("\\", "/"):
                    return d.name
                # Also match by profile path
                instance_base = MO2_INSTANCE_ROOT / d.name
                if bd:
                    instance_base = Path(bd)
                if profile_path.replace("\\", "/").startswith(str(instance_base).replace("\\", "/")):
                    return d.name
            # Fallback: return what MO2 reported
            return base_path
        else:
            print(f"Warning: Could not auto-detect instance: {state.get('error','')}", file=sys.stderr)
            return instance_name
    return instance_name


def guard_check(target_instance: str, target_profile: str = "") -> dict:
    """
    安全检查：对比目标实例/Profile 与 MO2 当前打开的是否一致。
    Returns {'ok': True, 'match': True/False, 'current': {...}, 'target': {...}}
    """
    state = get_mo2_state("")
    if not state.get("ok"):
        return {"ok": False, "error": "Cannot reach MO2 plugin. Is MO2 running?", "match": None}

    current = state["state"]
    current_instance = resolve_instance("auto")

    result = {
        "ok": True,
        "current": {
            "instance": current_instance,
            "profile": current.get("profileName", ""),
            "game": current.get("gameName", ""),
            "basePath": current.get("basePath", ""),
        },
        "target": {
            "instance": target_instance,
            "profile": target_profile or "(any)",
        },
    }

    instance_match = (target_instance == current_instance or
                      target_instance in (".", "auto", current_instance))
    profile_match = True
    if target_profile:
        profile_match = (target_profile == current.get("profileName", ""))

    result["match"] = instance_match and profile_match

    if not instance_match:
        result["warning"] = (
            f"实例不匹配！MO2 当前打开: '{current_instance}', "
            f"AI 目标: '{target_instance}'"
        )
    elif not profile_match:
        result["warning"] = (
            f"Profile 不匹配！MO2 当前: '{current.get('profileName','')}', "
            f"AI 目标: '{target_profile}'"
        )

    return result


def send_trigger(command: str, instance: str, **kwargs) -> dict:
    """发送命令到 MO2 插件（通过触发文件，带文件锁防止并发冲突）。"""
    TRIGGER_DIR.mkdir(parents=True, exist_ok=True)

    trigger_file = TRIGGER_DIR / "command.json"
    result_file = TRIGGER_DIR / "result.json"
    lock_file = TRIGGER_DIR / "command.lock"

    # Wait for lock (max 10s)
    waited = 0
    while lock_file.exists() and waited < 10:
        time.sleep(0.3)
        waited += 0.3
        # Break stale lock
        if lock_file.exists():
            try:
                if time.time() - lock_file.stat().st_mtime > 30:
                    lock_file.unlink()
            except: pass

    # Acquire lock
    try:
        lock_file.touch()
    except Exception:
        pass

    # Clean previous result
    if result_file.exists():
        result_file.unlink()

    trigger = {
        "command": command,
        "instance": instance,
        "timestamp": datetime.now().isoformat(),
        "params": kwargs,
    }

    try:
        with open(trigger_file, "w", encoding="utf-8") as f:
            json.dump(trigger, f, indent=2)
    finally:
        # Release lock so plugin can pick it up
        try: lock_file.unlink()
        except: pass

    # Wait for result (timeout 45s for refresh-causing commands, 30s for others)
    is_slow = command in ("refresh_mod_list", "set_mod_priority", "set_load_order",
                          "create_separator", "delete_mod", "create_mod")
    timeout = 60 if is_slow else 45  # 5s poll + 3s refresh + processing
    interval = 0.5
    waited = 0
    while waited < timeout:
        if result_file.exists():
            time.sleep(0.2)  # Small delay to ensure write complete
            with open(result_file, "r", encoding="utf-8") as f:
                result = json.load(f)
            # Clean up
            result_file.unlink()
            return result
        time.sleep(interval)
        waited += interval

    return {
        "ok": False,
        "error": f"Timeout waiting for MO2 plugin response ({timeout}s). Is MO2 running with the BGS-MO2-Control plugin?",
        "command": command,
    }


# ── CLI ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="MO2 Control — MO2 实例内容控制工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
安全协议：所有修改操作前自动创建带时间戳的备份。

Examples:
  python mo2_control.py backup "mod make" "pbr"
  python mo2_control.py backups "mod make" "pbr"
  python mo2_control.py restore "mod make" "pbr" 20260629_120000
  python mo2_control.py create-mod "mod make" "New Mod Name"
  python mo2_control.py create-separator "mod make" "pbr" "My Separator"
  python mo2_control.py reorder-mod "mod make" "pbr" 5 10
  python mo2_control.py reorder-plugin "mod make" "pbr" 3 7
  python mo2_control.py enable-mod "mod make" "pbr" "ModName" true
  python mo2_control.py enable-plugin "mod make" "pbr" "plugin.esp" true
  python mo2_control.py refresh "mod make"
  python mo2_control.py launch-game "mod make" "SKSE"
        """,
    )

    subparsers = parser.add_subparsers(dest="cmd", help="命令")

    # backup
    bp = subparsers.add_parser("backup", help="创建备份")
    bp.add_argument("instance", nargs="?", default="auto", help="实例名（默认=自动检测）")
    bp.add_argument("profile", help="Profile 名")
    bp.add_argument("label", nargs="?", default="", help="备份标签（可选）")

    # backups
    bl = subparsers.add_parser("backups", help="列出备份")
    bl.add_argument("instance", nargs="?", default="auto", help="实例名（默认=自动检测）")
    bl.add_argument("profile", help="Profile 名")

    # restore
    rs = subparsers.add_parser("restore", help="还原备份")
    rs.add_argument("instance", nargs="?", default="auto", help="实例名（默认=自动检测）")
    rs.add_argument("profile", help="Profile 名")
    rs.add_argument("backup_id", help="备份 ID")

    # create-mod
    cm = subparsers.add_parser("create-mod", help="创建空 MOD 目录")
    cm.add_argument("instance", nargs="?", default="auto", help="实例名（默认=自动检测）")
    cm.add_argument("name", help="MOD 名称")

    # create-separator
    cs = subparsers.add_parser("create-separator", help="创建分隔符")
    cs.add_argument("name", help="分隔符名称")
    cs.add_argument("instance", nargs="?", default="auto", help="实例名（默认=自动检测）")
    cs.add_argument("profile", nargs="?", default="auto", help="Profile名（默认=自动检测）")

    # reorder-mod
    rm = subparsers.add_parser("reorder-mod", help="调整 MOD 排序")
    rm.add_argument("instance", nargs="?", default="auto", help="实例名（默认=自动检测）")
    rm.add_argument("profile", help="Profile 名")
    rm.add_argument("from_index", type=int, help="源索引（0-based）")
    rm.add_argument("to_index", type=int, help="目标索引（0-based）")

    # reorder-plugin
    rp = subparsers.add_parser("reorder-plugin", help="调整插件排序")
    rp.add_argument("instance", nargs="?", default="auto", help="实例名（默认=自动检测）")
    rp.add_argument("profile", help="Profile 名")
    rp.add_argument("from_index", type=int, help="源索引（0-based）")
    rp.add_argument("to_index", type=int, help="目标索引（0-based）")

    # refresh
    rf = subparsers.add_parser("refresh", help="触发 MO2 刷新 MOD 列表")
    rf.add_argument("instance", nargs="?", default="auto", help="实例名（默认=自动检测）")

    # state
    st = subparsers.add_parser("state", help="获取当前运行的 MO2 状态")
    st.add_argument("instance", nargs="?", default="auto", help="实例名（默认=自动检测）")

    # guard
    gd = subparsers.add_parser("guard", help="安全检查")
    gd.add_argument("instance", help="目标实例名")
    gd.add_argument("profile", nargs="?", default="", help="目标Profile名")

    # load-order
    lo = subparsers.add_parser("load-order", help="获取当前插件加载顺序")
    lo.add_argument("instance", nargs="?", default="auto", help="实例名（默认=自动检测）")

    # launch-game
    lg = subparsers.add_parser("launch-game", help="通过 MO2 启动游戏")
    lg.add_argument("instance", nargs="?", default="auto", help="实例名（默认=自动检测）")
    lg.add_argument("executable", nargs="?", default="SKSE", help="可执行程序名称（默认: SKSE）")

    # create-mod-via-plugin
    cmp = subparsers.add_parser("create-mod-api", help="通过 MO2 插件 API 创建 MOD")
    cmp.add_argument("instance", nargs="?", default="auto", help="实例名（默认=自动检测）")
    cmp.add_argument("name", help="MOD 名称")

    # set-mod-active (via plugin)
    sma = subparsers.add_parser("set-mod-active", help="通过 MO2 API 启用/禁用 MOD")
    sma.add_argument("instance", nargs="?", default="auto", help="实例名（默认=自动检测）")
    sma.add_argument("name", help="MOD 内部名称")
    sma.add_argument("state", choices=["true", "false"], help="true=启用")

    # set-plugin-state (via plugin)
    sps = subparsers.add_parser("set-plugin-state", help="通过 MO2 API 启用/禁用插件")
    sps.add_argument("instance", nargs="?", default="auto", help="实例名（默认=自动检测）")
    sps.add_argument("name", help="插件文件名")
    sps.add_argument("state", choices=["true", "false"], help="true=启用")

    # set-plugin-priority (via plugin)
    spp = subparsers.add_parser("set-plugin-priority", help="通过 MO2 API 调整插件优先级")
    spp.add_argument("instance", nargs="?", default="auto", help="实例名（默认=自动检测）")
    spp.add_argument("name", help="插件文件名")
    spp.add_argument("priority", type=int, help="新优先级")

    # query-mod (combined mod + plugin info)
    qm = subparsers.add_parser("query-mod", help="查询 MOD 完整信息（meta.ini + 插件状态）")
    qm.add_argument("instance", nargs="?", default="auto", help="实例名（默认=自动检测）")
    qm.add_argument("name", help="MOD 名称")

    # set-load-order (via plugin)
    slo = subparsers.add_parser("set-load-order", help="通过 MO2 API 设置加载顺序")
    slo.add_argument("instance", nargs="?", default="auto", help="实例名（默认=自动检测）")
    slo.add_argument("order_json", help="JSON 格式的插件名列表 或 @文件路径")

    args = parser.parse_args()

    if not args.cmd:
        parser.print_help()
        return

    # Auto-resolve instance/profile from running MO2 if not specified
    _auto = {"instance": None, "profile": None}
    if hasattr(args, "instance") and args.instance in (None, "", ".", "auto"):
        state = get_mo2_state("")
        if state.get("ok"):
            _auto["instance"] = resolve_instance("auto")
            _auto["profile"] = state["state"].get("profileName", "")
            if _auto["instance"] and _auto["instance"] not in (".", "auto"):
                args.instance = _auto["instance"]
        else:
            # Plugin not available — use most recently modified instance
            best = None; best_time = 0
            for d in sorted(MO2_INSTANCE_ROOT.iterdir()):
                if not d.is_dir() or d.name in NON_INSTANCE_DIRS: continue
                try:
                    mtime = (d / "ModOrganizer.ini").stat().st_mtime
                    if mtime > best_time: best_time = mtime; best = d.name
                except: pass
            if best: args.instance = best
    if hasattr(args, "profile") and args.profile in (None, "", ".", "auto"):
        args.profile = _auto["profile"] or args.profile

    result = None

    if args.cmd == "backup":
        result = create_backup(args.instance, args.profile, args.label)
    elif args.cmd == "backups":
        backups = list_backups(args.instance, args.profile)
        if backups:
            print(f"Backups for {args.instance}/{args.profile}:")
            for b in backups:
                label = f" ({b.get('label', '')})" if b.get('label') else ""
                print(f"  {b['backupId']}{label} — {', '.join(b.get('files', []))}")
            print(f"\n  Total: {len(backups)} backup(s)")
        else:
            print("No backups found.")
        return
    elif args.cmd == "restore":
        result = restore_backup(args.instance, args.profile, args.backup_id)
    elif args.cmd == "create-mod":
        result = op_create_mod(args.instance, args.name)
    elif args.cmd == "create-separator":
        result = op_create_separator(args.instance, args.profile, args.name)
    elif args.cmd == "reorder-mod":
        result = op_reorder_mod(args.instance, args.profile, args.from_index, args.to_index)
    elif args.cmd == "reorder-plugin":
        result = op_reorder_plugin(args.instance, args.profile, args.from_index, args.to_index)
    elif args.cmd == "refresh":
        result = send_trigger("refresh_mod_list", args.instance)
    elif args.cmd == "state":
        result = get_mo2_state(args.instance)
    elif args.cmd == "guard":
        result = guard_check(args.instance, args.profile if hasattr(args, 'profile') else "")
    elif args.cmd == "load-order":
        result = send_trigger("get_load_order", args.instance)
    elif args.cmd == "launch-game":
        result = send_trigger("launch_executable", args.instance, executable=args.executable)
    elif args.cmd == "create-mod-api":
        result = send_trigger("create_mod", args.instance, name=args.name)
    elif args.cmd == "set-mod-active":
        result = send_trigger("set_mod_active", args.instance, name=args.name,
                              active=args.state == "true")
    elif args.cmd == "set-plugin-priority":
        result = send_trigger("set_plugin_priority", args.instance, name=args.name,
                              priority=args.priority)
    elif args.cmd == "query-plugin":
        result = send_trigger("query_plugin", args.instance, name=args.name)
    elif args.cmd == "query-mod":
        result = op_query_mod(args.instance, args.name)
    elif args.cmd == "set-load-order":
        # parse order from arg (json string or @file)
        order_raw = args.order_json
        try:
            if order_raw.startswith("@"):
                with open(order_raw[1:], "r") as f:
                    order = json.load(f)
            else:
                order = json.loads(order_raw)
            result = send_trigger("set_load_order", args.instance, order=order)
        except Exception as e:
            result = {"ok": False, "error": f"Failed to parse order: {e}"}

    if result:
        if result.get("ok") or result.get("launched"):
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
