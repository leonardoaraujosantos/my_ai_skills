# Sentry — JavaScript / TypeScript

Docs: https://docs.sentry.io/platforms/javascript/ (append `.md` for Markdown).
Snippets below are from SDK v10.x (August 2026).

## Pick the right package

| Target | Package | Wizard |
|--------|---------|--------|
| Plain browser / Vite / vanilla | `@sentry/browser` | — |
| React SPA | `@sentry/react` | `npx @sentry/wizard@latest -i react` |
| Next.js | `@sentry/nextjs` | `npx @sentry/wizard@latest -i nextjs` |
| SvelteKit | `@sentry/sveltekit` | `npx @sentry/wizard@latest -i sveltekit` |
| Svelte (no kit) | `@sentry/svelte` | — |
| Vue / Angular / Astro / Remix / Nuxt | `@sentry/<framework>` | most have a wizard |
| Node server (Express, Fastify, Nest, Koa) | `@sentry/node` | — |
| Cloudflare Workers / Deno / Bun | `@sentry/cloudflare` / `@sentry/deno` / `@sentry/bun` | — |
| WebAssembly in the browser | `@sentry/browser` + `@sentry/wasm` | — |

Never mix `@sentry/browser` and a framework package in one app — the framework package
re-exports everything the base one has.

**Use the wizard when there is one.** It writes the config files, patches the bundler
for source-map upload, and creates `.env.sentry-build-plugin` — the upload wiring is
the part that's tedious to do by hand.

---

## Browser init

```bash
npm install @sentry/browser --save
```

```javascript
import * as Sentry from "@sentry/browser";

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  environment: import.meta.env.MODE,
  release: import.meta.env.VITE_RELEASE,   // must match the source-map upload release

  dataCollection: {
    // To disable sending user data and HTTP bodies, uncomment the lines below:
    // userInfo: false,
    // httpBodies: [],
  },

  integrations: [
    Sentry.browserTracingIntegration(),
    Sentry.replayIntegration(),
    Sentry.feedbackIntegration({ colorScheme: "system" }),
  ],
  enableLogs: true,
  tracesSampleRate: 0.1,
  tracePropagationTargets: ["localhost", /^https:\/\/yourserver\.io\/api/],
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
});
```

Notes that bite:

- **`dataCollection` replaces the old `sendDefaultPii` on the JS SDK.** `userInfo: false`
  stops IP/user capture; `httpBodies: []` stops request/response body capture. Older
  code and older docs use `sendDefaultPii: true` — it still works on some SDKs but
  prefer `dataCollection` on v10+.
- **`tracePropagationTargets` is a security boundary.** It controls which outgoing
  requests get `sentry-trace`/`baggage` headers. Leave third-party origins out or you
  leak trace IDs and trigger CORS preflight failures.
- Session replay masks all text and media by default. Loosen it deliberately
  (`maskAllText: false`) and never on a screen showing customer data.
- The DSN is safe in a client bundle. `SENTRY_AUTH_TOKEN` is not — it must only ever
  exist at build time.

### CDN / lazy loader (no bundler)

```html
<script
  src="https://js.sentry-cdn.com/<your-public-key>.min.js"
  crossorigin="anonymous"
></script>
```

Configure via `window.sentryOnLoad`. Pinned bundles live at
`https://browser.sentry-cdn.com/<version>/bundle.tracing.min.js`.

---

## Next.js (App Router)

```bash
npx @sentry/wizard@latest -i nextjs
```

Files the wizard creates:

| File | Role |
|------|------|
| `instrumentation-client.ts` | browser init |
| `sentry.server.config.ts` | Node runtime init |
| `sentry.edge.config.ts` | Edge runtime init |
| `instrumentation.ts` | registers the two above + `onRequestError` |
| `next.config.ts` | wrapped in `withSentryConfig` (source maps, tunnel) |
| `app/global-error.tsx` | catches render errors in the root layout |
| `.env.sentry-build-plugin` | build-time auth token — **must be gitignored** |

```typescript
// instrumentation-client.ts
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: "https://<key>@o<orgId>.ingest.sentry.io/<projectId>",
  dataCollection: {
    // userInfo: false,
    // httpBodies: [],
  },
  tracesSampleRate: process.env.NODE_ENV === "development" ? 1.0 : 0.1,
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
  enableLogs: true,
  integrations: [Sentry.replayIntegration()],
});
```

```typescript
// sentry.server.config.ts  (sentry.edge.config.ts is identical minus replay)
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: "https://<key>@o<orgId>.ingest.sentry.io/<projectId>",
  dataCollection: {
    // userInfo: false,
    // httpBodies: [],
  },
  tracesSampleRate: process.env.NODE_ENV === "development" ? 1.0 : 0.1,
  enableLogs: true,
});
```

```typescript
// instrumentation.ts
import * as Sentry from "@sentry/nextjs";

export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("./sentry.server.config");
  }
  if (process.env.NEXT_RUNTIME === "edge") {
    await import("./sentry.edge.config");
  }
}

export const onRequestError = Sentry.captureRequestError;
```

