import { test, expect } from '@playwright/test';
import { mkdirSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const repo = resolve(import.meta.dirname, '../../..');
const credentialManifest = JSON.parse(
  readFileSync(resolve(repo, 'scratch/test-credentials.json'), 'utf8'),
);
const runbookCredentials = JSON.parse(readFileSync(resolve(repo, 'credentials.json'), 'utf8'))
  .runbook_e2e.users.acme_transformation_office;
const deployedBaseUrl = credentialManifest.base_url;
const baseUrl = process.env.TRANSMUTER_LOCAL_UI || deployedBaseUrl;
const proxyApi = process.env.TRANSMUTER_LOCAL_UI ? `${deployedBaseUrl}/api` : null;
const tenant = process.env.TRANSMUTER_FINANCIAL_TENANT || 'acme';
const evidenceDir = resolve(repo, 'scratch/issue-452');

async function useRealDevApi(page) {
  if (!proxyApi) return;
  await page.route('http://localhost:8000/**', async (route) => {
    const requestUrl = new URL(route.request().url());
    const headers = { ...route.request().headers() };
    for (const name of ['host', 'origin', 'referer', 'content-length']) delete headers[name];
    const method = route.request().method();
    const response = await fetch(`${proxyApi}${requestUrl.pathname}${requestUrl.search}`, {
      method,
      headers,
      body: ['GET', 'HEAD'].includes(method) ? undefined : route.request().postDataBuffer(),
    });
    const responseHeaders = Object.fromEntries(response.headers.entries());
    for (const name of ['content-encoding', 'content-length', 'transfer-encoding'])
      delete responseHeaders[name];
    await route.fulfill({
      status: response.status,
      headers: responseHeaders,
      body: Buffer.from(await response.arrayBuffer()),
    });
  });
}

async function authenticateContext(context) {
  const response = await fetch(`${deployedBaseUrl}/api/auth/login`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      email: runbookCredentials.email,
      password: runbookCredentials.password,
    }),
  });
  expect(response.status).toBe(200);
  const session = await response.json();
  await context.addInitScript(
    ({ accessToken, refreshToken }) => {
      localStorage.setItem('access_token', accessToken);
      if (refreshToken) localStorage.setItem('refresh_token', refreshToken);
    },
    { accessToken: session.access_token, refreshToken: session.refresh_token },
  );
  return session;
}

test('tenant financial keys, formulas, subtabs, and value bridge editor', async ({ browser }) => {
  test.setTimeout(180_000);
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  await authenticateContext(context);
  const page = await context.newPage();
  const pageErrors = [];
  const serverErrors = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));
  page.on('response', (response) => {
    if (response.status() >= 500) serverErrors.push(`${response.status()} ${response.url()}`);
  });
  await useRealDevApi(page);

  await page.goto(`${baseUrl}/admin`);
  await page.getByRole('button', { name: 'Open Financial Configuration admin tab' }).click();
  const workbench = page.getByTestId('financial-configuration-workbench');
  await expect(workbench).toBeVisible();
  await expect(workbench).toContainText('same key may be used safely by another tenant');
  await expect(page.getByRole('tab')).toHaveCount(5);
  await page.getByRole('button', { name: 'Save reporting settings' }).click();
  await expect(workbench).toContainText('Financial settings saved.');

  await page.getByTestId('financial-subtab-metrics').click();
  await page.getByRole('button', { name: 'Add metric definition' }).click();
  await page.getByLabel('Metric definition label').fill('Revenue Uplift');
  await expect(page.getByLabel('Metric formula key')).toHaveValue('revenue_uplift');
  await page.getByRole('button', { name: 'Add metric definition' }).click();
  await expect(page.getByLabel('Metric definition label')).toHaveValue('Custom Metric 2');
  await page.getByLabel('Metric definition label').fill('Customer Retention Value');
  const newKey = page.getByLabel('Metric formula key');
  await expect(newKey).toBeEnabled();
  await expect(newKey).toHaveValue('customer_retention_value');
  await page.getByLabel('Metric aggregation').selectOption('formula');
  const formulaEditor = page.getByLabel('Metric formula', { exact: true });
  await expect(formulaEditor).toBeVisible();
  const variables = page.getByRole('button', { name: /Insert formula variable/ });
  await expect(variables.first()).toBeVisible();
  const selectedVariable = await variables.first().getAttribute('aria-label');
  const insertedKey = selectedVariable.replace('Insert formula variable ', '');
  await variables.first().click();
  await expect(formulaEditor).toHaveValue(insertedKey);

  await newKey.fill('Revenue Uplift');
  await expect(workbench).toContainText('Use lowercase letters, numbers, and underscores');

  await page.getByTestId('financial-subtab-bridge').click();
  await page.getByRole('button', { name: 'Add value bridge row' }).click();
  const bridgeLabel = page.getByLabel('Bridge row label');
  await expect(bridgeLabel).toBeVisible();
  expect((await bridgeLabel.boundingBox()).width).toBeGreaterThanOrEqual(320);
  await expect(page.getByLabel('Bridge row key')).toBeEnabled();
  await expect(page.getByText(/inputs · (active|hidden)/).first()).toBeVisible();

  mkdirSync(evidenceDir, { recursive: true });
  await page.screenshot({
    path: resolve(evidenceDir, 'financial-value-bridge-desktop.png'),
    fullPage: true,
  });

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(workbench).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1),
  ).toBe(true);
  await page.screenshot({
    path: resolve(evidenceDir, 'financial-value-bridge-mobile.png'),
    fullPage: true,
  });
  expect(pageErrors).toEqual([]);
  expect(serverErrors).toEqual([]);
  await context.close();
});

