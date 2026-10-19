# Sequential shared-worktree recovery after a Native Swarm failure

Use this recovery when a repository-backed Native Swarm has already produced useful edits, but the composite runtime cannot accept them because its completion/report contract or immutable-candidate contract was not satisfied and isolated branch commits were not authorized.

## Failure signature

Typical evidence is a combination of:

- Worker cards contain valid tests/artifacts but the composite runtime rejects a human-readable completion summary because it expected a strict JSON report envelope.
- Worker worktrees remain dirty because generic coding instructions correctly avoided unrequested commits, while runtime integration requires a clean immutable candidate SHA.
- Parallel Workers may have overlapping files or two implementations of the same boundary, so blindly copying every diff is unsafe.

This is an orchestration-contract failure, not proof that the implementation itself failed.

## Bounded recovery

1. Let every already-running Worker reach a terminal state; preserve worktrees, logs, comments, and test evidence.
2. Integrate the useful diffs into a separate clean checkout, not the user's original dirty checkout. Resolve overlaps explicitly and run a focused integration suite plus full regression.
3. When commits remain unauthorized, stop using the repository-backed Native runtime for this recovery. Create a sequential shared-directory chain instead:
   - one Dev writer card;
   - one independent QA card depending on that Dev card;
   - the next Dev stage depending on the QA card;
   - a final independent acceptance card and synthesizer.
4. Every Dev card must say `Do not commit`, must complete normally with changed files/tests/risks, and must not self-block merely because review is required.
5. If a finished Dev nevertheless self-blocks only for review, do not invent a SHA, mark it done, or generic-unblock it. Confirm the worker is terminal and its comment/log contains scoped changed files plus focused/full evidence. Then link a valid completed prior-stage/audit anchor to the independent verifier, read back both parents, unlink the blocked Dev, verify the Dev has no children, and archive it as preserved execution evidence. The verifier must inspect the actual shared worktree and remains the semantic gate.
6. Every QA card reads actual artifacts and runs independent probes. A semantic failure stays failed.
7. For a failed QA gate, create a materially changed Dev rework plus fresh independent QA. Link the replacement QA to every downstream child and verify both edges before unlinking the failed QA. Archive the failed QA only after its child list is empty.
8. Run exactly one dispatcher pass after graph repair and read back the replacement Dev, replacement QA, downstream parents, and archived failed gate.

## Monitoring rule

Treat monitor processes as graph-versioned controllers:

- Monitor the exact current chain IDs and exit on the first active `blocked` card or final synthesis completion.
- After rewiring the graph, terminate or supersede monitors that still contain old IDs.
- A delayed exit notification from an old monitor is historical evidence, not current-chain failure. Verify the monitor session ID and live task graph before reporting.

## Acceptance pitfall

A lightweight acceptance helper may only pattern-match criteria and can report `passed=true` even when the task itself is `blocked` with a semantic failure. Never let that boolean override:

1. live task status;
2. latest run outcome;
3. QA summary/metadata;
4. raw commands and artifact probes.

For QA, `blocked` or an explicit fail verdict is authoritative until a replacement QA independently passes.

## Stale composite state after accepted recovery

A replacement chain may end with all of the following true:

- replacement Functional QA and Global QA have `metadata.gate="pass"`;
- the Synthesizer is `done` with a substantive Blackboard handoff;
- the root queue card is `done` with final evidence;
- the original Native runtime is still historically blocked;
- the root's composite `swarm_state` still reads `running` because the recovery chain is outside the original runtime controller.

Handle this explicitly:

1. Inspect live CLI capabilities before assuming a state-repair command exists.
2. If no public composite-state setter exists, do not update Kanban SQLite directly.
3. Add a root audit comment that names the accepted replacement gates, the stale field, the historical runtime blocker, and the absence of a safe public repair path.
4. Report the implementation as **recovered delivery accepted**, not as successful completion of the original Native runtime.
5. Preserve the original runtime block and stale composite field as audit evidence.
6. Before user-facing completion, independently rerun one sufficient verification from the orchestrating session and inspect the final built artifact; do not rely on Worker/QA summaries alone.

This distinction prevents a stale UI field from invalidating a verified delivery while also preventing a false claim that the original composite runtime recovered.
