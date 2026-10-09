import { expect, test } from '@playwright/test';
import { randomUUID } from 'node:crypto';
import { execFileSync } from 'node:child_process';

test('account deletion requires password and confirmation, then ends the login session', async ({ page }) => {
  const pageErrors: string[] = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  const suffix = `${Date.now()}_${test.info().project.name}`;
  const username = `delete_${suffix}`;
  const password = `Test-${randomUUID()}!`;
  await page.goto('/signup/');
  await page.fill('#id_username', username);
  await page.fill('#id_email', `${username}@example.test`);
  await page.fill('#id_password1', password);
  await page.fill('#id_password2', password);
  await page.fill('#id_nickname', '退会確認用ユーザー');
  await Promise.all([page.waitForURL(/\/accounts\/dashboard\//), page.click('#signup-btn')]);

  await page.goto('/accounts/profile/delete/');
  await expect(page.getByText('この操作は取り消せません', { exact: true })).toBeVisible();
  let deletePosts = 0;
  page.on('request', request => {
    if (request.method() === 'POST' && new URL(request.url()).pathname === '/accounts/profile/delete/') {
      deletePosts += 1;
    }
  });
  await page.fill('#confirm', 'DELETE');
  await page.fill('#password', password);
  await page.click('#delete-btn');
  const modal = page.locator('[id^="arkham-confirm-"]');
  await expect(modal).toBeVisible();
  await modal.getByRole('button', { name: 'キャンセル', exact: true }).click();
  await expect(modal).toHaveCount(0);
  expect(deletePosts).toBe(0);
  await page.reload();
  await expect(page.locator('#delete-form')).toBeVisible();

  await page.fill('#confirm', 'DELETE');
  await page.fill('#password', 'intentionally-wrong-password');
  await page.click('#delete-btn');
  await Promise.all([
    page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith('/accounts/profile/delete/')),
    modal.locator('[data-confirm-action]').click(),
  ]);
  await expect(page.getByText('パスワードが正しくありません。', { exact: true }).first()).toBeVisible();
  expect(deletePosts).toBe(1);

  await page.fill('#confirm', 'DELETE');
  await page.fill('#password', password);
  await page.click('#delete-btn');
  await Promise.all([
    page.waitForURL(url => url.pathname === '/'),
    modal.locator('[data-confirm-action]').click(),
  ]);
  expect(deletePosts).toBe(2);
  await expect(page.getByText('アカウントを削除しました。ご利用ありがとうございました。', { exact: true })).toBeVisible();
  const notice = page.locator('#home-messages [role="alert"]');
  const noticeMetrics = () => notice.evaluate(element => {
    const rgb = (value: string) => (value.match(/[\d.]+/g) || []).map(Number);
    const blend = (foreground: number[], background: number[]) => background.map((value, index) =>
      value * (1 - (foreground[3] ?? 1)) + foreground[index] * (foreground[3] ?? 1));
    const luminance = (color: number[]) => color.map(value => {
      const normalized = value / 255;
      return normalized <= 0.04045 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
    }).reduce((sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index], 0);
    const layers: number[][] = [];
    for (let current: Element | null = element; current; current = current.parentElement) {
      layers.unshift(rgb(getComputedStyle(current).backgroundColor));
    }
    const background = layers.reduce((result, layer) => blend(layer, result), [255, 255, 255]);
    const backgroundL = luminance(background);
    const foregroundL = luminance(blend(rgb(getComputedStyle(element).color), background));
    const range = document.createRange();
    range.selectNodeContents(element.querySelector('.home-message-text')!);
    const textRects = Array.from(range.getClientRects());
    return {
      contrast: (Math.max(foregroundL, backgroundL) + 0.05) / (Math.min(foregroundL, backgroundL) + 0.05),
      textRight: Math.max(...textRects.map(rect => rect.right)),
      buttonLeft: element.querySelector('button')!.getBoundingClientRect().left,
    };
  });
  for (const width of [1280, 390]) {
    await page.setViewportSize({ width, height: 844 });
    for (const colorScheme of ['light', 'dark'] as const) {
      await page.emulateMedia({ colorScheme });
      // Measure the actual finished theme transition without overriding styles.
      await expect(page.locator('body')).toHaveCSS('background-color',
        colorScheme === 'light' ? 'rgb(248, 250, 252)' : 'rgb(15, 23, 42)');
      await expect(page.locator('body')).toHaveCSS('color',
        colorScheme === 'light' ? 'rgb(30, 41, 59)' : 'rgb(248, 250, 252)');
      await expect(notice).toBeVisible();
      await expect.poll(async () => (await noticeMetrics()).contrast).toBeGreaterThanOrEqual(4.5);
      const metrics = await noticeMetrics();
      expect(metrics.textRight).toBeLessThanOrEqual(metrics.buttonLeft);
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
      await test.info().attach(`notice-${width}-${colorScheme}-metrics`, { body: JSON.stringify(metrics), contentType: 'application/json' });
      await page.screenshot({ path: test.info().outputPath(`account-deleted-home-${width}-${colorScheme}.png`), fullPage: true });
    }
  }
  const dismiss = page.locator('#home-messages').getByRole('button', { name: '閉じる', exact: true });
  await dismiss.focus();
  await expect(dismiss).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('#home-messages [role="alert"]')).toHaveCount(0);
  await page.reload();
  await expect(page.locator('#home-messages')).toHaveCount(0);
  await page.emulateMedia({ colorScheme: 'light' });
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto('/accounts/dashboard/');
  await expect(page).toHaveURL(/\/accounts\/login\//);
  await page.fill('[name="username"]', `${username}@example.test`);
  await page.fill('[name="password"]', password);
  await page.locator('#email-login-form').getByRole('button', { name: /ログイン/ }).click();
  await expect(page).toHaveURL(/\/accounts\/login\//);
  await expect(page.locator('.alert-danger').first()).toBeVisible();
  expect(pageErrors).toEqual([]);
});

test('nonterminal Stripe contracts keep the account and login when deletion is confirmed', async ({ page }) => {
  const username = `deleteguard_${Date.now()}_${test.info().project.name}`;
  const password = `Test-${randomUUID()}!`;
  await page.goto('/signup/');
  await page.fill('#id_username', username);
  await page.fill('#id_email', `${username}@example.test`);
  await page.fill('#id_password1', password);
  await page.fill('#id_password2', password);
  await page.fill('#id_nickname', '契約終了前の退会確認');
  await Promise.all([page.waitForURL(/\/accounts\/dashboard\//), page.click('#signup-btn')]);

  // Change only this newly registered disposable account. Never load a local
  // environment file or use live Stripe resources to prepare the fixture.
  const fixture = (status: string) => execFileSync(
    process.platform === 'win32' ? 'python' : 'python3',
    ['manage.py', 'shell', '-c', `
import os
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from accounts.models import PremiumSubscription
assert settings.DEBUG and os.environ.get('ENV_FILE') == '' and os.environ.get('APP_ENV') == 'local'
name = os.environ['TABLENO_DELETE_FIXTURE_USER']
assert name.startswith('deleteguard_')
user = get_user_model().objects.get(username=name, email=name+'@example.test', is_staff=False, is_superuser=False)
status = os.environ['TABLENO_DELETE_FIXTURE_STATUS']
if status == 'cleanup':
    user.delete()
else:
    assert status in ('past_due', 'revoked', 'active')
    PremiumSubscription.objects.update_or_create(user=user, defaults={
        'stripe_customer_id': 'cus_e2e_fixture_only', 'stripe_subscription_id': 'sub_e2e_fixture_only',
        'subscription_status': status, 'cancel_at_period_end': status == 'active',
        'revoked_at': timezone.now() if status == 'revoked' else None,
    })
`],
    { env: { ...process.env, TABLENO_DELETE_FIXTURE_USER: username, TABLENO_DELETE_FIXTURE_STATUS: status } },
  );
  try {
    for (const status of ['past_due', 'revoked', 'active']) {
      fixture(status);
      await page.goto('/accounts/profile/delete/');
      await expect(page.getByText('Stripeの契約が終了していません。', { exact: true })).toBeVisible();
      await expect(page.getByRole('link', { name: '課金管理へ', exact: true })).toBeVisible();
      await page.fill('#confirm', 'DELETE');
      await page.fill('#password', password);
      await page.click('#delete-btn');
      await Promise.all([
        page.waitForURL(/\/accounts\/billing\/$/),
        page.locator('[id^="arkham-confirm-"] [data-confirm-action]').click(),
      ]);
      await page.goto('/accounts/dashboard/');
      await expect(page).toHaveURL(/\/accounts\/dashboard\/$/);
    }
  } finally {
    fixture('cleanup');
  }
});
