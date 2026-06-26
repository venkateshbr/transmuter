import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { spawn } from 'node:child_process';

const uiBaseUrl = process.env.TRANSMUTER_UI_BASE_URL ?? 'https://transmuter-dev.ishirock.tech';
const apiBaseUrl = process.env.TRANSMUTER_API_BASE_URL ?? `${uiBaseUrl}/api`;
const chromeBin = process.env.CHROME_BIN ?? '/snap/bin/chromium';
const password = process.env.TRANSMUTER_E2E_PASSWORD;
const debugPort = Number(process.env.CHROME_DEBUG_PORT ?? 9254);

const tenants = {
  pinnacle: {
    email: 'pinnacle.to@transmuter-e2e.dev',
    currency: 'USD',
    fiscalMonth: 1,
    fiscalLabel: 'January',
  },
  aurelia: {
    email: 'aurelia.to@transmuter-e2e.dev',
    currency: 'GBP',
    fiscalMonth: 4,
    fiscalLabel: 'April',
  },
  nordvik: {
    email: 'nordvik.to@transmuter-e2e.dev',
    currency: 'EUR',
    fiscalMonth: 1,
    fiscalLabel: 'January',
  },
  cascade: {
    email: 'cascade.to@transmuter-e2e.dev',
    currency: 'AUD',
    fiscalMonth: 7,
    fiscalLabel: 'July',
  },
  verdant: {
    email: 'verdant.to@transmuter-e2e.dev',
    currency: 'BRL',
    fiscalMonth: 1,
    fiscalLabel: 'January',
  },
  helios: {
    email: 'helios.to@transmuter-e2e.dev',
    currency: 'USD',
    fiscalMonth: 10,
    fiscalLabel: 'October',
  },
  meridian: {
    email: 'meridian.to@transmuter-e2e.dev',
    currency: 'SGD',
    fiscalMonth: 1,
    fiscalLabel: 'January',
  },
  stellar: {
    email: 'stellar.to@transmuter-e2e.dev',
    currency: 'USD',
    fiscalMonth: 1,
    fiscalLabel: 'January',
  },
};

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function waitFor(fn, label, timeoutMs = 30_000) {
  const start = Date.now();
  let lastError;
  while (Date.now() - start < timeoutMs) {
    try {
      const value = await fn();
      if (value) return value;
    } catch (error) {
      lastError = error;
    }
    await sleep(250);
  }
  throw new Error(`Timed out waiting for ${label}${lastError ? `: ${lastError.message}` : ''}`);
}

async function requestJson(url, init = {}) {
  const response = await fetch(url, init);
  const text = response.status === 204 ? '' : await response.text();
  assert(response.ok, `${url} returned ${response.status}: ${text.slice(0, 1000)}`);
  return text ? JSON.parse(text) : null;
}

async function connectToPage(wsUrl) {
  const socket = new WebSocket(wsUrl);
  let nextId = 1;
  const pending = new Map();
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (message.method === 'Page.javascriptDialogOpening') {
      socket.send(JSON.stringify({ id: nextId++, method: 'Page.handleJavaScriptDialog', params: { accept: true } }));
      return;
    }
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
  const result = await page.send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.exception?.description ?? result.exceptionDetails.text ?? 'Browser evaluation failed');
  }
  return result.result.value;
}

async function browserFetch(page, path, options = {}) {
  return evalJs(page, `
    (async () => {
      const token = localStorage.getItem('access_token');
      const response = await fetch(${JSON.stringify(`${apiBaseUrl}${path}`)}, {
        method: ${JSON.stringify(options.method ?? 'GET')},
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: 'Bearer ' + token } : {}),
          ...${JSON.stringify(options.headers ?? {})}
        },
        body: ${options.body === undefined ? 'undefined' : JSON.stringify(JSON.stringify(options.body))},
      });
      const text = response.status === 204 ? '' : await response.text();
      if (!response.ok) throw new Error(${JSON.stringify(path)} + ' returned ' + response.status + ': ' + text.slice(0, 1000));
      return text ? JSON.parse(text) : null;
    })()
  `);
}

async function navigate(page, path) {
  const url = path.startsWith('http') ? path : `${uiBaseUrl}${path}`;
  await page.send('Page.navigate', { url });
}

async function login(page, tenant) {
  await navigate(page, '/auth/login');
  await waitFor(() => evalJs(page, "document.querySelector('input[name=email]') !== null"), 'login form');
  await evalJs(page, 'localStorage.clear(); sessionStorage.clear(); true');
  await setField(page, 'input[name=email]', tenant.email);
  await setField(page, 'input[name=password]', password);
  await clickFirst(page, 'button[type=submit]');
  await waitFor(
    () => evalJs(page, "!!localStorage.getItem('access_token') && !location.pathname.includes('/auth/login')"),
    `authenticated session for ${tenant.email}`,
    45_000,
  );
}

async function setField(page, selector, value) {
  await evalJs(page, `
    (() => {
      const el = document.querySelector(${JSON.stringify(selector)});
      if (!el) throw new Error('Missing field: ' + ${JSON.stringify(selector)});
      el.focus();
      el.value = ${JSON.stringify(String(value))};
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    })()
  `);
}

