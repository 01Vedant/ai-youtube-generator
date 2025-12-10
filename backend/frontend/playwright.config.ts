import { defineConfig, devices } from '@playwright/test';
import * as path from 'path';
import { fileURLToPath } from 'url';

// ESM-safe path helpers
const __filename = fileURLToPath(import.meta.url);
const __dirname  = path.dirname(__filename);

const REPO_ROOT     = path.resolve(__dirname, '..', '..');   // <repo>
const FRONTEND_DIR  = __dirname;                              // <repo>/backend/frontend

const isWin  = process.platform === 'win32';
const nodeExe = isWin
  ? 'C:\\\\Users\\\\vedant.sharma\\\\Documents\\\\node-v24.11.1-win-x64\\\\node.exe'
  : 'node';

const viteCmd = `${nodeExe} node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort`;

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: { timeout: 10_000 },
  retries: process.env.CI ? 2 : 0,
  grepInvert: process.env.CI ? /@quarantine/ : undefined,
  reporter: [
    ['list'],
    ['html',  { outputFolder: path.join(FRONTEND_DIR, 'artifacts', 'playwright-report'), open: 'never' }],
    ['junit', { outputFile:   path.join(FRONTEND_DIR, 'artifacts', 'playwright', 'junit.xml') }],
    ['blob',  { outputFile:   path.join(FRONTEND_DIR, 'artifacts', 'playwright', 'blob-report') }],
  ],
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  webServer: [
    {
      // run from repo root so "backend.backend.main" imports correctly
      command: 'uvicorn backend.backend.main:app --port 8000',
      url: 'http://127.0.0.1:8000/docs',
      cwd: REPO_ROOT,
      env: { SIMULATE_RENDER: '1' },
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      stdout: 'pipe',
      stderr: 'pipe',
    },
    {
      // run vite from the frontend dir with absolute node on Windows
      command: viteCmd,
      url: 'http://127.0.0.1:5173',
      cwd: FRONTEND_DIR,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      stdout: 'pipe',
      stderr: 'pipe',
    },
  ],
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
