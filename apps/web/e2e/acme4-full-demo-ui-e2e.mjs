import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { resolve } from 'node:path';
import { spawn } from 'node:child_process';

const uiBaseUrl = process.env.TRANSMUTER_UI_BASE_URL ?? 'https://transmuter-dev.ishirock.tech';
const apiBaseUrl = process.env.TRANSMUTER_API_BASE_URL ?? `${uiBaseUrl}/api`;
const chromeBin = process.env.CHROME_BIN ?? '/snap/bin/chromium';
const email = process.env.TRANSMUTER_E2E_EMAIL ?? 'admin@acme4-transformation.dev';
const password = process.env.TRANSMUTER_E2E_PASSWORD;
const debugPort = Number(process.env.CHROME_DEBUG_PORT ?? 9244);
const ledgerCsvPath = resolve(process.env.ACME_LEDGER_CSV ?? 'docs/user-guides/acme-benefit-ledger-import.csv');
const canonicalCodes = Array.from({ length: 10 }, (_, index) => `ENT-${String(index + 1).padStart(3, '0')}`);

const KPI_BY_CODE = {
  'ENT-001': ['Benefits governance cadence', '%', '95', '98', '96'],
  'ENT-002': ['Invoice touchless processing', '%', '72', '85', '74'],
  'ENT-003': ['Digital onboarding cycle time reduction', '%', '30', '40', '32'],
  'ENT-004': ['Back-office productivity uplift', '%', '18', '24', '20'],
  'ENT-005': ['Certified data domains live', 'count', '6', '8', '5'],
  'ENT-006': ['Discount leakage reduction', '%', '12', '16', '13'],
  'ENT-007': ['Sales coverage productivity', '%', '15', '22', '16'],
  'ENT-008': ['Spend under preferred vendors', '%', '68', '78', '70'],
  'ENT-009': ['Control tower exception closure', '%', '75', '88', '77'],
  'ENT-010': ['Service desk automation rate', '%', '55', '70', '58'],
};

const RISKS_BY_CODE = {
  'ENT-001': ['Benefits office capacity limits governance cadence.', 'operational', 'medium', 'medium', 'Weekly value office cadence and escalation.'],
  'ENT-002': ['ERP workflow variance slows automation adoption.', 'operational', 'high', 'medium', 'Standardize process exceptions before rollout.'],
  'ENT-003': ['Customer data quality blocks onboarding automation.', 'technology', 'high', 'medium', 'Prioritize data cleanse with commercial owners.'],
  'ENT-004': ['Offshore transition knowledge transfer slips.', 'people', 'medium', 'high', 'Wave-based transition checklist and hypercare.'],
  'ENT-005': ['Enterprise data model decision delays platform release.', 'technology', 'high', 'high', 'Steering committee decision by architecture board.'],
  'ENT-006': ['Sales adoption resistance limits pricing impact.', 'people', 'medium', 'medium', 'Sponsor-led adoption and discount exception reviews.'],
  'ENT-007': ['Coverage expansion hiring lags territory plan.', 'people', 'medium', 'medium', 'Prioritize critical markets and backfill channels.'],
  'ENT-008': ['Vendor consolidation faces contract breakage costs.', 'financial', 'medium', 'medium', 'Legal review and phased transition plan.'],
  'ENT-009': ['Supply chain source-system latency reduces signal quality.', 'technology', 'high', 'medium', 'Daily data quality checks and fallback feeds.'],
  'ENT-010': ['AI service desk accuracy misses adoption threshold.', 'technology', 'medium', 'medium', 'Human review loop and prompt tuning cadence.'],
};

const SHARED_COST_POOLS = [
  {
    name: 'Group technology and data platform',
    description: 'Shared data, cloud, AI, and integration platform costs used by transformation initiatives.',
    category: 'Software / Licenses',
    amountPlan: '650000',
    amountActual: '585000',
    method: 'Benefit weighted',
    driverMetric: 'Gross Margin Uplift',
    targetCodes: ['ENT-002', 'ENT-005', 'ENT-006', 'ENT-009', 'ENT-010'],
  },
  {
    name: 'Transformation PMO and benefits office',
    description: 'Central governance and benefits-office run cost allocated across the bankable portfolio.',
    category: 'People Support',
    amountPlan: '400000',
    amountActual: '360000',
    method: 'Equal split',
    targetCodes: [],
  },
  {
    name: 'Shared change and training support',
    description: 'Shared adoption, training, and change-support capacity for process-heavy initiatives.',
    category: 'Training / Change Management',
    amountPlan: '220000',
    amountActual: '198000',
    method: 'Manual amount',
    targetCodes: ['ENT-002', 'ENT-004', 'ENT-005', 'ENT-010'],
    weights: { 'ENT-002': '55000', 'ENT-004': '70000', 'ENT-005': '55000', 'ENT-010': '40000' },
  },
  {
    name: 'Central advisory and vendor support',
    description: 'Central advisory support allocated to workstreams that used the transformation vendor.',
    category: 'External Consultants',
    amountPlan: '180000',
    amountActual: '162000',
    method: 'Fixed percentage',
    targetCodes: ['ENT-005', 'ENT-008', 'ENT-009'],
    weights: { 'ENT-005': '40', 'ENT-008': '35', 'ENT-009': '25' },
  },
];

function assert(condition, message) {
  if (!condition) throw new Error(message);
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
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  throw new Error(`Timed out waiting for ${label}${lastError ? `: ${lastError.message}` : ''}`);
}

