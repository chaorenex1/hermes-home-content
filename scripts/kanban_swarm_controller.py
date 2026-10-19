#!/usr/bin/env python3
"""Deterministic Kanban Swarm acceptance/progress controller.

Runs from cron. It never calls an LLM: it validates the durable graph, emits
swarm lifecycle events on the root card, and blocks downstream cards when a
hard gate is invalid. Existing Gateway Kanban subscriptions deliver events to
the creator chat.
"""
import json, sqlite3, time
from pathlib import Path

ROOT = Path.home() / "AppData" / "Local" / "hermes"
DB = ROOT / "kanban.db"
PREFIX = "[swarm:blackboard] "


def payload(v):
    try: return json.loads(v) if v else None
    except Exception: return None


def emit(conn, task_id, kind, data):
    marker = json.dumps(data, ensure_ascii=False, sort_keys=True)
    exists = conn.execute(
        "SELECT 1 FROM task_events WHERE task_id=? AND kind=? AND payload=? LIMIT 1",
        (task_id, kind, marker),
    ).fetchone()
    if not exists:
        conn.execute(
            "INSERT INTO task_events(task_id,run_id,kind,payload,created_at) VALUES(?,?,?,?,?)",
            (task_id, None, kind, marker, int(time.time())),
        )
        return True
    return False


def comment(conn, task_id, text):
    conn.execute(
        "INSERT INTO task_comments(task_id,author,body,created_at) VALUES(?,?,?,?)",
        (task_id, "swarm-controller", text, int(time.time())),
    )


def block(conn, task_id, reason, kind="capability"):
    row = conn.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()
    if not row or row[0] in ("done", "archived", "blocked"): return False
    conn.execute("UPDATE tasks SET status='blocked', block_kind=?, last_failure_error=? WHERE id=?", (kind, reason, task_id))
    emit(conn, task_id, "blocked", {"reason": reason, "kind": kind, "source": "swarm-controller"})
    comment(conn, task_id, "[swarm-controller] " + reason)
    return True


def main():
    if not DB.exists(): return
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("ALTER TABLE tasks ADD COLUMN swarm_state TEXT") if "swarm_state" not in {r[1] for r in conn.execute("PRAGMA table_info(tasks)")} else None
    roots = conn.execute("SELECT * FROM tasks WHERE title LIKE 'Swarm:%' AND status != 'archived'").fetchall()
    changed = []
    for root in roots:
        conn.execute("UPDATE tasks SET swarm_state=COALESCE(swarm_state, 'running') WHERE id=?", (root["id"],))
        comments = conn.execute("SELECT body FROM task_comments WHERE task_id=? ORDER BY id", (root["id"],)).fetchall()
        topo = None
        for c in comments:
            body = c["body"] or ""
            if body.startswith(PREFIX):
                obj = payload(body[len(PREFIX):])
                if obj and obj.get("key") == "topology": topo = obj.get("value")
        if not isinstance(topo, dict): continue
        worker_ids = [str(x) for x in topo.get("worker_ids", [])]
        verifier_id, synth_id = str(topo.get("verifier_id", "")), str(topo.get("synthesizer_id", ""))
        ids = worker_ids + [verifier_id, synth_id]
        rows = {r["id"]: r for r in conn.execute("SELECT * FROM tasks WHERE id IN (%s)" % ",".join("?"*len(ids)), ids)} if ids else {}
        if len(rows) != len(ids):
            emit(conn, root["id"], "swarm_gate_failed", {"reason":"topology references missing task", "source":"swarm-controller"})
            continue
        done_workers = [x for x in worker_ids if rows[x]["status"] == "done"]
        bad_workers = [x for x in worker_ids if rows[x]["status"] in ("blocked", "archived")]
        progress = {"root_id":root["id"], "workers_done":len(done_workers), "workers_total":len(worker_ids), "verifier":rows[verifier_id]["status"], "synthesizer":rows[synth_id]["status"]}
        if emit(conn, root["id"], "swarm_progress", progress): changed.append(root["id"])
        missing_handoffs = []
        for worker_id in done_workers:
            latest = conn.execute("SELECT summary, metadata, outcome FROM task_runs WHERE task_id=? ORDER BY id DESC LIMIT 1", (worker_id,)).fetchone()
            if not latest or latest["outcome"] != "completed" or not latest["summary"] or not isinstance(payload(latest["metadata"]), dict):
                missing_handoffs.append(worker_id)
        if bad_workers:
            reason = f"Swarm worker failure: {', '.join(bad_workers)}"
            if block(conn, root["id"], reason):
                conn.execute("UPDATE tasks SET swarm_state='blocked' WHERE id=?", (root["id"],))
                emit(conn, root["id"], "swarm_blocked", {"reason":reason, **progress})
            continue
        if missing_handoffs:
            reason = f"Worker handoff incomplete: {', '.join(missing_handoffs)}"
            if rows[verifier_id]["status"] in ("ready", "running"):
                block(conn, verifier_id, reason)
            emit(conn, root["id"], "swarm_gate_failed", {"reason":reason, "workers":missing_handoffs, **progress})
            continue
        if len(done_workers) == len(worker_ids):
            emit(conn, root["id"], "swarm_workers_ready_for_verification", progress)
        vrun = conn.execute("SELECT metadata,summary,outcome FROM task_runs WHERE task_id=? ORDER BY id DESC LIMIT 1", (verifier_id,)).fetchone()
        vmeta = payload(vrun["metadata"]) if vrun else {}
        gate = vmeta.get("gate") if isinstance(vmeta, dict) else None
        if rows[verifier_id]["status"] == "done" and gate != "pass":
            reason = "Verifier completed without metadata.gate=pass; synthesizer is not allowed to proceed."
            if rows[synth_id]["status"] in ("ready", "running"):
                block(conn, synth_id, reason)
            emit(conn, root["id"], "swarm_gate_failed", {"verifier_id":verifier_id, "reason":reason, **progress})
        if rows[synth_id]["status"] == "done":
            srun = conn.execute("SELECT summary,metadata,outcome FROM task_runs WHERE task_id=? ORDER BY id DESC LIMIT 1", (synth_id,)).fetchone()
            smeta = payload(srun["metadata"]) if srun else {}
            if not srun or srun["outcome"] != "completed" or not srun["summary"] or not isinstance(smeta, dict):
                reason = "Synthesizer completed without a valid summary and metadata."
                block(conn, synth_id, reason)
                emit(conn, root["id"], "swarm_gate_failed", {"synthesizer_id":synth_id, "reason":reason, **progress})
            elif gate == "pass" and len(done_workers) == len(worker_ids):
                conn.execute("UPDATE tasks SET swarm_state='completed' WHERE id=?", (root["id"],))
                emit(conn, root["id"], "swarm_completed", {
                    "root_id": root["id"],
                    "verifier_gate": "pass",
                    "synthesis_summary": srun["summary"],
                    **progress,
                })
    conn.commit(); conn.close()
    # Cron output is intentionally local-only. User-facing delivery is emitted
    # as root task_events and routed by the Gateway notifier subscription.
    if changed:
        print(json.dumps({"type": "swarm_progress", "roots": changed, "routing": "gateway-root-subscription"}, ensure_ascii=False))

if __name__ == "__main__": main()
