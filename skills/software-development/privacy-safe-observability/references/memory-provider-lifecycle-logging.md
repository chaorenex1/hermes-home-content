# Memory-provider lifecycle logging pattern

This reference captures a reusable instrumentation pattern for a profile-local provider that owns lifecycle hooks, bounded queues, background prefetch, temporary-memory observation, idle extraction, and session switching.

## Recommended event surface

```text
provider.initialized
provider.turn_started
provider.turn_sync_queued
provider.turn_sync_failed
provider.lifecycle_consumed
provider.prefetch_queued
provider.prefetch_completed
provider.prefetch_failed
provider.session_switched
provider.session_switch_failed
provider.session_end_queued
provider.session_end_queue_failed
provider.session_end_temp_clear_failed
provider.memory_write_mirrored
provider.memory_write_failed
provider.temp_observer_completed
provider.temp_observer_failed
provider.idle_extraction_scheduled
provider.idle_extraction_schedule_failed
provider.idle_extraction_completed
provider.idle_extraction_failed
provider.shutdown
```

This is a taxonomy example, not a mandatory global naming list. Preserve the target project's existing component vocabulary.

## Safe field choices

- `session`: first 12 hex characters of SHA-256 over the session ID
- `turn`, `generation`, `sequence`: bounded integers
- `message_count`, `result_count`, `cached_chars`, `content_chars`, `cancelled_work`: counts only
- `primary`, `enabled`, `applied`, `lineage`, `reset`, `rewound`, `classifier`: booleans
- `source`, `action`, `target`, `checkpoint_status`: validated controlled enums
- `error_type`: `type(exc).__name__`

Never include raw session IDs, user/assistant messages, retrieval queries, memory bodies, tool names/arguments, absolute profile paths, evidence contents, or exception messages.

## Regression-test shape

Create private sentinels that would be obvious if leaked:

```python
with caplog.at_level(logging.DEBUG, logger="plugin.provider"):
    provider.initialize("private-session-id", ...)
    provider.sync_turn("private user content", "private assistant content")
    provider.queue_prefetch("private retrieval query")
    provider.shutdown()

output = "\n".join(record.getMessage() for record in caplog.records)
assert "provider.turn_sync_queued" in output
assert "provider.prefetch_completed" in output
for secret in (
    "private-session-id",
    "private user content",
    "private assistant content",
    "private retrieval query",
):
    assert secret not in output
```

For swallowed exceptions, inject a distinctive exception message and require only its class:

```python
def fail(*args, **kwargs):
    raise ValueError("private failure text")

output = capture_operation(fail)
assert "provider.operation_failed" in output
assert "error_type=ValueError" in output
assert "private failure text" not in output
```

## Async test race

A very fast worker may set its stored thread reference back to `None` before the test reads it. This is not a production failure. Use:

```python
worker = provider._worker
if worker is not None:
    worker.join(timeout=3)
```

Then assert the completion/failure event or durable state. If precise synchronization is required, inject an event-controlled fake worker rather than sleeping.

## Verification sequence

```text
python -m pytest -q tests/test_debug_logging.py
python -m pytest -q <related lifecycle/scheduler/worker tests>
python -m pytest -q
git diff --check -- <touched paths>
```

The interpreter-bound pytest form is useful in multi-environment installations because it proves which interpreter imports the source under test; it is not a claim that a bare `pytest` executable is universally wrong.
