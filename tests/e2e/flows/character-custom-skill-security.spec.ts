import { test, expect } from '@playwright/test';
import { devLogin } from './helpers';

for (const edition of ['6th', '7th']) {
  test(`${edition} custom skill names render as text without executing markup`, async ({ page }) => {
    const attack = '\"><img src=x onerror="window.__customSkillXss += 1">技能名';

    await page.addInitScript(() => {
      (window as any).__customSkillXss = 0;
    });
    await devLogin(page, 'admin', `/accounts/character/create/${edition}/`);

    await page.evaluate(name => {
      const host = document.createElement('div');
      host.id = 'custom-skill-security-host';
      host.innerHTML = (window as any).createCustomSkillItemHTML(name, 'all');
      document.body.appendChild(host);
    }, attack);

    const customSkill = page.locator('#custom-skill-security-host .custom-skill');
    await expect(page.locator('img[src="x"]')).toHaveCount(0);
    await expect.poll(() => page.evaluate(() => (window as any).__customSkillXss)).toBe(0);
    await expect(customSkill.locator('.custom-skill-name')).toHaveValue(attack);
  });
}
