---
name: hermes-profile-identity-management
description: "Use when managing SOUL.md across Hermes profiles."
version: 1.0.0
author: Masía
created_by: agent
metadata:
  hermes:
    tags: [hermes, profiles, soul, identity, kanban, swarm]
    related_skills: [hermes-agent, hermes-profile-synchronization, hermes-kanban-orchestration]
---

# Hermes Profile Identity Management

Use this skill to design, audit, deploy, or repair role-specific `SOUL.md` files across Hermes Profiles, especially named Kanban/Swarm workers.

This skill manages **identity and behavioral contracts**, not profile extension synchronization. Profile homes are isolated: each named Profile loads its own `HERMES_HOME/SOUL.md` and does not automatically inherit the default Profile's SOUL or user memory.

For the current Masía Native Swarm role map and canonical shared baseline, read [`references/masia-native-swarm-baseline.md`](references/masia-native-swarm-baseline.md).

## Identity layering model

Build each Profile SOUL from two conceptual layers:

1. **Shared behavior baseline** — user-facing style, evidence discipline, retry limits, safety, reversibility, and handoff-vs-acceptance semantics.
2. **Role contract** — the Profile's authority, required inputs/outputs, write boundary, forbidden actions, and lifecycle position.

Keep the output self-contained because Hermes does not require another Profile's SOUL to be present at runtime. Do not copy the complete default SOUL into every Worker: broad directives such as “create a Swarm” or “complete the entire task” conflict with bounded Developer, QA, Observer, and Ops roles.

Prefer the phrase **complete the current bound phase end-to-end** over **complete the whole task** for non-controller Profiles.

## Concern boundaries

Put only durable identity and behavior in SOUL:

- tone, language, directness, neutrality;
- evidence and verification defaults;
- role authority and prohibitions;
- bounded retry and escalation behavior;
- safety and secrecy constraints.

Keep these elsewhere:

- Profile capability descriptions used for routing: Profile metadata/description;
- current task IDs, digests, SHA, acceptance criteria, and evidence: Kanban card/context;
- project build, test, file-ownership, and repository rules: `AGENTS.md`;
- reusable domain procedures: Skills;
- temporary task status and session narrative: task/run state.

Do not include `SOUL.md` in a broad `skills/` or `plugins/` exact-mirror job unless identity synchronization is explicitly requested and role-aware. Generic mirroring can erase necessary role differences.

## Audit workflow

1. Enumerate the exact Profiles in scope from the live profile registry.
2. Determine which Profiles the selected workflow actually dispatches. Distinguish Native goal-only roles, manual `--worker`/`--verifier`/`--synthesizer` overrides, generic orchestrators, leads, observers, and operational executors.
3. Read every relevant SOUL. Group same-class lanes such as `dev1`–`dev4` and `qa1`–`qa4`, but confirm their role/lane identity remains distinct.
4. Check for:
   - missing shared behavior;
   - duplicated or contradictory directives;
   - Worker authority broader than its task phase;
   - QA permitted to implement or Developer permitted to accept;
   - evidence based only on summaries/paths;
   - unbounded retry or vague escalation;
   - project/task details embedded in durable identity.
5. Produce a role matrix before mutation: Profile, workflow phase, may-write scope, may-review, may-accept, may-orchestrate, expected handoff.

## Safe deployment workflow

1. Confirm the target Profile set and insertion policy.
2. Create a timestamped, non-overwriting backup of every target `SOUL.md`.
3. Use a stable section marker for the shared baseline and insert it once, normally after `# Identity` and before the first role-specific section.
4. Preserve the complete role contract; do not replace all SOULs with one generic file.
5. Make deployment idempotent: an existing marker is a skip, not a second insertion.
6. Read back representative controller, Developer, QA, and Ops/Observer files.
7. Deterministically verify:
   - every target contains the marker exactly once;
   - no unexpected Profile was modified;
   - backup count equals target count;
   - role-specific headings and authority boundaries remain present.
8. Start fresh Profile sessions or dispatch new Workers. Existing sessions retain the SOUL loaded at startup; a gateway restart is normally unnecessary for newly spawned Workers.
9. Smoke-test behavior through real cards: Developers do not orchestrate or self-accept, QA remains read-only toward the candidate, controllers cite actual evidence, and output matches the user-facing style contract.

## Role-bound wording rules

Shared directives must include an authority qualifier such as:

> within the authority of the current Profile, card, phase, and write scope

This avoids turning a useful global preference into a role-boundary violation.

Recommended semantic distinctions:

- Worker completion = handoff, not acceptance.
- QA pass = independent recommendation/evidence, not root completion.
- Judge acceptance = criterion resolution, not necessarily workflow finalization.
- Runtime/controller = authoritative lifecycle state transition.
- User-facing synthesis = presentation of verified state, not evidence creation.

## Verification checklist

- [ ] Exact target Profiles were enumerated.
- [ ] Workflow-to-Profile routing was confirmed.
- [ ] Every original SOUL has a rollback copy.
- [ ] Shared baseline appears exactly once per target.
- [ ] Role-specific authority and prohibitions remain intact.
- [ ] No secrets, project state, task IDs, or temporary artifacts entered SOUL.
- [ ] Representative files were read back.
- [ ] New-session behavior was tested or the new-session requirement was reported.

## Rollback

Restore each backed-up file to the corresponding Profile path, then start fresh sessions. Keep the failed deployment and verification report long enough to identify whether the defect came from target selection, insertion logic, or contradictory baseline wording.

## Common pitfalls

1. **Assuming default SOUL inheritance.** Named Profiles use their own `HERMES_HOME/SOUL.md`.
2. **Copying the entire default SOUL.** General orchestration instructions can make bounded Workers exceed authority.
3. **Using “finish the whole task” in every role.** Use current-phase completion for Workers, QA, Ops, and observers.
4. **Treating Profile descriptions as SOUL.** Descriptions route work; SOUL controls identity and behavior.
5. **Editing only one representative lane.** Deploy and verify all configured lanes while preserving lane identity.
6. **Verifying only command success.** Read back files and count the marker deterministically.
7. **Expecting running sessions to reload identity.** SOUL changes apply cleanly to fresh sessions.
8. **Broadly mirroring SOUL with extensions.** Skills/plugins may have one authoritative source; role SOULs require role-aware generation or explicit targeted edits.
