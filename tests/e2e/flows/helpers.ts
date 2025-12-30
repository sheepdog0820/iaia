import { expect, Page } from '@playwright/test';

export async function devLogin(page: Page, username = 'admin'): Promise<void> {
  await page.goto('/accounts/dev-login/');

  const targetButton = page
    .locator('.user-card', { hasText: username })
    .locator('button.login-btn:not([disabled])');
  const fallbackButton = page.locator('button.login-btn:not([disabled])').first();
  const loginButton = (await targetButton.count()) ? targetButton.first() : fallbackButton;

  await Promise.all([
    page.waitForURL(url => url.pathname === '/'),
    loginButton.click(),
  ]);

  await expect(page.locator('.welcome-section')).toBeVisible();
}
