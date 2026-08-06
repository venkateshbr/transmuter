import { test, expect } from '@playwright/test';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const repo = resolve(import.meta.dirname, '../../..');
const credentials = JSON.parse(readFileSync(resolve(repo, 'credentials.json'), 'utf8'));
const fixture = credentials.five_tenant_fixture;
const baseUrl = fixture.base_url;
const password = fixture.shared_password;
const platformEmail = credentials.platform_admin.email;
const platformPassword = credentials.platform_admin.password;
const deployedCommit = process.env.TRANSMUTER_DEPLOYED_COMMIT;
if (fixture.environment !== 'dev' || new URL(baseUrl).hostname !== 'transmuter-dev.ishirock.tech') {
  throw new Error('Fresh-tenant acceptance is restricted to the approved dev environment.');
}
if (!deployedCommit || !/^[0-9a-f]{7,40}$/i.test(deployedCommit)) {
  throw new Error('TRANSMUTER_DEPLOYED_COMMIT must identify the deployed dev commit.');
}
const runId = new Date()
  .toISOString()
  .replace(/[-:TZ.]/g, '')
  .slice(0, 14);
const tenantName = `Acme Full Guide ${runId}`;
const tenantSlug = `acme-full-guide-${runId}`;
const adminEmail = `acme-full-${runId}@qa.transmuter-dev.ishirock.tech`;
const results = {
  environment: baseUrl,
  commit: deployedCommit,
  tenant: tenantName,
  tenantSlug,
  execution: 'external Playwright Chromium; UI mutations and rendered assertions',
  scenarios: [],
  pageErrors: [],
  serverErrors: [],
  initiativeCodes: [],
  cleanup: false,
};

async function settle(page) {
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle', { timeout: 8_000 }).catch(() => undefined);
  await page
    .locator('div[role="status"].fixed.inset-0')
    .waitFor({ state: 'hidden', timeout: 30_000 })
    .catch(() => undefined);
  await page.waitForTimeout(350);
}

async function openRoute(page, route) {
  await page.goto(`${baseUrl}${route}`, { waitUntil: 'domcontentloaded' });
  await settle(page);
  expect(new URL(page.url()).pathname).toBe(route);
}

async function login(page, email, pass) {
  await page.goto(`${baseUrl}/auth/login`, { waitUntil: 'domcontentloaded' });
  await page.getByLabel('Email Address').fill(email);
  await page.getByLabel('Password').fill(pass);
  await page.getByRole('button', { name: 'Sign in to Transmuter' }).click();
}

async function selectContaining(select, text) {
  await expect
    .poll(async () => await select.locator('option').filter({ hasText: text }).count(), {
      timeout: 20_000,
    })
    .toBeGreaterThan(0);
  const option = select.locator('option').filter({ hasText: text }).first();
  await select.selectOption(await option.getAttribute('value'));
}

async function selectFirst(select) {
  await expect
    .poll(async () => await select.locator('option[value]:not([value=""])').count(), {
      timeout: 20_000,
    })
    .toBeGreaterThan(0);
  const option = select.locator('option[value]:not([value=""])').first();
  await select.selectOption(await option.getAttribute('value'));
}

async function expectInputValue(locator, value) {
  await expect
    .poll(
      async () =>
        locator.evaluateAll(
          (elements, expected) => elements.some((element) => element.value === expected),
          value,
        ),
      { timeout: 20_000 },
    )
    .toBe(true);
}

async function createAdminItem(page, inputLabel, buttonLabel, value) {
  const input = page.getByLabel(inputLabel);
  const button = page.getByLabel(buttonLabel);
  await expect(input).toHaveValue('', { timeout: 30_000 });
  await input.fill(value);
  await expect(button).toBeEnabled();
  await button.click();
  await expect(input).toHaveValue('', { timeout: 30_000 });
}

