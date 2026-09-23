import { defineConfig } from 'vite';
import { apiPlugins } from './server/proxies.js';

export default defineConfig({
  plugins: apiPlugins(),
  server: {
    host: 'localhost',
    port: 4173,
    fs: { deny: ['.env', '.env.*', '*.pem', '.git/**'] },
    headers: { 'X-Frame-Options': 'DENY', 'Content-Security-Policy': "frame-ancestors 'none'" },
  },
  preview: { port: 4173 },
  build: { chunkSizeWarningLimit: 5000 },
});