async function setTextareaByName(page, name, value) {
  await setField(page, `textarea[name="${name}"]`, value);
}

async function setSelectValue(page, selector, value) {
  await evalJs(page, `
    (() => {
      const select = document.querySelector(${JSON.stringify(selector)});
      if (!select) throw new Error('Missing select: ' + ${JSON.stringify(selector)});
      const option = [...select.options].find(item => item.value === ${JSON.stringify(String(value))});
      if (!option) throw new Error('Missing option value ' + ${JSON.stringify(String(value))} + ' in ' + ${JSON.stringify(selector)});
      select.value = option.value;
      select.dispatchEvent(new Event('input', { bubbles: true }));
      select.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    })()
  `);
}

async function selectByOptionText(page, selector, text) {
  await evalJs(page, `
    (() => {
      const select = document.querySelector(${JSON.stringify(selector)});
      if (!select) throw new Error('Missing select: ' + ${JSON.stringify(selector)});
      const needle = ${JSON.stringify(text)}.toLowerCase();
      const option = [...select.options].find(item => item.textContent.trim().toLowerCase().includes(needle));
      if (!option) throw new Error('Missing option text ' + needle + ' in ' + ${JSON.stringify(selector)});
      select.value = option.value;
      select.dispatchEvent(new Event('input', { bubbles: true }));
      select.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    })()
  `);
}

async function setCheckbox(page, selector, checked) {
  await evalJs(page, `
    (() => {
      const input = document.querySelector(${JSON.stringify(selector)});
      if (!input) throw new Error('Missing checkbox: ' + ${JSON.stringify(selector)});
      if (Boolean(input.checked) !== ${JSON.stringify(Boolean(checked))}) input.click();
      input.dispatchEvent(new Event('change', { bubbles: true }));
      return input.checked;
    })()
  `);
}

async function clickFirst(page, selector) {
  await evalJs(page, `
    (() => {
      const el = document.querySelector(${JSON.stringify(selector)});
      if (!el) throw new Error('Missing clickable selector: ' + ${JSON.stringify(selector)});
      el.click();
      return true;
    })()
  `);
}

async function clickButtonText(page, text) {
  await evalJs(page, `
    (() => {
      const needle = ${JSON.stringify(text)}.toLowerCase();
      const button = [...document.querySelectorAll('button')]
        .filter(item => !item.disabled)
        .find(item => item.textContent.trim().toLowerCase().includes(needle));
      if (!button) throw new Error('Missing enabled button text: ' + needle);
      button.click();
      return true;
    })()
  `);
}

async function clickTab(page, text) {
  await evalJs(page, `
    (() => {
      const detailNav = [...document.querySelectorAll('nav')]
        .find(nav => ['Overview', 'Financials', 'Milestones', 'Status', 'Summary']
          .every(label => [...nav.querySelectorAll('button')].some(item => item.textContent.trim() === label)));
      if (!detailNav) throw new Error('Missing initiative detail tab navigation');
      const button = [...detailNav.querySelectorAll('button')]
        .find(item => item.textContent.trim() === ${JSON.stringify(text)});
      if (!button) throw new Error('Missing tab: ' + ${JSON.stringify(text)});
      button.click();
      return true;
    })()
  `);
}

async function clickFinancialsView(page, view) {
  const selector = view === 'validation' ? '[data-testid="financials-view-validation"]' : '[data-testid="financials-view-entry"]';
  await waitFor(() => evalJs(page, `document.querySelector(${JSON.stringify(selector)}) !== null`), `financials ${view} view tab`);
  await evalJs(page, `
    (() => {
      const button = document.querySelector(${JSON.stringify(selector)});
      if (!button) throw new Error('Missing financials view tab: ' + ${JSON.stringify(view)});
      button.click();
      return true;
    })()
  `);
  await waitFor(() => evalJs(page, `
    document.querySelector(${JSON.stringify(selector)})?.getAttribute('aria-selected') === 'true'
  `), `financials ${view} view selected`);
}

async function openAdminTab(page, tab) {
  await navigate(page, '/admin');
  await waitFor(() => evalJs(page, "document.body.innerText.includes('Control Center')"), 'admin page');
  await evalJs(page, `
    (() => {
      const button = [...document.querySelectorAll('button')]
        .find(item => item.getAttribute('aria-label') === ${JSON.stringify(`Open ${tab} admin tab`)});
      if (!button) throw new Error('Missing admin tab: ' + ${JSON.stringify(tab)});
      button.click();
      return true;
    })()
  `);
}

