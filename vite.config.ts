import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'node:path';

export default defineConfig({
  root: resolve(__dirname, 'apps/desktop'),
  base: './',
  plugins: [react()],
  build: { outDir: resolve(__dirname, 'dist'), emptyOutDir: true },
  test: { globals: true, environment: 'jsdom', setupFiles: resolve(__dirname, 'apps/desktop/src/renderer/test/setup.ts') }
});
