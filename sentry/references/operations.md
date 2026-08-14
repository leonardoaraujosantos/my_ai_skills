# Sentry — Operations

Releases, symbol upload, CI, PII, quota, and alerting. Read this for **every** install:
a Sentry setup without releases and symbols produces issues nobody can act on.

---

## Secrets and env vars

| Variable | Scope | Secret? |
|----------|-------|---------|
| `SENTRY_DSN` | runtime, all environments | No — write-only, safe in a client bundle. Still keep it in config, not source. |
| `SENTRY_AUTH_TOKEN` (`sntrys_…`) | build/CI only | **Yes.** Read/write on your org. Never in a client bundle, never committed. |
| `SENTRY_ORG`, `SENTRY_PROJECT` | build/CI | No |
| `SENTRY_ENVIRONMENT` | runtime | No |
| `SENTRY_RELEASE` | runtime **and** build | No — must be identical in both |
| `SENTRY_URL` | build/CI | No — set for self-hosted (`https://sentry.example.com/`) |

Gitignore the files wizards create with tokens in them: `.sentryclirc`,
`.env.sentry-build-plugin`, `sentry.properties`. Check they're ignored *before* the
first commit after running a wizard.

Create tokens at **Settings → Auth Tokens** (org-level) with the minimum scopes:
`project:releases` and `org:read` for release/source-map work.

---

## Releases

A release ties an event to the code that produced it, enables regression detection, and
is the key that source maps and debug files are matched on.

Naming: `<package>@<semver>` or `<service>@<git-sha>`, e.g. `api@1.4.2`,
`web@a1b2c3d`. Keep it unique per build.

```bash
export SENTRY_AUTH_TOKEN=sntrys_...
export SENTRY_ORG=my-org
export SENTRY_PROJECT=my-project

VERSION=$(sentry-cli releases propose-version)

sentry-cli releases new "$VERSION"
sentry-cli releases set-commits "$VERSION" --auto      # needs a repo integration
# without the integration, from a local checkout:
sentry-cli releases set-commits "$VERSION" --local
sentry-cli releases finalize "$VERSION"

sentry-cli deploys new --release "$VERSION" -e production
```

Install the CLI: `npm install -g @sentry/cli`, `brew install getsentry/tools/sentry-cli`,
or `curl -sL https://sentry.io/get-cli/ | bash`.

`set-commits --auto` is what powers "suspect commits" — the single highest-value
optional step, because it names the commit and author on each new issue.

The **same** `$VERSION` must be passed to `Sentry.init({ release })` /
`sentry_sdk.init(release=...)` / `options.releaseName` in the shipped build. Mismatch =
unsymbolicated traces and no regression detection.

---

## Source maps (JavaScript)

Preferred: the bundler plugin, which injects Debug IDs and uploads on build.

| Bundler | Plugin |
|---------|--------|
| Vite | `@sentry/vite-plugin` |
| Webpack | `@sentry/webpack-plugin` |
| Rollup | `@sentry/rollup-plugin` |
| esbuild | `@sentry/esbuild-plugin` |
| Next.js | built into `withSentryConfig` |
| SvelteKit / Nuxt / Astro / Remix | built into the framework SDK's plugin |

```javascript
// vite.config.ts
import { sentryVitePlugin } from "@sentry/vite-plugin";

export default defineConfig({
  build: { sourcemap: true },        // required
  plugins: [
    sentryVitePlugin({
      org: process.env.SENTRY_ORG,
      project: process.env.SENTRY_PROJECT,
      authToken: process.env.SENTRY_AUTH_TOKEN,
      release: { name: process.env.SENTRY_RELEASE },
    }),
  ],
});
```

CLI fallback (also the right tool when the build happens outside your control):

```bash
sentry-cli sourcemaps inject ./dist          # stamps Debug IDs into files + maps
sentry-cli sourcemaps upload ./dist \
  --release "$VERSION" --org "$SENTRY_ORG" --project "$SENTRY_PROJECT"
```

Run `inject` **before** `upload` and before any minifier that would strip the injected
comment. Debug IDs are what make uploads work without matching URLs — much more robust
than the old `--url-prefix` approach.

Don't serve `.map` files publicly if the code is proprietary — Sentry only needs the
uploaded copy. Delete them from the deployed bundle after upload
(`sourcemaps: { deleteFilesAfterUpload: true }` in the plugin, or `rm -f dist/**/*.map`).

**Verify:** Sentry UI → **Settings → Projects → <project> → Source Maps** lists the
uploaded artifact bundles. Or check a real issue: frames should show your source file
and line, not `index-4f2a.js:1:98211`.

---

## Debug files (native, iOS, Android, WASM, Unreal)

```bash
# dSYMs, PDBs, ELF/.so, Breakpad, wasm
sentry-cli debug-files upload --include-sources /path/to/symbols

# Android ProGuard/R8
sentry-cli upload-proguard --uuid <uuid> app/build/outputs/mapping/release/mapping.txt

# check what Sentry already has
sentry-cli debug-files check /path/to/binary
sentry-cli debug-files find <debug-id>
```

`--include-sources` embeds source snippets in the upload so stack frames show real code.
Skip it if you'd rather not store source on Sentry.

Most platform integrations automate this (Xcode build phase, Android Gradle plugin,
Unity build post-processor, Unreal plugin) — prefer the automation, it can't be
forgotten on a hotfix build.

