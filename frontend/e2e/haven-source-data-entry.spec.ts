/**
 * Slow visible demo: enter Haven SourceData (sheet 101-01) through the UI.
 * Data extracted from SourceData_export (29).xlsx
 */
import { test, expect, type Page } from '@playwright/test';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const FIXTURE = JSON.parse(
  readFileSync(join(__dirname, 'fixtures/haven-source-data-sample.json'), 'utf-8')
);

const PAUSE_MS = 1200;

test.use({ launchOptions: { slowMo: 900 } });

async function pause(page: Page, ms = PAUSE_MS) {
  await page.waitForTimeout(ms);
}

test.describe('Haven SourceData ù slow browser entry', () => {
  test('register ? project ? units ? fabrication parts ? package', async ({ page }) => {
    test.setTimeout(600_000);

    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error' && !msg.text().includes('404')) {
        consoleErrors.push(msg.text());
      }
    });
    page.on('pageerror', (err) => consoleErrors.push(err.message));

    const email = `haven_demo_${Date.now()}@builddesk.accept`;
    const password = 'HavenDemo123!';

    // ?? Register workspace ??
    await page.goto('/register');
    await pause(page, 800);
    await page.getByTestId('register-workspace').fill('Virgin Surfaces ù Haven Demo');
    await pause(page);
    await page.getByTestId('register-email').fill(email);
    await pause(page);
    await page.getByTestId('register-password').fill(password);
    await pause(page);
    await page.getByTestId('register-submit').click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 30_000 });
    await pause(page, 2000);

    // ?? Create project from Excel metadata ??
    await page.getByRole('button', { name: /new project/i }).click();
    await expect(page.getByTestId('create-project-name')).toBeVisible();
    await pause(page);
    await page.getByTestId('create-project-name').fill(FIXTURE.projectName);
    await pause(page);
    await page.getByTestId('create-project-client').fill(FIXTURE.clientName);
    await pause(page);
    await page.getByTestId('create-project-material').fill(FIXTURE.material);
    await pause(page);
    await page.getByTestId('create-project-submit').click();
    await expect(page).toHaveURL(/\/projects\//, { timeout: 20_000 });
    await expect(page.getByRole('heading', { name: FIXTURE.projectName })).toBeVisible();
    await pause(page, 2000);

    // ?? Units: unit type + single unit from Excel ??
    await page.getByRole('button', { name: /^units$/i }).click();
    await pause(page);
    await page.getByPlaceholder('Type Code (e.g. A1)').fill(FIXTURE.unitTypeCode);
    await pause(page);
    await page.getByPlaceholder('Name (e.g. 1 Bed / 1 Bath)').fill(FIXTURE.unitTypeName);
    await pause(page);
    await page.getByRole('button', { name: 'Add Type' }).click();
    await expect(page.getByRole('cell', { name: FIXTURE.unitTypeCode, exact: true })).toBeVisible({ timeout: 10_000 });
    await pause(page, 1500);

    await page.getByPlaceholder('Single Unit Code (e.g. 101)').fill(`${FIXTURE.unitCode}-${FIXTURE.drawing}`);
    await pause(page);
    const unitsSection = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Units' }) });
    await page
      .getByPlaceholder('Single Unit Code (e.g. 101)')
      .locator('xpath=following-sibling::select[1]')
      .selectOption({ label: `${FIXTURE.unitTypeCode} - ${FIXTURE.unitTypeName}` });
    await pause(page);
    await page.getByRole('button', { name: 'Add Single Unit' }).click();
    await expect(
      unitsSection.locator('div.font-bold.text-gray-900').filter({ hasText: `${FIXTURE.unitCode}-${FIXTURE.drawing}` }).first()
    ).toBeVisible({ timeout: 10_000 });
    await pause(page, 2000);

    // ?? Fabrication: assembly shell ??
    await page.getByRole('button', { name: /^fabrication$/i }).click();
    await pause(page);
    await page.getByRole('button', { name: '+ New Assembly' }).click();
    await pause(page);
    await page.getByPlaceholder('Kitchen A').fill(FIXTURE.assemblyName);
    await pause(page);
    await page
      .locator('.bg-indigo-50')
      .locator('select')
      .first()
      .selectOption({ label: `${FIXTURE.unitTypeCode} - ${FIXTURE.unitTypeName}` });
    await pause(page);
    await page.getByRole('button', { name: 'Create' }).click();
    await expect(page.getByRole('button', { name: FIXTURE.assemblyName })).toBeVisible({ timeout: 10_000 });
    await pause(page, 1500);

    // ?? Enter parts from Excel (drawing 101-01) ??
    await page.getByRole('button', { name: FIXTURE.assemblyName }).click();
    await pause(page);
    await page.getByRole('button', { name: 'Edit' }).click();
    await expect(page.getByText('Parts Configuration')).toBeVisible();
    await pause(page, 1500);

    for (let i = 0; i < FIXTURE.parts.length; i++) {
      const part = FIXTURE.parts[i];
      await page.getByRole('button', { name: '+ Add Part' }).click();
      await pause(page, 1000);

      const card = page.locator('.bg-white.p-4.rounded.border.shadow-sm').last();
      await card.locator('input[type="text"]').first().fill(`${part.partNum} ù ${part.partType}`);
      await pause(page, 600);

      const isSplash = /splash/i.test(part.partType);
      if (isSplash) {
        await card.locator('select').first().selectOption('loose_piece');
      }
      await pause(page, 400);

      const numInputs = card.locator('input[type="number"]');
      await numInputs.nth(0).fill(String(part.length));
      await pause(page, 600);
      await numInputs.nth(1).fill(String(part.depth));
      await pause(page, 1000);
    }

    await page.getByRole('button', { name: 'Save Assembly' }).click();
    await pause(page, 2500);
    await expect(page.getByText('Fabrication Drawing Preview')).toBeVisible({ timeout: 20_000 });
    await pause(page, 3000);

    await page.getByRole('button', { name: '? Back' }).click();
    await pause(page, 1500);

    // ?? Generate fabrication package ??
    await page.getByRole('button', { name: /^package$/i }).click();
    await pause(page);
    await page.getByRole('button', { name: /generate package/i }).click();
    await pause(page);
    await page.locator('.fixed.inset-0 input[type="text"]').first().fill(`Job ${FIXTURE.jobNumber}`);
    await pause(page);
    await page.getByRole('button', { name: /^generate$/i }).click();
    await pause(page, 3000);

    await expect(page.getByText(/ready|generating/i)).toBeVisible({ timeout: 60_000 });
    await pause(page, 5000);

    expect(consoleErrors, `Unexpected browser errors:\n${consoleErrors.join('\n')}`).toEqual([]);
  });
});
