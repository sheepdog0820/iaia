import { expect, Page, test } from '@playwright/test';
import { randomUUID } from 'node:crypto';

async function signUp(page: Page, suffix: string): Promise<void> {
  await page.goto('/signup/');
  await page.fill('#id_username', `release_${suffix}`);
  await page.fill('#id_email', `release_${suffix}@example.com`);
  const password = `Vault-${randomUUID()}!`;
  await page.fill('#id_password1', password);
  await page.fill('#id_password2', password);
  await page.fill('#id_nickname', `通常利用者 ${suffix}`);
  await Promise.all([
    page.waitForURL(/\/accounts\/dashboard\//),
    page.click('#signup-btn'),
  ]);
}

test('registered owner creates a private group and completes a session; outsider cannot read it', async ({ page, browser }) => {
  const suffix = `${Date.now()}_${test.info().project.name}`;
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('dialog', dialog => dialog.accept());
  await signUp(page, suffix);

  await page.goto('/accounts/groups/view/?show_test_data=1');
  await page.click('button[data-bs-target="#createGroupModal"]');
  await expect(page.locator('#createGroupModal')).toBeVisible();
  const groupName = `通常利用者の非公開グループ ${suffix}`;
  await page.click('#groupName');
  await page.fill('#groupName', groupName);
  await expect(page.locator('#groupName')).toHaveValue(groupName);
  await page.fill('#groupDescription', '正式公開の操作確認用');
  await page.selectOption('#groupVisibility', 'private');
  const [groupResponse] = await Promise.all([
    page.waitForResponse(response => new URL(response.url()).pathname === '/api/accounts/groups/' && response.request().method() === 'POST'),
    page.click('#saveGroupBtn'),
  ]);
  expect(groupResponse.status()).toBe(201);
  const group = await groupResponse.json();
  await expect(page.locator('.group-card', { hasText: groupName })).toBeVisible();

  await page.goto('/api/schedules/calendar/view/');
  await page.click('button[data-bs-target="#newSessionModal"]');
  await expect(page.locator('#newSessionModal')).toBeVisible();
  const title = `通常利用者のセッション ${suffix}`;
  await page.click('#sessionTitle');
  await page.fill('#sessionTitle', title);
  await expect(page.locator('#sessionTitle')).toHaveValue(title);
  const date = new Date(Date.now() + 86400000);
  const pad = (value: number) => String(value).padStart(2, '0');
  const localDate = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T18:00`;
  await page.fill('#sessionDate', localDate);
  await page.fill('#sessionDuration', '2');
  await page.fill('#sessionLocation', 'オンライン');
  await expect(page.locator(`#sessionGroup option[value="${group.id}"]`)).toBeAttached();
  await page.selectOption('#sessionGroup', String(group.id));
  await page.selectOption('#sessionVisibility', 'group');
  const [sessionResponse] = await Promise.all([
    page.waitForResponse(response => new URL(response.url()).pathname === '/api/schedules/sessions/' && response.request().method() === 'POST'),
    page.click('#saveSessionBtn'),
  ]);
  expect(sessionResponse.status()).toBe(201);
  const session = await sessionResponse.json();
  await page.goto(`/api/schedules/sessions/${session.id}/detail/`);
  await expect(page.locator('h3', { hasText: title }).first()).toBeVisible();
  await page.click('button[data-bs-target="#editSessionModal"]');
  await expect(page.locator('#editSessionModal')).toBeVisible();
  await page.selectOption('#editSessionStatus', 'completed');
  const [updateResponse] = await Promise.all([
    page.waitForResponse(response => new URL(response.url()).pathname === `/api/schedules/sessions/${session.id}/` && response.request().method() === 'PATCH'),
    page.waitForNavigation({ waitUntil: 'domcontentloaded' }),
    page.click('#editSessionModal button[onclick="updateSession()"]'),
  ]);
  expect(updateResponse.status()).toBe(200);
  await page.reload();
  await expect(page.locator('span.badge', { hasText: '完了' }).first()).toBeVisible();
  const savedResponse = await page.request.get(`/api/schedules/sessions/${session.id}/`);
  expect(savedResponse.status()).toBe(200);
  const saved = await savedResponse.json();
  expect(saved.status).toBe('completed');
  expect(saved.duration_minutes).toBe(120);
  await page.screenshot({ path: test.info().outputPath('owner-completed.png'), fullPage: true });

  const outsiderContext = await browser.newContext({ baseURL: new URL(page.url()).origin });
  try {
    const outsider = await outsiderContext.newPage();
    await signUp(outsider, `${suffix}_outside`);
    expect((await outsider.request.get(`/api/accounts/groups/${group.id}/`)).status()).toBe(404);
    expect((await outsider.request.get(`/api/schedules/sessions/${session.id}/`)).status()).toBe(404);
    const deniedPage = await outsider.goto(`/api/schedules/sessions/${session.id}/detail/`);
    expect(deniedPage?.status()).toBe(403);
    await expect(outsider.locator('body')).not.toContainText(title);
    await expect(outsider.getByRole('heading', { name: 'アクセス権限がありません' })).toBeVisible();
    await expect(outsider.getByRole('link', { name: 'ホームへ' })).toBeVisible();
    await expect(outsider.locator('body')).not.toContainText('Django REST framework');
    await outsider.screenshot({ path: test.info().outputPath('outsider-denied.png'), fullPage: true });
    await outsider.setViewportSize({ width: 390, height: 844 });
    const deniedPoll = await outsider.goto(`/api/schedules/sessions/${session.id}/date-poll/`);
    expect(deniedPoll?.status()).toBe(403);
    await expect(outsider.getByRole('heading', { name: 'アクセス権限がありません' })).toBeVisible();
    await expect(outsider.locator('body')).not.toContainText(title);
    const homeBox = await outsider.getByRole('link', { name: 'ホームへ' }).boundingBox();
    const backBox = await outsider.getByRole('link', { name: '前のページへ戻る' }).boundingBox();
    expect(homeBox).not.toBeNull();
    expect(backBox).not.toBeNull();
    expect(Math.abs(homeBox!.x - backBox!.x)).toBeLessThan(1);
    expect(Math.abs(homeBox!.width - backBox!.width)).toBeLessThan(1);
    await outsider.screenshot({ path: test.info().outputPath('outsider-poll-denied-mobile.png'), fullPage: true });
  } finally {
    await outsiderContext.close();
  }
  expect(errors).toEqual([]);
});
