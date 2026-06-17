import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawn } from 'node:child_process';

const uiBaseUrl = process.env.TRANSMUTER_UI_BASE_URL ?? 'http://localhost:4300';
const apiBaseUrl = process.env.TRANSMUTER_API_BASE_URL ?? 'http://localhost:8000';
const chromeBin = process.env.CHROME_BIN ?? '/usr/bin/chromium-browser';
const email = process.env.TRANSMUTER_E2E_EMAIL ?? 'admin@acme-transformation.dev';
const password = process.env.TRANSMUTER_E2E_PASSWORD ?? 'Transmuter2026!';
const debugPort = Number(process.env.CHROME_DEBUG_PORT ?? 9224);
const baselineYear = Number(process.env.TRANSMUTER_BASELINE_YEAR ?? 2026);

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function decimal(value) {
  return Number.parseFloat(String(value ?? '0'));
}

function approx(actual, expected, tolerance, label) {
  assert(
    Math.abs(actual - expected) <= tolerance,
    `${label}: expected ${expected}, got ${actual}`,
  );
}

async function waitFor(fn, label, timeoutMs = 25_000) {
  const start = Date.now();
  let lastError;
  while (Date.now() - start < timeoutMs) {
    try {
      const value = await fn();
      if (value) return value;
    } catch (error) {
      lastError = error;
    }
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  throw new Error(`Timed out waiting for ${label}${lastError ? `: ${lastError.message}` : ''}`);
}

async function requestJson(url, init = {}) {
  const response = await fetch(url, init);
  const text = response.status === 204 ? '' : await response.text();
  assert(response.ok, `${url} returned ${response.status}: ${text.slice(0, 500)}`);
  return text ? JSON.parse(text) : null;
}

async function connectToPage(wsUrl) {
  const socket = new WebSocket(wsUrl);
  let nextId = 1;
  const pending = new Map();

  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (!message.id || !pending.has(message.id)) return;
    const { resolve, reject } = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) reject(new Error(message.error.message));
    else resolve(message.result);
  });

  await new Promise((resolve, reject) => {
    socket.addEventListener('open', resolve, { once: true });
    socket.addEventListener('error', reject, { once: true });
  });

  return {
    send(method, params = {}) {
      const id = nextId++;
      socket.send(JSON.stringify({ id, method, params }));
      return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
    },
    close() {
      socket.close();
    },
  };
}

