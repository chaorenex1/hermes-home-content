---
name: privacy-safe-observability
description: Design, implement, and verify useful application diagnostics without leaking user content, identifiers, paths, secrets, or exception payloads. Use for debug logging, lifecycle instrumentation, background-worker visibility, and log-safety reviews.
version: 1.0.0
author: Masia
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [observability, logging, privacy, debugging, testing]
    related_skills: [test-driven-development, systematic-debugging]
---

# Privacy-Safe Observability

Build logs that answer “what happened, where, and what state changed?” without copying the data being processed into the log stream.

## When to Use

- Adding DEBUG/INFO/WARNING events to a service, provider, plugin, scheduler, queue, or lifecycle hook
- Diagnosing silent failures hidden by intentional exception handling
- Instrumenting asynchronous workers, retries, timers, or stale-result fencing
- Reviewing logs for private-content, secret, path, or identifier leakage
- Adding tests for logging behavior

## Core Contract

Every event should provide:

1. A stable machine-searchable event name, such as `provider.prefetch_completed`
2. Safe correlation, usually a deterministic short hash rather than a raw user/session identifier
3. Bounded structural metadata: counts, booleans, generation/attempt numbers, states, durations, and exception class names
4. No raw payload, secret, user message, query, memory body, tool argument, host path, or exception message

DEBUG is not a secrecy boundary. Anything unsafe at INFO is also unsafe at DEBUG.

## Implementation Workflow

### 1. Map the state transitions

Instrument transitions rather than every line:

- initialized / shutdown
- queued / consumed / completed
- scheduled / started / completed
- switched / cancelled / superseded
- retrying / exhausted / failed
- stale result discarded / result applied

For background work, always cover both the success and caught-error path. An exception that is intentionally swallowed still needs a sanitized diagnostic event.

### 2. Define a stable event vocabulary

Use lowercase dotted names:

```text
<component>.<operation>_<transition>
provider.prefetch_queued
provider.prefetch_completed
provider.prefetch_failed
```

Keep field names stable. Prefer `error_type`, `result_count`, `message_count`, `generation`, `applied`, and `checkpoint_status` over free-form prose.

### 3. Correlate without disclosure

Hash private identifiers before logging:

```python
session_debug_id = hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:12]
```

A short hash is for correlation only, not authentication. Do not hash low-entropy secrets and assume they are safe; omit them entirely.

### 4. Sanitize failures

For expected caught failures, log the class—not the message:

```python
except EXPECTED_ERRORS as exc:
    logger.debug(
        "provider.operation_failed session=%s error_type=%s",
        session_debug_id,
        type(exc).__name__,
    )
    return
```

Use `exc_info=True` only when the stack and exception text have been reviewed as safe for that deployment. Library/plugin code should generally avoid configuring root handlers or log levels; emit through a module logger and let the host decide visibility.

### 5. Test first

Use RED → GREEN for logging behavior:

- Seed unmistakable private sentinel strings
- Capture logs at the target logger and level
- Assert stable event names and safe structural fields
- Assert every sentinel is absent
- Exercise both success and swallowed-error paths

Do not assert the entire formatted line. Exact-line assertions are brittle and discourage useful safe fields.

### 6. Handle asynchronous tests deterministically

A worker can finish before the test reads its thread/task handle. Capture the handle immediately when available and wait with a bound; if it is already gone, assert the observable event/state instead of requiring the internal handle to exist. Never use an unbounded join or arbitrary sleep as the primary synchronization mechanism.

### 7. Verify at increasing scope

1. New focused observability tests
2. Related lifecycle, scheduler, queue, and worker tests
3. Full suite
4. Syntax/diff checks for the touched paths

Use an interpreter-bound test command such as `python -m pytest` when a bare executable may resolve to a different Python environment than the source under test.

## Event Design Guide

| Situation | Useful safe fields | Avoid |
|---|---|---|
| Queue operation | generation, queue size, item count | payload, raw key |
| Retrieval | mode, result count, cached chars, applied | query, document body |
| Session lifecycle | short hash, turn, cancelled count | raw session ID, messages |
| Background failure | operation, attempt, exception class | exception message, traceback by default |
| Scheduler | checkpoint status, delay bucket, classifier configured | full timestamps tied to user data when unnecessary |
| Memory processing | action enum, target enum, character count | memory content, tool arguments |

## Pitfalls

1. **Success-only instrumentation** — the system is still opaque when the worker fails.
2. **Logging exception strings** — storage errors frequently contain absolute paths; validation errors may echo user input.
3. **Raw correlation IDs** — session, chat, document, and candidate IDs can be private even without content.
4. **Logging before validation** — malformed hostile input can reach logs unchanged.
5. **Over-instrumenting hot loops** — prefer one transition event with counts to per-item logs.
6. **Changing host logging configuration from a library** — emit records; do not seize global handlers or levels.
7. **Racy tests** — do not assert that a fast worker handle must still exist after dispatch.
8. **Using DEBUG as permission to leak** — log level controls volume, not data classification.

## Reference Files

- `references/memory-provider-lifecycle-logging.md` — worked event taxonomy and regression-test pattern for a provider with queues, prefetch, session switching, timers, and idle workers.
