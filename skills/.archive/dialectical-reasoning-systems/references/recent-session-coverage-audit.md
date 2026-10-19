# Recent Session Coverage Audit — July 2026

## Purpose

This reference records the concrete evidence that motivated the class-level workflow in `dialectical-reasoning-systems`. Treat the values as a dated baseline, not permanent product behavior.

## Runtime Snapshot

Source: profile-local LanceDB memory metadata and dialectical profile artifacts, covering approximately `2026-07-28T09:18:27Z` through `2026-07-30T11:00:36Z`.

| Measure | Baseline |
|---|---:|
| Dialectical jobs | 39 |
| Completed | 15 / 39 = 38.5% |
| Failed | 24 / 39 = 61.5% |
| Generic `DialecticalValidationError` | 22 / 39 = 56.4% |
| Startup-recovery terminalization | 2 / 39 = 5.1% |
| Successful runs using more than one round | 0 / 15 |
| Resolved injection receipts adopted | 6 / 20 = 30.0% |
| Insight-level adoption | 25 / 87 = 28.7% |
| Active profile insights | 79 |
| Active insights supported only by assistant text | 61 / 79 = 77.2% |
| Active insights containing user evidence | 18 / 79 = 22.8% |
| Active insight categories | 67 fact, 12 goal, 0 preference/habit |
| Retired insights | 2, versus 79 still active |

The completed runs all ended after one round with `sufficient=true`. This does not prove every one-round result was wrong, but it provides no evidence that the advertised second/third-round challenge path was exercised.

The then-current reasoner contract requested state fields—session summary, user representation, profile card, active focus, observations, conclusions, and working-set operations—but no first-class thesis, challenge, evidence comparison, or resolution object. This made semantic opposition coverage unobservable.

## Replay Anchors

Use the exact session windows and actual artifacts when constructing a replay set. Message IDs are stable anchors; do not judge from these summaries alone.

### Scope boundary was detected after mutation

- Session: `@session:default/20260715_121108_578d5f`
- Messages: `21951–21955`, `21958`, `21960`
- Pattern: annual-report design was written into a Ralph plan before the user clarified that the question was outside plan scope; the edit then required rollback.
- Expected trigger: `scope_conflict`.
- Expected pre-action synthesis: answer the analysis question without modifying the plan.

### Observer authority was misinterpreted

- Session: `@session:default/20260722_193640_178c94`
- Messages: `36473`, `36474`, subsequent task-state reads
- Pattern: the assistant concluded observers/controllers should stop and direct development should begin; the user clarified that the observer should diagnose and automatically repair the blocked state.
- Expected trigger: `role_authority_conflict`.
- Expected behavior: inspect the bound task contract and live graph before changing the control strategy.

### Explicit equality was over-engineered into an alias layer

- Session: `@session:default/20260728_220847_ddf4fe`
- Messages: `51564`, `51567`, `52037`, `52095`
- Pattern: `ceo is cto` was reinterpreted as logical CEO → physical CTO, with extra configuration and an unwanted `opsprotocol` lane. A later correction removed the abstraction.
- Expected trigger: `explicit_definition_correction`.
- Safety counterexample in the same window: the request for worktree deletion without preconditions should not silently erase path/ownership safety invariants.

### Independent review found the material counterexample

- Session: `@session:default/20260729_003610_d8958d`
- Messages: `52381`, `53149`, `53185`, `53191`
- Pattern: resolving Windows npm/NVM `.cmd` shims through the parent process PATH was incomplete; an independent review showed that the final child `spawn_env["PATH"]` could select a different Codex binary. A RED regression and explicit PATH parameter closed the issue.
- Expected trigger: `reviewer_counterexample`.
- This session had five dialectical jobs and no successful dialectical run; the effective opposition came from independent code review.

### File validation did not verify runtime semantics

- Session: `@session:default/20260730_172922_20e133`
- Messages: `53919`, `53924`, later runtime inspection and `54016`
- Pattern: 17 Profile SOUL files passed content checks, but the actual Native Swarm automatic runtime used 11 execution Profiles and assigned different write semantics to `opsconfig` and `opsdocs`.
- Expected trigger: `artifact_vs_runtime_conflict`.
- Expected behavior: establish the live role/phase/permission matrix before mutating role contracts.

### User-profile epistemic status improved only after repeated output

- Session: `@session:default/20260714_221912_fe01a5a6`
- Messages: `53881`, `53921`, `53923`
- Pattern: early profile versions promoted proposed recommendation architecture and assistant inferences; the third version separated confirmed goals, proposed-but-unconfirmed designs, and unknowns.
- Expected trigger: `profile_evidence_boundary`.
- Expected state operation: narrow or retire unsupported profile claims rather than append another high-confidence fact.

### Positive control: verified evidence overturned the premise

- Session: `@session:default/20260714_221912_fe01a5a6`
- Messages: `20568`, `20574`
- Pattern: a task title asserted Windows 10, while live WMI evidence showed Windows 11 Build 26200. The assistant corrected the premise and exposed WMI uncertainty around GPU memory and storage-interface labels.
- Expected outcome: valid evidence-grounded correction; a replay evaluator should pass this behavior.

### Completion status was not equivalent to successful extraction

- Session: `@session:default/20260729_112740_f4ccde`
- Messages: `53618`, `53774`
- Pattern: jobs labeled `completed` had produced no candidate or promotion input; later work separated `completed`, `completed_empty`, `rejected`, and `failed`, and changed checkpoint identity from session-level to job-level.
- Expected trigger: `status_semantics_conflict`.
- Expected behavior: inspect downstream artifacts before accepting a status label as proof.

## Evaluation Use

For each anchor, freeze a bounded message window and any cited artifact bytes. Independent reviewers should label:

- eligibility and trigger type;
- severity;
- thesis and strongest non-strawman challenge;
- authority and evidence for each atomic claim;
- required state operation;
- acceptable synthesis;
- residual uncertainty;
- forbidden premature action.

Include routine negative controls so trigger precision is measurable. Keep current-turn decision coverage separate from post-turn memory-reconciliation coverage.

## Dated Improvement Targets

These are rollout targets, not timeless invariants:

- structured run completion at least 95%;
- high-severity trigger recall at least 90%;
- explicit user-correction recall at least 98%;
- non-strawman opposition pass rate at least 90% on eligible high-risk cases;
- critical-claim evidence coverage at least 90%;
- required state-revision correctness at least 95%;
- assistant-only stable profile facts below 5%;
- opportunity-aware injection adoption at least 60% before broad rollout.

Do not optimize these in isolation. User correction rate, unsafe synthesis, cost, latency, and irrelevant-trigger rate must pass simultaneously.
