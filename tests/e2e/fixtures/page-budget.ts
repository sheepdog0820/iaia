import { test as base } from '@playwright/test';

export function withPageSetupBudget(pageSetupTimeout = 30_000) {
  return base.extend({
    // Keep the isolated browser context supplied by Playwright (including
    // tracing/video and its cleanup). Only page creation gets its own budget;
    // the test body and beforeEach hooks retain the configured test timeout.
    page: [async ({ context }, use) => {
      await use(await context.newPage());
    }, { timeout: pageSetupTimeout }],
  });
}

export const test = withPageSetupBudget();
export { expect } from '@playwright/test';