test('custom metric deletion discloses blockers and requires its immutable key', async ({
  browser,
}) => {
  test.setTimeout(180_000);
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const session = await authenticateContext(context);
  const suffix = Date.now().toString(36);
  const targetKey = `browser_delete_${suffix}`;
  const formulaKey = `${targetKey}_ratio`;
  const targetLabel = `Browser delete target ${suffix}`;
  const created = [];
  const headers = {
    authorization: `Bearer ${session.access_token}`,
    'content-type': 'application/json',
  };
  const api = `${deployedBaseUrl}/api`;
  const metricPayload = (key, label, formula = null) => ({
    key,
    label,
    value_type: formula ? 'percent' : 'currency',
    direction: 'increase_good',
    aggregation: formula ? 'formula' : 'sum',
    is_benefit: !formula,
    benefit_class: formula ? null : 'other',
    formula,
    formula_inputs: formula ? [targetKey] : [],
    precision: 4,
    display_order: 9999,
    applies_to: 'opt_in',
    validation: {},
    is_active: true,
  });

  try {
    const targetResponse = await fetch(`${api}/admin/financial-engine/metrics`, {
      method: 'POST',
      headers,
      body: JSON.stringify(metricPayload(targetKey, targetLabel)),
    });
    expect(targetResponse.status).toBe(201);
    const target = await targetResponse.json();
    created.push([target.id, targetKey]);

    const formulaResponse = await fetch(`${api}/admin/financial-engine/metrics`, {
      method: 'POST',
      headers,
      body: JSON.stringify(
        metricPayload(formulaKey, `Browser delete formula ${suffix}`, targetKey),
      ),
    });
    expect(formulaResponse.status).toBe(201);
    const formula = await formulaResponse.json();
    created.push([formula.id, formulaKey]);

    const page = await context.newPage();
    const pageErrors = [];
    const serverErrors = [];
    page.on('pageerror', (error) => pageErrors.push(error.message));
    page.on('response', (response) => {
      if (response.status() >= 500) serverErrors.push(`${response.status()} ${response.url()}`);
    });
    await useRealDevApi(page);
    await page.goto(`${baseUrl}/admin`);
    await page.getByRole('button', { name: 'Open Financial Configuration admin tab' }).click();
    await page.getByTestId('financial-subtab-metrics').click();
    await page.getByLabel('Search metric definitions').fill(targetKey);
    await page.getByRole('button', { name: `Edit metric ${targetLabel}` }).click();
    await page.getByRole('button', { name: `Delete metric ${targetLabel}` }).click();

    const dialog = page.getByTestId('metric-deletion-dialog');
    await expect(dialog).toBeVisible();
    await expect.poll(() => page.evaluate(() => document.body.style.overflow)).toBe('hidden');
    await expect(dialog).toContainText('Deletion blocked');
    await expect(dialog).toContainText('Formula dependencies');
    await expect(
      dialog.getByRole('button', { name: 'Hide metric instead of deleting' }),
    ).toBeVisible();
    mkdirSync(evidenceDir, { recursive: true });
    await page.screenshot({
      path: resolve(evidenceDir, 'financial-metric-deletion-blocked-desktop.png'),
      fullPage: true,
    });
    await dialog.getByRole('button', { name: 'Cancel metric deletion' }).click();
    await expect.poll(() => page.evaluate(() => document.body.style.overflow)).toBe('');

    const deleteFormula = await fetch(`${api}/admin/financial-engine/metrics/${formula.id}`, {
      method: 'DELETE',
      headers,
      body: JSON.stringify({ confirmation_key: formulaKey }),
    });
    expect(deleteFormula.status).toBe(204);
    created.splice(
      created.findIndex(([id]) => id === formula.id),
      1,
    );

    await page.getByRole('button', { name: `Delete metric ${targetLabel}` }).click();
    await expect(dialog).toContainText('No surviving dependencies');
    await page.setViewportSize({ width: 390, height: 844 });
    await expect(dialog).toBeVisible();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1),
    ).toBe(true);
    await page.screenshot({
      path: resolve(evidenceDir, 'financial-metric-deletion-confirm-mobile.png'),
      fullPage: true,
    });
    const confirmation = dialog.getByLabel(`Type ${targetKey} to confirm metric deletion`);
    await expect(
      dialog.getByRole('button', { name: `Permanently delete metric ${targetLabel}` }),
    ).toBeDisabled();
    await confirmation.fill(targetKey);
    await dialog.getByRole('button', { name: `Permanently delete metric ${targetLabel}` }).click();
    await expect(dialog).toBeHidden();
    await expect(page.getByTestId('financial-configuration-workbench')).toContainText(
      `Metric ${targetLabel} deleted.`,
    );
    created.splice(
      created.findIndex(([id]) => id === target.id),
      1,
    );

    await page.screenshot({
      path: resolve(evidenceDir, 'financial-metric-deletion.png'),
      fullPage: true,
    });
    expect(pageErrors).toEqual([]);
    expect(serverErrors).toEqual([]);
  } finally {
    for (const [id, key] of created.reverse()) {
      await fetch(`${api}/admin/financial-engine/metrics/${id}`, {
        method: 'DELETE',
        headers,
        body: JSON.stringify({ confirmation_key: key }),
      });
    }
    await context.close();
  }
});
