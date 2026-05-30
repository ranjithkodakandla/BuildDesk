/**
 * Populate fabrication parts for Haven ù 1A-ADA ù 101-01 from SourceData Excel.
 * Selectors derived from AssemblyEditor.tsx / AssembliesPanel.tsx (live DOM).
 *
 * Run:
 *   cd frontend && FRONTEND_URL=http://127.0.0.1:5174 npx playwright test e2e/haven-fabrication-populate.spec.ts --workers=1
 */
import { test, expect, type Page, type Locator } from '@playwright/test';
import { mkdirSync } from 'fs';
import { join } from 'path';

const BASE = process.env.FRONTEND_URL || 'http://127.0.0.1:5174';
const EMAIL = process.env.HAVEN_EMAIL || 'haven_demo_1780105167246@builddesk.accept';
const PASSWORD = process.env.HAVEN_PASSWORD || 'HavenDemo123!';
const PROJECT_NAME = 'Haven On Main New';
const PROJECT_ID = process.env.HAVEN_PROJECT_ID || '43f32a8e-acee-4479-95d2-e59a8da25161';
const ASSEMBLY_NAME = 'Haven ù 1A-ADA ù 101-01';

const SHOTS = join(process.cwd(), 'e2e-screenshots/haven-fabrication');

const PART_1 = {
  heading: 'Part A',
  name: 'Kitchen Island Top',
  type: 'island_top',
  length: '98.5',
  depth: '42',
  edges: [
    { position: 'FRONT', edge: 'EASED' },
    { position: 'BACK', edge: 'EASED' },
    { position: 'LEFT', edge: 'EASED' },
    { position: 'RIGHT', edge: 'EASED' },
  ],
};

const PART_2 = {
  heading: 'Part B',
  name: 'Kitchen Perimeter Top',
  type: 'main_top',
  length: '75',
  depth: '25.5',
  edges: [
    { position: 'FRONT', edge: 'EASED' },
    { position: 'BACK', edge: 'RAW' },
    { position: 'LEFT', edge: 'EASED' },
    { position: 'RIGHT', edge: 'EASED' },
  ],
};

function shot(page: Page, name: string) {
  mkdirSync(SHOTS, { recursive: true });
  return page.screenshot({ path: join(SHOTS, `${name}.png`), fullPage: true });
}

/** Part card: div.bg-white.p-4.rounded.border.shadow-sm containing h4 "Part X" */
function partCard(page: Page, heading: string): Locator {
  return page.locator('div.bg-white.p-4.rounded.border.shadow-sm').filter({
    has: page.getByRole('heading', { name: heading, exact: true }),
  });
}

async function fillPartBasics(card: Locator, spec: typeof PART_1) {
  const grid = card.locator('div.grid.grid-cols-2');
  await grid.locator('input[type="text"]').fill(spec.name);
  await grid.locator('select').selectOption(spec.type);
  const numbers = grid.locator('input[type="number"]');
  await numbers.nth(0).fill(spec.length);
  await numbers.nth(1).fill(spec.depth);
}

async function configureEdges(card: Locator, edges: typeof PART_1.edges) {
  const edgesBlock = card.locator('div.bg-gray-50.p-3.rounded.border').filter({
    has: card.getByText('Edges', { exact: true }),
  });
  const addBtn = edgesBlock.getByRole('button', { name: '+ Add Edge' });

  let rows = edgesBlock.locator('div.flex.space-x-2.mb-2');
  while ((await rows.count()) < edges.length) {
    await addBtn.click();
    rows = edgesBlock.locator('div.flex.space-x-2.mb-2');
  }
  while ((await rows.count()) > edges.length) {
    await rows.last().getByRole('button', { name: 'ù' }).click();
    rows = edgesBlock.locator('div.flex.space-x-2.mb-2');
  }

  for (let i = 0; i < edges.length; i++) {
    const row = rows.nth(i);
    const selects = row.locator('select');
    await selects.nth(0).selectOption(edges[i].position.toLowerCase());
    await selects.nth(1).selectOption(edges[i].edge.toLowerCase());
  }
}