async function saveReportingSettingsViaUi(page, settings) {
  await openAdminTab(page, 'Financial Configuration');
  await waitFor(() => evalJs(page, "document.querySelector('input[aria-label=\"Reporting currency\"]') !== null"), 'reporting controls');
  await setField(page, 'input[aria-label="Reporting currency"]', settings.currency);
  await selectByOptionText(page, 'select[aria-label="Fiscal year start month"]', settings.fiscalLabel);
  if (settings.inflationMode) {
    await setSelectValue(page, 'select[aria-label="Recurring cost inflation mode"]', settings.inflationMode);
  }
  if (settings.defaultInflationRate !== undefined) {
    await setField(page, 'input[aria-label="Default annual recurring cost inflation percent"]', settings.defaultInflationRate);
  }
  if (settings.allowOverride !== undefined) {
    await setCheckbox(page, 'input[aria-label="Allow cost line inflation override"]', settings.allowOverride);
  }
  await clickFirst(page, 'button[aria-label="Save reporting settings"]');
  await waitFor(async () => {
    const config = await browserFetch(page, '/financial-engine-configuration');
    const actual = config.settings;
    return actual.reporting_currency === settings.currency
      && Number(actual.fiscal_year_start_month) === Number(settings.fiscalMonth)
      && (!settings.inflationMode || actual.recurring_cost_inflation_mode === settings.inflationMode)
      && (settings.defaultInflationRate === undefined || Number(actual.default_annual_inflation_rate_pct) === Number(settings.defaultInflationRate))
      && (settings.allowOverride === undefined || Boolean(actual.allow_cost_line_inflation_override) === Boolean(settings.allowOverride));
  }, `persisted reporting settings for ${settings.currency}/${settings.fiscalLabel}`, 45_000);

  await navigate(page, '/admin');
  await openAdminTab(page, 'Financial Configuration');
  await waitFor(() => evalJs(page, `
    (() => document.querySelector('input[aria-label="Reporting currency"]')?.value === ${JSON.stringify(settings.currency)}
      && (document.querySelector('select[aria-label="Fiscal year start month"]')?.selectedOptions?.[0]?.textContent || '').includes(${JSON.stringify(settings.fiscalLabel)}))()
  `), `admin UI reloaded reporting settings ${settings.currency}/${settings.fiscalLabel}`, 45_000);
  const uiValues = await evalJs(page, `
    (() => ({
      currency: document.querySelector('input[aria-label="Reporting currency"]')?.value,
      fiscalText: document.querySelector('select[aria-label="Fiscal year start month"]')?.selectedOptions?.[0]?.textContent.trim(),
      inflationMode: document.querySelector('select[aria-label="Recurring cost inflation mode"]')?.value,
      defaultInflationRate: document.querySelector('input[aria-label="Default annual recurring cost inflation percent"]')?.value,
      allowOverride: document.querySelector('input[aria-label="Allow cost line inflation override"]')?.checked,
    }))()
  `);
  assert(uiValues.currency === settings.currency, `UI currency reverted: expected ${settings.currency}, got ${uiValues.currency}`);
  assert(uiValues.fiscalText.includes(settings.fiscalLabel), `UI fiscal start reverted: expected ${settings.fiscalLabel}, got ${uiValues.fiscalText}`);
  return uiValues;
}

async function findInitiative(page, nameNeedle) {
  const list = await browserFetch(page, '/initiatives?page_size=200&sort_by=initiative_code');
  const needle = nameNeedle.toLowerCase();
  const initiative = (list.items ?? []).find(item =>
    String(item.name ?? '').toLowerCase().includes(needle)
    || String(item.initiative_code ?? '').toLowerCase().includes(needle)
  );
  assert(initiative, `Missing initiative matching ${nameNeedle}; available=${(list.items ?? []).map(item => item.name).join(' | ')}`);
  return initiative;
}

async function visibleBenefitCards(page) {
  return evalJs(page, `
    (() => [...document.querySelectorAll('button[aria-label="Update benefit line risk"]')]
      .map(button => {
        const card = button.parentElement?.parentElement;
        return {
          text: card?.innerText || '',
          buttons: [...(card?.querySelectorAll('button') || [])].map(item => item.textContent.trim()).filter(Boolean),
        };
      }))()
  `);
}

async function validateBenefitButtonStates(page) {
  const initiative = await findInitiative(page, 'Accounting System Implementation');
  await navigate(page, `/initiatives/${initiative.id}`);
  await waitFor(() => evalJs(page, "document.body.innerText.includes('Accounting System Implementation')"), 'Pinnacle initiative detail');
  await clickTab(page, 'Financials');
  await waitFor(() => evalJs(page, "document.querySelector('[data-testid=\"financials-view-entry\"]')?.getAttribute('aria-selected') === 'true'"), 'financials entry view');
  const entryControlsHidden = await evalJs(page, `
    document.querySelector('button[aria-label="Update benefit line risk"]') === null
      && document.querySelector('[data-testid="financial-validation-panel"]') === null
  `);
  assert(entryControlsHidden, 'Finance validation controls should not be visible in the Entry view');
  await clickFinancialsView(page, 'validation');
  await waitFor(() => evalJs(page, "document.querySelector('[data-testid=\"financial-validation-panel\"]') !== null"), 'finance validation section');
  const cards = await visibleBenefitCards(page);
  assert(cards.length >= 1, 'Expected visible benefit-line finance validation cards');
  const validated = cards.filter(card => card.text.toLowerCase().includes('finance validated'));
  const submitted = cards.filter(card => card.text.toLowerCase().includes('submitted to finance'));
  assert(validated.length > 0, `Expected at least one finance-validated PIN-001 card: ${JSON.stringify(cards)}`);
  assert(submitted.length > 0, `Expected at least one submitted PIN-001 card: ${JSON.stringify(cards)}`);
  assert(validated.every(card => JSON.stringify(card.buttons.map(item => item.toLowerCase())) === JSON.stringify(['risk'])), `Finance-validated cards exposed wrong buttons: ${JSON.stringify(validated)}`);
  assert(submitted.every(card => {
    const buttons = card.buttons.map(item => item.toLowerCase()).join('|');
    return buttons.includes('validate') && buttons.includes('reject') && buttons.includes('risk')
      && !buttons.includes('submit') && !buttons.includes('delete');
  }), `Submitted cards exposed wrong buttons: ${JSON.stringify(submitted)}`);
  return { cards: cards.length, validated: validated.length, submitted: submitted.length };
}

