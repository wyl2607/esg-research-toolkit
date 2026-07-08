import path from 'path'
import { defineConfig } from 'vitest/config'

// Unit tests only: Playwright e2e specs live in tests/*.spec.ts and are run
// separately via npm run test:playwright — keep them out of vitest's glob.
export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
})
