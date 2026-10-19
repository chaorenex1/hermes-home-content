#!/usr/bin/env python
"""Probe the REAL host facade contract for the plugin-Agent context seam.

Why: the plugin side keys context runs by the plugin id it reads from the host
facade -- `getattr(agent_facade, "_plugin_id", "lancedb")` -- while the host
envelope carries `identity.plugin_id` ("memory/lancedb" via the memory loader).
Repo fixtures fake `_plugin_id`, so the suite can stay green while every
plugin-agent kb_* call refuses with "plugin Agent context belongs to another
plugin". This probe checks the real classes.

Usage (host venv python, any cwd):
    python host_facade_probe.py <hermes-agent tree> [<HERMES_HOME>]

Exit code 0 = facade exposes _plugin_id == identity.plugin_id; 1 = mismatch.
"""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    tree = Path(sys.argv[1]).resolve()
    home = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else tree.parent
    sys.path.insert(0, str(tree))
    from hermes_cli.plugin_runtime import PluginIdentity, PluginRuntimeServices

    ident = PluginIdentity(
        plugin_id="memory/lancedb",
        source="exclusive",
        manifest_path=None,
        config_namespace="lancedb",
        hermes_home=home,
        agent_routes=("extraction", "dialectical", "retrieval"),
        skill_namespace="lancedb",
    )
    facade = PluginRuntimeServices(ident).agent
    present = hasattr(facade, "_plugin_id")
    plugin_reads = getattr(facade, "_plugin_id", "lancedb")
    print("facade class:", type(facade).__name__)
    print("facade._plugin_id present:", present)
    print("plugin-side fallback reads:", plugin_reads)
    print("host envelope id (identity.plugin_id):", ident.plugin_id)
    ok = present and plugin_reads == ident.plugin_id
    print(
        "VERDICT:",
        "OK"
        if ok
        else (
            "MISMATCH - plugin-agent kb_* calls will refuse with "
            "'plugin Agent context belongs to another plugin'"
        ),
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
