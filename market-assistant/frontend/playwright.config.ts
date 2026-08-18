import { defineConfig } from "@playwright/test";

const PORT = 4173;
const baseURL = `http://127.0.0.1:${PORT}`;

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: "**/*.spec.ts",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: process.env.CI ? "github" : "list",
  // Snapshots are platform-specific; baselines are generated on Linux to match CI.
  snapshotPathTemplate: "{testDir}/__snapshots__/{testFilePath}/{arg}-{projectName}{ext}",
  expect: {
    toHaveScreenshot: { maxDiffPixelRatio: 0.03, animations: "disabled" },
  },
  use: {
    baseURL,
    trace: "on-first-retry",
  },
  projects: [
    { name: "desktop", use: { viewport: { width: 1440, height: 900 } } },
    { name: "mobile", use: { viewport: { width: 375, height: 812 } } },
  ],
  webServer: {
    command: `npm run build && npm run preview -- --port ${PORT} --strictPort --host 127.0.0.1`,
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    stdout: "pipe",
    stderr: "pipe",
    timeout: 180_000,
  },
});
