import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawn } from 'node:child_process';

const uiBaseUrl = process.env.TRANSMUTER_UI_BASE_URL ?? 'http://localhost:4300';
const apiBaseUrl = process.env.TRANSMUTER_API_BASE_URL ?? 'http://localhost:8000';
const chromeBin = process.env.CHROME_BIN ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const email = process.env.TRANSMUTER_E2E_EMAIL ?? 'admin@ishirock.dev';
const password = process.env.TRANSMUTER_E2E_PASSWORD ?? 'Transmuter2026!';
const debugPort = Number(process.env.CHROME_DEBUG_PORT ?? 9223);

function assert(condition, message) {
  if (!condition) throw new Error(message);
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

async function requestJson(url, init) {
  const response = await fetch(url, init);
  assert(response.ok, `${url} returned ${response.status}`);
  return response.json();
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
    throw new Error(result.exceptionDetails.text ?? 'Runtime evaluation failed');
  }
  return result.result.value;
}

async function assertPage(page, url, predicate, label) {
  await page.send('Page.navigate', { url });
  await waitFor(() => evalJs(page, predicate), label);
}

async function main() {
  await requestJson(`${apiBaseUrl}/health`);
  const auth = await requestJson(`${apiBaseUrl}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  const initiatives = await requestJson(`${apiBaseUrl}/initiatives`, {
    headers: { Authorization: `Bearer ${auth.access_token}` },
  });
  const initiativeId = initiatives.items[0]?.id;
  assert(initiativeId, 'Seeded initiative is required for detail dependency UI');

  const userDataDir = await mkdtemp(join(tmpdir(), 'transmuter-phase2a-ui-'));
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

  let page;
  try {
    await waitFor(
      () => fetch(`http://127.0.0.1:${debugPort}/json/version`).then(r => r.ok),
      'Chrome DevTools endpoint',
    );
    const target = await requestJson(
      `http://127.0.0.1:${debugPort}/json/new?${encodeURIComponent('about:blank')}`,
      { method: 'PUT' },
    );
    page = await connectToPage(target.webSocketDebuggerUrl);
    await page.send('Page.enable');
    await page.send('Runtime.enable');
    await page.send('Page.addScriptToEvaluateOnNewDocument', {
      source: `
        globalThis.__TRANSMUTER_API_URL__ = ${JSON.stringify(apiBaseUrl)};
        localStorage.setItem('access_token', ${JSON.stringify(auth.access_token)});
      `,
    });

    await assertPage(
      page,
      `${uiBaseUrl}/reports/control-tower`,
      "location.pathname === '/reports/control-tower' && document.body.innerText.includes('Executive Control Tower') && document.body.innerText.includes('Burdened Value Bridge') && document.body.innerText.includes('Dependency Risk')",
      'executive control tower page',
    );
    await assertPage(
      page,
      `${uiBaseUrl}/shared-costs`,
      "location.pathname === '/shared-costs' && document.body.innerText.includes('Shared Cost Pools') && document.body.innerText.includes('Allocation Rules')",
      'shared cost pools page',
    );
    await assertPage(
      page,
      `${uiBaseUrl}/progress/dependencies`,
      "location.pathname === '/progress/roadmap' && document.body.innerText.includes('Roadmap Explorer') && !document.querySelector('[data-testid=\"dependency-graph\"]') && !document.querySelector('[data-testid=\"dependency-table\"]')",
      'portfolio dependency redirect to roadmap',
    );
    await assertPage(
      page,
      `${uiBaseUrl}/initiatives/${initiativeId}`,
      "location.pathname.startsWith('/initiatives/') && Array.from(document.querySelectorAll('button')).filter(button => button.innerText.trim() === 'Dependencies').length >= 1",
      'initiative detail page',
    );
    await evalJs(page, `
      (() => {
        const buttons = Array.from(document.querySelectorAll('button')).filter(item => item.innerText.trim() === 'Dependencies');
        const button = buttons.at(-1);
        if (!button) throw new Error('Missing Dependencies tab');
        button.click();
        return true;
      })()
    `);
    await waitFor(
      () => evalJs(page, "document.body.innerText.toLowerCase().includes('initiative dependencies') && document.body.innerText.toLowerCase().includes('create an initiative-level dependency edge')"),
      'initiative dependency tab',
    );

    console.log('Phase 2A UI acceptance passed');
  } finally {
    page?.close();
    chrome.kill('SIGTERM');
    await new Promise(resolve => chrome.once('exit', resolve));
    await rm(userDataDir, { recursive: true, force: true });
  }
}

main().catch(error => {
  console.error(error);
  process.exit(1);
});
