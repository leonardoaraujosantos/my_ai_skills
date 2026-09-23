// OpenSky state vectors via /api/flights (15 s server cache, cooldown on 429,
// serve-stale). Honest staleness: snapshot older than 120 s => STALE.
import * as Cesium from 'cesium';

const STALE_MS = 120_000;

export function createFlightsLayer() {
  let points = null;
  const byId = new Map();
  let stats = { count: 0, lastUpdate: 0, error: null };

  return {
    id: 'flights',
    name: 'Flights',
    group: 'Movement',
    source: 'OpenSky',
    refreshInterval: 30_000,
    init({ viewer }) {
      points = viewer.scene.primitives.add(new Cesium.PointPrimitiveCollection());
      points.show = false;
    },
    enable() {
      points.show = true;
    },
    disable() {
      points.show = false;
    },
    async update({ governor }) {
      try {
        const res = await fetch('/api/flights', { signal: AbortSignal.timeout(25_000) });
        if (!res.ok) throw new Error(res.status === 429 ? 'OpenSky rate limited' : `HTTP ${res.status}`);
        const cacheState = res.headers.get('X-Cache');
        const json = await res.json();
        const seen = new Set();
        for (const s of json.states ?? []) {
          const [icao, callsign, country, , , lon, lat, baroAlt, onGround, velocity, track, , , geoAlt] = s;
          if (!icao || !Number.isFinite(lat) || !Number.isFinite(lon)) continue;
          seen.add(icao);
          const alt = Number.isFinite(geoAlt) ? geoAlt : Number.isFinite(baroAlt) ? baroAlt : onGround ? 0 : 10_000;
          let p = byId.get(icao);
          if (!p) {
            p = points.add({ pixelSize: 5, color: Cesium.Color.WHITE });
            byId.set(icao, p);
          }
          p.position = Cesium.Cartesian3.fromDegrees(lon, lat, alt);
          p.color = onGround ? Cesium.Color.GRAY : Cesium.Color.WHITE;
          p.id = { kind: 'aircraft', title: `${(callsign || icao).trim()} · ${country} · ${Math.round(alt)} m · ${Math.round((velocity ?? 0) * 1.944)} kt`, track };
        }
        for (const [id, p] of byId) {
          if (!seen.has(id)) {
            points.remove(p);
            byId.delete(id);
          }
        }
        const snapshotMs = (json.time ?? 0) * 1000;
        stats = {
          count: byId.size,
          lastUpdate: snapshotMs || Date.now(),
          error: null,
          stale: !snapshotMs || Date.now() - snapshotMs > STALE_MS || cacheState?.startsWith('STALE'),
        };
      } catch (err) {
        stats = { ...stats, error: err.message };
      }
      governor.requestRender();
    },
    getStats: () => stats,
  };
}
