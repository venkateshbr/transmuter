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
  throw new Error('Meetings acceptance is restricted to the approved dev environment.');
}
if (!deployedCommit || !/^[0-9a-f]{7,40}$/i.test(deployedCommit)) {
  throw new Error('TRANSMUTER_DEPLOYED_COMMIT must identify the deployed dev commit.');
}
const reportPath = resolve(repo, 'scratch/meetings-v4-browser-acceptance-results.json');

const results = {
  environment: baseUrl,
  commit: deployedCommit,
  execution: 'Playwright Chromium against real Angular UI and real dev API',
  seriesName: '',
  meetingPath: '',
  sessionPath: '',
  checks: [],
  pageErrors: [],
  serverErrors: [],
  teamsWrites: [],
};

async function settle(page) {
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle', { timeout: 8_000 }).catch(() => undefined);
  await page
    .locator('div[role="status"].fixed.inset-0')
    .waitFor({ state: 'hidden', timeout: 30_000 })
    .catch(() => undefined);
  await page.waitForTimeout(300);
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

async function selectOptionContaining(select, text) {
  await expect
    .poll(async () => select.locator('option').filter({ hasText: text }).count(), {
      timeout: 20_000,
    })
    .toBeGreaterThan(0);
  const option = select.locator('option').filter({ hasText: text }).first();
  const value = await option.getAttribute('value');
  expect(value).toBeTruthy();
  await select.selectOption(value);
  return value;
}

async function recoverMeeting(browser, seriesName) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const recoveryPage = await context.newPage();
  try {
    await login(recoveryPage);
    await openRoute(recoveryPage, '/admin');
    await recoveryPage.getByRole('button', { name: 'Open Data Cleanup admin tab' }).click();
    const meeting = recoveryPage.getByLabel(`Select meeting ${seriesName} for cleanup`);
    if (await meeting.count()) {
      await meeting.check();
      await recoveryPage.getByLabel('Meeting cleanup confirmation phrase').fill('DELETE MEETINGS');
      await recoveryPage.getByRole('button', { name: 'Delete selected meetings' }).click();
      await expect(recoveryPage.getByText('Deleted 1 meeting series.')).toBeVisible();
    }
  } finally {
    await context.close();
  }
}

function record(check, evidence = '') {
  results.checks.push({ check, status: 'passed', evidence });
  console.log(`[meetings-v4] PASS ${check}${evidence ? ` — ${evidence}` : ''}`);
}

