"""Host-seam probe: drive the real host boundary-outbox functions against the repo plugin.

Reproduces the deferred-delivery path that used to wedge the outbox
(ValueError: session_id does not match the active Provider session) and asserts the repaired
contract:

  delivery 1  deferred shutdown boundary of an old session
              -> no exception, counters stopped, one session_end dialectic trigger
  delivery 2  deferred new_session boundary (same event drives end + switch)
              -> no exception, live binding untouched, boundary event recorded
  replay      the same events again (host retry semantics) -> accepted, still no rebind

Read-only with respect to $HERMES_HOME: everything runs inside a temp hermes home.

Usage:
  python scripts/boundary_outbox_probe.py [--repo <repo>] [--host <hermes-agent tree>]

Exit code 0 = all checks passed. System Python is fine (no pytest needed).
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

DEFAULT_REPO = r"<USER_HOME>\projects\hermes-lancedb-memory"
DEFAULT_HOST = r"<HERMES_HOME>\hermes-agent"

LIVE = "live-session"
OLD = "20260817_152037_2b030c"
OLD_CHILD = "20260817_160018_3e2ddd"


class _FakeSessionDB:
    def get_memory_boundary_messages(self, session_id, message_high_watermark=0):
        return [
            {"role": "user", "content": f"history of {session_id}"},
            {"role": "assistant", "content": "recorded"},
        ]


class _FakeManager:
    def __init__(self, providers):
        self.providers = providers


def _event(event_id: str, *, parent: str, child: str, reason: str) -> dict:
    return {
        "event_id": event_id,
        "parent_session_id": parent,
        "child_session_id": child,
        "reason": reason,
        "in_place": False,
        "message_high_watermark": 2,
        "payload": {
            "transition_reason": reason,
            "transition_old_session_id": parent,
            "transition_new_session_id": child,
            "session_mode": "session",
            "session_mode_source": "probe",
            "session_mode_revision": 1,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--host", default=DEFAULT_HOST)
    args = parser.parse_args()

    sys.path.insert(0, args.repo)
    sys.path.insert(0, args.host)

    from agent.memory_boundary_outbox import deliver_memory_boundary_event
    from plugin.lancedb import LanceDBMemoryProvider
    from plugin.lancedb.config import save_profile_config

    failures: list[str] = []
    home = tempfile.mkdtemp(prefix="boundary_probe_")
    provider = None
    try:
        # cadence=2 so a single turn is NOT on a trigger multiple and the boundary trigger
        # must fire (cadence=1 would dedupe it by design).
        save_profile_config(
            Path(home),
            {
                "context": {"cadence_turns": 2},
                "dialectical": {"cadence_turns": 2, "depth": 3},
            },
        )
        provider = LanceDBMemoryProvider()
        provider.initialize(
            LIVE,
            hermes_home=home,
            agent_context="primary",
            agent_identity="default",
            platform="probe",
        )
        assert provider._layer_state is not None
        provider._layer_state.start_session(
            profile_name="default",
            session_id=OLD,
            scope_key=f"session:{OLD}",
            mode="session",
        )
        provider._layer_state.advance_turns(profile_name="default", session_id=OLD)
        manager = _FakeManager([provider])

        def deliver(event: dict) -> None:
            deliver_memory_boundary_event(
                session_db=_FakeSessionDB(), memory_manager=manager, event=event
            )

        # 1) deferred shutdown boundary of an already-ended session
        shutdown = _event("probe-shutdown-1", parent=OLD, child="", reason="shutdown")
        try:
            deliver(shutdown)
            print("delivery 1 (deferred shutdown): OK")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"delivery 1 raised {type(exc).__name__}: {exc}")

        counters = provider._layer_state.get("default", OLD)
        triggers = provider._layer_state.list_triggers(
            profile_name="default", session_id=OLD, kind="session_end"
        )
        print(
            "counters:",
            None if counters is None else (counters.counting, counters.dialectic_turns),
        )
        print("session_end triggers:", len(triggers))
        if counters is None or counters.counting is not False:
            failures.append("old session counters were not stopped")
        if len(triggers) != 1 or triggers[0].scope_key != f"session:{OLD}":
            failures.append("missing/incorrect dialectic trigger for the old session")

        # 2) deferred new_session boundary: end + switch must not rebind the live session
        switch = _event("probe-switch-2", parent=OLD, child=OLD_CHILD, reason="new_session")
        try:
            deliver(switch)
            print("delivery 2 (deferred new_session): OK")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"delivery 2 raised {type(exc).__name__}: {exc}")
        print("bound session after deferred switch:", provider._session_id)
        print("recorded boundary:", provider._processed_boundary_event("probe-switch-2"))
        if provider._session_id != LIVE:
            failures.append("deferred switch rebound the live session")
        if provider._processed_boundary_event("probe-switch-2") != (OLD, OLD_CHILD):
            failures.append("deferred switch boundary was not recorded")

        # 3) replay (host retry semantics) must be accepted, never raise, never rebind
        for event in (shutdown, switch):
            try:
                deliver(event)
                print("replay", event["event_id"], ": OK")
            except Exception as exc:  # noqa: BLE001
                failures.append(
                    f"replay of {event['event_id']} raised {type(exc).__name__}: {exc}"
                )
    finally:
        if provider is not None:
            try:
                provider.shutdown()
            except Exception:  # noqa: BLE001
                pass
        # Windows: the provider keeps memory.db handles open, so TemporaryDirectory
        # cleanup would fail with WinError 32 — remove best-effort only.
        shutil.rmtree(home, ignore_errors=True)

    print("FAILURES:", failures if failures else "none")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
