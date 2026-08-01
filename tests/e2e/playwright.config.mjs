/* e2e config — drives the real service (site + /v1 on one origin).
 *
 * The service is started for the run by webServer below: uvicorn on 8801,
 * mock judge, no Redis (it degrades), no rate limit. Nothing here needs a
 * key or the network. `make test-e2e`.
 */
import { defineConfig, devices } from "@playwright/test";

const PORT = 8801;

export default defineConfig({
  testDir: ".",
  testMatch: "*.spec.mjs",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "line" : [["list"]],
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
  webServer: {
    command: `.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port ${PORT}`,
    url: `http://127.0.0.1:${PORT}/v1/healthz`,
    cwd: "../..",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
    env: {
      PB_DEFAULT_JUDGE: "mock",
      PB_ANTHROPIC_API_KEY: "",
      PB_REDIS_URL: "redis://127.0.0.1:6390/0",
      PB_RATE_LIMIT_PER_MINUTE: "0",
    },
  },
});
