import { expect, Page, test } from '@playwright/test';
import { randomUUID } from 'node:crypto';

async function signUp(page: Page, suffix: string, nickname?: string): Promise<void> {
  await page.goto('/signup/');
  await page.fill('#id_username', `release_${suffix}`);
  await page.fill('#id_email', `release_${suffix}@example.com`);
  const password = `Vault-${randomUUID()}!`;
  await page.fill('#id_password1', password);
  await page.fill('#id_password2', password);
  await page.fill('#id_nickname', nickname ?? `通常利用者 ${suffix}`);
  await Promise.all([
    page.waitForURL(/\/accounts\/dashboard\//),
    page.click('#signup-btn'),
  ]);
}

test('anonymous guest joins and a normally registered user claims the participant', async ({ page, browser }) => {
  const suffix = `${Date.now()}_${test.info().project.name}`;
  await signUp(page, `guestgm_${suffix}`);
  const setup = await page.evaluate(async suffix => {
    const group = (await (window as any).axios.post('/api/accounts/groups/', {
      name: `ゲスト検証 ${suffix}`, visibility: 'private',
    })).data;
    const session = (await (window as any).axios.post('/api/schedules/sessions/', {
      title: `ゲスト参加 ${suffix}`, group: group.id, visibility: 'group',
      date: new Date(Date.now() + 86400000).toISOString(), duration_minutes: 120,
    })).data;
    return { session };
  }, suffix);
  await page.goto('/integrations/');
  await page.selectOption('#integration-session', String(setup.session.id));
  const [issued] = await Promise.all([
    page.waitForResponse(response => new URL(response.url()).pathname === `/api/sessions/${setup.session.id}/guest-invitations/` && response.request().method() === 'POST'),
    page.getByRole('button', { name: 'ゲスト招待URLを発行' }).click(),
  ]);
  expect(issued.status()).toBe(201);
  const invitation = await issued.json();
  await expect(page.locator('#guest-invitation-url')).toHaveValue(invitation.invitation_url);
  const guestContext = await browser.newContext({ baseURL: new URL(page.url()).origin });
  try {
    const guest = await guestContext.newPage();
    await guest.goto(invitation.invitation_url);
    await expect(guest.locator('h1')).toContainText(setup.session.title);
    await guest.fill('#guest-name', '招待された参加者');
    await guest.selectOption('#player-slot', '1');
    await guest.fill('#character-name', '引き継ぐ探索者');
    const [response] = await Promise.all([
      guest.waitForResponse(response => new URL(response.url()).pathname.endsWith('/respond/') && response.request().method() === 'POST'),
      guest.getByRole('button', { name: '参加を確定' }).click(),
    ]);
    expect(response.status()).toBe(201);
    const participant = await response.json();
    expect(participant.player_slot).toBe(1);
    await expect(guest.locator('#guest-response-message')).toContainText('参加を登録しました');
    await expect(guest.locator('#guest-response-message')).toContainText('引き継ぎコード');
    await expect(guest.getByRole('link', { name: '参加枠の引き継ぎへ' })).toHaveAttribute('href', '/integrations/');
    await expect(guest.getByRole('button', { name: '参加を確定' })).toBeDisabled();
    const claimUrl = `/api/participants/${participant.participant_id}/claim/`;
    const anonymousClaim = await guest.request.post(claimUrl, { data: { claim_token: participant.claim_token } });
    expect([401, 403]).toContain(anonymousClaim.status());
    const reused = await guest.goto(invitation.invitation_url);
    expect(reused?.status()).toBe(410);
    await expect(guest.locator('h1')).toHaveText('招待を利用できません');
    await expect(guest.locator('#guest-response-form')).toHaveCount(0);
    await expect(guest.locator('body')).not.toContainText(setup.session.title);

    await signUp(guest, `guestpl_${suffix}`);
    const sessionUrl = `/api/schedules/sessions/${setup.session.id}/`;
    expect((await guest.request.get(sessionUrl)).status()).toBe(404);
    await guest.goto('/integrations/');
    await guest.setViewportSize({ width: 390, height: 844 });
    const missing = await guest.evaluate(async url => {
      return (await (window as any).axios.post(url, {}).catch((error: any) => error.response)).status;
    }, claimUrl);
    expect(missing).toBe(403);
    await guest.getByLabel('引き継ぐゲスト参加者ID', { exact: true }).fill(String(participant.participant_id));
    await guest.getByLabel('引き継ぎコード', { exact: true }).fill(participant.claim_token);
    const [claimed] = await Promise.all([
      guest.waitForResponse(response => new URL(response.url()).pathname === claimUrl && response.request().method() === 'POST'),
      guest.getByRole('button', { name: '参加枠を引き継ぐ', exact: true }).click(),
    ]);
    expect(claimed.status()).toBe(200);
    const claim = await claimed.json();
    expect(claim.participant_id).toBe(participant.participant_id);
    expect(claim.character_name).toBe('引き継ぐ探索者');
    await expect(guest.locator('#integration-message')).toContainText('ゲスト参加枠を引き継ぎました。');
    const duplicate = await guest.evaluate(async ({ url, token }) => {
      return (await (window as any).axios.post(url, { claim_token: token }).catch((error: any) => error.response)).status;
    }, { url: claimUrl, token: participant.claim_token });
    expect(duplicate).toBe(409);
    const savedSession = await guest.request.get(sessionUrl);
    expect(savedSession.status()).toBe(200);
    expect((await savedSession.json()).title).toBe(setup.session.title);
    const claimCard = guest.locator('.card', { has: guest.locator('#claim-participant') });
    await claimCard.scrollIntoViewIfNeeded();
    await claimCard.screenshot({ path: test.info().outputPath('guest-claim-mobile.png'), mask: [guest.locator('#claim-token')], animations: 'disabled' });
  } finally {
    await guestContext.close();
  }
});

test('group invitation displays stored markup safely and can be accepted', async ({ page, browser }) => {
  const suffix = `${Date.now()}_${test.info().project.name}`;
  const markup = '<img src=x onerror="window.__inviteXss=1">';
  await signUp(page, `invite_${suffix}`, markup);
  const group = await page.evaluate(async name => {
    return (await (window as any).axios.post('/api/accounts/groups/', { name, visibility: 'private' })).data;
  }, markup);
  const recipientContext = await browser.newContext({ baseURL: new URL(page.url()).origin });
  try {
    const recipient = await recipientContext.newPage();
    await signUp(recipient, `recipient_${suffix}`);
    const invitation = await page.evaluate(async ({ id, username, message }) => {
      return (await (window as any).axios.post(`/api/accounts/groups/${id}/invite/`, { username, message })).data;
    }, { id: group.id, username: `release_recipient_${suffix}`, message: markup });
    expect(invitation.status).toBe('pending');
    await recipient.goto('/api/schedules/notifications/view/');
    const notification = recipient.locator('[data-notification-id]', { hasText: '【グループ招待】' });
    await expect(notification).toBeVisible();
    await expect(notification.locator('.notification-message')).toContainText(`${markup}さんから招待が届いています。`);
    await expect(notification.locator('.notification-message')).toContainText(`グループ: ${markup}`);
    await expect(notification.locator('.notification-message')).toContainText(`メッセージ: ${markup}`);
    await expect(notification.locator('img')).toHaveCount(0);
    expect(await recipient.evaluate(() => (window as any).__inviteXss)).toBeUndefined();
    const notificationId = await notification.getAttribute('data-notification-id');
    const [marked] = await Promise.all([
      recipient.waitForResponse(response => new URL(response.url()).pathname === `/api/schedules/notifications/${notificationId}/mark_read/` && response.request().method() === 'PATCH'),
      notification.locator('[data-action="mark-read"]').click(),
    ]);
    expect(marked.status()).toBe(200);
    await expect(notification.locator('[data-action="mark-read"]')).toHaveCount(0);
    const savedNotification = await recipient.request.get(`/api/schedules/notifications/${notificationId}/`);
    expect(savedNotification.status()).toBe(200);
    expect((await savedNotification.json()).is_read).toBe(true);
    await recipient.goto('/accounts/groups/view/?show_test_data=1');
    const item = recipient.locator('.invitation-item');
    await expect(item).toBeVisible();
    await expect(item.locator('strong')).toHaveText(markup);
    await expect(item.locator('.invitation-meta').nth(0)).toHaveText(`招待者: ${markup}`);
    await expect(item.locator('.invitation-meta').nth(1)).toHaveText(`メッセージ: ${markup}`);
    await expect(item.locator('img')).toHaveCount(0);
    expect(await recipient.evaluate(() => (window as any).__inviteXss)).toBeUndefined();
    const [accepted] = await Promise.all([
      recipient.waitForResponse(response => new URL(response.url()).pathname === `/api/accounts/invitations/${invitation.id}/accept/` && response.request().method() === 'POST'),
      item.getByRole('button', { name: /承認$/ }).click(),
    ]);
    expect(accepted.status()).toBe(200);
    await expect(item).toContainText('承認済み');
    await expect(recipient.locator('.group-card', { hasText: markup })).toBeVisible();
    const saved = await (await recipient.request.get(`/api/accounts/groups/${group.id}/`)).json();
    expect(saved.is_member).toBe(true);
    expect(saved.member_role).toBe('member');
  } finally {
    await recipientContext.close();
  }
});

test('group details display stored markup as text for another registered user', async ({ page, browser }) => {
  const suffix = `${Date.now()}_${test.info().project.name}`;
  const markup = '<img src=x onerror="window.__groupXss=1">';
  await signUp(page, `markup_${suffix}`, markup);
  const groupName = `表示確認 ${suffix}`;
  await page.evaluate(async ({ name, description }) => {
    await (window as any).axios.post('/api/accounts/groups/', { name, description, visibility: 'public' });
  }, { name: groupName, description: markup });
  const viewerContext = await browser.newContext({ baseURL: new URL(page.url()).origin });
  try {
    const viewer = await viewerContext.newPage();
    await signUp(viewer, `viewer_${suffix}`);
    await viewer.goto('/accounts/groups/view/?show_test_data=1');
    await viewer.click('label[for="publicGroupsView"]');
    await viewer.fill('#groupSearchInput', groupName);
    const card = viewer.locator('.group-card', { hasText: groupName });
    await expect(card).toContainText(markup);
    await card.click();
    const modal = viewer.locator('#groupDetailModal');
    await expect(modal).toBeVisible();
    await expect(modal.locator('.member-item')).toContainText(markup);
    await expect(modal.locator('#groupDetailBody > .row > .col-md-8 > p')).toHaveText(markup);
    await expect(modal.locator('.col-md-4 .card-body')).toContainText(markup);
    await expect(modal.locator('img')).toHaveCount(0);
    expect(await viewer.evaluate(() => (window as any).__groupXss)).toBeUndefined();
  } finally {
    await viewerContext.close();
  }
});

test('owner grants and revokes group administration for a registered member', async ({ page, browser }) => {
  const suffix = `${Date.now()}_${test.info().project.name}`;
  await signUp(page, `roles_${suffix}`);
  const groupName = `権限確認 ${suffix}`;
  const group = await page.evaluate(async name => {
    const response = await (window as any).axios.post('/api/accounts/groups/', { name, visibility: 'public' });
    return response.data;
  }, groupName);
  const memberContext = await browser.newContext({ baseURL: new URL(page.url()).origin });
  try {
    const member = await memberContext.newPage();
    await signUp(member, `member_${suffix}`);
    await member.goto('/accounts/groups/view/?show_test_data=1');
    await member.click('label[for="publicGroupsView"]');
    await member.fill('#groupSearchInput', groupName);
    const memberCard = member.locator('.group-card', { hasText: groupName });
    const [joined] = await Promise.all([
      member.waitForResponse(response => new URL(response.url()).pathname === `/api/accounts/groups/${group.id}/join/` && response.request().method() === 'POST'),
      memberCard.locator('button.btn-success').click(),
    ]);
    expect(joined.status()).toBe(201);
    await expect(memberCard.locator('.badge.bg-info')).toBeVisible();
    await memberCard.click();
    const memberModal = member.locator('#groupDetailModal');
    await expect(memberModal).toContainText(groupName);
    await expect(memberModal.getByRole('button', { name: 'グループを編集' })).toHaveCount(0);

    await page.goto('/accounts/groups/view/?show_test_data=1');
    await page.locator('.group-card', { hasText: groupName }).click();
    const ownerModal = page.locator('#groupDetailModal');
    const memberRow = ownerModal.locator('.member-item', { hasText: `通常利用者 member_${suffix}` });
    const changeRole = async (label: string) => {
      await memberRow.getByRole('button', { name: label, exact: true }).click();
      const [changed] = await Promise.all([
        page.waitForResponse(response => new URL(response.url()).pathname === `/api/accounts/groups/${group.id}/set_member_role/` && response.request().method() === 'POST'),
        page.getByRole('button', { name: '変更する', exact: true }).click(),
      ]);
      expect(changed.status()).toBe(200);
    };
    await changeRole('管理者にする');
    await expect(memberRow.locator('.role-badge')).toHaveText('管理者');
    await member.reload();
    await member.locator('.group-card', { hasText: groupName }).click();
    await expect(memberModal.getByRole('button', { name: 'グループを編集' })).toBeVisible();
    const protectedActions = await member.evaluate(async ({ id, creator }) => {
      const client = (window as any).axios;
      const statusOf = async (operation: Promise<any>) => {
        try { return (await operation).status; } catch (error: any) { return error.response.status; }
      };
      return [
        await statusOf(client.patch(`/api/accounts/groups/${id}/`, { description: '追加された管理者による更新' })),
        await statusOf(client.post(`/api/accounts/groups/${id}/set_member_role/`, { user_id: creator, role: 'member' })),
        await statusOf(client.delete(`/api/accounts/groups/${id}/remove_member/`, { data: { user_id: creator } })),
      ];
    }, { id: group.id, creator: group.created_by });
    expect(protectedActions).toEqual([200, 400, 400]);

    await changeRole('管理者解除');
    await expect(memberRow.locator('.role-badge')).toHaveCount(0);
    // The already-open administrator page must lose API authority immediately.
    const revoked = await member.evaluate(async id => {
      try {
        return (await (window as any).axios.patch(`/api/accounts/groups/${id}/`, { description: '拒否される変更' })).status;
      } catch (error: any) { return error.response.status; }
    }, group.id);
    expect(revoked).toBe(403);
    const saved = await (await page.request.get(`/api/accounts/groups/${group.id}/`)).json();
    expect(saved.description).toBe('追加された管理者による更新');
    expect(saved.created_by).toBe(group.created_by);
    await member.reload();
    await member.locator('.group-card', { hasText: groupName }).click();
    await expect(memberModal).toContainText('追加された管理者による更新');
    await expect(memberModal.getByRole('button', { name: 'グループを編集' })).toHaveCount(0);
    await member.screenshot({ path: test.info().outputPath('member-after-admin-revocation.png'), fullPage: true, animations: 'disabled' });
  } finally {
    await memberContext.close();
  }
});

test('friend search preserves the query when the HTTP client CDN is unavailable', async ({ page }) => {
  await page.route('https://cdn.jsdelivr.net/npm/axios/**', route => route.abort());
  await signUp(page, `search_${Date.now()}_${test.info().project.name}`);
  await page.goto('/accounts/groups/view/');
  const query = '検索 +&?';
  const [request] = await Promise.all([
    page.waitForRequest(request => new URL(request.url()).pathname === '/api/accounts/friend-candidates/'),
    page.fill('#friendSearchInput', query),
  ]);
  expect(new URL(request.url()).searchParams.get('q')).toBe(query);
});

test('icons load when the icon CDN is unavailable', async ({ page }) => {
  await page.route('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/**', route => route.abort());
  await page.goto('/signup/');
  const fonts = await page.evaluate(async () => {
    const loaded = await Promise.all([
      document.fonts.load('900 16px "Font Awesome 6 Free"'),
      document.fonts.load('400 16px "Font Awesome 6 Free"'),
      document.fonts.load('400 16px "Font Awesome 6 Brands"'),
    ]);
    return loaded.map(faces => faces.length);
  });
  expect(fonts).toEqual([1, 1, 1]);
  await expect(page.locator('.fas').first()).toHaveCSS('font-family', '"Font Awesome 6 Free"');
});

test('calendar and session form initialize when the calendar CDN is unavailable', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('https://cdn.jsdelivr.net/npm/fullcalendar@*/**', route => route.abort());
  await signUp(page, `calendar_${Date.now()}_${test.info().project.name}`);
  await page.goto('/api/schedules/calendar/view/');
  await expect(page.locator('#calendar .fc-view-harness')).toBeVisible();
  await page.screenshot({ path: test.info().outputPath('calendar-without-cdn.png'), fullPage: true });
  await page.click('button[data-bs-target="#newSessionModal"]');
  await expect(page.locator('#newSessionModal')).toBeVisible();
  await expect(page.locator('#sessionGroup option').first()).toHaveText('グループなし（個別セッション）');
  expect(errors).toEqual([]);
});

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
