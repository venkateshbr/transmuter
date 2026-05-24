import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawn } from 'node:child_process';

const uiBaseUrl = process.env.TRANSMUTER_UI_BASE_URL ?? 'http://localhost:4300';
const apiBaseUrl = process.env.TRANSMUTER_API_BASE_URL ?? 'http://localhost:8000';
const chromeBin = process.env.CHROME_BIN ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
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
    throw new Error(
      result.exceptionDetails.exception?.description
      ?? result.exceptionDetails.text
      ?? 'Browser evaluation failed',
    );
  }
  return result.result.value;
}

function expiredToken() {
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url');
  const payload = Buffer.from(JSON.stringify({
    sub: 'expired-session-test',
    tenant_id: '00000000-0000-0000-0000-000000000000',
    role: 'transformation_office',
    exp: 1,
  })).toString('base64url');
  return `${header}.${payload}.expired`;
}

async function main() {
  await requestJson(`${apiBaseUrl}/health`);

  const userDataDir = await mkdtemp(join(tmpdir(), 'transmuter-expired-signup-'));
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
    await page.send('Page.addScriptToEvaluateOnNewDocument', {
      source: `globalThis.__TRANSMUTER_API_URL__ = ${JSON.stringify(apiBaseUrl)};`,
    });
    await page.send('Page.navigate', { url: `${uiBaseUrl}/get-started` });
    await waitFor(
      () => evalJs(page, "document.querySelector('input[name=organizationName]') !== null"),
      'signup form',
    );
    await evalJs(page, `localStorage.setItem('access_token', ${JSON.stringify(expiredToken())})`);

    const stamp = Date.now();
    await evalJs(page, `
      (() => {
        const setValue = (selector, value) => {
          const input = document.querySelector(selector);
          if (!input) throw new Error('Missing field: ' + selector);
          input.value = value;
          input.dispatchEvent(new Event('input', { bubbles: true }));
          input.dispatchEvent(new Event('change', { bubbles: true }));
        };
        setValue('input[name=organizationName]', 'Expired Session E2E ${stamp}');
        setValue('input[name=organizationSlug]', 'expired-session-e2e-${stamp}');
        setValue('input[name=adminName]', 'Expired Session Admin');
        setValue('input[name=adminEmail]', 'expired.session.${stamp}@example.com');
        setValue('input[name=initialPassword]', 'TransmuterE2E${stamp}!');
        setValue('input[name=confirmPassword]', 'TransmuterE2E${stamp}!');
        setValue('input[name=plannedUsers]', '10');
        document.querySelector('button[type=submit]').click();
      })()
    `);

    await waitFor(
      () => evalJs(page, "location.href.includes('checkout.stripe.com') || location.href.includes('/auth/login')"),
      'checkout or login redirect',
      30_000,
    );

    const finalUrl = await evalJs(page, 'location.href');
    assert(
      finalUrl.includes('checkout.stripe.com'),
      `Public signup was blocked by expired session redirect: ${finalUrl}`,
    );
    assert(
      !finalUrl.includes('/auth/login'),
      `Public signup reached login instead of checkout: ${finalUrl}`,
    );
    page.close();
    console.log('Expired-session public signup regression passed.');
  } finally {
    chrome.kill('SIGTERM');
    await rm(userDataDir, { recursive: true, force: true });
  }
}

main().catch(error => {
  console.error(error);
  process.exit(1);
});