async function login(page: Page) {
  await page.goto(`${BASE}/login`);
  await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible();
  await page.getByTestId('login-email').fill(EMAIL);
  await page.getByTestId('login-password').fill(PASSWORD);
  await page.getByTestId('login-submit').click();
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 30_000 });
}

async function openAssemblyEditor(page: Page) {
  await page.goto(`${BASE}/projects/${PROJECT_ID}`);
  await expect(page.getByRole('heading', { name: PROJECT_NAME })).toBeVisible({ timeout: 15_000 });

  await page.getByRole('button', { name: 'Fabrication', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Fabrication' })).toBeVisible();

  await page.getByRole('button', { name: ASSEMBLY_NAME, exact: true }).click();
  await page.getByRole('button', { name: 'Edit', exact: true }).click();

  await expect(page.getByRole('heading', { name: `Edit Assembly: ${ASSEMBLY_NAME}` })).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByRole('heading', { name: 'Parts Configuration' })).toBeVisible();
}

test.use({ baseURL: BASE, launchOptions: { slowMo: 400 } });

test.describe('Haven fabrication populate', () => {
  test('populate parts from Excel mapping and validate persistence', async ({ page }) => {
    test.setTimeout(300_000);

    await login(page);
    await openAssemblyEditor(page);
    await shot(page, '01-before-edit');

    // Part A ù update existing or ensure one part exists
    const partAExists = (await partCard(page, PART_1.heading).count()) > 0;
    if (!partAExists) {
      await page.getByRole('button', { name: '+ Add Part' }).click();
      await expect(partCard(page, PART_1.heading)).toBeVisible();
    }

    const cardA = partCard(page, PART_1.heading);
    await fillPartBasics(cardA, PART_1);
    await configureEdges(cardA, PART_1.edges);
    await shot(page, '02-after-part-1');

    // Part B ù add second part
    const partBExists = (await partCard(page, PART_2.heading).count()) > 0;
    if (!partBExists) {
      await page.getByRole('button', { name: '+ Add Part' }).click();
      await expect(partCard(page, PART_2.heading)).toBeVisible();
    }

    const cardB = partCard(page, PART_2.heading);
    await fillPartBasics(cardB, PART_2);
    await configureEdges(cardB, PART_2.edges);
    await shot(page, '03-after-part-2');

    // Save
    await page.getByRole('button', { name: 'Save Assembly' }).click();
    await expect(page.getByRole('button', { name: 'Save Assembly' })).toBeEnabled({ timeout: 30_000 });
    await expect(page.getByText('Fabrication Drawing Preview')).toBeVisible({ timeout: 30_000 });
    await expect(page.getByAltText('Assembly drawing preview')).toBeVisible({ timeout: 30_000 });
    await shot(page, '04-after-save');

    // Back to list ù verify parts count
    await page.getByRole('button', { name: '? Back' }).click();
    await expect(page.getByRole('heading', { name: 'Fabrication' })).toBeVisible();
    await expect(page.getByText('2 parts ù Open Edit for live SVG preview')).toBeVisible();

    // Reload persistence check
    await page.reload();
    await expect(page.getByRole('heading', { name: PROJECT_NAME })).toBeVisible();
    await page.getByRole('button', { name: 'Fabrication', exact: true }).click();
    await page.getByRole('button', { name: ASSEMBLY_NAME, exact: true }).click();
    await expect(page.getByText('2 parts ù Open Edit for live SVG preview')).toBeVisible();

    await page.getByRole('button', { name: 'Edit', exact: true }).click();
    await expect(partCard(page, PART_1.heading)).toBeVisible();
    await expect(partCard(page, PART_2.heading)).toBeVisible();
    await expect(partCard(page, PART_1.heading).locator('input[type="text"]')).toHaveValue(PART_1.name);
    await expect(partCard(page, PART_2.heading).locator('input[type="text"]')).toHaveValue(PART_2.name);
    await shot(page, '05-after-reload-validation');
  });
});
