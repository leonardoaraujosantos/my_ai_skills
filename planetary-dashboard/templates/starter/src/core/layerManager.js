// Owns every data layer. Serializes transitions per layer (no double polling
// intervals), skips overlapping refreshes, and publishes change events.
//
// Layer contract:
//   { id, name, group, source, refreshInterval?, requiresKey?,
//     init(ctx), enable(ctx), disable(ctx), update(ctx) -> bool, destroy?(),
//     getStats() -> {count, lastUpdate, status, error, stale, fallback, ...},
//     getAnalystRecords?() }
export class LayerManager {
  constructor(ctx) {
    this.ctx = ctx;
    this.layers = new Map();
    this.listeners = new Set();
  }

  register(layer) {
    if (!layer?.id) throw new Error('layer needs a stable id');
    if (this.layers.has(layer.id)) throw new Error(`duplicate layer id: ${layer.id}`);
    this.layers.set(layer.id, { layer, enabled: false, intent: false, initialized: false, timer: null, busy: false, chain: Promise.resolve() });
  }

  subscribe(fn) {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  emit(type, id) {
    for (const fn of this.listeners) fn({ type, id });
  }

  isEnabled(id) {
    return this.layers.get(id)?.enabled ?? false;
  }

  setEnabled(id, enabled) {
    const entry = this.layers.get(id);
    if (!entry) throw new Error(`unknown layer: ${id}`);
    entry.intent = enabled; // latest request wins; toggle() reads this, not the settled state
    entry.chain = entry.chain
      .then(() => (enabled ? this.#enable(entry) : this.#disable(entry)))
      .catch((err) => {
        console.warn(`[layer ${id}] transition failed`, err);
        this.emit('error', id);
      });
    return entry.chain;
  }

  toggle(id) {
    const entry = this.layers.get(id);
    if (!entry) throw new Error(`unknown layer: ${id}`);
    return this.setEnabled(id, !entry.intent);
  }

  async #enable(entry) {
    if (entry.enabled) return;
    const { layer } = entry;
    if (!entry.initialized) {
      await layer.init?.(this.ctx);
      entry.initialized = true;
    }
    await layer.enable?.(this.ctx);
    entry.enabled = true;
    this.emit('visibility', layer.id);
    await this.refresh(layer.id);
    if (!entry.enabled) return; // disabled while the first refresh ran
    if (layer.refreshInterval > 0) {
      clearInterval(entry.timer);
      entry.timer = setInterval(() => this.refresh(layer.id), layer.refreshInterval);
      entry.timer?.unref?.(); // Node (tests): don't keep the process alive
    }
  }

  async #disable(entry) {
    if (!entry.enabled) return;
    clearInterval(entry.timer);
    entry.timer = null;
    entry.enabled = false;
    await entry.layer.disable?.(this.ctx);
    this.emit('visibility', entry.layer.id);
  }

  async refresh(id) {
    const entry = this.layers.get(id);
    if (!entry?.enabled || entry.busy) return;
    entry.busy = true;
    try {
      await entry.layer.update?.(this.ctx);
    } catch (err) {
      console.warn(`[layer ${id}]`, err);
    } finally {
      entry.busy = false;
      this.emit('data', id);
    }
  }

  snapshot() {
    return [...this.layers.values()].map(({ layer, enabled }) => ({
      id: layer.id,
      name: layer.name,
      group: layer.group,
      source: layer.source,
      enabled,
      stats: layer.getStats?.() ?? {},
    }));
  }

  async destroyAll() {
    for (const entry of this.layers.values()) {
      await this.#disable(entry);
      await entry.layer.destroy?.();
    }
    this.layers.clear();
  }
}
