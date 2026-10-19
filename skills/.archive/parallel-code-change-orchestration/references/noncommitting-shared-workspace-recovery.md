# Non-committing shared-workspace recovery

Use this reference when a durable multi-agent code run must modify one existing dirty checkout and the user has not authorized commits.

## Why the normal parallel shape can fail

A Native delivery route is not merely an observer. It can advance through Dev → QA → rework and consume route attempts. If read-only baseline audits are created as peer routes carrying the full feature acceptance set, their expected pre-implementation findings can trigger QA rework while the sole writer is still active. The composite may become blocked even though useful implementation work continues.

Generated retry/rework cards can also lose root-only context. A scratch worker may know the failed criterion but not the repository or frozen plan path, causing expensive rediscovery and ambiguous writes.

## Safe topology

```text
preflight audits (read-only, non-gating)
                 │
                 v
single shared-directory Dev writer
                 │ terminal evidence packet
                 v
fresh Functional QA (read-only)
                 │ gate=pass
                 v
fresh Global QA (read-only)
                 │ gate=pass
                 v
one final Synthesizer (read-only)
```

Never start Functional QA against a changing shared tree. A Dev handoff completes the Dev card; it does not mean the feature is accepted.

## Required task context

Repeat all of these in every Dev recovery, Functional QA, Global QA, and Synthesizer card:

- absolute repository/workspace path;
- frozen plan or specification path/digest;
- exact writable files and `Do not commit`;
- protected pre-existing dirty paths;
- exact failed criteria and preserved passed criteria;
- required focused/full test commands;
- deployment/parity/smoke evidence requirements;
- failure path and retry ceiling;
- authoritative active-chain parent/child IDs when using Kanban.

Do not rely on a root Blackboard comment or prior task body being inherited by generated recovery cards.

## Historical runtime versus recovered delivery

If the original composite exhausts attempts, keep it as immutable failure evidence. Do not mutate the database to make it look successful. A replacement chain can separately prove that the current shared artifact is accepted.

Report both states explicitly:

```text
historical composite: blocked/stale evidence
active replacement chain: Dev → Functional QA → Global QA → Synthesizer
recovered artifact acceptance: pass/fail from the replacement gates
```

After rewiring, archive or mark superseded branches and their held descendants. User-facing status should name exactly one active chain instead of counting every historical `todo` card as current work.

## Checklist synchronization

Do not leave a long external checklist at its initial state until the final gate. After independent QA proves a criterion, mark that criterion complete. Keep only unresolved integration or end-to-end items in progress. This makes repeated status requests truthful without implying overall release acceptance.

## Hermetic packaging trap

Fixing the first failing nested package build is insufficient. Search the entire repository for every subprocess invocation of package builders, including tests that call `pip wheel`, `python -m build`, or equivalent.

For offline/hermetic wheel tests:

- use the same explicit no-build-isolation contract at every nested call;
- preserve artifact, entry-point, descriptor, and exclusion assertions;
- run each wheel test alone;
- run all wheel tests together;
- run the complete suite in the same isolated/no-network conditions;
- treat `focused pass + full-suite packaging failure` as a real unresolved integration gate.

A robust verification sequence is:

```text
1. repository-wide scan of nested build commands
2. exact packaging regression
3. all packaging regressions together
4. focused product/security matrix
5. full suite with zero failures
6. diff check
7. source/installed manifest parity
8. installed schema/status/smoke
9. protected dirty-path comparison
```

## Failure signatures and response

- **Audit QA fails before writer stops:** classify it as a baseline snapshot; create fresh QA after the stable handoff.
- **Recovery worker searches random directories:** add the absolute repo/plan/protected-path contract to the task immediately and to every subsequent generated card.
- **Composite blocked but recovery active:** preserve the blocked state; report the replacement chain as the active execution path.
- **Many superseded todo chains remain:** safely disconnect/archive them or label them historical; never present them as parallel active work.
- **One packaging test still contacts the network:** scan all nested build calls before another full-suite attempt; do not patch failures one call at a time.
