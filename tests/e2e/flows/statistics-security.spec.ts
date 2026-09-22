import { test, expect } from '@playwright/test';
import { devLogin } from './helpers';

test('statistics renders API-provided names as text without executing markup', async ({ page }) => {
  const attack = '<img src=x onerror="window.__statisticsXss += 1">表示名';
  const year = new Date().getFullYear();

  await page.addInitScript(() => {
    (window as any).__statisticsXss = 0;
  });
  await page.route('**/api/accounts/statistics/**', async route => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/accounts/statistics/tindalos/') {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          user: { trpg_start_year: year },
          yearly_stats: {
            total_sessions: 1,
            gm_sessions: 1,
            pl_sessions: 0,
            total_hours: 2,
            total_minutes: 120,
            sessions_per_month: 1,
            avg_session_hours: 2,
            active_groups: 1,
            played_scenarios: 1,
            completion_rate: 100,
          },
          monthly_stats: Array.from({ length: 12 }, () => ({ session_count: 0, total_hours: 0 })),
          role_stats: {
            gm: { session_count: 1 },
            pl: { session_count: 0 },
          },
          system_stats: [],
          weekly_stats: { counts: Array(7).fill(0) },
          hourly_stats: { counts: Array(24).fill(0) },
          group_stats: [{
            group_name: attack,
            session_count: 1,
            total_hours: 2,
            active_members: 1,
            top_gm: attack,
          }],
          recent_sessions: [{
            title: attack,
            date: '2026-09-22T00:00:00Z',
            group_name: attack,
            gm_name: attack,
            role: 'gm',
            duration_hours: 2,
          }],
        }),
      });
      return;
    }
    if (url.pathname === '/api/accounts/statistics/ranking/') {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          ranking: [{ rank: 1, nickname: attack, total_hours: 2, session_count: 1, gm_count: 1 }],
        }),
      });
      return;
    }
    await route.continue();
  });

  await devLogin(page, 'admin', '/accounts/statistics/view/');

  await expect(page.locator('#groupStats')).toContainText(attack);
  await expect(page.locator('#recentSessions')).toContainText(attack);
  await expect(page.locator('#ranking')).toContainText(attack);
  await expect(page.locator('#groupStats img, #recentSessions img, #ranking img')).toHaveCount(0);
  await expect.poll(() => page.evaluate(() => (window as any).__statisticsXss)).toBe(0);
});
