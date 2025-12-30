import { test, expect } from '@playwright/test';
import { devLogin } from './helpers';

test.describe('groups', () => {
  test('create a group and find it in the list', async ({ page }) => {
    await devLogin(page);
    await page.goto('/accounts/groups/view/');

    await page.click('button[data-bs-target="#createGroupModal"]');
    await expect(page.locator('#createGroupModal')).toBeVisible();

    const groupName = `E2E Group ${Date.now()}`;

    await page.fill('#groupName', groupName);
    await page.fill('#groupDescription', 'Created by Playwright');
    await page.selectOption('#groupVisibility', 'public');

    await Promise.all([
      page.waitForResponse(response =>
        response.url().includes('/api/accounts/groups/') &&
        response.request().method() === 'POST'
      ),
      page.click('#saveGroupBtn'),
    ]);

    const groupCard = page.locator('.group-card', { hasText: groupName });
    await expect(groupCard).toBeVisible();

    await page.fill('#groupSearchInput', groupName);
    await expect(page.locator('.group-card', { hasText: groupName })).toBeVisible();
  });
});
