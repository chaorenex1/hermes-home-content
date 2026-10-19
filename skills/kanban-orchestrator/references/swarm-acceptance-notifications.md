# Swarm acceptance and creator-notification implementation notes

## Durable controller contract

The deterministic controller can run as a no-agent cron script. It reads the Kanban SQLite board, identifies Swarm roots from the topology Blackboard comment, and emits idempotent root-level events:

- `swarm_progress`
- `swarm_workers_ready_for_verification`
- `swarm_gate_failed`
- `swarm_blocked`
- `swarm_completed`

Hard checks:

1. Root topology references existing Worker, Verifier, and Synthesizer cards.
2. Every Worker is `done` and its latest run has `outcome=completed`, non-empty `summary`, and JSON metadata.
3. Verifier is accepted only when latest metadata contains `gate: pass`.
4. Synthesizer is accepted only with `outcome=completed`, non-empty summary, and JSON metadata.
5. Gate failures block downstream work and must not emit success.

Event insertion must be idempotent, because a five-minute controller will inspect the same roots repeatedly. Use a stable payload and check for an existing `(task_id, kind, payload)` before inserting.

## Creator notification contract

The Gateway notifier must claim the root subscription's event cursor and render Swarm lifecycle events. Recommended user-visible events are creation, progress, gate failure, block, and completion. Consume internal events silently so they cannot wedge later events. Keep subscription cursors and delivery retries intact; a subscription disappearing after a genuinely final task is expected only after cursor advancement and delivery.

Do not confuse local cron output with chat delivery. To reach the creator, the task must be created from a Gateway session (or explicitly subscribed) and the dispatch-owning Gateway must be running its Kanban notifier watcher.

## Verification recipe

1. Create a two-worker Swarm with a verifier and synthesizer.
2. Dispatch and verify both workers run in parallel.
3. Run the controller and confirm `swarm_progress`.
4. Confirm the verifier starts only after both workers complete.
5. Confirm the verifier's `gate=pass` unlocks the synthesizer.
6. Confirm the synthesizer completion creates `swarm_completed`.
7. For a negative test, remove/omit a worker handoff or set a non-pass gate; confirm a gate-failure/block event and no success event.
8. Separately verify subscription target, event row, cursor advancement, Gateway log, and actual chat delivery.

## Known design boundary

The topology helper may mark the planning root `done` immediately because it is also a Blackboard. Treat that as planning completion, not whole-Swarm completion; use root-level Swarm events for workflow status.
