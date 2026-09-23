// Idle globe = no frames. Anything that animates takes a named hold; the
// scene renders continuously only while at least one hold exists.
export function createRenderGovernor(scene) {
  const holds = new Set();
  scene.requestRenderMode = true;
  scene.maximumRenderTimeChange = Infinity;
  const apply = () => {
    scene.requestRenderMode = holds.size === 0;
    scene.requestRender();
  };
  return {
    hold(owner) {
      holds.add(owner);
      apply();
    },
    release(owner) {
      if (holds.delete(owner)) apply();
    },
    requestRender() {
      scene.requestRender();
    },
    get holds() {
      return [...holds];
    },
  };
}