async function clickRetry(locator) {
  let lastError;
  for (let attempt = 0; attempt < 4; attempt += 1) {
    try {
      await locator.click();
      return;
    } catch (error) {
      lastError = error;
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
  }
  throw lastError;
}

async function checkout(page) {
  await page.goto(`${baseUrl}/get-started`, { waitUntil: 'domcontentloaded' });
  await page.getByLabel('Organization name').fill(tenantName);
  await expect(page.getByLabel('Organization short name')).toHaveValue(tenantSlug);
  await page.getByLabel('Initial admin name').fill('Acme Transformation Office Director');
  await page.getByLabel('Initial admin email').fill(adminEmail);
  await page.getByLabel('Set password').fill(password);
  await page.getByLabel('Confirm password').fill(password);
  await page.getByLabel('Planned users').fill('10');
  await page.getByLabel('Billing interval').selectOption('month');
  await page.getByRole('button', { name: 'Continue to Stripe Checkout' }).click();
  await page.waitForURL((url) => url.hostname.includes('stripe.com'), { timeout: 30_000 });
  await page.locator('input[name="cardNumber"]').fill('4242424242424242');
  await page.locator('input[name="cardExpiry"]').fill('1230');
  await page.locator('input[name="cardCvc"]').fill('123');
  if (await page.locator('input[name="billingName"]').count())
    await page.locator('input[name="billingName"]').fill('Acme QA');
  if (await page.locator('input[name="billingPostalCode"]').count())
    await page.locator('input[name="billingPostalCode"]').fill('94107');
  await page.getByRole('button', { name: /Subscribe|Pay/i }).click();
  await page.waitForURL(
    (url) => url.origin === new URL(baseUrl).origin && url.pathname === '/subscription/success',
    { timeout: 90_000 },
  );
  await expect(page.getByRole('link', { name: 'Go to login' })).toBeVisible({ timeout: 60_000 });
  await page.getByRole('link', { name: 'Go to login' }).click();
  await login(page, adminEmail, password);
  await page.waitForURL((url) => url.pathname === '/dashboard', { timeout: 30_000 });
}

async function cleanup(browser) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  try {
    await login(page, platformEmail, platformPassword);
    await page.waitForURL((url) => url.pathname === '/platform', { timeout: 30_000 });
    await expect(page.locator('body')).not.toContainText('Loading', { timeout: 30_000 });
    const button = page.getByRole('button', { name: `Delete tenant ${tenantName}` });
    if (!(await button.count())) return false;
    await button.click();
    await page.getByLabel('Tenant deletion confirmation slug').fill(tenantSlug);
    await page.getByRole('button', { name: 'Delete tenant', exact: true }).click();
    await expect(page.locator('body')).toContainText('Tenant deleted.', { timeout: 60_000 });
    await page.getByRole('button', { name: 'Close', exact: true }).click();
    await expect(page.getByRole('button', { name: `Delete tenant ${tenantName}` })).toHaveCount(0);
    return true;
  } finally {
    await context.close();
  }
}

