---
name: iterative-planning-workflows
description: "Use for persistent Ralph or Deep Interview planning loops."
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [planning, ralph, deep-interview, review, persistence, handoff]
---

# Iterative Planning Workflows

## Overview

Class-level guide for planning-only loops that inspect evidence, update one designated Markdown plan, persist lifecycle state, pass an independent review gate, and optionally hand an approved immutable artifact to execution. The planner plans; it does not implement.

Use the protected `plan` skill for one-shot planning without a persistent review loop.

## Shared Contract

1. Bind one profile-local owner, plan ID, canonical path, and writable artifact.
2. Read authoritative evidence with read-only tools; modify only the designated plan.
3. Persist goal, template, path, owner, status, round, review attempt, verdict, evidence, and bounded history.
4. Keep logical rounds separate from review attempts; real user input preempts synthetic continuation.
5. Give the Judge actual bounded Markdown, not a prose summary or inferred path; invalid/failed review fails closed.
6. Approval binds the exact artifact digest without rewriting the file.
7. Execution rejects missing, moved, escaped, changed, unapproved, or non-executable plans.
8. Finite budgets end in an explicit paused/blocked/review state, never an unbounded loop.

## Ralph Branch

Ralph supports iterative evidence-driven updates, durable review state, cross-surface routing, explicit execution grammar, and digest-bound handoff. Keep edit anchors out of the plan; resolve them immediately before patching. Ensure CLI, TUI, Gateway, and Desktop use one semantic plan identity despite transport IDs. See `references/ralph-planning-workflows.md` and migrated Ralph references.

### Ingesting user correction notes

When a round starts from the user's correction-notes file instead of a prior plan review:

- `stat` the notes and the plan first: notes are frequently newer than the plan they correct, and both may be newer than the code they assume.
- Classify every notes item into exactly one outcome: already in the plan / already implemented in code (cite file:line) / new or conflicting. An item that contradicts a standing plan constraint is a conflict to surface, never to silently reconcile.
- When the notes declare an earlier analysis wrong, verify the corrected claim against the code anyway — the old misunderstanding often still exists as live code, and sometimes in the plan's own sample text.
- Never re-seed stale strings quoted inside the notes (old path orders, old module names, old schema fields) into the plan; quote the target form from current code or plan instead.
- Leave residual ambiguities (identifier naming, field source-of-truth, layout choices) as explicit open questions for the user; guessing re-derives the errors the notes exist to correct.

## Deep Interview Branch

Deep Interview is the constrained variant: one canonical Markdown plan under the active profile's plan root; no implementation, install, commit, deploy, service restart, or writes elsewhere. Approval freezes SHA-256 of exact UTF-8 bytes, and Native/Ultrawork verifies ownership, confinement, status, and digest before execution. See `references/deep-interview-planning-workflows.md`.

## Verification Checklist

- [ ] Only the designated plan file was writable.
- [ ] Ownership/path/template/round/attempt/verdict survive restart.
- [ ] User input preempts continuation.
- [ ] Judge receives actual Markdown and fails closed.
- [ ] Approval does not alter bytes.
- [ ] Every surface uses one plan identity.
- [ ] Handoff is digest-bound, dependency-valid, and retry-consistent.