test('Meetings V4 full browser acceptance and cleanup', async ({ page, browser }) => {
  test.setTimeout(600_000);
  page.on('pageerror', error => results.pageErrors.push(error.message));
  page.on('response', response => {
    if (response.status() >= 500) {
      results.serverErrors.push({ status: response.status(), path: new URL(response.url()).pathname });
    }
  });
  page.on('request', request => {
    if (
      request.method() !== 'GET'
      && request.url().includes('/external-events/microsoft')
    ) {
      results.teamsWrites.push({ method: request.method(), url: request.url() });
    }
  });

  let seriesName = '';
  try {
    await page.goto(`${baseUrl}/health`);
    await expect(page.locator('body')).toContainText(/healthy|ok/i);
    await page.goto(`${baseUrl}/api/health`);
    await expect(page.locator('body')).toContainText(/healthy|ok/i);
    await login(page);
    record('Public health and seeded sign-in');

    const suffix = Date.now().toString(36);
    seriesName = `Meetings V4 Browser Acceptance ${suffix}`;
    const defaultTopic = 'Review Meetings V4 workflow';
    const undiscussedTopic = 'Budget review should remain undiscussed';
    const initiativeTopic = 'Confirm ENT-001 delivery owner and next milestone';
    const sessionTopic = 'Resolve ENT-001 implementation dependency';
    const today = new Date();
    const daysUntilSaturday = (6 - today.getDay() + 7) % 7 || 7;
    const seriesStart = new Date(today);
    seriesStart.setDate(today.getDate() + daysUntilSaturday);
    const seriesEnd = new Date(seriesStart);
    seriesEnd.setDate(seriesStart.getDate() + 35);
    const isoDate = value => value.toISOString().slice(0, 10);
    const humanSeriesStart = seriesStart.toLocaleDateString('en-US', {
      weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
    });
    results.seriesName = seriesName;

    await openRoute(page, '/meetings');
    await page.getByRole('button', { name: 'Create meeting series' }).click();
    await expect(page.getByRole('heading', { name: 'New meeting series' })).toBeVisible();
    await page.getByLabel('Meeting name').fill(seriesName);
    await page.getByLabel('Meeting scope').selectOption('all');
    await page.getByLabel('Meeting recurrence').selectOption('weekly');
    await page.getByLabel('Meeting day of week').selectOption({ label: 'Saturday' });
    await page.getByLabel('Meeting series start date').fill(isoDate(seriesStart));
    await page.getByLabel('Meeting series end date').fill(isoDate(seriesEnd));
    await page.getByLabel('Meeting start time').fill('09:00');
    await page.getByLabel('Meeting duration minutes').fill('60');
    await page
      .getByLabel('Default agenda items')
      .fill(`${defaultTopic}\n${undiscussedTopic}`);
    await page
      .getByLabel('Meeting description')
      .fill('Browser acceptance of Meetings V4 series, agenda, session, and minutes behavior.');
    await page
      .locator('fieldset')
      .filter({ hasText: 'Participants' })
      .locator('input[type=checkbox]')
      .first()
      .check();
    await page.getByRole('button', { name: 'Create series' }).click();
    await page.waitForURL(/\/meetings\/[0-9a-f-]+$/i, { timeout: 30_000 });
    results.meetingPath = new URL(page.url()).pathname;
    await expect(page.getByRole('heading', { name: seriesName })).toBeVisible();
    await expect(page.getByText(defaultTopic).first()).toBeVisible();
    await expect(page.getByText(undiscussedTopic).first()).toBeVisible();
    record('Weekly series creation with default agenda and participant', results.meetingPath);

    await page.getByRole('button', { name: 'Suggest agenda items' }).click();
    await expect(page.getByText('No agenda suggestions were available.')).toBeVisible();
    record('Agenda generation is gated when no initiative is linked');

    await page.getByRole('button', { name: 'Link initiative' }).click();
    await selectOptionContaining(page.getByLabel('Select initiative'), 'ENT-001');
    await page.getByRole('button', { name: 'Link', exact: true }).click();
    await expect(page.getByText('ENT-001').first()).toBeVisible();

    await page.getByRole('button', { name: 'Add agenda item' }).click();
    await page.getByLabel('Agenda topic').fill(initiativeTopic);
    await selectOptionContaining(page.getByLabel('Agenda initiative'), 'ENT-001');
    await page.getByRole('button', { name: 'Add', exact: true }).first().click();
    await expect(page.getByText(initiativeTopic).first()).toBeVisible();
    record('Series initiative link and initiative-backed agenda item');

    await page.getByRole('button', { name: 'Edit meeting series' }).click();
    await expect(page.getByRole('dialog', { name: 'Edit meeting series' })).toBeVisible();
    await page.getByLabel('Meeting description').fill(
      'Edited in the browser before lifecycle acceptance.',
    );
    await page.getByRole('button', { name: 'Save changes' }).click();
    await expect(page.getByText('Edited in the browser before lifecycle acceptance.')).toBeVisible();
    record('Series edit persists through the real UI');

    await page.getByRole('button', { name: 'Start next scheduled session' }).click();
    await expect(page.getByRole('heading', { name: 'Start session' })).toBeVisible();
    await expect(page.getByLabel('Session date')).toHaveCount(0);
    await expect(page.getByText(humanSeriesStart)).toBeVisible();
    await page.getByRole('button', { name: 'Start', exact: true }).click();
    await page.waitForURL(/\/meetings\/sessions\/[0-9a-f-]+$/i, { timeout: 30_000 });
    results.sessionPath = new URL(page.url()).pathname;
    await expect(page.getByText(defaultTopic).first()).toBeVisible();
    await expect(page.getByText(undiscussedTopic).first()).toBeVisible();
    await expect(page.getByText(initiativeTopic).first()).toBeVisible();
    record('Scheduled session starts without arbitrary date input');
    record('Default and series agenda propagate to the materialized session', results.sessionPath);

    await page.getByRole('button', { name: 'Add session agenda item' }).click();
    await page.locator('textarea[aria-label="Session agenda item"]').fill(sessionTopic);
    await selectOptionContaining(page.getByLabel('Linked initiative'), 'ENT-001');
    await page.getByRole('button', { name: 'Add Agenda Item' }).click();
    await expect(page.getByText(sessionTopic).first()).toBeVisible();
    record('Session agenda item can link the meeting initiative');

    await page.getByRole('button', { name: 'Suggest Agenda' }).click();
    const suggestions = page.getByLabel(/^Accept /);
    await expect.poll(() => suggestions.count(), { timeout: 30_000 }).toBeGreaterThan(0);
    const suggestionCount = await suggestions.count();
    expect(suggestionCount).toBeLessThanOrEqual(5);
    await page.getByRole('button', { name: 'Add accepted' }).click();
    await expect(page.getByText('Accepted agenda suggestions added.')).toBeVisible();
    record('Linked-initiative agenda suggestions are available, accepted, and capped', `${suggestionCount} suggestions`);

    await page.getByText(defaultTopic).first().click();
    const notes = [
      'The team verified Meetings V4 default agenda propagation and initiative links.',
      'ENT-001 requires a named delivery owner before the next milestone review.',
      'The committee decided to use ad-hoc meeting series for unscheduled meetings.',
      `Alex will document browser acceptance evidence by ${isoDate(seriesEnd)}.`,
    ].join(' ');
    await page
      .getByPlaceholder('Capture meeting minutes, decisions, and key discussion points...')
      .fill(notes);
    await expect(page.getByText(/All changes saved/i)).toBeVisible({ timeout: 30_000 });

    await page.getByRole('button', { name: 'Import Transcript' }).click();
    const microsoftSync = page.waitForResponse(response =>
      response.url().includes('/transcript/sync/microsoft')
      && response.request().method() === 'POST',
    );
    await page.getByRole('button', { name: 'Sync Microsoft Teams transcript' }).click();
    const microsoftResponse = await microsoftSync;
    expect(microsoftResponse.status()).toBeLessThan(500);
    await expect(page.getByTestId('transcript-sync-error')).toContainText(
      /Create and sync a Teams invite|Microsoft Graph connection is required/i,
    );
    await page.getByRole('button', { name: 'Cancel', exact: true }).click();
    await expect(page.getByTestId('transcript-sync-error')).toHaveCount(0);
    await expect(page.locator('body')).not.toContainText('Microsoft Graph connection is required');
    record('Disconnected Microsoft transcript sync reports inside the modal and clears on cancel');

    await page.getByRole('button', { name: 'Import Transcript' }).click();
    await page.locator('textarea[aria-label="Transcript text"]').fill(
      [
        'The meeting reviewed Meetings V4 behavior and confirmed that default agenda items now appear in sessions.',
        'The group confirmed ENT-001 initiative linking on both series and session agenda items.',
        'The committee agreed that unscheduled meetings should use an ad-hoc meeting series.',
        `Alex accepted the action to document browser acceptance evidence by ${isoDate(seriesEnd)}.`,
      ].join(' '),
    );
    await page.getByRole('button', { name: 'Import transcript', exact: true }).click();
    await expect(page.getByText('Transcript imported.')).toBeVisible();

    await page.getByLabel('Artifact type').selectOption('decision');
    await page.getByLabel('Artifact priority').selectOption('high');
    await page
      .getByPlaceholder('Capture a new action item...')
      .fill('Use ad-hoc meeting series for unscheduled meetings');
    await page.getByRole('button', { name: 'Add decision' }).click();
    await expect(
      page.getByText('Use ad-hoc meeting series for unscheduled meetings').first(),
    ).toBeVisible();

    await page.getByLabel('Artifact type').selectOption('action');
    await page.getByLabel('Artifact priority').selectOption('high');
    await page
      .getByPlaceholder('Capture a new action item...')
      .fill(`Document browser acceptance evidence by ${isoDate(seriesEnd)}`);
    await page.getByRole('button', { name: 'Add action' }).click();
    await expect(
      page.getByText(`Document browser acceptance evidence by ${isoDate(seriesEnd)}`).first(),
    ).toBeVisible();
    record('Inline notes, transcript, decision, and action are captured');

    await page.getByRole('button', { name: 'Generate Minutes' }).click();
    const minutes = page.getByLabel('Draft meeting minutes');
    await expect(minutes).toBeVisible({ timeout: 120_000 });
    await expect(minutes).toHaveValue(/## Executive Summary/);
    await expect(minutes).toHaveValue(/Meetings V4/i);
    await expect(minutes).toHaveValue(/ad-hoc meeting series/i);
    await expect(minutes).toHaveValue(/Document browser acceptance evidence/i);
    const generated = await minutes.inputValue();
    const summary = generated.split('## Key Discussion')[0];
    expect(summary).not.toMatch(/Budget review/i);
    expect(generated).not.toMatch(/- Discussed /);
    expect(generated).not.toMatch(/No specific transcript or note content was captured/i);
    await minutes.fill(`${generated}\n\nBrowser reviewer: draft checked and approved for persistence.`);
    await page.getByRole('button', { name: 'Save Draft' }).click();
    await expect(page.getByText('Draft minutes saved.')).toBeVisible();
    await page.reload();
    await expect(page.getByLabel('Draft meeting minutes')).toHaveValue(/Browser reviewer/);
    record('Professional evidence-grounded AI minutes generate, save, and persist');

    await page.getByRole('button', { name: 'Complete Session' }).click();
    await page.waitForURL(new RegExp(`${results.meetingPath}$`), { timeout: 30_000 });
    await expect(page.getByText('COMPLETED', { exact: true }).first()).toBeVisible();
    record('Session completes and returns to the series');

    page.once('dialog', dialog => dialog.accept());
    await page.getByRole('button', { name: 'Edit meeting series' }).click();
    await page.getByRole('button', { name: 'Cancel meeting series' }).click();
    await page.waitForURL(url => url.pathname === '/meetings', { timeout: 30_000 });
    await expect(page.locator('h3').filter({ hasText: seriesName })).toHaveCount(0);
    record('Series cancellation returns to Meetings list and removes active card');

    await openRoute(page, '/admin');
    await page.getByRole('button', { name: 'Open Data Cleanup admin tab' }).click();
    await page.getByLabel(`Select meeting ${seriesName} for cleanup`).check();
    await page.getByLabel('Meeting cleanup confirmation phrase').fill('DELETE MEETINGS');
    await page.getByRole('button', { name: 'Delete selected meetings' }).click();
    await expect(page.getByText('Deleted 1 meeting series.')).toBeVisible();
    results.cleanup = true;
    record('Temporary meeting series removed through Admin cleanup');

    expect(results.teamsWrites, 'No Teams invite/event write should occur').toEqual([]);
    expect(results.pageErrors, 'Unexpected browser page errors').toEqual([]);
    expect(results.serverErrors, 'Unexpected server errors observed by browser').toEqual([]);
    record('No Teams write, browser page error, or observed 5xx response');
  } finally {
    if (seriesName && !results.cleanup) {
      try {
        await recoverMeeting(browser, seriesName);
        results.recoveryCleanup = 'passed';
      } catch (error) {
        results.recoveryCleanup = 'failed';
        results.recoveryCleanupError = error instanceof Error ? error.message : String(error);
      }
    } else {
      results.recoveryCleanup = 'not-required';
    }
    writeFileSync(reportPath, `${JSON.stringify(results, null, 2)}\n`);
  }
  expect(results.recoveryCleanup).not.toBe('failed');
});
