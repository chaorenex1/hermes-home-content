# SQLite lifecycle-state expansion: safe staged pattern

Use when a durable table has an existing constrained status column, event-history table, and callers that must distinguish a temporary state from terminal deletion.

## Decision point

Before changing the base status `CHECK`, inventory:

- foreign keys pointing to the base table;
- append-only triggers on historical events;
- all default-read queries and indexes that currently select `status = 'active'`;
- explicit resolution paths (clear, retain, revoke, expire, etc.).

If a table rebuild would be high-risk, add a narrow state table keyed by the original record ID:

```sql
CREATE TABLE item_transitional_state (
  item_id TEXT PRIMARY KEY REFERENCES items(item_id),
  observation_key TEXT NOT NULL UNIQUE,
  reason TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  resolved_at TEXT
);
```

Expose `effective_status` through a left join/case expression. Default retrieval must require both base active status and no unresolved transitional row. Resolution should set `resolved_at` and append an event rather than erase the state history.

## Required regression slices

1. Upgrade from the prior schema applies the monotonic migration and verifies required tables.
2. Marking a record transitional removes it from default recall/injection without deleting its canonical history.
3. Explicit keep/retain restores default visibility; explicit clear/terminal decision preserves audit history.
4. Repeated observations are deduplicated by a stable observation key.
5. Existing terminal states remain terminal and cannot be accidentally reactivated.

## Handoff format under interruption

Report only verified facts: exact RED/ GREEN commands, changed paths, migration version, the unimplemented next slice, and whether combined/full-suite verification remains outstanding.
