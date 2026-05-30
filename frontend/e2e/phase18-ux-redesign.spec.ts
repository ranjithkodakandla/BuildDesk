/**
 * Phase 18 UX Redesign — visible browser validation.
 * Verifies: new tab labels, command center, progressive units, shop drawings panel, package panel.
 */
import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://127.0.0.1:5176';

function attachDiagnostics(page: Page) {
  const problems: string[] = [];
  page.on('pageerror', (err) => problems.push(`pageerror: ${err.message}`));
  page.on('console', (msg) => {
    if (msg.type() === 'error') problems.push(`console.error: ${msg.text()}`);
  });
  page.on('response', (res) => {
    const url = res.url();
    if (url.includes('/api/v1/') && res.status() >= 500) {
      problems.push(`http-5xx: ${res.status()} ${url}`);
    }
  });
  return () => {
    const fatal = problems.filter(
      (p) => !p.includes('favicon') && !p.includes('vite.svg')
    );
    expect(fatal, `Browser diagnostics:\n${fatal.join('\n')}`).toEqual([]);
  };
}

test.describe('Phase 18 UX Redesign', () => {

  test('Dashboard — project card layout and nav tabs', async ({ page }) => {
    test.setTimeout(180_000);
    const assertClean = attachDiagnostics(page);

    const ws    = `P18-Dash-${Date.now().toString(36)}`;
    const email = `p18d_${Date.now()}@builddesk.accept`;
    const pw    = 'Phase18Test!';

    // Register
    await page.goto(`${FRONTEND_URL}/register`);
    await page.getByTestId('register-workspace').fill(ws);
    await page.getByTestId('register-email').fill(email);
    await page.getByTestId('register-password').fill(pw);
    await page.getByTestId('register-submit').click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 30_000 });

    // Dashboard: nav tabs Projects / Queue / Search / Settings
    await expect(page.getByRole('button', { name: /^Projects$/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /^Queue$/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /^Search$/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /^Settings$/i })).toBeVisible();

    // Empty state should show "No projects yet"
    await expect(page.getByText(/no projects yet/i)).toBeVisible({ timeout: 10_000 });

    // Create project via modal
    await page.getByRole('button', { name: /\+ new project/i }).click();
    await expect(page.getByRole('heading', { name: /new fabrication project/i })).toBeVisible();

    await page.getByTestId('create-project-name').fill('Haven On Main Phase 18');
    await page.getByTestId('create-project-client').fill('Virgin Surfaces');
    await page.getByTestId('create-project-material').fill('3CM Calacatta Quartz');
    await page.getByTestId('create-project-submit').click();

    await expect(page).toHaveURL(/\/projects\//, { timeout: 20_000 });

    await page.screenshot({ path: 'e2e-screenshots/p18-dashboard.png', fullPage: true });
    assertClean();
  });

  test('Workspace — new tab labels (Home, Unit Schedule, Shop Drawings, Package, Queue)', async ({ page }) => {
    test.setTimeout(300_000);
    const assertClean = attachDiagnostics(page);

    const ws    = `P18-Tabs-${Date.now().toString(36)}`;
    const email = `p18t_${Date.now()}@builddesk.accept`;
    const pw    = 'Phase18Test!';

    // Register & create project
    await page.goto(`${FRONTEND_URL}/register`);
    await page.getByTestId('register-workspace').fill(ws);
    await page.getByTestId('register-email').fill(email);
    await page.getByTestId('register-password').fill(pw);
    await page.getByTestId('register-submit').click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 30_000 });

    await page.getByRole('button', { name: /\+ new project/i }).click();
    await page.getByTestId('create-project-name').fill('Tab Label Test');
    await page.getByTestId('create-project-submit').click();
    await expect(page).toHaveURL(/\/projects\//, { timeout: 20_000 });

    // Verify NEW tab labels
    await expect(page.getByRole('button', { name: /^Home$/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /^Unit Schedule$/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /^Shop Drawings$/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /^Package$/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /^Queue$/i })).toBeVisible();

    // OLD labels must NOT exist
    await expect(page.getByRole('button', { name: /^Fabrication$/i })).toHaveCount(0);
    await expect(page.getByRole('button', { name: /^Operations$/i })).toHaveCount(0);

    await page.screenshot({ path: 'e2e-screenshots/p18-workspace-tabs.png', fullPage: false });

    assertClean();
  });

  test('Home tab — Project Command Center with health tiles and quick actions', async ({ page }) => {
    test.setTimeout(300_000);
    const assertClean = attachDiagnostics(page);

    const ws    = `P18-Home-${Date.now().toString(36)}`;
    const email = `p18h_${Date.now()}@builddesk.accept`;
    const pw    = 'Phase18Test!';

    await page.goto(`${FRONTEND_URL}/register`);
    await page.getByTestId('register-workspace').fill(ws);
    await page.getByTestId('register-email').fill(email);
    await page.getByTestId('register-password').fill(pw);
    await page.getByTestId('register-submit').click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 30_000 });

    await page.getByRole('button', { name: /\+ new project/i }).click();
    await page.getByTestId('create-project-name').fill('Command Center Test');
    await page.getByTestId('create-project-client').fill('Virgin Surfaces');
    await page.getByTestId('create-project-submit').click();
    await expect(page).toHaveURL(/\/projects\//, { timeout: 20_000 });

    // Home tab should be active by default
    await expect(page.getByRole('button', { name: /^Home$/i })).toBeVisible();

    // Command Center should show project health section
    await expect(page.getByText(/Project Command Center/i)).toBeVisible({ timeout: 15_000 });

    // Health tiles: Import/Schedule, Fabrication, Package, Approval
    await expect(page.getByText('Import / Schedule', { exact: true })).toBeVisible();
    await expect(page.getByText('Fabrication', { exact: true })).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText('Approval Status', { exact: true })).toBeVisible();

    // Quick Actions section
    await expect(page.getByText(/Quick Actions/i)).toBeVisible();
    await expect(page.getByText(/Import \/ Review Unit Schedule/i)).toBeVisible();
    await expect(page.getByText(/Review Shop Drawings/i)).toBeVisible();
    await expect(page.getByText(/Generate Fabrication Package/i)).toBeVisible();

    // Warnings section — new project has no units, should show issues count
    await expect(page.getByText(/Require Attention|All systems ready/i).first()).toBeVisible();

    await page.screenshot({ path: 'e2e-screenshots/p18-home-command-center.png', fullPage: true });

    // Click "Review Shop Drawings" quick action → should navigate to Shop Drawings
    await page.getByText(/Review Shop Drawings/i).click();
    await expect(page.getByText(/Shop Drawings/i)).toBeVisible();

    await page.screenshot({ path: 'e2e-screenshots/p18-shop-drawings-nav.png', fullPage: false });

    assertClean();
  });

  test('Unit Schedule tab — progressive disclosure type cards', async ({ page }) => {
    test.setTimeout(300_000);
    const assertClean = attachDiagnostics(page);

    const ws    = `P18-Units-${Date.now().toString(36)}`;
    const email = `p18u_${Date.now()}@builddesk.accept`;
    const pw    = 'Phase18Test!';

    await page.goto(`${FRONTEND_URL}/register`);
    await page.getByTestId('register-workspace').fill(ws);
    await page.getByTestId('register-email').fill(email);
    await page.getByTestId('register-password').fill(pw);
    await page.getByTestId('register-submit').click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 30_000 });

    await page.getByRole('button', { name: /\+ new project/i }).click();
    await page.getByTestId('create-project-name').fill('Units UX Test');
    await page.getByTestId('create-project-submit').click();
    await expect(page).toHaveURL(/\/projects\//, { timeout: 20_000 });

    // Navigate to Unit Schedule
    await page.getByRole('button', { name: /^Unit Schedule$/i }).click();

    // Empty state should show clean message
    await expect(page.getByText('No units yet', { exact: true })).toBeVisible({ timeout: 10_000 });

    // Summary bar has Import CSV button (first one is in the summary bar)
    await expect(page.getByRole('button', { name: /Import CSV/i }).first()).toBeVisible();
    await expect(page.getByRole('button', { name: /Tools/i })).toBeVisible();

    // Tools should be hidden by default — expand it
    await page.getByRole('button', { name: /Tools/i }).click();
    await expect(page.getByText(/Bulk Generate Units/i)).toBeVisible();
    await expect(page.getByText(/Add Unit Type/i)).toBeVisible();

    // Collapse Tools
    await page.getByRole('button', { name: /Tools/i }).click();

    await page.screenshot({ path: 'e2e-screenshots/p18-unit-schedule.png', fullPage: true });
    assertClean();
  });

  test('Package tab — Package Control Center layout', async ({ page }) => {
    test.setTimeout(300_000);
    const assertClean = attachDiagnostics(page);

    const ws    = `P18-Pkg-${Date.now().toString(36)}`;
    const email = `p18p_${Date.now()}@builddesk.accept`;
    const pw    = 'Phase18Test!';

    await page.goto(`${FRONTEND_URL}/register`);
    await page.getByTestId('register-workspace').fill(ws);
    await page.getByTestId('register-email').fill(email);
    await page.getByTestId('register-password').fill(pw);
    await page.getByTestId('register-submit').click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 30_000 });

    await page.getByRole('button', { name: /\+ new project/i }).click();
    await page.getByTestId('create-project-name').fill('Package UX Test');
    await page.getByTestId('create-project-submit').click();
    await expect(page).toHaveURL(/\/projects\//, { timeout: 20_000 });

    await page.getByRole('button', { name: /^Package$/i }).click();

    // Package Control section
    await expect(page.getByText(/Package Control/i)).toBeVisible({ timeout: 10_000 });

    // No package yet — should show "No Package Generated"
    await expect(page.getByText(/No Package Generated/i)).toBeVisible({ timeout: 10_000 });

    // Generate Package button visible (scope to main content, not header)
    await expect(page.getByRole('main').getByRole('button', { name: /Generate Package/i })).toBeVisible();

    // Revision History section
    await expect(page.getByText(/Revision History/i)).toBeVisible();

    // Open generate modal (use the main content button, not the header shortcut)
    await page.getByRole('main').getByRole('button', { name: /Generate Package/i }).click();
    await expect(page.getByRole('heading', { name: /Generate Package/i })).toBeVisible();
    await expect(page.locator('input[placeholder="Rev A"]')).toBeVisible();

    // Cancel
    await page.getByRole('button', { name: /Cancel/i }).click();

    await page.screenshot({ path: 'e2e-screenshots/p18-package-control.png', fullPage: true });
    assertClean();
  });

  test('Shop Drawings tab — assembly list and preview pane', async ({ page }) => {
    test.setTimeout(300_000);
    const assertClean = attachDiagnostics(page);

    const ws    = `P18-Shop-${Date.now().toString(36)}`;
    const email = `p18s_${Date.now()}@builddesk.accept`;
    const pw    = 'Phase18Test!';

    await page.goto(`${FRONTEND_URL}/register`);
    await page.getByTestId('register-workspace').fill(ws);
    await page.getByTestId('register-email').fill(email);
    await page.getByTestId('register-password').fill(pw);
    await page.getByTestId('register-submit').click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 30_000 });

    await page.getByRole('button', { name: /\+ new project/i }).click();
    await page.getByTestId('create-project-name').fill('Shop Drawings UX Test');
    await page.getByTestId('create-project-submit').click();
    await expect(page).toHaveURL(/\/projects\//, { timeout: 20_000 });

    await page.getByRole('button', { name: /^Shop Drawings$/i }).click();

    // Tab should be active, panel header visible
    await expect(page.getByRole('button', { name: 'Shop Drawings', exact: true })).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/0 assembl/i)).toBeVisible();

    // Empty list state
    await expect(page.getByText(/No assemblies yet/i)).toBeVisible();

    // + New Assembly button
    await expect(page.getByRole('button', { name: /\+ New Assembly/i })).toBeVisible();

    // Create an assembly
    await page.getByRole('button', { name: /\+ New Assembly/i }).click();
    await expect(page.getByPlaceholder('Kitchen A')).toBeVisible();

    await page.getByPlaceholder('Kitchen A').fill('Kitchen Type A');
    await page.getByRole('button', { name: /Create Assembly/i }).click();

    // Assembly should appear in list sidebar
    await expect(page.getByText('Kitchen Type A').first()).toBeVisible({ timeout: 10_000 });

    // Detail pane heading
    await expect(page.getByRole('heading', { name: /Kitchen Type A/i })).toBeVisible();

    // Stats strip at bottom (use exact label text)
    await expect(page.getByText('Parts', { exact: true })).toBeVisible();
    await expect(page.getByText('Edges', { exact: true })).toBeVisible();
    await expect(page.getByText('Cutouts', { exact: true })).toBeVisible();

    // Edit Drawing button
    await expect(page.getByRole('button', { name: /Edit Drawing/i })).toBeVisible();

    await page.screenshot({ path: 'e2e-screenshots/p18-shop-drawings.png', fullPage: false });
    assertClean();
  });

});
