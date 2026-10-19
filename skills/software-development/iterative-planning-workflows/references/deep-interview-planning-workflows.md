---
name: deep-interview-planning-workflows
description: "Use for Deep Interview planning, review, persistence, and Native Ultrawork handoff."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [deep-interview, planning, iterative, persistent, review, ultrawork]
    related_skills: [plan, durable-agent-orchestration]
---

# Deep Interview Planning Workflows

## Contract

Deep Interview is a planning-only loop. It may inspect evidence and update one
designated Markdown plan under the active profile's `HERMES_HOME/plans`, but it
must not implement, install, commit, deploy, restart services, or modify any
other file.

The lifecycle is stored in the active board's `kanban.db`. A plan has one
profile-local owner, one canonical file, bounded rounds, separate review
attempts, and fail-closed independent review. Real user input preempts an
internal continuation.

## Evidence-Driven Refinement

1. Read the current plan and authoritative sources.
2. Map gaps to exact files, ordered tasks, dependencies, acceptance criteria,
   verification evidence, retry limits, rollback, and stop conditions.
3. Update only the designated plan file and read it back completely.
4. Give the Judge the actual Markdown, not a prose summary or inferred path.
5. Keep the plan human-readable. Do not generate an execution manifest or DAG.

## Review And Handoff

Approval freezes the SHA-256 digest of the exact UTF-8 plan bytes without
rewriting the file. Any later byte change invalidates execution.

Run `ultrawork_execute` with the approved `deep-interview-*` plan ID and an
optional explicit repository. Native Swarm verifies ownership, confinement,
status, and digest, then its CTO planning card reads the complete plan and
freezes the Native task graph. Deep Interview never compiles routes itself.

## Verification Checklist

- Only the designated plan file was written.
- Plan ownership, path, round, attempt, verdict, and history survive restart.
- Judge input contains the complete Markdown and failure cannot approve it.
- Approval does not alter plan bytes.
- Execution rejects an unapproved, moved, escaped, or digest-mismatched plan.
- Native execution records the plan ID, digest, and path in one `kanban.db`.
