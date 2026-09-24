import { expect, test } from '@playwright/test';
import { devLogin } from './helpers';

for (const edition of ['6th', '7th']) {
  test(`${edition} saved history appears only for its linked investigator`, async ({ page }) => {
    await devLogin(page, 'admin', '/accounts/character/list/');
    const cleanup: string[] = [];
    const post = async (path: string, data: Record<string, unknown>) => {
      const result = await page.evaluate(async ({ path, data }) => {
        const response = await (window as any).axios.post(path, data, { validateStatus: () => true });
        return { status: response.status, data: response.data };
      }, { path, data });
      expect(result.status, JSON.stringify(result.data)).toBeGreaterThanOrEqual(200);
      expect(result.status, JSON.stringify(result.data)).toBeLessThan(300);
      return result.data;
    };
    const create = async (path: string, data: Record<string, unknown>, deletePath = path) => {
      const result = await post(path, data);
      cleanup.push(`${deletePath}${result.id}/`);
      return result;
    };
    const suffix = `${edition}-${Date.now()}`;
    const markup = '<img src=x onerror="window.__historyXss++">履歴 & 記録';
    await page.addInitScript(() => { (window as any).__historyXss = 0; });
    try {
      const group = await create('/api/accounts/groups/', { name: `履歴試験 ${suffix}`, visibility: 'private' });
      const scenario = await create('/api/scenarios/scenarios/', { title: markup, game_system: edition === '6th' ? 'coc6' : 'coc7', visibility: 'private' });
      const value = edition === '6th' ? 12 : 60;
      const attributes = {
        age: 30, gender: 'unknown', luck: 60, str_value: value, con_value: value,
        pow_value: value, dex_value: value, app_value: value, siz_value: value, int_value: value, edu_value: value,
      };
      const character = await create(`/api/accounts/character-sheets/create_${edition}_edition/`, {
        ...attributes, name: `履歴対象 ${suffix}`,
      }, '/api/accounts/character-sheets/');
      const other = await create(`/api/accounts/character-sheets/create_${edition}_edition/`, {
        ...attributes, name: `別探索者 ${suffix}`,
      }, '/api/accounts/character-sheets/');
      const histories: number[] = [];
      for (const selected of [character, other]) {
        const session = await create('/api/schedules/sessions/', {
          title: `履歴セッション ${selected.id}`, group: group.id, scenario: scenario.id, as_gm: true,
          visibility: 'group', date: '2026-09-22T00:00:00Z', duration_minutes: 120,
        });
        await post(`/api/schedules/sessions/${session.id}/join/`, { character_sheet_id: selected.id });
        const history = await create('/api/scenarios/history/', {
          scenario: scenario.id, session: session.id, role: 'player',
          played_date: '2026-09-22T00:00:00Z', notes: selected.id === character.id ? markup : '別探索者だけの記録',
        });
        histories.push(history.id);
      }
      await page.goto(`/accounts/character/6th/${character.id}/`);
      for (let attempt = 0; attempt < 2; attempt++) {
        const [response] = await Promise.all([
          page.waitForResponse(response => response.url().endsWith(`/api/scenarios/history/?character_sheet=${character.id}`)),
          page.locator('#play-history-tab').click(),
        ]);
        expect(response.status()).toBe(200);
        expect((await response.json()).map((row: { id: number }) => row.id)).toEqual([histories[0]]);
        await expect(page.locator('#playHistoryContainer .play-history-card')).toHaveCount(1);
        await expect(page.locator('#playHistoryContainer')).toContainText(markup);
        await expect(page.locator('#playHistoryContainer')).not.toContainText('別探索者だけの記録');
        await expect(page.locator('#playHistoryContainer')).toContainText(`クトゥルフ神話TRPG ${edition === '6th' ? '6' : '7'}版`);
        await expect(page.locator('#playHistoryContainer img')).toHaveCount(0);
        expect(await page.evaluate(() => (window as any).__historyXss)).toBe(0);
        if (attempt === 0) await page.reload();
      }
      await page.goto(`/accounts/character/6th/${other.id}/`);
      await page.locator('#play-history-tab').click();
      await expect(page.locator('#playHistoryContainer .play-history-card')).toHaveCount(1);
      await expect(page.locator('#playHistoryContainer')).toContainText('別探索者だけの記録');
    } finally {
      const failures: string[] = [];
      for (const path of cleanup.reverse()) {
        try {
          await page.evaluate(async url => { await (window as any).axios.delete(url); }, path);
        } catch {
          failures.push(path);
        }
      }
      expect(failures, '使い捨て試験データの削除').toEqual([]);
    }
  });
}
