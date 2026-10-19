---
name: ralph-planning-workflows
description: "Use for Ralph planning, review, persistence, and handoff."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [ralph, planning, iterative, persistent, review, ultrawork]
    related_skills: [plan, durable-agent-orchestration]
---

# Ralph Planning Workflows

## Overview

This is the class-level guide for Ralph: planning-only loops that inspect evidence, update one designated plan artifact, persist lifecycle state, pass an independent review gate, and optionally hand an approved immutable plan to execution. Ralph plans work; it does not perform the planned implementation.

## When to Use

- `/ralph` planning mode is active.
- A plan must be iteratively refined from repository or document evidence.
- Existing plan content needs surgical updates and executable verification criteria.
- Ralph lifecycle, review, persistence, UI routing, or Ultrawork handoff is being designed or debugged.

Use `plan` for a one-shot plan without a persistent review loop.

## Planning-Only Contract

1. Read authoritative sources with read-only tools.
2. Write or patch only the designated plan file. Never modify source, tests, config, dependencies, Git history, services, or external systems.
3. Keep one durable plan owner and one writable artifact. Persist plan ID, path, goal, status, template identity, round/attempt, review evidence, and bounded history.
4. A finite budget ends in a reviewable paused/blocked state, never an unbounded loop.
5. Real user input preempts synthetic continuation.
6. Completion requires a readable artifact, evidence-backed acceptance criteria, and explicit approval; prose claims are not completion evidence.

## Evidence-Driven Refinement

For each round:

1. Read the current plan sections and authoritative source material.
2. Map every concrete gap to an exact target section, required replacement/addition, source evidence, verification command, recovery behavior, and blocker condition.
3. Keep `old_string` out of the plan artifact. Resolve exact edit anchors immediately before a later `patch` call using `read_file`/`search_files`.
4. Prefer surgical updates over full rewrites. When scope expands, update goal, tasks, acceptance criteria, risks, rollback, and handoff consistently.
5. Verify every changed section by rereading it and run full-text checks for stale vocabulary, missing headings, and contradictions.

The worked update example is `references/ralph-plan-update-worked-example.md`.

## Durable Loop and Review State

Model the lifecycle explicitly:

```text
active planning round -> candidate persisted -> judge
-> awaiting_review -> approve/continue | approve/done | feedback/same-round retry | pause/block
```

- Logical round and review attempt are separate counters.
- Judge actual bounded Markdown, not planner prose or an unreadable path.
- Judge failure/invalid output fails safe to revise or blocked.
- Persist review evidence before presenting choices.
- Clarify timeouts leave the plan awaiting review.
- Pause, clear, archive, and cross-session resume preserve single-owner semantics; transfer is transactional/compare-and-swap.

Implementation references:
- `references/dedicated-sqlite-state.md`
- `references/hermes-planning-loop-design.md`
- `references/ralph-round-state-and-intent.md`
- `references/ralph-review-pitfalls.md`
- `references/ralph-lifecycle-invariants.md`

## Cross-Surface Routing

CLI, Gateway, TUI, and Desktop share lifecycle semantics while respecting transport shapes.

- Bind Ralph to the durable live session key used by the planning turn.
- Start/resume acknowledgement is not a planner turn; route a canonical continuation through the prompt path.
- Tag continuations with plan identity, keep them below user input, and prevent self-cancellation.
- Route slash controls before ordinary review interception.
- Desktop review state is session/request scoped and cleared by a semantic resolution event.
- Test distinct transport/durable IDs, restart/reconnect, replies, user preemption, and background attribution.

See `references/tui-session-binding.md`, `references/hermes-tui-ralph-integration.md`, and `references/ralph-runtime-repair-checklist.md`.

## Plan Grammar and Execution Handoff

An executable approved plan uses stable task sections, explicit dependencies, acceptance/evidence requirements, verification commands, retry limits, rollback, and stop conditions. Approval binds a digest and exactly one canonical execution manifest. Execution rejects missing, changed, unapproved, or non-executable plans.

- Validate dependencies as a DAG and schedule only dependency-ready work.
- Align one-shot operations with `max_attempts: 1`.
- Map every acceptance criterion to substantive evidence.
- Permit at most one active execution owner per plan.
- Record terminal template-history outcome exactly once.

## Verification Checklist

- [ ] Only the designated plan file is writable.
- [ ] Goal, plan path, template, owner, round, attempt, and verdict survive reload.
- [ ] User input preempts continuation.
- [ ] Judge receives actual plan Markdown and fails closed.
- [ ] Review transitions are distinct and audited.
- [ ] Every surface uses the same plan identity.
- [ ] Execution handoff is digest-bound, dependency-valid, and retry-consistent.

## Pitfalls

- Do not execute implementation work from planning mode.
- Do not persist exact `old_string` blocks inside the plan artifact.
- Do not key ownership to a rotating transport/session ID.
- Do not infer identity from goal text when plan ID is available.
- Do not let a general Judge approve an artifact that cannot compile into the required route.
- Do not treat a visible review card as proof persisted ownership is correct.
