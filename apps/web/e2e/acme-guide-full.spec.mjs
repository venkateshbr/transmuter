import { test, expect } from '@playwright/test';
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const repo = resolve(import.meta.dirname, '../../..');
const credentials = JSON.parse(readFileSync(resolve(repo, 'credentials.json'), 'utf8'));
const fixture = credentials.five_tenant_fixture;
const baseUrl = fixture.base_url;
const password = fixture.shared_password;
const deployedCommit = process.env.TRANSMUTER_DEPLOYED_COMMIT;
if (
  fixture.environment !== 'dev'
  || new URL(baseUrl).hostname !== 'transmuter-dev.ishirock.tech'
) {
  throw new Error('ACME guide acceptance is restricted to the approved dev environment.');
}
if (!deployedCommit || !/^[0-9a-f]{7,40}$/i.test(deployedCommit)) {
  throw new Error('TRANSMUTER_DEPLOYED_COMMIT must identify the deployed dev commit.');
}
const results = {
  commit: deployedCommit,
  environment: baseUrl,
  execution: 'external Playwright Chromium; real Angular UI and API',
  scenarios: [],
  pageErrors: [],
  serverErrors: [],
  temporaryInitiative: null,
  temporaryMeeting: null,
};

async function settle(page) {
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle', { timeout: 8_000 }).catch(() => undefined);
  await page.locator('div[role="status"].fixed.inset-0').waitFor({ state: 'hidden', timeout: 30_000 }).catch(() => undefined);
  await page.waitForTimeout(400);
}

async function openRoute(page, route) {
  await page.goto(`${baseUrl}${route}`, { waitUntil: 'domcontentloaded' });
  await settle(page);
  expect(new URL(page.url()).pathname, `${route} redirected unexpectedly`).toBe(route);
  await expect(page.locator('body')).not.toContainText('Cannot GET');
}

async function login(page) {
  await page.goto(`${baseUrl}/auth/login`, { waitUntil: 'domcontentloaded' });
  await page.getByLabel('Email Address').fill(fixture.tenant_admins.acme);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Sign in to Transmuter' }).click();
  await page.waitForURL(url => url.pathname === '/dashboard', { timeout: 30_000 });
  await expect(page.getByRole('heading', { name: /Strategic Yield Dashboard/i })).toBeVisible();
}

async function selectFirstRealOption(select) {
  await expect.poll(async () => {
    const options = select.locator('option');
    const count = await options.count();
    for (let index = 0; index < count; index += 1) {
      if (await options.nth(index).getAttribute('value')) return true;
    }
    return false;
  }, { timeout: 20_000 }).toBe(true);
  const options = select.locator('option');
  for (let index = 0; index < await options.count(); index += 1) {
    const value = await options.nth(index).getAttribute('value');
    if (value) {
      await select.selectOption(value);
      return value;
    }
  }
  throw new Error('No selectable option was available after waiting');
}

async function selectOptionContaining(select, text) {
  const option = select.locator('option').filter({ hasText: text }).first();
  await expect(option).toHaveCount(1);
  const value = await option.getAttribute('value');
  expect(value).toBeTruthy();
  await select.selectOption(value);
  return value;
}

async function inputValues(locator) {
  const values = [];
  for (let index = 0; index < await locator.count(); index += 1) values.push(await locator.nth(index).inputValue());
  return values;
}

async function recoverAcmeRecords(browser, initiativeName, initiativeCode, meetingName) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const recoveryPage = await context.newPage();
  try {
    await login(recoveryPage);
    await openRoute(recoveryPage, '/admin');
    await recoveryPage.getByRole('button', { name: 'Open Data Cleanup admin tab' }).click();
    if (meetingName) {
      const meeting = recoveryPage.getByLabel(`Select meeting ${meetingName} for cleanup`);
      if (await meeting.count()) {
        await meeting.check();
        await recoveryPage.getByLabel('Meeting cleanup confirmation phrase').fill('DELETE MEETINGS');
        await recoveryPage.getByRole('button', { name: 'Delete selected meetings' }).click();
        await expect(recoveryPage.getByText('Deleted 1 meeting series.')).toBeVisible();
      }
    }
    if (initiativeName && initiativeCode) {
      await openRoute(recoveryPage, '/admin');
      await recoveryPage.getByRole('button', { name: 'Open Data Cleanup admin tab' }).click();
      const initiative = recoveryPage.getByRole('button', { name: `Select ${initiativeName} for deletion` });
      if (await initiative.count()) {
        await initiative.click();
        await recoveryPage.getByLabel('Initiative delete confirmation code').fill(initiativeCode);
        await recoveryPage.getByRole('button', { name: 'Delete selected initiative' }).click();
        await expect(recoveryPage.getByText(`Deleted ${initiativeCode}.`)).toBeVisible();
      }
    }
  } finally {
    await context.close();
  }
}

