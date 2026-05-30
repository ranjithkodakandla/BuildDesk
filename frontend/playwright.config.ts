import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 300_000,
  use: {
    headless: false,
    baseURL:
      process.env.FRONTEND_URL ||
      'https://builddesk-web-149130710868.us-central1.run.app',
    screenshot: 'on',
    trace: 'on',
    video: 'on',
    launchOptions: { slowMo: 500 },
  },
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'e2e-report' }]],
});
