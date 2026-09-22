import { expect, test } from '@playwright/test';
import { devLogin } from './helpers';

test('growth records and summary render user text without interpreting HTML', async ({ page }) => {
  await devLogin(page, 'admin', '/accounts/character/list/');
  const id = await page.evaluate(async () => {
    const response = await (window as any).axios.post('/api/accounts/character-sheets/create_6th_edition/', {
      name: `成長表示安全性 ${Date.now()}`, age: 30, gender: 'unknown',
      str_value: 12, con_value: 12, pow_value: 12, dex_value: 12,
      app_value: 12, siz_value: 12, int_value: 12, edu_value: 12,
    });
    return response.data.id;
  });
  try {
    const attack = '<img src=x onerror="window.__growthXss += 1">成長 & 記録';
    await page.addInitScript(() => { (window as any).__growthXss = 0; });
    await page.route(`**/accounts/character-sheets/${id}/growth-records/`, route => route.fulfill({
      json: [{
        id: 1, session_date: '2026-09-22', scenario_name: attack, gm_name: attack,
        special_rewards: attack, notes: attack, net_sanity_change: 1,
        sanity_gained: 2, sanity_lost: 1, experience_gained: 3,
        skill_growths: [{ skill_name: attack, old_value: 20, new_value: 25, growth_amount: 5, growth_roll_result: 30 }],
      }],
    }));
    await page.route(`**/accounts/character-sheets/${id}/growth-records/summary/`, route => route.fulfill({
      json: {
        total_sessions: 1, total_san_gained: 2, total_san_lost: 1,
        net_san_change: 1, total_experience: 3,
        skill_growth_stats: { [attack]: { total_growth: 5, growth_count: 1 } },
      },
    }));
    await page.goto(`/accounts/character/6th/${id}/`);
    await page.locator('#growth-records-tab').click();
    const records = page.locator('#growthRecordsContainer');
    await expect(records.getByText(attack, { exact: false })).toHaveCount(5);
    await expect(records.locator('img')).toHaveCount(0);
    await expect(records).toContainText('20 → 25');
    await page.locator('#viewGrowthSummaryBtn').click();
    await expect(page.locator('#growthSummaryModal')).toBeVisible();
    await expect(page.locator('#growthSummaryContent td').first()).toHaveText(attack);
    await expect(page.locator('#growthSummaryContent img')).toHaveCount(0);
    expect(await page.evaluate(() => (window as any).__growthXss)).toBe(0);
  } finally {
    await page.evaluate(async characterId => {
      await (window as any).axios.delete(`/api/accounts/character-sheets/${characterId}/`);
    }, id);
  }
});
