import { expect, test } from '@playwright/test';
import { devLogin } from './helpers';

for (const edition of ['6th', '7th']) {
  test(`${edition} detail skills, equipment and history treat HTML as text`, async ({ page }) => {
    await devLogin(page, 'admin', '/accounts/character/list/');
    const id = await page.evaluate(async selectedEdition => {
      const value = selectedEdition === '6th' ? 12 : 60;
      const response = await (window as any).axios.post(`/api/accounts/character-sheets/create_${selectedEdition}_edition/`, {
        name: `詳細表示安全性 ${Date.now()}`, age: 30, gender: 'unknown', luck: 60,
        str_value: value, con_value: value, pow_value: value, dex_value: value,
        app_value: value, siz_value: value, int_value: value, edu_value: value,
      });
      return response.data.id;
    }, edition);
    try {
      // Verify the real API contract without injecting a user field or history response.
      await page.goto(`/accounts/character/6th/${id}/`);
      const [emptyHistory] = await Promise.all([
        page.waitForResponse(response => response.url().endsWith(`/api/scenarios/history/?character_sheet=${id}`)),
        page.locator('#play-history-tab').click(),
      ]);
      expect(emptyHistory.status()).toBe(200);
      expect(await emptyHistory.json()).toEqual([]);
      await expect(page.locator('#playHistoryContainer')).toHaveText('この探索者を設定したセッションのプレイ履歴はありません。');
      const attack = '"><img src=x onerror="window.__detailXss++">入力 & 値';
      await page.addInitScript(() => { (window as any).__detailXss = 0; });
      await page.route(`**/api/accounts/character-sheets/${id}/`, async route => {
        if (route.request().method() !== 'GET') return route.continue();
        const response = await route.fetch();
        const character = await response.json();
        character.skills = [{ skill_name: attack, current_value: 30, base_value: 20, occupation_points: 10 }];
        character.equipment = ['weapon', 'armor', 'item'].map(item_type => ({
          item_type, name: attack, damage: attack, base_range: attack, description: attack, armor_points: 2,
        }));
        if (edition === '6th') {
          character.character_6th.mental_disorder = attack;
          character.character_6th.damage_bonus = attack;
        }
        await route.fulfill({ json: character });
      });
      await page.route(`**/api/scenarios/history/?character_sheet=${id}`, route => route.fulfill({ json: [{
        played_date: '2026-09-22', role: 'player', notes: attack,
        scenario_detail: { title: attack, author: attack, game_system: 'coc' },
      }] }));
      await page.goto(`/accounts/character/6th/${id}/`);
      await expect(page.locator('#skillsContainer .skill-card-title')).toHaveText(attack);
      await expect(page.locator('#skillsContainer .skill-total')).toHaveAttribute('aria-label', `${attack} 合計 30`);
      for (const container of ['skillsContainer', 'weaponsContainer', 'armorContainer', 'itemsContainer']) {
        await expect(page.locator(`#${container}`)).toContainText(attack);
        await expect(page.locator(`#${container} img`)).toHaveCount(0);
      }
      await expect(page.locator('#weaponsContainer').getByText(attack, { exact: false })).toHaveCount(4);
      if (edition === '6th') {
        await expect(page.locator('#editionSpecificContainer').getByText(attack, { exact: true })).toHaveCount(2);
        await expect(page.locator('#editionSpecificContainer img')).toHaveCount(0);
      }
      await page.locator('#play-history-tab').click();
      await expect(page.locator('#playHistoryContainer').getByText(attack, { exact: false })).toHaveCount(3);
      await expect(page.locator('#playHistoryContainer img')).toHaveCount(0);
      expect(await page.evaluate(() => (window as any).__detailXss)).toBe(0);
    } finally {
      await page.evaluate(async characterId => {
        await (window as any).axios.delete(`/api/accounts/character-sheets/${characterId}/`);
      }, id);
    }
  });
}
