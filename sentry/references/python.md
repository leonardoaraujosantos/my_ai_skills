# Sentry — Python

Docs: https://docs.sentry.io/platforms/python/ (append `.md` to any page for Markdown).

## Install

```bash
pip install "sentry-sdk"
# framework extras are optional — the integration activates if the package is importable
pip install "sentry-sdk[fastapi]"   # or [django], [flask], [celery], [asyncpg], ...
```

Add `sentry-sdk` to `pyproject.toml` / `requirements.txt` — pin a major
(`sentry-sdk>=2,<3`) so a major bump doesn't silently change option names.

## Init — the shape to use everywhere

```python
import os
import sentry_sdk

sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),          # None disables the SDK cleanly — good for local dev
    environment=os.environ.get("SENTRY_ENVIRONMENT", "development"),
    release=os.environ.get("SENTRY_RELEASE"),  # e.g. "api@1.4.2" — must match the artifact upload
    # Request headers, cookies, body and user IP. Requires scrubbing — see operations.md.
    send_default_pii=True,
    enable_logs=True,
    traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
    profile_session_sample_rate=float(os.environ.get("SENTRY_PROFILES_SAMPLE_RATE", "0.1")),
    profile_lifecycle="trace",                 # profile only while a transaction is active
)
```

`dsn=None` (or unset env var) makes every SDK call a no-op — that is the correct way
to disable Sentry in tests and local dev, not wrapping calls in `if PROD`.

Auto-enabled integrations activate purely from installed packages: FastAPI, Starlette,
Django, Flask, Celery, Redis, SQLAlchemy, asyncpg, httpx, boto3, logging, and more.
You rarely need to list `integrations=[...]` — do it only to configure one
(e.g. `LoggingIntegration(level=..., event_level=...)`) or to disable defaults.

---

## FastAPI

The FastAPI integration is enabled automatically when `fastapi` is installed.
**Init before the `FastAPI()` object is created.**

```python
from fastapi import FastAPI
import sentry_sdk

sentry_sdk.init(
    dsn="https://<key>@o<orgId>.ingest.sentry.io/<projectId>",
    send_default_pii=True,
    enable_logs=True,
    traces_sample_rate=1.0,
    profile_session_sample_rate=1.0,
    profile_lifecycle="trace",
)

app = FastAPI()
```

In a project laid out as `app/main.py`, put the `init` at the very top of the module
that creates the app, above the `FastAPI()` call — not in a router, not in a
`startup` event handler (too late for import-time errors).

Under Gunicorn/Uvicorn workers each worker process initializes independently; the
module-level init above is per-worker and correct.

### Verify

```python
@app.get("/sentry-debug")
async def trigger_error():
    division_by_zero = 1 / 0
```

Hit `http://localhost:8000/sentry-debug/`. You get both an error event and a
transaction, linked. Delete the route once confirmed.

---

## Django

```bash
pip install "sentry-sdk[django]"
```

Init at the bottom of `settings.py` (after `DEBUG`/env loading), or in `wsgi.py`/`asgi.py`
before `get_wsgi_application()`:

```python
import sentry_sdk

sentry_sdk.init(
    dsn=os.environ["SENTRY_DSN"],
    environment=ENVIRONMENT,
    release=os.environ.get("SENTRY_RELEASE"),
    send_default_pii=True,
    enable_logs=True,
    traces_sample_rate=0.1,
)
```

The integration covers middleware spans, DB query spans, template rendering, signals,
and the `django.request` logger. Don't add a custom 500 handler that re-captures —
you'll get duplicates.

---

## Flask

```bash
pip install "sentry-sdk[flask]"
```

Init before `Flask(__name__)`. Same option block. Blueprint routes are covered
automatically; `app.errorhandler` handlers that swallow the exception suppress the
event — re-raise or `capture_exception` explicitly there.

---

## Celery

```bash
pip install "sentry-sdk[celery]"
```

Init inside the worker bootstrap. With Celery, initialize in the
`celeryd_init`/`beat_init` signal so forked workers each get a client:

