import { expect, test } from '@playwright/test';
import { randomUUID } from 'node:crypto';

test('ordinary free user can open scenario tools and import a CCFOLIA character', async ({ page }) => {
  const suffix = `${Date.now()}_${test.info().project.name}`;
  await page.goto('/signup/');
  await page.fill('#id_username', `free_${suffix}`);
  await page.fill('#id_email', `free_${suffix}@example.com`);
  const password = `Test-${randomUUID()}!`;
  await page.fill('#id_password1', password);
  await page.fill('#id_password2', password);
  await page.fill('#id_nickname', '無料プランのKP');
  await Promise.all([page.waitForURL(/\/accounts\/dashboard\//), page.click('#signup-btn')]);
  await page.goto('/');
  await expect(page.locator('#scenarios-link')).toBeVisible();
  await page.locator('#add-scenario-btn').click();
  await expect(page).toHaveURL(/\/api\/scenarios\/archive\/view\//);
  await expect(page.locator('#scenariosList')).toBeVisible();

  await page.goto('/accounts/character/list/');
  await page.locator('#createCharacterDropdown').click();
  await page.locator('button[data-bs-target="#ccfoliaImportModal"]').click();
  await expect(page.locator('#ccfoliaImportModal')).toBeVisible();
  await page.locator('#ccfoliaImportAge').fill('20');
  const name = `無料インポート ${suffix}`;
  await page.locator('#ccfoliaImportJson').fill(JSON.stringify({
    kind: 'character',
    data: {
      name, commands: 'CCB<=50 【目星】',
      status: [{ label: 'HP', value: 10, max: 10 }, { label: 'MP', value: 10, max: 10 }, { label: 'SAN', value: 50, max: 50 }],
      params: ['STR', 'CON', 'POW', 'DEX', 'APP', 'SIZ', 'INT', 'EDU'].map(label => ({ label, value: '10' })),
    },
  }));
  const [response] = await Promise.all([
    page.waitForResponse(r => r.url().includes('/import_ccfolia_json/') && r.request().method() === 'POST'),
    page.locator('#ccfoliaImportSubmitBtn').click(),
  ]);
  expect(response.status()).toBe(201);
  await page.waitForURL(/\/accounts\/character\/6th\/\d+\//);
  const characterId = new URL(page.url()).pathname.match(/\/character\/6th\/(\d+)\//)![1];
  const saved = await page.request.get(`/api/accounts/character-sheets/${characterId}/`);
  expect(saved.status()).toBe(200);
  expect((await saved.json()).name).toBe(name);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: test.info().outputPath('free-import-mobile.png'), fullPage: true });
  for (const edition of ['6th', '7th']) {
    await page.goto(`/accounts/character/create/${edition}/`);
    await expect(page.locator('#character-images')).toHaveAttribute('data-max-images', '5');
    await expect(page.locator('body')).toContainText('現在の添付上限: 最大5枚');
  }
});
