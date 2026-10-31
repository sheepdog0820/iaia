import { BrowserContext, expect, Page, test } from '@playwright/test';
import { randomUUID } from 'node:crypto';
import { execFileSync } from 'node:child_process';

test.use({ actionTimeout: 15000 });

async function signup(page: Page, username: string, nickname: string): Promise<string> {
  await page.bringToFront();
  await page.goto('/signup/', { waitUntil: 'commit' });
  await expect(page.locator('#email-signup-form')).toBeVisible();
  await expect(page.locator('#signup-btn')).toBeEnabled();
  await page.fill('#id_username', username);
  await page.fill('#id_email', `${username}@example.test`);
  const password = `Vault-${randomUUID()}!`;
  for (const field of ['#id_password1', '#id_password2']) {
    await page.locator(field).focus();
    await page.locator(field).pressSequentially(password);
    await expect(page.locator(field)).toHaveValue(password);
  }
  await page.fill('#id_nickname', nickname);
  await Promise.all([page.waitForURL(/\/accounts\/dashboard\//, { waitUntil: 'commit' }), page.click('#signup-btn')]);
  await expect(page.getByRole('heading', { name: /ダッシュボード/ })).toBeVisible();
  return password;
}

async function openGroup(page: Page, name: string, publicView = false): Promise<void> {
  await page.bringToFront();
  await page.goto('/accounts/groups/view/?show_test_data=1');
  if (publicView) await page.locator('label[for="publicGroupsView"]').click();
  await page.fill('#groupSearchInput', name);
  await page.locator('.group-card', { hasText: name }).click();
  await expect(page.locator('#groupDetailModal')).toBeVisible();
  await expect(page.locator('#group-ownership-panel')).toBeVisible();
}

async function confirm(page: Page): Promise<void> {
  const dialog = page.locator('[id^="arkham-confirm-"]');
  await expect(dialog).toBeVisible();
  await dialog.locator('[data-confirm-action]').click();
}

async function ownershipAction(page: Page, name: string, path: string, status: number, targetUsername?: string): Promise<void> {
  await page.locator('#group-ownership-panel').getByRole('button', { name, exact: true }).click();
  if (targetUsername) await expect(page.locator('[id^="arkham-confirm-"] [data-confirm-message]')).toContainText(targetUsername);
  const response = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith(path));
  await confirm(page);
  expect((await response).status()).toBe(status);
}

function cleanup(names: string[], groupName: string): void {
  // Only the explicitly disposable local/CI SQLite. No environment bootstrap,
  // remote database, real billing customer or staff account may be touched.
  execFileSync(process.platform === 'win32' ? 'python' : 'python3', ['-c', `
import json,os,re,sys
from pathlib import Path
assert os.environ.get('APP_ENV')=='local' and os.environ.get('DB_ENGINE')=='sqlite'
assert os.environ.get('ENV_FILE')=='' and not os.environ.get('AWS_SECRETS_JSON') and not os.environ.get('AWS_SECRETS_FILE')
root=Path.cwd().resolve()
fixture=json.load(sys.stdin)
assert len(fixture['names'])==3 and all(re.fullmatch(r'f02_[abc]_[0-9a-f]{10}',name) for name in fixture['names'])
assert fixture['group_name'].startswith('所有権')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','tableno.settings')
import django;django.setup()
from django.conf import settings
db=Path(settings.DATABASES['default']['NAME']).resolve()
assert (os.environ.get('CI')=='true' and db==root/'db.sqlite3') or (db.parent==root/'tmp' and db.name.startswith('ownership-ui-'))
from django.contrib.auth import get_user_model
from django.db.models import Q
from accounts.models import Group,PremiumSubscription
users=get_user_model().objects.filter(username__in=fixture['names'])
assert not users.filter(Q(is_staff=True)|Q(is_superuser=True)).exists()
assert not PremiumSubscription.objects.filter(user__in=users).exclude(stripe_customer_id='').exists()
Group.objects.filter(name=fixture['group_name']).filter(Q(created_by__in=users)|Q(owner__in=users)).delete()
users.delete()
`], { input: JSON.stringify({ names, group_name: groupName }), encoding: 'utf8' });
}

test('ordinary users consent to ownership, preserve creator history and can leave or delete accounts', async ({ page, browser, baseURL }, testInfo) => {
  test.setTimeout(180000);
  expect(['localhost', '127.0.0.1']).toContain(new URL(baseURL!).hostname);
  const suffix = randomUUID().replaceAll('-', '').slice(0, 10);
  const names = ['a', 'b', 'c'].map(actor => `f02_${actor}_${suffix}`);
  const groupName = `所有権${suffix}`;
  const contexts: BrowserContext[] = [];
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  try {
    const ownerPassword = await signup(page, names[0], '移譲元');
    await page.goto('/accounts/groups/view/?show_test_data=1');
    await page.locator('button[data-bs-target="#createGroupModal"]').click();
    await expect(page.locator('#createGroupModal')).toBeFocused();
    await page.fill('#groupName', groupName);
    await page.selectOption('#groupVisibility', 'public');
    const creation = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith('/api/accounts/groups/'));
    await page.click('#saveGroupBtn');
    expect((await creation).status()).toBe(201);
    await expect(page.locator('#createGroupModal')).toBeHidden();
    await page.fill('#groupSearchInput', groupName);
    await page.locator('.group-card', { hasText: groupName }).click();
    await expect(page.locator('#group-ownership-panel').getByRole('heading', { name: '所有権の移譲' })).toBeVisible();

    const actor = async (username: string, nickname: string, mobile = false) => {
      const context = await browser.newContext({ baseURL, viewport: mobile ? { width: 390, height: 844 } : { width: 1280, height: 900 } });
      contexts.push(context);
      const actorPage = await context.newPage();
      actorPage.on('pageerror', error => errors.push(error.message));
      await signup(actorPage, username, nickname);
      await openGroup(actorPage, groupName, true);
      const joining = actorPage.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith('/join/'));
      await actorPage.getByRole('button', { name: /グループに参加$/ }).click();
      expect((await joining).status()).toBe(201);
      await openGroup(actorPage, groupName);
      return actorPage;
    };
    const target = await actor(names[1], '移譲先', true);
    const other = await actor(names[2], '他の管理者');
    await openGroup(page, groupName);
    await page.locator('.member-item', { hasText: '他の管理者' }).getByRole('button', { name: '管理者にする', exact: true }).click();
    const promotion = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith('/set_member_role/'));
    await confirm(page);
    expect((await promotion).status()).toBe(200);
    await openGroup(other, groupName);
    await expect(other.locator('#group-ownership-panel').getByLabel('移譲先のメンバー')).toHaveCount(0);

    const start = async () => {
      await openGroup(page, groupName);
      await page.locator('#group-ownership-panel').getByLabel('移譲先のメンバー').selectOption({ label: `移譲先（ユーザー名: ${names[1]}）` });
      await ownershipAction(page, '移譲を申請', '/ownership-transfer/', 201, names[1]);
      await expect(page.locator('#group-ownership-panel')).toContainText('承諾待ち');
    };

    await start();
    await openGroup(target, groupName);
    await expect(target.locator('#group-ownership-panel')).toContainText('あなた宛て');
    await ownershipAction(page, '申請を取り消す', '/ownership-transfer/cancel/', 200);
    await ownershipAction(target, '承諾して引き継ぐ', '/ownership-transfer/accept/', 404);
    await expect(target.locator('#group-ownership-panel').getByRole('button', { name: '承諾して引き継ぐ' })).toHaveCount(0);

    await start();
    await openGroup(target, groupName);
    await ownershipAction(target, '辞退する', '/ownership-transfer/decline/', 200);
    await start();
    await openGroup(other, groupName);
    await expect(other.locator('#group-ownership-panel').getByRole('button', { name: '承諾して引き継ぐ' })).toHaveCount(0);
    await openGroup(target, groupName);
    await ownershipAction(target, '承諾して引き継ぐ', '/ownership-transfer/accept/', 200);
    await expect(target.locator('#group-ownership-panel')).toContainText('現在の所有者: 移譲先');
    await expect(target.locator('#group-ownership-panel').getByLabel('移譲先のメンバー')).toBeVisible();

    await openGroup(page, groupName);
    await expect(page.locator('#group-ownership-panel').getByLabel('移譲先のメンバー')).toHaveCount(0);
    await page.getByRole('button', { name: /グループを退出$/ }).click();
    await confirm(page);
    await expect(page.locator('#groupDetailModal')).toBeHidden();
    await page.goto('/integrations/');
    await expect(page.locator('#group-links')).toContainText('管理権限のあるグループがありません。');
    await expect(page.locator('#discord-group option', { hasText: groupName })).toHaveCount(0);
    await page.goto('/accounts/profile/delete/');
    await page.fill('#confirm', 'DELETE');
    await page.fill('#password', ownerPassword);
    await page.click('#delete-btn');
    await Promise.all([page.waitForURL(url => url.pathname === '/'), confirm(page)]);
    await openGroup(target, groupName);
    await expect(target.locator('#groupDetailModal')).toContainText('退会済みユーザー');
    await expect(target.locator('#group-ownership-panel')).toContainText('現在の所有者: 移譲先');
    await target.locator('#group-ownership-panel').scrollIntoViewIfNeeded();
    expect(await target.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
    await target.screenshot({ path: testInfo.outputPath('ownership-mobile.png') });
    expect(errors).toEqual([]);
  } finally {
    await page.close();
    const closed = await Promise.allSettled(contexts.map(context => context.close()));
    cleanup(names, groupName);
    const failed = closed.find(result => result.status === 'rejected');
    if (failed?.status === 'rejected') throw failed.reason;
  }
});
