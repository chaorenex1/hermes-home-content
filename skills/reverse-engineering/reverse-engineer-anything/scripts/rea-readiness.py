#!/usr/bin/env python3
"""Compact REA readiness report from `rea-agents doctor --json`.

Answers "what does REA need to run here?" without paging the ~2,400-line
text catalog: prints one row per host check plus failing provider checks.
Exit code mirrors the audit (0 healthy, 1 not healthy, 2 no report).
"""
import argparse
import json
import subprocess
import sys


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="latest", help="rea-agents version to inspect (default: latest)")
    ap.add_argument("--node", action="store_true", help="also print the running node version")
    args = ap.parse_args()

    proc = run(["npx", "-y", f"rea-agents@{args.version}", "doctor", "--json"])
    if not proc.stdout.strip():
        print(proc.stderr.strip() or "doctor produced no output", file=sys.stderr)
        return 2
    report = json.loads(proc.stdout)

    if args.node:
        print("node " + run(["node", "-v"]).stdout.strip())
    print(
        "healthy={} environment_healthy={} exit={}".format(
            report.get("healthy"), report.get("environment_healthy"), proc.returncode
        )
    )

    checks = report.get("checks") or report.get("scope_checks") or []
    width = max([len(c.get("name", "")) for c in checks] + [4])
    for check in checks:
        state = "ok" if check.get("ok") else "FAIL"
        row = "{:<{w}}  {:<4}  {}".format(
            check.get("name", ""), state, check.get("classification", ""), w=width
        )
        if check.get("detail"):
            row += "  [" + str(check["detail"]) + "]"
        print(row)
        if check.get("remediation") and not check.get("ok"):
            print("{:{w}}        -> {}".format("", check["remediation"], w=width))

    for provider in report.get("providerInspections") or []:
        print(
            "provider {}: configured={} available={}".format(
                provider.get("id"), provider.get("configured"), provider.get("available")
            )
        )
        for check in provider.get("checks") or []:
            if check.get("ok"):
                continue
            print("  {} {}: {}".format(check.get("name"), check.get("code"), check.get("detail")))
            if check.get("remediation"):
                print("    -> " + check["remediation"])

    return 0 if report.get("healthy") else 1


if __name__ == "__main__":
    sys.exit(main())
