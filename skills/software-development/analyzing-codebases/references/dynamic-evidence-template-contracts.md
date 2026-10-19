# Dynamic Memory Content Template Contracts

Use this reference when a profile-local prompt creates the body of a memory document from conversation content. It captures the boundary between memory content, outer extraction protocol, and runtime integration.

## Three-layer boundary

### 1. Memory-type content template

Owns:

- what kind of durable fact belongs in this memory type;
- document headings and their ordering;
- dynamic versus fixed field semantics;
- atomicity, normalization, omissions, and type boundaries;
- rendered-content examples.

Does not own:

- evidence IDs or source spans;
- JSON or candidate schemas;
- trust, review, promotion, or persistence state;
- update operations or controller instructions.

A content template may still require that all facts come from the supplied conversation and forbid unsupported inference. That is a content-quality rule, not an evidence protocol.

### 2. Outer extraction/controller prompt

Owns evidence binding, source-span validation, safety treatment of untrusted input, strict output shape, candidate operations, limits, and review lifecycle.

### 3. Runtime integration

Owns template initialization/loading, renderer compatibility, validation, persistence, update anchors, and activation. Creating a file proves only that it is stored.

## Entity content pattern

Entity bodies have dynamic name and attribute fields. Do not force them into fixed `Properties`, `Relationships`, or `Entity Attributes` sections.

Source:

```text
asia is a technical agent, uses Windows, and prefers concise answers.
```

Faithful rendered body:

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

- one document describes one explicitly named entity;
- the name-field label may vary (`Agent name`, `Project name`, `Service name`, etc.); examples are not a whitelist;
- attribute labels are concise noun phrases produced by lossless semantic normalization;
- attribute count and labels are dynamic;
- split compound statements into atomic fields;
- preserve negation, temporal state, environment, and scope;
- qualify context-specific properties (`Development Platform`) instead of broadening them (`Operating System`);
- do not emit `Windows 10` unless the conversation actually supports version 10;
- omit unnamed entities and name-only entities without durable attributes.

## Event content pattern

Event bodies use stable core chapters because event semantics are not an arbitrary property bag:

```text
# <event name>

## Event Name
<event name>

## Occurred At
<event occurrence time>

## Background
<pre-event conditions or reasons>

## Result
<direct event outcome>

## Impact
<downstream consequence>
```

Rules:

- `Event Name` and `Occurred At` are required under a date-partitioned storage topology;
- include `Background`, `Result`, and `Impact` only when the conversation supports them;
- keep direct result separate from downstream impact;
- preserve time precision and timezone; do not replace event time with report/extraction time;
- do not invent a complete date merely to satisfy `/events/YYYY/MM/DD/...` storage;
- split independent decisions, deployments, failures, recoveries, or milestones into separate events;
- a continuous sequence may remain one event when it shares one goal, bounded time window, and direct result;
- optional chapters such as `Trigger`, `Participants`, `Timeline`, `Follow-up`, and `Related Entities` appear only when useful and supported;
- do not emit empty, `Unknown`, `N/A`, or placeholder chapters.

## Content-only prompt verification

After writing or editing a memory content template, verify:

1. Required headings and examples match the user's declared topology.
2. Dynamic fields remain dynamic; examples are not accidentally described as a whitelist.
3. Values do not exceed the conversation facts.
4. Compound statements are shown as atomic fields.
5. Optional unsupported sections are omitted rather than filled with placeholders.
6. The template contains no protocol sections or fields unless explicitly requested:
   - `Evidence Contract`
   - `Structured Semantic Output`
   - `evidence_ids`
   - `source_spans`
   - `source_ref`
7. The edit touched only the requested prompt files unless integration work was explicitly requested.

## Integration audit map

When the task is to integrate—not merely author—the template, inspect separately:

1. Prompt file creation and initialization.
2. Production loader and effective profile path.
3. Prompt composition order with the outer extraction protocol.
4. Classifier/extractor output schema.
5. Fixed section allowlists and omission rules.
6. Renderer loops and dynamic heading generation.
7. Rendered-document parser/validator.
8. Patch/update anchor selection and duplicate-field behavior.
9. Persistence of protocol metadata outside the content template.
10. Tests proving the installed production path consumes the editable template.

Report activation accurately:

- **stored**: the file exists;
- **loaded**: production reads it;
- **enforced**: generated output and downstream validation follow it.

Never report these states as equivalent.
