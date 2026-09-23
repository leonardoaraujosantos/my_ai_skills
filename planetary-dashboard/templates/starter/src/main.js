// __APP_NAME__ — keyless-first 3D planetary dashboard.
// Imagery: Google 3D (key) > Esri World Imagery > OSM. Terrain: ion (token) > Re:Earth > ellipsoid.
import * as Cesium from 'cesium';
import { LayerManager } from './core/layerManager.js';
import { feedState, ageLabel } from './core/feedState.js';
import { encodeState, decodeState } from './core/shareLink.js';
import { createRenderGovernor } from './core/renderGovernor.js';
import { createSensorStyles, STYLE_IDS } from './sensorStyles.js';
import { createEarthquakesLayer } from './layers/earthquakes.js';
import { createSatellitesLayer } from './layers/satellites.js';
import { createFlightsLayer } from './layers/flights.js';

const ION_TOKEN = import.meta.env.VITE_CESIUM_ION_TOKEN || '';
const GOOGLE_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '';
const ESRI = 'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
const REEARTH_TERRAIN = 'https://terrain.reearth.land/cesium-mesh/ellipsoid';
const LAYER_TOKENS = { flights: 'f', satellites: 's', earthquakes: 'e' };

const $ = (sel) => document.querySelector(sel);

function toast(msg) {
  const el = $('#toast');
  el.textContent = msg;
  el.hidden = false;
  clearTimeout(toast.t);
  toast.t = setTimeout(() => (el.hidden = true), 2000);
}

async function createViewer() {
  if (ION_TOKEN) Cesium.Ion.defaultAccessToken = ION_TOKEN;
  const viewer = new Cesium.Viewer('globe', {
    animation: false, timeline: false, baseLayerPicker: false, geocoder: false, homeButton: false,
    sceneModePicker: false, navigationHelpButton: false, fullscreenButton: false, infoBox: false,
    selectionIndicator: false, baseLayer: false, msaaSamples: 4, creditContainer: $('#credits'),
  });
  viewer.scene.globe.enableLighting = true;

  // Imagery with automatic Esri -> OSM fallback after repeated tile failures.
  const esri = new Cesium.UrlTemplateImageryProvider({ url: ESRI, maximumLevel: 19, credit: 'Powered by Esri' });
  let esriFailures = 0;
  esri.errorEvent.addEventListener(() => {
    if (++esriFailures !== 3) return;
    viewer.imageryLayers.removeAll();
    viewer.imageryLayers.addImageryProvider(new Cesium.OpenStreetMapImageryProvider({ url: 'https://tile.openstreetmap.org/' }));
    toast('Esri imagery unavailable; using OSM');
  });
  viewer.imageryLayers.addImageryProvider(esri);

  // Terrain: ion World Terrain if a token exists, else keyless Re:Earth, else flat.
  try {
    viewer.terrainProvider = ION_TOKEN
      ? await Cesium.createWorldTerrainAsync()
      : await Cesium.CesiumTerrainProvider.fromUrl(REEARTH_TERRAIN);
  } catch (err) {
    console.warn('terrain unavailable, using ellipsoid', err);
  }

  // Optional photoreal upgrade.
  if (GOOGLE_KEY) {
    try {
      Cesium.GoogleMaps.defaultApiKey = GOOGLE_KEY;
      const tiles = await Cesium.createGooglePhotorealistic3DTileset();
      viewer.scene.primitives.add(tiles);
      viewer.scene.globe.show = false;
    } catch (err) {
      console.warn('Google 3D Tiles unavailable; keeping keyless globe', err);
    }
  }
  return viewer;
}

function cameraState(viewer) {
  const c = viewer.camera.positionCartographic;
  return {
    lat: Cesium.Math.toDegrees(c.latitude),
    lon: Cesium.Math.toDegrees(c.longitude),
    alt: c.height,
    heading: Math.round(Cesium.Math.toDegrees(viewer.camera.heading)) % 360,
    pitch: Cesium.Math.toDegrees(viewer.camera.pitch),
  };
}

function renderLayerPanel(manager) {
  const list = $('#layer-list');
  list.replaceChildren(
    ...manager.snapshot().map((l) => {
      const state = feedState(l);
      const li = document.createElement('li');
      li.className = 'layer-row';
      const name = Object.assign(document.createElement('span'), { className: 'name', textContent: l.name });
      const btn = Object.assign(document.createElement('button'), { type: 'button', className: 'state', textContent: state.toUpperCase() });
      btn.dataset.state = state;
      btn.setAttribute('role', 'switch');
      btn.setAttribute('aria-checked', String(l.enabled));
      btn.setAttribute('aria-label', `${l.name}: ${state}`);
      btn.addEventListener('click', () => manager.toggle(l.id));
      const meta = document.createElement('span');
      meta.className = 'meta';
      const s = l.stats;
      meta.textContent = l.enabled
        ? [l.source, s.count ? `${s.count.toLocaleString()} items` : null, ageLabel(s.lastUpdate), s.error].filter(Boolean).join(' · ')
        : l.source;
      li.append(name, btn, meta);
      return li;
    }),
  );
}

