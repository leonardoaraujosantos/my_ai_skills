// Copy Cesium's static runtime (workers, assets, widgets) into public/cesium so
// it is served same-origin. Avoids vite-plugin-cesium, which breaks under some
// bundler setups (SvelteKit prod builds). index.html sets CESIUM_BASE_URL.
import { cpSync, existsSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const src = join(root, 'node_modules/cesium/Build/Cesium');
const dest = join(root, 'public/cesium');
if (!existsSync(src)) {
  console.error('cesium not installed — run npm install first');
  process.exit(1);
}
mkdirSync(dest, { recursive: true });
for (const dir of ['Workers', 'Assets', 'ThirdParty', 'Widgets']) {
  cpSync(join(src, dir), join(dest, dir), { recursive: true });
}
console.log('Cesium assets copied to public/cesium');
