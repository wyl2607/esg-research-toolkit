import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { defineConfig, devices } from '@playwright/test'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const repoRoot = path.resolve(__dirname, '..')
const localPython = path.join(repoRoot, '.venv', 'bin', 'python')
const pythonCommand = process.env.ESG_PYTHON_CMD || (fs.existsSync(localPython) ? localPython : 'python')
const frontendPort = process.env.ESG_FRONTEND_PORT || '4173'
const baseURL = process.env.ESG_FRONTEND_URL || `http://127.0.0.1:${frontendPort}`
const apiPort = process.env.ESG_API_PORT || '8001'
const browserChannel = process.env.ESG_PW_CHANNEL || 'chrome'
const skipWebServer = process.env.ESG_PW_SKIP_WEBSERVER === '1'

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'desktop-chrome',
      use: {
        ...devices['Desktop Chrome'],
        browserName: 'chromium',
        channel: browserChannel,
      },
    },
    {
      name: 'mobile-chrome',
      use: {
        ...devices['Pixel 7'],
        browserName: 'chromium',
        channel: browserChannel,
      },
    },
  ],
  webServer: skipWebServer
    ? undefined
    : [
        {
          command: `${pythonCommand} -m uvicorn main:app --host 127.0.0.1 --port ${apiPort}`,
          cwd: repoRoot,
          url: `http://127.0.0.1:${apiPort}/health`,
          reuseExistingServer: !process.env.CI,
          timeout: 120_000,
        },
        {
          command: `ESG_API_PORT=${apiPort} npm run dev -- --host 127.0.0.1 --port ${frontendPort}`,
          cwd: __dirname,
          url: baseURL,
          reuseExistingServer: !process.env.CI,
          timeout: 120_000,
        },
      ],
})