async function main() {
  const viewer = await createViewer();
  const governor = createRenderGovernor(viewer.scene);
  const styles = createSensorStyles(viewer);
  const manager = new LayerManager({ viewer, governor });
  [createFlightsLayer(), createSatellitesLayer(), createEarthquakesLayer()].forEach((l) => manager.register(l));

  // Panel re-renders on every layer event and ticks ages once a second.
  manager.subscribe(() => renderLayerPanel(manager));
  setInterval(() => renderLayerPanel(manager), 1000);
  renderLayerPanel(manager);

  // Share-link writer (declared before anything that can trigger it).
  let hashTimer = null;
  function writeHash() {
    clearTimeout(hashTimer);
    hashTimer = setTimeout(() => {
      const layers = manager.snapshot().filter((l) => l.enabled).map((l) => l.id);
      history.replaceState(null, '', `#${encodeState({ camera: cameraState(viewer), style: styles.current, layers }, LAYER_TOKENS)}`);
    }, 500);
  }

  // Sensor style chips (keys 1..N).
  const chips = $('#style-chips');
  STYLE_IDS.forEach((id, i) => {
    const b = Object.assign(document.createElement('button'), { type: 'button', textContent: `${i + 1} ${id.toUpperCase()}` });
    b.dataset.style = id;
    b.addEventListener('click', () => applyStyle(id));
    chips.append(b);
  });
  function applyStyle(id) {
    styles.set(id);
    chips.querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.style === styles.current)));
    writeHash();
  }

  // Share links: restore first, then write on camera/layer changes (debounced).
  const restored = decodeState(location.hash, LAYER_TOKENS);
  if (restored) {
    const c = restored.camera;
    viewer.camera.setView({
      destination: Cesium.Cartesian3.fromDegrees(c.lon, c.lat, c.alt),
      orientation: { heading: Cesium.Math.toRadians(c.heading), pitch: Cesium.Math.toRadians(c.pitch), roll: 0 },
    });
    applyStyle(restored.style);
    for (const id of restored.layers) manager.setEnabled(id, true);
  } else {
    viewer.camera.setView({ destination: Cesium.Cartesian3.fromDegrees(-30, 25, 22_000_000) });
    applyStyle('normal');
  }
  viewer.camera.moveEnd.addEventListener(writeHash);
  manager.subscribe((e) => e.type === 'visibility' && writeHash());

  // HUD readout (MSL/geoid correction left as an exercise: see references/rendering.md A5).
  viewer.camera.changed.addEventListener(() => {
    const c = cameraState(viewer);
    $('#hud').textContent = `LAT ${c.lat.toFixed(4)}  LON ${c.lon.toFixed(4)}  ALT ${(c.alt / 1000).toFixed(1)} KM  HDG ${Math.round((c.heading + 360) % 360)}°`;
  });
  viewer.camera.percentageChanged = 0.01;

  // Click-to-inspect (6 px drag tolerance) + Escape to dismiss.
  const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
  let down = null;
  handler.setInputAction((e) => (down = e.position), Cesium.ScreenSpaceEventType.LEFT_DOWN);
  handler.setInputAction((e) => {
    if (!down || Cesium.Cartesian2.distance(down, e.position) > 6) return;
    const picked = viewer.scene.pick(e.position);
    const info = picked?.id?.properties?.getValue?.() ?? picked?.id;
    const card = $('#card');
    if (info?.title) {
      card.textContent = info.title;
      card.hidden = false;
    } else card.hidden = true;
  }, Cesium.ScreenSpaceEventType.LEFT_UP);

  // Globe actions.
  $('#btn-share').addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(location.href);
      toast('Link copied');
    } catch {
      toast('Copy blocked — use the address bar');
    }
  });
  $('#btn-globe').addEventListener('click', () => {
    const c = cameraState(viewer);
    viewer.camera.flyTo({ destination: Cesium.Cartesian3.fromDegrees(c.lon, Math.max(-60, Math.min(60, c.lat)), 18_000_000), duration: 2.8 });
  });
  $('#btn-north').addEventListener('click', () => rotateAroundCentre(viewer, { heading: 0 }));
  $('#btn-tilt').addEventListener('click', (e) => {
    const tilted = e.currentTarget.getAttribute('aria-pressed') === 'true';
    rotateAroundCentre(viewer, { pitch: tilted ? -89 : -35 });
    e.currentTarget.setAttribute('aria-pressed', String(!tilted));
  });

  document.addEventListener('keydown', (e) => {
    if (e.target.closest('input, textarea, select') || e.metaKey || e.ctrlKey || e.altKey) return;
    const n = Number(e.key);
    if (n >= 1 && n <= STYLE_IDS.length) applyStyle(STYLE_IDS[n - 1]);
    if (e.key === 'Escape') $('#card').hidden = true;
  });

  // Hidden tab: stop rendering entirely.
  document.addEventListener('visibilitychange', () => (viewer.useDefaultRenderLoop = !document.hidden));
  window.__dashboard = { viewer, manager, governor, styles };
}

// Keep the ground point under the screen centre fixed while changing heading/pitch.
function rotateAroundCentre(viewer, { heading, pitch }) {
  const scene = viewer.scene;
  const centre = new Cesium.Cartesian2(scene.canvas.clientWidth / 2, scene.canvas.clientHeight / 2);
  const target = scene.pickPosition(centre) ?? viewer.camera.pickEllipsoid(centre);
  if (!target) return;
  const range = Cesium.Cartesian3.distance(viewer.camera.positionWC, target);
  viewer.camera.flyToBoundingSphere(new Cesium.BoundingSphere(target, 1), {
    offset: new Cesium.HeadingPitchRange(
      heading !== undefined ? Cesium.Math.toRadians(heading) : viewer.camera.heading,
      pitch !== undefined ? Cesium.Math.toRadians(pitch) : viewer.camera.pitch,
      range,
    ),
    duration: 0.65,
  });
}

main().catch((err) => {
  console.error(err);
  const p = Object.assign(document.createElement('p'), { className: 'toast', textContent: `Startup failed: ${err.message ?? err}` });
  p.setAttribute('role', 'alert');
  document.body.append(p);
});
