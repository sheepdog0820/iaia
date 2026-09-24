import { expect, test } from '@playwright/test';
import { randomUUID } from 'node:crypto';
import { execFileSync } from 'node:child_process';

test('account deletion requires password and confirmation, then ends the login session', async ({ page }) => {
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
    page.waitForURL(/\/accounts\/login\//),
    modal.locator('[data-confirm-action]').click(),
  ]);
  expect(deletePosts).toBe(2);
  await page.goto('/accounts/dashboard/');
  await expect(page).toHaveURL(/\/accounts\/login\//);
  await page.fill('[name="username"]', `${username}@example.test`);
  await page.fill('[name="password"]', password);
  await page.locator('#email-login-form').getByRole('button', { name: /ログイン/ }).click();
  await expect(page).toHaveURL(/\/accounts\/login\//);
  await expect(page.locator('.alert-danger').first()).toBeVisible();
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
