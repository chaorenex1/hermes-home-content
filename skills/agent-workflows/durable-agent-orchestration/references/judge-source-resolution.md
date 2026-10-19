# AI Judge source-resolution boundary

## Problem class

A dynamic route can carry human-readable `source_refs` such as `Task 1: <title>` while deterministic extraction expects a stable heading key such as `Task 1`. Treating the mismatch as a pre-Judge hard failure blocks otherwise valid work and prevents the semantic Judge from evaluating the evidence.

## Required split

- **Deterministic safety gate:** locate the Ralph artifact, read it, hash its exact bytes, and require equality with the workflow's frozen plan digest. Missing/unreadable artifact or digest mismatch fails closed.
- **AI semantic gate:** resolve route refs against the digest-verified plan. Give the Judge the route node, original refs, a bounded candidate heading/section map or plan Markdown, raw task evidence, and stable criterion IDs. The Judge returns strict JSON mapping each ref to resolved sections or `unresolved` / `ambiguous`, plus `pass|rework|blocked` criterion assessments.

## Rules

1. Do not reject a route before the Judge only because a source ref fails literal heading matching.
2. Do not silently rewrite aliases: retain original refs and persist Judge-resolved refs with the review evidence.
3. A genuinely unresolved/ambiguous required ref is a Judge-backed `rework` or `blocked` finding with candidate headings and a recovery instruction.
4. Keep v1/non-route workflows compatible: they may omit route-source packets.
5. Tests must cover a valid alias resolving semantically and a non-existent/ambiguous alias receiving an actionable Judge verdict.
