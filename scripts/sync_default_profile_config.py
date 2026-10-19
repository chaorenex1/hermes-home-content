#!/usr/bin/env python3
"""Synchronize default config.yaml to every named Hermes profile safely.

The default profile is authoritative. Target credentials (.env), cron job
records, SOUL.md, sessions, skills, plugins, and all other profile content are
never copied. Target configs receive the default configuration with every
configured messaging platform explicitly disabled. Existing target cron jobs
are paused, never deleted.
"""
from __future__ import annotations

import argparse
import copy
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

HOME = Path(__file__).resolve().parent.parent
PROFILE_ROOT = HOME / "profiles"
SOURCE_CONFIG = HOME / "config.yaml"
BACKUP_NAME = ".profile-config-sync-backups"
ACTIVE_JOB = re.compile(r"^\s*([0-9a-f]+)\s+\[active\]\s*$", re.IGNORECASE)


def canonical_yaml(config: dict[str, Any]) -> str:
    return yaml.safe_dump(
        config,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=1000,
    )


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except OSError as exc:
        raise RuntimeError(f"cannot read {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise RuntimeError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{path} must contain a YAML mapping")
    return value


def desired_target_config(source: dict[str, Any]) -> dict[str, Any]:
    """Copy source config while guaranteeing target message channels are off."""
    target = copy.deepcopy(source)
    source_platforms = source.get("platforms", {})
    if not isinstance(source_platforms, dict):
        raise RuntimeError("default config's platforms section must be a mapping")

    # Channel credentials/settings may remain in config for future setup, but no
    # target gateway can connect because every known platform is explicitly off.
    target["platforms"] = {
        name: {"enabled": False}
        for name in source_platforms
    }
    return target


def target_profiles() -> list[Path]:
    if not PROFILE_ROOT.is_dir():
        raise RuntimeError(f"profile root is missing: {PROFILE_ROOT}")
    return sorted((path for path in PROFILE_ROOT.iterdir() if path.is_dir()), key=lambda path: path.name.casefold())


def active_cron_jobs(profile_name: str) -> list[str]:
    result = subprocess.run(
        ["hermes", "-p", profile_name, "cron", "list", "--all"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"cannot inspect cron jobs: {result.stderr.strip() or result.stdout.strip()}")
    return [match.group(1) for line in result.stdout.splitlines() if (match := ACTIVE_JOB.match(line))]


def pause_jobs(profile_name: str, job_ids: list[str], dry_run: bool) -> int:
    if dry_run:
        return len(job_ids)
    for job_id in job_ids:
        result = subprocess.run(
            ["hermes", "-p", profile_name, "cron", "pause", job_id],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            raise RuntimeError(
                f"cannot pause cron job {job_id}: {result.stderr.strip() or result.stdout.strip()}"
            )
    return len(job_ids)


def atomic_write(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(content, encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink(missing_ok=True)


def sync_profile(profile: Path, desired: str, dry_run: bool, stamp: str) -> tuple[str, int]:
    config_path = profile / "config.yaml"
    current = canonical_yaml(load_yaml(config_path)) if config_path.exists() else None
    config_state = "unchanged" if current == desired else "updated"
    jobs = active_cron_jobs(profile.name)

    # Pause first. If config synchronization fails, the safety invariant still
    # holds: target cron jobs remain disabled.
    paused = pause_jobs(profile.name, jobs, dry_run)
    if config_state == "updated" and not dry_run:
        backup = profile / BACKUP_NAME / stamp / "config.yaml"
        backup.parent.mkdir(parents=True, exist_ok=True)
        if config_path.exists():
            shutil.copy2(config_path, backup)
        atomic_write(config_path, desired)
    return config_state, paused


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report changes without modifying profiles.")
    args = parser.parse_args()

    source = load_yaml(SOURCE_CONFIG)
    desired = canonical_yaml(desired_target_config(source))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    totals = {"updated": 0, "unchanged": 0, "paused": 0, "failed": 0}

    for profile in target_profiles():
        try:
            state, paused = sync_profile(profile, desired, args.dry_run, stamp)
        except RuntimeError as exc:
            totals["failed"] += 1
            print(f"{profile.name}: ERROR {exc}", file=sys.stderr)
            continue
        totals[state] += 1
        totals["paused"] += paused
        print(f"{profile.name}: config={state} cron_jobs_paused={paused}")

    mode = "DRY-RUN" if args.dry_run else "SYNC"
    print(
        f"{mode} complete: profiles={totals['updated'] + totals['unchanged'] + totals['failed']} "
        f"updated={totals['updated']} unchanged={totals['unchanged']} "
        f"cron_jobs_paused={totals['paused']} failed={totals['failed']}"
    )
    return 1 if totals["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
