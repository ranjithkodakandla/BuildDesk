/**
 * Live E2E smoke — deployed frontend vs deployed API.
 * Run: FRONTEND_URL=... npx playwright test e2e/live-smoke.spec.ts
 */
import { test, expect } from '@playwright/test';
import { randomUUID } from 'crypto';

const FRONTEND_URL = process.env.FRONTEND_URL || 'https://stonedesk-app.web.app';
const tenantId = randomUUID();
const email = `e2e_${Date.now()}@example.com`;
const password = 'E2eTestPass123!';

test.describe('BuildDesk live E2E', () => {
  test('register → dashboard → project workspace', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });

    await page.goto(`${FRONTEND_URL}/register`);
    await page.getByPlaceholder('UUID of your tenant').fill(tenantId);
    await page.getByPlaceholder('you@example.com').fill(email);
    await page.getByPlaceholder('Min 8 characters').fill(password);
    await page.getByRole('button', { name: /create account/i }).click();

    await expect(page).toHaveURL(/\/dashboard/, { timeout: 20000 });
    await expect(page.getByText(/BuildDesk/i).first()).toBeVisible();

    await page.getByRole('button', { name: /\+ New Project/i }).click();
    await expect(page).toHaveURL(/\/projects\//, { timeout: 15000 });

    const criticalErrors = consoleErrors.filter(
      (e) => !e.includes('favicon') && !e.includes('404') && !e.includes('net::ERR')
    );
    expect(criticalErrors, `console errors: ${criticalErrors.join('; ')}`).toEqual([]);
  });
});
