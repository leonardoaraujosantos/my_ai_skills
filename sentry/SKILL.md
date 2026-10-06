---
name: sentry
description: Add and operate Sentry error monitoring, tracing, profiling, logs, and session replay across Python (FastAPI/Django/Flask/Celery), JavaScript/TypeScript (browser, Node, Next.js, Svelte, WASM), Go, iOS/Apple, Android, Unity, and Unreal. Covers SDK install and init, DSN/secret handling, environments and releases, source-map and debug-symbol upload, PII scrubbing, sampling and quota tuning, and a stdlib-only test-event sender for verifying an install. Use when the user says "add Sentry", "instrument this app", "set up error tracking/monitoring", "why aren't my events showing up", "my stack traces are minified/unsymbolicated", "upload source maps/dSYMs/ProGuard mapping", "sentry-wizard", "sentry-cli", "tune traces_sample_rate", or "we're burning our Sentry quota".
argument-hint: [python|javascript|go|apple|android|games|operations] [topic]
---

# Sentry Skill

Instrument a project with Sentry correctly the first time: SDK init in the right place,
secrets out of source, readable stack traces, PII under control, and sampling that
doesn't torch the quota.

| Stack | Reference file |
|-------|----------------|
| Python — FastAPI, Django, Flask, Celery, AWS Lambda, plain scripts | `references/python.md` |
| JavaScript/TypeScript — browser, Node, Next.js, Svelte/SvelteKit, WASM | `references/javascript.md` |
| Go — net/http, Gin, Echo, Fiber, gRPC | `references/go.md` |
| iOS / macOS / tvOS / watchOS / visionOS (Swift, Obj-C) | `references/apple.md` |
| Android (Kotlin/Java, Gradle plugin) | `references/android.md` |
| Unity, Unreal Engine | `references/games.md` |
| Releases, source maps, debug symbols, CI, alerts, quota, self-hosted | `references/operations.md` |

**How to use this skill:** identify the stack, read the matching reference file
*before* writing any code, then read `references/operations.md` — every install is
only half-done until releases and symbol upload work. For a multi-service app
(e.g. FastAPI backend + Next.js frontend), read both platform files plus operations,
and use **one Sentry project per deployable**, not one per repo.