async function validatePinnacleFinancialGridScenarioRows(page) {
  const initiative = await findInitiative(page, 'CoSec Workflow Automation');
  await navigate(page, `/initiatives/${initiative.id}`);
  await waitFor(() => evalJs(page, "document.body.innerText.includes('CoSec Workflow Automation')"), 'Pinnacle PIN-002 initiative detail');
  await clickTab(page, 'Financials');
  await waitFor(() => evalJs(page, "document.body.innerText.includes('Initiative Financials')"), 'initiative financials grid');

  const grid = await browserFetch(page, `/initiatives/${initiative.id}/financials`);
  const costSavings = (grid.definitions ?? []).find(item => item.key === 'cost_savings');
  const base = scenarioByKind(grid.scenarios ?? [], 'plan', ['plan_base', 'base']);
  const high = scenarioByKind(grid.scenarios ?? [], 'plan', ['plan_high', 'high']);
  const actual = scenarioByKind(grid.scenarios ?? [], 'actual', ['actual']);
  assert(costSavings && base && high && actual, 'Missing PIN-002 cost savings metric/scenario definitions');
  const valueFor = scenario => (grid.values ?? [])
    .filter(item => item.metric_definition_id === costSavings.id && item.scenario_id === scenario.id)
    .reduce((sum, item) => sum + Number(item.value || 0), 0);
  assert(valueFor(base) === 3_600_000, `Expected PIN-002 base savings 3.6M, got ${valueFor(base)}`);
  assert(valueFor(high) === 4_500_000, `Expected PIN-002 high savings 4.5M, got ${valueFor(high)}`);

  const gridLabels = [
    `Cost Savings (${base.label})`,
    `Cost Savings (${high.label})`,
    `Cost Savings (${actual.label})`,
    'Recurring Costs (Plan)',
    'Recurring Costs (Actual)',
    'One-off Costs (Plan)',
    'One-off Costs (Actual)',
  ];
  const labelPresence = () => evalJs(page, `
    (async () => {
      const labels = ${JSON.stringify(gridLabels)};
      const found = Object.fromEntries(labels.map(label => [label, false]));
      const container = document.querySelector('.handsontable-container');
      const holder = container?.querySelector('.wtHolder') || container;
      if (!container || !holder) return labels.map(label => [label, false]);
      const maxScroll = Math.max(holder.scrollHeight - holder.clientHeight, 0);
      const step = Math.max(Math.floor(holder.clientHeight * 0.75), 160);
      for (let top = 0; top <= maxScroll + step; top += step) {
        holder.scrollTop = Math.min(top, maxScroll);
        holder.dispatchEvent(new Event('scroll', { bubbles: true }));
        await new Promise(resolve => setTimeout(resolve, 80));
        const text = container.innerText || '';
        for (const label of labels) {
          if (text.includes(label)) found[label] = true;
        }
        if (labels.every(label => found[label])) break;
      }
      holder.scrollTop = 0;
      holder.dispatchEvent(new Event('scroll', { bubbles: true }));
      return labels.map(label => [label, found[label]]);
    })()
  `);
  const missingLabels = presence => presence.filter(([, present]) => !present).map(([label]) => label);
  await waitFor(async () => missingLabels(await labelPresence()).length === 0, 'all financial scenario and cost grid labels');
  const beforePresence = await labelPresence();

  const clickCardScenario = label => evalJs(page, `
    (() => {
      const root = document.querySelector('[data-testid="financial-scenario-toggle"]');
      if (!root) throw new Error('Missing financial card scenario toggle');
      const button = [...root.querySelectorAll('button')]
        .find(item => item.textContent.trim() === ${JSON.stringify(label)});
      if (!button) throw new Error('Missing card scenario button: ' + ${JSON.stringify(label)});
      button.click();
      return true;
    })()
  `);
  await clickCardScenario('High');
  await waitFor(() => evalJs(page, `
    (() => [...document.querySelectorAll('[data-testid="financial-scenario-toggle"] button')]
      .some(button => button.textContent.trim() === 'High' && button.getAttribute('aria-pressed') === 'true'))()
  `), 'High card scenario selected');
  const highPresence = await labelPresence();
  await clickCardScenario('Actuals');
  await waitFor(() => evalJs(page, `
    (() => [...document.querySelectorAll('[data-testid="financial-scenario-toggle"] button')]
      .some(button => button.textContent.trim() === 'Actuals' && button.getAttribute('aria-pressed') === 'true'))()
  `), 'Actuals card scenario selected');
  const actualPresence = await labelPresence();
  assert(missingLabels(highPresence).length === 0, `Grid labels missing after High card toggle: ${missingLabels(highPresence).join(', ')}`);
  assert(missingLabels(actualPresence).length === 0, `Grid labels missing after Actuals card toggle: ${missingLabels(actualPresence).join(', ')}`);

  return {
    initiative: initiative.name,
    baseSavings: valueFor(base),
    highSavings: valueFor(high),
    labels: gridLabels,
  };
}

