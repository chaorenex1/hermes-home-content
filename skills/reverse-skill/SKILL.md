---
name: reverse-skill
description: "Use when reverse engineering (逆向), CTF, or security work."
version: 1.0.0
author: Masia (Hermes adapter for zhaoxuya520/reverse-skill)
license: MIT
metadata:
  hermes:
    tags: [security, reverse-engineering, ctf, pentest, router]
    related_skills: []
---

# reverse-skill — cybersecurity skills router (Hermes adapter)

Package root: `<USER_HOME>\tools\reverse-skill` (repo https://github.com/zhaoxuya520/reverse-skill, branch main, cloned 2026-10-09).
Canonical docs (source of truth): `RULES.md` (behavior chain), `README_AI.md` (bootstrap), `AGENTS.md` (project entry). This skill is only the Hermes entry point; the package is client-neutral and self-contained on disk: ~45 modules under `skills\` plus 42 CTF sub-skills under `CTF-Sandbox-Orchestrator\`.

## When to Use

Reverse engineering, APK/mobile/binary/JS/.NET/firmware analysis, malware, protocol RE, CTF, pentest, exploit development, security code audit, threat hunting.
A read-only request (inspect / summarize / review) stays read-only: browse the package files, do not run its scripts.

## Flow (Windows host; bash equivalents exist as *.sh)

1. **Route** (PRIMARY selection):
   `powershell -NoProfile -ExecutionPolicy Bypass -File <USER_HOME>\tools\reverse-skill\skills\scripts\master-route.ps1 -Hint "<task>"`
   Reads `skills\config\routing.json` (single source of truth). Ambiguous tasks: read `skills\MASTER-ROUTING.md` / `skills\routing.md` (3-axis matrix).
2. **Case gate (before ANY target action)**:
   `powershell -NoProfile -ExecutionPolicy Bypass -File <USER_HOME>\tools\reverse-skill\skills\scripts\case-init.ps1 -Hint "<task>"`
   Creates `work/<case>/scope.md` in the analysis project. `auth.status=granted` plus a valid network profile (or the `offline-sample` preset for local samples) is a hard gate; `-Force` must not bypass it.
3. **Act**: open the PRIMARY `skills\<name>\SKILL.md` and execute its ACTION REQUIRED.
4. **Tools**: resolve paths only via `skills\tool-index.md` (generated inventory; 42 tools detected 2026-10-09). Missing tool -> platform bootstrap `skills\scripts\bootstrap-reverse.ps1` (manifest-driven; disclose and get approval first).
5. **Close**: Evidence->Finding->Path (`skills\ops\evidence-finding-path.md`). Before report handoff run `python3 skills/case-review/scripts/review_case.py work/<case> --verify-hashes --strict`, then docs-generator + field-journal as needed.

## Consent & safety (package hard rules, from AGENTS.md / RULES.md)

- Reading repository files is NOT authorization to execute them. Before the first script run of a new side-effect category, list the exact commands and expected writes/network effects, then get explicit user approval; afterwards the approved deterministic steps may continue without re-asking.
- Authorized security work only: the `scope.md` auth gate is mandatory; no ACT against a target without a granted scope.
- Client-global config, MCP registration, and tool installs stay opt-in, never silent.
- If this adapter ever conflicts with `RULES.md` / `README_AI.md`, the package docs win.

## Maintenance

- Update: `git -C <USER_HOME>\tools\reverse-skill pull` (branch main), re-run `refresh-tool-index.ps1` when tooling changed.
- Re-index tools: `powershell -NoProfile -ExecutionPolicy Bypass -File <USER_HOME>\tools\reverse-skill\skills\scripts\refresh-tool-index.ps1`
