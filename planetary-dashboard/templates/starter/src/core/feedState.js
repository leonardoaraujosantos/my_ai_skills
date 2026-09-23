// One feed-state vocabulary for panel, HUD and any AI agent.
// Keep EVERY state in SEVERITY — a missing entry silently drops a layer from
// "worst state" summaries.
export const FEED_STATES = ['unavailable', 'loading', 'degraded', 'stale', 'partial', 'fallback', 'nominal', 'off'];
const SEVERITY = Object.fromEntries(FEED_STATES.map((s, i) => [s, i]));

const GUIDANCE = new Set(['zoom-in', 'empty', 'idle']);

/**
 * Reduce a layer's stats to one feed state.
 * @param {{enabled:boolean, stats?:object}} layer
 */
export function feedState({ enabled, stats = {} }) {
  if (!enabled) return 'off';
  const { status, error, count = 0, lastUpdate, stale, partial, fallback, loading } = stats;
  if (GUIDANCE.has(status)) return 'nominal';
  if (['unavailable', 'offline', 'down', 'error', 'key-required'].includes(status)) return 'unavailable';
  if (error && !lastUpdate) return 'unavailable';
  if (loading && !lastUpdate) return 'loading';
  if (error) return 'degraded';
  if (stale) return 'stale';
  if (partial) return 'partial';
  if (fallback) return 'fallback';
  if (!lastUpdate && count === 0) return 'loading';
  return 'nominal';
}

/** Most severe state across layers (for HUD / agent summaries). */
export function worstFeedState(states) {
  let worst = 'off';
  for (const s of states) {
    if (!(s in SEVERITY)) throw new Error(`unknown feed state: ${s}`);
    if (SEVERITY[s] < SEVERITY[worst]) worst = s;
  }
  return worst;
}

export function ageLabel(lastUpdate, now = Date.now()) {
  if (!lastUpdate) return 'never';
  const s = Math.max(0, Math.round((now - lastUpdate) / 1000));
  if (s < 5) return 'just now';
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.round(s / 60)}m ago`;
  return `${Math.round(s / 3600)}h ago`;
}
