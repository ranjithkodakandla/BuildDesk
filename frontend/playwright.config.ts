import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 120_000,
  use: {
    baseURL: process.env.FRONTEND_URL || 'https://stonedesk-app.web.app',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'e2e-report' }]],
});
