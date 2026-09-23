// USGS M2.5+ past day. Keyless, CORS-enabled -> safe to fetch from the browser.
import * as Cesium from 'cesium';

const FEED = 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson';

export function createEarthquakesLayer() {
  let ds = null;
  let stats = { count: 0, lastUpdate: 0, error: null };
  let controller = null;

  return {
    id: 'earthquakes',
    name: 'Earthquakes (24h, M2.5+)',
    group: 'Events',
    source: 'USGS',
    refreshInterval: 60_000,
    async init({ viewer }) {
      ds = new Cesium.CustomDataSource('earthquakes');
      await viewer.dataSources.add(ds);
      ds.show = false;
    },
    enable() {
      ds.show = true;
    },
    disable() {
      ds.show = false;
      controller?.abort();
    },
    async update({ governor }) {
      controller?.abort();
      controller = new AbortController();
      try {
        const res = await fetch(FEED, { signal: AbortSignal.any([controller.signal, AbortSignal.timeout(15_000)]) });
        if (!res.ok) throw new Error(`USGS HTTP ${res.status}`);
        const { features } = await res.json();
        const seen = new Set();
        for (const f of features) {
          const [lon, lat, depthKm] = f.geometry?.coordinates ?? [];
          const mag = f.properties?.mag;
          if (!Number.isFinite(lat) || !Number.isFinite(lon) || !Number.isFinite(mag)) continue;
          seen.add(f.id);
          const color = depthKm < 70 ? Cesium.Color.RED : depthKm < 300 ? Cesium.Color.ORANGE : Cesium.Color.YELLOW;
          const entity = ds.entities.getById(f.id) ?? ds.entities.add({ id: f.id });
          entity.position = Cesium.Cartesian3.fromDegrees(lon, lat);
          entity.ellipse = {
            semiMajorAxis: 2 ** mag * 1000,
            semiMinorAxis: 2 ** mag * 1000,
            material: color.withAlpha(mag >= 5 ? 0.45 : 0.25),
            classificationType: Cesium.ClassificationType.TERRAIN, // drape; outlines unsupported when clamped
          };
          // Point keeps the event visible from orbit, where the ellipse is sub-pixel.
          entity.point = { pixelSize: 3 + mag * 1.5, color: color.withAlpha(0.9), outlineColor: Cesium.Color.BLACK, outlineWidth: 1 };
          entity.properties = { kind: 'earthquake', title: `M${mag.toFixed(1)} · ${f.properties.place ?? ''}`, depthKm, time: f.properties.time };
        }
        for (const e of [...ds.entities.values]) if (!seen.has(e.id)) ds.entities.remove(e);
        stats = { count: seen.size, lastUpdate: Date.now(), error: null };
      } catch (err) {
        if (err.name === 'AbortError') return;
        stats = { ...stats, error: err.message };
      }
      governor.requestRender();
    },
    getStats: () => stats,
    getAnalystRecords: () => ds?.entities.values.map((e) => ({ id: e.id, ...e.properties.getValue() })) ?? [],
  };
}
