import { test, expect } from '@playwright/test';
import { randomUUID } from 'node:crypto';

async function signUp(page: import('@playwright/test').Page, suffix: string) {
  await page.goto('/signup/');
  await page.fill('#id_username', `poll_${suffix}`);
  await page.fill('#id_email', `poll_${suffix}@example.com`);
  const password = `Vault-${randomUUID()}!`;
  await page.fill('#id_password1', password);
  await page.fill('#id_password2', password);
  await page.fill('#id_nickname', `日程調整 ${suffix}`);
  await Promise.all([
    page.waitForURL(/\/accounts\/dashboard\//),
    page.click('#signup-btn'),
  ]);
}

test.describe('date poll flow', () => {
  test.use({ timezoneId: 'UTC' });
  test('GM creates poll, player votes, GM confirms', async ({ page, browser }) => {
    const suffix = `${Date.now()}_${test.info().project.name}`;
    await signUp(page, suffix);
    await page.waitForFunction(() => (window as any).axios?.post);

    const timestamp = Date.now();
    const groupName = `E2E DatePoll Group ${timestamp}`;
    const sessionTitle = `E2E DatePoll Session ${timestamp}`;

    const { group, session } = await page.evaluate(async ({ groupName, sessionTitle }) => {
      const groupResp = await (window as any).axios.post('/api/accounts/groups/', {
        name: groupName,
        visibility: 'public',
      });
      const group = groupResp.data;

      const sessionResp = await (window as any).axios.post('/api/schedules/sessions/', {
        title: sessionTitle,
        description: 'Date poll flow test',
        group: group.id,
        visibility: 'group',
      });

      return { group, session: sessionResp.data };
    }, { groupName, sessionTitle });

    const playerContext = await browser.newContext({ baseURL: new URL(page.url()).origin, timezoneId: 'UTC' });
    const playerPage = await playerContext.newPage();

    try {
      await signUp(playerPage, `${suffix}_pl`);
      await playerPage.goto('/accounts/groups/view/?show_test_data=1');

      await playerPage.click('label[for="publicGroupsView"]');
      await playerPage.fill('#groupSearchInput', groupName);

      const groupCard = playerPage.locator('.group-card', { hasText: groupName }).first();
      await expect(groupCard).toBeVisible({ timeout: 15000 });

      const joinButton = groupCard.locator('button.btn-success').first();
      await expect(joinButton).toBeVisible({ timeout: 15000 });

      await Promise.all([
        playerPage.waitForResponse(resp =>
          resp.url().includes(`/api/accounts/groups/${group.id}/join/`) &&
          resp.request().method() === 'POST'
        ),
        joinButton.click(),
      ]);

      await expect(joinButton).toHaveCount(0);
      await expect(groupCard.locator('.badge.bg-info')).toBeVisible({ timeout: 15000 });

      await page.goto(`/api/schedules/sessions/${session.id}/date-poll/`);
      await expect(page.locator('#datePollContainer')).toBeVisible();
      await expect(page.locator('#datePollCreateTitle')).toBeVisible({ timeout: 15000 });

      const optionInput = page.locator('.date-poll-option-datetime').first();
      await expect(optionInput).toBeVisible({ timeout: 15000 });
      await optionInput.fill('2030-01-01T19:00');

      const [createPollResponse] = await Promise.all([
        page.waitForResponse(resp =>
          resp.url().includes('/api/schedules/date-polls/') &&
          resp.request().method() === 'POST' &&
          resp.status() === 201
        ),
        page.click('button[onclick="createDatePollForSession()"]'),
      ]);

      const poll = await createPollResponse.json();
      expect(poll.session).toBe(session.id);
      expect(Array.isArray(poll.options)).toBeTruthy();
      expect(poll.options.length).toBeGreaterThan(0);

      const pollId = poll.id as number;
      const optionId = poll.options[0].id as number;

      await playerPage.goto(`/api/schedules/sessions/${session.id}/date-poll/`);
      await expect(playerPage.locator('#datePollContainer')).toBeVisible();
      await playerPage.fill('#datePollChatInput', '参加予定を確認しました。');
      const [commentResponse] = await Promise.all([
        playerPage.waitForResponse(response => new URL(response.url()).pathname === `/api/schedules/date-polls/${pollId}/comments/` && response.request().method() === 'POST'),
        playerPage.click('#datePollChatSendBtn'),
      ]);
      expect(commentResponse.status()).toBe(201);
      await expect(playerPage.locator('#datePollChatLog')).toContainText('参加予定を確認しました。');

      const voteButtonSelector = `button[onclick="voteDatePollOption(${pollId}, ${optionId}, 'available')"]`;
      await expect(playerPage.locator(voteButtonSelector)).toBeVisible({ timeout: 15000 });

      await Promise.all([
        playerPage.waitForResponse(resp =>
          resp.url().includes(`/api/schedules/date-polls/${pollId}/vote/`) &&
          resp.request().method() === 'POST'
        ),
        playerPage.click(voteButtonSelector),
      ]);

      await page.reload({ waitUntil: 'domcontentloaded' });
      await page.fill('#datePollChatInput', '回答ありがとうございます。');
      const [replyResponse] = await Promise.all([
        page.waitForResponse(response => new URL(response.url()).pathname === `/api/schedules/date-polls/${pollId}/comments/` && response.request().method() === 'POST'),
        page.click('#datePollChatSendBtn'),
      ]);
      expect(replyResponse.status()).toBe(201);
      await playerPage.reload();
      await expect(playerPage.locator('#datePollChatLog')).toContainText('回答ありがとうございます。');

      const confirmButtonSelector = `button[onclick="confirmDatePollOption(${pollId}, ${optionId})"]`;
      await expect(page.locator(confirmButtonSelector)).toBeVisible({ timeout: 15000 });

      const confirmResponsePromise = page.waitForResponse(resp =>
        resp.url().includes(`/api/schedules/date-polls/${pollId}/confirm/`) &&
        resp.request().method() === 'POST'
      );

      await page.click(confirmButtonSelector);
      const confirmModal = page.locator('.modal.show', { has: page.locator('[data-confirm-action]') }).last();
      await expect(confirmModal).toBeVisible({ timeout: 15000 });

      await Promise.all([
        confirmResponsePromise,
        page.waitForNavigation({ waitUntil: 'domcontentloaded' }),
        confirmModal.locator('[data-confirm-action]').click(),
      ]);

      const confirmResponse = await confirmResponsePromise;
      expect(confirmResponse.ok()).toBeTruthy();

      await page.waitForFunction(() => (window as any).axios?.get);
      const { updatedSession, polls } = await page.evaluate(async (sessionId: number) => {
        const [sessionResp, pollsResp] = await Promise.all([
          (window as any).axios.get(`/api/schedules/sessions/${sessionId}/`),
          (window as any).axios.get('/api/schedules/date-polls/', { params: { session_id: sessionId } }),
        ]);
        return { updatedSession: sessionResp.data, polls: pollsResp.data };
      }, session.id);

      expect(updatedSession.date).toBeTruthy();
      expect(Array.isArray(polls)).toBeTruthy();
      expect(polls[0]?.is_closed).toBe(true);
      expect(polls[0]?.selected_date).toBeTruthy();
      expect(new Date(updatedSession.date).getTime()).toBe(new Date(polls[0].selected_date).getTime());
      await expect(page.locator('#datePollContainer')).toContainText('19:00');
      await expect(page.getByText('日時の入力・表示: 日本時間（Asia/Tokyo）')).toBeVisible();
      await expect(page.locator('#datePollChatLog')).toContainText('参加予定を確認しました。');
      await page.addStyleTag({ content: '* { transition: none !important; animation: none !important; }' });
      for (const colorScheme of ['light', 'dark'] as const) {
        await page.emulateMedia({ colorScheme });
        const ratios = await page.locator('#datePollContainer tbody .text-muted, #datePollChatLog .text-muted, #datePollChatLog .date-poll-chat-meta, .breadcrumb a, .breadcrumb-item.active').evaluateAll(elements => {
          const rgb = (value: string) => (value.match(/[\d.]+/g) || []).map(Number);
          const luminance = (color: number[]) => color.slice(0, 3).map(value => {
            const normalized = value / 255;
            return normalized <= 0.04045 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
          }).reduce((sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index], 0);
          return elements.map(element => {
            const cell = element.closest('td') || element.closest('.date-poll-chat-wrap') || document.body;
            const style = getComputedStyle(cell);
            let background = rgb(style.backgroundColor);
            const shadow = style.boxShadow.match(/rgba?\([^)]+\)/)?.[0];
            if (shadow) {
              const overlay = rgb(shadow);
              const alpha = overlay[3] ?? 1;
              background = background.map((value, index) => value * (1 - alpha) + overlay[index] * alpha);
            }
            const foreground = rgb(getComputedStyle(element).color);
            const alpha = foreground[3] ?? 1;
            const foregroundL = luminance(background.map((value, index) => value * (1 - alpha) + foreground[index] * alpha));
            const backgroundL = luminance(background);
            return (Math.max(foregroundL, backgroundL) + 0.05) / (Math.min(foregroundL, backgroundL) + 0.05);
          });
        });
        expect(ratios.length).toBeGreaterThanOrEqual(8);
        for (const ratio of ratios) expect(ratio).toBeGreaterThanOrEqual(4.5);
        await page.screenshot({ path: test.info().outputPath(`poll-${colorScheme}.png`), fullPage: true, animations: 'disabled' });
      }
      await page.emulateMedia({ colorScheme: 'light' });
      await page.screenshot({ path: test.info().outputPath('gm-confirmed-date.png'), fullPage: true });
    } finally {
      await playerContext.close();
    }
  });
});