async function rejectSubmittedBenefitWithReasonAndRestore(page) {
  const initiative = await findInitiative(page, 'AI Customer Support Automation');
  await navigate(page, `/initiatives/${initiative.id}`);
  await waitFor(() => evalJs(page, "document.body.innerText.includes('AI Customer Support Automation')"), 'Stellar initiative detail');
  await clickTab(page, 'Financials');
  await clickFinancialsView(page, 'validation');
  await waitFor(() => evalJs(page, "document.querySelector('[data-testid=\"financial-validation-panel\"]') !== null"), 'Stellar finance validation section');
  let before = await browserFetch(page, `/initiatives/${initiative.id}/financials`);
  for (const stale of (before.benefit_lines ?? []).filter(item =>
    item.validation_status === 'rejected'
    && String(item.rejection_reason ?? '').startsWith('Browser validation rejection reason')
  )) {
    await browserFetch(page, `/initiatives/${initiative.id}/financials/benefit-lines/${stale.id}/submit`, {
      method: 'POST',
      body: { comment: 'Restored stale browser validation line before rerun.' },
    }).catch(() => null);
  }
  before = await browserFetch(page, `/initiatives/${initiative.id}/financials`);
  const line = (before.benefit_lines ?? []).find(item => item.validation_status === 'submitted');
  assert(line, 'Expected a submitted Stellar benefit line to validate rejection reason UI');
  await evalJs(page, `
    (() => {
      const cards = [...document.querySelectorAll('button[aria-label="Update benefit line risk"]')]
        .map(button => button.parentElement?.parentElement)
        .filter(Boolean);
      const card = cards.find(item => item.innerText.toLowerCase().includes('submitted to finance'));
      if (!card) throw new Error('Missing submitted benefit card');
      const reject = [...card.querySelectorAll('button')].find(item => item.textContent.trim() === 'Reject' && !item.disabled);
      if (!reject) throw new Error('Missing Reject button on submitted card');
      reject.click();
      return true;
    })()
  `);
  await waitFor(() => evalJs(page, "document.body.innerText.toLowerCase().includes('rejection reason')"), 'inline rejection reason panel');
  const reason = `Browser validation rejection reason ${Date.now()}`;
  await setField(page, 'textarea[aria-label="Benefit validation comment"]', reason);
  await clickFirst(page, 'button[aria-label="Confirm benefit validation action"]');
  await waitFor(async () => {
    const grid = await browserFetch(page, `/initiatives/${initiative.id}/financials`);
    const updated = (grid.benefit_lines ?? []).find(item => item.id === line.id);
    return updated?.validation_status === 'rejected' && updated?.rejection_reason === reason;
  }, 'benefit line rejected with reason');

  await browserFetch(page, `/initiatives/${initiative.id}/financials/benefit-lines/${line.id}/submit`, {
    method: 'POST',
    body: { comment: 'Restored to submitted after browser validation.' },
  });
  await waitFor(async () => {
    const grid = await browserFetch(page, `/initiatives/${initiative.id}/financials`);
    const restored = (grid.benefit_lines ?? []).find(item => item.id === line.id);
    return restored?.validation_status === 'submitted';
  }, 'benefit line restored to submitted');
  return { initiative: initiative.name, line: line.name, rejectedWithReason: true, restoredTo: 'submitted' };
}

async function validateStatusRagPropagation(page) {
  const initiative = await findInitiative(page, 'Revenue Cycle Remediation');
  await navigate(page, `/initiatives/${initiative.id}`);
  await waitFor(() => evalJs(page, "document.body.innerText.includes('Revenue Cycle Remediation')"), 'Helios initiative detail');
  await clickTab(page, 'Status');
  await waitFor(() => evalJs(page, "document.body.innerText.includes('Status Heartbeat')"), 'status heartbeat tab');
  const isEditing = await evalJs(page, "document.body.innerText.includes('New Status Report') || document.body.innerText.includes('Edit Draft Update')");
  if (!isEditing) await clickButtonText(page, 'Create Update');
  await waitFor(() => evalJs(page, "document.querySelector('textarea[name=status_summary]') !== null"), 'status update form');
  await evalJs(page, `
    (() => {
      const red = [...document.querySelectorAll('button')].find(item => item.textContent.trim().toLowerCase() === 'red');
      if (!red) throw new Error('Missing RED RAG button');
      red.click();
      return true;
    })()
  `);
  const stamp = Date.now();
  await setTextareaByName(page, 'status_summary', `Browser validation red status propagation ${stamp}.`);
  await setTextareaByName(page, 'status_issues', 'Validation issue requires executive attention.');
  await setTextareaByName(page, 'status_next_steps', 'Confirm dashboard RAG propagation.');
  await clickButtonText(page, 'Submit Final Report');
  await waitFor(async () => {
    const detail = await browserFetch(page, `/initiatives/${initiative.id}`);
    return detail.rag_status === 'red';
  }, 'initiative headline RAG propagated to red', 45_000);
  const detail = await browserFetch(page, `/initiatives/${initiative.id}`);
  return { initiative: initiative.name, rag_status: detail.rag_status };
}

