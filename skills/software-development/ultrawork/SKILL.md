---
name: ultrawork
description: "Use for Hermes Ultrawork planning, execution, and runtime inspection."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [ultrawork, planning, execution, kanban, session, deep-interview]
    related_skills: [deep-interview-planning-workflows, plan, ultrawork-for-memory-injection]
---

# Hermes Ultrawork

## Trigger

Use this skill when the task is to plan, execute, inspect, or explain the
Hermes Ultrawork workflow.

## Command Grammar

Supported commands:

```text
/ultrawork plan <goal-or-spec-path> [repository]
/ultrawork execute <plan-path> --mode session|Kanban
/ultrawork status
/ultrawork routes <run-id>
/ultrawork events <run-id>

hermes ultrawork plan <goal-or-spec-path> [repository]
hermes ultrawork execute <plan-path> --mode session|Kanban
hermes deep_interview <goal>
```

The Ultrawork namespace has only `plan` and `execute`. A bare invocation with
goal text is rejected and does not start Deep Interview. Use the dedicated
Deep Interview command when requirements need clarification. Legacy Kanban
orchestration and Ralph-only workflows are not Ultrawork entry points.

## Source Classification

- `plan` accepts either a direct natural-language goal or a completed
  Deep Interview specification path.
- Path-like input that does not exist is an error. Never reinterpret it as a
  direct goal.
- When `repository` is omitted, Ultrawork selects one bounded Git repository
  autonomously and records evidence in the plan receipt.

## Plan Contract

- Planning writes exactly one authoritative file under:

```text
HERMES_HOME/lancedb-memory/resource/plan/<title>.md
```

- Do not create `tasks/plan.md`, `tasks/todo.md`, or `repository_spec_path`.
- The plan decomposes the goal/specification into vertical XS/S/M tasks with
  requirement traceability, dependencies, acceptance, verification, and write
  scope.
- Plan and Execute are separate. Execute must not re-plan.

## Execute Contract

- `execute` accepts only a completed plan file under the exact profile-local
  `resource/plan` root.
- `--mode session` runs the frozen DAG in a Hermes session coordinator.
- `--mode Kanban` runs the exact same frozen DAG through durable Kanban/Native
  Swarm runtime semantics.
- `Kanban` is accepted case-insensitively at the command boundary and
  normalized internally.

## Resume And Inspection

- Resume through the owning Hermes session or durable Kanban run; do not create
  a replacement plan or execution run.
- `/ultrawork status` lists current runs.
- `/ultrawork routes <run-id>` shows persisted route state.
- `/ultrawork events <run-id>` shows the durable event history.
- After resuming, read the current Ultrawork Context and persisted loop state
  before taking another action.

## Runtime Rules

- No Ultrawork content hash or digest fields are authoritative.
- Use frozen plan/spec revisions, exact content comparison, stable IDs, and
  persisted evidence instead.
- Cleanup-enabled work follows:

```text
Dev -> De-Sloppify -> QA
```

- Fixed/max/adaptive iteration policies are transactional and must record
  changed strategy on retry after failure.
- LLM-based completion criteria must cite evidence and cannot be the sole
  release or merge gate.

## Context And Checkpoint Discipline

- Read the current Ultrawork Context before major decisions or resumed work.
- Update durable runtime state before publishing the next Context projection.
- After two qualifying browse/search/inspection actions, commit a findings
  checkpoint before the third qualifying action.
- Context stores only bounded progress/focus/future-needs summaries plus basic
  PR/spec reference metadata.

## PR Specification Reference

- PRs cite only bounded specification sections and excerpts.
- Store only:
  - spec title
  - spec version
  - referenced requirement IDs or section headings
  - PR number or URL
- Never store the full specification, full excerpt, or full plan in Context.

## Forbidden Behavior

- Do not run bare `/ultrawork <goal>`; use `/ultrawork plan <goal>` instead.
- Do not use `hermes kanban swarm`; that public orchestration entry point is removed.
- Do not route Ultrawork through Ralph or Ralph-only workflows.
- Do not write Provider physical context files directly.
- Do not execute arbitrary Markdown outside the frozen plan root.
- Do not reintroduce content digests as Ultrawork runtime identity.
