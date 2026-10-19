# Ralph Lifecycle Ownership Invariants

Use this when reviewing or changing `hermes_cli.ralph` persistence and its TUI/CLI/tool surfaces.

## Canonical-state rule

A `plan_id` must have exactly one canonical lifecycle state. A detached record may be a routing pointer, but must never be an independently resumable clone of the plan state.

Required behavior:

1. `pause`, `clear`, and `archive` update or remove any detached alias atomically with the canonical plan.
2. Resuming a plan into another session transfers ownership (or rejects the operation); it must not leave both sessions `active` for the same `plan_id`.
3. Starting a new plan in a session with an active or awaiting-review plan must require an explicit replacement action (pause/clear/archive) rather than silently overwrite its state.
4. Search and archive must resolve a `plan_id` to one unambiguous canonical record.

## Regression probes

Run these as focused tests against a temporary `HERMES_HOME`:

- `start → pause → archive` leaves no paused detached copy that can be resumed.
- `resume(target, active_plan_id)` either transfers ownership or refuses; it never produces two active records with the same plan ID.
- `start(session, A) → start(session, B)` preserves A as an explicitly terminal/paused state or refuses B; A must remain searchable.
- Archive followed by an unqualified `resume` must not revive an archived plan through detached fallback.
