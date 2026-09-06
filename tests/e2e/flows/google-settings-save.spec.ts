import { expect, test } from '@playwright/test';
import { devLogin } from './helpers';

for (const outcome of ['permission', 'authentication', 'forbidden', 'server', 'network', 'success']) {
  test(`Google settings save reports ${outcome} and allows retry`, async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(error.message));
    let attempt = 0;
    let saved = false;
    await page.route('**/api/**', async route => {
      if (!new URL(route.request().url()).pathname.endsWith('/google/integration/')) {
        await route.fulfill({ json: [] });
        return;
      }
      if (route.request().method() === 'PUT') {
        attempt += 1;
        expect(route.request().postDataJSON()).toEqual({ calendar_enabled: true, sheets_enabled: false });
        if (attempt === 1 && outcome !== 'success') {
          if (outcome === 'network') {
            await route.abort('failed');
          } else {
            const status = outcome === 'permission' ? 400 : outcome === 'authentication' ? 401 : outcome === 'forbidden' ? 403 : 500;
            await route.fulfill({ status, json: { calendar_enabled: '<img src=x onerror=alert(1)> credential-detail' } });
          }
          return;
        }
        saved = true;
      }
      await route.fulfill({ json: {
        connected: saved, calendar_enabled: saved, sheets_enabled: false,
        scopes: saved ? ['https://www.googleapis.com/auth/calendar.events'] : [],
      } });
    });
    await devLogin(page, 'admin', '/integrations/');
    await expect(page.locator('#google-status')).toHaveText('未連携');
    await page.locator('#google-calendar-enabled').check();
    await page.locator('#save-google-settings').click();
    const message = page.locator('#integration-message');
    if (outcome !== 'success') {
      const expected = outcome === 'permission'
        ? 'Googleの追加権限を確認できません。「Googleを再連携」から権限を許可して、もう一度保存してください。'
        : outcome === 'authentication' || outcome === 'forbidden'
          ? 'ログイン状態を確認できません。再ログインしてから、もう一度保存してください。'
          : 'Google連携設定の保存を確認できませんでした。通信状態を確認し、再読み込みで保存状態を確認してください。';
      await expect(message).toHaveText(expected);
      await expect(message).toHaveClass(/alert-danger/);
      await expect(message.locator('img')).toHaveCount(0);
      await expect(page.locator('#google-status')).toHaveText('未連携');
      await expect(page.locator('#save-google-settings')).toBeEnabled();
      await page.locator('#save-google-settings').click();
    }
    await expect(message).toHaveText('Google連携設定を保存しました。');
    await expect(page.locator('#google-status')).toContainText('連携済み');
    await expect(page.locator('#google-calendar-enabled')).toBeChecked();
    await expect(page.locator('#save-google-settings')).toBeEnabled();
    expect(errors).toEqual([]);
  });
}

test('Google save locks controls and uses the saved response without another GET', async ({ page }) => {
  let releaseSave!: () => void;
  const saveGate = new Promise<void>(resolve => { releaseSave = resolve; });
  let reads = 0;
  let writes = 0;
  await page.route('**/api/**', async route => {
    if (!new URL(route.request().url()).pathname.endsWith('/google/integration/')) {
      await route.fulfill({ json: [] });
      return;
    }
    if (route.request().method() === 'PUT') {
      writes += 1;
      await saveGate;
      await route.fulfill({ json: { connected: true, calendar_enabled: true, sheets_enabled: false, scopes: [] } });
    } else {
      reads += 1;
      await route.fulfill({ status: reads === 1 ? 200 : 503, json: {
        connected: false, calendar_enabled: false, sheets_enabled: false, scopes: [],
      } });
    }
  });
  await devLogin(page, 'admin', '/integrations/');
  await expect(page.locator('#google-status')).toHaveText('未連携');
  await page.locator('#google-calendar-enabled').check();
  await page.locator('#save-google-settings').click();
  try {
    await expect(page.locator('#save-google-settings')).toBeDisabled();
    await expect(page.locator('#google-calendar-enabled')).toBeDisabled();
    await expect(page.locator('#google-sheets-enabled')).toBeDisabled();
    await expect(page.locator('#integration-message')).toHaveText('Google連携設定を保存しています。');
  } finally {
    releaseSave();
  }
  await expect(page.locator('#integration-message')).toHaveText('Google連携設定を保存しました。');
  await expect(page.locator('#google-status')).toContainText('連携済み');
  await expect(page.locator('#save-google-settings')).toBeEnabled();
  expect(reads).toBe(1);
  expect(writes).toBe(1);
});
