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

for (const paginated of [false, true]) {
  test(`dashboard renders history markup as text (${paginated ? 'paginated' : 'array'})`, async ({ page }) => {
    const markup = '<img src=x onerror="window.__dashboardXss=1">';
    const activities = [{ scenario_detail: { title: markup }, notes: markup, played_date: '2026-09-06', role: 'gm' }];
    await page.route('**/api/scenarios/history/?limit=8', route => route.fulfill({
      json: paginated ? { results: activities } : activities,
    }));
    await devLogin(page, 'admin', '/accounts/dashboard/');
    await expect(page.locator('#activity-feed strong')).toHaveText(markup);
    await expect(page.locator('#activity-feed .activity-content p')).toHaveText(markup);
    await expect(page.locator('#activity-feed img')).toHaveCount(0);
    expect(await page.evaluate(() => (window as any).__dashboardXss)).toBeUndefined();
  });
}

test('dashboard displays persisted history safely', async ({ page }) => {
  await devLogin(page, 'admin', '/accounts/dashboard/');
  const markup = `<img src=x onerror="window.__savedHistoryXss=1"> ${Date.now()}`;
  const saved = await page.evaluate(async text => {
    const client = (window as any).axios;
    const scenario = await client.post('/api/scenarios/scenarios/', {
      title: text, game_system: 'coc6', visibility: 'private',
    });
    const history = await client.post('/api/scenarios/history/', {
      scenario: scenario.data.id, notes: text, played_date: '2026-09-06', role: 'gm',
    });
    return { status: history.status, id: history.data.id };
  }, markup);
  expect(saved.status).toBe(201);
  await page.reload();
  const activity = page.locator('#activity-feed .activity-item', { hasText: markup });
  await expect(activity.locator('strong')).toHaveText(markup);
  await expect(activity.locator('.activity-content p')).toHaveText(markup);
  await expect(activity.locator('img')).toHaveCount(0);
  expect(await page.evaluate(() => (window as any).__savedHistoryXss)).toBeUndefined();
  const response = await page.request.get(`/api/scenarios/history/${saved.id}/`);
  expect(response.status()).toBe(200);
  expect((await response.json()).notes).toBe(markup);
});
