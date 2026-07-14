import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

// https://vite.dev/config/
// `base` controls the public path the built assets are served from. In
// production the SPA is hosted on GitHub Pages under aguzmancruz.com/local-rag,
// so assets must resolve under /local-rag/. Dev keeps the root path.
// Override via BASE_PATH if the subpath ever changes.
export default defineConfig(({ command }) => ({
  base: command === 'build' ? process.env.BASE_PATH ?? '/local-rag/' : '/',
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
  },
}))
