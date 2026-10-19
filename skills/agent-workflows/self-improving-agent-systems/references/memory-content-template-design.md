# Memory Content Template Design

Use this reference when authoring editable per-type prompts under:

```text
HERMES_HOME/lancedb-memory/prompts/
```

## Layer Boundary

Each `<memory_type>.md` is a **content-generation prompt**, not the whole extraction protocol. It should define:

- what durable content belongs to the type;
- required and optional body sections;
- section semantics and ordering;
- when to split or merge memories;
- omission, grounding, and anti-hallucination rules;
- boundaries against sibling memory types;
- one or two concrete content examples.

Keep these concerns in the outer host/extraction contract instead:

- evidence IDs, source spans, citations, and offsets;
- untrusted-input/tool-execution policy;
- JSON or transport schema;
- candidate create/update/skip operations;
- quarantine, review, promotion, and persistence;
- retries, model limits, and lifecycle metadata.

Do not add `Evidence Contract`, `Structured Semantic Output`, or protocol field names to content templates. Templates may still require that facts come from the supplied conversation; that is a content-grounding rule, not a citation schema.

Default to normal content-generation prompts. A section skeleton is not a variable-replacement contract. Add replacement tokens only after the caller explicitly confirms the requirement and the runtime defines token syntax, required/optional values, escaping, unresolved-token failure, and literal non-recursive replacement.

## Shared Authoring Rules

- Generate one bounded memory unit per candidate.
- Do not import unsupported facts from external knowledge, accepted memory, directory summaries, or hindsight.
- Preserve negation, uncertainty, time, scope, environment, and conditions.
- Omit unsupported optional sections entirely; never emit blank headings, `Unknown`, `None`, `N/A`, or unresolved placeholders.
- Keep facts atomic enough to update or contradict independently.
- Derive the document title from supported body content.
- Examples must obey the same rules as production output; do not show invalid placeholders and then explain them away.
- Verify the written file by reading it back and checking required headings plus forbidden protocol/placeholder tokens.
- Separately inspect runtime wiring. Prompt-file existence does not prove the provider loads it.

## Entities

Purpose: stable facts about one explicitly named entity.

The entity name field and every attribute field are dynamic. Do not force a fixed `Properties` section. Example:

```text
# asia

## Agent name
asia

## Role
Technical agent

## Operating System
Windows

## Response Preference
Concise answers
```

Rules:

- One entity per memory.
- The name label may reflect entity kind (`Agent name`, `Project name`, `Service name`, etc.); examples are not a whitelist.
- Attribute labels and count are dynamic semantic normalizations of conversation statements.
- Split compound statements into atomic attributes.
- Do not strengthen `uses Windows` into `Windows 10` unless version 10 appears in the conversation.
- Preserve qualified contexts such as `Development Platform` versus an unrestricted `Operating System`.

## Events

Purpose: one bounded, time-anchored occurrence.

Core body:

```text
Event Name
Occurred At
Background
Result
Impact
```

`Event Name` and `Occurred At` are required. Other sections appear only when supported. Optional additions include Trigger, Participants, Timeline, Decisions, Follow-up, and Related Entities.

Rules:

- Separate event time from report, message, extraction, or persistence time.
- Preserve time precision and timezone; do not invent missing components.
- If storage topology requires `/events/YYYY/MM/DD/...`, skip events without a supported full date unless the topology is explicitly redesigned.
- Background is the pre-event condition or cause.
- Result is the direct immediate outcome.
- Impact is a downstream consequence; do not duplicate or infer it.
- Split independent decisions, deployments, failures, or milestones; keep one continuous causal sequence together when it shares one goal and outcome.

## Experiences

Purpose: one problem or goal and the process used to address it.

Recommended sections:

```text
Problem
Goal
Context and Constraints
Resolution Process
Final Solution
Result
Verification
Root Cause
What Worked
What Failed
Hypotheses Considered
Lesson Learned
Reusable Steps
Applicability and Limits
```

At least one of Problem or Goal, plus Resolution Process and Result, is required. Completed experiences may include Final Solution and Verification when actually supported.

Rules:

- Preserve action → observation → decision → adjustment, not a flat command log.
- Separate final solution (the intervention) from result (the observed state) and verification (how it was confirmed).
- Root Cause is confirmed; unverified possibilities belong under Hypotheses Considered.
- An unresolved process is allowed only when it contains durable diagnostic or ruled-out knowledge; state the unresolved result and do not invent a solution.
- Keep the memory problem-centered. Tool-centered operational knowledge belongs in tools; a full task history belongs in trajectories.

## Tools

Purpose: durable experience using one primary tool. This is a normal content-generation prompt, **not** a variable-replacement template by default.

Recommended sections:

```text
Tool Name
What It Is
Task or Goal
Context and Constraints
When to Use
Usage Workflow
Commands or Invocation
Key Options and Inputs
Observed Result
What Worked
Failure Cases
Quirks and Pitfalls
Reusable Guidance
Applicability and Limits
```

Tool Name, Task or Goal, Usage Workflow, and Observed Result are required.

Rules:

- One primary tool per memory; the title is the stable tool name so future experience can merge under one tool document.
- Keep the content tool-centered: how to use X. If the durable value is how to solve Y across tools, use experiences.
- Record actual commands/options and observed results, not invented manual content.
- Remove secrets and irrelevant temporary identifiers from reusable commands.
- A failed use is valid when it establishes a durable failure mode, prerequisite, recovery, or pitfall.
- Do not create `Usage Statistics` from ordinary conversation; isolated observations do not support reliable telemetry.

## Trajectories

Purpose: the actual execution of one user requirement from analysis through implementation and verification.

Recommended sections:

```text
User Requirement
Acceptance Criteria
Initial State
Analysis
Implementation
Verification
Outcome
Decisions and Alternatives
Failures and Recovery
Scope Changes
Artifacts and Changes
Next Steps
```

User Requirement, Analysis, and Outcome are required. A trajectory that claims completion must also contain actual Implementation and Verification content.

Rules:

- Preserve the user's real scope and mid-turn corrections; do not broaden the task retrospectively.
- Analysis contains observable findings, constraints, and decisions—not hidden chain-of-thought.
- Implementation records actions actually performed, never planned work presented as done.
- Verification records checks actually run and their observed results, never intended checks presented as passed.
- Outcome distinguishes completed, partial, blocked, and failed states and names the real artifact or limitation.
- Record meaningful retry loops honestly: analysis → implementation → failed verification → correction → re-verification.
- Next Steps appears only for explicit deferred, blocked, or agreed follow-up work; omit generic suggestions.
- Keep trajectories execution-centered. Distilled reusable problem-solving knowledge belongs in experiences; a time-anchored occurrence belongs in events.

## Runtime Compatibility Audit

Before wiring new section names into production, search for exact section-name dependencies in:

- deterministic renderers and validators;
- omission validation and patch-anchor allowlists;
- path derivation (especially event dates and entity subtype paths);
- trajectory-to-experience converters;
- tests and historical template migrations.

Changing only the editable prompt can cause generated content to be rejected when the runtime still whitelists legacy headings. Treat prompt semantics and runtime compatibility as separate deliverables, and report when the file is created but not active.
