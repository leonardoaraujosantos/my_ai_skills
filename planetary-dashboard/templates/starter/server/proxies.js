// Same-origin /api/* proxies as Vite middleware (dev + preview).
// Each proxy: keys stay server-side, one upstream call per TTL (single-flight),
// cooldown after 429, serve-stale-on-error, timeouts and body caps everywhere.
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const CACHE_DIR = join(process.cwd(), '.app-cache');
const MAX_BODY = 16 * 1024 * 1024;

async function readCapped(res, cap = MAX_BODY) {
  const declared = Number(res.headers.get('content-length'));
  if (declared > cap) throw Object.assign(new Error('upstream too large'), { status: 502 });
  const reader = res.body.getReader();
  const chunks = [];
  let size = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > cap) {
      await reader.cancel();
      throw Object.assign(new Error('upstream too large'), { status: 502 });
    }
    chunks.push(value);
  }
  return Buffer.concat(chunks);
}

function diskGet(key) {
  try {
    return JSON.parse(readFileSync(join(CACHE_DIR, `${key}.json`), 'utf8'));
  } catch {
    return null;
  }
}

function diskPut(key, entry) {
  try {
    mkdirSync(CACHE_DIR, { recursive: true });
    writeFileSync(join(CACHE_DIR, `${key}.json`), JSON.stringify(entry));
  } catch {
    /* cache is best-effort */
  }
}

/**
 * Create a cached proxy for one upstream resource.
 * @param {object} o
 * @param {string} o.key        cache key (also disk file name)
 * @param {number} o.ttlMs      freshness window
 * @param {(signal: AbortSignal) => Promise<{status:number, headers:Headers, body:Buffer}>} o.fetchUpstream
 * @param {boolean} [o.disk]    persist to .app-cache/ (survives restarts)
 */
export function createCachedResource({ key, ttlMs, fetchUpstream, disk = false }) {
  let cache = disk ? diskGet(key) : null;
  let inflight = null;
  let cooldownUntil = 0;

  async function refresh() {
    const res = await fetchUpstream(AbortSignal.timeout(20_000));
    if (res.status === 429) {
      const retry = Number(res.headers.get('retry-after')) || 120;
      cooldownUntil = Date.now() + Math.min(Math.max(retry, 30), 1800) * 1000;
      throw Object.assign(new Error('rate limited'), { status: 429 });
    }
    if (res.status < 200 || res.status >= 300) {
      throw Object.assign(new Error(`upstream HTTP ${res.status}`), { status: 502 });
    }
    cache = { at: Date.now(), body: res.body.toString('utf8') };
    if (disk) diskPut(key, cache);
    return { ...cache, state: 'MISS' };
  }

  return async function load() {
    const fresh = cache && Date.now() - cache.at < ttlMs;
    if (fresh) return { ...cache, state: 'HIT' };
    if (Date.now() < cooldownUntil) {
      if (cache) return { ...cache, state: 'STALE' };
      throw Object.assign(new Error('rate limited; cooling down'), { status: 429 });
    }
    inflight ??= refresh()
      .catch((err) => {
        if (cache) return { ...cache, state: 'STALE-ERROR' };
        throw err;
      })
      .finally(() => {
        inflight = null;
      });
    return inflight;
  };
}

async function upstream(url, init = {}, signal) {
  const res = await fetch(url, { ...init, signal, redirect: 'error' });
  return { status: res.status, headers: res.headers, body: await readCapped(res) };
}

function sendJson(res, status, payload, extra = {}) {
  res.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', ...extra });
  res.end(typeof payload === 'string' ? payload : JSON.stringify(payload));
}

function route(path, handler) {
  // Block body: configureServer must NOT return the connect app (Vite would
  // treat a returned function as a post-middleware hook and call it).
  const mount = (server) => {
    server.middlewares.use(path, (req, res, next) => {
      if (req.method !== 'GET') return sendJson(res, 405, { error: 'Method not allowed' });
      handler(req, res).catch(next);
    });
  };
  return { name: `api:${path}`, configureServer: mount, configurePreviewServer: mount };
}

// ---------------------------------------------------------------- CelesTrak
// Only allowlisted groups: never forward arbitrary strings upstream.
const TLE_GROUPS = new Set(['stations', 'visual', 'gps-ops', 'geo', 'starlink', 'weather']);
const tleLoaders = new Map();

function celestrakProxy() {
  return route('/api/tle', async (req, res) => {
    const group = new URL(req.url, 'http://x').searchParams.get('group') || 'stations';
    if (!TLE_GROUPS.has(group)) return sendJson(res, 400, { error: 'unknown group' });
    if (!tleLoaders.has(group)) {
      tleLoaders.set(
        group,
        createCachedResource({
          key: `tle-${group}`,
          ttlMs: 6 * 3600_000,
          disk: true,
          fetchUpstream: (signal) =>
            upstream(
              `https://celestrak.org/NORAD/elements/gp.php?GROUP=${group}&FORMAT=tle`,
              { headers: { 'User-Agent': '__APP_SLUG__/0.1 (dashboard)' } },
              signal,
            ),
        }),
      );
    }
    try {
      const r = await tleLoaders.get(group)();
      res.writeHead(200, { 'Content-Type': 'text/plain', 'X-Cache': r.state });
      res.end(r.body);
    } catch (e) {
      sendJson(res, e.status === 429 ? 429 : 502, { error: 'TLE source unavailable' });
    }
  });
}

// ---------------------------------------------------------------- OpenSky
// Anonymous works; OAuth client credentials raise the quota. Snapshot is the
// whole planet; the client filters to what it renders.
let openSkyToken = null;

async function openSkyAuthHeaders() {
  const id = process.env.OPENSKY_CLIENT_ID;
  const secret = process.env.OPENSKY_CLIENT_SECRET;
  if (!id || !secret) return {};
  if (openSkyToken && openSkyToken.exp > Date.now() + 60_000) {
    return { Authorization: `Bearer ${openSkyToken.value}` };
  }
  const res = await fetch(
    'https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ grant_type: 'client_credentials', client_id: id, client_secret: secret }),
      signal: AbortSignal.timeout(10_000),
    },
  );
  if (!res.ok) return {};
  const json = await res.json();
  openSkyToken = { value: json.access_token, exp: Date.now() + (json.expires_in ?? 1800) * 1000 };
  return { Authorization: `Bearer ${openSkyToken.value}` };
}

const openSky = createCachedResource({
  key: 'opensky',
  ttlMs: 15_000,
  fetchUpstream: async (signal) =>
    upstream('https://opensky-network.org/api/states/all', { headers: await openSkyAuthHeaders() }, signal),
});

function openSkyProxy() {
  return route('/api/flights', async (_req, res) => {
    try {
      const r = await openSky();
      sendJson(res, 200, r.body, { 'X-Cache': r.state, 'X-Snapshot-Age': String(Date.now() - r.at) });
    } catch (e) {
      sendJson(res, e.status === 429 ? 429 : 502, { error: 'Flight source unavailable' });
    }
  });
}

// ---------------------------------------------------------------- 404
function apiNotFound() {
  const mount = (server) => {
    server.middlewares.use('/api', (_req, res) => sendJson(res, 404, { error: 'Unknown API route' }));
  };
  return { name: 'api:not-found', configureServer: mount, configurePreviewServer: mount };
}

export function apiPlugins() {
  // Order matters: specific routes first, catch-all 404 last.
  return [celestrakProxy(), openSkyProxy(), apiNotFound()];
}
