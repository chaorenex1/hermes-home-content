# Profile-Learning Sample Yield Audit

Use this when a memory or user-profile system is being evaluated as a future source of contextual-bandit, preference-learning, or fine-tuning data. The central rule is: **count training contracts, not database rows or generated artifacts**.

## Sample classes

Keep these counts separate:

1. **Source interaction units** — completed user→assistant turns. These are the closest estimate of statistically independent source events.
2. **Behavior-cloning/SFT rows** — source turns that pass quality, privacy, and outcome filters. A stored turn is not automatically trainable.
3. **Weak semantic labels** — memory-analysis candidates, extracted subjects, inferred preferences, classifications, or evidence links. They can supervise extractors or enrich features, but they are not rewards.
4. **State snapshots** — profile documents, summaries, context generations, dynamic leaves, and versioned cards. They are model inputs or derived state, not independent examples.
5. **Contextual-bandit samples** — complete tuples such as `(context_snapshot, action_id, action_probability, outcome, reward, reward_evidence)`. Missing any decision or reward field means the count is zero.
6. **Pairwise preference samples** — complete `(prompt/context, chosen, rejected, preference_source)` pairs. Corrections or profile text alone do not form a DPO pair.
7. **Outcome/reward evidence** — explicit approval, correction, verification, success/failure, or another declared outcome. Silence is missing data, never a positive label.

## Procedure

1. Trace the production boundary that creates one durable record per completed turn. Confirm whether its status describes the conversation, the memory pipeline, or both; a memory-extraction failure does not necessarily invalidate the source interaction.
2. Read the structured-output schemas and prompts. Record per-turn maxima for candidates or staged artifacts, but label them as amplification bounds rather than independent-sample throughput.
3. Inspect the live store read-only. Capture a timestamp, integrity/status summary, source-turn counts, status distributions, receipt-derived candidate counts, context-generation counts, and artifact-type counts. Return counts only unless content inspection is necessary and authorized.
4. Search the live schema for decision/outcome tables and required fields. For a bandit, require context version, action identity, action probability/propensity, outcome, reward, and evidence. For DPO, require chosen/rejected alternatives bound to one context.
5. Compute three views separately:
   - **Current corpus:** what is already persisted.
   - **Per-turn theoretical yield:** what schemas permit.
   - **Usable training yield:** what satisfies the target learner's full contract after filtering.
6. Report effective sample size conservatively. Multiple candidates, summaries, or profile artifacts derived from one turn are correlated; use the source-turn count as the default independence ceiling unless the modeling design proves otherwise.
7. Distinguish workflow success from label quality. A completed extraction receipt proves pipeline completion, not preference correctness; a touched path is not one candidate and not one reward.
8. Account for live mutation. Label the snapshot time and avoid combining changing counts from different snapshots as one state.

## Worked interpretation pattern

A store may contain 30 source turns, 219 analysis candidates, 50 context generations, and 229 context artifacts while still containing **zero complete RL samples**. The correct interpretation is:

- at most 30 raw behavior-cloning source units before quality filtering;
- 219 correlated weak labels, bounded by the same 30 source events;
- 229 derived state versions useful as features or replay context, not 229 independent examples;
- zero contextual-bandit samples when no normalized action/reward tuples exist;
- zero DPO pairs when no chosen/rejected records exist.

Never sum heterogeneous counts into a headline sample total.

## Readiness guidance

- A contextual bandit can begin collecting immediately, but learning starts only after reward-bearing events exist. Report reward coverage and per-action coverage, not just turn volume.
- DPO readiness depends on independently justified preference pairs, not the number of memory documents or user-profile facts.
- Memory candidates can train or evaluate extraction/classification components separately. Do not silently reuse them as policy rewards.
- The profile store should remain factual/evidence state. Add a separate append-only decision/outcome ledger rather than treating profile writes as reward events.

## Report format

```text
live snapshot → source interaction units → weak labels → derived state versions
→ complete bandit tuples → complete preference pairs → per-turn yield
→ effective independence ceiling → learner readiness → missing instrumentation
```

For each number, state the table/receipt/schema source and whether it is raw, derived, weakly labeled, reward-bearing, or pairwise.