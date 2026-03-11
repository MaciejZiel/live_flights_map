import { defineConfig } from "@playwright/test";

const CHROME_EXECUTABLE = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || "/usr/bin/google-chrome";
const PORT = Number(process.env.PLAYWRIGHT_PORT || "4178");
const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || `http://127.0.0.1:${PORT}`;
const SKIP_WEBSERVER = process.env.PLAYWRIGHT_SKIP_WEBSERVER === "1";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30000,
  fullyParallel: true,
  use: {
    baseURL: BASE_URL,
    headless: true,
    viewport: { width: 1440, height: 960 },
    launchOptions: {
      executablePath: CHROME_EXECUTABLE,
      args: ["--no-sandbox"],
    },
  },
  ...(SKIP_WEBSERVER
    ? {}
    : {
        webServer: {
          command: `npm run dev -- --host 127.0.0.1 --port ${PORT}`,
          cwd: ".",
          url: BASE_URL,
          reuseExistingServer: true,
          timeout: 120000,
        },
      }),
});
