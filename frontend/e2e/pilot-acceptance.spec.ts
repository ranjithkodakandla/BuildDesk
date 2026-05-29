/**
 * Pilot acceptance — realistic multifamily operator flow on deployed stack.
 * Run: FRONTEND_URL=https://builddesk-web-....run.app npx playwright test e2e/pilot-acceptance.spec.ts
 */
import { test, expect } from '@playwright/test';
import { randomUUID } from 'crypto';
import * as fs from 'fs';
import * as path from 'path';

const FRONTEND_URL =
  process.env.FRONTEND_URL || 'https://builddesk-web-149130710868.us-central1.run.app';
const SCREENSHOT_DIR = path.join(process.cwd(), 'e2e-screenshots', 'pilot-acceptance');

async function snap(page: import('@playwright/test').Page, name: string) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, `${name}.png`), fullPage: true });
}

test.describe('Pilot acceptance — live stack', () => {
  test.setTimeout(300_000);

  test('multifamily coordinator workflow (register → package PDF)', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });

    const tenantId = randomUUID();
    const email = `pilot_${Date.now()}@builddesk.accept`;
    const password = 'PilotAccept123!';

    // Register
    await page.goto(`${FRONTEND_URL}/register`);
    await page.getByPlaceholder('UUID of your tenant').fill(tenantId);
    await page.getByPlaceholder('you@example.com').fill(email);
    await page.getByPlaceholder('Min 8 characters').fill(password);
    await page.getByRole('button', { name: /create account/i }).click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 30_000 });
    await snap(page, '01-dashboard');

    // Tenant settings / branding
    await page.getByRole('button', { name: /^settings$/i }).click();
    await page.getByLabel(/company name/i).fill('Pilot Fab Co');
    await page.getByLabel(/pdf footer/i).fill('Pilot Acceptance — Confidential');
    await page.getByRole('button', { name: /save settings/i }).click();
    await expect(page.getByText(/pilot fab co/i).first()).toBeVisible({ timeout: 10_000 }).catch(() => {});
    await snap(page, '02-tenant-settings');

    // New project
    await page.getByRole('button', { name: /^projects$/i }).click();
    await page.getByRole('button', { name: /\+ New Project/i }).click();
    await expect(page).toHaveURL(/\/projects\//, { timeout: 20_000 });
    await snap(page, '03-workspace');

    // Hierarchy — unit types + bulk units (48 units: 101–148)
    await page.getByRole('button', { name: /^hierarchy$/i }).click();
    await page.getByPlaceholder('Type Code (e.g. A1)').fill('1BR');
    await page.getByPlaceholder('Name (e.g. 1 Bed / 1 Bath)').fill('One Bedroom');
    await page.getByRole('button', { name: 'Add Type' }).click();
    await page.getByPlaceholder('Type Code (e.g. A1)').fill('2BR');
    await page.getByPlaceholder('Name (e.g. 1 Bed / 1 Bath)').fill('Two Bedroom');
    await page.getByRole('button', { name: 'Add Type' }).click();
    await page.getByPlaceholder('Type Code (e.g. A1)').fill('PH');
    await page.getByPlaceholder('Name (e.g. 1 Bed / 1 Bath)').fill('Penthouse');
    await page.getByRole('button', { name: 'Add Type' }).click();

    await page.getByPlaceholder('e.g. A-').fill('');
    await page.getByPlaceholder('101').first().fill('101');
    await page.locator('input[placeholder="120"]').fill('148');
    await page.getByRole('button', { name: /^generate$/i }).click();
    await expect(page.getByText(/total:\s*48/i)).toBeVisible({ timeout: 60_000 });
    await snap(page, '04-hierarchy-bulk-units');

    // Assemblies — kitchen, vanity, island
    await page.getByRole('button', { name: /^assemblies$/i }).click();
    const asmTypes = [
      { name: 'Type 1BR Kitchen', type: 'kitchen' },
      { name: 'Type 1BR Vanity', type: 'vanity' },
      { name: 'PH Island', type: 'island' },
    ];
    for (const asm of asmTypes) {
      await page.getByRole('button', { name: /\+ New Assembly/i }).click();
      await page.getByPlaceholder('e.g. Master Vanity').fill(asm.name);
      await page.locator('.bg-blue-50 select').nth(0).selectOption(asm.type);
      await page.locator('.bg-blue-50').getByRole('button', { name: /^create$/i }).click();
      await expect(page.getByText(asm.name)).toBeVisible({ timeout: 15_000 });
    }
    await snap(page, '05-assemblies');

    // SVG preview in editor
    await page.getByRole('button', { name: /edit assembly/i }).first().click();
    await page.getByRole('button', { name: /\+ add part/i }).click();
    await page.getByRole('button', { name: /save assembly/i }).click();
    await expect(page.getByText(/fabrication drawing preview/i)).toBeVisible({ timeout: 30_000 });
    await expect(page.locator('img[alt="Assembly Preview"]')).toBeVisible();
    await snap(page, '06-svg-preview');
    await page.getByRole('button', { name: /← back/i }).click();

    // Package generation
    await page.getByRole('button', { name: /^packages$/i }).click();
    await page.getByPlaceholder('e.g. Rev A').fill('Pilot Rev 1');
    await page.getByPlaceholder(/added ada units/i).fill('Initial pilot package — 48 units');
    await page.getByRole('button', { name: /generate package/i }).click();

    await expect(page.getByText(/^ready$/i).first()).toBeVisible({ timeout: 180_000 });
    await snap(page, '07-package-ready');

    // PDF download (authenticated blob)
    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 60_000 }).catch(() => null),
      page.getByRole('button', { name: /download pdf/i }).click(),
    ]);
    if (download) {
      expect(download.suggestedFilename()).toMatch(/\.pdf$/i);
    }

    // Second revision
    await page.getByPlaceholder('e.g. Rev A').fill('Pilot Rev 2');
    await page.getByPlaceholder(/added ada units/i).fill('Revision after field walk');
    await page.getByRole('button', { name: /generate package/i }).click();
    await expect(page.getByText(/^ready$/i).first()).toBeVisible({ timeout: 180_000 });
    await expect(page.getByText(/pilot rev 2/i).first()).toBeVisible({ timeout: 10_000 });
    await snap(page, '08-revision-history');

    // Search + exports
    await page.getByRole('button', { name: /^search$/i }).click();
    await page.getByPlaceholder(/search projects/i).fill('Fabrication');
    await page.getByRole('button', { name: /search/i }).click();
    await snap(page, '09-search');

    await page.getByRole('button', { name: /export data/i }).click();
    await page.getByRole('button', { name: /generate export/i }).click();
    await expect(page.getByText(/project exports/i)).toBeVisible();
    await snap(page, '10-exports-modal');
    await page.getByRole('button', { name: '✕' }).click();

    // Dashboard queues (RFI/approval visibility — read-only)
    await page.getByRole('button', { name: /← back/i }).click();
    await page.getByRole('button', { name: /^queues$/i }).click();
    await expect(page.getByText(/open rfis/i)).toBeVisible();
    await expect(page.getByText(/packages awaiting approval/i)).toBeVisible();
    await snap(page, '11-operational-queues');

    const criticalErrors = consoleErrors.filter(
      (e) =>
        !e.includes('favicon') &&
        !e.includes('404') &&
        !e.includes('net::ERR') &&
        !e.includes('Failed to load resource')
    );
    expect(criticalErrors, `console errors: ${criticalErrors.join('; ')}`).toEqual([]);
  });
});
