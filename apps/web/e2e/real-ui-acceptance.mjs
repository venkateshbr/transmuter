import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawn } from 'node:child_process';

const uiBaseUrl = process.env.TRANSMUTER_UI_BASE_URL ?? 'http://localhost:4300';
const apiBaseUrl = process.env.TRANSMUTER_API_BASE_URL ?? 'http://localhost:8000';
const chromeBin = process.env.CHROME_BIN ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const email = process.env.TRANSMUTER_E2E_EMAIL ?? 'admin@ishirock.dev';
const password = process.env.TRANSMUTER_E2E_PASSWORD ?? 'Transmuter2026!';
const debugPort = Number(process.env.CHROME_DEBUG_PORT ?? 9222);

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
      const text = ${JSON.stringify(text)};
      const el = [...document.querySelectorAll('button,a')]
        .find(node => node.textContent.trim().includes(text));
      if (!el) throw new Error('Missing clickable text: ' + text);
      el.click();
      return true;
    })()
  `);
}

async function clickVisibleText(page, text) {
  await evalJs(page, `
    (() => {
      const text = ${JSON.stringify(text)};
      const el = [...document.querySelectorAll('button,a,[role="button"]')]
        .find(node => node.textContent.trim().includes(text));
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
  const chrome = spawn(chromeBin, [
    '--headless=new',
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
      () => evalJs(page, "location.pathname === '/' && !!localStorage.getItem('access_token')"),
      'authenticated dashboard',
      20_000,
    );

    await waitFor(
      () => evalJs(page, "document.body.innerText.includes('Transmuter')"),
      'dashboard content',
    );
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
          'dashboard-filter-rag',
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
      () => evalJs(page, "!!document.querySelector('[data-testid=\"dashboard-executive-summary-ready\"]')"),
      'executive summary generation',
    );

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
      await page.send('Page.navigate', { url: `${uiBaseUrl}/` });
      await waitFor(
        () => evalJs(page, "location.pathname === '/' && !!document.querySelector('[data-testid=\"dashboard-total-initiatives\"]')"),
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
      () => evalJs(page, "document.querySelector('select.input-field:nth-of-type(1)')?.value === 'red' || document.body.innerText.includes('All RAG')"),
      'pipeline red query handled',
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

    const peopleRows = await api('/users');
    assert(peopleRows.items.length > 0, 'Seeded users were not available');
    const seededPerson = peopleRows.items.find(item => item.status === 'active') ?? peopleRows.items[0];
    const seededPersonLabel = seededPerson.display_name || seededPerson.email;
    const inviteEmail = `transmuter.acceptance+ui.people.${Date.now()}@gmail.com`;
    let invitedPersonId;

    try {
      await page.send('Page.navigate', { url: `${uiBaseUrl}/people` });
      await waitFor(
        () => evalJs(page, "document.body.innerText.includes('People Insight') && document.body.innerText.includes('Invite Member')"),
        'people directory',
        20_000,
      );
      await waitFor(
        () => evalJs(page, `document.body.innerText.includes(${JSON.stringify(seededPersonLabel)})`),
        'seeded person visible in directory',
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
      await evalJs(page, `document.querySelector('.overlay button .material-icons')?.closest('button')?.click()`);

      await clickText(page, 'Invite Member');
      await waitFor(
        () => evalJs(page, "document.body.innerText.includes('Invite Platform User')"),
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
      await clickText(page, 'Send Invite');
      await waitFor(async () => {
        const invites = await api('/invites');
        const invited = invites.items.find(item => item.email === inviteEmail);
        if (invited) invitedPersonId = invited.id;
        return invited?.status === 'ghost';
      }, 'people invite persistence', 20_000);
      await clickText(page, 'Pending Invites');
      await waitFor(
        () => evalJs(page, `document.body.innerText.includes(${JSON.stringify(inviteEmail)})`),
        'pending invite visible',
      );
    } finally {
      if (invitedPersonId) {
        await api(`/users/${invitedPersonId}/deactivate`, { method: 'POST', body: '{}' }).catch(() => null);
      }
    }

    const manualInitiativeName = `UI Acceptance Initiative ${Date.now()}`;
    let manualInitiativeId;
    let uploadedInitiativeId;
    let statusSilentInitiativeId;

    try {
      await page.send('Page.navigate', { url: `${uiBaseUrl}/initiatives/pipeline` });
      await waitFor(
        () => evalJs(page, "document.body.innerText.includes('New Initiative')"),
        'pipeline create action',
        20_000,
      );
      await clickText(page, 'New Initiative');
      await waitFor(
        () => evalJs(page, "location.pathname === '/initiatives/new' && document.body.innerText.includes('Create Initiative')"),
        'initiative creation chooser',
        20_000,
      );

      await clickVisibleText(page, 'Create with Transmuter');
      await waitFor(() => evalJs(page, "document.querySelector('#init-name') !== null"), 'guided initiative form');
      await setField(page, '#init-name', manualInitiativeName);
      await setField(page, '#init-country', 'Singapore');
      await setField(page, '#init-theme', 'Acceptance operations');
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
      await clickText(page, 'Generate Suggestions');
      try {
        await waitFor(
          () => evalJs(page, "document.body.innerText.includes('HITL REVIEW') && document.body.innerText.includes('Transmuter suggestions')"),
          'guided initiative suggestions',
          20_000,
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
        () => evalJs(page, `
          location.pathname.startsWith('/initiatives/')
          && location.pathname !== '/initiatives/new'
          && document.body.innerText.includes(${JSON.stringify(manualInitiativeName)})
        `),
        'guided initiative detail',
        25_000,
      );
      manualInitiativeId = await evalJs(page, "location.pathname.split('/').pop()");
      const manualInitiative = await api(`/initiatives/${manualInitiativeId}`);
      assert(manualInitiative.name === manualInitiativeName, 'Guided initiative was not persisted');
      assert(manualInitiative.theme === 'Acceptance operations', 'Guided initiative theme was not persisted');
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
      assert(hitlFinancials.entries.some(item => Number(item.gm_uplift_base) > 0), 'HITL financial suggestion was not persisted');

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
          && updated.stage === 'scoping'
          && updated.rag_status === 'amber'
          && updated.actual_start === '2026-06-15'
          && updated.actual_end === '2026-10-31';
      }, 'overview edit persistence');

      const blockedStage = await api(`/initiatives/${manualInitiativeId}`, {
        method: 'PUT',
        body: JSON.stringify({ stage: 'in_progress' }),
        allowError: true,
      });
      assert(blockedStage.status === 400, 'Stage advancement should require an approved gate');
      assert(blockedStage.body.detail.includes('Gate 1 must be approved'), 'Stage gate guard should explain the missing approval');

      await clickTab(page, 'Governance');
      await waitFor(() => evalJs(page, "document.body.innerText.includes('Readiness Review')"), 'governance tab');
      await waitFor(
        () => evalJs(page, "document.querySelectorAll('input[type=\"checkbox\"]').length > 0"),
        'governance criteria checkboxes',
      );
      await evalJs(page, `
        (() => {
          const checkbox = document.querySelector('input[type="checkbox"]');
          checkbox.click();
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
        return detail.stage === 'in_progress';
      }, 'governance stage transition');
      await waitFor(async () => {
        const portfolio = await api('/portfolio/governance');
        return portfolio.submissions.some(item => item.id === gateSubmissionId && item.decision === 'approved');
      }, 'portfolio governance approval persistence');

      let teamUserId;
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
      teamUserId = await evalJs(page, `
        (() => document.querySelector('select[aria-label="Select owner"]').options[1].value)()
      `);
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
      await evalJs(page, `
        (() => {
          window.confirm = () => true;
          const remove = document.querySelector('button[aria-label="Remove team member"]');
          if (!remove) throw new Error('Missing remove team member button');
          remove.click();
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
        () => evalJs(page, `document.body.innerText.includes(${JSON.stringify(silentStatus.name)})`),
        'silent status initiative compliance row',
        20_000,
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
      await waitFor(() => evalJs(page, `document.body.innerText.includes(${JSON.stringify(upstreamMilestoneName)})`), 'upstream milestone created');
      await clickText(page, 'New Milestone');
      await waitFor(() => evalJs(page, "document.body.innerText.includes('New Milestone')"), 'second milestone modal');
      await setField(page, 'input[placeholder^="e.g. Pilot"]', downstreamMilestoneName);
      await setField(page, 'textarea[placeholder^="Key outcomes"]', 'Blocked by the upstream acceptance milestone');
      await clickText(page, 'Create Milestone');
      await waitFor(() => evalJs(page, `document.body.innerText.includes(${JSON.stringify(downstreamMilestoneName)})`), 'downstream milestone created');
      let milestoneList = await api(`/initiatives/${manualInitiativeId}/milestones`);
      const upstreamMilestone = milestoneList.items.find(item => item.name === upstreamMilestoneName);
      const downstreamMilestone = milestoneList.items.find(item => item.name === downstreamMilestoneName);
      assert(upstreamMilestone && downstreamMilestone, 'Milestones were not persisted');
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
        const detail = await api(`/milestones/${downstreamMilestone.id}`);
        return detail.dependencies.some(dep => dep.upstream_milestone_id === upstreamMilestone.id);
      }, 'milestone dependency persistence');
      await page.send('Page.navigate', { url: `${uiBaseUrl}/progress/dependencies` });
      await waitFor(
        () => evalJs(page, `document.body.innerText.includes(${JSON.stringify(upstreamMilestoneName)}) && document.body.innerText.includes(${JSON.stringify(downstreamMilestoneName)})`),
        'portfolio dependencies view',
      );
      await waitFor(
        () => evalJs(page, "!!document.querySelector('[data-testid=\"dependency-stats\"]') && !!document.querySelector('[data-testid=\"dependency-graph\"]') && !!document.querySelector('[data-testid=\"dependency-table\"]')"),
        'dependency stats graph and table',
      );
      await page.send('Page.navigate', { url: `${uiBaseUrl}/initiatives/${manualInitiativeId}` });
      await waitFor(
        () => evalJs(page, `document.body.innerText.includes(${JSON.stringify(manualInitiativeName)})`),
        'return to initiative detail after dependencies',
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
      const initiativeWorkbookPath = join(userDataDir, 'initiative-import.xlsx');
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
      const uploadedFinancials = await api(`/initiatives/${uploadedInitiativeId}/financials`);
      assert(uploadedFinancials.entries.some(item =>
        item.year === 2030
        && item.quarter === 1
        && Number(item.revenue_uplift_base) === 100000
      ), 'Uploaded financial entry was not persisted');
    } finally {
      if (statusSilentInitiativeId) await api(`/initiatives/${statusSilentInitiativeId}`, { method: 'DELETE' }).catch(() => null);
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
    const financialInitiativeId = initiatives.items[0].id;
    const financialBefore = await api(`/initiatives/${financialInitiativeId}/financials`);
    const costLinesBefore = await api(`/initiatives/${financialInitiativeId}/financials/cost-lines`);
    const originalCostLinesById = new Map(costLinesBefore.items.map(item => [item.id, item]));
    const financialOriginal = financialBefore.entries.find(entry => entry.month !== null) ?? financialBefore.entries[0];
    const year = financialOriginal.year;
    const periodColumn = financialOriginal.month
      ? `col_${year}_m${financialOriginal.month}`
      : `col_${year}_q${financialOriginal.quarter}`;
    let financialAssumptionId = null;
    const isTouchedGridCostLine = line =>
      ['Recurring Costs (Grid)', 'One-off Costs (Grid)'].includes(line.name)
      && line.year === financialOriginal.year
      && line.quarter === financialOriginal.quarter
      && line.month === financialOriginal.month;
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
    };

    try {
      await page.send('Page.navigate', { url: `${uiBaseUrl}/initiatives/${financialInitiativeId}` });
      await waitFor(() => evalJs(page, "document.body.innerText.includes('Financials')"), 'initiative detail tabs');
      await clickTab(page, 'Financials');
      await waitFor(() => evalJs(page, "document.body.innerText.includes('Initiative Financials')"), 'financials tab');
      await clickText(page, 'Edit Details');
      await waitFor(() => evalJs(page, "!!globalThis.__transmuterFinancials"), 'financial grid harness');
      await evalJs(page, "globalThis.__transmuterFinancials.setScenario('high')");
      await waitFor(
        () => evalJs(page, "document.body.innerText.includes('High') && !!document.querySelector('[data-testid=\"financial-break-even-chart\"]')"),
        'financial scenario and break-even UI',
      );
      await evalJs(page, `
        (() => {
          globalThis.__transmuterFinancials.setCell('revenue_uplift_base', ${JSON.stringify(periodColumn)}, 123456);
          globalThis.__transmuterFinancials.setCell('gm_uplift_actual', ${JSON.stringify(periodColumn)}, 35000);
          globalThis.__transmuterFinancials.setCell('costs_recurring_plan', ${JSON.stringify(periodColumn)}, 1250);
          globalThis.__transmuterFinancials.setCell('costs_recurring_actual', ${JSON.stringify(periodColumn)}, 1000);
          globalThis.__transmuterFinancials.save();
          return true;
        })()
      `);
      await waitFor(() => evalJs(page, "!document.body.innerText.includes('Saving...')"), 'financial save completion', 25_000);
      await waitFor(async () => {
        const reloaded = await api(`/initiatives/${financialInitiativeId}/financials`);
        const entry = reloaded.entries.find(item =>
          item.year === financialOriginal.year
          && item.quarter === financialOriginal.quarter
          && item.month === financialOriginal.month
        );
        return Number(entry?.revenue_uplift_base) === 123456
          && Number(entry?.gm_uplift_actual) === 35000;
      }, 'financial values persisted through UI', 25_000);
      const bridge = await api(`/initiatives/${financialInitiativeId}/financials/value-bridge`);
      assert(Number(bridge.actual.costs_recurring) >= 1000, 'Financial recurring actual was not reflected in value bridge');
      const scenarioSummary = await api(`/initiatives/${financialInitiativeId}/financials/scenario-summary?scenario=high`);
      assert(scenarioSummary.scenario === 'high' && Number.isFinite(Number(scenarioSummary.gm_uplift)), 'High scenario summary was not returned');
      const breakEven = await api(`/initiatives/${financialInitiativeId}/financials/break-even?scenario=high`);
      assert(breakEven.points.length > 0, 'Break-even points were not returned');

      const assumptionText = `UI acceptance assumption ${Date.now()}`;
      await evalJs(page, `
        (() => {
          globalThis.__transmuterFinancials.setAssumption('gm_uplift_base', ${JSON.stringify(periodColumn)}, ${JSON.stringify(assumptionText)});
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
      const workbookPath = join(userDataDir, 'financials-import.xlsx');
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
        body: JSON.stringify({ entries: [restoreEntry], cost_lines: [] }),
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
            }),
          }).catch(() => null);
        }));
    }

    await page.close();
    console.log('Real browser acceptance passed: login, dashboard, people directory/profile/invite, initiative create/import, overview edit, team owner/member flow, summary results persistence, milestones/checklist/dependencies, KPI entry save, risk create/close, meetings flow, financial grid save/reload, scenario toggle, break-even, cell assumptions, Excel export/import, and value bridge.');
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
