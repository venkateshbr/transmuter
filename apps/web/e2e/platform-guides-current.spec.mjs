import { test, expect } from '@playwright/test';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const repo = resolve(import.meta.dirname, '../../..');
const platformCredentials = JSON.parse(
  readFileSync(resolve(repo, 'credentials.json'), 'utf8'),
).platform_admin;
const localCredentials = JSON.parse(readFileSync(resolve(repo, 'credentials.json'), 'utf8'));
const tenantCredentials = localCredentials.five_tenant_fixture;
const baseUrl = tenantCredentials.base_url;
const deployedCommit = process.env.TRANSMUTER_DEPLOYED_COMMIT;
if (
  tenantCredentials.environment !== 'dev'
  || new URL(baseUrl).hostname !== 'transmuter-dev.ishirock.tech'
) {
  throw new Error('Platform guide acceptance is restricted to the approved dev environment.');
}
if (!deployedCommit || !/^[0-9a-f]{7,40}$/i.test(deployedCommit)) {
  throw new Error('TRANSMUTER_DEPLOYED_COMMIT must identify the deployed dev commit.');
}
const evidenceDir = resolve(repo, 'scratch/issue-447');
const results = { commit: deployedCommit, environment: baseUrl, scenarios: [], pageErrors: [], serverErrors: [] };

function monitor(page) {
  page.on('pageerror', error => results.pageErrors.push(error.message));
  page.on('response', response => {
    if (response.status() >= 500) {
      results.serverErrors.push({ status: response.status(), path: new URL(response.url()).pathname });
    }
  });
}

async function login(page, email, password, expectedPath) {
  await page.goto(`${baseUrl}/auth/login`);
  await page.getByLabel('Email Address').fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Sign in to Transmuter' }).click();
  await page.waitForURL(url => url.pathname === expectedPath, { timeout: 30_000 });
}

async function scenario(name, work) {
  const startedAt = Date.now();
  try {
    await work();
    results.scenarios.push({ name, status: 'passed', durationMs: Date.now() - startedAt });
    console.log(`[guide-current] PASS ${name}`);
  } catch (error) {
    results.scenarios.push({ name, status: 'failed', durationMs: Date.now() - startedAt, error: error.message });
    throw error;
  }
}

