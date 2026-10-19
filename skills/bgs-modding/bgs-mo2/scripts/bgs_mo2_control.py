# BGS-MO2-Control — MO2 Control Plugin v1.3.2 (no startup I/O, refresh via QTimer)
import json, time
from pathlib import Path
import mobase
from PyQt6.QtCore import QCoreApplication, QTimer

_TRIGGER_DIR = Path.home() / "AppData" / "Local" / "Temp" / "mo2_control"
_POLL_SEC = 3  # poll interval (seconds)

class BGSMO2Control(mobase.IPluginTool):
    def __init__(self):
        super().__init__()
        self.__organizer = None
        self.__timer = None
        self.__processing = False
        self.__poll_count = 0
        self.__processed_count = 0
        self.__pending_refresh = False

    def init(self, organizer: mobase.IOrganizer) -> bool:
        self.__organizer = organizer
        _TRIGGER_DIR.mkdir(parents=True, exist_ok=True)
        self.__timer = QTimer()
        self.__timer.timeout.connect(self.__tick)
        self.__timer.start(_POLL_SEC * 1000)
        return True

    def name(self): return "BGS MO2 Control"
    # def localizedName(self): return "BGS MO2 Control"
    # def author(self): return "Hermes Agent (BGS-MO2)"
    # def description(self): return "AI agent control interface for Mod Organizer 2"
    # def version(self): return mobase.VersionInfo(1, 3, 0, mobase.ReleaseType.ALPHA)
    # def requirements(self): return []
    # def enabledByDefault(self): return True
    # def master(self): return "BGS MO2 Control"
    def settings(self): return []
    def displayName(self): return "BGS MO2 Control"
    def tooltip(self): return "AI agent control interface"
    def icon(self):
        from PyQt6.QtGui import QIcon
        return QIcon()
    def display(self):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self._parentWidget(), "BGS MO2 Control",
            f"v1.3.0, Processed: {self.__processed_count}, Poll: {_POLL_SEC}s")

    def _safe_refresh(self):
        """Deferred refresh via QTimer to avoid blocking MO2 UI."""
        if not self.__pending_refresh:
            self.__pending_refresh = True
            QTimer.singleShot(500, self.__do_refresh)

    def __do_refresh(self):
        self.__pending_refresh = False
        self.__organizer.refresh(True)

    # ── Tick: poll for new commands + process queue ──

    def __tick(self):
        self.__poll_count += 1
        if self.__processing:
            return
        tf = _TRIGGER_DIR / "command.json"
        lock = _TRIGGER_DIR / "command.lock"
        if not tf.exists():
            return
        # Acquire lock — skip if another instance holds it
        if lock.exists():
            try:
                age = time.time() - lock.stat().st_mtime
                if age > 30:  # stale lock > 30s
                    lock.unlink()
                else:
                    return
            except:
                return
        try:
            lock.touch()
            self.__processing = True
            cmd = json.loads(tf.read_text(encoding="utf-8"))
            tf.unlink()
            ts = cmd.get("timestamp", "")
            if ts != getattr(self, '_last_ts', ""):
                self._last_ts = ts
                result = self.__execute(cmd)
                (_TRIGGER_DIR / "result.json").write_text(json.dumps(result, indent=2))
                self.__processed_count += 1
        except Exception as e:
            try:
                (_TRIGGER_DIR / "result.json").write_text(
                    json.dumps({"ok": False, "error": str(e)}, indent=2))
            except: pass
        finally:
            self.__processing = False
            try: lock.unlink()
            except: pass

    # ── Command dispatch ──

    def __execute(self, cmd):
        command = cmd.get("command", "")
        params = cmd.get("params", {})
        instance = cmd.get("instance", "")
        try:
            if command == "get_state": return self.__cmd_get_state()
            elif command == "get_load_order": return self.__cmd_get_load_order()
            elif command == "refresh_mod_list":
                self._safe_refresh()
                return {"ok": True, "message": "Refresh done"}
            elif command == "launch_executable":
                h = self.__organizer.startApplication(params.get("executable", "SKSE"))
                return {"ok": True, "launched": bool(h), "handle": h}
            elif command == "create_separator":
                return self.__cmd_create_separator(params.get("name", ""))
            elif command == "create_mod":
                m = self.__organizer.createMod(params.get("name", ""))
                return {"ok": True, "created": params.get("name", "")} if m else {"ok": False}
            elif command == "set_mod_active":
                ok = self.__organizer.modList().setActive(params.get("name", ""), params.get("active", True))
                return {"ok": ok, "name": params.get("name", ""), "active": params.get("active", True)}
            elif command == "set_mod_priority":
                ok = self.__organizer.modList().setPriority(params.get("name", ""), params.get("priority", 0))
                self._safe_refresh()
                return {"ok": ok, "name": params.get("name", ""), "priority": params.get("priority", 0)}
            elif command == "delete_mod":
                return self.__cmd_delete_mod(params.get("name", ""))
            elif command == "query_plugin": return self.__cmd_query_plugin(params.get("name", ""))
            elif command == "query_mod": return self.__cmd_query_mod(params.get("name", ""))
            elif command == "set_plugin_state":
                pl = self.__organizer.pluginList()
                st = mobase.PluginState.ACTIVE if params.get("active", True) else mobase.PluginState.INACTIVE
                pl.setState(params.get("name", ""), st)
                return {"ok": True}
            elif command == "set_plugin_priority":
                ok = self.__organizer.pluginList().setPriority(params.get("name", ""), params.get("priority", 0))
                return {"ok": ok}
            elif command == "set_load_order":
                self.__organizer.pluginList().setLoadOrder(params.get("order", []))
                self._safe_refresh()
                return {"ok": True}
            else: return {"ok": False, "error": f"Unknown: {command}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Handlers ──

    def __cmd_get_state(self):
        o = self.__organizer; g = o.managedGame()
        return {"ok": True, "state": {
            "profileName": o.profileName(), "profilePath": o.profilePath(),
            "gameName": g.gameName() if g else "", "basePath": o.basePath(),
            "modsPath": o.modsPath(), "appVersion": str(o.appVersion()),
            "modCount": len(o.modList().allMods()),
            "pluginCount": len(o.pluginList().pluginNames()),
        }}

    def __cmd_get_load_order(self):
        pl = self.__organizer.pluginList()
        names = pl.pluginNames(); order = []
        for n in names:
            lo = pl.loadOrder(n)
            order.append({"name": n, "loadOrder": lo, "active": pl.state(n) == mobase.PluginState.ACTIVE})
        order.sort(key=lambda x: x["loadOrder"] if x["loadOrder"] >= 0 else 99999)
        return {"ok": True, "count": len(order), "plugins": order}

    def __cmd_create_separator(self, name):
        if not name: return {"ok": False, "error": "name required"}
        sep_name = name + "_separator"
        mod = self.__organizer.createMod(sep_name)
        if mod:
            self._safe_refresh()
            return {"ok": True, "name": name, "separator": sep_name}
        return {"ok": False, "error": f"Failed: {sep_name}"}

    def __cmd_delete_mod(self, name):
        if not name: return {"ok": False, "error": "name required"}
        mod = self.__organizer.modList().getMod(name)
        if not mod: return {"ok": False, "error": f"Not found: {name}"}
        removed = self.__organizer.modList().removeMod(mod)
        if removed: self._safe_refresh()
        return {"ok": removed, "deleted": name}

    def __cmd_query_plugin(self, name):
        if not name: return {"ok": False, "error": "name required"}
        pl = self.__organizer.pluginList()
        return {"ok": True, "plugin": {
            "name": name, "state": str(pl.state(name)), "priority": pl.priority(name),
            "loadOrder": pl.loadOrder(name), "origin": pl.origin(name),
            "masters": list(pl.masters(name)) if pl.masters(name) else [],
            "isMaster": pl.isMasterFlagged(name), "isLight": pl.isLightFlagged(name),
            "hasMasterExt": pl.hasMasterExtension(name), "hasLightExt": pl.hasLightExtension(name),
            "hasNoRecords": pl.hasNoRecords(name),
        }}

    def __cmd_query_mod(self, name):
        if not name: return {"ok": False, "error": "name required"}
        mod = self.__organizer.modList().getMod(name)
        if not mod: return {"ok": False, "error": f"Not found: {name}"}
        ft = mod.fileTree(); files = []; dirs = set()
        if ft:
            def walk(e, pfx=""):
                nm = e.name()
                if e.isDir():
                    for c in e: walk(c, f"{pfx}/{nm}" if pfx else nm)
                else:
                    fp = f"{pfx}/{nm}" if pfx else nm; files.append(fp)
                    if pfx: dirs.add(pfx)
            walk(ft)
        plugs = [f for f in files if f.lower().endswith((".esp",".esm",".esl"))]
        pl = self.__organizer.pluginList(); pstates = []
        for pn in plugs:
            try: pstates.append({"filename": pn, "state": str(pl.state(pn)),
                "priority": pl.priority(pn), "loadOrder": pl.loadOrder(pn),
                "origin": pl.origin(pn), "masters": list(pl.masters(pn)) if pl.masters(pn) else []})
            except: pass
        return {"ok": True, "mod": {
            "name": mod.name(), "modid": mod.nexusId(),
            "version": str(mod.version()), "newestVersion": str(mod.newestVersion()),
            "url": mod.url(), "repository": mod.repository(), "gameName": mod.gameName(),
            "installationFile": mod.installationFile(), "primaryCategory": mod.primaryCategory(),
            "comments": mod.comments(), "notes": mod.notes(),
            "endorsedState": str(mod.endorsedState()), "trackedState": str(mod.trackedState()),
            "converted": mod.converted(), "validated": mod.validated(),
            "isBackup": mod.isBackup(), "isSeparator": mod.isSeparator(),
            "isForeign": mod.isForeign(), "isOverwrite": mod.isOverwrite(),
            "fileTree": {"totalFiles": len(files), "directories": sorted(dirs), "files": files[:200]},
            "pluginStates": pstates,
        }}

    def tr(self, v): return QCoreApplication.translate("BGSMO2Control", v)

def createPlugin(): return BGSMO2Control()
