# Quality: testing a WebGL dashboard without fooling yourself

Unit tests do not render a globe, and screenshots do not tell you when something is subtly wrong. All three projects use layered gates for that reason. Use the same layers here.

## 1. Unit layer: pure functions, high coverage

- **Keep the maths outside components.** Put it in `utils/*.ts`, `records.js` and `policy.js`. That covers orbit/SGP4 wrappers, sun position, radio horizon, geoid, throughput, chart geometry, SSE parsing, caches, coordinate parsing, share-link encode/decode, feed-state reduction, and label arbitration.
- **Coverage targets.** Aim for 90% lines and functions, and 85% branches. Exclude `.svelte`, rune viewmodels, Cesium adapters and type-only files.
- **Normalizers run on recorded fixtures.** For each upstream, commit one real response under `fixtures/`. Add tests for sentinels (AIS speed ≥102.3 kn, heading 511), rows with a position of 0,0, duplicate IDs, and malformed feeds. Decide whether a malformed feed rejects the whole snapshot or only the bad row, then write the test that pins that decision.
- **Deterministic fakes for analysis.** Seed each fake from a hash of the geometry, so the UI and CI behave the same offline.
- **Proxy tests.** Stub `fetch` and cover these cases:
  - Cache hit/miss/stale, and single-flight.
  - Cooldown after a 429.
  - Allowlist rejection, including `constructor` and `__proto__` keys.
  - Body caps.
  - Redirect refusal.
  - The missing-key state.
- **Tool-surface snapshot.** Snapshot the list of MCP and agent tools. Any change to it becomes a deliberate diff.

## 2. Contract and config pins (cheap, catches silent failures)

Each of these is a small test that fails the moment the load-bearing config drifts:

- The MapLibre worker URL is set, maplibre is excluded from `optimizeDeps`, and `worker.format === 'es'`.
- `CESIUM_BASE_URL` is defined before the first chunk runs, and the copied asset directories exist.
- No tile host needs a key, and no CARTO raster URLs are used (unkeyed CARTO raster tiles carry a watermark).
- Every CSS custom property referenced from JS or TS is defined in a stylesheet.
- The icon-font subset includes every icon name the code uses.
- Every registered layer has a share-link token, and every token maps to a layer.
- Every legend or trust label comes from the closed vocabulary.
- The docs' version badges match `package.json`.

## 3. Architecture gates in CI

- **Import-direction script.** Sources must not import renderers. The browser must not import node or server code. Portable modules must stay free of `window` and `cesium`.
- **Package/export boundary builds.** Optional, for libraries.
- **Formatter** over an explicit scope.
- **Allocation budgets for hot paths.** Measure bytes per call in the sprite tick, the overlay frame and the focus helpers, using `node --expose-gc`. Calibrate the budget for one Node major and skip the check on others unless it is explicitly required.
- **Every PR:** `npm ci → doctor → format:check → boundaries → test → build`. Add an SSR smoke test for SvelteKit, which asserts that `GET /` returns 200 with no console errors.

## 4. Browser layer: offline e2e plus visual evidence

- **Playwright, offline.**
  - Use `page.route('**/api/*')` to serve canned fixtures, and `route.abort()` for tile hosts (GIBS, CARTO, ion, OSM).
  - Wait for a readiness attribute (`data-globe-ready="true"`) instead of sleeping.
  - Seed auth with `addInitScript`.
- **QA harnesses.** Write one Puppeteer script per feature (`qa-<feature>.mjs`) that runs against a dev server already running at `QA_BASE_URL`, using SwiftShader or ANGLE when headless. Save screenshots and a JSON verdict to a git-ignored `qa-shots/`.
  - **Mutation variants** (`qa-*-mutations.mjs`): break the thing on purpose and check that the harness notices.
- **Tracking regression suite** with synthetic feeds. Assert these invariants:
  - No jitter.
  - No pull-out.
  - No cross-layer orphans.
  - Clicking the tracked target again does nothing.
  - When a contact ages out, the camera stays where it is.
  - Landing ghosts are culled.
- **Screenshot and GIF recipes.** Use a declarative JSON recipe, CDP `Page.startScreencast`, a repaint keep-alive, and one ffmpeg palette per clip. Use these for the README and for review.
- **Performance baseline.** Record one machine, browser and resolution in `docs/PERFORMANCE.md`: cold start, idle FPS, per-layer activation cost, per-style FPS, and heap. Compare against it; don't treat it as a guarantee.

## 5. Specs

- Onboard the project with the `openspec-baseline` skill, so every capability carries SHALL requirements and scenarios. Run `openspec validate --all --strict` in CI.
- For context packs, parse the Given/When/Then scenarios into a BDD coverage register (see `pipelines-and-deploy.md` §6).

## 6. Pre-ship review checklist

- [ ] Works with **zero keys**. Every keyed layer shows KEY REQUIRED with guidance.
- [ ] Every upstream fetch has a timeout and a response-size cap. Every proxy has a cache with serve-stale-on-error.
- [ ] No client-supplied URL reaches `fetch` on the server (IDs only, or strict allowlists).
- [ ] Metered fallbacks can't be abused: Street View behind a camera proxy, token minting, and debug logs are all rate-limited or restricted to loopback.
- [ ] The feed state and trust label are visible on every layer, and the voice or chat agent repeats them.
- [ ] A share link restores the view, and live target handoffs expire.
- [ ] The idle globe renders nothing (render governor), and the hidden tab stops rendering and polling.
- [ ] Credits are visible in every mode. Non-commercial datasets are flagged in DATA_SOURCES.md.
- [ ] Keyboard path, focus ring, Esc behaviour and reduced motion have been checked.
- [ ] README claims match the code. GEV's README promised camera handoff and "exact view back", and the code does neither.
