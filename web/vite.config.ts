import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The dev server proxies the API to uvicorn, so the frontend talks to the same
// origin in development and in production and never needs to know a base URL.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: { outDir: 'dist', sourcemap: true },
})
