import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawn } from 'node:child_process';

const uiBaseUrl = (process.env.TRANSMUTER_UI_BASE_URL ?? 'https://transmuter-dev.ishirock.tech').replace(/\/$/, '');
const apiBaseUrl = (process.env.TRANSMUTER_API_BASE_URL ?? `${uiBaseUrl}/api`).replace(/\/$/, '');
const chromeBin = process.env.CHROME_BIN ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const debugPort = Number(process.env.CHROME_DEBUG_PORT ?? 9224);
const emailDomain = process.env.TRANSMUTER_RBAC_EMAIL_DOMAIN ?? 'acme-transformation.dev';
const password = process.env.TRANSMUTER_RBAC_SAMPLE_PASSWORD ?? 'Transmuter2026!';

const roles = [
  'transformation_office',
  'tenant_admin',
  'pmo_lead',
  'finance_lead',
  'workstream_lead',
  'initiative_owner',
  'business_benefit_owner',
  'executive_sponsor',
  'viewer',
];

const expectations = {
  transformation_office: {
    peopleNav: true,
    adminNav: true,
    routes: {
      '/people': true,
      '/admin': true,
      '/shared-costs': true,
      '/initiatives/new': true,
    },
  },
  tenant_admin: {
    peopleNav: true,
    adminNav: true,
    routes: {
      '/people': true,
      '/admin': true,
      '/shared-costs': false,
      '/initiatives/new': false,
    },
  },
  pmo_lead: {
    peopleNav: false,
    adminNav: true,
    routes: {
      '/people': false,
      '/admin': true,
      '/shared-costs': false,
      '/initiatives/new': false,
    },
  },
  finance_lead: {
    peopleNav: false,
    adminNav: true,
    routes: {
      '/people': false,
      '/admin': true,
      '/shared-costs': true,
      '/initiatives/new': false,
    },
  },
  workstream_lead: {
    peopleNav: false,
    adminNav: false,
    routes: {
      '/people': false,
      '/admin': false,
      '/shared-costs': false,
      '/initiatives/new': false,
    },
  },
  initiative_owner: {
    peopleNav: false,
    adminNav: false,
    routes: {
      '/people': false,
      '/admin': false,
      '/shared-costs': false,
      '/initiatives/new': false,
    },
  },
  business_benefit_owner: {
    peopleNav: false,
    adminNav: false,
    routes: {
      '/people': false,
      '/admin': false,
      '/shared-costs': false,
      '/initiatives/new': false,
    },
  },
  executive_sponsor: {
    peopleNav: false,
    adminNav: false,
    routes: {
      '/people': false,
      '/admin': false,
      '/shared-costs': false,
      '/initiatives/new': false,
    },
  },
  viewer: {
    peopleNav: false,
    adminNav: false,
    routes: {
      '/people': false,
      '/admin': false,
      '/shared-costs': false,
      '/initiatives/new': false,
    },
  },
};

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function roleEmail(role) {
  return `rbac-${role.replaceAll('_', '-')}@${emailDomain}`;
}

