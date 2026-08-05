import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 90_000,
  expect: { timeout: 15_000 },
  reporter: [['line'], ['html', { outputFolder: '../../scratch/issue-447/playwright-report', open: 'never' }]],
  outputDir: '../../scratch/issue-447/test-results',
  use: {
    headless: true,
    viewport: { width: 1440, height: 1000 },
    actionTimeout: 20_000,
    navigationTimeout: 30_000,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
});
