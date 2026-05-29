import { test, expect } from '@playwright/test';
import { randomUUID } from 'crypto';

const FRONTEND_URL = process.env.FRONTEND_URL || 'https://builddesk-web-149130710868.us-central1.run.app';

test.describe('Workspace flows', () => {
  test('tenant settings, hierarchy, package tab, export modal', async ({ page }) => {
    const tenantId = randomUUID();
    const email = `ws_${Date.now()}@example.com`;
    const password = 'E2eWorkspace123!';

    await page.goto(`${FRONTEND_URL}/register`);
    await page.getByPlaceholder('UUID of your tenant').fill(tenantId);
    await page.getByPlaceholder('you@example.com').fill(email);
    await page.getByPlaceholder('Min 8 characters').fill(password);
    await page.getByRole('button', { name: /create account/i }).click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 20000 });

    await page.getByRole('button', { name: /^settings$/i }).click();
    await expect(page.getByText(/company name/i)).toBeVisible({ timeout: 15000 });

    await page.getByRole('button', { name: /^projects$/i }).click();
    await page.getByRole('button', { name: /\+ New Project/i }).click();
    await expect(page).toHaveURL(/\/projects\//, { timeout: 15000 });

    await page.getByRole('button', { name: /^hierarchy$/i }).click();
    await expect(page.getByText(/hierarchy/i).first()).toBeVisible();

    await page.getByRole('button', { name: /^packages$/i }).click();
    await expect(page.getByText(/fabrication package/i)).toBeVisible({ timeout: 10000 });

    await page.getByRole('button', { name: /export data/i }).click();
    await expect(page.getByText(/project exports/i)).toBeVisible();
    await page.getByRole('button', { name: '✕' }).click();
  });
});
