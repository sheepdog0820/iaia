import { test, expect } from '@playwright/test';
import { devLogin, setInputValue } from './helpers';

test.describe('groups', () => {
  test('create a group and find it in the list', async ({ page }) => {
    await devLogin(page);
    await page.goto('/accounts/groups/view/');

    await page.click('button[data-bs-target="#createGroupModal"]');
    await expect(page.locator('#createGroupModal')).toBeVisible();

    const groupName = `E2E Group ${Date.now()}`;

    await setInputValue(page, '#groupName', groupName);
    await setInputValue(page, '#groupDescription', 'Created by Playwright');
    await page.selectOption('#groupVisibility', 'public');

    const createResponse = page.waitForResponse(response =>
      response.url().includes('/api/accounts/groups/') &&
      response.request().method() === 'POST'
    );
    await page.click('#saveGroupBtn');
    await createResponse;
    await page.waitForResponse(response => {
      if (response.request().method() !== 'GET') return false;
      return new URL(response.url()).pathname === '/api/accounts/groups/';
    });

    const groupCard = page.locator('.group-card', { hasText: groupName });
    await expect(groupCard).toBeVisible({ timeout: 15000 });

    await page.fill('#groupSearchInput', groupName);
    await expect(page.locator('.group-card', { hasText: groupName })).toBeVisible();
  });
});
