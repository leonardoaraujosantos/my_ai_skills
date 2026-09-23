# Server proxies: getting public data onto the globe safely

Every non-trivial feed goes through a same-origin `/api/*` proxy. The proxy exists to:

1. Keep keys off the client.
2. Cache and coalesce requests so the upstream sees one request per TTL, not one per viewer.
3. Respect the upstream's rate limits.
4. Degrade to stale or fallback data instead of failing.
5. Contain SSRF.

Where the proxy runs:
- **Vite only**: Vite `configureServer` and `configurePreviewServer` middleware (GEV).
- **SvelteKit**: `routes/api/<feed>/+server.ts` (GS, KZ).
- **FastAPI**: a Python backend (GS backend).

Browser-direct calls are acceptable only for keyless, CORS-enabled, public tiles and JSON, such as GIBS, Esri, USGS and RainViewer. When you make a browser-direct call, say so explicitly.

---

## 1. The response contract

Choose one contract and apply it to every route.

**GS style ("always 200").** Every route returns 200 with this body:
```
{ items: [...], error?, rateLimited?, retryAt?, tooLarge?, stale?, source }
```
- Viewmodels never have to handle thrown errors.
- `rateLimited` and `retryAt` drive the client back-off.
- `tooLarge` drives a "zoom in" hint.

**GEV style (real status codes).** Routes return real HTTP status codes with a JSON `{error}` body.
- Return a 503 with a `reason` or status descriptor when a key is missing, so the UI can show KEY REQUIRED.
- Report provenance in headers: `X-<Feed>-Cache: HIT|MISS|STALE|STALE-ERROR`, `X-Flight-Source`, `X-*-Stale-Seconds`.

Either way, send an unknown `/api/*` path to `404 {"error":"Unknown API route"}`. It must never fall through to the SPA HTML.

## 2. Cache layers

| Data | TTL | Notes |
|---|---|---|
| Aircraft state vectors | 8–30 s, adaptive | OpenSky: set the TTL from `X-Rate-Limit-Remaining`. Above 2400 → 9 s, above 1200 → 30 s, above 400 → 90 s, otherwise 300 s |
| Military aircraft (adsb.lol) | 12 s | Honour `Retry-After`, clamped to 5–120 s |
| Quakes, weather | 60 s – 5 min | |
| FIRMS, cyclones, launches | 5–30 min | FIRMS 30 min, filtered to 24 h on every serve |
| TLEs | 2–6 h, on disk | CelesTrak blocks clients that download too often |
| Overpass | 24 h in memory, 7–30 d on disk | Snap the bbox to a grid (0.05°–0.5°) so different viewports share cache entries |
| Terrain heights | 30 d per point, on disk | |
| Climate history | 30 d | Past data doesn't change |
| Static datasets (airports, power plants) | 24 h, in module memory | Parse CSV or ZIP on the server, once |

Patterns to apply:
- **Single-flight**: concurrent misses on the same key share one upstream request.
- **Stale-while-error**: if the upstream fails and a cache entry exists, serve it marked stale. Only return 502 when nothing is cached.
- **Cache successes only.** Cache negative results (404, "no route") with a short TTL.
- **On the client**, cache the promise itself so concurrent callers share one request, and evict it on rejection (GS `createTtlCache`).
- **Put disk caches under `.app-cache/` and add it to `.gitignore`.** Prune them, because unbounded per-key files grow forever.

## 3. Rate limits, both directions

**Inbound (protect your keys and your upstream).**
- Use a sliding window per client plus a global backstop, and cap the number of tracked keys (around 2,000).
- **Key on the socket address.** Ignore `X-Forwarded-For` unless you terminate at a trusted proxy.
- Make metered throttles opt-in through an environment variable, e.g. `RATELIMIT_OPENAI_PER_MIN=N`. The per-client limit is N and the global limit is 20×N. Launchers such as Pinokio set safe defaults.

**Outbound (respect providers).**
- **Nominatim**: at most 1 request per second, serialized through a queue (at most 4 pending, each waiting at most 10 s). Send an identifying User-Agent and Referer. When the queue is full, return 429 with `Retry-After`.
- **OSRM**: 1 request per second, a queue of 8, 2–12 waypoints, and caps on leg and total length.
- **Cooldowns**: after a 429, stop calling the upstream until `retry-after`, clamped to between 30 s and 30 min. Serve stale data in the meantime.
- **Daily budgets** for metered tiles, e.g. TomTom at 6,000 per UTC day. Persist the count to disk. When the budget is exhausted, serve stale tiles, otherwise return 429 `{error:'budget'}`.

## 4. Fallback chains

```
primary (OpenSky) ──fail/429/stale>120s──► regional fallback (adsb.lol 250 nm around view) ──► last good cache
Overpass: mirror1 → mirror2 → mirror3 → mirror4 (22 s each) → stale disk cache
Terrain:  Re:Earth mesh → ellipsoid
Imagery:  Google 3D → ion → Esri → OSM (switch automatically after N tile failures)
Wind:     latest GFS cycle → previous cycle (don't forget this one) → stale manifest
Pipeline (KZ): sources[0] live → sources[1..] mirror → committed snapshot → missing
```

Mark which link in the chain served the data (`fallback`, `mirror`, `snapshot`). The UI and the AI agent must say so.

## 5. Push feeds (WebSocket) held server-side