```python
from celery.signals import celeryd_init

@celeryd_init.connect
def init_sentry(**_kwargs):
    sentry_sdk.init(dsn=..., traces_sample_rate=0.1, enable_logs=True)
```

Traces propagate from the web request into the task automatically, so a slow job shows
up under the request that queued it.

---

## Short-lived processes (scripts, CLI, Lambda)

Buffered events are lost if the process exits first:

```python
try:
    main()
finally:
    sentry_sdk.flush(timeout=2.0)
```

For AWS Lambda use the `AwsLambdaIntegration` (auto-enabled) — it flushes at the end of
each invocation. `sentry_sdk.init()` goes at module scope, outside the handler, so it
survives warm starts.

---

## Logs

Two paths, both fine together:

```python
import sentry_sdk

sentry_sdk.logger.info("This is an info log message")
sentry_sdk.logger.warning("This is a warning message")
sentry_sdk.logger.error("This is an error message")
```

The stdlib `logging` module is forwarded automatically when `enable_logs=True`:

```python
import logging

logger = logging.getLogger(__name__)

logger.info("This will be sent to Sentry")
logger.warning("User login failed")
logger.error("Something went wrong")
```

By default the `LoggingIntegration` also turns `logger.error(...)` and above into
breadcrumbs/events. If that duplicates your explicit `capture_exception` calls, tune it:

```python
from sentry_sdk.integrations.logging import LoggingIntegration

sentry_sdk.init(
    # ...
    integrations=[LoggingIntegration(level=logging.INFO, event_level=None)],
)
```

Keep log volume under control at the logger level (log levels, sampling in your own
code) — `enable_logs` has no rate knob.

## Metrics

```python
from sentry_sdk import metrics

metrics.count("checkout.failed", 1)
metrics.gauge("queue.depth", 42)
metrics.distribution("cart.amount_usd", 187.5)
```

Keep tag cardinality low — a tag per user ID will be dropped or will cost you.

---

## Manual capture and context

```python
import sentry_sdk

try:
    risky()
except ValueError as exc:
    sentry_sdk.capture_exception(exc)

sentry_sdk.capture_message("cache rebuild took too long", level="warning")

sentry_sdk.set_user({"id": user.id, "email": user.email})   # respect PII policy
sentry_sdk.set_tag("tenant", tenant.slug)
sentry_sdk.set_context("job", {"batch_id": batch.id, "size": len(rows)})

with sentry_sdk.start_span(op="db.migrate", name="backfill_orders"):
    backfill()
```

Use `sentry_sdk.new_scope()` (context manager) to keep tags/user scoped to one block
instead of leaking into every later event on the same thread.

## Filtering before send

```python
def before_send(event, hint):
    exc = (hint or {}).get("exc_info", (None, None, None))[1]
    if isinstance(exc, ClientDisconnected):
        return None                      # drop entirely
    request = event.get("request", {})
    if "authorization" in request.get("headers", {}):
        request["headers"]["authorization"] = "[Filtered]"
    return event

sentry_sdk.init(dsn=..., before_send=before_send)
```

`ignore_errors=[KeyboardInterrupt, ClientDisconnected]` handles the simple cases
without a callback.

## Sampling by route

```python
def traces_sampler(ctx):
    path = ctx.get("asgi_scope", {}).get("path", "")
    if path in ("/health", "/metrics", "/readyz"):
        return 0.0
    if path.startswith("/api/checkout"):
        return 1.0
    return 0.05

sentry_sdk.init(dsn=..., traces_sampler=traces_sampler)
```

`traces_sampler` wins over `traces_sample_rate`; define only one.

## Testing

Assert on captured events without a network call:

```python
import sentry_sdk
from sentry_sdk.transport import Transport

class CapturingTransport(Transport):
    def __init__(self):
        super().__init__()
        self.events = []
    def capture_envelope(self, envelope):
        self.events.append(envelope)

transport = CapturingTransport()
sentry_sdk.init(dsn="https://key@example.invalid/1", transport=transport)
```

Simpler still: leave `dsn` unset in the test settings so the SDK is inert, and only
spin up the capturing transport in the one test that asserts reporting behavior.
