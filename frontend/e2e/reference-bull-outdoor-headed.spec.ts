/**
 * VISIBLE validation replay for Bull Outdoor reference sheet.
 *
 * Run (browser window stays open — NOT headless):
 *   cd frontend
 *   REF_VALIDATION_EMAIL=... REF_VALIDATION_PASSWORD=... REF_VALIDATION_TENANT=... \
 *   REF_VALIDATION_PROJECT_ID=... \
 *   FRONTEND_URL=https://builddesk-web-149130710868.us-central1.run.app \
 *   npx playwright test e2e/reference-bull-outdoor-headed.spec.ts --headed --workers=1
 *
 * Credentials: artifacts/reference-validation/reference_seed_manifest.json
 */
import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const FRONTEND_URL =
  process.env.FRONTEND_URL || 'https://builddesk-web-149130710868.us-central1.run.app';

const ARTIFACT_DIR = path.resolve(
  __dirname,
  '../../artifacts/reference-validation/browser'
);

function loadManifest(): Record<string, string> {
  const p = path.resolve(
    __dirname,
    '../../artifacts/reference-validation/reference_seed_manifest.json'
  );
  if (fs.existsSync(p)) {
    return JSON.parse(fs.readFileSync(p, 'utf-8')) as Record<string, string>;
  }
  return {};
}

const manifest = loadManifest();

const email =
  process.env.REF_VALIDATION_EMAIL ||
  process.env.BULL_REF_EMAIL ||
  manifest.email;
const password =
  process.env.REF_VALIDATION_PASSWORD ||
  process.env.BULL_REF_PASSWORD ||
  manifest.password;
const tenantId =
  process.env.REF_VALIDATION_TENANT ||
  process.env.BULL_REF_TENANT ||
  manifest.tenant_id;
const projectId =
  process.env.REF_VALIDATION_PROJECT_ID ||
  process.env.BULL_REF_PROJECT_ID ||
  manifest.project_id;

async function snap(page: import('@playwright/test').Page, name: string) {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
  await page.screenshot({
    path: path.join(ARTIFACT_DIR, `${name}.png`),
    fullPage: true,
  });
}

test.describe('Reference PDF — visible operator replay', () => {
  test.skip(
    !email || !password || !tenantId || !projectId,
    'Set REF_VALIDATION_* env vars from reference_seed_manifest.json'
  );

  test('login → workspace → assemblies → package → download', async ({ page }) => {
    test.setTimeout(300_000);
    test.slow();

    const downloadPath = path.join(ARTIFACT_DIR, 'builddesk_browser_download.pdf');

    await page.goto(`${FRONTEND_URL}/login`, { waitUntil: 'domcontentloaded' });

    const tenantField = page.getByTestId('login-tenant-id').or(
      page.locator('input[placeholder="UUID of your tenant"]')
    );
    const emailField = page.getByTestId('login-email').or(page.locator('input[type="email"]'));
    const passwordField = page.getByTestId('login-password').or(
      page.locator('input[type="password"]')
    );

    await expect(tenantField).toBeVisible({ timeout: 20_000 });
    await expect(emailField).toBeVisible();
    await expect(passwordField).toBeVisible();

    await tenantField.fill(tenantId!);
    await emailField.fill(email!);
    await passwordField.fill(password!);

    await expect(tenantField).toHaveValue(tenantId!);
    await expect(emailField).toHaveValue(email!);
    await expect(passwordField).toHaveValue(password!);
    await snap(page, '01b-login-filled');

    const loginResponse = page.waitForResponse(
      (r) => r.url().includes('/auth/login') && r.request().method() === 'POST'
    );
    await page.getByTestId('login-submit').or(page.getByRole('button', { name: /sign in/i })).click();
    const loginRes = await loginResponse;
    expect(
      loginRes.status(),
      `login API returned ${loginRes.status()}: ${await loginRes.text()}`
    ).toBe(200);
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 30_000 });
    await snap(page, '02-dashboard');

    await page.goto(`${FRONTEND_URL}/projects/${projectId}`);
    await expect(page.getByText(/BULL OUTDOOR/i).first()).toBeVisible({ timeout: 20_000 });
    await snap(page, '03-project-overview');

    await page.getByRole('button', { name: /^assemblies$/i }).click();
    await expect(page.getByText(/Splashes \(3 sides Polish\)/i)).toBeVisible();
    await expect(page.getByText(/Piece 1/i).first()).toBeVisible();
    await snap(page, '04-assemblies-list');

    await page.getByRole('button', { name: /edit assembly/i }).first().click();
    await expect(page.getByText(/parts configuration/i)).toBeVisible();
    await page.waitForTimeout(2500);
    await snap(page, '05-assembly-editor');
    await page.getByRole('button', { name: /← back/i }).click();

    await page.getByRole('button', { name: /^packages$/i }).click();
    await expect(page.getByText(/ready/i).first()).toBeVisible({ timeout: 90_000 });
    await snap(page, '06-packages-ready');

    const downloadPromise = page.waitForEvent('download', { timeout: 60_000 });
    await page.getByRole('button', { name: /download pdf/i }).click();
    const download = await downloadPromise;
    await download.saveAs(downloadPath);
    expect(fs.existsSync(downloadPath)).toBeTruthy();
    const stat = fs.statSync(downloadPath);
    expect(stat.size).toBeGreaterThan(5000);
    await snap(page, '07-after-download');
  });
});