test('fresh-tenant ACME full setup guide browser acceptance', async ({ page, browser }) => {
  test.setTimeout(1_800_000);
  mkdirSync(resolve(repo, 'scratch/issue-447'), { recursive: true });
  page.on('pageerror', (error) => results.pageErrors.push(error.message));
  page.on('response', (response) => {
    if (response.status() >= 500)
      results.serverErrors.push({
        status: response.status(),
        path: new URL(response.url()).pathname,
      });
  });
  let provisioned = false;
  async function scenario(name, work) {
    const started = Date.now();
    console.log(`[fresh-guide] START ${name}`);
    await work();
    results.scenarios.push({ name, status: 'passed', durationMs: Date.now() - started });
    console.log(`[fresh-guide] PASS  ${name}`);
  }

  try {
    await scenario('Public signup, Stripe checkout, provisioning, and first login', async () => {
      provisioned = true;
      await checkout(page);
      await openRoute(page, '/profile');
      await expect(page.locator('body')).toContainText('Acme Transformation Office Director');
      await expect(page.locator('body')).toContainText(/Transformation Office/i);
      await openRoute(page, '/admin');
      await expect(page.getByLabel('Legal entity name')).toHaveValue(tenantName);
      await page.getByRole('button', { name: 'Open Billing admin tab' }).click();
      await expect(page.locator('body')).toContainText(/Active|Stripe/i);
    });

    await scenario('Strategic master data and financial defaults', async () => {
      await openRoute(page, '/admin');
      await page.getByRole('button', { name: 'Open Strategic Parameters admin tab' }).click();
      for (const name of [
        'Automation',
        'Commercial Growth',
        'ERP & Data Platform',
        'Offshoring & Operating Model',
        'Procurement & Supply Chain',
      ]) {
        await createAdminItem(page, 'New workstream name', 'Create workstream', name);
        await expectInputValue(page.getByLabel('Workstream name'), name);
      }
      for (const name of [
        'Corporate',
        'Commercial',
        'Operations',
        'Shared Services',
        'Technology',
      ]) {
        await createAdminItem(page, 'New business unit name', 'Create business unit', name);
        await expectInputValue(page.getByLabel('Business unit name'), name);
      }
      for (const name of ['Group', 'Regional'])
        await createAdminItem(page, 'New market name', 'Create market', name);
      await createAdminItem(
        page,
        'New theme name',
        'Create theme',
        'Manufacturing productivity and profitable growth',
      );
      for (const name of ['automation', 'commercial', 'offshoring', 'other'])
        await createAdminItem(page, 'New tag name', 'Create tag', name);
      await page.getByRole('button', { name: 'Open Financial Configuration admin tab' }).click();
      const financialWorkbench = page.getByTestId('financial-configuration-workbench');
      await expect(financialWorkbench).toContainText('10 metrics · 6 bridge rows');
      await page.getByLabel('Reporting currency').fill('USD');
      await page.getByLabel('Fiscal year start month').selectOption({ label: 'January' });
      await page.getByLabel('Save reporting settings').click();
      await expect(financialWorkbench).toContainText('Financial settings saved.');
      await page.getByTestId('financial-subtab-metrics').click();
      await expect(page.getByRole('button', { name: /Edit metric / })).toHaveCount(10);
      await expect(page.getByLabel('Metric formula key')).not.toHaveValue('');
      await page.getByTestId('financial-subtab-taxonomy').click();
      await expect(page.getByLabel('Cost category label')).toHaveCount(8);
      await page.getByTestId('financial-subtab-planning').click();
      await expect(page.getByLabel('Scenario label')).toHaveCount(4);
      await page.getByLabel('Tenant baseline fiscal year').fill('2026');
      await page.getByLabel('Tenant annual baseline for Annual Revenue Baseline').fill('20000000');
      await page
        .getByLabel('Tenant annual baseline for Annual Gross Margin Baseline')
        .fill('9000000');
      await page.getByLabel('Save tenant annual baselines').click();
      await openRoute(page, '/admin');
      await page.getByRole('button', { name: 'Open Strategic Parameters admin tab' }).click();
      for (const name of ['Group', 'Regional'])
        await expectInputValue(page.getByLabel('Market name'), name);
      await expectInputValue(
        page.getByLabel('Theme name'),
        'Manufacturing productivity and profitable growth',
      );
      for (const name of ['automation', 'commercial', 'offshoring', 'other'])
        await expectInputValue(page.getByLabel('Tag name'), name);
    });

    await scenario('Five stage gates, criteria, plan governance, and dashboard menu', async () => {
      await openRoute(page, '/admin');
      await page.getByRole('button', { name: 'Open Governance Engine admin tab' }).click();
      const gates = [
        [1, 'Opportunity qualified', 'identified', 'scoping'],
        [2, 'Business case approved', 'scoping', 'approved'],
        [3, 'Plan mobilized', 'approved', 'planning'],
        [4, 'Execution launched', 'planning', 'executing'],
        [5, 'Value sustained', 'executing', 'complete'],
      ];
      for (let index = 0; index < gates.length; index += 1) {
        const [number, label, from, to] = gates[index];
        await page.getByLabel('Add stage gate').click();
        await page.getByLabel('Gate number').nth(index).fill(String(number));
        await page.getByLabel('Gate label').nth(index).fill(label);
        await page.getByLabel('Gate from stage').nth(index).fill(from);
        await page.getByLabel('Gate to stage').nth(index).fill(to);
        const required = page.getByLabel('Require all criteria').nth(index);
        if (!(await required.isChecked())) await required.check();
        await page.getByLabel('Approver roles').nth(index).fill('transformation_office');
        await page.getByLabel('Save stage gate').nth(index).click({ force: true });
        await expect(page.getByLabel('Gate label')).toHaveCount(index + 1, { timeout: 30_000 });
        await page.getByLabel('New gate criterion').nth(index).fill(`${label}: evidence reviewed`);
        await page.getByLabel('Create gate criterion').nth(index).click({ force: true });
        await expect(page.getByLabel('Gate criterion label').nth(index)).toHaveValue(
          `${label}: evidence reviewed`,
        );
      }
      await page.getByLabel('Bankable plan lock gate number').fill('2');
      await page.getByLabel('Annual baseline lock gate number').fill('2');
      for (const label of [
        'Lock plan on gate approval',
        'Lock annual baseline on gate approval',
        'Allow governed rebaseline',
      ]) {
        const control = page.getByLabel(label);
        if (!(await control.isChecked())) await control.check();
      }
      await page
        .getByLabel('Rebaseline roles')
        .fill('transformation_office, finance_lead, pmo_lead');
      await page.getByLabel('Save bankable plan governance settings').click();
      await page.getByRole('button', { name: 'Open Dashboard Configuration admin tab' }).click();
      const enables = page.locator('input[aria-label^="Enable "]');
      for (let index = 0; index < (await enables.count()); index += 1)
        if (!(await enables.nth(index).isChecked())) await enables.nth(index).check();
      await page.getByLabel('Save dashboard configuration').click();
      await page.getByRole('button', { name: 'Open General admin tab' }).click();
      await page.getByLabel('Refresh setup status').click();
      await expect(page.getByText('7/7 complete', { exact: true })).toBeVisible();
    });

    await scenario('Ten-person operating model', async () => {
      await openRoute(page, '/people');
      const people = [
        ['Tenant Administrator', 'tenant_admin'],
        ['PMO Lead', 'pmo_lead'],
        ['Finance Lead', 'finance_lead'],
        ['Workstream Lead', 'workstream_lead'],
        ['Initiative Owner', 'initiative_owner'],
        ['Business Benefit Owner', 'business_benefit_owner'],
        ['Executive Sponsor', 'executive_sponsor'],
        ['Management Viewer', 'viewer'],
        ['Transformation Analyst', 'transformation_office'],
      ];
      for (let index = 0; index < people.length; index += 1) {
        const [name, role] = people[index];
        await page.getByRole('button', { name: 'Add User' }).click();
        await page.getByLabel('Create user mode').click();
        await page
          .getByLabel('Invite email')
          .fill(`acme-full-${role}-${runId}@qa.transmuter-dev.ishirock.tech`);
        await page.getByLabel('Invite display name').fill(name);
        await page.getByLabel('Invite title').fill(name);
        await page.getByLabel('Invite role').selectOption(role);
        await page.locator('input[aria-label="Temporary password"]').fill(password);
        if (role === 'workstream_lead')
          await page.locator('input[aria-label^="Assign "]').first().check();
        await page.getByRole('button', { name: 'Create user', exact: true }).click();
        await expect(page.getByText(name, { exact: true }).first()).toBeVisible();
        await page.getByLabel('Close user profile').click();
      }
      await page.getByRole('button', { name: 'Pending Access' }).click();
      await expect(
        page.locator('.card').filter({ hasText: 'Pending Users' }).locator('tbody tr'),
      ).toHaveCount(9);
    });

    const initiatives = [
      [
        'Transformation PMO and Value Office',
        'Automation',
        'Corporate',
        'other',
        'capability_building',
      ],
      ['Smart Factory Automation', 'Automation', 'Operations', 'automation', 'cost_reduction'],
      [
        'Commercial Pricing Excellence',
        'Commercial Growth',
        'Commercial',
        'commercial',
        'revenue_growth',
      ],
      [
        'Shared Services Consolidation',
        'Offshoring & Operating Model',
        'Shared Services',
        'offshoring',
        'cost_reduction',
      ],
      [
        'Enterprise Data and ERP Modernization',
        'ERP & Data Platform',
        'Technology',
        'automation',
        'capability_building',
      ],
      [
        'Aftermarket Revenue Growth',
        'Commercial Growth',
        'Commercial',
        'commercial',
        'revenue_growth',
      ],
      [
        'Strategic Account Expansion',
        'Commercial Growth',
        'Commercial',
        'commercial',
        'revenue_growth',
      ],
      [
        'Strategic Procurement',
        'Procurement & Supply Chain',
        'Operations',
        'other',
        'cost_reduction',
      ],
      [
        'Supply Chain Control Tower',
        'Procurement & Supply Chain',
        'Operations',
        'automation',
        'capability_building',
      ],
      [
        'AI-enabled Predictive Maintenance',
        'Automation',
        'Operations',
        'automation',
        'cost_reduction',
      ],
    ];
    const paths = [];
    await scenario('Ten guided initiatives and HITL planning suggestions', async () => {
      for (let index = 0; index < initiatives.length; index += 1) {
        const [name, workstream, unit, tag, type] = initiatives[index];
        await openRoute(page, '/initiatives/new');
        if (index === 0) {
          const downloadPromise = page.waitForEvent('download');
          await page.getByLabel('Download blank initiative template').click();
          const download = await downloadPromise;
          expect(await download.failure()).toBeNull();
        }
        await page.getByLabel('Create initiative with Transmuter').click();
        await page.locator('#init-name').fill(name);
        await selectContaining(page.locator('#init-workstream'), workstream);
        await page.getByLabel(`Toggle business unit ${unit}`).check();
        await selectContaining(page.locator('#init-country'), index % 2 ? 'Regional' : 'Group');
        await selectFirst(page.locator('#init-theme'));
        await page.locator('#init-type').selectOption(type);
        await page.locator('#init-impact').selectOption('recurring');
        await page.locator('#init-priority').selectOption(index < 5 ? 'high' : 'medium');
        await page.locator('#init-tag').selectOption(tag);
        await page.getByLabel('Go to next step').click();
        if (index === 0) {
          await page.getByLabel('Generate initiative narrative').click();
          await expect
            .poll(async () => (await page.locator('#init-summary').inputValue()).length, {
              timeout: 90_000,
            })
            .toBeGreaterThan(10);
        }
        await page
          .locator('#init-summary')
          .fill(
            `${name} converts a defined transformation opportunity into measurable enterprise value.`,
          );
        await page
          .locator('#init-context-problem')
          .fill(
            'Fragmented ownership, manual controls, and inconsistent data prevent reliable value delivery.',
          );
        await page
          .locator('#init-value-logic')
          .fill(
            'Standardized process, technology enablement, and accountable adoption deliver recurring value by FY2028.',
          );
        await page
          .locator('#init-deps')
          .fill('Requires executive sponsorship, validated data, and cross-functional adoption.');
        await page.getByLabel('Go to next step').click();
        await selectFirst(page.locator('#init-owner'));
        await selectFirst(page.locator('#init-group-owner'));
        await page.locator('#init-start').fill('2026-08-01');
        await page.locator('#init-end').fill('2028-06-30');
        await page.getByLabel('Generate initiative suggestions').click();
        await expect(page.getByText('HITL Review', { exact: true })).toBeVisible({
          timeout: 90_000,
        });
        await page.getByLabel('Create initiative').click();
        await page.waitForURL(/\/initiatives\/[0-9a-f-]+$/i, { timeout: 45_000 });
        paths.push(new URL(page.url()).pathname);
        await expect(page.getByRole('heading', { name }).first()).toBeVisible();
        const code = (
          await page.locator('app-overview-tab span.font-mono').first().innerText()
        ).trim();
        results.initiativeCodes.push(code);
      }
      await openRoute(page, '/initiatives/pipeline');
      await expect(page.getByText(/10 initiatives/).first()).toBeVisible();
    });

    await scenario(
      'Initiative scope, baseline, benefits, costs, delivery artifacts, dependency, and lock',
      async () => {
        const path = paths[0];
        await openRoute(page, `${path}/financial-scope`);
        for (const label of [
          'Annual Revenue Baseline',
          'Annual Gross Margin Baseline',
          'Gross Margin Uplift',
          'Cost Savings',
        ]) {
          const toggle = page
            .locator('label')
            .filter({ hasText: label })
            .getByLabel('Toggle financial metric')
            .first();
          if (!(await toggle.isChecked())) await toggle.check();
        }
        for (const label of ['Implementation / Project Cost', 'Software / Licenses']) {
          const toggle = page
            .locator('label')
            .filter({ hasText: label })
            .getByLabel('Toggle cost category')
            .first();
          if (!(await toggle.isChecked())) await toggle.check();
        }
        await page.getByLabel('Save financial scope').click();
        await page.waitForURL(new RegExp(`${path}$`));
        const financialLoad = page.waitForResponse(
          (response) =>
            new URL(response.url()).pathname === `/api${path}/financials` &&
            response.status() === 200,
        );
        await page.getByRole('button', { name: 'Financials', exact: true }).click();
        await financialLoad;
        await settle(page);
        await page.getByLabel('Initiative baseline fiscal year').fill('2026');
        await page.getByLabel('Initiative baseline Annual Revenue Baseline').fill('2000000');
        await page.getByLabel('Initiative baseline Annual Gross Margin Baseline').fill('900000');
        await page.getByLabel('Save initiative annual baseline').click();
        await expect(page.getByText('Initiative annual baseline saved.')).toBeVisible();
        await selectContaining(page.getByLabel('Benefit line metric'), 'Gross Margin Uplift');
        await page.getByLabel('Benefit line name').fill('PMO delivery acceleration value');
        await page.getByLabel('Benefit line confidence').fill('80');
        await page.getByLabel('Benefit line phasing mode').selectOption('spread');
        await page.getByLabel('Benefit line base amount').fill('250000');
        await page.getByLabel('Benefit line high amount').fill('300000');
        await page.getByLabel('Benefit line actual amount').fill('100000');
        await page.getByLabel('Benefit line start month').fill('2028-01');
        await page.getByLabel('Benefit line end month').fill('2028-12');
        await page.getByLabel('Add benefit line').click();
        await expect(page.getByText('PMO delivery acceleration value').first()).toBeVisible();
        await selectContaining(page.getByLabel('Cost line category'), 'Software / Licenses');
        await page.getByLabel('Cost line name').fill('PMO analytics subscription');
        await page.getByLabel('Cost line lane').selectOption('plan');
        await page.getByLabel('Cost line phasing mode').selectOption('spread');
        await page.getByLabel('Cost line amount').fill('12000');
        await page.getByLabel('Cost line start month').fill('2028-01');
        await page.getByLabel('Cost line end month').fill('2028-12');
        await page.getByLabel('Generate cost line').click();
        await expect(page.getByText('PMO analytics subscription').first()).toBeVisible();
        await page.getByRole('button', { name: 'Milestones', exact: true }).click();
        await page.getByRole('button', { name: 'New Milestone' }).click();
        await page
          .getByPlaceholder('e.g. Pilot Launch complete')
          .fill('Value office operating cadence live');
        await page
          .getByPlaceholder('Key outcomes or requirements...')
          .fill('Weekly value reviews and owner escalations operating.');
        await page.getByRole('button', { name: 'Create Milestone' }).click();
        await expect(page.getByText('Value office operating cadence live')).toBeVisible();
        await page.getByRole('button', { name: 'KPIs', exact: true }).click();
        await expect(
          page.getByRole('heading', { name: /Key Performance Indicators/i }),
        ).toBeVisible();
        await page.getByRole('button', { name: 'Risks', exact: true }).click();
        await expect(page.getByRole('heading', { name: /Risk Register/i })).toBeVisible();
        await page.getByRole('button', { name: 'Dependencies', exact: true }).click();
        await page.getByLabel('Upstream initiative').selectOption(paths[0].split('/').pop());
        await page.getByLabel('Downstream initiative').selectOption(paths[1].split('/').pop());
        await page.getByLabel('Dependency type').selectOption('blocks');
        await page.getByLabel('Dependency severity').selectOption('high');
        await page.getByLabel('Dependency due date').fill('2027-03-31');
        await page
          .getByLabel('Dependency resolution notes')
          .fill('PMO cadence must stabilize before factory scale-up.');
        await page.getByLabel('Create initiative dependency').click();
        await expect(page.locator('body')).toContainText(
          'TRN-001 · Transformation PMO and Value Office blocks',
        );
        await page.getByRole('button', { name: 'Governance', exact: true }).click();
        const gateReviewLabels = ['Opportunity qualified', 'Business case approved'];
        for (let gate = 1; gate <= 2; gate += 1) {
          await expect(page.locator('app-governance-tab h3')).toContainText(
            `${gateReviewLabels[gate - 1]} Readiness Review`,
            { timeout: 30_000 },
          );
          const checklist = page.locator('app-governance-tab label input[type="checkbox"]');
          await expect
            .poll(async () => await checklist.count(), { timeout: 30_000 })
            .toBeGreaterThan(0);
          for (let i = 0; i < (await checklist.count()); i += 1)
            if (!(await checklist.nth(i).isChecked()))
              await checklist.nth(i).check({ force: true });
          await page.getByRole('button', { name: 'Submit for Approval' }).click();
          await expect(page.getByText('Pending Approval')).toBeVisible();
          await page
            .getByPlaceholder('Review comments or requirements...')
            .fill(`Gate ${gate} approved in fresh-tenant browser acceptance.`);
          await page.getByRole('button', { name: 'Approve', exact: true }).click();
          await expect(page.locator('app-governance-tab')).toContainText('Approved');
        }
        await page.getByRole('button', { name: 'Financials', exact: true }).click();
        await settle(page);
        await expect(page.getByLabel('Initiative baseline fiscal year')).toBeDisabled();
        await expect(page.locator('body')).toContainText(/locked by governance/i);
      },
    );

    await scenario('Shared-cost pools and allocation runs', async () => {
      await openRoute(page, '/shared-costs');
      for (const label of [
        'Include shared costs in executive control tower',
        'Include shared costs in dashboard executive brief',
        'Include shared costs in portfolio financials',
      ]) {
        const control = page.getByLabel(label);
        if (!(await control.isChecked())) await control.check();
      }
      const pools = [
        ['Group technology and data platform', '650000', '585000'],
        ['Transformation PMO and benefits office', '350000', '315000'],
        ['Shared change and training support', '250000', '225000'],
        ['Central advisory and vendor support', '200000', '180000'],
      ];
      for (const [name, plan, actual] of pools) {
        await page.getByLabel('Shared cost pool name').fill(name);
        await selectFirst(page.getByLabel('Shared cost category'));
        await selectContaining(page.getByLabel('Shared cost scenario'), 'Plan Base');
        await page.getByLabel('Shared cost year').fill('2028');
        await page.getByLabel('Shared cost period grain').selectOption('annual');
        await page.getByLabel('Shared cost planned amount').fill(plan);
        await page.getByLabel('Shared cost actual amount').fill(actual);
        await page.getByLabel('Shared cost reporting treatment').selectOption('report_only');
        await page
          .getByLabel('Shared cost pool description')
          .fill('Enterprise cost allocated transparently across the transformation portfolio.');
        await page.getByLabel('Create shared cost pool').click();
        await page.getByRole('button', { name: `Select ${name}` }).click();
        await page.getByLabel('Allocation rule name').fill(`${name} equal allocation`);
        await page.getByLabel('Allocation method').selectOption('equal_split');
        await page.getByLabel('Missing basis behavior').selectOption('fail');
        await page.getByLabel('Save allocation rule').click();
        await page
          .getByRole('button', { name: `Select allocation rule ${name} equal allocation` })
          .click();
        await page.getByLabel('Preview shared cost allocation').click();
        await expect(page.locator('body')).toContainText(/Reconciled|reconciled/i);
        await page.getByLabel('Post locked shared cost allocation run').click();
        await expect(page.locator('body')).toContainText(/Locked|posted/i);
      }
    });

    await scenario('Full demo route and new-function inventory', async () => {
      const routes = [
        ['/dashboard', /Strategic Yield Dashboard/i],
        ['/initiatives/pipeline', /10 initiatives/i],
        ['/initiatives/matrix', /Matrix/i],
        ['/financials', /Financial/i],
        ['/financials/initiative-portfolio', /Initiative Portfolio/i],
        ['/financials/investments-payback', /Payback/i],
        ['/financials/benefits-register', /Benefits Register/i],
        ['/financials/bankable-plan', /Bankable Plan/i],
        ['/financials/benefit-tracking', /Benefit Tracking|Realization/i],
        ['/financials/waterline', /Waterline/i],
        ['/progress', /Milestones|Progress/i],
        ['/progress/roadmap', /Roadmap/i],
        ['/progress/action-items', /Action Items/i],
        ['/progress/status-updates', /Status Updates/i],
        ['/pmo/governance', /Governance/i],
        ['/pmo/kpis', /KPI/i],
        ['/pmo/risks', /Risk/i],
        ['/pmo/ai-insights', /AI|Insight/i],
        ['/reports/control-tower', /Control Tower/i],
        ['/meetings', /Meeting/i],
        ['/profile', /Profile|Acme/i],
      ];
      for (const [route, text] of routes) {
        await openRoute(page, route);
        await expect(page.locator('body')).toContainText(text);
      }
      await openRoute(page, '/financials');
      const downloadPromise = page.waitForEvent('download');
      await page.getByLabel('Export board pack').click();
      const download = await downloadPromise;
      expect(await download.failure()).toBeNull();
    });

    expect(results.pageErrors).toEqual([]);
    expect(results.serverErrors).toEqual([]);
  } finally {
    if (provisioned) {
      try {
        results.cleanup = await cleanup(browser);
      } catch (error) {
        results.cleanup = false;
        results.cleanupError = error instanceof Error ? error.message : String(error);
      }
    }
    writeFileSync(
      resolve(repo, 'scratch/issue-447/fresh-tenant-full-guide.json'),
      `${JSON.stringify(results, null, 2)}\n`,
    );
  }
  expect(results.cleanup).toBe(true);
});