async function evalJs(page, expression) {
  const result = await page.send('Runtime.evaluate', {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (result.exceptionDetails) {
    throw new Error(
      result.exceptionDetails.exception?.description
      ?? result.exceptionDetails.text
      ?? 'Browser evaluation failed',
    );
  }
  return result.result.value;
}

async function assertPage(page, url, predicate, label, timeoutMs = 25_000) {
  await page.send('Page.navigate', { url });
  await waitFor(
    () => evalJs(page, 'document.body !== null && document.readyState !== "loading"'),
    `${label} document body`,
    timeoutMs,
  );
  try {
    await waitFor(() => evalJs(page, predicate), label, timeoutMs);
  } catch (error) {
    const state = await evalJs(page, `
      ({
        href: location.href,
        title: document.title,
        text: document.body?.innerText?.slice(0, 1000) ?? ''
      })
    `).catch(() => null);
    if (state) {
      throw new Error(`${error.message}; page=${JSON.stringify(state)}`);
    }
    throw error;
  }
}

async function runApiChecks(authHeaders) {
  const config = await requestJson(`${apiBaseUrl}/financial-engine-configuration`, {
    headers: authHeaders,
  });
  const definitions = config.definitions ?? [];
  const definitionByKey = new Map(definitions.map(item => [item.key, item]));
  [
    'annual_revenue_baseline',
    'annual_gross_margin_baseline',
    'revenue_uplift',
    'gm_uplift',
    'cost_savings',
    'target_revenue',
    'target_gross_margin',
    'revenue_growth_pct',
    'gross_margin_run_rate_pct',
    'gm_improvement_pct',
  ].forEach(key => assert(definitionByKey.has(key), `Missing configured metric ${key}`));

  const tenantBaseline = await requestJson(
    `${apiBaseUrl}/admin/financial-engine/annual-baselines?baseline_year=${baselineYear}`,
    { headers: authHeaders },
  );
  const baselineByMetric = new Map(tenantBaseline.values.map(item => [item.metric_key, item]));
  approx(decimal(baselineByMetric.get('annual_revenue_baseline')?.value), 20_000_000, 1, 'tenant revenue baseline');
  approx(decimal(baselineByMetric.get('annual_gross_margin_baseline')?.value), 9_000_000, 1, 'tenant gross margin baseline');

  const initiatives = await requestJson(`${apiBaseUrl}/initiatives?page_size=25`, {
    headers: authHeaders,
  });
  assert((initiatives.items ?? []).length === 10, 'Expected exactly 10 enterprise initiatives');

  let initiativeRevenueBaseline = 0;
  let initiativeGrossMarginBaseline = 0;
  for (const initiative of initiatives.items) {
    const baseline = await requestJson(
      `${apiBaseUrl}/initiatives/${initiative.id}/financials/baseline?baseline_year=${baselineYear}`,
      { headers: authHeaders },
    );
    assert(baseline.locked === true, `${initiative.name} baseline should be locked after seeded Gate 2 approval`);
    const values = new Map(baseline.values.map(item => [item.metric_key, item]));
    initiativeRevenueBaseline += decimal(values.get('annual_revenue_baseline')?.value);
    initiativeGrossMarginBaseline += decimal(values.get('annual_gross_margin_baseline')?.value);
  }
  approx(initiativeRevenueBaseline, 20_000_000, 1, 'initiative revenue baseline allocation');
  approx(initiativeGrossMarginBaseline, 9_000_000, 1, 'initiative gross margin baseline allocation');

  const fy28 = await requestJson(`${apiBaseUrl}/portfolio/financials?granularity=yearly&year=2028`, {
    headers: authHeaders,
  });
  const summaryByKey = new Map((fy28.summary ?? []).map(item => [item.key, item]));
  assert(decimal(summaryByKey.get('benefits')?.plan) > 9_000_000, 'FY28 plan benefits should include margin and savings');
  assert(decimal(summaryByKey.get('costs')?.plan) > 700_000, 'FY28 recurring costs should be present');
  assert(decimal(summaryByKey.get('net_value')?.plan) > 8_000_000, 'FY28 net run-rate value should be steering-positive');

  const contributors = await requestJson(
    `${apiBaseUrl}/portfolio/financials/contributors?granularity=yearly&period=2028&year=2028`,
    { headers: authHeaders },
  );
  const contributorBenefits = (contributors.contributors ?? []).reduce((sum, item) => sum + decimal(item.benefits_plan), 0);
  const contributorRecurring = (contributors.contributors ?? []).reduce((sum, item) => sum + decimal(item.recurring_costs_plan), 0);
  const contributorNet = (contributors.contributors ?? []).reduce((sum, item) => sum + decimal(item.net_value_plan), 0);
  const benefitLineCount = (contributors.contributors ?? []).reduce((sum, item) => sum + (item.benefit_lines ?? []).length, 0);
  approx(contributorBenefits, decimal(summaryByKey.get('benefits')?.plan), 1, 'FY28 contributor benefit reconciliation');
  approx(contributorRecurring, decimal(summaryByKey.get('costs')?.plan), 1, 'FY28 contributor recurring cost reconciliation');
  approx(contributorNet, decimal(summaryByKey.get('net_value')?.plan), 1, 'FY28 contributor net value reconciliation');
  assert(benefitLineCount >= 10, 'Contributor drawer should include benefit-line detail');

  const benefitLedger = await requestJson(`${apiBaseUrl}/benefit-ledger/summary?granularity=yearly`, {
    headers: authHeaders,
  });
  assert(decimal(benefitLedger.bankable_plan_amount) > 0, 'Benefit ledger should include seeded locked baseline');
  assert(decimal(benefitLedger.actual_amount) > 0, 'Benefit ledger should include seeded actuals');

  const bridge = await requestJson(`${apiBaseUrl}/portfolio/value-bridge`, { headers: authHeaders });
  const bridgeLabels = (bridge.rows ?? []).map(row => row.label);
  ['Revenue Uplift', 'Gross Margin Uplift', 'Cost Savings', 'Recurring Costs', 'One-off Costs'].forEach(label => {
    assert(bridgeLabels.includes(label), `Portfolio value bridge missing ${label}`);
  });

  const financialInitiative = initiatives.items.find(item => item.initiative_code === 'ENT-006') ?? initiatives.items[0];
  const grid = await requestJson(`${apiBaseUrl}/initiatives/${financialInitiative.id}/financials`, {
    headers: authHeaders,
  });
  assert(grid.baseline?.baseline_year === baselineYear, 'Initiative grid should include FY26 annual baseline context');
  assert((grid.scenarios ?? []).some(item => item.key === 'baseline'), 'Initiative grid missing baseline scenario');
  assert((grid.values ?? []).some(item => item.year === 2028 && item.month === 1), 'Initiative grid missing FY28 monthly values');

  const scenarioSummary = await requestJson(
    `${apiBaseUrl}/initiatives/${financialInitiative.id}/financials/scenario-summary?scenario=base`,
    { headers: authHeaders },
  );
  assert(decimal(scenarioSummary.revenue_uplift) > 1_000_000, 'Commercial scenario should carry revenue uplift');

  const rebaselineInitiative = initiatives.items.find(item => item.initiative_code === 'ENT-005');
  assert(rebaselineInitiative, 'ENT-005 should exist for rebaseline validation');
  const rebaselinePlan = await requestJson(
    `${apiBaseUrl}/initiatives/${rebaselineInitiative.id}/bankable-plan`,
    { headers: authHeaders },
  );
  assert((rebaselinePlan.history ?? []).length >= 2, 'ENT-005 should include a seeded rebaseline history');
  assert(rebaselinePlan.current?.version === 2, 'ENT-005 current bankable plan should be version 2');

  return { initiatives, financialInitiative };
}

async function runBrowserChecks(auth, initiative) {
  const userDataDir = await mkdtemp(join(tmpdir(), 'transmuter-annual-baseline-ui-'));
  const chrome = spawn(chromeBin, [
    '--headless=new',
    `--remote-debugging-port=${debugPort}`,
    `--user-data-dir=${userDataDir}`,
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-gpu',
    '--no-sandbox',
    'about:blank',
  ], { stdio: ['ignore', 'ignore', 'pipe'] });

  chrome.stderr.on('data', chunk => {
    const text = chunk.toString();
    if (!text.includes('DevTools listening')) process.stderr.write(text);
  });

  let page;
  try {
    await waitFor(
      () => fetch(`http://127.0.0.1:${debugPort}/json/version`).then(r => r.ok),
      'Chrome DevTools endpoint',
    );
    const targets = await requestJson(`http://127.0.0.1:${debugPort}/json/list`);
    const target = targets.find(item => item.type === 'page') ?? targets[0];
    assert(target?.webSocketDebuggerUrl, 'Chrome page target was not available');
    page = await connectToPage(target.webSocketDebuggerUrl);
    await page.send('Runtime.enable');
    await page.send('Page.enable');

    await page.send('Page.navigate', { url: uiBaseUrl });
    await waitFor(() => evalJs(page, 'document.readyState === "complete"'), 'initial page load');
    await evalJs(page, `
      localStorage.setItem('access_token', ${JSON.stringify(auth.access_token)});
      localStorage.setItem('refresh_token', ${JSON.stringify(auth.refresh_token)});
      true
    `);

    await assertPage(
      page,
      `${uiBaseUrl}/admin`,
      `
        document.body.innerText.toLowerCase().includes('financial configuration')
        && document.body.innerText.toLowerCase().includes('admin')
      `,
      'admin shell',
    );
    await evalJs(page, `
      (() => {
        const tab = [...document.querySelectorAll('button')]
          .find(node => node.textContent.trim().toLowerCase().includes('financial configuration'));
        if (!tab) throw new Error('Financial Configuration tab not found');
        tab.click();
        return true;
      })()
    `);
    try {
      await waitFor(
        () => evalJs(page, `
          document.body.innerText.toLowerCase().includes('annual baselines')
          && document.body.innerText.toLowerCase().includes('financial metric engine')
          && [...document.querySelectorAll('input')].some(input => input.value === String(${baselineYear}))
        `),
        'admin annual baseline panel',
      );
    } catch (error) {
      const state = await evalJs(page, `
        ({
          href: location.href,
          activeButtonTexts: [...document.querySelectorAll('button')]
            .map(button => button.textContent.trim())
            .slice(0, 25),
          text: document.body?.innerText?.slice(0, 1600) ?? '',
          inputs: [...document.querySelectorAll('input')].map(input => input.value).slice(0, 20)
        })
      `);
      throw new Error(`${error.message}; page=${JSON.stringify(state)}`);
    }

    await assertPage(
      page,
      `${uiBaseUrl}/initiatives/pipeline`,
      `
        document.body.innerText.includes('Transformation PMO & Benefits Office')
        && document.body.innerText.includes('Pricing & Discount Optimization')
        && document.body.innerText.includes('AI Service Desk Automation')
      `,
      'enterprise initiative pipeline',
    );

    await assertPage(
      page,
      `${uiBaseUrl}/initiatives/${initiative.id}`,
      `
        document.body.innerText.includes(${JSON.stringify(initiative.name)})
        && document.body.innerText.includes('Financials')
      `,
      'initiative detail shell',
    );
    await evalJs(page, `
      (() => {
        const button = [...document.querySelectorAll('button,a')]
          .find(node => node.textContent.trim() === 'Financials');
        if (!button) throw new Error('Financials tab not found');
        button.click();
        return true;
      })()
    `);
    await waitFor(
      () => evalJs(page, `
        document.body.innerText.includes('Baseline')
        && document.body.innerText.includes('Plan Base')
        && document.body.innerText.includes('Revenue Uplift')
      `),
      'initiative financials tab with baseline scenario',
    );

    await assertPage(
      page,
      `${uiBaseUrl}/financials`,
      `
        document.body.innerText.includes('Portfolio Financials')
        || document.body.innerText.includes('Net Value')
        || document.body.innerText.includes('Run-rate')
      `,
      'portfolio financials dashboard',
    );
  } finally {
    if (page) page.close();
    chrome.kill('SIGTERM');
    await rm(userDataDir, { recursive: true, force: true });
  }
}

async function main() {
  await requestJson(`${apiBaseUrl}/health`);
  const auth = await requestJson(`${apiBaseUrl}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  const authHeaders = { Authorization: `Bearer ${auth.access_token}` };
  const { initiatives, financialInitiative } = await runApiChecks(authHeaders);
  await runBrowserChecks(auth, financialInitiative);
  console.log(
    `Annual baseline enterprise scenario passed: ${initiatives.items.length} initiatives, FY${String(baselineYear).slice(-2)} baseline, FY28 revenue/gross-margin dashboard checks.`,
  );
}

main().catch(error => {
  console.error(error);
  process.exit(1);
});
