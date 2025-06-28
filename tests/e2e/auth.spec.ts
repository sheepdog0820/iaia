import { test, expect } from '@playwright/test';

test.describe('認証機能', () => {
  test('ログインページが表示される', async ({ page }) => {
    await page.goto('/accounts/login/');
    
    // ページタイトルの確認
    await expect(page).toHaveTitle(/ログイン/);
    
    // ソーシャルログインボタンの確認
    await expect(page.locator('text=Googleでログイン')).toBeVisible();
    await expect(page.locator('text=X (Twitter)でログイン')).toBeVisible();
  });

  test('開発用ログインでログインできる', async ({ page }) => {
    // 開発用ログインページへ
    await page.goto('/accounts/dev-login/');
    
    // adminユーザーでログイン（管理者セクションの「このユーザーでログイン」ボタンをクリック）
    await page.locator('h3:has-text("管理者")').locator('..').locator('button:has-text("このユーザーでログイン")').click();
    
    // ホームページへのリダイレクトを確認
    await expect(page).toHaveURL('http://localhost:8000/');
    
    // ユーザー名が表示されていることを確認（ナビゲーションバー内）
    await expect(page.locator('button:has-text("アーカムの管理者")')).toBeVisible();
  });

  test('ソーシャルログインリンクが機能する', async ({ page }) => {
    await page.goto('/accounts/login/');
    
    // Googleログインリンクの確認
    const googleLink = page.locator('a:has-text("Googleでログイン")');
    await expect(googleLink).toBeVisible();
    await expect(googleLink).toHaveAttribute('href', '/auth/google/login/');
    
    // Twitterログインリンクの確認
    const twitterLink = page.locator('a:has-text("X (Twitter)でログイン")');
    await expect(twitterLink).toBeVisible();
    await expect(twitterLink).toHaveAttribute('href', '/auth/twitter/login/');
  });

  test('ログアウトできる', async ({ page }) => {
    // 開発用ログインでログイン
    await page.goto('/accounts/dev-login/');
    await page.locator('h3:has-text("管理者")').locator('..').locator('button:has-text("このユーザーでログイン")').click();
    
    // ホームページに遷移したことを確認
    await expect(page).toHaveURL('http://localhost:8000/');
    
    // ユーザードロップダウンを開く
    await page.click('button[data-bs-toggle="dropdown"]:has-text("アーカムの管理者")');
    
    // ログアウトリンクをクリック
    await page.click('a:has-text("ログアウト")');
    
    // ログインページにリダイレクトされることを確認
    await expect(page).toHaveURL(/\/auth\/login\//);
  });
});