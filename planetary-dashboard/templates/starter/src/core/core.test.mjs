import assert from 'node:assert/strict';
import { test } from 'node:test';
import { feedState, worstFeedState, ageLabel } from './feedState.js';
import { LayerManager } from './layerManager.js';
import { encodeState, decodeState } from './shareLink.js';
import { createRenderGovernor } from './renderGovernor.js';

test('feed state reduction', () => {
  assert.equal(feedState({ enabled: false }), 'off');
  assert.equal(feedState({ enabled: true, stats: { status: 'key-required' } }), 'unavailable');
  assert.equal(feedState({ enabled: true, stats: { error: 'x' } }), 'unavailable');
  assert.equal(feedState({ enabled: true, stats: { error: 'x', lastUpdate: 1 } }), 'degraded');
  assert.equal(feedState({ enabled: true, stats: { lastUpdate: 1, stale: true } }), 'stale');
  assert.equal(feedState({ enabled: true, stats: { lastUpdate: 1, fallback: true } }), 'fallback');
  assert.equal(feedState({ enabled: true, stats: { status: 'zoom-in' } }), 'nominal');
});

test('worst state covers every state, including partial', () => {
  assert.equal(worstFeedState(['nominal', 'partial']), 'partial');
  assert.equal(worstFeedState(['off', 'nominal', 'unavailable']), 'unavailable');
  assert.throws(() => worstFeedState(['bogus']));
});

test('age label', () => {
  assert.equal(ageLabel(0), 'never');
  assert.equal(ageLabel(1000, 3000), 'just now');
  assert.equal(ageLabel(0 + 1, 90_001), '2m ago');
});

test('layer manager serializes toggles and never double-polls', async () => {
  let enables = 0;
  const layer = { id: 'a', refreshInterval: 10_000, enable() { enables++; }, disable() {}, update() {} };
  const m = new LayerManager({});
  m.register(layer);
  await Promise.all([m.setEnabled('a', true), m.setEnabled('a', true), m.toggle('a'), m.toggle('a')]);
  assert.equal(enables, 2);
  assert.equal(m.isEnabled('a'), true);
  await m.destroyAll();
});

test('layer manager rejects duplicate ids', () => {
  const m = new LayerManager({});
  m.register({ id: 'x' });
  assert.throws(() => m.register({ id: 'x' }));
});

test('share link round-trip and unknown token rejection', () => {
  const tokens = { flights: 'f', satellites: 's' };
  const hash = encodeState(
    { camera: { lat: 30.26, lon: -97.74, alt: 1200, heading: 15, pitch: -30 }, style: 'nvg', layers: ['satellites', 'flights'] },
    tokens,
  );
  const s = decodeState(`#${hash}`, tokens);
  assert.deepEqual(s.layers.sort(), ['flights', 'satellites']);
  assert.equal(s.style, 'nvg');
  const bad = decodeState('#lat=1&lon=2&l=fZ', tokens);
  assert.deepEqual(bad.layers, []);
  assert.equal(bad.layersInvalid, true);
  assert.equal(decodeState('#lat=100&lon=2', tokens), null);
});

test('render governor holds continuous rendering', () => {
  const scene = { requestRenderMode: false, requestRender() {} };
  const g = createRenderGovernor(scene);
  assert.equal(scene.requestRenderMode, true);
  g.hold('tracking');
  assert.equal(scene.requestRenderMode, false);
  g.release('tracking');
  assert.equal(scene.requestRenderMode, true);
});
