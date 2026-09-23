# Architecture: how a planetary dashboard is put together

This document condenses three codebases:

- **GEV**: God's Eye View. Vanilla JS, CesiumJS and Vite middleware proxies. 27 live layers.
- **GS**: GeoSphere (`CyberdyneCorp/geo_dashboard`). SvelteKit, Svelte 5 runes, CesiumJS, with a FastAPI backend.
- **KZ**: KANZI (`aminitech/kanzi`). SvelteKit, MapLibre 6 and Cesium, driven by a GDAL pipeline and manifests.

---

## 1. Pick the engine first

| Need | Engine | Why |
|---|---|---|
| Whole-planet view, orbits, aircraft altitude, 3D Tiles (Google photoreal / OSM Buildings), sensor-style post-processing | **CesiumJS** | True WGS84 globe, SGP4-friendly, `Cesium3DTileset`, `PostProcessStage` |
| One country or site: terrain, extruded buildings, dense vector styling, data-driven cartography, lighter bundle | **MapLibre GL** (6.x) | Vector tiles, style expressions, `raster-dem` terrain, fill-extrusion, `CustomLayerInterface` |
| Both: a national or site "twin" plus an orbital "lens" | **MapLibre for the analyst views, Cesium for the globe or lens** (KZ pattern) | Share one manifest and one token layer between them |

Do not try to make MapLibre behave like a globe-scale tracker, or Cesium behave like a cartography engine.

## 2. Keyless-first is an architectural rule

Every capability must still work with **zero keys**. Keys only unlock upgrades.

- Imagery: Esri World Imagery, falling back to OSM. Upgrades are Google Photorealistic 3D (Google key) or ion Bing plus World Terrain (ion token).
- Terrain: Re:Earth quantized mesh or AWS terrarium, falling back to the flat ellipsoid.
- Flights: anonymous OpenSky, falling back to adsb.lol. Fires, AIS, TomTom and voice show a **KEY REQUIRED** state instead of breaking.
- Traffic: without TomTom it is **simulated along real OSM roads** and labelled SIMULATED.
- Voice: without OpenAI it falls back to a typed-intent parser that calls the same tools (KZ).
- Only two keys may ever reach the browser: `GOOGLE_MAPS_API_KEY` and `CESIUM_ION_TOKEN`. Restrict both by referrer. Every other key stays on the server.

## 3. Application skeleton (choose one style)

### A. Phased app plus layer registry (GEV, vanilla JS)
```
createApplication({ scene, controls, data, tools })
  start order:     scene → controls → data → tools
  teardown order:  tools → controls → data → scene
  each phase receives: {...earlierComponents, signal, defer(cleanup)}
```
- `defer()` is valid only while the constructor runs. Cleanups run LIFO and their errors are aggregated.
- Status is `created | starting | ready | destroying | destroyed | failed`, published as frozen snapshots.
- One application per page. A second one throws.

### B. MVVM with runes (GS, Svelte 5)
- `models/{types,ports,services}` hold data shapes, ports with **NULL implementations**, and stateless fetchers.
- `viewmodels/*.svelte.ts` use `createXxxVM()`: private `$state`, getters plus mutators, and `type XxxVM = ReturnType<…>`.
- `components/globe` holds Cesium layer components only. `components/panels` holds the UI.
- `services/cesium` holds the port implementations. Bind them on viewer-ready and unbind on destroy.
- Cross-VM dependencies are **getter closures** (`createAircraftVM(() => globe.viewBBox)`), not imports.
- Use the context key `Symbol.for('app.viewmodels')`, not `Symbol()`, so it survives HMR.
- Pure maths lives in `utils/*.ts` and is 90%+ unit-tested. Rune VMs and Cesium adapters are excluded from coverage.

### C. Manifest-driven viewer (KZ)
- The viewer is **a pure function of `twin_manifest.json`**: terrain spec, basemaps, camera presets, layers, provenance and degraded layers.
- Changing the tile host or dataset means republishing data, not changing code. There is one manifest per pipeline stage.

## 4. The layer contract (all three converge on this)

```js
{
  id: 'flights',                     // stable, unique; also the share-link token owner
  name, icon, group,                 // panel presentation
  source,                            // attribution line
  requiresKeyId?: 'opensky',         // drives KEY REQUIRED UI
  refreshInterval?: 30_000,          // polling cadence, or
  updateInterval: 0,                 // 0 = camera-driven (reload on moveEnd, debounced)
  init(viewer, {signal}),            // create DataSource/Primitive collections once
  enable(viewer, {signal}),          // show + start
  disable(viewer),                   // hide + stop polling + clear buffers (no stale flash on re-enable)
  update(viewer, {signal}),          // fetch + reconcile; return false on failure
  destroy(),                         // release GPU resources
  getStats() → {count, lastUpdate, status, error, retryInSec, source, stale, fallback},
  getParams()/setParams(),           // per-layer options (serialized into share links)
  getAnalystRecords?() → [...]       // plain records for AI/analyst queries
}
```

A single manager owns every layer. It is responsible for:

- **Serializing transitions per layer.** One promise chain per layer, so fast toggling never creates two polling intervals.
- **Skipping overlapping refreshes.** If an update is still running, the next tick does nothing.
- **Tracking intent origins.** `user | voice | tool` count as explicit intent and cancel pending share-link restores. `restore` and `scene` origins can be overridden.
- **Visibility guards.** A context mode can block a toggle and give a reason.
- **Reacting to activity events.** `data-updated` triggers a render request and invalidates detection. `status` refreshes the panel. Panel refreshes are deferred while the tab is hidden.
- **Sealed registration.** Every layer must declare its serialization disposition, and the manager throws on mismatch. This prevents a new layer from silently breaking share links.

In Svelte, one `$state` record `{[id]: {visible, opacity}}` plus one component per layer is enough. Each component polls only while visible, driven by an `$effect` on the toggle (GS). **Generate the toggle UI, panel cards and pick routes from the registry.** A hand-written 1,900-line layer panel is the anti-pattern here.

## 5. Feed state: one vocabulary everywhere

Every layer reduces to one of:

`nominal · loading · degraded · stale · partial · fallback · unavailable · off`

- `unavailable`: status is error or down, or there is an error and no prior data.
- `fallback`: served by the backup provider (e.g. adsb.lol instead of OpenSky).
- `stale`: the snapshot is older than the layer's freshness window, e.g. more than 120 s for aircraft.
- Guidance statuses (`zoom-in`, `empty`, `idle`) are **not** faults.
- The panel toggle, HUD, loading chip, voice agent and analyst answers all read the same snapshot `{id, feedState, source, count, lastUpdate, ageLabel, error}`.
- Keep **every** state in the severity table. GEV's analyst reported `partial` layers as "off" because the table was missing that state.

KZ adds a **trust label** to each legend item: `LIVE | REAL | MODEL | SCREENING | NOT OBSERVED | SIMULATED`. It also adds a provenance status for each layer: `live | mirror | snapshot | missing`. Use both when the audience makes decisions from the map.

## 6. Coordination primitives worth copying

- **Source slots**: a stable proxy with the provider hot-swappable behind it. A late result from a replaced provider rejects with `AbortError`.
- **State channel**: deep-frozen plain snapshots with a monotonic revision number and FIFO delivery, even when a listener publishes during delivery.
- **Pointer lease**: exactly one tool owns clicks (draw, directions, imagery box). Claims never stack or steal. Tracking clicks are ignored while a lease is held.
- **Pick registry**: each layer registers a predicate, and one central handler routes a pick to its owner. GS puts `entity.entityKind` and `entityRef` on entities. Cluster billboards carry a marker object.
- **Ports with NULL implementations** (`TerrainSampler`, `ScreenPicker`) keep Cesium out of viewmodels, so they run under SSR and in tests.
- **Request and consume bridge for camera moves (GS)**: the VM publishes `flyTarget = {…, id: ++seq}`, and the view runs `flyTo` and consumes it by id. This gives imperative camera control without a viewer reference in state.
- **Latest-wins guards**: use a generation counter or `seq`, checked after every await, plus a rotating `AbortController` per selection.
- **Render governor**: see `rendering.md`. Keep the globe in request-render mode unless a named hold exists.

## 7. Module boundaries

- **Sources and parsers** (fetch plus normalization) must not import renderers or UI. Browser code must not import Node or server modules. Portable modules must not touch `window`, `cesium` or `vite`.
- **Enforce these rules with a script in CI**, e.g. GEV's `check-import-directions.mjs` and per-export package boundary builds. Do not rely on code review for them.
- **Pin load-bearing config with tests** (KZ):
  - The MapLibre worker URL and `optimizeDeps` exclusion.
  - No key-gated tile hosts. Unkeyed CARTO raster tiles return a watermark with HTTP 200.
  - Every CSS token referenced from TS/JS must exist in a stylesheet.

## 8. Build gotchas

- **Cesium plus Vite (vanilla)**: `vite-plugin-cesium` works. Alternatively, copy `node_modules/cesium/Build/Cesium/{Workers,Assets,ThirdParty,Widgets}` to `public/cesium/` in `predev`/`prebuild`. Then set `window.CESIUM_BASE_URL = '/cesium/'` **before** any chunk runs.
- **Cesium plus SvelteKit**: **do not use `vite-plugin-cesium`**. Its external-globals rewrite causes a TDZ crash in production builds. Use the copy script, `ssr.noExternal: ['cesium']`, `await import('cesium')` behind `if (!browser)`, and type-only `import('cesium').Viewer`. Add an SSR smoke test, and give Docker a `/healthz` route that does not SSR the globe.
- **MapLibre 6 plus Vite**: import `maplibre-gl-worker.mjs?worker&url`, call `setWorkerUrl` once in a single `maplibre.ts` module, exclude maplibre-gl from `optimizeDeps`, and set `worker.format: 'es'`.
- **Fonts and icons**: self-host them for sovereign deployments. Subset Material Symbols with `icon_names=`, and enforce the subset with a test.
- **HTML templates**: allowlist names when expanding partials at build time. An unknown name must fail the build.