async function validateMilestonePressure(page) {
  const initiative = await findInitiative(page, 'Supply Chain Control Tower');
  await navigate(page, `/initiatives/${initiative.id}`);
  await waitFor(() => evalJs(page, "document.body.innerText.includes('Supply Chain Control Tower')"), 'Meridian overview');
  const detail = await browserFetch(page, `/initiatives/${initiative.id}`);
  const milestoneHealth = Number(detail.pressure_breakdown?.milestone_health ?? 0);
  assert(Number(detail.counts?.milestones_overdue ?? 0) > 0, `Expected past-due incomplete milestones to count overdue: ${JSON.stringify(detail.counts)}`);
  assert(milestoneHealth > 0, `Expected milestone pressure > 0, got ${JSON.stringify(detail.pressure_breakdown)}`);
  return {
    initiative: initiative.name,
    milestones_overdue: detail.counts.milestones_overdue,
    milestone_health: detail.pressure_breakdown.milestone_health,
  };
}

function scenarioByKind(scenarios, kind, keyIncludes = []) {
  return scenarios.find(item => keyIncludes.includes(item.key))
    || scenarios.find(item => item.kind === kind && (kind !== 'plan' || item.is_primary))
    || scenarios.find(item => item.kind === kind);
}

async function validateSingleBenefitLineScenarioEntry(page) {
  const initiative = await findInitiative(page, 'Pricing & Markdown Optimisation');
  await navigate(page, `/initiatives/${initiative.id}`);
  await waitFor(() => evalJs(page, "document.body.innerText.includes('Pricing & Markdown Optimisation')"), 'Aurelia initiative detail');
  await clickTab(page, 'Financials');
  await waitFor(() => evalJs(page, "document.body.innerText.toLowerCase().includes('benefit metric')"), 'benefit line entry form');
  const labelsPresent = await evalJs(page, `
    (() => ['base', 'high', 'actual'].every(label => document.body.innerText.toLowerCase().includes(label)))()
  `);
  assert(labelsPresent, 'Expected Base, High, and Actual amount controls in the benefit-line add form');

  const grid = await browserFetch(page, `/initiatives/${initiative.id}/financials`);
  const metric = (grid.definitions ?? [])[0];
  const base = scenarioByKind(grid.scenarios ?? [], 'plan', ['plan_base', 'base']);
  const high = scenarioByKind(grid.scenarios ?? [], 'plan', ['plan_high', 'high']);
  const actual = scenarioByKind(grid.scenarios ?? [], 'actual', ['actual']);
  assert(metric && base && high && actual, 'Missing metric/scenario definitions for benefit-line validation');
  const lineName = `Browser validation one-line benefit ${Date.now()}`;
  const line = await browserFetch(page, `/initiatives/${initiative.id}/financials/benefit-lines`, {
    method: 'POST',
    body: {
      metric_definition_id: metric.id,
      name: lineName,
      description: 'Temporary browser validation line for base/high/actual one-line entry.',
      impact_type: 'recurring',
      timing: null,
      confidence: '95',
      phasing: { mode: 'manual' },
      attributes: {},
      show_in_summary: true,
      display_order: 9999,
    },
  });
  try {
    await browserFetch(page, `/initiatives/${initiative.id}/financials`, {
      method: 'PUT',
      body: {
        values: [
          { metric_definition_id: metric.id, scenario_id: base.id, benefit_line_id: line.id, year: 2026, month: 1, value: '1.0000', status: 'draft' },
          { metric_definition_id: metric.id, scenario_id: high.id, benefit_line_id: line.id, year: 2026, month: 1, value: '2.0000', status: 'draft' },
          { metric_definition_id: metric.id, scenario_id: actual.id, benefit_line_id: line.id, year: 2026, month: 1, value: '0.5000', status: 'draft' },
        ],
      },
    });
    const after = await browserFetch(page, `/initiatives/${initiative.id}/financials`);
    const matchingLines = (after.benefit_lines ?? []).filter(item => item.name === lineName);
    const values = (after.values ?? []).filter(item => item.benefit_line_id === line.id);
    assert(matchingLines.length === 1, `Expected exactly one benefit line, got ${matchingLines.length}`);
    assert(values.length === 3, `Expected base/high/actual values on one line, got ${values.length}`);
    return { initiative: initiative.name, oneLine: true, values: values.length };
  } finally {
    await browserFetch(page, `/initiatives/${initiative.id}/financials/benefit-lines/${line.id}`, { method: 'DELETE' }).catch(() => null);
  }
}