Forgetting the `onRequestError` export is the single most common Next.js mistake —
server component and route handler errors silently never arrive.

```tsx
// app/global-error.tsx
"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

export default function GlobalError({
  error,
}: {
  error: Error & { digest?: string };
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html>
      <body>
        <h1>Something went wrong!</h1>
      </body>
    </html>
  );
}
```

```typescript
// next.config.ts
import { withSentryConfig } from "@sentry/nextjs";

export default withSentryConfig(nextConfig, {
  org: "<your-org-slug>",
  project: "<your-project-slug>",
  authToken: process.env.SENTRY_AUTH_TOKEN,
  tunnelRoute: "/sentry-tunnel",
  silent: !process.env.CI,
});
```

`tunnelRoute` proxies events through your own domain, which defeats ad-blockers —
worth keeping if you care about client-side error completeness. It does route event
traffic through your server, so account for the bandwidth.

In CI, set `SENTRY_AUTH_TOKEN` as a secret; `.env.sentry-build-plugin` is for local
builds only.

---

## Svelte

```bash
npm install @sentry/svelte --save
```

Init in the entry point (`src/main.ts`), before mounting the app:

```javascript
Sentry.init({
  dsn: "https://<key>@o<orgId>.ingest.sentry.io/<projectId>",
  dataCollection: { userInfo: false, httpBodies: [] },
  integrations: [
    Sentry.browserTracingIntegration(),
    Sentry.replayIntegration(),
    Sentry.feedbackIntegration({ colorScheme: "system" }),
  ],
  enableLogs: true,
  tracesSampleRate: 1.0,
  tracePropagationTargets: ["localhost", /^https:\/\/yourserver\.io\/api/],
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
});
```

For a **SvelteKit** app use `@sentry/sveltekit` and its wizard instead — it adds
`hooks.client.ts`/`hooks.server.ts` handlers and the Vite plugin for source maps.
`@sentry/svelte` alone covers only the browser half.

---

## Node / Express

```bash
npm install @sentry/node --save
```

Init must run **before any other import** so the SDK can patch modules. Use a separate
file loaded first:

```javascript
// instrument.js  — CommonJS
const Sentry = require("@sentry/node");

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  environment: process.env.NODE_ENV,
  release: process.env.SENTRY_RELEASE,
  tracesSampleRate: 0.1,
  enableLogs: true,
});
```

```javascript
// app.js
require("./instrument");     // FIRST line
const express = require("express");
const Sentry = require("@sentry/node");

const app = express();
// ... routes ...
Sentry.setupExpressErrorHandler(app);   // after routes, before other error middleware
```

ESM can't hoist that trick — use `node --import ./instrument.mjs app.mjs`.

---

## WebAssembly

```bash
npm install @sentry/browser @sentry/wasm --save
```

```javascript
import * as Sentry from "@sentry/browser";
import { wasmIntegration } from "@sentry/wasm";

Sentry.init({
  dsn: "https://<key>@o<orgId>.ingest.sentry.io/<projectId>",
  sendDefaultPii: true,
  integrations: [Sentry.browserTracingIntegration(), wasmIntegration()],
  tracesSampleRate: 1.0,
});
```

The integration extracts Debug IDs, Debug Files, Code IDs and memory addresses from
wasm frames. To get symbolicated function names you must upload the debug files
(DWARF in the `.wasm`, or split debug info) with
`sentry-cli debug-files upload --include-sources <dir>` — see `operations.md`.
Compile with debug info retained (`-g` / `--debug` / `RUSTFLAGS="-g"`) or there is
nothing to symbolicate.

---

## Manual capture and context

```typescript
Sentry.captureException(err);
Sentry.captureMessage("checkout retried", "warning");

Sentry.setUser({ id: user.id, email: user.email });   // respect PII policy
Sentry.setTag("tenant", tenant.slug);
Sentry.setContext("cart", { items: cart.length, total: cart.total });

await Sentry.startSpan({ op: "task", name: "recalculate totals" }, async () => {
  await recalculate();
});

Sentry.logger.info("cache warmed", { keys: 1200 });   // requires enableLogs
```

## Filtering

```typescript
Sentry.init({
  // ...
  ignoreErrors: ["ResizeObserver loop limit exceeded", /^Non-Error promise rejection/],
  denyUrls: [/extensions\//, /^chrome:\/\//],
  beforeSend(event) {
    if (event.request?.headers?.authorization) {
      event.request.headers.authorization = "[Filtered]";
    }
    return event;
  },
});
```

Browser noise worth ignoring by default: `ResizeObserver loop limit exceeded`, extension
scripts, and `Non-Error promise rejection captured` from third-party widgets.

## Source maps — non-negotiable

Without uploaded source maps your production stack traces are `a.min.js:1:24601`.
Every bundler has a plugin; all need `SENTRY_AUTH_TOKEN`, `org`, `project`, and a
`release` matching `Sentry.init`. See `operations.md` for the plugin list, the
`sentry-cli sourcemaps inject && upload` fallback, and how to verify the upload.
