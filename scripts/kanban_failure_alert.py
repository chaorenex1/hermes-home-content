#!/usr/bin/env python3
"""Kanban health/failure monitor.

Failure notifications are written as events on the Swarm root Blackboard.
The Gateway notifier then routes them through the creator's subscription;
this script never chooses a fixed chat or platform.
"""
import json
import sqlite3
import subprocess
import time
from pathlib import Path

ROOT = Path.home() / "AppData" / "Local" / "hermes"
DB = ROOT / "kanban.db"
STATE = ROOT / "kanban" / "alert-state.json"
KINDS = {"crashed", "timed_out", "gave_up", "spawn_failed", "protocol_violation"}
PREFIX = "[swarm:blackboard] "


def parse(value):
    try:
        return json.loads(value) if value else None
    except Exception:
        return None


def emit(conn, task_id, kind, data):
    marker = json.dumps(data, ensure_ascii=False, sort_keys=True)
    if conn.execute(
        "SELECT 1 FROM task_events WHERE task_id=? AND kind=? AND payload=? LIMIT 1",
        (task_id, kind, marker),
    ).fetchone():
        return False
    conn.execute(
        "INSERT INTO task_events(task_id,run_id,kind,payload,created_at) VALUES(?,?,?,?,?)",
        (task_id, None, kind, marker, int(time.time())),
    )
    return True


def swarm_roots(conn):
    mapping = {}
    roots = conn.execute(
        "SELECT id FROM tasks WHERE title LIKE 'Swarm:%' AND status != 'archived'"
    ).fetchall()
    for root in roots:
        comments = conn.execute(
            "SELECT body FROM task_comments WHERE task_id=? ORDER BY id", (root[0],)
        ).fetchall()
        for comment in comments:
            body = comment[0] or ""
            if not body.startswith(PREFIX):
                continue
            obj = parse(body[len(PREFIX):])
            topology = obj.get("value") if isinstance(obj, dict) and obj.get("key") == "topology" else None
            if not isinstance(topology, dict):
                continue
            child_ids = [str(x) for x in topology.get("worker_ids", [])]
            child_ids += [str(topology.get("verifier_id", "")), str(topology.get("synthesizer_id", ""))]
            for child_id in filter(None, child_ids):
                mapping[child_id] = str(root[0])
    return mapping


def main():
    if not DB.exists():
        return
    STATE.parent.mkdir(parents=True, exist_ok=True)
    try:
        old = json.loads(STATE.read_text(encoding="utf8")) if STATE.exists() else {}
    except Exception:
        old = {}

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    now = int(time.time())
    alerts = []
    root_for_task = swarm_roots(conn)
    rows = conn.execute(
        "SELECT e.id,e.task_id,e.kind,e.payload,t.title,t.assignee,t.status,"
        "t.consecutive_failures,t.max_retries FROM task_events e JOIN tasks t ON t.id=e.task_id "
        "WHERE e.kind IN ('crashed','timed_out','gave_up','spawn_failed','protocol_violation') "
        "ORDER BY e.id DESC LIMIT 100"
    ).fetchall()

    for row in rows:
        event_id = str(row["id"])
        if event_id in old:
            continue
        alert = dict(row)
        alerts.append(alert)
        old[event_id] = now
        root_id = root_for_task.get(str(row["task_id"]))
        if root_id:
            root_kind = "swarm_blocked" if row["kind"] in {"gave_up", "protocol_violation"} else "swarm_gate_failed"
            emit(conn, root_id, root_kind, {
                "source": "kanban-health",
                "failure_event_id": row["id"],
                "task_id": row["task_id"],
                "task_title": row["title"],
                "failure_kind": row["kind"],
                "payload": parse(row["payload"]),
            })

        # Retry only transient worker loss and never unblock human-gated tasks.
        if (
            row["kind"] in {"crashed", "timed_out"}
            and row["status"] in {"ready", "running"}
            and int(row["consecutive_failures"] or 0) < int(row["max_retries"] or 2)
        ):
            try:
                subprocess.run(
                    ["hermes", "kanban", "dispatch", "--json"],
                    capture_output=True, text=True, timeout=40,
                )
            except Exception:
                pass

    old = dict(sorted(old.items(), key=lambda item: int(item[0]), reverse=True)[:500])
    STATE.write_text(json.dumps(old), encoding="utf8")
    counts = {row["status"]: row["n"] for row in conn.execute("SELECT status,COUNT(*) n FROM tasks GROUP BY status")}
    stale = [dict(row) for row in conn.execute(
        "SELECT id,assignee,claim_expires FROM tasks WHERE status='running' "
        "AND claim_expires IS NOT NULL AND claim_expires < ?", (now,)
    )]
    blocked = [dict(row) for row in conn.execute(
        "SELECT id,title,block_kind FROM tasks WHERE status='blocked' ORDER BY created_at DESC LIMIT 10"
    )]
    conn.commit()
    conn.close()
    print(json.dumps({
        "type": "kanban_alert" if alerts else "kanban_health",
        "healthy": not stale and not alerts,
        "alerts": alerts,
        "counts": counts,
        "stale_running": stale,
        "blocked": blocked,
        "routing": "swarm-root-events-via-gateway",
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