async function validateRecurringCostInflation(page) {
  const initiative = await findInitiative(page, 'Digital Twin / Throughput');
  await navigate(page, `/initiatives/${initiative.id}`);
  await waitFor(() => evalJs(page, "document.body.innerText.includes('Digital Twin / Throughput')"), 'Nordvik initiative detail');
  await clickTab(page, 'Financials');
  try {
    await waitFor(() => evalJs(page, "document.querySelector('select[aria-label=\"Cost line category\"]') !== null"), 'cost line entry form');
  } catch (error) {
    const state = await evalJs(page, `
      (() => ({
        path: location.pathname,
        navButtons: [...document.querySelectorAll('nav button')].map(item => item.textContent.trim()),
        text: document.body.innerText.slice(0, 3000),
      }))()
    `);
    throw new Error(`${error.message}; browser state=${JSON.stringify(state)}`);
  }
  const controlsVisible = await waitFor(() => evalJs(page, `
    (() => {
      const text = document.body.innerText.toLowerCase();
      return text.includes('inflate') && text.includes('infl. %');
    })()
  `), 'recurring-cost inflation controls');
  assert(controlsVisible, 'Expected recurring-cost inflation controls in Financials tab');

  const name = `Browser validation inflation ${Date.now()}`;
  await browserFetch(page, `/initiatives/${initiative.id}/financials`, {
    method: 'PUT',
    body: {
      cost_lines: [
        { name, category_key: 'software', year: 2026, month: 1, amount_plan: '100.0000', amount_actual: null, is_recurring: true, inflation_enabled: true, annual_inflation_rate_pct: '3.0000' },
        { name, category_key: 'software', year: 2027, month: 1, amount_plan: '100.0000', amount_actual: null, is_recurring: true, inflation_enabled: true, annual_inflation_rate_pct: '3.0000' },
      ],
    },
  });
  try {
    const lines = await browserFetch(page, `/initiatives/${initiative.id}/financials/cost-lines`);
    const matching = (lines.items ?? []).filter(item => item.name === name).sort((a, b) => a.year - b.year);
    assert(matching.length === 2, `Expected two validation cost lines, got ${matching.length}`);
    assert(matching[0].amount_plan === '100.0000', `Expected first year 100.0000, got ${matching[0].amount_plan}`);
    assert(matching[1].amount_plan === '103.0000', `Expected second year 103.0000, got ${matching[1].amount_plan}`);
    assert(matching.every(item => item.inflation_enabled && item.annual_inflation_rate_pct === '3.0000'), `Inflation metadata missing: ${JSON.stringify(matching)}`);
    return { initiative: initiative.name, firstYear: matching[0].amount_plan, secondYear: matching[1].amount_plan };
  } finally {
    const lines = await browserFetch(page, `/initiatives/${initiative.id}/financials/cost-lines`).catch(() => ({ items: [] }));
    for (const line of (lines.items ?? []).filter(item => item.name === name)) {
      await browserFetch(page, `/initiatives/${initiative.id}/financials/cost-lines/${line.id}`, { method: 'DELETE' }).catch(() => null);
    }
  }
}

async function validateRapidWorkstreamAdd(page) {
  await openAdminTab(page, 'Strategic Parameters');
  await waitFor(() => evalJs(page, "document.querySelector('input[aria-label=\"New workstream name\"]') !== null"), 'new workstream input');
  const name = `Browser Validation ${Date.now()}`;
  const before = await browserFetch(page, '/workstreams');
  await setField(page, 'input[aria-label="New workstream name"]', name);
  await evalJs(page, `
    (() => {
      const button = document.querySelector('button[aria-label="Create workstream"]');
      if (!button) throw new Error('Missing Create workstream button');
      button.click();
      button.click();
      return true;
    })()
  `);
  await waitFor(async () => {
    const rows = await browserFetch(page, '/workstreams');
    return (rows.items ?? rows.data ?? []).some(item => item.name === name);
  }, 'workstream created once');
  const after = await browserFetch(page, '/workstreams');
  const matches = (after.items ?? after.data ?? []).filter(item => item.name === name);
  assert(matches.length === 1, `Expected one workstream after rapid double-click, got ${matches.length}`);
  const messageVisible = await evalJs(page, "document.body.innerText.includes('Workstream saved.')");
  assert(messageVisible, 'Expected workstream save feedback message');
  await browserFetch(page, `/workstreams/${matches[0].id}`, { method: 'DELETE' });
  const cleaned = await browserFetch(page, '/workstreams');
  assert(!(cleaned.items ?? cleaned.data ?? []).some(item => item.name === name), 'Validation workstream cleanup failed');
  return { before: (before.items ?? before.data ?? []).length, addedOnce: true, cleanedUp: true };
}

