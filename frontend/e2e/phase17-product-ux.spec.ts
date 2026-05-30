/**
 * Phase 17  visible product UX validation (headed).
 * Fails on console errors / failed API responses so issues surface without manual log review.
 */
import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://127.0.0.1:5174';

function attachDiagnostics(page: Page) {
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const failedRequests: string[] = [];

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });
  page.on('pageerror', (err) => {
    pageErrors.push(err.message);
  });
  page.on('response', (res) => {
    const url = res.url();
    if (url.includes('/api/v1/') && res.status() >= 400) {
      failedRequests.push(`${res.status()} ${url}`);
    }
  });

  return () => {
    const problems = [
      ...pageErrors.map((e) => `pageerror: ${e}`),
      ...consoleErrors.map((e) => `console.error: ${e}`),
      ...failedRequests.map((e) => `http: ${e}`),
    ].filter(
      (p) =>
        !p.includes('404') ||
        !p.includes('/package/status')
    );
    expect(problems, `Browser diagnostics:\n${problems.join('\n')}`).toEqual([]);
  };
}

test.describe('Phase 17 product UX', () => {
  test('register ? dashboard ? workspace tabs ? package panel', async ({ page }) => {
    test.setTimeout(300_000);
    const assertClean = attachDiagnostics(page);

    const ws = `Phase17 ${Date.now().toString(36)}`;
    const email = `p17_${Date.now()}@builddesk.accept`;
    const password = 'Phase17Test123!';

    // Registration (no tenant UUID)
    await page.goto(`${FRONTEND_URL}/register`);
    await page.getByTestId('register-workspace').fill(ws);
    await page.getByTestId('register-email').fill(email);
    await page.getByTestId('register-password').fill(password);
    await page.getByTestId('register-submit').click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 30_000 });

    // Dashboard loads projects list (was crashing with projects.map)
    await expect(page.getByRole('heading', { name: /operations/i })).toBeVisible();
    await expect(page.getByText(/loading projects/i)).toBeHidden({ timeout: 15_000 });

    // Create project  dashboard creates directly, no modal
    await page.getByRole('button', { name: /new project/i }).click();
    await expect(page).toHaveURL(/\/projects\//, { timeout: 20_000 });

    // Workspace navigation labels
    await expect(page.getByRole('button', { name: /^overview$/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /^units$/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /^fabrication$/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /^package$/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /^operations$/i })).toBeVisible();

    await page.getByRole('button', { name: /^overview$/i }).click();
    await expect(page.getByText(/project overview/i)).toBeVisible();

    await page.getByRole('button', { name: /^fabrication$/i }).click();
    await expect(page.getByRole('heading', { name: /^fabrication$/i })).toBeVisible();

    await page.getByRole('button', { name: /^package$/i }).click();
    await expect(page.getByText(/package status/i)).toBeVisible();

    assertClean();
  });

  test('login with email + password only', async ({ page }) => {
    test.setTimeout(120_000);
    const assertClean = attachDiagnostics(page);

    const ws = `LoginTest ${Date.now().toString(36)}`;
    const email = `login_${Date.now()}@builddesk.accept`;
    const password = 'LoginTest123!';

    await page.goto(`${FRONTEND_URL}/register`);
    await page.getByTestId('register-workspace').fill(ws);
    await page.getByTestId('register-email').fill(email);
    await page.getByTestId('register-password').fill(password);
    await page.getByTestId('register-submit').click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 30_000 });

    await page.getByRole('button', { name: /sign out/i }).click();
    await expect(page).toHaveURL(/\/login/, { timeout: 10_000 });

    await page.getByTestId('login-email').fill(email);
    await page.getByTestId('login-password').fill(password);
    await page.getByTestId('login-submit').click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 30_000 });
    await expect(page.getByText(/tenant uuid/i)).toHaveCount(0);

    assertClean();
  });
});
