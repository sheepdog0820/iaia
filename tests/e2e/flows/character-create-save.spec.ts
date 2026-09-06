import { expect, test } from '@playwright/test';
import { devLogin } from './helpers';

for (const edition of ['6th', '7th']) {
  test(`${edition} character can be created, edited and reopened through the form`, async ({ page }) => {
    await devLogin(page, 'investigator1');
    await page.goto(`/accounts/character/create/${edition}/`);
    const name = `保存確認 ${edition} ${test.info().project.name} ${Date.now()}`;
    await page.locator('#character-name').fill(name);
    await page.locator('#character-name-kana').fill('ほぞんかくにん');
    await page.locator('#age').fill('28');
    const imageBuffer = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAEklEQVR4nGNkYPjPwMDAxAAGAAsfAQMU4wsAAAAAAElFTkSuQmCC', 'base64');
    await expect(page.locator('#character-images')).toHaveAttribute('data-max-images', '5');
    await page.locator('#character-images').setInputFiles(
      Array.from({ length: 5 }, (_, index) => ({ name: `立ち絵${index + 1}.png`, mimeType: 'image/png', buffer: imageBuffer }))
    );
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
    await page.locator('#skills-tab').click();
    await page.locator('#exploration-tab').click();
    await page.locator('.occupation-skill[data-skill="spot_hidden"]').fill('20');
    await page.locator('.interest-skill[data-skill="spot_hidden"]').fill('10');
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
    await expect(page.locator('.character-edit-thumbnail-image')).toHaveCount(5);
    for (const thumbnail of await page.locator('.character-edit-thumbnail-image').all()) {
      await expect(thumbnail).toBeVisible();
      await expect.poll(() => thumbnail.evaluate((img: HTMLImageElement) => img.naturalWidth)).toBe(2);
    }
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

    await page.locator('#skills-tab').click();
    await page.locator('#exploration-tab').click();
    await expect(page.locator('.occupation-skill[data-skill="spot_hidden"]')).toHaveValue('20');
    await expect(page.locator('.interest-skill[data-skill="spot_hidden"]')).toHaveValue('10');
    await page.locator('.occupation-skill[data-skill="spot_hidden"]').fill('30');
    await page.locator('.interest-skill[data-skill="spot_hidden"]').fill('15');

    await page.locator('#basic-info-tab').click();
    await page.locator('#character-name').fill(`${name} 更新`);
    await page.locator('#character-name-kana').fill('こうしんご');
    await page.locator('#age').fill('35');
    await page.locator('#abilities-tab').click();
    const updatedAbility = edition === '6th' ? '14' : '70';
    await page.locator('#con').fill(updatedAbility);
    await page.locator('#pow').fill(updatedAbility);
    const [updatedResponse] = await Promise.all([
      page.waitForResponse(r => new URL(r.url()).pathname === `/accounts/character-sheets/${created.id}/` && r.request().method() === 'PATCH'),
      page.locator('#footerSaveCharacter').click(),
    ]);
    expect(updatedResponse.status()).toBe(200);
    await page.waitForURL(`**/accounts/character/6th/${created.id}/`);
    await expect(page.locator('.character-name')).toHaveText(`${name} 更新`);
    await page.goto(`/accounts/character/create/${edition}/?id=${created.id}`);
    await expect(page.locator('#character-name')).toHaveValue(`${name} 更新`);
    await expect(page.locator('#character-name-kana')).toHaveValue('こうしんご');
    await expect(page.locator('#age')).toHaveValue('35');
    await page.locator('#abilities-tab').click();
    await expect(page.locator('#con')).toHaveValue(updatedAbility);
    await expect(page.locator('#pow')).toHaveValue(updatedAbility);
    const updated = await page.request.get(`/api/accounts/character-sheets/${created.id}/`);
    expect(updated.status()).toBe(200);
    const data = await updated.json();
    expect(data.edition).toBe(edition);
    expect(data.hit_points_max).toBe(13);
    expect(data.magic_points_max).toBe(14);
    if (luck !== null) expect(data.character_7th.current_luck).toBe(luck);
    await page.locator('#skills-tab').click();
    await page.locator('#exploration-tab').click();
    await expect(page.locator('.occupation-skill[data-skill="spot_hidden"]')).toHaveValue('30');
    await expect(page.locator('.interest-skill[data-skill="spot_hidden"]')).toHaveValue('15');
    const skillsResponse = await page.request.get(`/api/accounts/character-sheets/${created.id}/skills/`);
    expect(skillsResponse.status()).toBe(200);
    const skillsPayload = await skillsResponse.json();
    const skill = (Array.isArray(skillsPayload) ? skillsPayload : skillsPayload.results)
      .find((item: any) => item.skill_name === '目星');
    expect(skill).toMatchObject({ base_value: 25, occupation_points: 30, interest_points: 15 });
    await page.locator('#basic-info-tab').click();
    await expect(page.locator('.character-edit-thumbnail-image')).toHaveCount(5);
    await page.locator('#character-images').setInputFiles({ name: '上限超過.png', mimeType: 'image/png', buffer: imageBuffer });
    await expect(page.locator('.alert').filter({ hasText: 'キャラクター画像は最大5枚まで選択できます。' })).toBeVisible();
    expect(await page.locator('#character-images').evaluate((input: HTMLInputElement) => input.files?.length)).toBe(0);
    await page.locator('[data-delete-existing-image-id]').first().click();
    const confirmation = page.locator('.modal.show').filter({ hasText: '既存の立ち絵を削除しますか？' });
    await expect(confirmation).toBeVisible();
    const [deleted] = await Promise.all([
      page.waitForResponse(r => r.url().includes(`/character-sheets/${created.id}/images/`) && r.request().method() === 'DELETE'),
      confirmation.locator('[data-confirm-action]').click(),
    ]);
    expect(deleted.status()).toBe(204);
    await expect(page.locator('.character-edit-thumbnail-image')).toHaveCount(4);
    await page.reload();
    await expect(page.locator('.character-edit-thumbnail-image')).toHaveCount(4);
  });
}