async function validateCrossTenantIsolation(page, sourceTenant, targetTenant, targetInitiativeName) {
  const sourceToken = await evalJs(page, "localStorage.getItem('access_token')");
  assert(sourceToken, `Missing active source token for ${sourceTenant.email}`);
  await login(page, targetTenant);
  const targetInitiative = await findInitiative(page, targetInitiativeName);
  const result = await evalJs(page, `
    (async () => {
      const response = await fetch(${JSON.stringify(`${apiBaseUrl}/initiatives/${targetInitiative.id}`)}, {
        headers: { Authorization: 'Bearer ' + ${JSON.stringify(sourceToken)} },
      });
      return { status: response.status, text: await response.text() };
    })()
  `);
  assert(result.status === 404, `Expected cross-tenant initiative access to return 404, got ${result.status}: ${result.text.slice(0, 500)}`);
  return { source: sourceTenant.email, targetInitiative: targetInitiative.name, status: result.status };
}

async function main() {
  assert(password, 'TRANSMUTER_E2E_PASSWORD is required');
  await requestJson(`${apiBaseUrl}/health`);
  const userDataDir = await mkdtemp(`${tmpdir()}/transmuter-runbook-remediation-`);
  const chrome = spawn(chromeBin, [
    '--headless=new',
    '--no-sandbox',
    `--remote-debugging-port=${debugPort}`,
    `--user-data-dir=${userDataDir}`,
    '--no-first-run',
    '--no-default-browser-check',
    'about:blank',
  ], { stdio: ['ignore', 'ignore', 'pipe'] });
  chrome.stderr.on('data', chunk => {
    const text = chunk.toString();
    if (!text.includes('DevTools listening')) process.stderr.write(text);
  });

  let page;
  const results = {};
  try {
    await waitFor(() => fetch(`http://127.0.0.1:${debugPort}/json/version`).then(response => response.ok), 'Chrome DevTools endpoint');
    const target = await requestJson(`http://127.0.0.1:${debugPort}/json/new?${encodeURIComponent('about:blank')}`, { method: 'PUT' });
    page = await connectToPage(target.webSocketDebuggerUrl);
    await page.send('Runtime.enable');
    await page.send('Page.enable');
    await page.send('DOM.enable');
    await page.send('Page.addScriptToEvaluateOnNewDocument', {
      source: "window.alert = message => console.log('[alert]', message); window.confirm = () => true;",
    });

    if (process.env.TRANSMUTER_RUNBOOK_SECTION === 'inflation') {
      await login(page, tenants.nordvik);
      results.inflationAdmin = await saveReportingSettingsViaUi(page, {
        ...tenants.nordvik,
        inflationMode: 'optional_per_line',
        defaultInflationRate: '3',
        allowOverride: true,
      });
      results.recurringCostInflation = await validateRecurringCostInflation(page);
      console.log(JSON.stringify({ status: 'passed', results }, null, 2));
      return;
    }

    if (process.env.TRANSMUTER_RUNBOOK_SECTION === 'benefit-validation') {
      await login(page, tenants.pinnacle);
      results.benefitButtonStates = await validateBenefitButtonStates(page);
      await login(page, tenants.stellar);
      results.rejectionReason = await rejectSubmittedBenefitWithReasonAndRestore(page);
      console.log(JSON.stringify({ status: 'passed', results }, null, 2));
      return;
    }

    if (process.env.TRANSMUTER_RUNBOOK_SECTION === 'financial-grid') {
      await login(page, tenants.pinnacle);
      results.pinnacleFinancialGrid = await validatePinnacleFinancialGridScenarioRows(page);
      console.log(JSON.stringify({ status: 'passed', results }, null, 2));
      return;
    }

    results.reportingSettings = {};
    for (const [slug, tenant] of Object.entries(tenants)) {
      await login(page, tenant);
      const settings = await saveReportingSettingsViaUi(page, tenant);
      results.reportingSettings[slug] = {
        currency: settings.currency,
        fiscalStart: settings.fiscalText,
      };
      await sleep(500);
    }

    await login(page, tenants.nordvik);
    results.inflationAdmin = await saveReportingSettingsViaUi(page, {
      ...tenants.nordvik,
      inflationMode: 'optional_per_line',
      defaultInflationRate: '3',
      allowOverride: true,
    });
    results.recurringCostInflation = await validateRecurringCostInflation(page);

    await login(page, tenants.pinnacle);
    results.benefitButtonStates = await validateBenefitButtonStates(page);
    results.pinnacleFinancialGrid = await validatePinnacleFinancialGridScenarioRows(page);
    results.rapidWorkstreamAdd = await validateRapidWorkstreamAdd(page);

    await login(page, tenants.stellar);
    results.rejectionReason = await rejectSubmittedBenefitWithReasonAndRestore(page);

    await login(page, tenants.helios);
    results.ragPropagation = await validateStatusRagPropagation(page);

    await login(page, tenants.meridian);
    results.milestonePressure = await validateMilestonePressure(page);

    await login(page, tenants.aurelia);
    results.singleBenefitLineScenarioEntry = await validateSingleBenefitLineScenarioEntry(page);

    results.crossTenantIsolation = await validateCrossTenantIsolation(
      page,
      tenants.aurelia,
      tenants.pinnacle,
      'Accounting System Implementation',
    );

    console.log(JSON.stringify({ status: 'passed', results }, null, 2));
  } finally {
    page?.close();
    chrome.kill('SIGTERM');
    await rm(userDataDir, { recursive: true, force: true });
  }
}

main().catch(error => {
  console.error(error);
  process.exit(1);
});
