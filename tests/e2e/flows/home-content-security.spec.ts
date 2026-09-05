import { expect, test } from '@playwright/test';
import { devLogin } from './helpers';

test('home renders group and history markup as text', async ({ page }) => {
  const markup = '<img src=x onerror="window.__homeXss=1">';
  await page.route('**/api/accounts/groups/', route => route.fulfill({ json: [
    { id: 1, name: markup, description: markup, member_count: 1 },
  ] }));
  await page.route('**/api/scenarios/history/?limit=5', route => route.fulfill({ json: [
    { scenario_detail: { title: markup }, played_date: '2026-09-06', role: 'gm' },
  ] }));
  await devLogin(page);
  await expect(page.locator('#user-groups .card-title')).toHaveText(markup);
  await expect(page.locator('#user-groups .card-text')).toHaveText(markup);
  await expect(page.locator('#recent-activity strong')).toHaveText(markup);
  await expect(page.locator('#user-groups img, #recent-activity img')).toHaveCount(0);
  expect(await page.evaluate(() => (window as any).__homeXss)).toBeUndefined();
});
