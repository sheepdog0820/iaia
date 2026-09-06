import { expect, test } from '@playwright/test';
import { devLogin } from './helpers';

for (const edition of ['6th', '7th']) {
  test(`${edition} character can be created through the form and reopened for editing`, async ({ page }) => {
    await devLogin(page, 'investigator1');
    await page.goto(`/accounts/character/create/${edition}/`);
    const name = `保存確認 ${edition} ${test.info().project.name} ${Date.now()}`;
    await page.locator('#character-name').fill(name);
    await page.locator('#character-name-kana').fill('ほぞんかくにん');
    await page.locator('#age').fill('28');
    await page.locator('#abilities-tab').click();
    const ability = edition === '6th' ? '12' : '60';
    for (const field of ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu']) {
      await page.locator(`#${field}`).fill(ability);
    }
    const luck = edition === '7th' ? Number(await page.locator('#luck').inputValue()) : null;
    if (luck !== null) {
      expect(luck).toBeGreaterThanOrEqual(15);
      expect(luck).toBeLessThanOrEqual(90);
      expect(luck % 5).toBe(0);
    }
    page.on('dialog', dialog => dialog.accept());
    const [response] = await Promise.all([
      page.waitForResponse(r => r.url().includes(`/create_${edition}_edition/`) && r.request().method() === 'POST'),
      page.locator('#footerSaveCharacter').click(),
    ]);
    expect(response.status()).toBe(201);
    const created = await response.json();
    await page.waitForURL('**/accounts/character/list/');
    await page.goto(`/accounts/character/create/${edition}/?id=${created.id}`);
    await expect(page.locator('#character-name')).toHaveValue(name);
    await expect(page.locator('#character-name-kana')).toHaveValue('ほぞんかくにん');
    await expect(page.locator('#age')).toHaveValue('28');
    await page.locator('#abilities-tab').click();
    for (const field of ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu']) {
      await expect(page.locator(`#${field}`)).toHaveValue(ability);
    }
    const savedResponse = await page.request.get(`/api/accounts/character-sheets/${created.id}/`);
    expect(savedResponse.status()).toBe(200);
    const saved = await savedResponse.json();
    expect(saved.edition).toBe(edition);
    expect(saved.hit_points_max).toBe(12);
    expect(saved.magic_points_max).toBe(12);
    if (luck !== null) expect(saved.character_7th.current_luck).toBe(luck);
  });
}
