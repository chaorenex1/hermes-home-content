# Compression Health Check Recipe

Use this reference after loading the parent skill. It is a check-only recipe: it does not change configuration, rotate sessions, restart processes, or read message bodies.

## 1. Effective Configuration

Read only the keys that determine trigger timing and summary routing:

```bash
for key in \
  compression.enabled \
  compression.threshold \
  compression.threshold_tokens \
  compression.target_ratio \
  compression.abort_on_summary_failure \
  auxiliary.compression.provider \
  auxiliary.compression.model \
  model.context_length; do
  printf '%s=' "$key"
  hermes config get "$key"
done
```

Interpretation:

- `enabled` gates automatic compression, not an explicit `/compress`.
- `threshold_tokens` is an absolute upper trigger when set.
- A ratio is meaningful only against the effective input window after output reservation.
- Custom gateways may enforce a smaller window than model metadata. Treat observed provider behavior as the live contract.

## 2. Minimal Summary-Route Probe

Run from the Hermes source environment. This uses the configured `auxiliary.compression.*` route and prints no credentials or request payload:

```python
from agent.auxiliary_client import call_llm

response = call_llm(
    task="compression",
    messages=[{"role": "user", "content": "Reply with exactly OK."}],
    temperature=0,
    max_tokens=8,
    timeout=45,
)
choice = response.choices[0]
content = getattr(choice.message, "content", "") or ""
print("model=", response.model)
print("finish=", choice.finish_reason)
print("usable_content=", bool(content.strip()))
```

Pass criteria: a configured model is reported, the request stops normally, and content is non-empty. Do not treat the literal wording as a quality test.

## 3. Synthetic End-to-End Transform

Use generated text only. Keep the test context small enough to force a compressible middle without creating a huge provider request.

```python
from agent.context_compressor import (
    COMPRESSED_SUMMARY_METADATA_KEY,
    ContextCompressor,
    SUMMARY_PREFIX,
)
from agent.model_metadata import estimate_messages_tokens_rough

messages = []
for i in range(14):
    messages.append({
        "role": "user",
        "content": f"Synthetic request {i}. " + ("alpha beta gamma delta " * 150),
    })
    messages.append({
        "role": "assistant",
        "content": f"Synthetic result {i}. " + ("one two three four " * 150),
    })

before = estimate_messages_tokens_rough(messages)
compressor = ContextCompressor(
    model="compression-health-probe",
    threshold_percent=0.8,
    protect_first_n=1,
    protect_last_n=2,
    summary_target_ratio=0.1,
    quiet_mode=True,
    config_context_length=32768,
    abort_on_summary_failure=True,
)
compressed = compressor.compress(
    messages,
    current_tokens=before,
    focus_topic="continuity",
    force=True,
)
after = estimate_messages_tokens_rough(compressed)
summary_rows = [
    message for message in compressed
    if message.get(COMPRESSED_SUMMARY_METADATA_KEY)
]
alternation_ok = all(
    left.get("role") != right.get("role")
    for left, right in zip(compressed, compressed[1:])
)

print("before_messages=", len(messages))
print("after_messages=", len(compressed))
print("before_tokens_est=", before)
print("after_tokens_est=", after)
print("summary_rows=", len(summary_rows))
print("summary_prefix=", bool(
    summary_rows and SUMMARY_PREFIX in str(summary_rows[0].get("content", ""))
))
print("alternation_ok=", alternation_ok)
print("compression_count=", compressor.compression_count)
print("aborted=", compressor._last_compress_aborted)
print("fallback=", compressor._last_summary_fallback_used)
print("error_present=", bool(compressor._last_summary_error))
```

Pass criteria:

- after-counts are materially lower than before-counts;
- one summary row and the current prefix are present;
- role alternation is valid;
- compression count increments;
- no abort, fallback, or error is reported.

This probe intentionally does not test session leases, database rotation, resume, or the owning frontend process.

## 4. Focused Regression Set

Select existing tests by exact filename rather than a broad keyword over the whole repository. Cover these behaviors when present:

- manual CLI compression;
- focus-topic preservation;
- summary metadata and signal isolation;
- preflight trigger gates;
- provider/memory context handed to the summarizer;
- compression lineage guard;
- concurrent lock-skip behavior.

Example shape:

```bash
python -m pytest -q \
  tests/test_cli_manual_compress.py \
  tests/agent/test_compress_focus.py \
  tests/agent/test_compress_signal_leak.py \
  tests/agent/test_compressed_summary_metadata.py \
  tests/agent/test_preflight_compression_gate.py \
  tests/agent/test_pre_compress_memory_context.py \
  tests/state/test_compression_lineage_guard.py \
  tests/tui_gateway/test_compress_lock_skip.py
```

Adjust filenames to the checked-out revision. If a broad run times out, record it as incomplete and run a named subset to completion.

## 5. Privacy-Safe SessionDB Inspection

Resolve the active home through Hermes rather than hardcoding a profile path:

```python
import sqlite3
from hermes_cli.config import get_hermes_home

session_id = "<target-session-id>"
db_path = get_hermes_home() / "state.db"
connection = sqlite3.connect(db_path)

session_columns = {
    row[1] for row in connection.execute("PRAGMA table_info(sessions)")
}
message_columns = {
    row[1] for row in connection.execute("PRAGMA table_info(messages)")
}

wanted = [
    name for name in (
        "id", "source", "model", "parent_session_id", "started_at",
        "ended_at", "end_reason", "message_count",
        "compression_failure_cooldown_until", "compression_failure_error",
        "compression_fallback_streak", "compression_ineffective_count",
    )
    if name in session_columns
]
row = connection.execute(
    "SELECT " + ",".join(wanted) + " FROM sessions WHERE id=?",
    (session_id,),
).fetchone()
print(dict(zip(wanted, row)) if row else "session-not-found")

if "active" in message_columns:
    print("active_messages=", connection.execute(
        "SELECT count(*) FROM messages WHERE session_id=? AND active=1",
        (session_id,),
    ).fetchone()[0])
if "compacted" in message_columns:
    print("compacted_messages=", connection.execute(
        "SELECT count(*) FROM messages WHERE session_id=? AND compacted=1",
        (session_id,),
    ).fetchone()[0])

locks = connection.execute("SELECT count(*) FROM compression_locks").fetchone()[0]
print("current_compression_locks=", locks)
connection.close()
```

Do not select `messages.content`. Counts and lifecycle metadata are enough for the first diagnosis pass.

## 6. Log Correlation

Filter by the exact target session and bounded event classes:

```text
compression triggered
compression attempt telemetry
changed before lease acquisition
compression skipped due to lock
summary fallback / summary aborted
session rotated / child adopted
context length exceeded
post-compression real prompt usage
```

Rules:

1. Prefer one authoritative log stream.
2. If reading several logs, deduplicate by session, timestamp, and normalized event.
3. Exclude the time/session window of compression tests; failure-path tests intentionally emit fake quota, authentication, malformed-response, and timeout warnings.
4. Report a bounded error class, not raw provider payloads or private endpoints.

## 7. Verdict Template

```markdown
## Verdict: Healthy | Partially healthy | Unhealthy | Inconclusive

| Layer | Status | Evidence |
|---|---|---|
| Trigger policy | | |
| Summary backend | | |
| Transform | | |
| Orchestration | | |
| Persistence/resume | | |
| Next provider request | | |
| User-visible surface | | |

Changes made: none | <bounded list>
Remaining risk: <first unverified or failing layer>
```

“Healthy” requires a successful live post-compaction request and durable resume/readback. A passing synthetic transform with a failing live lease/rotation path is “Partially healthy.”
