import { test, expect } from '@playwright/test';
import { devLogin, setInputValue } from './helpers';

test.describe('groups', () => {
  test('create a group and find it in the list', async ({ page }) => {
    await devLogin(page);
    await page.goto('/accounts/groups/view/?show_test_data=1');

    const createButton = page.locator('button[data-bs-target="#createGroupModal"]');
    await createButton.click();
    await expect(page.locator('#createGroupModal')).toBeFocused();

    const groupName = `E2E Group ${Date.now()}`;

    await setInputValue(page, '#groupName', groupName);
    await setInputValue(page, '#groupDescription', 'Created by Playwright');
    await page.selectOption('#groupVisibility', 'public');

    const createResponse = page.waitForResponse(response =>
      response.url().includes('/api/accounts/groups/') &&
      response.request().method() === 'POST'
    );
    await page.click('#saveGroupBtn');
    expect((await createResponse).status()).toBe(201);
    await expect(page.locator('#createGroupModal')).toBeHidden();
    await expect(createButton).toBeFocused();

    await page.fill('#groupSearchInput', groupName);
    await expect(page.locator('#groupSearchInput')).toHaveValue(groupName);
    const groupCard = page.locator('.group-card', { hasText: groupName });
    await expect(groupCard).toBeVisible({ timeout: 15000 });
  });
});
