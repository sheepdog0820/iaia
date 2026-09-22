import { expect, test } from '@playwright/test';
import { devLogin } from './helpers';

for (const failure of [false, true]) {
  test(`character list treats ${failure ? 'API errors' : 'names and occupations'} as text`, async ({ page }) => {
    const attack = '"><img src=x onerror="window.__listXss += 1">表示名';
    await page.addInitScript(() => { (window as any).__listXss = 0; });
    await page.route('**/api/accounts/character-sheets/', route => route.fulfill({
      status: failure ? 400 : 200,
      contentType: 'application/json',
      body: JSON.stringify(failure ? { detail: attack } : [{
        id: 123, name: attack, occupation: attack, edition: '6th', status: 'alive',
        age: 30, version: 1, created_at: '2026-09-22T00:00:00Z',
      }]),
    }));
    await devLogin(page, 'admin', '/accounts/character/list/');
    await expect(page.locator('#characterContainer')).toContainText(attack);
    await expect(page.locator('#characterContainer img[src="x"]')).toHaveCount(0);
    if (!failure) await expect(page.locator('.character-card-img')).toHaveAttribute('alt', attack);
    expect(await page.evaluate(() => (window as any).__listXss)).toBe(0);
  });
}
