import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

const apiProxy = {
  '/api': {
    target: 'http://localhost:8000',
    rewrite: (p: string) => p.replace(/^\/api/, ''),
  },
}

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  server: {
    proxy: apiProxy,
  },
  preview: {
    proxy: apiProxy,
  },
  build: {
    manifest: true,
    // PERF: raise warning threshold; large chunks are expected for recharts
    chunkSizeWarningLimit: 400,
    rollupOptions: {
      output: {
        // PERF: stable vendor chunks improve browser cache hit rate on
        // app-code-only changes; react/router/query are unlikely to change
        manualChunks(id) {
          if (id.includes('node_modules/react-dom') || id.includes('node_modules/react/')) return 'vendor-react'
          if (id.includes('node_modules/react-router-dom')) return 'vendor-router'
          if (id.includes('node_modules/@tanstack/react-query')) return 'vendor-query'
        },
      },
    },
  },
})