function waitForInitiativeFinancialGrid(page, initiativePath) {
  const expectedPath = `/api${initiativePath}/financials`;
  return page.waitForResponse(response =>
    new URL(response.url()).pathname === expectedPath
      && response.request().method() === 'GET'
      && response.status() === 200,
  );
}

test('ACME transformation-office client demo guide in one headed browser session', async ({ page, browser }) => {
  test.setTimeout(1_500_000);
  page.on('pageerror', error => results.pageErrors.push(error.message));
  page.on('response', response => {
    if (response.status() >= 500) results.serverErrors.push({ status: response.status(), path: new URL(response.url()).pathname });
  });

  const failures = [];
  let temporaryInitiativeName = '';
  let temporaryInitiativeCode = '';
  let temporaryInitiativePath = '';
  let temporaryMeetingName = '';

  async function scenario(name, objective, work) {
    const startedAt = Date.now();
    console.log(`[acme-guide] START ${name}`);
    try {
      await work();
      results.scenarios.push({ name, objective, status: 'passed', durationMs: Date.now() - startedAt });
      console.log(`[acme-guide] PASS  ${name}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      results.scenarios.push({ name, objective, status: 'failed', durationMs: Date.now() - startedAt, error: message });
      failures.push(`${name}: ${message}`);
      console.log(`[acme-guide] FAIL  ${name}: ${message.split('\n')[0]}`);
    }
  }

  try {

  await scenario('Public health and sign-in', 'Establish that the client demo uses the healthy public dev app and a real ACME transformation-office identity.', async () => {
    await page.goto(`${baseUrl}/health`);
    await expect(page.locator('body')).toContainText(/healthy|ok/i);
    await page.goto(`${baseUrl}/api/health`);
    await expect(page.locator('body')).toContainText(/healthy|ok/i);
    await login(page);
  });

  await scenario('Profile and tenant context', 'Confirm the presenter is operating inside ACME and has the transformation-office management role.', async () => {
    await openRoute(page, '/profile');
    await expect(page.locator('body')).toContainText('Acme Transformation Admin');
    await expect(page.locator('body')).toContainText('@acme-global-manufacturing.qa.transmuter-dev.ishirock.tech');
    await expect(page.locator('body')).toContainText(/Transformation Office/i);
  });

  await scenario('Tenant setup completeness', 'Show that all prerequisite structure is configured before initiatives are governed.', async () => {
    await openRoute(page, '/admin');
    await expect(page.getByText('7/7 complete', { exact: true })).toBeVisible();
    await expect(page.getByLabel('Legal entity name')).toHaveValue('Acme Global Manufacturing');
  });

  await scenario('Strategic dimensions', 'Explain the workstreams, business units, markets, theme, and tags used to slice the ACME portfolio.', async () => {
    await page.getByRole('button', { name: 'Open Strategic Parameters admin tab' }).click();
    await expect(page.getByLabel('Workstream name', { exact: true })).toHaveCount(5);
    await expect(page.getByLabel('Business unit name', { exact: true })).toHaveCount(5);
    await expect(page.getByLabel('Market name', { exact: true })).toHaveCount(2);
    expect(await inputValues(page.getByLabel('Workstream name', { exact: true }))).toEqual(['Automation', 'Commercial Growth', 'ERP & Data Platform', 'Offshoring & Operating Model', 'Procurement & Supply Chain']);
    expect(await inputValues(page.getByLabel('Business unit name', { exact: true }))).toEqual(['Commercial', 'Corporate', 'Operations', 'Shared Services', 'Technology']);
    expect(await inputValues(page.getByLabel('Market name', { exact: true }))).toEqual(['Group', 'Regional']);
    expect(await inputValues(page.getByLabel('Theme name', { exact: true }))).toEqual(['Manufacturing productivity and profitable growth']);
    expect(await inputValues(page.getByLabel('Tag name', { exact: true }))).toEqual(['automation', 'offshoring', 'commercial', 'other']);
  });

  await scenario('Financial configuration', 'Show the common currency, fiscal calendar, original baseline, scenarios, value bridge, and cost taxonomy behind comparable business cases.', async () => {
    await page.getByRole('button', { name: 'Open Financial Configuration admin tab' }).click();
    await expect(page.getByLabel('Reporting currency')).toHaveValue('USD');
    await expect(page.getByLabel('Fiscal year start month').locator('option:checked')).toHaveText('January');
    await expect(page.getByLabel('Tenant baseline fiscal year')).toHaveValue('2026');
    await expect(page.getByLabel('Tenant annual baseline for Annual Revenue Baseline')).toHaveValue('20000000.0000');
    await expect(page.getByLabel('Tenant annual baseline for Annual Gross Margin Baseline')).toHaveValue('9000000.0000');
    expect(await inputValues(page.getByLabel('Scenario label'))).toEqual(['Baseline', 'Plan Base', 'Plan High', 'Actual']);
    await expect(page.locator('input[aria-label="Metric definition label"]')).toHaveCount(10);
    await expect(page.locator('input[aria-label="Cost category label"]')).toHaveCount(8);
    expect(await inputValues(page.getByLabel('Cost category label'))).toEqual(expect.arrayContaining(['Software / Licenses', 'People Support']));
  });

  await scenario('Governance and access model', 'Explain stage-gate control and role separation before demonstrating delivery workflows.', async () => {
    await page.getByRole('button', { name: 'Open Governance Engine admin tab' }).click();
    await expect(page.getByLabel('Gate number', { exact: true })).toHaveCount(5);
    expect(await inputValues(page.getByLabel('Gate number', { exact: true }))).toEqual(['1', '2', '3', '4', '5']);
    expect(await inputValues(page.getByLabel('Approver roles'))).toEqual(['transformation_office', 'transformation_office', 'transformation_office', 'transformation_office', 'transformation_office']);
    const requireAllCriteria = page.getByLabel('Require all criteria');
    await expect(requireAllCriteria).toHaveCount(5);
    for (let index = 0; index < 5; index += 1) await expect(requireAllCriteria.nth(index)).toBeChecked();
    await page.getByRole('button', { name: 'Open Access Control admin tab' }).click();
    await expect(page.locator('body')).toContainText(/Transformation Office/i);
    await expect(page.locator('body')).toContainText(/Finance Lead/i);
    await expect(page.locator('body')).toContainText(/Initiative Owner/i);
  });

  await scenario('People roster', 'Demonstrate the seeded operating team and the browser-visible invite/access controls.', async () => {
    await openRoute(page, '/people');
    await expect(page.getByRole('button', { name: 'Add User' })).toBeVisible();
    await expect(page.locator('.card').filter({ has: page.getByRole('button', { name: 'Profile' }) })).toHaveCount(10);
    await expect(page.getByRole('button', { name: 'Pending Access' })).toBeVisible();
  });

  await scenario('Executive dashboard', 'Open with the portfolio story: ten initiatives, value matrix, stage waterline, actions, KPI pulse, and recent activity.', async () => {
    await openRoute(page, '/dashboard');
    await expect(page.getByTestId('dashboard-total-initiatives')).toContainText('10');
    for (const id of ['dashboard-workstream-targets', 'dashboard-stage-gate-waterline', 'dashboard-value-matrix', 'dashboard-my-actions', 'dashboard-kpi-pulse', 'dashboard-recent-activity']) {
      await expect(page.getByTestId(id)).toBeVisible();
    }
  });

  await scenario('Initiative pipeline and filters', 'Show how a transformation manager narrows the portfolio by strategic tag and workstream without losing the ten-initiative master view.', async () => {
    await openRoute(page, '/initiatives/pipeline');
    await expect(page.getByText(/10 initiatives/).first()).toBeVisible();
    await page.getByRole('button', { name: 'Open Tag filter' }).click();
    await page.getByLabel('Tag: Automation').check();
    await expect(page.locator('[data-testid="initiatives-filter-tag"]')).toContainText('1');
    await page.getByTestId('initiatives-clear-filters').click();
    await expect(page.getByText(/10 initiatives/).first()).toBeVisible();
    await page.getByRole('button', { name: 'Open Workstream filter' }).click();
    await page.getByLabel('Workstream: Commercial Growth').check();
    await expect(page.locator('[data-testid="initiatives-filter-workstream"]')).toContainText('1');
    await page.getByTestId('initiatives-clear-filters').click();
  });

  await scenario('Portfolio financial overview', 'Explain FY28 run-rate benefits, recurring cost, net value, actuals, category drilldown, and contributor traceability.', async () => {
    await openRoute(page, '/financials');
    await page.getByLabel('Filter financial year').fill('2028');
    const benefits = page.getByRole('button', { name: /Benefits (On|Off)/ });
    if ((await benefits.getAttribute('aria-pressed')) === 'false') await benefits.click();
    const actuals = page.getByRole('button', { name: /Actuals (On|Off)/ });
    if (await actuals.isEnabled() && (await actuals.getAttribute('aria-pressed')) === 'false') await actuals.click();
    const body = page.locator('body');
    await expect(body).toContainText('$9,182,000');
    await expect(body).toContainText('$800,000');
    await expect(body).toContainText('$8,382,000');
    await page.getByLabel('Filter cost category').selectOption({ label: 'Software / Licenses' });
    await expect(body).toContainText('Software / Licenses');
    await page.getByLabel('Filter cost category').selectOption('');
    await page.getByLabel('Select value bridge basis').selectOption({ index: 1 });
    const contributorButton = page.getByRole('button', { name: /Show initiatives for 2028-M01/i }).first();
    await contributorButton.click();
    await expect(page.getByRole('button', { name: 'Close contributor drawer' })).toBeVisible();
    await expect(page.locator('body')).toContainText('ENT-006');
    await page.getByRole('button', { name: 'Close contributor drawer' }).click();
  });

  await scenario('Initiative value case and locked baseline', 'Trace portfolio value into the ACME aftermarket-growth initiative and explain why its approved original baseline is immutable.', async () => {
    await openRoute(page, '/initiatives/pipeline');
    await page.getByRole('link', { name: 'Aftermarket Revenue Growth', exact: true }).click();
    await page.waitForURL(/\/initiatives\/[0-9a-f-]+$/i);
    await page.getByRole('button', { name: 'Financials', exact: true }).click();
    await expect(page.getByTestId('initiative-annual-baseline-panel')).toBeVisible();
    await expect(page.getByLabel('Initiative baseline fiscal year')).toBeDisabled();
    await expect(page.getByLabel('Initiative baseline Annual Revenue Baseline')).toBeDisabled();
    await expect(page.getByLabel('Initiative baseline Annual Gross Margin Baseline')).toBeDisabled();
    await expect(page.getByRole('button', { name: 'Save initiative annual baseline' })).toBeDisabled();
    await expect(page.getByText(/locked by governance/i)).toBeVisible();
    await expect(page.getByRole('link', { name: /Configure initiative financial metrics/i })).toBeVisible();
    await expect(page.getByLabel('Export initiative workbook')).toBeVisible();
  });

  await scenario('Bankable plan and benefits governance', 'Connect the approved value case to rebaseline history, finance validation, and realized benefit tracking.', async () => {
    await openRoute(page, '/financials/bankable-plan');
    await selectOptionContaining(page.getByLabel('Select initiative for bankable plan review'), 'ENT-005');
    await expect(page.locator('body')).toContainText(/Version 2|v2/i);
    await expect(page.getByLabel('Plan state badge')).toContainText(/locked/i);
    await openRoute(page, '/financials/benefits-register');
    await page.getByLabel('Filter benefits register year').fill('2028');
    await expect(page.locator('body')).toContainText(/Finance Validation/i);
    await expect(page.locator('body')).toContainText(/ENT-00/i);
    await openRoute(page, '/financials/benefit-tracking');
    await expect(page.getByRole('heading', { name: /Locked Baseline Realization/i })).toBeVisible();
    await page.getByRole('button', { name: 'Yearly' }).click();
    await expect(page.locator('body')).toContainText('$13,802,000');
    await expect(page.locator('body')).toContainText('$7,973,200');
    await page.getByRole('button', { name: 'Weekly' }).click();
    await page.getByRole('button', { name: 'Monthly' }).click();
  });

  await scenario('Waterline and initiative portfolio', 'Show selection discipline and reconcile original baselines to target-year value without locking a new snapshot during the demo.', async () => {
    await openRoute(page, '/financials/waterline');
    await selectFirstRealOption(page.getByLabel('Select workstream for target lock'));
    await page.getByLabel('Workstream target lock date').fill('2026-07-18');
    await page.getByLabel('Preview workstream target lock').click();
    await expect(page.locator('body')).toContainText(/Preview|Included/i);
    await openRoute(page, '/financials/initiative-portfolio');
    await expect(page.getByTestId('initiative-portfolio-page')).toBeVisible();
    await selectOptionContaining(page.getByLabel('Select baseline year'), '2026');
    await selectOptionContaining(page.getByLabel('Select value year'), '2028');
    await expect(page.getByTestId('initiative-portfolio-table')).toContainText('ENT-001');
    await expect(page.locator('body')).toContainText(/Annual revenue|Gross margin/i);
  });

  await scenario('Shared cost allocation', 'Explain how enterprise platform, PMO, change, and advisory costs are allocated separately from direct initiative economics.', async () => {
    await openRoute(page, '/shared-costs');
    for (const pool of [
      'Group technology and data platform', 'Transformation PMO and benefits office',
      'Shared change and training support', 'Central advisory and vendor support',
    ]) {
      await page.getByRole('button', { name: `Select ${pool}` }).click();
      await expect(page.locator('body')).toContainText(pool);
      await expect(page.locator('body')).toContainText(/Rules, Targets, and Weights/i);
    }
  });

  await scenario('Progress, PMO, and control tower', 'Demonstrate delivery oversight across milestones, status, actions, governance, risks, KPIs, allocated cost, and net value.', async () => {
    const routes = [
      ['/progress', /Progress|Delivery/i], ['/progress/roadmap', /Roadmap/i], ['/progress/status-updates', /Status Updates/i],
      ['/progress/action-items', /Action Items/i], ['/pmo/governance', /Governance/i], ['/pmo/risks', /Risks/i], ['/pmo/kpis', /KPIs/i],
    ];
    for (const [route, text] of routes) {
      await openRoute(page, route);
      await expect(page.locator('body')).toContainText(text);
    }
    await openRoute(page, '/reports/control-tower');
    await page.getByLabel('Target year').fill('2028');
    await expect(page.locator('body')).toContainText(/Allocated Costs/i);
    await expect(page.locator('body')).toContainText(/Net After Allocation/i);
  });

  await scenario('Guided initiative authoring and HITL', 'Create a temporary client example, review AI suggestions before write, and prove the result appears in the real portfolio.', async () => {
    temporaryInitiativeName = `Client Demo Margin Recovery ${Date.now()}`;
    await openRoute(page, '/initiatives/new');
    await page.getByRole('button', { name: 'Create initiative with Transmuter' }).click();
    await page.locator('#init-name').fill(temporaryInitiativeName);
    await selectOptionContaining(page.locator('#init-workstream'), 'Commercial Growth');
    await page.getByLabel('Toggle business unit Commercial').check();
    await page.locator('#init-country').selectOption({ label: 'Regional' });
    await selectFirstRealOption(page.locator('#init-theme'));
    await page.locator('#init-type').selectOption('revenue_growth');
    await page.locator('#init-impact').selectOption('recurring');
    await page.locator('#init-priority').selectOption('high');
    await page.locator('#init-tag').selectOption('commercial');
    await page.getByRole('button', { name: 'Go to next step' }).click();
    await page.locator('#init-summary').fill('Recover aftermarket margin by standardizing price corridors and managing exceptions through a weekly commercial cadence.');
    await page.locator('#init-context-problem').fill('Regional discount leakage obscures profitable growth and weakens accountability for realized margin.');
    await page.locator('#init-value-logic').fill('A governed one-point margin recovery creates recurring gross-margin uplift after adoption and data-quality controls are in place.');
    await page.locator('#init-deps').fill('Requires reliable price waterfall data and regional sales-owner adoption.');
    await page.getByRole('button', { name: 'Go to next step' }).click();
    await selectFirstRealOption(page.locator('#init-owner'));
    await selectFirstRealOption(page.locator('#init-group-owner'));
    await page.locator('#init-start').fill('2026-08-01');
    await page.locator('#init-end').fill('2028-06-30');
    await page.getByRole('button', { name: 'Generate initiative suggestions' }).click();
    await expect(page.getByText('HITL Review', { exact: true })).toBeVisible({ timeout: 90_000 });
    await expect(page.getByLabel('Suggested KPI name').first()).toBeVisible();
    await page.getByLabel('Suggested KPI name').first().fill('Regional price realization');
    const riskSuggestion = page.getByLabel('Accept risk suggestion').first();
    if (!(await riskSuggestion.isChecked())) await riskSuggestion.check();
    await page.getByRole('button', { name: 'Create initiative', exact: true }).click();
    await page.waitForURL(/\/initiatives\/[0-9a-f-]+$/i, { timeout: 45_000 });
    temporaryInitiativePath = new URL(page.url()).pathname;
    await expect(page.getByRole('heading', { name: temporaryInitiativeName }).first()).toBeVisible();
    temporaryInitiativeCode = (await page.locator('app-overview-tab span.font-mono').first().innerText()).trim();
    expect(temporaryInitiativeCode).toBeTruthy();
    results.temporaryInitiative = { name: temporaryInitiativeName, code: temporaryInitiativeCode, created: true };
    for (const tab of ['Milestones', 'KPIs', 'Risks']) {
      await page.getByRole('button', { name: tab, exact: true }).click();
      await expect(page.locator('body')).not.toContainText(/No .* configured/i);
    }
  });

  await scenario('Temporary initiative financial scope and baseline', 'Configure the new initiative, save its original operating baseline, and prove persistence after a browser reload.', async () => {
    expect(temporaryInitiativePath).toBeTruthy();
    await openRoute(page, `${temporaryInitiativePath}/financial-scope`);
    const metricLabels = ['Annual Revenue Baseline', 'Annual Gross Margin Baseline', 'Gross Margin Uplift'];
    for (const label of metricLabels) {
      const toggle = page.locator('label').filter({ hasText: label }).getByLabel('Toggle financial metric').first();
      await expect(toggle).toBeVisible();
      if (!(await toggle.isChecked())) await toggle.check();
    }
    const costToggle = page.locator('label').filter({ hasText: 'Software / Licenses' }).getByLabel('Toggle cost category').first();
    await expect(costToggle).toBeVisible();
    if (!(await costToggle.isChecked())) await costToggle.check();
    await page.getByLabel('Save financial scope').click();
    await page.waitForURL(new RegExp(`${temporaryInitiativePath}$`));
    await openRoute(page, `${temporaryInitiativePath}/financial-scope`);
    for (const label of metricLabels) await expect(page.locator('label').filter({ hasText: label }).getByLabel('Toggle financial metric').first()).toBeChecked();
    await expect(page.locator('label').filter({ hasText: 'Software / Licenses' }).getByLabel('Toggle cost category').first()).toBeChecked();
    await openRoute(page, temporaryInitiativePath);
    const initialGrid = waitForInitiativeFinancialGrid(page, temporaryInitiativePath);
    await page.getByRole('button', { name: 'Financials', exact: true }).click();
    await initialGrid;
    await page.waitForTimeout(500);
    await expect(page.getByLabel('Initiative baseline fiscal year')).toBeEnabled();
    await page.getByLabel('Initiative baseline fiscal year').fill('2026');
    await page.getByLabel('Initiative baseline Annual Revenue Baseline').fill('3000000.0000');
    await page.getByLabel('Initiative baseline Annual Gross Margin Baseline').fill('1350000.0000');
    const baselineSave = page.getByRole('button', { name: 'Save initiative annual baseline' });
    console.log('[acme-guide] baseline control state', {
      year: await page.getByLabel('Initiative baseline fiscal year').inputValue(),
      revenue: await page.getByLabel('Initiative baseline Annual Revenue Baseline').inputValue(),
      grossMargin: await page.getByLabel('Initiative baseline Annual Gross Margin Baseline').inputValue(),
      saveDisabled: await baselineSave.isDisabled(),
    });
    await expect(baselineSave).toBeEnabled();
    await baselineSave.click();
    await expect(page.getByText('Initiative annual baseline saved.')).toBeVisible();
    await page.reload();
    const persistedGrid = waitForInitiativeFinancialGrid(page, temporaryInitiativePath);
    await page.getByRole('button', { name: 'Financials', exact: true }).click();
    await persistedGrid;
    await page.waitForTimeout(500);
    await expect(page.getByLabel('Initiative baseline fiscal year')).toHaveValue('2026');
    await expect(page.getByLabel('Initiative baseline Annual Revenue Baseline')).toHaveValue('3000000.0000');
    await expect(page.getByLabel('Initiative baseline Annual Gross Margin Baseline')).toHaveValue('1350000.0000');
  });

  await scenario('Temporary initiative benefit and cost lines', 'Build an auditable example value case with a named benefit and a separately phased recurring implementation cost.', async () => {
    expect(temporaryInitiativePath).toBeTruthy();
    await openRoute(page, temporaryInitiativePath);
    const initialGrid = waitForInitiativeFinancialGrid(page, temporaryInitiativePath);
    await page.getByRole('button', { name: 'Financials', exact: true }).click();
    await initialGrid;
    await page.waitForTimeout(500);
    await selectFirstRealOption(page.getByLabel('Benefit line metric'));
    await page.getByLabel('Benefit line name').fill('Regional price realization uplift');
    await page.getByLabel('Benefit line confidence').fill('80');
    await page.getByLabel('Benefit line phasing mode').selectOption('spread');
    await page.getByLabel('Benefit line base amount').fill('120000');
    await page.getByLabel('Benefit line high amount').fill('150000');
    await page.getByLabel('Benefit line actual amount').fill('0');
    await page.getByLabel('Benefit line start month').fill('2027-01');
    await page.getByLabel('Benefit line end month').fill('2027-12');
    const benefitGridReload = waitForInitiativeFinancialGrid(page, temporaryInitiativePath);
    await page.getByRole('button', { name: 'Add benefit line' }).click();
    await expect(page.getByText(/Benefit line added/)).toBeVisible({ timeout: 30_000 });
    await benefitGridReload;
    await page.reload();
    const persistedBenefitGrid = waitForInitiativeFinancialGrid(page, temporaryInitiativePath);
    await page.getByRole('button', { name: 'Financials', exact: true }).click();
    await persistedBenefitGrid;
    await expect(page.getByText('Regional price realization uplift').first()).toBeVisible();
    await selectFirstRealOption(page.getByLabel('Cost line category'));
    await page.getByLabel('Cost line name').fill('Pricing analytics subscription');
    await page.getByLabel('Cost line lane').selectOption('plan');
    await page.getByLabel('Cost line phasing mode').selectOption('spread');
    await page.getByLabel('Cost line amount').fill('12000');
    await page.getByLabel('Cost line start month').fill('2027-01');
    await page.getByLabel('Cost line end month').fill('2027-12');
    const costGridReload = waitForInitiativeFinancialGrid(page, temporaryInitiativePath);
    await page.getByRole('button', { name: 'Generate cost line' }).click();
    await expect(page.getByText(/12 cost lines added/)).toBeVisible({ timeout: 30_000 });
    await costGridReload;
    await page.waitForTimeout(500);
    await expect(page.getByText('Pricing analytics subscription').first()).toBeVisible();
    await page.reload();
    const persistedValueCaseGrid = waitForInitiativeFinancialGrid(page, temporaryInitiativePath);
    await page.getByRole('button', { name: 'Financials', exact: true }).click();
    await persistedValueCaseGrid;
    await expect(page.getByText('Regional price realization uplift').first()).toBeVisible();
    await expect(page.getByText('Pricing analytics subscription').first()).toBeVisible();
    await page.getByRole('button', { name: /Edit Details/i }).click();
    await expect(page.locator('.handsontable').first()).toBeVisible();
    await expect(page.getByRole('button', { name: /Save Changes/i })).toBeVisible();
  });

  await scenario('Saturday meeting command center', 'Create a Saturday steering series, build an initiative-backed agenda, capture notes, attach a decision and risk to that agenda, generate/review AI minutes, complete the session, and remove the temporary series.', async () => {
    const name = `ACME Client Demo Saturday ${Date.now()}`;
    temporaryMeetingName = name;
    const today = new Date();
    const daysUntilSaturday = (6 - today.getDay() + 7) % 7 || 7;
    const seriesStart = new Date(today);
    seriesStart.setDate(today.getDate() + daysUntilSaturday);
    const seriesEnd = new Date(seriesStart);
    seriesEnd.setDate(seriesStart.getDate() + 35);
    const isoDate = value => value.toISOString().slice(0, 10);
    await openRoute(page, '/meetings');
    await page.getByRole('button', { name: 'Create meeting series' }).click();
    await page.getByLabel('Meeting name').fill(name);
    await page.getByLabel('Meeting scope').selectOption('all');
    await page.getByLabel('Meeting recurrence').selectOption('weekly');
    await page.getByLabel('Meeting day of week').selectOption({ label: 'Saturday' });
    await page.getByLabel('Meeting series start date').fill(isoDate(seriesStart));
    await page.getByLabel('Meeting series end date').fill(isoDate(seriesEnd));
    await page.getByLabel('Meeting start time').fill('09:00');
    await page.getByLabel('Meeting duration minutes').fill('60');
    await page.getByLabel('Meeting description').fill('Weekly ACME steering review of value, milestones, decisions, and risks.');
    await page.locator('fieldset').filter({ hasText: 'Participants' }).locator('input[type=checkbox]').first().check();
    await page.getByRole('button', { name: 'Create series' }).click();
    await page.waitForURL(/\/meetings\/[0-9a-f-]+$/i);
    const meetingPath = new URL(page.url()).pathname;
    await page.getByRole('button', { name: 'Link initiative' }).click();
    await selectOptionContaining(page.getByLabel('Select initiative'), 'ENT-005');
    await page.getByRole('button', { name: 'Link', exact: true }).click();
    await page.getByRole('button', { name: 'Add agenda item' }).click();
    const topic = 'ENT-005 data platform value and migration risk';
    await page.getByLabel('Agenda topic').fill(topic);
    await selectOptionContaining(page.getByLabel('Agenda initiative'), 'ENT-005');
    await page.getByRole('button', { name: 'Add', exact: true }).first().click();
    await page.getByRole('button', { name: 'Start next scheduled session' }).click();
    await page.getByRole('button', { name: 'Start', exact: true }).click();
    await page.waitForURL(/\/meetings\/sessions\/[0-9a-f-]+$/i);
    await expect(page.getByText(topic).first()).toBeVisible();
    await page.getByText(topic).first().click();
    await expect(page.getByText(/Brief Financials/i)).toBeVisible();
    const notes = 'ENT-005 remains on the FY28 value path. Finance will confirm the benefit owner. Architecture will name a rollback owner before migration. The committee will retain the Saturday checkpoint until migration risk is green.';
    await page.getByPlaceholder('Capture meeting minutes, decisions, and key discussion points...').fill(notes);
    await expect(page.getByText(/All changes saved/i)).toBeVisible({ timeout: 30_000 });
    await page.getByLabel('Artifact type').selectOption('decision');
    await page.getByLabel('Artifact priority').selectOption('high');
    await page.getByPlaceholder('Capture a new action item...').fill('Retain Saturday checkpoint until migration risk is green');
    await page.getByRole('button', { name: 'Add decision' }).click();
    await page.locator('div[role="status"].fixed.inset-0').waitFor({ state: 'hidden', timeout: 30_000 });
    await page.getByLabel('Artifact type').selectOption('risk');
    await page.getByPlaceholder('Capture a new action item...').fill('Migration rollback ownership is not yet confirmed');
    await page.getByRole('button', { name: 'Add risk' }).click();
    await expect(page.getByText('Retain Saturday checkpoint until migration risk is green').first()).toBeVisible();
    await expect(page.getByText('Migration rollback ownership is not yet confirmed').first()).toBeVisible();
    await page.getByRole('button', { name: 'Generate Minutes' }).click();
    const minutes = page.getByLabel('Draft meeting minutes');
    await expect(minutes).toBeVisible({ timeout: 90_000 });
    await expect(minutes).toHaveValue(/Executive Summary|AI Summary/);
    await expect(minutes).toHaveValue(/Migration rollback ownership/);
    await minutes.fill(`${await minutes.inputValue()}\n\nPresenter review: minutes checked and accepted in the browser.`);
    const minutesSave = page.waitForResponse(response =>
      response.url().includes('/api/meetings/sessions/')
        && response.request().method() === 'PATCH'
        && response.status() === 200,
    );
    await page.getByRole('button', { name: 'Save Draft' }).click();
    await minutesSave;
    await expect(page.getByText('Draft minutes saved.')).toBeVisible();
    await page.reload();
    await expect(page.getByLabel('Draft meeting minutes')).toHaveValue(/Presenter review/);
    for (const artifactTitle of [
      'Migration rollback ownership is not yet confirmed',
      'Retain Saturday checkpoint until migration risk is green',
    ]) {
      const artifactCard = page.getByText(artifactTitle, { exact: true }).locator('..');
      await artifactCard.getByLabel('Delete action item').click();
      await expect(page.getByText(artifactTitle, { exact: true })).toHaveCount(0);
    }
    await page.getByRole('button', { name: 'Complete Session' }).click();
    await page.waitForURL(new RegExp(`${meetingPath}$`));
    await expect(page.getByText('COMPLETED', { exact: true }).first()).toBeVisible();
    results.temporaryMeeting = { name, day: 'Saturday', completed: true, decisionAttached: true, riskAttached: true };
    await openRoute(page, '/admin');
    await page.getByRole('button', { name: 'Open Data Cleanup admin tab' }).click();
    await page.getByLabel(`Select meeting ${name} for cleanup`).check();
    await page.getByLabel('Meeting cleanup confirmation phrase').fill('DELETE MEETINGS');
    await page.getByRole('button', { name: 'Delete selected meetings' }).click();
    await expect(page.getByText('Deleted 1 meeting series.')).toBeVisible();
    results.temporaryMeeting.cleanedUp = true;
  });

  await scenario('Deterministic temporary initiative cleanup', 'Return ACME to its canonical ten-initiative demo state entirely through the admin browser workflow.', async () => {
    expect(temporaryInitiativeName).toBeTruthy();
    expect(temporaryInitiativeCode).toBeTruthy();
    await openRoute(page, '/admin');
    await page.getByRole('button', { name: 'Open Data Cleanup admin tab' }).click();
    await page.getByRole('button', { name: `Select ${temporaryInitiativeName} for deletion` }).click();
    await page.getByLabel('Initiative delete confirmation code').fill(temporaryInitiativeCode);
    await page.locator('div[role="status"].fixed.inset-0').waitFor({ state: 'hidden', timeout: 30_000 });
    await page.getByRole('button', { name: 'Delete selected initiative' }).click();
    await expect(page.getByText(`Deleted ${temporaryInitiativeCode}.`)).toBeVisible();
    await openRoute(page, '/initiatives/pipeline');
    await expect(page.getByText(/10 initiatives/).first()).toBeVisible();
    await expect(page.getByText(temporaryInitiativeName)).toHaveCount(0);
    await openRoute(page, '/meetings');
    await expect(page.getByText(results.temporaryMeeting?.name || 'impossible-name')).toHaveCount(0);
    results.temporaryInitiative.cleanedUp = true;
  });

  expect(results.pageErrors, 'Unexpected browser page errors').toEqual([]);
  expect(results.serverErrors, 'Unexpected server errors observed by the browser').toEqual([]);
  } finally {
    const needsRecovery = (
      Boolean(temporaryMeetingName) && !results.temporaryMeeting?.cleanedUp
    ) || (
      Boolean(temporaryInitiativeName && temporaryInitiativeCode)
      && !results.temporaryInitiative?.cleanedUp
    );
    if (needsRecovery) {
      try {
        await recoverAcmeRecords(
          browser,
          temporaryInitiativeName,
          temporaryInitiativeCode,
          temporaryMeetingName,
        );
        results.recoveryCleanup = 'passed';
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        results.recoveryCleanup = 'failed';
        results.recoveryCleanupError = message;
        failures.push(`Recovery cleanup: ${message}`);
      }
    } else {
      results.recoveryCleanup = 'not-required';
    }
    writeFileSync(resolve(repo, 'scratch/issue-447/acme-guide-full.json'), `${JSON.stringify(results, null, 2)}\n`);
  }
  expect(failures, failures.join('\n\n')).toEqual([]);
});
