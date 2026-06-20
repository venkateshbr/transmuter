import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { homedir, tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawn } from 'node:child_process';

const uiBaseUrl = process.env.TRANSMUTER_UI_BASE_URL ?? 'http://localhost:4300';
const apiBaseUrl = process.env.TRANSMUTER_API_BASE_URL ?? 'http://localhost:8000';
const chromeBin = process.env.CHROME_BIN ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const email = process.env.TRANSMUTER_E2E_EMAIL ?? 'admin@ishirock.dev';
const password = process.env.TRANSMUTER_E2E_PASSWORD ?? 'Transmuter2026!';
const debugPort = Number(process.env.CHROME_DEBUG_PORT ?? 9222);
const chromeUploadDir = process.env.CHROME_UPLOAD_DIR ?? homedir();

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function waitFor(fn, label, timeoutMs = 15_000) {
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

async function requestJson(url, init) {
  const response = await fetch(url, init);
  if (init?.allowError) {
    const body = response.status === 204 ? null : await response.json();
    return { status: response.status, body };
  }
  assert(response.ok, `${url} returned ${response.status}`);
  if (response.status === 204) return null;
  return response.json();
}

async function requestBytes(url, init) {
  const response = await fetch(url, init);
  assert(response.ok, `${url} returned ${response.status}`);
  return new Uint8Array(await response.arrayBuffer());
}

async function connectToPage(wsUrl) {
  const socket = new WebSocket(wsUrl);
  let nextId = 1;
  const pending = new Map();
  const events = [];

  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) reject(new Error(message.error.message));
      else resolve(message.result);
    } else if (message.method === 'Runtime.exceptionThrown' || message.method === 'Log.entryAdded') {
      events.push(message);
    }
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
    events,
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

async function clickText(page, text) {
  await evalJs(page, `
    (() => {
      const text = ${JSON.stringify(text)}.toLowerCase();
      const el = [...document.querySelectorAll('button,a')]
        .find(node => node.textContent.trim().toLowerCase().includes(text));
      if (!el) throw new Error('Missing clickable text: ' + text);
      el.click();
      return true;
    })()
  `);
}

async function clickVisibleText(page, text) {
  await evalJs(page, `
    (() => {
      const text = ${JSON.stringify(text)}.toLowerCase();
      const el = [...document.querySelectorAll('button,a,[role="button"]')]
        .find(node => node.textContent.trim().toLowerCase().includes(text));
      if (!el) throw new Error('Missing visible clickable text: ' + text);
      el.click();
      return true;
    })()
  `);
}