async function waitFor(fn, label, timeoutMs = 20_000) {
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

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function stopProcess(process) {
  if (process.exitCode !== null || process.signalCode !== null) return;

  const exited = new Promise(resolve => {
    process.once('exit', resolve);
  });
  process.kill('SIGTERM');
  const terminated = await Promise.race([exited.then(() => true), delay(5_000).then(() => false)]);
  if (!terminated && process.exitCode === null && process.signalCode === null) {
    process.kill('SIGKILL');
    await Promise.race([exited, delay(2_000)]);
  }
}

async function requestJson(url, init) {
  const response = await fetch(url, init);
  assert(response.ok, `${url} returned ${response.status}`);
  if (response.status === 204) return null;
  return response.json();
}

async function loginApi(role) {
  const payload = await requestJson(`${apiBaseUrl}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: roleEmail(role), password }),
  });
  return payload;
}

async function firstOwnedInitiativeId() {
  const session = await loginApi('initiative_owner');
  const payload = await requestJson(`${apiBaseUrl}/initiatives`, {
    headers: { Authorization: `Bearer ${session.access_token}` },
  });
  const item = payload.items?.[0] ?? payload.data?.[0];
  return item?.id ?? null;
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

async function browserLogin(page, role) {
  const session = await loginApi(role);
  await page.send('Page.addScriptToEvaluateOnNewDocument', {
    source: `globalThis.__TRANSMUTER_API_URL__ = ${JSON.stringify(apiBaseUrl)};`,
  });
  await page.send('Page.navigate', { url: `${uiBaseUrl}/auth/login` });
  await waitFor(
    () => evalJs(page, "document.readyState === 'complete'"),
    `${role} login origin`,
  );
  await evalJs(page, `
    (() => {
      localStorage.clear();
      sessionStorage.clear();
      localStorage.setItem('access_token', ${JSON.stringify(session.access_token)});
      ${session.refresh_token ? `localStorage.setItem('refresh_token', ${JSON.stringify(session.refresh_token)});` : ''}
      return true;
    })()
  `);
  await page.send('Page.navigate', { url: `${uiBaseUrl}/dashboard` });
  await waitFor(
    () => evalJs(page, "!!localStorage.getItem('access_token') && !location.pathname.startsWith('/auth') && document.querySelector('header') !== null"),
    `${role} authenticated shell`,
    45_000,
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
    () => evalJs(page, "document.querySelector('header') !== null"),
    `${role} app chrome`,
  );
}

async function navVisible(page, path) {
  return evalJs(page, `
    [...document.querySelectorAll('a')]
      .some(anchor => new URL(anchor.href, location.href).pathname === ${JSON.stringify(path)})
  `);
}

async function assertRoute(page, role, path, allowed) {
  await page.send('Page.navigate', { url: `${uiBaseUrl}${path}` });
  await waitFor(
    () => evalJs(page, "document.readyState === 'complete' && !!localStorage.getItem('access_token')"),
    `${role} route ${path}`,
  );
  await new Promise(resolve => setTimeout(resolve, 750));
  const pathname = await evalJs(page, 'location.pathname');
  if (allowed) {
    assert(
      pathname === path || pathname.startsWith(`${path}/`),
      `${role} should be allowed on ${path}; got ${pathname}`,
    );
  } else {
    assert(
      pathname !== path && !pathname.startsWith(`${path}/`),
      `${role} should be redirected away from ${path}`,
    );
  }
}

async function main() {
  await requestJson(`${apiBaseUrl}/health`);
  const ownedInitiativeId = await firstOwnedInitiativeId();

  const userDataDir = await mkdtemp(join(tmpdir(), 'transmuter-rbac-ui-'));
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

    const results = [];
    for (const role of roles) {
      await browserLogin(page, role);
      const expected = expectations[role];
      const peopleNav = await navVisible(page, '/people');
      const adminNav = await navVisible(page, '/admin');
      assert(peopleNav === expected.peopleNav, `${role} people nav expected ${expected.peopleNav}, got ${peopleNav}`);
      assert(adminNav === expected.adminNav, `${role} admin nav expected ${expected.adminNav}, got ${adminNav}`);
      for (const [path, allowed] of Object.entries(expected.routes)) {
        await assertRoute(page, role, path, allowed);
      }
      if (role === 'initiative_owner' && ownedInitiativeId) {
        await assertRoute(page, role, `/initiatives/${ownedInitiativeId}/edit`, true);
      }
      results.push({ role, peopleNav, adminNav });
    }
    page.close();
    console.log(JSON.stringify({ ui_permission_results: results }, null, 2));
  } finally {
    await stopProcess(chrome);
    await rm(userDataDir, { recursive: true, force: true, maxRetries: 10, retryDelay: 250 });
  }
}

main().catch(error => {
  console.error(error);
  process.exit(1);
});
