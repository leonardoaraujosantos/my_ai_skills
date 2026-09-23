// CelesTrak TLEs via the /api/tle proxy (disk-cached 6 h), propagated in the
// browser with SGP4 once per second. Point primitives scale to thousands.
import * as Cesium from 'cesium';
import { twoline2satrec, propagate, gstime, eciToGeodetic } from 'satellite.js';

const GROUPS = ['stations', 'visual', 'gps-ops', 'geo'];
const COLORS = { stations: '#fff6e5', visual: '#9fb3c4', 'gps-ops': '#4fd8ff', geo: '#c89bff' };

function parseTle(text, group) {
  const lines = text.split(/\r?\n/).map((l) => l.trimEnd()).filter(Boolean);
  const out = [];
  for (let i = 0; i + 2 < lines.length; i += 3) {
    const [name, l1, l2] = [lines[i], lines[i + 1], lines[i + 2]];
    if (!l1?.startsWith('1 ') || !l2?.startsWith('2 ')) continue;
    out.push({ name: name.trim(), norad: l1.slice(2, 7).trim(), group, satrec: twoline2satrec(l1, l2) });
  }
  return out;
}

export function createSatellitesLayer() {
  let points = null;
  let sats = [];
  let ticker = null;
  let stats = { count: 0, lastUpdate: 0, error: null };

  function tick(governor) {
    const now = new Date();
    const gmst = gstime(now);
    for (const s of sats) {
      const pv = propagate(s.satrec, now);
      const eci = pv?.position;
      if (!eci || typeof eci !== 'object') {
        s.point.show = false;
        continue;
      }
      const geo = eciToGeodetic(eci, gmst);
      s.point.position = Cesium.Cartesian3.fromRadians(geo.longitude, geo.latitude, geo.height * 1000);
      s.point.show = true;
      s.altKm = geo.height;
    }
    governor.requestRender();
  }

  return {
    id: 'satellites',
    name: 'Satellites',
    group: 'Space',
    source: 'CelesTrak',
    refreshInterval: 5 * 60_000,
    init({ viewer }) {
      points = viewer.scene.primitives.add(new Cesium.PointPrimitiveCollection());
      points.show = false;
    },
    enable({ governor }) {
      points.show = true;
      ticker = setInterval(() => tick(governor), 1000);
    },
    disable() {
      points.show = false;
      clearInterval(ticker);
    },
    async update({ governor }) {
      const results = await Promise.allSettled(
        GROUPS.map((g) => fetch(`/api/tle?group=${g}`).then((r) => (r.ok ? r.text() : Promise.reject(new Error(`HTTP ${r.status}`))))),
      );
      const failed = results.filter((r) => r.status === 'rejected').length;
      if (failed === GROUPS.length) {
        stats = { ...stats, error: 'CelesTrak unreachable' };
        return;
      }
      points.removeAll();
      const seen = new Set();
      sats = [];
      results.forEach((r, i) => {
        if (r.status !== 'fulfilled') return;
        for (const s of parseTle(r.value, GROUPS[i])) {
          if (seen.has(s.norad)) continue; // first group wins
          seen.add(s.norad);
          const isIss = s.norad === '25544';
          s.point = points.add({
            pixelSize: isIss ? 10 : 4,
            color: isIss ? Cesium.Color.RED : Cesium.Color.fromCssColorString(COLORS[s.group]),
            id: { kind: 'satellite', title: `${s.name} · NORAD ${s.norad}`, norad: s.norad },
          });
          sats.push(s);
        }
      });
      tick(governor);
      stats = { count: sats.length, lastUpdate: Date.now(), error: failed ? `${failed} group(s) unavailable` : null, partial: failed > 0 };
    },
    getStats: () => stats,
    getAnalystRecords: () => sats.map((s) => ({ id: s.norad, name: s.name, group: s.group, altitudeKm: s.altKm })),
  };
}