SDK APIs move fast. The snippets here were captured from
[docs.sentry.io](https://docs.sentry.io/platforms/) in August 2026. For anything
version-sensitive (option names, integration names, plugin versions), confirm against
live docs — append `.md` to any Sentry docs URL for a clean Markdown version
(e.g. `https://docs.sentry.io/platforms/python/integrations/fastapi.md`), or use the
**context7 MCP**.

---

## Golden rules

1. **Init before anything else.** `sentry_sdk.init()` / `Sentry.init()` /
   `SentrySDK.start` must run before the app object, framework, or router is
   constructed — otherwise auto-instrumentation patches nothing and you get errors
   without transactions. On iOS that means `application:didFinishLaunchingWithOptions:`
   or the SwiftUI `App.init()`; on Next.js it means `instrumentation.ts`.
2. **The DSN is config, not a constant.** Read it from an env var
   (`SENTRY_DSN`, `NEXT_PUBLIC_SENTRY_DSN`, `io.sentry.dsn` manifest entry). A DSN is
   write-only and safe to ship in a client bundle, but hardcoding it makes staging
   events land in the production project — which is the actual failure mode.
   **Never** put an auth token (`sntrys_…`, `SENTRY_AUTH_TOKEN`) in source or a client
   bundle; those are read/write and belong in CI secrets and `.gitignore`.
3. **Set `environment` and `release` on every init.** Without them you cannot tell
   staging noise from production incidents, regressions are undetectable, and
   source maps/symbols won't match. `release` must be identical between the running
   app and the artifact upload.
4. **No symbols, no value.** A JS install isn't done until source maps upload; iOS
   until dSYMs upload; Android until the ProGuard/R8 mapping uploads. Verify by
   looking at a real stack trace in the UI, not by the absence of build errors.
5. **Decide PII deliberately.** `send_default_pii=True` attaches request headers,
   cookies, body, and user IP. That is often what you want — and is illegal for some
   data. Turn it on only with scrubbing configured (`before_send`, `denyList`,
   session-replay masking, which is on by default). See `references/operations.md`.
6. **Sample tracing, not errors.** Errors are cheap and always wanted;
   `traces_sample_rate: 1.0` in production is the #1 cause of blown quota. Ship
   `1.0` in dev, `0.05–0.2` in production, and use a `traces_sampler` to drop health
   checks entirely. Profiling multiplies transaction volume — sample it lower still.
7. **Flush before exit.** Short-lived processes (CLI tools, Go binaries, Lambdas,
   scripts) must flush or the buffered event is lost:
   `sentry.Flush(2*time.Second)` in Go, `sentry_sdk.flush()` in Python.
8. **Don't double-report.** Framework integrations already capture unhandled
   exceptions. An extra `capture_exception` inside a global handler produces two
   issues for one failure.
9. **One project per deployable, tags for the rest.** Split by app/service
   (`api`, `web`, `ios`), not by feature. Use tags/`environment` for finer slicing.
10. **Verify with a deliberate error, then delete the route.** The `/sentry-debug`
    style endpoint is a test fixture, not a shipping feature.

---

## Standard workflow

Follow this order; steps 5–7 are the ones people skip and then file "Sentry doesn't work".

1. **Detect the stack.** Look at `pyproject.toml`/`requirements.txt`, `package.json`,
   `go.mod`, `*.xcodeproj`/`Package.swift`, `build.gradle*`, `*.uproject`,
   `Packages/manifest.json`. In a monorepo, enumerate every deployable.
2. **Get or create the DSN.** Ask the user for it, or read an existing `SENTRY_DSN`
   from the environment / deployment config. Never invent one.
3. **Install the SDK and init early** — see the platform reference. Prefer the
   official wizard where one exists (`npx @sentry/wizard@latest -i <platform>`,
   `sentry-wizard -i ios`); it also wires up symbol upload, which hand-rolling misses.
4. **Wire `environment`, `release`, and sampling** from env vars, not literals.
5. **Enable symbol/source-map upload** in the build (`references/operations.md`).
6. **Configure scrubbing** if `sendDefaultPii` is on.
7. **Verify end-to-end**: trigger one deliberate error, confirm it appears in the UI
   *with a readable stack trace*, confirm the release and environment tags are right,
   then remove the trigger.
8. **Document it**: note the env vars in the project README/`.env.example` and, in
   repos with an `openspec/` directory, spec the change through OpenSpec first —
   observability config touches deployment and data handling.

---

## Sampling defaults to start from

Tune from real volume after a week; these are safe starting points.

| Option | Dev | Production | Notes |
|--------|-----|------------|-------|
| error capture | always | always | Not sampled by default; leave it that way. |
| `traces_sample_rate` | `1.0` | `0.1` | Low-traffic internal service: `1.0` is fine. High-traffic API: `0.01–0.05`. |
| `profile_session_sample_rate` / `profilesSampleRate` | `1.0` | `0.1` | Fraction *of sampled traces*, so it compounds. |
| `replaysSessionSampleRate` (JS) | `1.0` | `0.01–0.1` | Replay is the most expensive product per event. |
| `replaysOnErrorSampleRate` (JS) | `1.0` | `1.0` | Cheap and the highest-value replay. |
| `enableLogs` / `enable_logs` | `true` | `true` | Then control volume at the logger level, not here. |

Prefer a `traces_sampler` function over a flat rate as soon as you have noisy
endpoints — drop `/health`, `/metrics`, and static assets to `0.0` and spend the
budget on checkout/auth paths.

---

## Fast triage

| Symptom | Where to look |
|---------|---------------|
| No events at all | DSN typo/wrong project; init never ran (called after app construction, or module never imported); process exited before flush; ad-blocker eating the browser request → `tunnelRoute` in `references/javascript.md` |
| Errors arrive, no transactions | `traces_sample_rate` unset or `0`; init ran after the framework was created so nothing got patched |
| Stack trace is minified/obfuscated | Source maps / dSYMs / ProGuard mapping not uploaded, or uploaded under a different `release` — `references/operations.md` |
| Events tagged wrong environment | `environment` hardcoded or falling back to `production` by default |
| Quota exhausted mid-month | `traces_sample_rate: 1.0`, replay session sampling too high, or a hot loop capturing the same handled exception — see quota section in `references/operations.md` |
| Duplicate issues for one failure | Manual `capture_exception` on top of an integration that already reports |
| PII showing up in issues | `send_default_pii` on without `before_send` scrubbing; check server-side scrubbing rules too |
| iOS crashes never appear | App was run with the debugger attached; SDK started off the main thread; dSYMs missing |
| Next.js server errors missing | `onRequestError = Sentry.captureRequestError` not exported from `instrumentation.ts` |

---

## Test-event sender

`scripts/send_test_event.py` posts an event straight to the Sentry envelope endpoint
using only the Python stdlib — no SDK, no project changes. Use it to prove a DSN is
valid and reachable *before* blaming the instrumentation.

```bash
# DSN from $SENTRY_DSN
python3 ~/.claude/skills/sentry/scripts/send_test_event.py

# or explicitly, with tags
python3 ~/.claude/skills/sentry/scripts/send_test_event.py \
  --dsn "https://<key>@o<org>.ingest.de.sentry.io/<project>" \
  --message "connectivity check from laptop" \
  --environment staging --release "api@1.4.2" --level warning
```

It prints the parsed DSN components, the target URL, the HTTP status, and the
`event_id` to search for in the UI. A `200` here plus nothing in the UI means the
project is inbound-filtering or rate-limiting the event, not that the network is broken.