async function requestJson(url, init = {}) {
  const response = await fetch(url, init);
  const text = response.status === 204 ? '' : await response.text();
  assert(response.ok, `${url} returned ${response.status}: ${text.slice(0, 800)}`);
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
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), ${Number(process.env.TRANSMUTER_BROWSER_FETCH_TIMEOUT_MS ?? 20000)});
      let response;
      try {
        response = await fetch(${JSON.stringify(`${apiBaseUrl}${path}`)}, {
        method: ${JSON.stringify(options.method ?? 'GET')},
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: 'Bearer ' + token } : {}),
          ...${JSON.stringify(options.headers ?? {})}
        },
        body: ${options.body === undefined ? 'undefined' : JSON.stringify(JSON.stringify(options.body))},
        signal: controller.signal
        });
      } finally {
        clearTimeout(timeout);
      }
      const text = response.status === 204 ? '' : await response.text();
      if (!response.ok) throw new Error(${JSON.stringify(path)} + ' returned ' + response.status + ': ' + text.slice(0, 800));
      return text ? JSON.parse(text) : null;
    })()
  `);
}

async function loginWithUi(page) {
  await page.send('Page.navigate', { url: `${uiBaseUrl}/auth/login` });
  await waitFor(() => evalJs(page, "document.querySelector('input[name=email]') !== null"), 'login form');
  await setField(page, 'input[name=email]', email);
  await setField(page, 'input[name=password]', password);
  await clickFirst(page, 'button[type=submit]');
  await waitFor(() => evalJs(page, "!!localStorage.getItem('access_token') && !location.pathname.includes('/auth/login')"), 'authenticated UI session');
}

async function setField(page, selector, value) {
  await evalJs(page, `
    (() => {
      const el = document.querySelector(${JSON.stringify(selector)});
      if (!el) throw new Error('Missing field: ' + ${JSON.stringify(selector)});
      el.value = ${JSON.stringify(value)};
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
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

async function clickText(page, text) {
  await evalJs(page, `
    (() => {
      const needle = ${JSON.stringify(text)}.toLowerCase();
      const el = [...document.querySelectorAll('button,a,[role="button"]')]
        .filter(node => !node.disabled)
        .find(node => node.textContent.trim().toLowerCase().includes(needle));
      if (!el) throw new Error('Missing clickable text: ' + needle);
      el.click();
      return true;
    })()
  `);
}

async function clickTab(page, text) {
  await evalJs(page, `
    (() => {
      const el = [...document.querySelectorAll('nav button')]
        .find(node => node.textContent.trim() === ${JSON.stringify(text)});
      if (!el) throw new Error('Missing tab: ' + ${JSON.stringify(text)});
      el.click();
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
      const option = [...select.options].find(item => item.textContent.toLowerCase().includes(needle));
      if (!option) throw new Error('Missing option ' + needle + ' in ' + ${JSON.stringify(selector)});
      select.value = option.value;
      select.dispatchEvent(new Event('input', { bubbles: true }));
      select.dispatchEvent(new Event('change', { bubbles: true }));
      return option.value;
    })()
  `);
}

async function setSelectValue(page, selector, value) {
  await evalJs(page, `
    (() => {
      const select = document.querySelector(${JSON.stringify(selector)});
      if (!select) throw new Error('Missing select: ' + ${JSON.stringify(selector)});
      select.value = ${JSON.stringify(value)};
      select.dispatchEvent(new Event('input', { bubbles: true }));
      select.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    })()
  `);
}

async function setInputFile(page, selector, filePath) {
  const root = await page.send('DOM.getDocument');
  const node = await page.send('DOM.querySelector', { nodeId: root.root.nodeId, selector });
  assert(node.nodeId, `Missing file input: ${selector}`);
  await page.send('DOM.setFileInputFiles', { nodeId: node.nodeId, files: [filePath] });
  await evalJs(page, `
    (() => {
      const input = document.querySelector(${JSON.stringify(selector)});
      if (!input) throw new Error('Missing file input after set: ' + ${JSON.stringify(selector)});
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
      return input.files?.length || 0;
    })()
  `);
}

function canonicalCodeFor(initiative, index) {
  if (initiative.initiative_code?.startsWith('ENT-')) return initiative.initiative_code;
  return canonicalCodes[index] ?? initiative.initiative_code;
}

function buildCodeMaps(initiatives) {
  const byActualCode = Object.fromEntries(initiatives.map(item => [item.initiative_code, item]));
  const byCanonicalCode = {};
  initiatives.forEach((initiative, index) => {
    byCanonicalCode[canonicalCodeFor(initiative, index)] = initiative;
  });
  return { byActualCode, byCanonicalCode };
}

async function tenantLedgerCsvPath(initiatives, tempDir) {
  const { byCanonicalCode } = buildCodeMaps(initiatives);
  const source = await readFile(ledgerCsvPath, 'utf8');
  const mapped = source.replace(/\bENT-\d{3}\b/g, code => byCanonicalCode[code]?.initiative_code ?? code);
  const target = `${tempDir}/acme4-benefit-ledger-import.csv`;
  await writeFile(target, mapped);
  return target;
}

async function tenantLedgerCsvText(initiatives) {
  const { byCanonicalCode } = buildCodeMaps(initiatives);
  const source = await readFile(ledgerCsvPath, 'utf8');
  return source.replace(/\bENT-\d{3}\b/g, code => byCanonicalCode[code]?.initiative_code ?? code);
}

async function ensureMilestonesKpisRisks(page, initiative) {
  console.log(`[acme4] enriching initiative ${initiative.initiative_code}`);
  const canonicalCode = canonicalCodeFor(initiative, Number(initiative.initiative_code?.match(/\d+$/)?.[0] ?? 1) - 1);
  await page.send('Page.navigate', { url: `${uiBaseUrl}/initiatives/${initiative.id}` });
  await waitFor(() => evalJs(page, `document.body.innerText.includes(${JSON.stringify(initiative.name)})`), `initiative ${initiative.initiative_code}`);

  await clickTab(page, 'Milestones');
  console.log(`[acme4] ${initiative.initiative_code}: milestones`);
  const existingMilestones = await browserFetch(page, `/initiatives/${initiative.id}/milestones`);
  for (const [name, description, endDate] of [
    [`${initiative.initiative_code} baseline and plan approved`, 'Baseline, assumptions, and owner accountability approved.', '2027-03-31'],
    [`${initiative.initiative_code} FY28 run-rate activated`, 'Run-rate capability is live and tracked through realization cadence.', '2028-06-30'],
  ]) {
    if ((existingMilestones.items ?? []).some(item => item.name === name)) continue;
    await clickText(page, 'New Milestone');
    await waitFor(() => evalJs(page, "document.body.innerText.includes('New Milestone')"), 'new milestone modal');
    await setField(page, 'input[placeholder^="e.g. Pilot"]', name);
    await setField(page, 'textarea[placeholder^="Key outcomes"]', description);
    await setField(page, 'input[type=date]', endDate);
    await clickText(page, 'Create Milestone');
    await waitFor(() => evalJs(page, `document.body.innerText.includes(${JSON.stringify(name)})`), `milestone ${name}`);
  }

  await clickTab(page, 'KPIs');
  console.log(`[acme4] ${initiative.initiative_code}: KPIs`);
  const [kpiName, unit, base, high, actual] = KPI_BY_CODE[canonicalCode] ?? [`${initiative.initiative_code} value KPI`, '%', '80', '90', '82'];
  const existingKpis = await browserFetch(page, `/initiatives/${initiative.id}/kpis`);
  if (!(existingKpis.items ?? []).some(item => item.name === kpiName)) {
    await clickText(page, 'Add KPI');
    await waitFor(() => evalJs(page, "document.body.innerText.includes('New KPI Definition')"), 'new KPI modal');
    await setField(page, 'input[placeholder^="e.g. Monthly"]', kpiName);
    await setField(page, 'input[placeholder^="e.g. %"]', unit);
    await clickText(page, 'Create KPI');
    await waitFor(() => evalJs(page, `document.body.innerText.includes(${JSON.stringify(kpiName)})`), `KPI ${kpiName}`);
  }
  const currentKpis = await browserFetch(page, `/initiatives/${initiative.id}/kpis`);
  const kpi = (currentKpis.items ?? []).find(item => item.name === kpiName);
  assert(kpi, `KPI was not persisted: ${kpiName}`);
  await evalJs(page, `
    (() => {
      if (!globalThis.__transmuterKpis) throw new Error('KPI component instance is not available');
      globalThis.__transmuterKpis.entryDrafts[${JSON.stringify(kpi.id)}] = {
        year: 2028,
        quarter: 4,
        value_base: ${JSON.stringify(base)},
        value_high: ${JSON.stringify(high)},
        value_actual: ${JSON.stringify(actual)}
      };
      globalThis.__transmuterKpis.onSaveEntry(${JSON.stringify(kpi)});
      return true;
    })()
  `);
  await waitFor(async () => {
    const kpis = await browserFetch(page, `/initiatives/${initiative.id}/kpis`);
    return (kpis.items ?? []).some(item => item.name === kpiName && item.entries?.some(entry => entry.year === 2028 && entry.quarter === 4));
  }, `KPI entry ${kpiName}`);

  await clickTab(page, 'Risks');
  console.log(`[acme4] ${initiative.initiative_code}: risks`);
  const [description, type, impact, likelihood, mitigation] = RISKS_BY_CODE[canonicalCode] ?? [`${initiative.initiative_code} adoption risk`, 'operational', 'medium', 'medium', 'Governance cadence.'];
  const existingRisks = await browserFetch(page, `/initiatives/${initiative.id}/risks`);
  if (!(existingRisks.items ?? []).some(item => item.description === description)) {
    await clickText(page, 'Add Risk');
    await waitFor(() => evalJs(page, "document.body.innerText.includes('Register New Risk')"), 'risk modal');
    await setField(page, 'textarea[placeholder^="What is the potential"]', description);
    await setField(page, 'textarea[placeholder^="How will we address"]', mitigation);
    await evalJs(page, `
      (() => {
        const selects = [...document.querySelectorAll('select.input-field')];
        const setByValue = (value, index = 0) => {
          const matches = selects.filter(select => [...select.options].some(option => option.value === value));
          const select = matches[index];
          if (!select) throw new Error('Missing risk select option: ' + value);
          select.value = value;
          select.dispatchEvent(new Event('input', { bubbles: true }));
          select.dispatchEvent(new Event('change', { bubbles: true }));
        };
        setByValue(${JSON.stringify(type)});
        setByValue(${JSON.stringify(impact)}, 0);
        setByValue(${JSON.stringify(likelihood)}, 1);
        return true;
      })()
    `);
    await clickText(page, 'Create Risk');
    await waitFor(() => evalJs(page, `document.body.innerText.includes(${JSON.stringify(description)})`), `risk ${description}`);
  }
}

async function ensureInitiativeDependencies(page, byCode) {
  console.log('[acme4] enriching initiative dependencies');
  const specs = [
    ['ENT-004', 'ENT-005', 'blocks', 'high', '2028-03-31', 'ERP process standardization must stabilize before procurement wave 2 cutover.'],
    ['ENT-006', 'ENT-002', 'requires_decision', 'high', '2028-02-28', 'Enterprise data model decision gates the revenue analytics rollout.'],
    ['ENT-010', 'ENT-008', 'enables', 'medium', '2028-04-15', 'Collaboration tooling adoption enables the shared services productivity case.'],
  ];
  const existing = await browserFetch(page, '/initiative-dependencies');
  for (const [upstream, downstream, type, severity, dueDate, notes] of specs) {
    const upstreamRow = byCode[upstream];
    const downstreamRow = byCode[downstream];
    await page.send('Page.navigate', { url: `${uiBaseUrl}/initiatives/${downstreamRow.id}` });
    if ((existing.items ?? []).some(item =>
      item.upstream?.initiative_code === upstreamRow.initiative_code
      && item.downstream?.initiative_code === downstreamRow.initiative_code
    )) continue;
    await waitFor(() => evalJs(page, `document.body.innerText.includes(${JSON.stringify(downstreamRow.name)})`), `dependency downstream ${downstream}`);
    await clickTab(page, 'Dependencies');
    await waitFor(() => evalJs(page, "document.body.innerText.includes('Link Dependency')"), 'dependencies tab');
    await waitFor(() => evalJs(page, `
      [...document.querySelectorAll('select[aria-label="Upstream initiative"] option')]
        .some(option => option.textContent.includes(${JSON.stringify(upstreamRow.initiative_code)}))
      && [...document.querySelectorAll('select[aria-label="Downstream initiative"] option')]
        .some(option => option.textContent.includes(${JSON.stringify(downstreamRow.initiative_code)}))
    `), `dependency options ${upstreamRow.initiative_code}->${downstreamRow.initiative_code}`);
    await selectByOptionText(page, 'select[aria-label="Upstream initiative"]', upstreamRow.initiative_code);
    await selectByOptionText(page, 'select[aria-label="Downstream initiative"]', downstreamRow.initiative_code);
    await setSelectValue(page, 'select[aria-label="Dependency type"]', type);
    await setSelectValue(page, 'select[aria-label="Dependency severity"]', severity);
    await setField(page, 'input[aria-label="Dependency due date"]', dueDate);
    await setField(page, 'input[aria-label="Dependency resolution notes"]', notes);
    await evalJs(page, `
      (() => {
        const upstreamValue = document.querySelector('select[aria-label="Upstream initiative"]')?.value;
        const downstreamValue = document.querySelector('select[aria-label="Downstream initiative"]')?.value;
        if (upstreamValue !== ${JSON.stringify(upstreamRow.id)} || downstreamValue !== ${JSON.stringify(downstreamRow.id)}) {
          throw new Error('Dependency select mismatch: ' + upstreamValue + ' -> ' + downstreamValue);
        }
        return true;
      })()
    `);
    await clickFirst(page, 'button[aria-label="Create initiative dependency"]');
    try {
      await waitFor(async () => {
        const deps = await browserFetch(page, '/initiative-dependencies');
        return (deps.items ?? []).some(item =>
          item.upstream?.initiative_code === upstreamRow.initiative_code
          && item.downstream?.initiative_code === downstreamRow.initiative_code
        );
      }, `initiative dependency ${upstream}->${downstream}`);
    } catch (error) {
      const state = await evalJs(page, `
        (() => ({
          path: location.pathname,
          text: document.body.innerText.slice(0, 2500),
          upstream: document.querySelector('select[aria-label="Upstream initiative"]')?.value,
          downstream: document.querySelector('select[aria-label="Downstream initiative"]')?.value,
          type: document.querySelector('select[aria-label="Dependency type"]')?.value,
          severity: document.querySelector('select[aria-label="Dependency severity"]')?.value,
          dueDate: document.querySelector('input[aria-label="Dependency due date"]')?.value,
          notes: document.querySelector('input[aria-label="Dependency resolution notes"]')?.value,
        }))()
      `);
      throw new Error(`${error.message}; dependency UI state=${JSON.stringify(state)}`);
    }
  }
}

async function ensureBenefitLedgerImport(page, initiatives, tempDir) {
  console.log('[acme4] importing benefit ledger through UI');
  const summary = await browserFetch(page, '/benefit-ledger/summary?scope=portfolio&granularity=monthly');
  if (Number(summary.actual_amount ?? 0) > 0 && Number(summary.periods?.length ?? 0) >= 24) return;
  await page.send('Page.navigate', { url: `${uiBaseUrl}/financials/benefit-tracking` });
  await waitFor(() => evalJs(page, "document.body.innerText.includes('Locked Baseline Realization')"), 'benefit tracking');
  await clickText(page, 'Import');
  await waitFor(() => evalJs(page, "document.querySelector('input[type=file][accept*=csv]') !== null"), 'benefit CSV input');
  const mappedCsvPath = await tenantLedgerCsvPath(initiatives, tempDir);
  await setInputFile(page, 'input[type=file][accept*=csv]', mappedCsvPath);
  await waitFor(() => evalJs(page, `
    [...document.querySelectorAll('button')]
      .some(button => button.textContent.trim() === 'Import CSV' && !button.disabled)
  `), 'enabled benefit ledger import button');
  await evalJs(page, `
    (() => {
      const button = [...document.querySelectorAll('button')]
        .find(item => item.textContent.trim() === 'Import CSV');
      if (!button) throw new Error('Missing exact Import CSV button');
      button.scrollIntoView({ block: 'center', inline: 'center' });
      button.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window }));
      button.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window }));
      button.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
      return true;
    })()
  `);
  try {
    await waitFor(() => evalJs(page, "document.body.innerText.includes('Import finished') && document.body.innerText.includes('errors')"), 'benefit ledger import result', 60_000);
  } catch (error) {
    const state = await evalJs(page, `
      (() => ({
        path: location.pathname,
        text: document.body.innerText.slice(0, 3500),
        fileCount: document.querySelector('input[type=file][accept*=csv]')?.files?.length || 0,
        importButton: [...document.querySelectorAll('button')]
          .find(button => button.textContent.trim() === 'Import CSV')
          ? { disabled: [...document.querySelectorAll('button')].find(button => button.textContent.trim() === 'Import CSV').disabled,
              text: [...document.querySelectorAll('button')].find(button => button.textContent.trim() === 'Import CSV').textContent.trim() }
          : null,
      }))()
    `);
    console.log(`[acme4] benefit ledger UI button did not complete import; falling back to authenticated browser FormData import. State: ${JSON.stringify(state)}`);
    const csvText = await tenantLedgerCsvText(initiatives);
    const fallback = await evalJs(page, `
      (async () => {
        const token = localStorage.getItem('access_token');
        const form = new FormData();
        form.append('file', new File([${JSON.stringify(csvText)}], 'acme4-benefit-ledger-import.csv', { type: 'text/csv' }));
        const response = await fetch(${JSON.stringify(`${apiBaseUrl}/benefit-ledger/import`)}, {
          method: 'POST',
          headers: token ? { Authorization: 'Bearer ' + token } : {},
          body: form,
        });
        const text = await response.text();
        if (!response.ok) throw new Error('benefit ledger fallback import returned ' + response.status + ': ' + text.slice(0, 800));
        return text ? JSON.parse(text) : null;
      })()
    `);
    console.log(`[acme4] benefit ledger fallback import result ${JSON.stringify(fallback)}`);
  }
  const after = await browserFetch(page, '/benefit-ledger/summary?scope=portfolio&granularity=monthly');
  assert(Number(after.actual_amount ?? 0) > 0, 'Benefit ledger import did not create realized actuals');
}

async function ensureSharedCostPool(page, pool, byCode) {
  console.log(`[acme4] enriching shared cost pool ${pool.name}`);
  await page.send('Page.navigate', { url: `${uiBaseUrl}/shared-costs` });
  await waitFor(() => evalJs(page, "document.body.innerText.includes('Shared Cost Pools')"), 'shared costs page');
  const existing = await browserFetch(page, '/shared-cost-pools');
  let poolRow = (existing.items ?? []).find(item => item.name === pool.name);
  if (!poolRow) {
    await setField(page, 'input[aria-label="Shared cost pool name"]', pool.name);
    await selectByOptionText(page, 'select[aria-label="Shared cost category"]', pool.category);
    await selectByOptionText(page, 'select[aria-label="Shared cost scenario"]', 'Plan Base');
    await setField(page, 'input[aria-label="Shared cost year"]', '2028');
    await setSelectValue(page, 'select[aria-label="Shared cost period grain"]', 'annual');
    await setField(page, 'input[aria-label="Shared cost planned amount"]', pool.amountPlan);
    await setField(page, 'input[aria-label="Shared cost actual amount"]', pool.amountActual);
    await setSelectValue(page, 'select[aria-label="Shared cost reporting treatment"]', 'report_only');
    await setField(page, 'textarea[aria-label="Shared cost pool description"]', pool.description);
    await clickText(page, 'Create Pool');
    await waitFor(async () => {
      const pools = await browserFetch(page, '/shared-cost-pools');
      poolRow = (pools.items ?? []).find(item => item.name === pool.name);
      return poolRow;
    }, `shared cost pool ${pool.name}`);
  }

  await page.send('Page.navigate', { url: `${uiBaseUrl}/shared-costs` });
  await waitFor(() => evalJs(page, "document.body.innerText.includes('Shared Cost Pools')"), 'shared costs page after pool create');
  await waitFor(() => evalJs(page, `
    [...document.querySelectorAll('button')]
      .some(node => node.getAttribute('aria-label') === ${JSON.stringify(`Select ${pool.name}`)})
  `), `pool row ${pool.name}`);
  await evalJs(page, `
    (() => {
      const button = [...document.querySelectorAll('button')]
        .find(node => node.getAttribute('aria-label') === ${JSON.stringify(`Select ${pool.name}`)});
      if (!button) throw new Error('Missing pool selector: ' + ${JSON.stringify(pool.name)});
      button.click();
      return true;
    })()
  `);
  await waitFor(() => evalJs(page, `
    document.querySelector('button[aria-label="Save allocation rule"]') !== null
    && !document.querySelector('button[aria-label="Save allocation rule"]').disabled
  `), `pool selected ${pool.name}`);

  const rules = await browserFetch(page, `/shared-cost-pools/${poolRow.id}/allocation-rules`);
  let rule = (rules ?? []).find(item => item.name === `${pool.method} allocation`);
  if (!rule) {
    await setField(page, 'input[aria-label="Allocation rule name"]', `${pool.method} allocation`);
    await selectByOptionText(page, 'select[aria-label="Allocation method"]', pool.method);
    if (pool.driverMetric) await selectByOptionText(page, 'select[aria-label="Allocation driver metric"]', pool.driverMetric);
    await selectByOptionText(page, 'select[aria-label="Allocation driver scenario"]', 'Plan Base');
    await clickText(page, 'Save Rule');
    await waitFor(async () => {
      const nextRules = await browserFetch(page, `/shared-cost-pools/${poolRow.id}/allocation-rules`);
      rule = (nextRules ?? []).find(item => item.name === `${pool.method} allocation`);
      return rule;
    }, `allocation rule ${pool.name}`);
  }

  if (!(pool.targetCodes ?? []).length && !Object.keys(pool.weights ?? {}).length) {
    const existingRuns = await browserFetch(page, `/shared-cost-pools/${poolRow.id}/allocation-runs`);
    if ((existingRuns ?? []).some(run => ['locked', 'posted', 'completed'].includes(run.status))) return;
  }

  await waitFor(() => evalJs(page, `
    [...document.querySelectorAll('button')]
      .some(node => node.getAttribute('aria-label') === ${JSON.stringify(`Select allocation rule ${rule.name}`)})
  `), `rule row ${rule.name}`);
  await evalJs(page, `
    (() => {
      const button = [...document.querySelectorAll('button')]
        .find(node => node.getAttribute('aria-label') === ${JSON.stringify(`Select allocation rule ${rule.name}`)});
      if (!button) throw new Error('Missing rule selector: ' + ${JSON.stringify(rule.name)});
      button.click();
      return true;
    })()
  `);

  for (const code of pool.targetCodes ?? []) {
    rule = (await browserFetch(page, `/shared-cost-pools/${poolRow.id}/allocation-rules`)).find(item => item.id === rule.id);
    if ((rule.targets ?? []).some(target => target.dimension_value === byCode[code].id)) continue;
    await setSelectValue(page, 'select[aria-label="Allocation target mode"]', 'include');
    await setSelectValue(page, 'select[aria-label="Allocation target dimension"]', 'initiative');
    await setSelectValue(page, 'select[aria-label="Allocation target value"]', byCode[code].id);
    await clickFirst(page, 'button[aria-label="Add allocation target"]');
    await waitFor(async () => {
      const nextRule = (await browserFetch(page, `/shared-cost-pools/${poolRow.id}/allocation-rules`)).find(item => item.id === rule.id);
      return (nextRule.targets ?? []).some(target => target.dimension_value === byCode[code].id);
    }, `target ${pool.name} ${code}`);
  }

  for (const [code, value] of Object.entries(pool.weights ?? {})) {
    rule = (await browserFetch(page, `/shared-cost-pools/${poolRow.id}/allocation-rules`)).find(item => item.id === rule.id);
    if ((rule.structured_weights ?? []).some(weight => weight.initiative_id === byCode[code].id)) continue;
    await waitFor(() => evalJs(page, `
      [...document.querySelectorAll('select[aria-label="Allocation weight initiative"] option')]
        .some(option => option.value === ${JSON.stringify(byCode[code].id)})
    `), `weight option ${pool.name} ${code}`);
    await setSelectValue(page, 'select[aria-label="Allocation weight initiative"]', byCode[code].id);
    await setField(page, 'input[aria-label="Allocation weight value"]', value);
    await clickFirst(page, 'button[aria-label="Add allocation weight"]');
    await waitFor(async () => {
      const nextRule = (await browserFetch(page, `/shared-cost-pools/${poolRow.id}/allocation-rules`)).find(item => item.id === rule.id);
      return (nextRule.structured_weights ?? []).some(weight => weight.initiative_id === byCode[code].id);
    }, `weight ${pool.name} ${code}`);
  }

  const runs = await browserFetch(page, `/shared-cost-pools/${poolRow.id}/allocation-runs`);
  if ((runs ?? []).some(run => ['locked', 'posted', 'completed'].includes(run.status))) return;
  await clickText(page, 'Preview Allocation');
  await waitFor(() => evalJs(page, "document.body.innerText.includes('Reconciled') && !document.body.innerText.includes('Blocked')"), `shared cost preview ${pool.name}`);
  await clickText(page, 'Post Locked Run');
  await waitFor(async () => {
    const nextRuns = await browserFetch(page, `/shared-cost-pools/${poolRow.id}/allocation-runs`);
    return (nextRuns ?? []).some(run => ['locked', 'posted', 'completed'].includes(run.status));
  }, `locked shared cost run ${pool.name}`);
}

async function ensureGovernedRebaseline(page, byCode) {
  const initiative = byCode['ENT-005'];
  assert(initiative, 'Missing ENT-005/TRN-005 initiative for governed rebaseline');
  let plan = await browserFetch(page, `/initiatives/${initiative.id}/bankable-plan`);
  if (Number(plan.current?.version ?? 0) >= 2) {
    console.log(`[acme4] ${initiative.initiative_code} already has bankable plan v${plan.current.version}`);
    return;
  }

  const reason = 'Governed Acme4 rebaseline after refreshed delivery timing and platform assumptions.';
  let governance = await browserFetch(page, `/initiatives/${initiative.id}/governance`);
  let pending = (governance.history ?? []).find(row => row.submission_type === 'bankable_plan_rebaseline' && row.decision === 'pending');

  if (!pending) {
    console.log(`[acme4] requesting governed rebaseline for ${initiative.initiative_code}`);
    await page.send('Page.navigate', { url: `${uiBaseUrl}/financials/bankable-plan` });
    await waitFor(() => evalJs(page, "location.pathname === '/financials/bankable-plan' && document.querySelector('select')"), 'bankable plan select');
    await waitFor(() => evalJs(page, `
      [...document.querySelectorAll('select option')]
        .some(option => option.textContent.includes(${JSON.stringify(initiative.initiative_code)}) || option.textContent.includes(${JSON.stringify(initiative.name)}))
    `), `${initiative.initiative_code} bankable plan option`);
    await selectByOptionText(page, 'select', initiative.initiative_code).catch(() => selectByOptionText(page, 'select', initiative.name));
    await waitFor(() => evalJs(page, `
      document.body.innerText.includes(${JSON.stringify(initiative.initiative_code)})
      || document.body.innerText.includes(${JSON.stringify(initiative.name)})
    `), 'selected bankable plan');
    await waitFor(() => evalJs(page, `
      [...document.querySelectorAll('button')]
        .some(button => !button.disabled && button.textContent.toLowerCase().includes('request rebaseline'))
    `), 'enabled rebaseline request button');
    await clickText(page, 'Request rebaseline');
    await waitFor(() => evalJs(page, "document.body.innerText.includes('Request rebaseline approval')"), 'rebaseline request modal');
    await setField(page, 'textarea[aria-label="Reason for bankable plan rebaseline"]', reason);
    await clickText(page, 'Submit request');
    await waitFor(async () => {
      governance = await browserFetch(page, `/initiatives/${initiative.id}/governance`);
      pending = (governance.history ?? []).find(row => row.submission_type === 'bankable_plan_rebaseline' && row.decision === 'pending');
      return pending;
    }, 'pending rebaseline request');
  }
  assert(pending, `Expected pending rebaseline request for ${initiative.initiative_code}`);

  console.log(`[acme4] approving governed rebaseline for ${initiative.initiative_code}`);
  await page.send('Page.navigate', { url: `${uiBaseUrl}/pmo/governance?status=pending` });
  await waitFor(() => evalJs(page, `
    location.pathname === '/pmo/governance'
    && document.body
    && document.body.innerText.includes('Governance Authority')
    && document.body.innerText.includes('Bankable plan rebaseline')
  `), 'governance queue');
  await evalJs(page, `
    (() => {
      const reason = ${JSON.stringify(reason)};
      const cards = [...document.querySelectorAll('.card')];
      const card = cards.find(node => node.textContent.includes(reason) || node.textContent.includes('Bankable plan rebaseline'));
      if (!card) throw new Error('Missing rebaseline governance card');
      const approve = [...card.querySelectorAll('button')]
        .find(button => button.textContent.trim().toLowerCase().includes('check') || button.querySelector('.material-icons')?.textContent.trim() === 'check');
      if (!approve) throw new Error('Missing rebaseline approve button');
      approve.click();
      return true;
    })()
  `);
  await waitFor(async () => {
    plan = await browserFetch(page, `/initiatives/${initiative.id}/bankable-plan`);
    return Number(plan.current?.version ?? 0) >= 2;
  }, `${initiative.initiative_code} rebaseline approval`);
}

async function validate(page) {
  console.log('[acme4] validating enriched demo tenant');
  const initiatives = await browserFetch(page, '/initiatives?page_size=100&sort_by=initiative_code');
  const items = initiatives.items ?? [];
  assert(items.length === 10, `Expected 10 initiatives, got ${items.length}`);

  const plans = await Promise.all(items.map(item => browserFetch(page, `/initiatives/${item.id}/bankable-plan`)));
  assert(plans.every(plan => plan.current), 'Expected every initiative to have a locked bankable plan');
  const rebaselinePlan = plans[items.findIndex(item => item.initiative_code === 'TRN-005' || item.initiative_code === 'ENT-005')];
  assert(Number(rebaselinePlan?.current?.version ?? 0) >= 2, 'Expected ACME4 TRN-005/ENT-005 to include governed rebaseline history');

  const kpiCounts = await Promise.all(items.map(item => browserFetch(page, `/initiatives/${item.id}/kpis`)));
  const riskCounts = await Promise.all(items.map(item => browserFetch(page, `/initiatives/${item.id}/risks`)));
  const milestoneCounts = await Promise.all(items.map(item => browserFetch(page, `/initiatives/${item.id}/milestones`)));
  assert(kpiCounts.every(row => (row.items ?? []).length >= 1), 'Expected each initiative to have at least one KPI');
  assert(riskCounts.every(row => (row.items ?? []).length >= 1), 'Expected each initiative to have at least one risk');
  assert(milestoneCounts.every(row => (row.items ?? []).length >= 2), 'Expected each initiative to have at least two milestones');

  const dependencies = await browserFetch(page, '/initiative-dependencies');
  assert((dependencies.items ?? []).length >= 3, 'Expected at least three initiative dependencies');

  const ledger = await browserFetch(page, '/benefit-ledger/summary?scope=portfolio&granularity=monthly');
  assert(Number(ledger.actual_amount ?? 0) > 0, 'Expected non-zero benefit ledger actuals');

  const pools = await browserFetch(page, '/shared-cost-pools');
  assert((pools.items ?? []).length >= 4, 'Expected four shared-cost pools');
  for (const pool of SHARED_COST_POOLS) {
    const row = (pools.items ?? []).find(item => item.name === pool.name);
    assert(row, `Missing shared-cost pool ${pool.name}`);
    const runs = await browserFetch(page, `/shared-cost-pools/${row.id}/allocation-runs`);
    assert((runs ?? []).some(run => ['locked', 'posted', 'completed'].includes(run.status)), `Missing locked run for ${pool.name}`);
  }

  await page.send('Page.navigate', { url: `${uiBaseUrl}/dashboard` });
  await waitFor(() => evalJs(page, "document.body.innerText.includes('KPI') && document.body.innerText.includes('Risk')"), 'executive dashboard KPI/risk widgets');
  await page.send('Page.navigate', { url: `${uiBaseUrl}/financials/benefit-tracking` });
  await waitFor(() => evalJs(page, "document.body.innerText.includes('Locked Baseline Realization') && !document.body.innerText.includes('$0.00')"), 'benefit tracking non-zero UI');
  await page.send('Page.navigate', { url: `${uiBaseUrl}/shared-costs` });
  await waitFor(() => evalJs(page, "location.pathname === '/shared-costs' && document.body && (document.body.innerText.includes('Financial Governance') || document.body.innerText.includes('Shared Cost Pools'))"), 'shared costs UI');
  await page.send('Page.navigate', { url: `${uiBaseUrl}/financials/bankable-plan` });
  await waitFor(() => evalJs(page, "location.pathname === '/financials/bankable-plan' && document.body && (document.body.innerText.includes('Bankable Plan') || document.body.innerText.includes('Financial Review'))"), 'bankable plan UI');

  return {
    initiatives: items.length,
    bankablePlans: plans.filter(plan => plan.current).length,
    kpis: kpiCounts.reduce((total, row) => total + (row.items ?? []).length, 0),
    risks: riskCounts.reduce((total, row) => total + (row.items ?? []).length, 0),
    milestones: milestoneCounts.reduce((total, row) => total + (row.items ?? []).length, 0),
    dependencies: (dependencies.items ?? []).length,
    ledgerActual: ledger.actual_amount,
    sharedCostPools: (pools.items ?? []).length,
    rebaselineVersion: rebaselinePlan.current.version,
  };
}

async function main() {
  assert(password, 'TRANSMUTER_E2E_PASSWORD is required');
  await requestJson(`${apiBaseUrl}/health`);
  const userDataDir = await mkdtemp(`${tmpdir()}/transmuter-acme4-full-demo-`);
  const chromeArgs = [
    '--headless=new',
    '--no-sandbox',
    `--remote-debugging-port=${debugPort}`,
    `--user-data-dir=${userDataDir}`,
    '--no-first-run',
    '--no-default-browser-check',
    'about:blank',
  ];
  const chrome = spawn(chromeBin, chromeArgs, { stdio: ['ignore', 'ignore', 'pipe'] });
  chrome.stderr.on('data', chunk => {
    const text = chunk.toString();
    if (!text.includes('DevTools listening')) process.stderr.write(text);
  });
  let page;
  try {
    await waitFor(() => fetch(`http://127.0.0.1:${debugPort}/json/version`).then(r => r.ok), 'Chrome DevTools endpoint');
    const target = await requestJson(`http://127.0.0.1:${debugPort}/json/new?${encodeURIComponent('about:blank')}`, { method: 'PUT' });
    page = await connectToPage(target.webSocketDebuggerUrl);
    await page.send('Runtime.enable');
    await page.send('Page.enable');
    await page.send('DOM.enable');
    await page.send('Page.addScriptToEvaluateOnNewDocument', {
      source: "window.alert = message => console.log('[alert]', message); window.confirm = () => true;",
    });
    await loginWithUi(page);
    await evalJs(page, "window.alert = message => console.log('[alert]', message); window.confirm = () => true; true");

    const list = await browserFetch(page, '/initiatives?page_size=100&sort_by=initiative_code');
    const initiatives = list.items ?? [];
    const { byActualCode, byCanonicalCode } = buildCodeMaps(initiatives);
    const byCode = { ...byActualCode, ...byCanonicalCode };
    assert(initiatives.length === 10, `Acme4 must already have 10 initiatives; got ${initiatives.length}`);
    assert(initiatives.every(item => /^TRN-\d{3}$|^ENT-\d{3}$/.test(item.initiative_code)), `Unexpected Acme4 initiative codes: ${initiatives.map(item => item.initiative_code).join(', ')}`);

    if (process.env.TRANSMUTER_SKIP_INITIATIVE_ARTIFACTS !== '1') {
      for (const initiative of initiatives) {
        await ensureMilestonesKpisRisks(page, initiative);
      }
    } else {
      console.log('[acme4] skipping initiative tab enrichment');
    }
    console.log('[acme4] initiative tabs complete');
    await ensureInitiativeDependencies(page, byCode);
    console.log('[acme4] dependencies complete');
    await ensureBenefitLedgerImport(page, initiatives, userDataDir);
    console.log('[acme4] benefit ledger complete');
    for (const pool of SHARED_COST_POOLS) {
      await ensureSharedCostPool(page, pool, byCode);
    }
    console.log('[acme4] shared costs complete');
    await ensureGovernedRebaseline(page, byCode);
    console.log('[acme4] governed rebaseline complete');

    const result = await validate(page);
    console.log(JSON.stringify({ status: 'passed', ...result }, null, 2));
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
