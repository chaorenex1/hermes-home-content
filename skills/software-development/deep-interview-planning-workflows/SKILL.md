---
name: deep-interview-planning-workflows
description: "Use for Kanban-authoritative Deep Interview fact gathering and Native Swarm handoff."
version: 2.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [deep-interview, planning, kanban, specification, ultrawork]
    related_skills: [plan, durable-agent-orchestration, deep-interview-for-memory-injection]
---

# Deep Interview Planning Workflows

## Contract

Deep Interview gathers explicit facts before implementation. `kanban.db` is the
only authority for the objective, feedback, hypotheses, decisions, future
goals, round snapshots, phase, and versions. Do not treat chat text,
`kb_temp`, Dynamic Context, or a specification file as a replacement authority.

The Host projects only goal and runtime state to
`kb_temp(information_type="deep_interview")` in three atomic sections:
`current_focus`, `current_progress`, and `future_needs`. AI may read this
projection through Dynamic Context but may not write it. The Host Projector is
the only writer.

## Interview Turns

1. Read the current Deep Interview block in Dynamic Context.
2. Use `interview_search` when the complete Kanban fact snapshot is needed.
3. Ask one concrete, falsifiable hypothesis about the current objective.
4. Do not create a plan, specification, implementation graph, or approval
   verdict during an interview round.
5. Let the Host append the authoritative future-goals footer. Do not generate
   that footer in the model response.

Explicit feedback is classified by the AI Feedback Router as exactly one of:

- `confirm_hypothesis`: record the confirmation and continue.
- `reject_hypothesis`: record the correction and ask a revised hypothesis.
- `goal_conflict`: keep the current goal and record the new goal as future work.
- `stop_interview`: stop immediately and generate the final specification.

There is no independent Judge, review round, approval step, next-round approval,
or stop confirmation.

## Specification And Handoff

Only `stop_interview` may create a specification. The canonical location is:

```text
HERMES_HOME/lancedb-memory/resource/spec/<title>.md
```

The specification is generated from the final Kanban fact snapshot and uses a
monotonic `spec_version`. Deep Interview does not compute a content hash or
digest.

Run `hermes ultrawork plan <spec-path> [repository]` or
`/ultrawork plan <spec-path> [repository]` after the specification is
completed. Plan accepts either the completed specification path or a direct
goal, but a path-like missing value must fail instead of being reinterpreted as
a goal.

## Read-Only Tools

- `interview_state`: compact operational phase and version metadata.
- `interview_search`: complete session, round, all-session, or keyword-matched
  Kanban fact snapshots.
- `kb_temp_get(information_type="deep_interview")`: projected goal/runtime
  state only.

`interview_search` is independent from `interview_state` and never mutates the
Interview. No legacy alias is registered.

## Verification Checklist

- Kanban facts commit before projection or visible continuation.
- The projection has exactly three sections and matches `goal_state_version`.
- Short feedback still receives strict Dynamic Context injection.
- Projection failure pauses the Interview and blocks the model turn.
- Future goals never replace the current goal.
- Every assistant response ends with the Host-generated future-goals footer.
- Importing Markdown creates a Kanban fact seed, not a specification.
- Only AI `stop_interview` creates the final specification.
- Native handoff uses the completed specification path/revision without a Deep
  Interview digest, and Execute consumes the resulting frozen plan path rather
  than the interview ID.
