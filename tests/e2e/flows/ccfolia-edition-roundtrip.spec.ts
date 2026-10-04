import { expect, test } from '@playwright/test';
import { randomUUID } from 'node:crypto';

for (const edition of ['6th', '7th']) {
  for (const output of ['server', 'copy']) {
    test(`${edition} ${output} export selects the same edition on free import`, async ({ page }) => {
      const errors: string[] = [];
      page.on('pageerror', error => errors.push(error.message));
      // Verify the real copy button and payload, not OS clipboard permissions.
      await page.addInitScript(() => {
        Object.defineProperty(navigator, 'clipboard', {
          value: { writeText: async (text: string) => { (window as any).roundtripClipboard = text; } },
        });
      });
      const suffix = `${Date.now()}_${test.info().project.name}_${edition}_${output}`;
      await page.goto('/signup/');
      await page.fill('#id_username', `roundtrip_${suffix}`);
      await page.fill('#id_email', `roundtrip_${suffix}@example.com`);
      const password = `Test-${randomUUID()}!`;
      await page.fill('#id_password1', password);
      await page.fill('#id_password2', password);
      await page.fill('#id_nickname', '版情報の往復検証');
      await Promise.all([page.waitForURL(/\/accounts\/dashboard\//), page.click('#signup-btn')]);
      await page.goto('/');
      await page.waitForFunction(() => (window as any).axios?.post);
      const character = await page.evaluate(async ({ edition, suffix }) => {
        const response = await (window as any).axios.post(
          `/api/accounts/character-sheets/create_${edition === '7th' ? '7th' : '6th'}_edition/`,
          {
            name: `往復探索者 ${suffix}`, age: 20,
            ...Object.fromEntries(['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu']
              .map(name => [`${name}_value`, edition === '7th' ? 65 : 13])),
            ...(edition === '7th' ? { luck: 70 } : {}),
          }
        );
        return response.data;
      }, { edition, suffix });
      let payload: any;
      if (output === 'server') {
        const response = await page.request.get(`/api/accounts/character-sheets/${character.id}/ccfolia_json/`);
        expect(response.status()).toBe(200);
        payload = await response.json();
      } else {
        await page.goto(`/accounts/character/${character.id}/`);
        await expect(page.locator('#ccfoliaExportLink')).toBeEnabled();
        await page.getByRole('button', { name: 'その他の操作', exact: true }).click();
        await expect(page.locator('#ccfoliaExportLink')).toBeVisible();
        await page.locator('#ccfoliaExportLink').click();
        await expect.poll(() => page.evaluate(() => (window as any).roundtripClipboard)).toBeTruthy();
        payload = JSON.parse(await page.evaluate(() => (window as any).roundtripClipboard));
      }
      expect(payload.edition).toBe(edition);
      await page.goto('/accounts/character/list/');
      await page.locator('#createCharacterDropdown').click();
      await page.locator('button[data-bs-target="#ccfoliaImportModal"]').click();
      await expect(page.locator('#ccfoliaImportModal')).toBeVisible();
      await page.locator('#ccfoliaImportJson').fill(JSON.stringify(payload));
      await expect(page.locator('#ccfoliaImportEdition')).toHaveValue(edition);
      const [importResponse] = await Promise.all([
        page.waitForResponse(response => response.url().includes('/import_ccfolia_json/')
          && response.request().method() === 'POST'),
        page.locator('#ccfoliaImportSubmitBtn').click(),
      ]);
      expect(importResponse.status()).toBe(201);
      // Read the persisted record; browser response bodies can disappear at navigation.
      await expect(page).toHaveURL(/\/accounts\/character\/6th\/\d+\//);
      const savedId = new URL(page.url()).pathname.match(/\/character\/6th\/(\d+)\//)![1];
      expect(Number(savedId)).not.toBe(character.id);
      const savedResponse = await page.request.get(`/api/accounts/character-sheets/${savedId}/`);
      expect(savedResponse.status()).toBe(200);
      const saved = await savedResponse.json();
      expect(saved.edition).toBe(edition);
      expect(saved.str_value).toBe(character.str_value);
      expect(saved.name).toBe(character.name);
      if (edition === '7th') expect(saved.character_7th.current_luck).toBe(70);
      // Both editions use the shared detail route with its legacy 6th prefix.
      await expect(page).toHaveURL(new RegExp(`/accounts/character/6th/${saved.id}/`));
      await expect(page.getByRole('heading', { name: new RegExp(`基本情報 ${edition === '7th' ? '7' : '6'}版`) }))
        .toBeVisible();
      expect(errors).toEqual([]);
    });
  }
}
