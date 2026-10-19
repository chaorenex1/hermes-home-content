# Kanban Swarm controller policy

The swarm controller is deterministic and runs independently of model judgment.

## Required gates
- All worker cards must be done before verification can pass.
- Every verifier must finish with `metadata.gate = "pass"`.
- A synthesizer must finish with outcome `completed`, non-empty summary, and JSON metadata.
- Missing tasks, blocked workers, failed gates, or incomplete synthesis block the swarm and prevent success notification.

## Creator notifications
The root task's gateway subscription is the creator notification channel. The controller emits `swarm_progress`, `swarm_gate_failed`, `swarm_blocked`, and `swarm_completed` events on the root card. Gateway sends these events to the subscribed creator chat.

Progress is event-based, not heartbeat-based, to avoid message flooding. The controller runs every five minutes.

## Worker contract
Workers report machine-readable facts in completion metadata. The verifier must explicitly set `gate` to `pass` only after reviewing all worker handoffs. The synthesizer must include a final summary, metadata, unresolved risks, and deliverable references.
