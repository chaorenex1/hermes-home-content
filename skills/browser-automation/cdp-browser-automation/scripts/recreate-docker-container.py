#!/usr/bin/env python3
"""Recreate a Docker container with its exact run config plus extra env vars.

Docker bakes environment variables at creation time, so a service tuned by env
(for example CAMOFOX_IDLE_EXIT_TIMEOUT_MS) has to be replaced, not updated.
This clones the run parameters reported by `docker inspect`, renames the old
container out of the way, and creates the replacement. Values, including API
keys, go straight from inspect output into argv and are never printed.

Usage:
  python scripts/recreate-docker-container.py --name camofox-browser \
      --env CAMOFOX_IDLE_EXIT_TIMEOUT_MS=31536000000

Verify the replacement yourself afterwards: this script only creates the
container and reports the docker status line.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any


def docker(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["docker", *args], capture_output=True, text=True)


def env_keys(values: list[str]) -> str:
    return ", ".join(v.split("=", 1)[0] for v in values)


def build_run_args(
    name: str, insp: dict[str, Any], extra_env: list[str], restart: str
) -> list[str]:
    cfg = insp["Config"]
    host = insp["HostConfig"]
    args = ["run", "-d", "--name", name]
    if restart and restart != "no":
        args += ["--restart", restart]
    if cfg.get("User"):
        args += ["--user", cfg["User"]]
    if cfg.get("WorkingDir"):
        args += ["-w", cfg["WorkingDir"]]
    for container_port, binds in (host.get("PortBindings") or {}).items():
        for bind in binds or []:
            host_ip = bind.get("HostIp") or ""
            port = container_port.split("/")[0]
            args += ["-p", f"{host_ip}:{bind['HostPort']}:{port}"]
    for mount in insp.get("Mounts") or []:
        args += ["-v", f"{mount['Source']}:{mount['Destination']}"]
    for value in cfg.get("Env") or []:
        args += ["-e", value]
    for value in extra_env:
        if "=" not in value:
            sys.exit(f"--env needs KEY=VALUE, got {value!r}")
        args += ["-e", value]
    entrypoint = (cfg.get("Entrypoint") or [None])[0]
    if entrypoint:
        args += ["--entrypoint", entrypoint]
    args.append(cfg["Image"])
    args += cfg.get("Cmd") or []
    return args


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--name", required=True)
    parser.add_argument("--env", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--restart", default="unless-stopped")
    parser.add_argument("--backup-suffix", default=".bak")
    parser.add_argument("--dry-run", action="store_true")
    opts = parser.parse_args()

    result = docker("inspect", opts.name)
    if result.returncode != 0:
        print(f"docker inspect {opts.name} failed: {result.stderr.strip()}")
        return 1
    insp = json.loads(result.stdout)[0]
    args = build_run_args(opts.name, insp, opts.env, opts.restart)

    print(f"image: {insp['Config']['Image']}")
    print(f"existing env keys: {env_keys(insp['Config'].get('Env') or [])}")
    print(f"added env keys: {env_keys(opts.env) or '(none)'}")
    print(f"restart policy: {opts.restart}")
    if opts.dry_run:
        print("dry run, nothing changed")
        return 0

    backup = opts.name + opts.backup_suffix
    if docker("inspect", backup).returncode == 0:
        print(f"backup container {backup} already exists; remove or rename it first")
        return 1
    if docker("rename", opts.name, backup).returncode != 0:
        print(f"could not rename {opts.name} to {backup}")
        return 1
    created = docker(*args)
    if created.returncode != 0:
        docker("rename", backup, opts.name)
        print(f"create failed, rolled back: {created.stderr.strip()}")
        return 1
    print(f"created {created.stdout.strip()[:12]} (old container kept as {backup})")
    print(docker("ps", "--filter", f"name={opts.name}", "--format", "{{.Status}}").stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