async function clickTab(page, text) {
  await evalJs(page, `
    (() => {
      const text = ${JSON.stringify(text)};
      const el = [...document.querySelectorAll('nav button')]
        .find(node => node.textContent.trim() === text);
      if (!el) throw new Error('Missing tab: ' + text);
      el.click();
      return true;
    })()
  `);
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

async function main() {
  await requestJson(`${apiBaseUrl}/health`);

  const userDataDir = await mkdtemp(join(tmpdir(), 'transmuter-e2e-'));
  const chromeArgs = [
    '--headless=new',
    `--remote-debugging-port=${debugPort}`,
    `--user-data-dir=${userDataDir}`,
    '--no-first-run',
    '--no-default-browser-check',
    'about:blank',
  ];
  if (typeof process.getuid === 'function' && process.getuid() === 0) {
    chromeArgs.splice(1, 0, '--no-sandbox');
  }
  const chrome = spawn(chromeBin, chromeArgs, { stdio: ['ignore', 'ignore', 'pipe'] });

  chrome.stderr.on('data', chunk => {
    const text = chunk.toString();
    if (!text.includes('DevTools listening')) process.stderr.write(text);
  });

  try {
    await waitFor(
      () => fetch(`http://127.0.0.1:${debugPort}/json/version`).then(r => r.ok),
      'Chrome DevTools endpoint',
    );

    const target = await requestJson(
      `http://127.0.0.1:${debugPort}/json/new?${encodeURIComponent('about:blank')}`,
      { method: 'PUT' },
    );
    const page = await connectToPage(target.webSocketDebuggerUrl);

    await page.send('Page.enable');
    await page.send('Runtime.enable');
    await page.send('Log.enable');
    await page.send('Page.addScriptToEvaluateOnNewDocument', {
      source: `globalThis.__TRANSMUTER_API_URL__ = ${JSON.stringify(apiBaseUrl)};`,
    });
    await page.send('Page.navigate', { url: `${uiBaseUrl}/auth/login` });

    await waitFor(
      () => evalJs(page, "document.querySelector('input[name=email]') !== null"),
      'login form',
    );

    await evalJs(page, `
      (() => {
        const setValue = (selector, value) => {
          const input = document.querySelector(selector);
          input.value = value;
          input.dispatchEvent(new Event('input', { bubbles: true }));
        };
        setValue('input[name=email]', ${JSON.stringify(email)});
        setValue('input[name=password]', ${JSON.stringify(password)});
        document.querySelector('button[type=submit]').click();
      })()
    `);

    await waitFor(
      () => evalJs(page, "['/', '/dashboard', '/platform'].includes(location.pathname) && !!localStorage.getItem('access_token')"),
      'authenticated dashboard',
      20_000,
    );

    await evalJs(page, `
      (() => {
        const onboarding = [...document.querySelectorAll('button')]
          .find(node => node.textContent.trim().includes('Enter Command Center'));
        if (onboarding) onboarding.click();
        return true;
      })()
    `);
    await waitFor(
      () => evalJs(page, `
        [
          'dashboard-my-actions',
          'dashboard-kpi-pulse',
          'dashboard-value-bridge',
          'dashboard-risk-heatmap',
          'dashboard-recent-activity',
          'dashboard-filter-business-unit',
          'dashboard-filter-workstream',
          'dashboard-filter-priority',
          'dashboard-filter-tag',
          'dashboard-executive-summary'
        ].every(testId => !!document.querySelector('[data-testid="' + testId + '"]'))
      `),
      'dashboard phase 2 widgets and filters',
    );
    const dashboardSnapshot = await requestJson(`${apiBaseUrl}/dashboard`, {
      headers: { Authorization: `Bearer ${await evalJs(page, "localStorage.getItem('access_token')")}` },
    });
    assert(Array.isArray(dashboardSnapshot.my_actions), 'dashboard API should expose my actions');
    assert(dashboardSnapshot.kpi_pulse && dashboardSnapshot.kpi_pulse.health_score !== undefined, 'dashboard API should expose KPI pulse');
    assert(dashboardSnapshot.value_bridge && dashboardSnapshot.value_bridge.net_base !== undefined, 'dashboard API should expose value bridge');
    assert(Array.isArray(dashboardSnapshot.recent_activity), 'dashboard API should expose recent activity');
    assert(dashboardSnapshot.available_filters?.business_units, 'dashboard API should expose business unit filters');
    await evalJs(page, `document.querySelector('[data-testid="dashboard-executive-summary"]').click()`);
    await waitFor(
      () => evalJs(page, "!!document.querySelector('[data-testid=\"dashboard-executive-summary-ready\"]') && !!document.querySelector('[data-testid=\"dashboard-executive-brief\"]')"),
      'executive brief generation',
    );
    await waitFor(
      () => evalJs(page, `
        !!document.querySelector('[data-testid="dashboard-executive-brief-pdf"]')
        && !!document.querySelector('[data-testid="dashboard-executive-brief-excel"]')
      `),
      'executive brief export controls',
    );
    await evalJs(page, `
      (() => {
        const close = document.querySelector('[aria-label="Close executive brief"]');
        if (!close) throw new Error('Missing executive brief close button');
        close.click();
        return true;
      })()
    `);
    await waitFor(
      () => evalJs(page, "!document.querySelector('[data-testid=\"dashboard-executive-brief\"]')"),
      'executive brief closed',
    );
    await evalJs(page, `document.querySelector('[data-testid="dashboard-decision-queue"]').click()`);
    await waitFor(
      () => evalJs(page, "!!document.querySelector('[data-testid=\"dashboard-decision-queue-panel\"]')"),
      'decision queue opens',
    );
    await evalJs(page, `
      (() => {
        const close = document.querySelector('[aria-label="Close decision queue"]');
        if (!close) throw new Error('Missing decision queue close button');
        close.click();
        return true;
      })()
    `);

    const clickDashboardTarget = async testId => {
      await evalJs(page, `
        (() => {
          const el = document.querySelector(${JSON.stringify(`[data-testid="${testId}"]`)});
          if (!el) throw new Error('Missing dashboard target: ' + ${JSON.stringify(testId)});
          el.click();
          return true;
        })()
      `);
    };

    const navigateToDashboard = async label => {
      await page.send('Page.navigate', { url: `${uiBaseUrl}/dashboard` });
      await waitFor(
        () => evalJs(page, "location.pathname === '/dashboard' && !!document.querySelector('[data-testid=\"dashboard-total-initiatives\"]')"),
        label,
        30_000,
      );
    };

    await clickDashboardTarget('dashboard-total-initiatives');
    await waitFor(
      () => evalJs(page, "location.pathname === '/initiatives/pipeline'"),
      'dashboard total initiatives drill-down',
    );
    await navigateToDashboard('dashboard reload');

    await clickDashboardTarget('dashboard-at-risk');
    await waitFor(
      () => evalJs(page, "location.pathname === '/initiatives/pipeline' && new URLSearchParams(location.search).get('rag_status') === 'red'"),
      'dashboard at-risk drill-down',
    );
    await waitFor(
      () => evalJs(page, "!!document.querySelector('[data-testid=\"initiatives-filter-business-unit\"]') && !document.body.innerText.toLowerCase().includes('loading portfolio')"),
      'pipeline red query handled',
      30_000,
    );
    await navigateToDashboard('dashboard reload after risk');

    await clickDashboardTarget('dashboard-pending-approvals');
    await waitFor(
      () => evalJs(page, "location.pathname === '/pmo/governance' && new URLSearchParams(location.search).get('status') === 'pending'"),
      'dashboard pending approvals drill-down',
    );
    await navigateToDashboard('dashboard reload after governance');

    await clickDashboardTarget('dashboard-rag-green');
    await waitFor(
      () => evalJs(page, "location.pathname === '/initiatives/pipeline' && new URLSearchParams(location.search).get('rag_status') === 'green'"),
      'dashboard rag segment drill-down',
    );
    await navigateToDashboard('dashboard reload after rag');

    await clickDashboardTarget('dashboard-stage-scoping');
    await waitFor(
      () => evalJs(page, "location.pathname === '/initiatives/pipeline' && new URLSearchParams(location.search).get('stage') === 'scoping'"),
      'dashboard stage bar drill-down',
    );
    await navigateToDashboard('dashboard reload after stage');

    await clickDashboardTarget('dashboard-pressure');
    await waitFor(
      () => evalJs(page, "location.pathname === '/progress'"),
      'dashboard pressure drill-down',
    );
    await navigateToDashboard('dashboard reload after pressure');

    const clickedMilestone = await evalJs(page, `
      (() => {
        const el = document.querySelector('[data-testid^="dashboard-milestone-"]');
        if (!el) return false;
        el.click();
        return true;
      })()
    `);
    if (clickedMilestone) {
      await waitFor(
        () => evalJs(page, "location.pathname.startsWith('/initiatives/')"),
        'dashboard milestone drill-down',
      );
      await navigateToDashboard('dashboard reload after milestone');
    }

    const token = await evalJs(page, "localStorage.getItem('access_token')");
    const api = (path, init = {}) => requestJson(`${apiBaseUrl}${path}`, {
      ...init,
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...(init.headers ?? {}),
      },
    });

    const gateCriteria = await api('/admin/governance/gate-criteria');
    if (gateCriteria.length < 1) {
      await api('/admin/governance/gate-criteria', {
        method: 'POST',
        body: JSON.stringify({
          gate_number: 1,
          criterion_id: 'acceptance_gate_criterion',
          label: 'Acceptance gate criterion',
          guidance: 'Acceptance data is present for the live browser flow.',
          sort_order: 0,
          is_active: true,
        }),
      });
    }

    let dependencies = await api('/initiative-dependencies');
    if (!(dependencies.rollups && dependencies.rollups.total >= 1)) {
      const initiativeList = await api('/initiatives');
      assert((initiativeList.items || []).length >= 2, 'Need at least two initiatives to seed dependencies');
      const [upstream, downstream] = initiativeList.items;
      await api('/initiative-dependencies', {
        method: 'POST',
        body: JSON.stringify({
          upstream_initiative_id: upstream.id,
          downstream_initiative_id: downstream.id,
          dependency_type: 'blocks',
          status: 'active',
          severity: 'high',
        }),
      });
      dependencies = await api('/initiative-dependencies');
    }
    assert(dependencies.rollups && dependencies.rollups.total >= 1, 'Dependencies should be available');
    assert(dependencies.rollups.critical_path_risk >= 1, 'Dependency rollups should expose critical path risk');

    let sharedPools = await api('/shared-cost-pools');
    if (sharedPools.items.length < 1) {
      await api('/shared-cost-pools', {
        method: 'POST',
        body: JSON.stringify({
          name: `E2E Shared Cost Pool ${Date.now()}`,
          category_key: 'other',
          year: 2026,
          amount_plan: '1000',
          is_recurring: false,
          status: 'active',
        }),
      });
      sharedPools = await api('/shared-cost-pools');
    }
    assert(sharedPools.items.length >= 1, 'Shared cost pools should be available');
    const controlTower = await api('/reports/executive-control-tower?target_year=2026');
    assert(controlTower.value_bridge?.allocated_costs_plan !== undefined, 'Control Tower report should expose allocated costs');
    assert(controlTower.dependency_risk?.total >= 1, 'Control Tower report should expose dependency risk');
    const investorSummary = await api('/reports/investor-summary?target_year=2026');
    assert(investorSummary.summary?.initiative_count >= 1, 'Investor summary should expose portfolio initiatives');

    const originalFinancialConfig = await api('/admin/financial-configuration');
    const acceptanceCategoryLabel = `UI Acceptance Category ${Date.now()}`;
    let acceptanceCategoryKey = null;
    let acceptanceCostLineId = null;
    try {
      await page.send('Page.navigate', { url: `${uiBaseUrl}/admin` });
      await waitFor(
        () => evalJs(page, "location.pathname === '/admin' && !!document.body && document.querySelectorAll('button').length > 0"),
        'admin financial configuration tab',
        20_000,
      );
      await evalJs(page, `
        (() => {
          const button = document.querySelector('button[aria-label="Open Financial Configuration admin tab"]');
          if (!button) throw new Error('Missing Financial Configuration admin tab');
          button.click();
          return true;
        })()
      `);
      await waitFor(
        () => evalJs(page, "document.body.innerText.includes('Cost Categories') && !!document.querySelector('input[aria-label=\"New cost category name\"]')"),
        'admin cost category configuration',
        45_000,
      );
      await setField(page, 'input[aria-label="New cost category name"]', acceptanceCategoryLabel);
      await evalJs(page, `
        (() => {
          const button = document.querySelector('button[aria-label="Create cost category"]');
          if (!button) throw new Error('Missing create cost category button');
          button.click();
          return true;
        })()
      `);
      await waitFor(async () => {
        const config = await api('/admin/financial-configuration');
        const category = config.items.find(item => item.label === acceptanceCategoryLabel && item.is_active !== false);
        if (category) acceptanceCategoryKey = category.key;
        return !!category;
      }, 'admin-created financial category persisted', 20_000);
      assert(acceptanceCategoryKey, 'Created financial category key was not found');

      const categoryInitiativeId = (await api('/initiatives')).items[0].id;
      const categoryCost = await api(`/initiatives/${categoryInitiativeId}/financials/cost-lines`, {
        method: 'POST',
        body: JSON.stringify({
          name: `UI Acceptance Categorized Cost ${Date.now()}`,
          year: 2026,
          quarter: 1,
          month: null,
          amount_plan: '2468.0000',
          amount_actual: '1357.0000',
          is_recurring: false,
          category_key: acceptanceCategoryKey,
        }),
      });
      acceptanceCostLineId = categoryCost.id;

      await page.send('Page.navigate', { url: `${uiBaseUrl}/financials` });
      await waitFor(
        () => evalJs(page, "location.pathname === '/financials' && document.body.innerText.includes('Financials') && document.body.innerText.includes('Cost Breakdown')"),
        'portfolio financials page',
        20_000,
      );
      await clickText(page, 'Quarterly');
      await evalJs(page, `
        (() => {
          const category = document.querySelector('select[aria-label="Filter cost category"]');
          if (!category) throw new Error('Missing cost category filter');
          category.value = ${JSON.stringify(acceptanceCategoryKey)};
          category.dispatchEvent(new Event('change', { bubbles: true }));
          return true;
        })()
      `);
      await waitFor(
        () => evalJs(page, `document.body.innerText.includes(${JSON.stringify(acceptanceCategoryLabel)}) && document.body.innerText.includes('$2,468')`),
        'portfolio financials category rollup',
        20_000,
      );
    } finally {
      if (acceptanceCostLineId) {
        const categoryInitiatives = await api('/initiatives').catch(() => ({ items: [] }));
        await Promise.all((categoryInitiatives.items || []).map(item =>
          api(`/initiatives/${item.id}/financials/cost-lines/${acceptanceCostLineId}`, { method: 'DELETE' }).catch(() => null)
        ));
      }
      await api('/admin/financial-configuration', {
        method: 'PUT',
        body: JSON.stringify(originalFinancialConfig),
      }).catch(() => null);
    }

    await page.send('Page.navigate', { url: `${uiBaseUrl}/reports/control-tower` });
    await waitFor(
      () => evalJs(page, "location.pathname === '/reports/control-tower' && document.body.innerText.includes('Executive Control Tower') && document.body.innerText.includes('Burdened Value Bridge')"),
      'control tower page',
      20_000,
    );
    await clickText(page, 'Investor');
    await waitFor(
      () => evalJs(page, "document.body.innerText.includes('Dependency Risk') && document.body.innerText.includes('Initiative Burdening')"),
      'investor report mode',
      20_000,
    );
    await page.send('Page.navigate', { url: `${uiBaseUrl}/shared-costs` });
    await waitFor(
      () => evalJs(page, "location.pathname === '/shared-costs' && (() => { const text = document.body.innerText.toLowerCase(); return text.includes('shared cost pools') && text.includes('allocation policy') && text.includes('reporting treatment') && text.includes('reconciliation and exceptions'); })()"),
      'shared cost page',
      20_000,
    );

    await evalJs(page, `
      (() => {
        const button = document.querySelector('button[aria-label="Open Transmuter assistant"]');
        if (!button) throw new Error('Missing Transmuter assistant button');
        button.click();
        return true;
      })()
    `);
    await waitFor(
      () => evalJs(page, "document.body.innerText.toLowerCase().includes('ask transmuter') && document.body.innerText.includes('Show me at-risk initiatives')"),
      'transmuter assistant panel',
    );
    await clickText(page, 'Show me at-risk initiatives');
    await waitFor(
      () => evalJs(page, `
        [...document.querySelectorAll('[data-testid="assistant-message-assistant"]')].length >= 1
        && [...document.querySelectorAll('[data-testid="assistant-source-chip"]')].length >= 1
      `),
      'assistant sourced response',
      20_000,
    );
    await evalJs(page, `
      (() => {
        const close = [...document.querySelectorAll('button')].find(button => button.getAttribute('aria-label') === 'Close');
        if (!close) throw new Error('Missing assistant close button');
        close.click();
        return true;
      })()
    `);

    const peopleRows = await api('/users');
    assert(peopleRows.items.length > 0, 'Seeded users were not available');
    const seededPerson = peopleRows.items.find(item => item.status === 'active') ?? peopleRows.items[0];
    const seededPersonLabel = seededPerson.display_name || seededPerson.email;
    const seededPersonRoleLabel = {
      transformation_office: 'Transformation Office',
      initiative_owner: 'Initiative Owner',
      viewer: 'Viewer',
    }[seededPerson.role] ?? seededPerson.role;
    const inviteEmail = `transmuter.acceptance+ui.people.${Date.now()}@gmail.com`;
    let invitedPersonId;

    try {
      await page.send('Page.navigate', { url: `${uiBaseUrl}/people` });
      await waitFor(
        () => evalJs(page, "location.pathname === '/people' && !!document.querySelector('[data-testid=\"people-filters\"]') && document.body.innerText.toLowerCase().includes('people insight')"),
        'people directory',
        20_000,
      );
      await waitFor(
        () => evalJs(page, "document.querySelector('[data-testid=\"people-filters\"]') !== null && document.querySelector('[data-testid=\"people-filters\"] input[aria-label=\"Search\"]') !== null && document.querySelector('button[aria-label=\"Open Role filter\"]') !== null && document.querySelector('button[aria-label=\"Open Status filter\"]') !== null"),
        'people filters',
      );
      await setField(page, '[data-testid="people-filters"] input[aria-label="Search"]', seededPerson.email);
      await waitFor(
        () => evalJs(page, `document.body.innerText.includes(${JSON.stringify(seededPersonLabel)})`),
        'seeded person visible in searched directory',
      );
      await evalJs(page, `
        (() => {
          const roleButton = document.querySelector('button[aria-label="Open Role filter"]');
          if (!roleButton) throw new Error('Missing role filter trigger');
          roleButton.click();
          return true;
        })()
      `);
      await waitFor(
        () => evalJs(page, `document.querySelector(${JSON.stringify(`input[aria-label="Role: ${seededPersonRoleLabel}"]`)}) !== null`),
        'people role filter option',
      );
      await evalJs(page, `
        (() => {
          const role = document.querySelector(${JSON.stringify(`input[aria-label="Role: ${seededPersonRoleLabel}"]`)});
          if (!role) throw new Error('Missing role filter option: ${seededPersonRoleLabel}');
          role.click();
          return true;
        })()
      `);
      await waitFor(
        () => evalJs(page, `document.body.innerText.includes(${JSON.stringify(seededPersonLabel)})`),
        'seeded person visible after role filter',
      );
      await evalJs(page, `
        (() => {
          const label = ${JSON.stringify(seededPersonLabel)};
          const card = [...document.querySelectorAll('.card')]
            .find(node => node.textContent.includes(label));
          if (!card) throw new Error('Missing seeded person card: ' + label);
          card.click();
          return true;
        })()
      `);
      try {
        await waitFor(
          () => evalJs(page, `
            (() => {
              const text = document.body.innerText.toLowerCase();
              return text.includes('on their plate') && text.includes('pressure score');
            })()
          `),
          'people profile drawer',
        );
        await waitFor(
          () => evalJs(page, `
            (() => {
              const text = document.body.innerText.toLowerCase();
              return text.includes('status')
                && text.includes('last login')
                && text.includes('workstreams')
                && text.includes('save profile')
                && text.includes('milestones & actions');
            })()
          `),
          'people profile management details',
        );
      } catch (error) {
        const peopleState = await evalJs(page, `
          (() => JSON.stringify({
            hasOverlay: document.querySelector('.overlay') !== null,
            hasSelectedUser: document.body.innerText.includes(${JSON.stringify(seededPersonLabel)}),
            text: document.body.innerText.slice(0, 1600),
          }))()
        `);
        const browserEvents = page.events.slice(-5).map(event => JSON.stringify(event.params));
        throw new Error(
          `${error.message}\nPeople UI state: ${peopleState}\nBrowser events: ${browserEvents.join('\n')}`,
        );
      }
      const profile = await api(`/users/${seededPerson.id}`);
      assert(profile.on_their_plate && profile.pressure, 'People profile payload missed workload or pressure');
      assert(Array.isArray(profile.workstreams), 'People profile payload missed workstreams');
      const originalTitle = profile.title;
      const editedTitle = `UI People Lead ${Date.now()}`;
      await setField(page, 'input[aria-label="User title"]', editedTitle);
      await clickText(page, 'Save Profile');
      await waitFor(async () => {
        const updated = await api(`/users/${seededPerson.id}`);
        return updated.title === editedTitle;
      }, 'people profile edit persistence');
      await api(`/users/${seededPerson.id}`, {
        method: 'PUT',
        body: JSON.stringify({ title: originalTitle }),
      });
      await evalJs(page, `
        (() => {
          const close = document.querySelector('button[aria-label="Close user profile"]');
          if (!close) throw new Error('Missing user profile close button');
          close.click();
          return true;
        })()
      `);
      await waitFor(
        () => evalJs(page, "!document.querySelector('[data-testid=\"people-profile-details\"]')"),
        'people profile drawer closed',
      );

      await clickText(page, 'Add User');
      await waitFor(
        () => evalJs(page, "document.body.innerText.includes('Add Platform User')"),
        'people invite modal',
      );
      await setField(page, 'input[aria-label="Invite email"]', inviteEmail);
      await setField(page, 'input[aria-label="Invite display name"]', 'UI Acceptance Invite');
      await setField(page, 'input[aria-label="Invite title"]', 'Acceptance Owner');
      await evalJs(page, `
        (() => {
          const select = document.querySelector('select[aria-label="Invite role"]');
          select.value = 'initiative_owner';
          select.dispatchEvent(new Event('input', { bubbles: true }));
          select.dispatchEvent(new Event('change', { bubbles: true }));
          return true;
        })()
      `);
      await evalJs(page, `
        (() => {
          const button = document.querySelector('button[aria-label="Send invite"]');
          if (!button) throw new Error('Missing send invite submit button');
          button.click();
          return true;
        })()
      `);
      await waitFor(async () => {
        const invites = await api('/invites');
        const invited = invites.items.find(item => item.email === inviteEmail);
        if (invited) invitedPersonId = invited.id;
        return invited?.status === 'pending';
      }, 'people invite persistence', 20_000);
      await waitFor(
        () => evalJs(page, `document.body.innerText.includes(${JSON.stringify(inviteEmail)})`),
        'pending invite visible',
      );
    } finally {
      if (invitedPersonId) {
        await api(`/invites/${invitedPersonId}/revoke`, { method: 'POST', body: '{}' }).catch(() => null);
      }
    }

    const manualInitiativeName = `UI Acceptance Initiative ${Date.now()}`;
    let manualInitiativeId;
    let uploadedInitiativeId;
    let statusSilentInitiativeId;
    let crossDependencyInitiativeId;

    try {
      await page.send('Page.navigate', { url: `${uiBaseUrl}/initiatives/pipeline` });
      await waitFor(
        () => evalJs(page, "document.body.innerText.toLowerCase().includes('new initiative')"),
        'pipeline create action',
        20_000,
      );
      await clickText(page, 'New Initiative');
      await waitFor(
        () => evalJs(page, "location.pathname === '/initiatives/new' && document.body.innerText.toLowerCase().includes('create initiative')"),
        'initiative creation chooser',
        20_000,
      );

      await clickVisibleText(page, 'Create with Transmuter');
      await waitFor(() => evalJs(page, "document.querySelector('#init-name') !== null"), 'guided initiative form');
      const selectedTheme = await evalJs(page, `
        (() => {
          const select = document.querySelector('#init-theme');
          return [...select.options].find(option => option.value)?.value || '';
        })()
      `);
      await setField(page, '#init-name', manualInitiativeName);
      await setField(page, '#init-country', 'Singapore');
      if (selectedTheme) await setField(page, '#init-theme', selectedTheme);
      await evalJs(page, `
        (() => {
          document.querySelector('#init-type').value = 'cost_reduction';
          document.querySelector('#init-type').dispatchEvent(new Event('change', { bubbles: true }));
          document.querySelector('#init-impact').value = 'recurring';
          document.querySelector('#init-impact').dispatchEvent(new Event('change', { bubbles: true }));
          document.querySelector('#init-tag').value = 'automation';
          document.querySelector('#init-tag').dispatchEvent(new Event('change', { bubbles: true }));
          return true;
        })()
      `);
      await clickText(page, 'Next');
      await waitFor(() => evalJs(page, "document.querySelector('#init-summary') !== null"), 'guided initiative context step');
      await setField(page, '#init-summary', 'Created from real browser acceptance.');
      await setField(page, '#init-value-logic', 'Acceptance path validates the real create API through the UI.');
      await setField(page, '#init-deps', 'Seeded workstreams and users.');
      await clickText(page, 'Next');
      await waitFor(() => evalJs(page, "document.querySelector('#init-start') !== null"), 'guided initiative timeline step');
      await setField(page, '#init-start', '2026-06-01');
      await setField(page, '#init-end', '2026-09-30');
      await waitFor(
        () => evalJs(page, "!document.querySelector('button[aria-label=\"Generate initiative suggestions\"]')?.disabled"),
        'initiative suggestion button enabled',
        20_000,
      );
      await clickText(page, 'Generate Suggestions');
      try {
        await waitFor(
          () => evalJs(page, "document.body.innerText.toLowerCase().includes('hitl review') && document.body.innerText.includes('Transmuter suggestions')"),
          'guided initiative suggestions',
          45_000,
        );
      } catch (error) {
        const bodyText = await evalJs(page, "document.body.innerText");
        throw new Error(`${error.message}\nCurrent page text:\n${bodyText}`);
      }
      await evalJs(page, `
        (() => {
          const kpiInput = [...document.querySelectorAll('input[aria-label="Suggested KPI name"]')][0];
          if (!kpiInput) throw new Error('Missing suggested KPI input');
          kpiInput.value = 'UI acceptance modified KPI';
          kpiInput.dispatchEvent(new Event('input', { bubbles: true }));
          kpiInput.dispatchEvent(new Event('change', { bubbles: true }));
          const riskCheckbox = [...document.querySelectorAll('input[aria-label="Accept risk suggestion"]')][0];
          if (!riskCheckbox) throw new Error('Missing suggested risk checkbox');
          riskCheckbox.click();
          return true;
        })()
      `);
      await clickText(page, 'Create Initiative');
      await waitFor(
        () => evalJs(page, "location.pathname.startsWith('/initiatives/') && location.pathname !== '/initiatives/new'"),
        'guided initiative detail',
        25_000,
      );
      manualInitiativeId = await evalJs(page, "location.pathname.split('/').pop()");
      const manualInitiative = await api(`/initiatives/${manualInitiativeId}`);
      assert(manualInitiative.name === manualInitiativeName, 'Guided initiative was not persisted');
      if (selectedTheme) assert(manualInitiative.theme === selectedTheme, 'Guided initiative theme was not persisted');
      assert(manualInitiative.counts.kpis_total >= 3, 'Guided HITL KPIs were not persisted');
      assert(manualInitiative.counts.risks_open >= 2, 'Guided HITL risk selection was not persisted');
      assert(manualInitiative.counts.milestones_total >= 3, 'Guided HITL milestones were not persisted');
      await waitFor(
        () => evalJs(page, "!!document.querySelector('[data-testid=\"initiative-export-workbook\"]')"),
        'initiative workbook export button',
      );
      const initiativeWorkbookExport = await evalJs(page, `
        (async () => {
          const response = await fetch(${JSON.stringify(apiBaseUrl)} + '/initiatives/' + ${JSON.stringify(manualInitiativeId)} + '/export', {
            headers: { Authorization: 'Bearer ' + localStorage.getItem('access_token') },
          });
          const bytes = await response.arrayBuffer();
          return {
            ok: response.ok,
            contentType: response.headers.get('content-type'),
            size: bytes.byteLength,
          };
        })()
      `);
      assert(initiativeWorkbookExport.ok, 'Initiative workbook export should succeed');
      assert(initiativeWorkbookExport.contentType === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'Initiative workbook export should be an XLSX');
      assert(initiativeWorkbookExport.size > 1000, 'Initiative workbook export should include workbook bytes');
      let hitlKpis = await api(`/initiatives/${manualInitiativeId}/kpis`);
      assert(hitlKpis.items.some(item => item.name === 'UI acceptance modified KPI'), 'Edited HITL KPI was not persisted');
      const hitlFinancials = await api(`/initiatives/${manualInitiativeId}/financials`);
      assert(Array.isArray(hitlFinancials.values), 'HITL financial grid should expose values');
      assert(Array.isArray(hitlFinancials.metric_values), 'HITL financial grid should expose metric values');

      const overviewSummaryText = `UI acceptance overview summary ${Date.now()}`;
      const overviewContextText = `UI acceptance overview context ${Date.now()}`;
      await waitFor(
        () => evalJs(page, "document.querySelector('button[aria-label=\"Edit initiative overview\"]') !== null"),
        'overview tab content',
      );
      await evalJs(page, `
        (() => {
          document.querySelector('button[aria-label="Edit initiative overview"]').click();
          return true;
        })()
      `);
      await waitFor(() => evalJs(page, "document.body.innerText.includes('Edit Initiative Details')"), 'overview edit modal');
      await evalJs(page, `
        (() => {
          const rag = [...document.querySelectorAll('select')].find(select => [...select.options].some(option => option.value === 'amber'));
          rag.value = 'amber';
          rag.dispatchEvent(new Event('change', { bubbles: true }));
          return true;
        })()
      `);
      await setField(page, 'textarea[rows="4"]', overviewSummaryText);
      await evalJs(page, `
        (() => {
          const dateInputs = [...document.querySelectorAll('input[type="date"]')];
          dateInputs[2].value = '2026-06-15';
          dateInputs[2].dispatchEvent(new Event('input', { bubbles: true }));
          dateInputs[2].dispatchEvent(new Event('change', { bubbles: true }));
          dateInputs[3].value = '2026-10-31';
          dateInputs[3].dispatchEvent(new Event('input', { bubbles: true }));
          dateInputs[3].dispatchEvent(new Event('change', { bubbles: true }));
          const textareas = [...document.querySelectorAll('textarea')];
          textareas[textareas.length - 1].value = ${JSON.stringify(overviewContextText)};
          textareas[textareas.length - 1].dispatchEvent(new Event('input', { bubbles: true }));
          textareas[textareas.length - 1].dispatchEvent(new Event('change', { bubbles: true }));
          return true;
        })()
      `);
      await clickText(page, 'Save Changes');
      await waitFor(async () => {
        const updated = await api(`/initiatives/${manualInitiativeId}`);
        return updated.summary === overviewSummaryText
          && updated.dependencies_text === overviewContextText
          && updated.stage === manualInitiative.stage
          && updated.rag_status === 'amber';
      }, 'overview edit persistence');

      const stageGates = await api('/governance/stage-gates');
      const nextStage = stageGates.find(gate => gate.from_stage === manualInitiative.stage)?.to_stage;
      assert(nextStage, 'Tenant stage gates should expose a next stage');

      const blockedStage = await api(`/initiatives/${manualInitiativeId}`, {
        method: 'PUT',
        body: JSON.stringify({ stage: nextStage }),
        allowError: true,
      });
      assert(blockedStage.status === 400, 'Stage advancement should require an approved gate');
      assert(blockedStage.body.detail.includes('must be approved'), 'Stage gate guard should explain the missing approval');

      await clickTab(page, 'Governance');
      await waitFor(() => evalJs(page, "document.body.innerText.includes('Readiness Review')"), 'governance tab');
      await waitFor(
        () => evalJs(page, "document.querySelectorAll('input[type=\"checkbox\"]').length > 0"),
        'governance criteria checkboxes',
      );
      await evalJs(page, `
        (() => {
          const checkboxes = [...document.querySelectorAll('input[type="checkbox"]')];
          if (!checkboxes.length) throw new Error('Missing gate criteria checkboxes');
          checkboxes.forEach(checkbox => {
            if (!checkbox.checked) checkbox.click();
          });
          return true;
        })()
      `);
      await clickText(page, 'Submit for Approval');
      await waitFor(async () => {
        const status = await api(`/initiatives/${manualInitiativeId}/gates`);
        return status.active_submission?.decision === 'pending';
      }, 'governance submission persistence');
      const gateSubmissionId = await waitFor(async () => {
        const status = await api(`/initiatives/${manualInitiativeId}/gates`);
        return status.active_submission?.id;
      }, 'governance submission id');
      await evalJs(page, `
        (() => {
          const textarea = document.querySelector('textarea[placeholder^="Review comments"]');
          if (!textarea) throw new Error('Missing gate decision commentary');
          textarea.value = 'Approved by UI acceptance';
          textarea.dispatchEvent(new Event('input', { bubbles: true }));
          return true;
        })()
      `);
      await clickText(page, 'Approve');
      await waitFor(async () => {
        const detail = await api(`/initiatives/${manualInitiativeId}`);
        return detail.stage === nextStage;
      }, 'governance stage transition');
      await waitFor(async () => {
        const portfolio = await api('/portfolio/governance');
        return portfolio.submissions.some(item => item.id === gateSubmissionId && item.decision === 'approved');
      }, 'portfolio governance approval persistence');

      let teamUserId;
      let teamUserLabel;
      const summaryText = `UI acceptance final summary ${Date.now()}`;
      const lessonsText = `UI acceptance lessons ${Date.now()}`;

      await clickTab(page, 'Team');
      await waitFor(() => evalJs(page, "document.body.innerText.includes('Initiative Team')"), 'team tab');
      await evalJs(page, `
        (() => {
          const button = document.querySelector('button[aria-label="Change initiative owner"]');
          if (!button) throw new Error('Missing change owner button');
          button.click();
          return true;
        })()
      `);
      await waitFor(() => evalJs(page, "document.body.innerText.includes('Change Initiative Owner')"), 'owner assignment modal');
      await waitFor(
        () => evalJs(page, "document.querySelector('select[aria-label=\"Select owner\"]')?.options.length > 1"),
        'owner options loaded',
      );
      const teamUser = JSON.parse(await evalJs(page, `
        (() => {
          const option = document.querySelector('select[aria-label="Select owner"]').options[1];
          return JSON.stringify({ id: option.value, label: option.textContent.trim() });
        })()
      `));
      teamUserId = teamUser.id;
      teamUserLabel = teamUser.label.replace(/\s+\(.+\)$/, '');
      await evalJs(page, `
        (() => {
          const select = document.querySelector('select[aria-label="Select owner"]');
          select.selectedIndex = [...select.options].findIndex(option => option.value === ${JSON.stringify(teamUserId)});
          select.dispatchEvent(new Event('input', { bubbles: true }));
          select.dispatchEvent(new Event('change', { bubbles: true }));
          [...document.querySelectorAll('button')].find(button => button.textContent.trim() === 'Save').click();
          return true;
        })()
      `);
      await waitFor(async () => {
        const updated = await api(`/initiatives/${manualInitiativeId}`);
        return updated.owner_id === teamUserId;
      }, 'owner update persistence');
      await waitFor(
        () => evalJs(page, "!document.body.innerText.includes('Change Initiative Owner')"),
        'owner modal closed',
      );

      await clickText(page, 'Add Member');
      await waitFor(() => evalJs(page, "document.body.innerText.includes('Assign New Stakeholder')"), 'add team member modal');
      await waitFor(
        () => evalJs(page, "document.querySelector('select.input-field')?.options.length > 1"),
        'team member options loaded',
      );
      await evalJs(page, `
        (() => {
          const select = document.querySelector('select.input-field');
          select.selectedIndex = [...select.options].findIndex(option => option.value === ${JSON.stringify(teamUserId)});
          select.dispatchEvent(new Event('input', { bubbles: true }));
          select.dispatchEvent(new Event('change', { bubbles: true }));
          globalThis.__transmuterTeam.newMember.user_id = ${JSON.stringify(teamUserId)};
          [...document.querySelectorAll('button')].find(button => button.textContent.trim() === 'reviewer').click();
          globalThis.__transmuterTeam.newMember.role = 'reviewer';
          globalThis.__transmuterTeam.addMember();
          return true;
        })()
      `);
      await waitFor(async () => {
        const team = await api(`/initiatives/${manualInitiativeId}/team`);
        return team.data.some(member => member.user_id === teamUserId && member.role === 'reviewer');
      }, 'team member add persistence');
      const addedTeamMember = (await api(`/initiatives/${manualInitiativeId}/team`)).data
        .find(member => member.user_id === teamUserId && member.role === 'reviewer');
      const teamCardLabel = addedTeamMember?.display_name || teamUserLabel;
      await waitFor(
        () => evalJs(page, `
          [...document.querySelectorAll('.card')]
            .some(node => node.textContent.includes(${JSON.stringify(teamCardLabel)}) && node.textContent.toLowerCase().includes('reviewer'))
        `),
        'added team member card',
      );
      await evalJs(page, `
        (async () => {
          const label = ${JSON.stringify(teamCardLabel)};
          const card = [...document.querySelectorAll('.card')]
            .find(node => node.textContent.includes(label) && node.textContent.toLowerCase().includes('reviewer'));
          if (!card) throw new Error('Missing added team member card: ' + label);
          const remove = card.querySelector('button[aria-label="Remove team member"]');
          if (!remove) throw new Error('Missing remove team member button');
          remove.click();
          await new Promise(resolve => setTimeout(resolve, 0));
          const confirm = [...card.querySelectorAll('button')]
            .find(button => button.textContent.trim().toLowerCase() === 'remove');
          if (!confirm) throw new Error('Missing confirm remove button');
          confirm.click();
          return true;
        })()
      `);
      await waitFor(async () => {
        const team = await api(`/initiatives/${manualInitiativeId}/team`);
        return !team.data.some(member => member.user_id === teamUserId);
      }, 'team member remove persistence');

      await clickTab(page, 'Summary');
      await waitFor(() => evalJs(page, "document.body.innerText.includes('Summary & Results')"), 'summary tab');
      await evalJs(page, `
        (() => {
          const editButtons = [...document.querySelectorAll('button')]
            .filter(button => button.querySelector('.material-icons')?.textContent.trim() === 'edit');
          if (editButtons.length < 2) throw new Error('Missing summary edit controls');
          editButtons[0].click();
          return true;
        })()
      `);
      await waitFor(() => evalJs(page, "document.querySelector('textarea[placeholder^=\"Summarize\"]') !== null"), 'summary editor');
      await setField(page, 'textarea[placeholder^="Summarize"]', summaryText);
      await clickText(page, 'Save Summary');
      await waitFor(async () => {
        const summary = await api(`/initiatives/${manualInitiativeId}/summary`);
        return summary.final_summary === summaryText;
      }, 'summary persistence');

      await evalJs(page, `
        (() => {
          const editButtons = [...document.querySelectorAll('button')]
            .filter(button => button.querySelector('.material-icons')?.textContent.trim() === 'edit');
          if (!editButtons.length) throw new Error('Missing lessons edit control');
          editButtons[editButtons.length - 1].click();
          return true;
        })()
      `);
      await waitFor(() => evalJs(page, "document.querySelector('textarea[placeholder^=\"What went well\"]') !== null"), 'lessons editor');
      await setField(page, 'textarea[placeholder^="What went well"]', lessonsText);
      await clickText(page, 'Save Lessons');
      await waitFor(async () => {
        const summary = await api(`/initiatives/${manualInitiativeId}/summary`);
        return summary.lessons_learned === lessonsText;
      }, 'lessons persistence');

      const statusSummaryText = `UI acceptance status ${Date.now()}`;
      await clickTab(page, 'Status');
      await waitFor(() => evalJs(page, "document.body.innerText.includes('Status Heartbeat')"), 'status updates tab');
      await clickText(page, 'Create Update');
      await waitFor(() => evalJs(page, "document.querySelector('textarea[placeholder^=\"High-level status\"]') !== null"), 'status update editor');
      await evalJs(page, "document.querySelector('[data-testid=\"generate-status-draft\"]').click()");
      await waitFor(
        () => evalJs(page, "document.body.innerText.toLowerCase().includes('ai draft') && document.querySelector('textarea[placeholder^=\"High-level status\"]')?.value.length > 0"),
        'generated status update draft',
        20_000,
      );
      await evalJs(page, "document.querySelector('[data-testid=\"edit-status-draft\"]').click()");
      await evalJs(page, "document.querySelector('[data-testid=\"discard-status-draft\"]').click()");
      await waitFor(
        () => evalJs(page, "document.querySelector('textarea[placeholder^=\"High-level status\"]')?.value === ''"),
        'discard generated status draft',
      );
      await evalJs(page, "document.querySelector('[data-testid=\"generate-status-draft\"]').click()");
      await waitFor(
        () => evalJs(page, "document.body.innerText.toLowerCase().includes('ai draft') && document.querySelector('textarea[placeholder^=\"High-level status\"]')?.value.length > 0"),
        'regenerated status update draft',
        20_000,
      );
      await evalJs(page, "document.querySelector('[data-testid=\"accept-status-draft\"]').click()");
      await waitFor(
        () => evalJs(page, "document.querySelector('textarea[placeholder^=\"High-level status\"]') !== null"),
        'accepted generated status draft',
      );
      await setField(page, 'textarea[placeholder^="High-level status"]', statusSummaryText);
      await setField(page, 'textarea[placeholder^="What significant"]', 'Browser acceptance achievement');
      await setField(page, 'textarea[placeholder^="Any blockers"]', 'No blockers');
      await setField(page, 'textarea[placeholder^="Priorities"]', 'Verify compliance');
      await clickText(page, 'Submit Final Report');
      await waitFor(async () => {
        const updates = await api(`/initiatives/${manualInitiativeId}/status-updates`);
        return updates.items.some(item => item.summary === statusSummaryText && item.is_draft === false);
      }, 'status update submit persistence');

      const silentStatus = await api('/initiatives', {
        method: 'POST',
        body: JSON.stringify({
          name: `UI Acceptance Silent Status ${Date.now()}`,
          priority: 'medium',
          country: 'Singapore',
        }),
      });
      statusSilentInitiativeId = silentStatus.id;
      await page.send('Page.navigate', { url: `${uiBaseUrl}/progress/status-updates` });
      await waitFor(
        () => evalJs(page, "document.body.innerText.includes('Status Updates') && document.body.innerText.includes('Compliance')"),
        'status update compliance view',
      );
      await waitFor(
        () => evalJs(page, "document.querySelector('[data-testid=\"status-compliance-summary\"]') !== null && document.querySelector('[data-testid=\"status-compliance-filters\"]') !== null && document.querySelector('[data-testid=\"status-compliance-list\"]') !== null && document.body.innerText.includes('DAYS SINCE')"),
        'status compliance summary filters and days-since column',
      );
      await evalJs(page, `
        (() => {
          const filters = [...document.querySelectorAll('[data-testid="status-compliance-filters"] button')].map(button => button.textContent.trim());
          for (const label of ['All', 'Nuclear', 'Overdue', 'On Time']) {
            if (!filters.some(text => text.includes(label))) throw new Error('Missing compliance filter ' + label);
          }
          return true;
        })()
      `);
      await waitFor(
        () => evalJs(page, `document.body.innerText.includes(${JSON.stringify(silentStatus.name)})`),
        'silent status initiative compliance row',
        20_000,
      );
      await evalJs(page, `
        (() => {
          const button = [...document.querySelectorAll('[data-testid="status-compliance-filters"] button')]
            .find(node => node.textContent.includes('Nuclear'));
          if (!button) throw new Error('Missing Nuclear filter button');
          button.click();
          return true;
        })()
      `);
      await waitFor(
        () => evalJs(page, `document.querySelector('[data-testid="status-compliance-list"]')?.textContent.includes(${JSON.stringify(silentStatus.name)})`),
        'nuclear compliance filter preserves silent initiative',
      );
      await evalJs(page, `
        (() => {
          const row = [...document.querySelectorAll('tr')]
            .find(node => node.textContent.includes(${JSON.stringify(silentStatus.name)}));
          if (!row) throw new Error('Missing silent status row');
          const button = row.querySelector('button');
          if (!button) throw new Error('Missing nudge button');
          button.click();
          return true;
        })()
      `);
      await waitFor(async () => {
        const compliance = await api('/portfolio/status-updates/compliance');
        const row = compliance.initiatives.find(item => item.initiative_id === statusSilentInitiativeId);
        return row?.status === 'nuclear' && row.nudge_count >= 1;
      }, 'status compliance nudge persistence');
      await clickText(page, 'Nudge Log');
      await waitFor(
        () => evalJs(page, `document.querySelector('[data-testid="status-nudge-log"]')?.textContent.includes(${JSON.stringify(silentStatus.name)})`),
        'status nudge log row',
      );
      await page.send('Page.navigate', { url: `${uiBaseUrl}/initiatives/${manualInitiativeId}` });
      await waitFor(
        () => evalJs(page, `document.body.innerText.includes(${JSON.stringify(manualInitiativeName)})`),
        'return to initiative detail after status compliance',
      );

      const upstreamMilestoneName = `UI Acceptance Upstream ${Date.now()}`;
      const downstreamMilestoneName = `UI Acceptance Downstream ${Date.now()}`;
      const checklistText = `UI acceptance checklist ${Date.now()}`;
      await clickTab(page, 'Milestones');
      await waitFor(() => evalJs(page, "document.body.innerText.includes('Milestones')"), 'milestones tab');
      await clickText(page, 'New Milestone');
      await waitFor(() => evalJs(page, "document.body.innerText.includes('New Milestone')"), 'new milestone modal');
      await setField(page, 'input[placeholder^="e.g. Pilot"]', upstreamMilestoneName);
      await setField(page, 'textarea[placeholder^="Key outcomes"]', 'Created by browser acceptance');
      await clickText(page, 'Create Milestone');
      await waitFor(async () => {
        const list = await api(`/initiatives/${manualInitiativeId}/milestones`);
        return list.items.some(item => item.name === upstreamMilestoneName);
      }, 'upstream milestone API created');
      await waitFor(
        () => evalJs(page, `document.body.innerText.includes(${JSON.stringify(upstreamMilestoneName)})`),
        'upstream milestone created',
        30_000,
      );
      await clickText(page, 'New Milestone');
      await waitFor(() => evalJs(page, "document.body.innerText.includes('New Milestone')"), 'second milestone modal');
      await setField(page, 'input[placeholder^="e.g. Pilot"]', downstreamMilestoneName);
      await setField(page, 'textarea[placeholder^="Key outcomes"]', 'Blocked by the upstream acceptance milestone');
      await clickText(page, 'Create Milestone');
      await waitFor(async () => {
        const list = await api(`/initiatives/${manualInitiativeId}/milestones`);
        return list.items.some(item => item.name === downstreamMilestoneName);
      }, 'downstream milestone API created');
      await waitFor(
        () => evalJs(page, `document.body.innerText.includes(${JSON.stringify(downstreamMilestoneName)})`),
        'downstream milestone created',
        30_000,
      );
      let milestoneList = await api(`/initiatives/${manualInitiativeId}/milestones`);
      const upstreamMilestone = milestoneList.items.find(item => item.name === upstreamMilestoneName);
      const downstreamMilestone = milestoneList.items.find(item => item.name === downstreamMilestoneName);
      assert(upstreamMilestone && downstreamMilestone, 'Milestones were not persisted');
      await api(`/milestones/${downstreamMilestone.id}`, {
        method: 'PUT',
        body: JSON.stringify({ planned_end: '2026-08-15' }),
      });
      await evalJs(page, `
        (() => {
          const row = [...document.querySelectorAll('.card')]
            .find(node => node.textContent.includes(${JSON.stringify(downstreamMilestoneName)}));
          if (!row) throw new Error('Missing downstream milestone row');
          row.querySelector('[class*="cursor-pointer"]')?.click();
          return true;
        })()
      `);
      await waitFor(() => evalJs(page, "document.querySelector('input[aria-label=\"New checklist item\"]') !== null"), 'milestone detail expanded');
      await setField(page, 'input[aria-label="New checklist item"]', checklistText);
      await evalJs(page, `document.querySelector('button[aria-label="Add checklist item"]').click()`);
      await waitFor(async () => {
        const detail = await api(`/milestones/${downstreamMilestone.id}`);
        return detail.checklist.some(item => item.text === checklistText);
      }, 'milestone checklist persistence');
      await evalJs(page, `
        (() => {
          const select = document.querySelector('select[aria-label="Select upstream dependency"]');
          select.value = ${JSON.stringify(upstreamMilestone.id)};
          select.dispatchEvent(new Event('input', { bubbles: true }));
          select.dispatchEvent(new Event('change', { bubbles: true }));
          globalThis.__transmuterMilestones.dependencyDraft = ${JSON.stringify(upstreamMilestone.id)};
          globalThis.__transmuterMilestones.addDependency(${JSON.stringify(downstreamMilestone.id)});
          return true;
        })()
      `);
      await waitFor(async () => {
        const [detail, dependencies] = await Promise.all([
          api(`/milestones/${downstreamMilestone.id}`),
          api('/dependencies'),
        ]);
        return detail.dependencies.some(dep => dep.upstream_milestone_id === upstreamMilestone.id)
          || dependencies.edges.some(edge => edge.source === upstreamMilestone.id && edge.target === downstreamMilestone.id);
      }, 'milestone dependency persistence', 30_000);
      await page.send('Page.navigate', { url: `${uiBaseUrl}/progress/dependencies` });
      await waitFor(
        () => evalJs(page, "location.pathname === '/progress/roadmap' && document.body.innerText.includes('Roadmap Explorer') && !document.querySelector('[data-testid=\"dependency-graph\"]') && !document.querySelector('[data-testid=\"dependency-table\"]')"),
        'portfolio dependencies redirect to roadmap',
      );

      const crossDependencyInitiative = await api('/initiatives', {
        method: 'POST',
        body: JSON.stringify({
          name: `UI Acceptance Dependency Peer ${Date.now()}`,
          priority: 'medium',
          country: 'Singapore',
          planned_start: '2026-06-01',
          planned_end: '2026-09-30',
        }),
      });
      crossDependencyInitiativeId = crossDependencyInitiative.id;
      const crossUpstreamMilestone = await api(`/initiatives/${crossDependencyInitiativeId}/milestones`, {
        method: 'POST',
        body: JSON.stringify({
          name: `UI Acceptance Cross Upstream ${Date.now()}`,
          planned_end: '2026-07-15',
        }),
      });
      await page.send('Page.navigate', { url: `${uiBaseUrl}/initiatives/${manualInitiativeId}` });
      await waitFor(
        () => evalJs(page, `document.body.innerText.includes(${JSON.stringify(manualInitiativeName)})`),
        'return to initiative detail after dependencies',
      );
      await clickTab(page, 'Milestones');
      await waitFor(async () => {
        const refreshed = await api(`/initiatives/${manualInitiativeId}/milestones`);
        return refreshed.items.some(item => item.id === downstreamMilestone.id && item.name === downstreamMilestoneName);
      }, 'downstream milestone API row after return');
      try {
        await waitFor(
          () => evalJs(page, `
            [...document.querySelectorAll('.card')]
              .some(node => node.textContent.includes(${JSON.stringify(downstreamMilestoneName)}))
          `),
          'downstream milestone row after return',
          30_000,
        );
      } catch (error) {
        const milestoneTabState = await evalJs(page, `
          (() => ({
            location: location.pathname,
            cardTexts: [...document.querySelectorAll('.card')].map(node => node.textContent.trim().slice(0, 300)),
            bodyText: (document.body?.innerText || '').slice(0, 2000),
          }))()
        `);
        throw new Error(`${error.message}\nMilestones tab state:\n${JSON.stringify(milestoneTabState, null, 2)}`);
      }
      await evalJs(page, `
        (() => {
          const row = [...document.querySelectorAll('.card')]
            .find(node => node.textContent.includes(${JSON.stringify(downstreamMilestoneName)}));
          if (!row) throw new Error('Missing downstream milestone row for cross dependency');
          row.querySelector('[class*="cursor-pointer"]')?.click();
          return true;
        })()
      `);
      await waitFor(
        () => evalJs(page, `
          [...document.querySelectorAll('select[aria-label="Select upstream dependency"] option')]
            .some(option => option.value === ${JSON.stringify(crossUpstreamMilestone.id)})
        `),
        'cross-initiative dependency candidate visible',
      );
      await evalJs(page, `
        (() => {
          const select = document.querySelector('select[aria-label="Select upstream dependency"]');
          if (![...select.options].some(option => option.value === ${JSON.stringify(crossUpstreamMilestone.id)})) {
            throw new Error('Missing cross-initiative milestone candidate');
          }
          select.value = ${JSON.stringify(crossUpstreamMilestone.id)};
          select.dispatchEvent(new Event('input', { bubbles: true }));
          select.dispatchEvent(new Event('change', { bubbles: true }));
          globalThis.__transmuterMilestones.dependencyDraft = ${JSON.stringify(crossUpstreamMilestone.id)};
          globalThis.__transmuterMilestones.addDependency(${JSON.stringify(downstreamMilestone.id)});
          return true;
        })()
      `);
      await waitFor(async () => {
        const detail = await api(`/milestones/${downstreamMilestone.id}`);
        return detail.dependencies.some(dep => dep.upstream_milestone_id === crossUpstreamMilestone.id);
      }, 'cross-initiative milestone dependency persistence');
      await waitFor(async () => {
        const [milestones, dependencies] = await Promise.all([
          api('/milestones'),
          api('/dependencies'),
        ]);
        const upstreamVisible = milestones.items.some(
          item => item.id === crossUpstreamMilestone.id && item.planned_end === '2026-07-15',
        );
        const downstreamVisible = milestones.items.some(
          item => item.id === downstreamMilestone.id && item.planned_end === '2026-08-15',
        );
        const edgeVisible = dependencies.edges.some(
          edge => edge.source === crossUpstreamMilestone.id && edge.target === downstreamMilestone.id,
        );
        return upstreamVisible && downstreamVisible && edgeVisible;
      }, 'cross-initiative roadmap dependency data');
      await page.send('Page.navigate', { url: `${uiBaseUrl}/progress/roadmap` });
      try {
        await waitFor(
          () => evalJs(page, `
            (() => {
              const bodyText = document.body?.innerText || '';
              const expectedTitle = ${JSON.stringify(`${crossUpstreamMilestone.name} blocks ${downstreamMilestoneName}`)};
              return bodyText.includes('Roadmap Explorer')
                && bodyText.includes(${JSON.stringify(crossUpstreamMilestone.name)})
                && !!document.querySelector('[data-testid="roadmap-milestone-${downstreamMilestone.id}"]')
                && [...document.querySelectorAll('svg path[stroke-dasharray="3 4"] title')]
                  .some(title => title.textContent === expectedTitle);
            })()
          `),
          'roadmap dotted dependency link',
          30_000,
        );
      } catch (error) {
        const roadmapState = await evalJs(page, `
          (() => ({
            pathCount: document.querySelectorAll('svg path[stroke-dasharray="3 4"]').length,
            downstreamMarker: !!document.querySelector('[data-testid="roadmap-milestone-${downstreamMilestone.id}"]'),
            upstreamNameVisible: (document.body?.innerText || '').includes(${JSON.stringify(crossUpstreamMilestone.name)}),
            titles: [...document.querySelectorAll('svg path[stroke-dasharray="3 4"] title')].map(title => title.textContent),
            bodyText: (document.body?.innerText || '').slice(0, 2000),
          }))()
        `);
        throw new Error(`${error.message}\nRoadmap state:\n${JSON.stringify(roadmapState, null, 2)}`);
      }
      await evalJs(page, `
        (() => {
          const button = document.querySelector('[data-testid="roadmap-milestone-${downstreamMilestone.id}"]');
          if (!button) throw new Error('Missing downstream roadmap milestone marker');
          button.scrollIntoView({ block: 'center', inline: 'center' });
          button.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
          return true;
        })()
      `);
      try {
        await waitFor(
          () => evalJs(page, `
            (() => {
              const modal = document.querySelector('[data-testid="roadmap-milestone-modal"]');
              const text = modal?.innerText || '';
              const normalizedText = text.toLowerCase();
              return !!modal
                && text.includes(${JSON.stringify(downstreamMilestoneName)})
                && text.includes(${JSON.stringify(crossUpstreamMilestone.name)})
                && text.includes('Upstream Dependencies')
                && text.includes('Downstream Dependencies')
                && normalizedText.includes('previous due')
                && normalizedText.includes('next due');
            })()
          `),
          'roadmap milestone dependency modal',
          30_000,
        );
      } catch (error) {
        const modalState = await evalJs(page, `
          (() => {
            const modal = document.querySelector('[data-testid="roadmap-milestone-modal"]');
            return {
              markerExists: !!document.querySelector('[data-testid="roadmap-milestone-${downstreamMilestone.id}"]'),
              modalExists: !!modal,
              modalText: (modal?.innerText || '').slice(0, 2000),
              upstreamPanelText: (document.querySelector('[data-testid="roadmap-upstream-dependencies"]')?.innerText || '').slice(0, 1000),
              bodyText: (document.body?.innerText || '').slice(0, 2000),
            };
          })()
        `);
        throw new Error(`${error.message}\nRoadmap modal state:\n${JSON.stringify(modalState, null, 2)}`);
      }
      await evalJs(page, `document.querySelector('[data-testid="roadmap-milestone-modal"] button[aria-label="Close milestone detail"]')?.click()`);
      await setField(page, 'select.input-field', '6');
      await waitFor(
        () => evalJs(page, "document.body.innerText.includes('links hidden by timeframe') || !!document.querySelector('svg path[stroke-dasharray=\"3 4\"]')"),
        'roadmap dependency visibility after timeframe change',
      );
      await page.send('Page.navigate', { url: `${uiBaseUrl}/initiatives/${manualInitiativeId}` });
      await waitFor(
        () => evalJs(page, `document.body.innerText.includes(${JSON.stringify(manualInitiativeName)})`),
        'return to initiative detail after roadmap',
      );

      const kpiName = `UI Acceptance KPI ${Date.now()}`;
      await clickTab(page, 'KPIs');
      await waitFor(() => evalJs(page, "document.body.innerText.includes('Key Performance Indicators')"), 'kpis tab');
      await clickText(page, 'Add KPI');
      await waitFor(() => evalJs(page, "document.body.innerText.includes('New KPI Definition')"), 'new kpi modal');
      await setField(page, 'input[placeholder^="e.g. Monthly"]', kpiName);
      await setField(page, 'input[placeholder^="e.g. %"]', '%');
      await clickText(page, 'Create KPI');
      await waitFor(() => evalJs(page, `document.body.innerText.includes(${JSON.stringify(kpiName)})`), 'kpi created');
      let kpis = await api(`/initiatives/${manualInitiativeId}/kpis`);
      const kpi = kpis.items.find(item => item.name === kpiName);
      assert(kpi, 'KPI was not persisted');
      await evalJs(page, `
        (() => {
          globalThis.__transmuterKpis.entryDrafts[${JSON.stringify(kpi.id)}] = {
            year: 2030,
            quarter: 1,
            value_base: '75.0000',
            value_high: '90.0000',
            value_actual: '82.5000'
          };
          globalThis.__transmuterKpis.onSaveEntry(${JSON.stringify(kpi)});
          return true;
        })()
      `);
      await waitFor(async () => {
        kpis = await api(`/initiatives/${manualInitiativeId}/kpis`);
        const updatedKpi = kpis.items.find(item => item.id === kpi.id);
        return updatedKpi?.entries.some(entry =>
          entry.year === 2030
          && entry.quarter === 1
          && Number(entry.value_actual) === 82.5
        );
      }, 'kpi entry persistence');

      const riskDescription = `UI Acceptance Risk ${Date.now()}`;
      await clickTab(page, 'Risks');
      await waitFor(() => evalJs(page, "document.body.innerText.includes('Risk Register')"), 'risks tab');
      await clickText(page, 'Add Risk');
      await waitFor(() => evalJs(page, "document.body.innerText.includes('Register New Risk')"), 'new risk modal');
      await setField(page, 'textarea[placeholder^="What is the potential"]', riskDescription);
      await setField(page, 'textarea[placeholder^="How will we address"]', 'Browser acceptance mitigation');
      await evalJs(page, `
        (() => {
          const selects = [...document.querySelectorAll('select.input-field')];
          selects.find(select => [...select.options].some(option => option.value === 'technology')).value = 'technology';
          selects.find(select => [...select.options].some(option => option.value === 'technology')).dispatchEvent(new Event('change', { bubbles: true }));
          const impact = selects.filter(select => [...select.options].some(option => option.value === 'high'))[0];
          const likelihood = selects.filter(select => [...select.options].some(option => option.value === 'high'))[1];
          impact.value = 'high';
          likelihood.value = 'high';
          impact.dispatchEvent(new Event('change', { bubbles: true }));
          likelihood.dispatchEvent(new Event('change', { bubbles: true }));
          return true;
        })()
      `);
      await clickText(page, 'Create Risk');
      await waitFor(async () => {
        const risks = await api(`/initiatives/${manualInitiativeId}/risks`);
        return risks.items.some(item => item.description === riskDescription && item.rating === 'high');
      }, 'risk persistence');
      await evalJs(page, `
        (() => {
          const row = [...document.querySelectorAll('.card')]
            .find(node => node.textContent.includes(${JSON.stringify(riskDescription)}));
          if (!row) throw new Error('Missing risk row');
          [...row.querySelectorAll('button')].find(button => button.textContent.trim() === 'Close').click();
          return true;
        })()
      `);
      await waitFor(async () => {
        const risks = await api(`/initiatives/${manualInitiativeId}/risks`);
        return risks.items.some(item => item.description === riskDescription && item.status === 'closed');
      }, 'risk close persistence');

      await page.send('Page.navigate', { url: `${uiBaseUrl}/initiatives/new` });
      await waitFor(() => evalJs(page, "document.body.innerText.includes('Upload Excel Template')"), 'initiative upload chooser');
      await clickVisibleText(page, 'Upload Excel Template');
      await waitFor(() => evalJs(page, "document.querySelector('input[type=file][accept*=xlsx]') !== null"), 'initiative upload input');

      const initiativeWorkbook = await requestBytes(
        `${apiBaseUrl}/initiatives/template`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      const initiativeWorkbookPath = join(chromeUploadDir, `initiative-import-${Date.now()}.xlsx`);
      await writeFile(initiativeWorkbookPath, initiativeWorkbook);
      const uploadDocumentNode = await page.send('DOM.getDocument');
      const uploadInputNode = await page.send('DOM.querySelector', {
        nodeId: uploadDocumentNode.root.nodeId,
        selector: 'input[type=file][accept*=".xlsx"]',
      });
      assert(uploadInputNode.nodeId, 'Missing initiative import file input');
      await page.send('DOM.setFileInputFiles', {
        nodeId: uploadInputNode.nodeId,
        files: [initiativeWorkbookPath],
      });
      await evalJs(page, `
        (() => {
          const input = document.querySelector('input[type=file][accept*=".xlsx"]');
          input.dispatchEvent(new Event('change', { bubbles: true }));
          return true;
        })()
      `);
      await waitFor(
        () => evalJs(page, "document.body.innerText.includes('Imported Acceptance Initiative')"),
        'initiative upload preview',
        20_000,
      );
      await clickText(page, 'Upload & Create');
      await waitFor(
        () => evalJs(page, `
          location.pathname.startsWith('/initiatives/')
          && location.pathname !== '/initiatives/new'
          && document.body.innerText.includes('Imported Acceptance Initiative')
        `),
        'uploaded initiative detail',
        25_000,
      );
      uploadedInitiativeId = await evalJs(page, "location.pathname.split('/').pop()");
      const uploadedInitiative = await api(`/initiatives/${uploadedInitiativeId}`);
      assert(uploadedInitiative.name === 'Imported Acceptance Initiative', 'Uploaded initiative was not persisted');
      assert(uploadedInitiative.theme === 'Finance automation', 'Uploaded initiative theme was not persisted');
      assert(uploadedInitiative.counts.kpis_total >= 1, 'Uploaded KPI was not persisted');
      assert(uploadedInitiative.counts.risks_open >= 1, 'Uploaded risk was not persisted');
      assert(uploadedInitiative.counts.milestones_total >= 1, 'Uploaded milestone was not persisted');
      await api(`/initiatives/${uploadedInitiativeId}/financials`);
    } finally {
      if (statusSilentInitiativeId) await api(`/initiatives/${statusSilentInitiativeId}`, { method: 'DELETE' }).catch(() => null);
      if (crossDependencyInitiativeId) await api(`/initiatives/${crossDependencyInitiativeId}`, { method: 'DELETE' }).catch(() => null);
      if (uploadedInitiativeId) await api(`/initiatives/${uploadedInitiativeId}`, { method: 'DELETE' }).catch(() => null);
      if (manualInitiativeId) await api(`/initiatives/${manualInitiativeId}`, { method: 'DELETE' }).catch(() => null);
    }

    await page.send('Page.navigate', { url: `${uiBaseUrl}/meetings` });
    await waitFor(
      () => evalJs(page, "document.body.innerText.includes('Transformation Steering Committee')"),
      'seeded meetings list',
      20_000,
    );

    const meetingName = `UI Acceptance Meeting ${Date.now()}`;
    const agendaText = `UI acceptance agenda ${Date.now()}`;
    const actionText = `UI acceptance action ${Date.now()}`;
    let meetingId;
    let agendaId;
    let attendeeId;
    let linkId;
    let sessionId;
    let actionId;

    try {
      await clickText(page, 'New Series');
      await waitFor(() => evalJs(page, "document.body.innerText.includes('New meeting series')"), 'new meeting dialog');
      await waitFor(
        () => evalJs(page, "document.querySelector('select[name=owner_id] option[value]') !== null"),
        'meeting owner options loaded',
      );
      await setField(page, 'input[name=name]', meetingName);
      await setField(page, 'textarea[name=description]', 'Created from real browser acceptance');
      await clickText(page, 'Create series');
      await waitFor(
        () => evalJs(page, `location.pathname.startsWith('/meetings/') && document.body.innerText.includes(${JSON.stringify(meetingName)})`),
        'created meeting detail',
        40_000,
      );
      meetingId = await evalJs(page, "location.pathname.split('/').pop()");
      let meeting = await api(`/meetings/${meetingId}`);
      assert(meeting.name === meetingName, 'Created meeting was not persisted');

      await clickText(page, 'Edit Series');
      await waitFor(() => evalJs(page, "document.body.innerText.includes('Edit meeting series')"), 'edit meeting dialog');
      await setField(page, 'input[name=edit_name]', `${meetingName} Edited`);
      await clickText(page, 'Save changes');
      await waitFor(
        () => evalJs(page, `document.body.innerText.includes(${JSON.stringify(`${meetingName} Edited`)})`),
        'edited meeting name',
      );
      meeting = await api(`/meetings/${meetingId}`);
      assert(meeting.name === `${meetingName} Edited`, 'Edited meeting was not persisted');

      await evalJs(page, `document.querySelector('button[aria-label="Add agenda item"]').click()`);
      await setField(page, 'input[name=agenda_text]', agendaText);
      await evalJs(page, `document.querySelector('input[name=agenda_text]').closest('form').querySelector('button[type=submit]').click()`);
      await waitFor(() => evalJs(page, `document.body.innerText.includes(${JSON.stringify(agendaText)})`), 'agenda item');
      meeting = await api(`/meetings/${meetingId}`);
      const agenda = meeting.agenda.find(item => item.text === agendaText);
      assert(agenda, 'Agenda item was not persisted');
      agendaId = agenda.id;

      await evalJs(page, `document.querySelector('button[aria-label="Add attendee"]').click()`);
      await evalJs(page, `document.querySelector('select[name=selected_user]').closest('form').querySelector('button[type=submit]').click()`);
      await waitFor(async () => {
        meeting = await api(`/meetings/${meetingId}`);
        return meeting.attendees.length > 0;
      }, 'attendee persistence');
      attendeeId = meeting.attendees[0].id;

      await evalJs(page, `document.querySelector('button[aria-label="Link initiative"]').click()`);
      await evalJs(page, `document.querySelector('select[name=selected_initiative]').closest('form').querySelector('button[type=submit]').click()`);
      await waitFor(async () => {
        meeting = await api(`/meetings/${meetingId}`);
        return meeting.initiatives.length > 0;
      }, 'initiative link persistence');
      linkId = meeting.initiatives[0].id;

      await clickText(page, 'Start Session');
      await waitFor(() => evalJs(page, "document.body.innerText.includes('Choose the review date to start or resume.')"), 'start session dialog');
      await evalJs(page, `
        (() => {
          const form = document.querySelector('input[name="session_date"]')?.closest('form');
          const button = form ? [...form.querySelectorAll('button')].find(node => node.textContent.trim() === 'Start') : null;
          if (!button) throw new Error('Missing start session submit button');
          button.click();
          return true;
        })()
      `);
      await waitFor(() => evalJs(page, "location.pathname.startsWith('/meetings/sessions/')"), 'live session');
      sessionId = await evalJs(page, "location.pathname.split('/').pop()");
      await waitFor(
        () => evalJs(page, `document.querySelector('textarea[placeholder^="Capture meeting minutes"]') !== null`),
        'session notes field',
      );
      await setField(page, 'textarea[placeholder^="Capture meeting minutes"]', 'UI acceptance notes autosaved');
      await waitFor(async () => {
        const session = await api(`/meetings/sessions/${sessionId}`);
        return session.notes === 'UI acceptance notes autosaved';
      }, 'autosaved notes', 20_000);

      await setField(page, 'textarea[placeholder^="Capture a new action item"]', actionText);
      await evalJs(page, `document.querySelector('button[aria-label="Add action item"]').click()`);
      await waitFor(() => evalJs(page, `document.body.innerText.includes(${JSON.stringify(actionText)})`), 'new action item');
      let actions = await api('/action-items');
      let action = actions.items.find(item => item.description === actionText);
      assert(action, 'Action item was not persisted');
      actionId = action.id;

      await evalJs(page, `document.querySelector('button[aria-label="Toggle action item status"]').click()`);
      await waitFor(async () => {
        actions = await api('/action-items');
        action = actions.items.find(item => item.id === actionId);
        return action?.status === 'completed';
      }, 'completed action item');

      await clickText(page, 'Complete Session');
      await waitFor(() => evalJs(page, `location.pathname === ${JSON.stringify(`/meetings/${meetingId}`)}`), 'completed session navigation');
      const session = await api(`/meetings/sessions/${sessionId}`);
      assert(session.status === 'completed', 'Session was not completed');

      await page.send('Page.navigate', { url: `${uiBaseUrl}/progress/action-items` });
      await waitFor(() => evalJs(page, `document.body.innerText.includes(${JSON.stringify(actionText)})`), 'action item progress view');
      await waitFor(
        () => evalJs(page, "!!document.querySelector('[data-testid=\"action-item-stats\"]') && document.body.innerText.includes('Completed')"),
        'action item stats bar',
      );
    } finally {
      if (actionId) await api(`/action-items/${actionId}`, { method: 'DELETE' }).catch(() => null);
      if (linkId && meetingId) await api(`/meetings/${meetingId}/initiatives/${linkId}`, { method: 'DELETE' }).catch(() => null);
      if (attendeeId && meetingId) await api(`/meetings/${meetingId}/attendees/${attendeeId}`, { method: 'DELETE' }).catch(() => null);
      if (agendaId && meetingId) await api(`/meetings/${meetingId}/agenda/${agendaId}`, { method: 'DELETE' }).catch(() => null);
      if (meetingId) await api(`/meetings/${meetingId}`, { method: 'DELETE' }).catch(() => null);
    }

    const initiatives = await api('/initiatives');
    let financialInitiativeId = initiatives.items[0].id;
    for (const item of initiatives.items) {
      const candidateFinancials = await api(`/initiatives/${item.id}/financials`);
      if (!candidateFinancials.locked) {
        financialInitiativeId = item.id;
        break;
      }
    }
    const financialInitiative = await api(`/initiatives/${financialInitiativeId}`);
    const financialBefore = await api(`/initiatives/${financialInitiativeId}/financials`);
    assert(!financialBefore.locked, 'Financial UI acceptance requires an editable initiative');
    const costLinesBefore = await api(`/initiatives/${financialInitiativeId}/financials/cost-lines`);
    const financialConfig = await api('/admin/financial-configuration');
    const recurringCostCategory = financialConfig.items.find(item =>
      item.item_type === 'cost_category'
      && item.is_active !== false
      && item.rollup_type === 'recurring_cost'
    );
    if (recurringCostCategory) {
      const selections = await api(`/initiatives/${financialInitiativeId}/financials/selections`);
      const selectedMetricKeys = selections.selected?.metric_keys || selections.metric_keys || [];
      const selectedCostCategoryKeys = selections.selected?.cost_category_keys || selections.cost_category_keys || [];
      const requiredMetricKeys = [
        'revenue_uplift_base',
        'revenue_uplift_high',
        'revenue_uplift_actual',
        'gm_uplift_base',
        'gm_uplift_high',
        'gm_uplift_actual',
      ];
      await api(`/initiatives/${financialInitiativeId}/financials/selections`, {
        method: 'PUT',
        body: JSON.stringify({
          metric_keys: [...new Set([...selectedMetricKeys, ...requiredMetricKeys])],
          cost_category_keys: [...new Set([...selectedCostCategoryKeys, recurringCostCategory.key])],
        }),
      });
    }
    let costPlanRowKey = recurringCostCategory ? `cost_${recurringCostCategory.key}_plan` : 'costs_recurring_plan';
    let costActualRowKey = recurringCostCategory ? `cost_${recurringCostCategory.key}_actual` : 'costs_recurring_actual';
    const originalCostLinesById = new Map(costLinesBefore.items.map(item => [item.id, item]));
    const startParts = /^(\d{4})-(\d{2})-\d{2}/.exec(financialInitiative.planned_start || '');
    const fallbackPeriod = financialBefore.values?.find(entry => entry.month !== null)
      || financialBefore.metric_values?.find(entry => entry.month !== null)
      || financialBefore.entries?.find(entry => entry.month !== null)
      || financialBefore.values?.[0]
      || financialBefore.metric_values?.[0]
      || financialBefore.entries?.[0];
    const year = startParts ? Number(startParts[1]) : (fallbackPeriod?.year ?? 2026);
    const month = startParts ? Number(startParts[2]) : (fallbackPeriod?.month ?? 1);
    const periodColumn = `col_${year}_m${month}`;
    const uniqueFinancialSeed = Date.now() % 1000;
    const expectedRevenueUpliftBase = 123000 + uniqueFinancialSeed;
    const expectedGmUpliftActual = 35000 + uniqueFinancialSeed;
    const financialRows = [
      ...(financialBefore.entries || []),
      ...(financialBefore.metric_values || []),
      ...(financialBefore.values || []),
    ];
    const financialOriginal = financialRows.find(entry => entry.year === year && entry.month === month) ?? {
      year,
      quarter: null,
      month,
      revenue_uplift_base: '0.0000',
      revenue_uplift_high: '0.0000',
      revenue_uplift_actual: null,
      gross_margin_base: '0.0000',
      gross_margin_high: '0.0000',
      gross_margin_actual: null,
      gm_uplift_base: '0.0000',
      gm_uplift_high: '0.0000',
      gm_uplift_actual: null,
      cogs_base: '0.0000',
      cogs_high: '0.0000',
      cogs_actual: null,
    };
    let financialAssumptionId = null;
    const isTouchedGridCostLine = line =>
      line.name.endsWith(' (Grid)')
      && line.year === year
      && line.quarter === null
      && line.month === month
      && (!recurringCostCategory || line.category_key === recurringCostCategory.key);
    const restoreEntry = {
      year: financialOriginal.year,
      quarter: financialOriginal.quarter,
      month: financialOriginal.month,
      revenue_uplift_base: financialOriginal.revenue_uplift_base,
      revenue_uplift_high: financialOriginal.revenue_uplift_high,
      revenue_uplift_actual: financialOriginal.revenue_uplift_actual,
      gross_margin_base: financialOriginal.gross_margin_base,
      gross_margin_high: financialOriginal.gross_margin_high,
      gross_margin_actual: financialOriginal.gross_margin_actual,
      gm_uplift_base: financialOriginal.gm_uplift_base,
      gm_uplift_high: financialOriginal.gm_uplift_high,
      gm_uplift_actual: financialOriginal.gm_uplift_actual,
      cogs_base: financialOriginal.cogs_base,
      cogs_high: financialOriginal.cogs_high,
      cogs_actual: financialOriginal.cogs_actual,
    };
    const metricValueRestores = [];
    let assumptionRowKey = 'gm_uplift_base';
    const scenarioDefinitionForUi = scenario => {
      const scenarios = (financialBefore.scenarios || []).filter(item => item.is_active !== false);
      const preferredKeys = {
        base: ['plan_base', 'base'],
        high: ['plan_high', 'high'],
        actual: ['actual'],
      }[scenario] || [];
      return scenarios.find(item => preferredKeys.includes(item.key))
        || (scenario === 'base' ? scenarios.find(item => item.kind === 'plan' && item.is_primary) : null)
        || scenarios.find(item => item.kind === (scenario === 'actual' ? 'actual' : 'plan'))
        || scenarios[0]
        || null;
    };
    const highScenarioDefinition = scenarioDefinitionForUi('high');
    const actualScenarioDefinition = scenarioDefinitionForUi('actual');
    assert(highScenarioDefinition && actualScenarioDefinition, 'Configurable financial scenarios were not available for browser acceptance');
    const enrichMetricRow = row => {
      if (!row || row.source !== 'metric_value') return row;
      if (row.metricDefinitionId && row.scenarioId && row.metricValueKey) return row;
      for (const definition of financialBefore.definitions || []) {
        for (const scenario of financialBefore.scenarios || []) {
          const prefix = `metric_${definition.id}_${scenario.id}_`;
          if (!row.key?.startsWith(prefix)) continue;
          const rawBenefitLineId = row.key.slice(prefix.length);
          return {
            ...row,
            metricDefinitionId: definition.id,
            scenarioId: scenario.id,
            metricValueKey: definition.key,
            metricScenario: row.metricScenario,
            benefitLineId: rawBenefitLineId && rawBenefitLineId !== 'default' ? rawBenefitLineId : null,
          };
        }
      }
      return row;
    };
    const pickMetricRow = (rows, preferredKeys, fallbackText, scenarioId = null) => {
      const enrichedRows = rows.map(enrichMetricRow)
        .filter(row => !scenarioId || row.scenarioId === scenarioId);
      return preferredKeys.map(key => enrichedRows.find(row => row.metricValueKey === key)).find(Boolean)
        || enrichedRows.find(row => row.metricValueKey && row.metricValueKey.includes(fallbackText))
        || enrichedRows[0]
        || null;
    };
    const restoreValueForMetricRow = row => {
      if (!row?.metricDefinitionId || !row?.scenarioId) return null;
      const original = (financialBefore.values || []).find(value =>
        value.metric_definition_id === row.metricDefinitionId
        && value.scenario_id === row.scenarioId
        && (value.benefit_line_id || null) === (row.benefitLineId || null)
        && value.year === year
        && value.month === month
      );
      return {
        metric_definition_id: row.metricDefinitionId,
        scenario_id: row.scenarioId,
        benefit_line_id: row.benefitLineId || null,
        year,
        month,
        value: original?.value ?? '0',
        status: original?.status ?? 'draft',
        note: original?.note ?? null,
      };
    };

    try {
      await page.send('Page.navigate', { url: `${uiBaseUrl}/initiatives/${financialInitiativeId}` });
      await waitFor(() => evalJs(page, "document.body.innerText.includes('Financials')"), 'initiative detail tabs');
      await clickTab(page, 'Financials');
      await waitFor(() => evalJs(page, "document.body.innerText.includes('Initiative Financials')"), 'financials tab');
      await clickText(page, 'Edit Details');
      await waitFor(() => evalJs(page, "!!globalThis.__transmuterFinancials"), 'financial grid harness');
      if (recurringCostCategory) {
        await waitFor(
          () => evalJs(page, `
            globalThis.__transmuterFinancials.rows().some(row =>
              row.costCategoryKey === ${JSON.stringify(recurringCostCategory.key)}
              && row.isRecurring === true
              && row.actual === true
            )
          `),
          'configured recurring cost category rows',
        );
      }
      await waitFor(
        () => evalJs(page, `
          globalThis.__transmuterFinancials.hasColumn(${JSON.stringify(periodColumn)})
            && !globalThis.__transmuterFinancials.columns().some(column => /^col_\\d+_q\\d+$/.test(column))
        `),
        'monthly-only financial edit columns',
      );
      const gridCostRows = await evalJs(page, `
        globalThis.__transmuterFinancials.rows()
          .filter(row => row.source === 'cost_line' || row.key.startsWith('costs_'))
      `);
      const planCostRow = gridCostRows.find(row => row.key === costPlanRowKey)
        || gridCostRows.find(row => row.costCategoryKey === recurringCostCategory?.key && row.actual === false)
        || gridCostRows.find(row => row.isRecurring === true && row.actual === false)
        || gridCostRows.find(row => row.key.includes('plan'));
      const actualCostRow = gridCostRows.find(row => row.key === costActualRowKey)
        || gridCostRows.find(row => row.costCategoryKey === recurringCostCategory?.key && row.actual === true)
        || gridCostRows.find(row => row.isRecurring === true && row.actual === true)
        || gridCostRows.find(row => row.key.includes('actual'));
      assert(planCostRow && actualCostRow, 'Financial cost category rows were not available in the initiative grid');
      costPlanRowKey = planCostRow.key;
      costActualRowKey = actualCostRow.key;
      await evalJs(page, "globalThis.__transmuterFinancials.setScenario('high')");
      await waitFor(
        () => evalJs(page, `
          document.body.innerText.includes('High')
            && !document.querySelector('[data-testid="financial-break-even-chart"]')
            && globalThis.__transmuterFinancials.rows().some(row =>
              row.source === 'metric_value'
              && row.readOnly !== true
              && ${JSON.stringify(highScenarioDefinition?.id || '')}
              && row.key.includes(${JSON.stringify(`_${highScenarioDefinition?.id || ''}_`)})
            )
        `),
        'financial scenario UI without break-even chart',
      );
      const highMetricRows = await evalJs(page, `
        globalThis.__transmuterFinancials.rows()
          .filter(row => row.source === 'metric_value' && row.readOnly !== true)
      `);
      const highMetricRow = pickMetricRow(highMetricRows, ['revenue_uplift'], 'revenue', highScenarioDefinition?.id || null);
      assert(highMetricRow, 'No editable configurable metric row was available for the high scenario');
      const highMetricRestore = restoreValueForMetricRow(highMetricRow);
      if (highMetricRestore) metricValueRestores.push(highMetricRestore);
      assumptionRowKey = highMetricRow.key;
      await evalJs(page, `
        (() => {
          globalThis.__transmuterFinancials.setCell(${JSON.stringify(highMetricRow.key)}, ${JSON.stringify(periodColumn)}, ${expectedRevenueUpliftBase});
          return true;
        })()
      `);
      await evalJs(page, "globalThis.__transmuterFinancials.setScenario('actual')");
      await waitFor(
        () => evalJs(page, `
          document.body.innerText.includes('Actuals')
          && globalThis.__transmuterFinancials.rows().some(row =>
            row.source === 'metric_value'
            && row.readOnly !== true
            && ${JSON.stringify(actualScenarioDefinition?.id || '')}
            && row.key.includes(${JSON.stringify(`_${actualScenarioDefinition?.id || ''}_`)})
          )
        `),
        'actual scenario configurable metric rows',
      );
      const actualMetricRows = await evalJs(page, `
        globalThis.__transmuterFinancials.rows()
          .filter(row => row.source === 'metric_value' && row.readOnly !== true)
      `);
      const actualMetricRow = pickMetricRow(actualMetricRows, ['gm_uplift'], 'margin', actualScenarioDefinition?.id || null);
      assert(actualMetricRow, 'No editable configurable metric row was available for the actual scenario');
      const actualMetricRestore = restoreValueForMetricRow(actualMetricRow);
      if (actualMetricRestore) metricValueRestores.push(actualMetricRestore);
      const currentGridCostRows = await evalJs(page, `
        globalThis.__transmuterFinancials.rows()
          .filter(row => row.source === 'cost_line' || row.key.startsWith('costs_'))
      `);
      const currentPlanCostRow = currentGridCostRows.find(row => row.key === costPlanRowKey)
        || currentGridCostRows.find(row => row.costCategoryKey === recurringCostCategory?.key && row.actual === false)
        || currentGridCostRows.find(row => row.isRecurring === true && row.actual === false)
        || null;
      const currentActualCostRow = currentGridCostRows.find(row => row.key === costActualRowKey)
        || currentGridCostRows.find(row => row.costCategoryKey === recurringCostCategory?.key && row.actual === true)
        || currentGridCostRows.find(row => row.isRecurring === true && row.actual === true)
        || currentGridCostRows.find(row => row.key.includes('actual'));
      assert(currentActualCostRow, 'Financial actual cost row was not available in the active scenario grid');
      costActualRowKey = currentActualCostRow.key;
      if (currentPlanCostRow) costPlanRowKey = currentPlanCostRow.key;
      await evalJs(page, `
        (() => {
          globalThis.__transmuterFinancials.setCell(${JSON.stringify(actualMetricRow.key)}, ${JSON.stringify(periodColumn)}, ${expectedGmUpliftActual});
          const planCostRowKey = ${JSON.stringify(currentPlanCostRow?.key || null)};
          if (planCostRowKey) globalThis.__transmuterFinancials.setCell(planCostRowKey, ${JSON.stringify(periodColumn)}, 1250);
          globalThis.__transmuterFinancials.setCell(${JSON.stringify(costActualRowKey)}, ${JSON.stringify(periodColumn)}, 1000);
          globalThis.__transmuterFinancials.save();
          return true;
        })()
      `);
      await waitFor(() => evalJs(page, "!document.body.innerText.includes('Saving...')"), 'financial save completion', 25_000);
      try {
        await waitFor(async () => {
          const bridge = await api(`/initiatives/${financialInitiativeId}/financials/value-bridge`);
          return Number(bridge.actual.costs_recurring) >= 1000;
        }, 'financial recurring actual value bridge', 25_000);
      } catch (error) {
        const [bridge, lines] = await Promise.all([
          api(`/initiatives/${financialInitiativeId}/financials/value-bridge`).catch(() => null),
          api(`/initiatives/${financialInitiativeId}/financials/cost-lines`).catch(() => ({ items: [] })),
        ]);
        const matchingLines = lines.items.filter(line =>
          line.year === year
          && line.month === month
          && line.is_recurring === true
          && (!recurringCostCategory || line.category_key === recurringCostCategory.key)
        );
        throw new Error(
          `${error.message}. Bridge actual=${JSON.stringify(bridge?.actual || null)}; matching recurring lines=${JSON.stringify(matchingLines)}`,
        );
      }
      const scenarioSummary = await api(`/initiatives/${financialInitiativeId}/financials/scenario-summary?scenario=high`);
      assert(scenarioSummary.scenario === 'high' && Number.isFinite(Number(scenarioSummary.gm_uplift)), 'High scenario summary was not returned');
      const assumptionText = `UI acceptance assumption ${Date.now()}`;
      await evalJs(page, `
        (() => {
          globalThis.__transmuterFinancials.setAssumption(${JSON.stringify(assumptionRowKey)}, ${JSON.stringify(periodColumn)}, ${JSON.stringify(assumptionText)});
          return true;
        })()
      `);
      await waitFor(async () => {
        const assumptions = await api(`/initiatives/${financialInitiativeId}/financials/assumptions`);
        const found = assumptions.items.find(item => item.comment === assumptionText);
        if (found) financialAssumptionId = found.id;
        return !!found;
      }, 'financial cell assumption persisted through UI', 20_000);
      await waitFor(
        () => evalJs(page, `document.body.innerText.includes(${JSON.stringify(assumptionText)})`),
        'financial cell assumption visible',
      );

      await evalJs(page, `
        (() => {
          const originalCreateObjectUrl = URL.createObjectURL.bind(URL);
          URL.createObjectURL = blob => {
            globalThis.__lastFinancialExportSize = blob.size;
            return originalCreateObjectUrl(blob);
          };
          return true;
        })()
      `);
      await evalJs(page, `
        (() => {
          const button = document.querySelector('button[aria-label="Export financial workbook"]');
          if (!button) throw new Error('Missing financial export button');
          button.click();
          return true;
        })()
      `);
      await waitFor(
        () => evalJs(page, "Number(globalThis.__lastFinancialExportSize || 0) > 1000"),
        'financial workbook export download',
        15_000,
      );

      const workbook = await requestBytes(
        `${apiBaseUrl}/initiatives/${financialInitiativeId}/financials/export.xlsx`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      const workbookPath = join(chromeUploadDir, `financials-import-${Date.now()}.xlsx`);
      await writeFile(workbookPath, workbook);
      const documentNode = await page.send('DOM.getDocument');
      const inputNode = await page.send('DOM.querySelector', {
        nodeId: documentNode.root.nodeId,
        selector: 'input[type=file][accept*=".xlsx"]',
      });
      assert(inputNode.nodeId, 'Missing financial import file input');
      await page.send('DOM.setFileInputFiles', {
        nodeId: inputNode.nodeId,
        files: [workbookPath],
      });
      await evalJs(page, `
        (() => {
          const input = document.querySelector('input[type=file][accept*=".xlsx"]');
          input.dispatchEvent(new Event('change', { bubbles: true }));
          return true;
        })()
      `);
      await waitFor(
        () => evalJs(page, "!globalThis.__transmuterFinancials.component.importing()"),
        'financial workbook import completion',
        20_000,
      );
    } finally {
      if (financialAssumptionId) {
        await api(`/initiatives/${financialInitiativeId}/financials/assumptions/${financialAssumptionId}`, { method: 'DELETE' }).catch(() => null);
      }
      await api(`/initiatives/${financialInitiativeId}/financials`, {
        method: 'PUT',
        body: JSON.stringify({ entries: [restoreEntry], values: metricValueRestores, cost_lines: [] }),
      }).catch(() => null);

      const currentCostLines = await api(`/initiatives/${financialInitiativeId}/financials/cost-lines`).catch(() => ({ items: [] }));
      await Promise.all(currentCostLines.items
        .filter(isTouchedGridCostLine)
        .map(line => {
          const original = originalCostLinesById.get(line.id);
          if (!original) {
            return api(`/initiatives/${financialInitiativeId}/financials/cost-lines/${line.id}`, { method: 'DELETE' }).catch(() => null);
          }
          return api(`/initiatives/${financialInitiativeId}/financials/cost-lines/${line.id}`, {
            method: 'PUT',
            body: JSON.stringify({
              name: original.name,
              year: original.year,
              quarter: original.quarter,
              month: original.month,
              amount_plan: original.amount_plan,
              amount_actual: original.amount_actual,
              is_recurring: original.is_recurring,
              category_key: original.category_key,
            }),
          }).catch(() => null);
        }));
    }

    await page.close();
    console.log('Real browser acceptance passed: login, dashboard, people directory/profile/invite, initiative create/import, overview edit, team owner/member flow, summary results persistence, milestones/checklist/dependencies, KPI entry save, risk create/close, meetings flow, financial grid save/reload, scenario toggle, cell assumptions, Excel export/import, and value bridge.');
  } finally {
    chrome.kill('SIGTERM');
    await new Promise(resolve => {
      chrome.once('exit', resolve);
      setTimeout(resolve, 1500);
    });
    await rm(userDataDir, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
  }
}

main().catch(error => {
  console.error(error);
  process.exit(1);
});
