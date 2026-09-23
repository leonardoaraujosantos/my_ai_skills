// URL hash <-> view state. Camera + style + layers. Tokens keep links short;
// an unknown token rejects the whole layer payload (camera still restores).
export function encodeState({ camera, style, layers }, tokens) {
  const p = new URLSearchParams();
  p.set('v', '1');
  p.set('lat', camera.lat.toFixed(4));
  p.set('lon', camera.lon.toFixed(4));
  p.set('alt', String(Math.round(camera.alt)));
  p.set('heading', String(Math.round(camera.heading)));
  p.set('pitch', String(Math.round(camera.pitch)));
  if (style && style !== 'normal') p.set('style', style);
  const l = layers.map((id) => tokens[id]).filter(Boolean).sort().join('');
  if (l) p.set('l', l);
  return p.toString();
}

export function decodeState(hash, tokens) {
  const p = new URLSearchParams(hash.replace(/^#/, ''));
  const lat = Number(p.get('lat'));
  const lon = Number(p.get('lon'));
  if (!p.has('lat') || !p.has('lon') || !Number.isFinite(lat) || !Number.isFinite(lon)) return null;
  if (Math.abs(lat) > 90 || Math.abs(lon) > 180) return null;
  const num = (k, d) => (Number.isFinite(Number(p.get(k))) && p.has(k) ? Number(p.get(k)) : d);
  const byToken = Object.fromEntries(Object.entries(tokens).map(([id, t]) => [t, id]));
  const raw = p.get('l') ?? '';
  let layers = [];
  let layersInvalid = false;
  if (raw.length > 64) layersInvalid = true;
  else {
    for (const ch of raw) {
      if (!byToken[ch]) {
        layersInvalid = true;
        break;
      }
      layers.push(byToken[ch]);
    }
  }
  if (layersInvalid) layers = [];
  return {
    camera: {
      lat,
      lon,
      alt: Math.min(Math.max(num('alt', 800), 1), 5e7),
      heading: num('heading', 0),
      pitch: Math.min(Math.max(num('pitch', -35), -90), 0),
    },
    style: p.get('style') || 'normal',
    layers,
    layersInvalid,
  };
}
