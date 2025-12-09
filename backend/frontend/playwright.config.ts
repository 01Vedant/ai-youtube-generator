import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  reporter: [
    ["list"],
    ["html", { outputFolder: "artifacts/playwright-report", open: "never" }],
  ],
  timeout: 120_000,
  // Start backend (SIMULATE_RENDER=1) and frontend (Vite) for tests
  webServer: [
    {
      command: "uvicorn backend.backend.main:app --port 8000 --reload",
      url: "http://127.0.0.1:8000/docs",
      reuseExistingServer: true,
      timeout: 120_000,
      stdout: "pipe",
      stderr: "pipe",
      env: { SIMULATE_RENDER: "1" },
      cwd: "C:\\Users\\vedant.sharma\\Documents\\ai-youtube-generator",
    },
    {
      command: "C:\\Users\\vedant.sharma\\Documents\\node-v24.11.1-win-x64\\node.exe node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: true,
      timeout: 120_000,
      stdout: "pipe",
      stderr: "pipe",
      cwd: "C:\\Users\\vedant.sharma\\Documents\\ai-youtube-generator\\backend\\frontend",
    },
  ],
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