---

## CI wiring

GitHub Actions:

```yaml
- name: Create Sentry release
  uses: getsentry/action-release@v3
  env:
    SENTRY_AUTH_TOKEN: ${{ secrets.SENTRY_AUTH_TOKEN }}
    SENTRY_ORG: my-org
    SENTRY_PROJECT: my-project
  with:
    environment: production
    version: ${{ github.sha }}
    sourcemaps: ./dist
```

Rules that keep this from rotting:

- Compute the version **once** in the pipeline and pass it to both the build (as
  `SENTRY_RELEASE`) and the release step.
- Fail the build if upload fails in production pipelines; allow it to warn in preview
  builds (`errorHandler` in the bundler plugins).
- Never run the release step on PR builds from forks — the token isn't available and
  shouldn't be.

---

## PII and data scrubbing

Sentry scrubs common secret-looking fields server-side by default (passwords, tokens,
credit cards). That is a backstop, not a policy.

Layers, outermost first:

1. **Don't send it.** `send_default_pii=False` / `dataCollection: { userInfo: false,
   httpBodies: [] }` when you have no need for request bodies or user identity.
2. **Client-side `before_send` / `beforeSend`** to redact known-sensitive fields —
   this runs before anything leaves the process, so it's the only layer that protects
   against Sentry-side exposure. Examples in `python.md` and `javascript.md`.
3. **Server-side scrubbing rules**: Settings → Security & Privacy → Data Scrubbing.
   Add custom fields and `$string` regex rules for your domain (national IDs, account
   numbers). Enable "Prevent Storing of IP Addresses" if you don't need IPs.
4. **Session replay masking** — on by default for text and media. Any place you unmask,
   assume the recording is customer data with the same retention obligations.
5. **Attachments** (screenshots, view hierarchies, minidumps) are not scrubbed the same
   way. Treat them as raw customer data and enable deliberately.

Region matters for data residency: `ingest.de.sentry.io` DSNs keep data in the EU,
`ingest.us.sentry.io`/`ingest.sentry.io` in the US. The DSN determines it; you can't
change region after project creation.

---

## Quota control

In rough order of impact:

1. **Lower `tracesSampleRate`.** `1.0` in production is the usual culprit. Start at
   `0.1` and go down from there for high-traffic services.
2. **Use a `traces_sampler`** to zero out health checks, metrics scrapes, static assets,
   and bot traffic.
3. **Lower replay `sessionSampleRate`** to `0.01–0.1`; keep `onErrorSampleRate` at `1.0`.
4. **Inbound filters** (Settings → Project → Inbound Filters): legacy browsers, web
   crawlers, localhost, known browser extension errors — free, server-side, no code.
5. **`ignoreErrors` / `denyUrls`** for the specific noise your app generates.
6. **Spike protection** (Settings → Subscription) — leave it on; it's the difference
   between a bad day and a burned month.
7. **Per-key rate limits** (Settings → Project → Client Keys) cap a single client.
8. **Retention/quota split**: set per-project quotas so one noisy service can't starve
   the rest.

Diagnose with **Stats → Usage** broken down by project and category (errors,
transactions, replays, attachments) to see which product is actually consuming it
before changing anything.

---

## Alerts

Defaults are noisy. A workable baseline:

- **Issue alert**: "a new issue is created" → team channel, but **filter to
  `environment:production`** and `level:error` or above.
- **Issue alert**: "an issue changes state from resolved to unresolved" (regression) →
  higher-urgency channel. This is the alert worth paging on.
- **Metric alert**: error rate or failure rate above threshold over 5 minutes — catches
  incidents that a per-issue alert misses because it's one issue firing 10k times.
- Use **ownership rules** (`.sentry/ownership` or Settings → Ownership Rules) to route
  by path so the right team gets it.
- Integrations: Slack, PagerDuty, Jira, Linear, GitHub. The GitHub/Jira link lets you
  resolve an issue via commit message (`Fixes SENTRY-123`).

Mute rather than delete alerts you don't want yet — deleted rules get recreated by the
next person who notices the gap.

---

## Self-hosted

https://develop.sentry.dev/self-hosted/ — Docker Compose based, needs ~16 GB RAM
realistically. Point the CLI and plugins at it with `SENTRY_URL=https://sentry.example.com/`.

Only worth it for hard data-residency or air-gap requirements; the operational cost
(Kafka, ClickHouse, Postgres, Redis, upgrade migrations) is real. If the driver is EU
data residency, use an `ingest.de.sentry.io` DSN on SaaS instead.

---

## Verification checklist

Before calling an install done:

- [ ] Deliberate error appears in the UI within a couple of minutes
- [ ] Stack trace shows **your source files and line numbers**
- [ ] Event is tagged with the right `environment`
- [ ] Event is tagged with a `release` that matches the deployed build
- [ ] Suspect commit / author is shown (if `set-commits` is wired)
- [ ] A transaction exists for the same request, linked to the error
- [ ] No secrets in the event body (check the request headers/body of a real event)
- [ ] Auth token is in CI secrets, and `.sentryclirc` / `.env.sentry-build-plugin` /
      `sentry.properties` are gitignored
- [ ] The test error route/button has been removed
- [ ] Env vars documented in the README or `.env.example`
