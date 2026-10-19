# Swarm notification and recovery lessons

## Failure modes observed

### Automatic repair
A health/failure script that only prints new `crashed` or `timed_out` events is an alert reporter, not an auto-repair controller. For transient worker loss, it must invoke the supported Dispatcher/re-dispatch path and respect the task's retry budget. Never auto-unblock `needs_input`, `capability`, or other human-gated states; those require notification and escalation.

### Creator routing
A CLI/cron-created task has no creator chat context. It cannot prove notification delivery. Gateway-created tasks must capture session ContextVars, not just process environment variables. The minimum durable target is platform, chat_id, chat_type, thread_id, user_id, and notifier_profile.

For Feishu, a group-origin message has a group chat_id and the creator's open_id. If private notification is required, send to the creator open_id; do not reuse the group chat_id. DM-origin tasks keep their DM chat_id. Never hard-code `chat_type="group"` when reconstructing a notification session.

### Swarm root lifecycle
The Swarm topology helper marks the Root/Blackboard task done immediately. Treat that as topology initialization, not workflow completion. Keep the Root subscription until a root-level `swarm_completed` or `swarm_blocked` event.

### Cron health jobs
A no-agent cron job may be running successfully while appearing silent if its script emits empty stdout. Health checks should emit a compact status payload even when there are no new failures. `deliver: local` or local cron output is not a Gateway chat notification; choose an explicit messaging destination for user-visible alerts.

## Verification order

1. Inspect subscription rows and target fields.
2. Confirm event rows exist.
3. Confirm notification cursor advances.
4. Inspect Gateway notifier delivery/send-failure logs.
5. Verify the actual target chat.
6. Restart Gateway only from an external shell after source changes; self-restart from inside the Gateway is blocked by design.
