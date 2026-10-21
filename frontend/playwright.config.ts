import { defineConfig, devices } from "@playwright/test";
import { platform } from "os";

export const STORAGE_STATE = "playwright/.auth/user.json";

const getStartScript = () => {
  const p = platform();
  if (p === "win32") return "scripts/start-windows.ps1";
  if (p === "darwin") return "scripts/start-mac.sh";
  return "scripts/start-linux.sh";
};

export default defineConfig({
  testDir: "./tests",
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:8000",
    trace: "retain-on-failure",
  },
  webServer: {
    command: getStartScript(),
    url: "http://127.0.0.1:8000",
    cwd: "..",
    reuseExistingServer: true,
    timeout: 120_000,
  },
  projects: [
    // Signs in once and saves the cookie, so the suite does not hit the sign-in rate limit.
    { name: "setup", testMatch: /auth\.setup\.ts/ },
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], storageState: STORAGE_STATE },
      dependencies: ["setup"],
    },
  ],
});