Use AISStream as the template:
- Open exactly **one** upstream socket per server.
- Keep an in-memory store: 50k rows, 30 min expiry, 64-sample tracks per ID.
- **Watchdog**: mark the feed stale after 120 s of silence, and recycle the socket after 2.5 × 120 s.
- **Reconnect backoff**: 5 s → 15 s → 60 s → 300 s, then every 15 min.
- **Auth failures**: probe once an hour.
- **Status vocabulary**: `missing-key | connecting | live | stale | reconnecting | down | auth-failed`.
- The browser polls `/api/ais-live?maxRows=` every 60 s. GS uses Redis ZSETs scored by timestamp instead of memory.

## 6. SSRF and input hygiene

- **Never accept an upstream URL from the client.** Accept an **ID** and look the URL up in a server registry. Examples: camera frames, transit feeds, radio stations. Click-tracking only accepts IDs that the server actually served.
- If a URL parameter is unavoidable (e.g. GBFS), allow **HTTPS only**, check host and path allowlists, and refuse redirects (`redirect: 'manual'`, treat any 3xx as 502).
- **Redirects**: allow them only within the same origin and cap the hops (3). Use `redirect: 'error'` for Places, OpenAI and similar APIs.
- **DNS rebinding**: resolve the hostname yourself, refuse private or non-global addresses, and pin the connection to the validated IP (Radio Browser).
- **Streaming body caps** in both directions: reject early on `Content-Length`, then count bytes while streaming. Typical request caps are 24 KB for Overpass bodies and 64 KB for LLM summaries. Response caps are 5–64 MB depending on the feed.
- **Timeouts on every upstream fetch**: `AbortSignal.timeout(10–60 s)`. A missing timeout on the busiest feed is the most common bug.
- **Overpass**: sanitize the QL. Clamp `[timeout:]` to 30 s or less, `around` to 50 km or less, and the bbox to 12° or less. Refuse area scans.
- **Geocoding and bbox parameters**: validate that values are finite and within range. Reject oversize areas before calling the upstream.
- **Allowlist lookups**: use `Map` or `Object.hasOwn`, never `obj[key]`. KZ's QA found an allowlist bypass through `constructor`.
- **Error bodies**: never echo raw upstream `error.message` back to the client.

## 7. Key hygiene

- Keep server-only keys out of the client bundle: use `$env/dynamic/private` in SvelteKit, or keep them outside Vite `define`. Browser keys are limited to the ion token and the Google Maps key.
- Never log URLs that contain keys (FIRMS keys sit in the path, TomTom keys in the query string). Fingerprint keys instead, e.g. `sha256[:12]`.
- Mint OpenAI Realtime **client secrets** on the server. The long-lived key never reaches the browser.
- If you add an in-app "POWER UP" key panel (GEV), it must:
  - Admit **loopback only**: check the socket address, the Host header and the exact Origin, and refuse any proxy header.
  - Accept only a closed registry of key names.
  - Reject values containing shell metacharacters.
  - Write atomically: a 0600 temp file, harden permissions, fsync, then rename. Refuse to follow symlinks.
  - Restart the dev server afterwards.
  - Never return key values in any response.
- Deny `.env`, `.env.*`, `*.pem` and `.git` in the dev file server (Vite `server.fs.deny`). Send `X-Frame-Options: DENY` and `frame-ancestors 'none'`.

## 8. Streaming through a catch-all proxy (GS `api/geo/[...path]`)

- Pass `response.body` straight through, so SSE works without special handling.
- Strip hop-by-hop headers, and also `accept-encoding` and `content-encoding`. This avoids undici double decompression.
- Forward the bearer token only. Drop `cookie` and `set-cookie`.
- Use `redirect: 'manual'`. Return 502 when the backend is unreachable.
- On the SSE response itself, send `X-Accel-Buffering: no` and `Cache-Control: no-cache`.

## 9. Canonical Vite middleware skeleton (JS)

```js
export function feedProxy({ path, ttlMs, fetchUpstream }) {
  let cache = null, inflight = null, cooldownUntil = 0;
  return {
    name: `proxy:${path}`,
    configureServer(s) { s.middlewares.use(path, handle); },
    configurePreviewServer(s) { s.middlewares.use(path, handle); },
  };
  async function load() {
    if (cache && Date.now() - cache.at < ttlMs) return { ...cache, hit: 'HIT' };
    if (Date.now() < cooldownUntil && cache) return { ...cache, hit: 'STALE' };
    inflight ??= (async () => {
      try {
        const body = await fetchUpstream(AbortSignal.timeout(15_000));
        cache = { at: Date.now(), body };
        return { ...cache, hit: 'MISS' };
      } catch (e) {
        if (e.status === 429) cooldownUntil = Date.now() + (e.retryAfterMs ?? 120_000);
        if (cache) return { ...cache, hit: 'STALE-ERROR' };
        throw e;
      } finally { inflight = null; }
    })();
    return inflight;
  }
  async function handle(req, res) {
    try {
      const r = await load();
      res.writeHead(200, { 'Content-Type': 'application/json', 'X-Cache': r.hit, 'Cache-Control': 'no-store' });
      res.end(r.body);
    } catch {
      res.writeHead(502, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'upstream unavailable' }));
    }
  }
}
```

The starter template (`templates/starter/server/proxies.js`) ships a working version of this skeleton.
