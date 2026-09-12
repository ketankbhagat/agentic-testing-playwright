import { defineConfig } from '@playwright/test';

// Read HEADED env var — start.sh sets this based on display availability
const isHeaded = process.env.HEADED !== 'false';

export default defineConfig({
  testDir: './tests',
  timeout: 60000,
  retries: 0,
  workers: 1,                        // Sequential — audience follows one test at a time
  use: {
    baseURL: 'https://www.saucedemo.com',
    headless: !isHeaded,              // VISIBLE by default, headless only if HEADED=false
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',       // Records video of failures for Allure report
    viewport: { width: 1280, height: 720 },
    launchOptions: {
      // slowMo is a launch option — Playwright silently ignores it directly under `use`
      slowMo: isHeaded ? 600 : 0,    // 600ms between actions when visible, instant when headless
    },
  },
  reporter: [
    ['list'],
    ['allure-playwright'],
  ],
});
