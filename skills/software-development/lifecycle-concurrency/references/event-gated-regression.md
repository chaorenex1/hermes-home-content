# Event-gated non-blocking regression

Use a blocking callback under test control instead of `sleep()`.

```python
started = threading.Event()
release = threading.Event()

def slow_work(*_args):
    started.set()
    assert release.wait(timeout=2)
    raise RuntimeError("transient")  # exercise existing retry path

owner = make_owner(callback=slow_work)
started_at = time.monotonic()
try:
    owner.on_event(...)
    assert time.monotonic() - started_at < 0.25
    assert started.wait(timeout=1)
    assert persisted_status() == "running"
finally:
    release.set()

# For older synchronous expectations:
deadline = time.monotonic() + 1
while persisted_status() in {"pending", "running"} and time.monotonic() < deadline:
    time.sleep(0.01)
assert persisted_status() == "backoff"
```

Keep the deadline short and deterministic. The tested guarantee is that the host hook does not wait for the work, not a particular thread scheduling order.
