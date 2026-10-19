# Memory-Body Prompt Template Audit

Use this reference when a memory system stores editable, type-specific prompt files that define the Markdown body of durable memories.

## Core separation

Treat three contracts as separate layers:

1. **Memory-body semantics** — what facts belong in a memory type, its headings, required/optional content, atomicity, omissions, examples, and boundaries from sibling types.
2. **Outer extraction protocol** — JSON shape, candidate operations, evidence IDs, source spans, trust state, safety handling, review, and persistence metadata.
3. **Runtime renderer/validator** — how extracted semantic fields become files, paths, headings, updates, and validated stored documents.

A body template should not repeat the extraction protocol. Remove sections such as `Evidence Contract`, `Structured Semantic Output`, JSON schema, evidence IDs, source spans, review, and persistence instructions. The outer prompt owns those concerns.

## Audit sequence

1. Resolve `HERMES_HOME` and inspect the actual `lancedb-memory/prompts/` directory. Do not assume declared templates exist.
2. Read the active extraction prompt, body renderer, validator, path resolver, and tests.
3. Prove whether file-based prompts are loaded in production. A storage class or test-only initialization is not runtime integration.
4. Compare each prompt's body contract with the renderer's allowed headings and update anchors.
5. Identify path/topology constraints such as singleton identity, date-keyed events, one-tool documents, or project directory slugs.
6. Separate semantic findings from implementation gaps. Creating a prompt file does not activate it.
7. After writing or editing a template, read it back and verify required headings plus forbidden protocol tokens once.

## Type contracts

### Entities

- One candidate describes one entity.
- The entity-name field is dynamic (`Agent name`, `Project name`, `Service name`, etc.).
- Every attribute field is dynamic (`Role`, `Operating System`, `Response Preference`, etc.); do not force attributes into fixed `Properties` or `Entity Attributes` sections.
- Attribute names may faithfully normalize conversation language, but values must not be strengthened. `uses Windows` does not justify `Windows 10` without additional conversation content.
- Keep attributes atomic and preserve qualifiers, negation, temporal scope, and unresolved conflicts.

### Events

- One candidate describes one bounded event.
- Core content: Event Name, Occurred At, Background, Result, and Impact; optional event-specific sections are omitted when unsupported.
- Distinguish result (direct outcome) from impact (downstream consequence).
- Preserve time precision and timezone. Never substitute report, message, extraction, or current system time for event time.
- If storage topology requires `YYYY/MM/DD`, either require a supported complete date or change topology; never invent a date to satisfy the path.

### Experiences

- One candidate describes one problem or goal and its resolution process.
- Separate Problem, Goal, Resolution Process, Final Solution, Result, Verification, Root Cause, What Worked, What Failed, Hypotheses, Lessons, Reusable Steps, and Limits as supported.
- Do not promote hypotheses to root cause or commands to verification.
- Experiences are distilled problem-solving knowledge, not raw task trajectories.

### Tools

- One candidate describes experience using one primary tool.
- Use a normal content-generation prompt unless the user explicitly requests a replacement-template engine. Do not infer variable replacement from the word “template.”
- Core content: Tool Name, Task or Goal, Usage Workflow, and Observed Result; optional content includes invocation, key options, what worked, failure cases, quirks, guidance, and limits.
- Avoid `Usage Statistics` from ordinary conversation; a small number of uses does not support reliable telemetry.
- Tools memory is tool-centered; cross-tool problem solving belongs in experiences.

### Trajectories

- One candidate describes one independently assessable user requirement from analysis through implementation and verification.
- Preserve User Requirement, acceptance criteria, initial state, observable analysis findings, actual implementation, actual verification results, outcome, corrections, failures/recovery, artifacts, and explicit next steps.
- Do not reconstruct hidden chain-of-thought. Record concise observable findings and decisions.
- Never turn plans into implementation claims or planned checks into passing verification.
- User corrections refining the same deliverable remain in one trajectory; independent deliverables split.

### Projects

- One candidate describes one project, not one task or arbitrary component.
- Core content starts with Project Name plus at least one of Purpose/Goals, Current State, or Architecture.
- Optional content includes scope, components, stack, storage, integrations, stable paths, configuration, workflow, testing, runtime, milestones, decisions, conventions, blockers, risks, and open work.
- Separate current from planned and implemented from runtime-enabled/verified.
- Separate blockers (active impediments) from risks (potential problems).
- Derive or inject project identity; never collapse unrelated projects into a fallback `default` slug.

### Identity

- Identity is a singleton user profile, not a collection of entity documents.
- Summarize only stable identity and work: preferred name, professional identity, roles, organization/team, work, responsibilities, skills, domains, sustained focus, affiliations, career goals, and background.
- Do not infer formal occupation, employer, seniority, name, gender, location, education, or ownership from one request, account, directory, repository, or tool use.
- Keep interaction preferences in preference memory and project details in projects memory.
- Minimize personal data and exclude credentials, financial, government-ID, precise address, health, political, religious, family, and other unnecessary sensitive information.
- Preserve explicit identity-operation gating when the runtime provides it.

## Template writing rules

- Use a stable title and an explicit ordered body contract.
- State required sections and conditional sections. Omit unsupported sections rather than filling placeholders.
- Include boundary rules, anti-inference rules, state/conflict handling, exclusions, and one grounded example.
- Keep headings semantic and specific; avoid catch-all sections such as `Properties`, `Project-Specific Notes`, or `Evidence Notes`.
- Do not claim file creation changes active runtime behavior.

## Verification probe

For every created template, verify:

- the file exists and is non-empty;
- required headings are present;
- forbidden protocol markers are absent: `## Evidence Contract`, `## Structured Semantic Output`, `evidence_ids`, `source_spans`, and `source_ref`;
- unresolved replacement tokens are absent unless replacement semantics were explicitly requested;
- examples do not violate the template's own rules.

One read-back plus one bounded content check is sufficient. Do not repeat verification after it passes.
