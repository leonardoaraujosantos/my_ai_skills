# Sentry — Go

Docs: https://docs.sentry.io/platforms/go/ (append `.md` for Markdown).

## Install

```shell
go get github.com/getsentry/sentry-go
```

Framework helpers are separate modules, e.g.:

```shell
go get github.com/getsentry/sentry-go/http     # net/http
go get github.com/getsentry/sentry-go/gin
go get github.com/getsentry/sentry-go/echo
go get github.com/getsentry/sentry-go/fiber
go get github.com/getsentry/sentry-go/otel     # OpenTelemetry bridge
```

Available integrations: **net/http, Gin, Echo, Fiber, Iris, Negroni, FastHTTP, gRPC**,
plus `logrus`/`slog`/`zerolog` log hooks.

## Init

```go
package main

import (
	"log"
	"os"
	"time"

	"github.com/getsentry/sentry-go"
)

func main() {
	err := sentry.Init(sentry.ClientOptions{
		Dsn:              os.Getenv("SENTRY_DSN"),
		Environment:      os.Getenv("SENTRY_ENVIRONMENT"),
		Release:          os.Getenv("SENTRY_RELEASE"),
		Debug:            true, // turn off once verified
		SendDefaultPII:   true,
		EnableTracing:    true,
		TracesSampleRate: 0.1,
	})
	if err != nil {
		log.Fatalf("sentry.Init: %s", err)
	}
	defer sentry.Flush(2 * time.Second)

	run()
}
```

**`defer sentry.Flush` is mandatory.** Go's SDK sends asynchronously; without a flush a
process that exits (or `os.Exit`, which skips defers entirely) drops the event that
explains why it exited. For a fatal path, flush explicitly before exiting:

```go
sentry.CaptureException(err)
sentry.Flush(2 * time.Second)
os.Exit(1)
```

An empty `Dsn` makes the SDK a no-op — the right way to disable it in tests.

## net/http

```go
import sentryhttp "github.com/getsentry/sentry-go/http"

sentryHandler := sentryhttp.New(sentryhttp.Options{
	Repanic: true,           // true when another middleware (or the server) recovers
	Timeout: 3 * time.Second,
})

http.Handle("/", sentryHandler.Handle(mux))
```

`Repanic: true` is almost always correct for a server: Sentry records the panic and
re-panics so your own recovery/logging still runs. `false` swallows the panic and
returns an empty 200 to the client.

## Gin

```go
import sentrygin "github.com/getsentry/sentry-go/gin"

router := gin.Default()
router.Use(sentrygin.New(sentrygin.Options{Repanic: true}))
```

Echo (`sentryecho`), Fiber (`sentryfiber`), Iris, Negroni, FastHTTP follow the same
`New(Options{...})` shape.

## Hubs, goroutines, and scope

The SDK's `Hub` is not goroutine-safe to share. Clone it per request/goroutine — the
framework middleware already does this and puts the hub on the request context:

```go
func handler(w http.ResponseWriter, r *http.Request) {
	hub := sentry.GetHubFromContext(r.Context())
	if hub == nil {
		hub = sentry.CurrentHub().Clone()
	}
	hub.Scope().SetTag("tenant", tenantFrom(r))
	hub.CaptureMessage("something noteworthy")
}
```

Spawning a goroutine from a request handler? Pass a cloned hub in, or the event lands
on the wrong scope (or races):

```go
go func(hub *sentry.Hub) {
	defer hub.Recover(nil)
	defer hub.Flush(2 * time.Second)
	doWork()
}(hub.Clone())
```

## Capture, context, tracing

```go
sentry.CaptureException(err)
sentry.CaptureMessage("cache rebuild took too long")

sentry.WithScope(func(scope *sentry.Scope) {
	scope.SetTag("job", "backfill")
	scope.SetLevel(sentry.LevelWarning)
	scope.SetContext("batch", map[string]interface{}{"id": batchID, "rows": len(rows)})
	sentry.CaptureException(err)
})

span := sentry.StartSpan(ctx, "db.migrate", sentry.WithDescription("backfill_orders"))
defer span.Finish()
```

Go errors carry no stack trace of their own. Wrap with `pkg/errors` (`errors.WithStack`)
or use `sentry.NewEvent` with an explicit stacktrace if your issues arrive with only a
one-frame trace at the capture site.

## Filtering and sampling

```go
sentry.ClientOptions{
	IgnoreErrors: []string{"context canceled", "client disconnected"},
	BeforeSend: func(event *sentry.Event, hint *sentry.EventHint) *sentry.Event {
		if event.Request != nil {
			delete(event.Request.Headers, "Authorization")
		}
		return event
	},
	TracesSampler: func(ctx sentry.SamplingContext) float64 {
		if ctx.Span != nil && strings.HasPrefix(ctx.Span.Name, "GET /health") {
			return 0.0
		}
		return 0.05
	},
}
```

`context canceled` from clients hanging up is the single noisiest Go event class — drop
it early.

## Build and release

Match `Release` to what you upload/deploy:

```bash
go build -ldflags "-X main.version=$(git rev-parse --short HEAD)" ./...
```

Go binaries are symbolicated from the compiled binary, so there's no source-map step —
but stripping (`-ldflags="-s -w"`) removes the information Sentry needs for readable
frames. Keep symbols in the build you ship, or upload debug files with
`sentry-cli debug-files upload`.
