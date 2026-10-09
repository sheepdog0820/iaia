import { expect, test } from '@playwright/test';

test.describe('auth release flows', () => {
  test('user can sign up and log in with email credentials', async ({ page }) => {
    const pageErrors: string[] = [];
    page.on('pageerror', error => pageErrors.push(error.message));
    const timestamp = Date.now();
    const username = `e2e_user_${timestamp}`;
    const email = `${username}@example.com`;
    const password = `Rlyeh-${timestamp}-Vault!`;
    const nickname = `E2E User ${timestamp}`;

    await page.goto('/signup/');
    await expect(page.locator('#email-signup-form')).toBeVisible();

    await page.fill('#id_username', username);
    await page.fill('#id_email', email);
    await page.fill('#id_password1', password);
    await page.fill('#id_password2', password);
    await page.fill('#id_nickname', nickname);
    await page.fill('#id_trpg_history', 'Playwright signup flow.');

    await Promise.all([
      page.waitForURL(/\/accounts\/dashboard\//),
      page.click('#signup-btn'),
    ]);
    await expect(page.locator('body')).toContainText(nickname);

    await page.goto('/accounts/logout/');
    await expect(page).toHaveURL(url => url.pathname === '/');
    await expect(page.locator('body')).not.toContainText(nickname);
    await page.screenshot({ path: test.info().outputPath('logout-public-home.png'), fullPage: true });

    // A public landing page must not imply that the login session survived.
    await page.goto('/accounts/dashboard/');
    await expect(page).toHaveURL(/\/accounts\/login\//);
    expect(new URL(page.url()).searchParams.get('next')).toBe('/accounts/dashboard/');

    // Verify the default login destination without the protected-page next.
    await page.goto('/accounts/login/');

    await page.fill('#id_username', email);
    await page.fill('#id_password', password);
    await Promise.all([
      page.waitForURL(url => url.pathname === '/'),
      page.click('#email-login-form button[type="submit"]'),
    ]);

    await expect(page.locator('body')).toContainText(nickname);
    expect(pageErrors).toEqual([]);
  });

  test('login page exposes OAuth state for release verification', async ({ page }) => {
    await page.goto('/login/');
    await expect(page.locator('#email-login-form')).toBeVisible();

    const providerButtons = page.locator('.social-btn');
    const warning = page.locator('.alert-warning', { hasText: 'ソーシャルログインは未設定です' });
    const providerCount = await providerButtons.count();

    if (providerCount > 0) {
      await expect(providerButtons.first()).toBeVisible();
      const labels = await providerButtons.allTextContents();
      expect(labels.join(' ')).toMatch(/Google|Discord|X/);
    } else {
      await expect(warning).toBeVisible();
      await expect(warning).toContainText('Google');
      await expect(warning).toContainText('Discord');
      await expect(warning).toContainText('X');
    }
  });
});