test('published guides and current platform capabilities', async ({ browser }) => {
  test.setTimeout(600_000);
  mkdirSync(evidenceDir, { recursive: true });

  const platformContext = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const platformPage = await platformContext.newPage();
  monitor(platformPage);

  try {

  await scenario('Platform-admin guide library and all published sources', async () => {
    await login(platformPage, platformCredentials.email, platformCredentials.password, '/platform');
    await expect(platformPage.getByRole('link', { name: 'User Guides' })).toBeVisible();
    await platformPage.getByRole('link', { name: 'User Guides' }).click();
    await platformPage.waitForURL(/\/platform\/guides/);
    await expect(platformPage.getByTestId('platform-guide-library')).toBeVisible();
    await expect(platformPage.getByText('15', { exact: true }).first()).toBeVisible();
    await expect(platformPage.getByText('6', { exact: true }).first()).toBeVisible();
    const guideButtons = platformPage.locator('[data-testid^="guide-index-"]');
    await expect(guideButtons).toHaveCount(15);
    const slugs = await guideButtons.evaluateAll(nodes => nodes.map(node => node.dataset.testid.replace('guide-index-', '')));
    for (const slug of slugs) {
      const response = await platformPage.goto(`${baseUrl}/platform/guides/${slug}`);
      expect(response?.status()).toBe(200);
      await expect(platformPage.getByTestId('published-guide').locator('header h2')).toBeVisible();
      await expect(platformPage.locator('.guide-content')).not.toContainText(/^#\s/m);
      await expect(platformPage.locator('.guide-content')).not.toContainText('undefined');
    }
  });

  await scenario('Guide search, filters, deep links, dark theme, and mobile layout', async () => {
    await platformPage.goto(`${baseUrl}/platform/guides`);
    const search = platformPage.getByTestId('guide-search');
    await search.fill('financial');
    await expect(platformPage.locator('[data-testid^="guide-index-"]')).toHaveCount(5);
    await search.fill('no-guide-can-match-this');
    await expect(platformPage.getByText('No published guides match this search.')).toBeVisible();
    await platformPage.getByRole('button', { name: 'Clear filters' }).click();
    await platformPage.getByRole('button', { name: 'Demo guides', exact: true }).click();
    await expect(platformPage.locator('[data-testid^="guide-index-"]')).toHaveCount(4);
    await platformPage.getByLabel('Toggle theme').click();
    await expect(platformPage.locator('html')).toHaveClass(/dark/);
    await platformPage.setViewportSize({ width: 390, height: 844 });
    await expect(platformPage.getByTestId('platform-guide-library')).toBeVisible();
    expect(await platformPage.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
  });

  const anonymousContext = await browser.newContext();
  const anonymousPage = await anonymousContext.newPage();
  await scenario('Guide role enforcement', async () => {
    await anonymousPage.goto(`${baseUrl}/platform/guides`);
    await anonymousPage.waitForURL(/\/auth\/login/);
    const tenantContext = await browser.newContext();
    const tenantPage = await tenantContext.newPage();
    await login(
      tenantPage,
      tenantCredentials.tenant_admins.acme,
      tenantCredentials.shared_password,
      '/dashboard',
    );
    await expect(tenantPage.getByRole('link', { name: 'User Guides' })).toHaveCount(0);
    await tenantPage.goto(`${baseUrl}/platform/guides`);
    await tenantPage.waitForURL(url => url.pathname === '/dashboard');
    const apiStatus = await tenantPage.evaluate(async () => {
      const token = localStorage.getItem('access_token');
      return (await fetch('/api/platform/guides', { headers: { Authorization: `Bearer ${token}` } })).status;
    });
    expect(apiStatus).toBe(403);
    await tenantContext.close();
  });

  const tenantContext = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const tenantPage = await tenantContext.newPage();
  monitor(tenantPage);
  await login(
    tenantPage,
    tenantCredentials.tenant_admins.acme,
    tenantCredentials.shared_password,
    '/dashboard',
  );

  await scenario('Tenant dashboard configuration API', async () => {
    const status = await tenantPage.evaluate(async () => {
      const token = localStorage.getItem('access_token');
      return (await fetch('/api/dashboard/configuration', {
        headers: { Authorization: `Bearer ${token}` },
      })).status;
    });
    expect(status).toBe(200);
  });

  await scenario('Global portfolio search', async () => {
    await tenantPage.locator('div[role="status"].fixed.inset-0').waitFor({ state: 'hidden', timeout: 30_000 }).catch(() => undefined);
    const search = tenantPage.getByLabel('Global portfolio search');
    await search.fill('ENT-005');
    await expect(tenantPage.locator('button').filter({ hasText: /ENT-005/ }).first()).toBeVisible({ timeout: 20_000 });
    await tenantPage.locator('button').filter({ hasText: /ENT-005/ }).first().click();
    await tenantPage.waitForURL(/\/initiatives\/[0-9a-f-]+/i);
  });

  await scenario('Central Microsoft organizer status in Admin', async () => {
    await tenantPage.goto(`${baseUrl}/admin`);
    await tenantPage.getByRole('button', { name: 'Open Microsoft 365 admin tab' }).click();
    await expect(tenantPage.locator('body')).toContainText(/Microsoft 365/i);
    await expect(tenantPage.locator('body')).toContainText(/organizer|connect|connected|disconnected/i);
  });

  await scenario('Portfolio Assistant/Hermes read path and graceful response', async () => {
    await tenantPage.goto(`${baseUrl}/dashboard`);
    await tenantPage.getByLabel('Open Transmuter assistant').click();
    await expect(tenantPage.getByText('Ask Transmuter', { exact: true })).toBeVisible();
    await tenantPage.getByPlaceholder('Ask Transmuter...').fill('Summarize the portfolio without making changes.');
    const responsePromise = tenantPage.waitForResponse(response =>
      response.url().includes('/api/ai/chat') && response.request().method() === 'POST',
      { timeout: 90_000 },
    );
    await tenantPage.getByLabel('Send').click();
    const response = await responsePromise;
    expect(response.status()).toBeLessThan(500);
    await expect(tenantPage.locator('aside')).toContainText(/portfolio|initiative|unable|unavailable/i, { timeout: 90_000 });
  });

  await platformContext.close();
  await anonymousContext.close();
  await tenantContext.close();

  expect(results.pageErrors).toEqual([]);
  expect(results.serverErrors).toEqual([]);
  } finally {
    writeFileSync(resolve(evidenceDir, 'platform-guides-current.json'), `${JSON.stringify(results, null, 2)}\n`);
  }
});
