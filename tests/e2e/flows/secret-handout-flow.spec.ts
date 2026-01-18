import { test, expect, Page } from '@playwright/test';
import { devLogin } from './helpers';

async function joinPublicGroup(page: Page, groupName: string, groupId: number): Promise<void> {
  await page.click('label[for="publicGroupsView"]');
  await page.fill('#groupSearchInput', groupName);

  const groupCard = page.locator('.group-card', { hasText: groupName }).first();
  await expect(groupCard).toBeVisible({ timeout: 15000 });

  const joinButton = groupCard.locator('button.btn-success').first();
  await expect(joinButton).toBeVisible({ timeout: 15000 });

  await Promise.all([
    page.waitForResponse(resp =>
      resp.url().includes(`/api/accounts/groups/${groupId}/join/`) &&
      resp.request().method() === 'POST'
    ),
    joinButton.click(),
  ]);

  await expect(joinButton).toHaveCount(0);
  await expect(groupCard.locator('.badge.bg-info')).toBeVisible({ timeout: 15000 });
}

test.describe('handout flow', () => {
  test('GM creates a secret handout visible only to the target participant', async ({ page, browser }) => {
    await devLogin(page, 'admin');
    await page.waitForFunction(() => (window as any).axios?.post);

    const timestamp = Date.now();
    const groupName = `E2E Handout Group ${timestamp}`;
    const sessionTitle = `E2E Handout Session ${timestamp}`;

    const { group, session } = await page.evaluate(async ({ groupName, sessionTitle }) => {
      const groupResp = await (window as any).axios.post('/api/accounts/groups/', {
        name: groupName,
        visibility: 'public',
      });
      const group = groupResp.data;

      const sessionResp = await (window as any).axios.post('/api/schedules/sessions/', {
        title: sessionTitle,
        description: 'Secret handout flow test',
        group: group.id,
        visibility: 'group',
        date: '2030-01-01T19:00:00Z',
      });
      return { group, session: sessionResp.data };
    }, { groupName, sessionTitle });

    const player1Context = await browser.newContext();
    const player1Page = await player1Context.newPage();

    const player2Context = await browser.newContext();
    const player2Page = await player2Context.newPage();

    try {
      await devLogin(player1Page, 'investigator1', '/accounts/groups/view/');
      await joinPublicGroup(player1Page, groupName, group.id);

      await player1Page.goto(`/api/schedules/sessions/${session.id}/detail/`);
      await expect(player1Page.locator('button[data-bs-target="#joinSessionModal"]')).toBeVisible({ timeout: 15000 });

      await player1Page.click('button[data-bs-target="#joinSessionModal"]');
      await expect(player1Page.locator('#joinSessionModal')).toHaveClass(/show/);
      await player1Page.fill('#character_name', `E2E Player1 ${timestamp}`);

      player1Page.once('dialog', dialog => dialog.accept());
      await Promise.all([
        player1Page.waitForResponse(resp =>
          resp.url().includes(`/api/schedules/sessions/${session.id}/join/`) &&
          resp.request().method() === 'POST'
        ),
        player1Page.waitForNavigation({ waitUntil: 'domcontentloaded' }),
        player1Page.click('#joinSessionModal button[onclick="joinSession()"]'),
      ]);

      await page.goto(`/api/schedules/sessions/${session.id}/detail/`);
      await expect(page.locator('h3', { hasText: sessionTitle }).first()).toBeVisible({ timeout: 15000 });

      await page.click('button[data-bs-target="#createHandoutModal"]');
      await expect(page.locator('#createHandoutModal')).toHaveClass(/show/);

      const participantId = await page.locator('#handout_participant option').nth(1).getAttribute('value');
      expect(participantId).toBeTruthy();
      await page.selectOption('#handout_participant', participantId!);

      const handoutTitle = `E2E Secret Handout ${timestamp}`;
      await page.fill('#handout_title', handoutTitle);
      await page.fill('#handout_content', 'This is a secret handout content.');
      await expect(page.locator('#handout_is_secret')).toBeChecked();

      page.once('dialog', dialog => dialog.accept());
      await Promise.all([
        page.waitForResponse(resp =>
          resp.url().includes('/api/schedules/handouts/') &&
          resp.request().method() === 'POST' &&
          resp.status() === 201
        ),
        page.waitForNavigation({ waitUntil: 'domcontentloaded' }),
        page.click('#createHandoutModal button[onclick="createHandout()"]'),
      ]);

      const handoutBox = page.locator('div.border.rounded', { hasText: handoutTitle }).first();
      await expect(handoutBox).toBeVisible({ timeout: 15000 });
      await expect(handoutBox.locator('i.fa-eye-slash')).toBeVisible();

      await player1Page.reload({ waitUntil: 'domcontentloaded' });
      await expect(player1Page.locator(`text=${handoutTitle}`)).toBeVisible({ timeout: 15000 });

      await devLogin(player2Page, 'investigator2', '/accounts/groups/view/');
      await joinPublicGroup(player2Page, groupName, group.id);
      await player2Page.goto(`/api/schedules/sessions/${session.id}/detail/`);
      await expect(player2Page.locator(`text=${handoutTitle}`)).toHaveCount(0);
    } finally {
      await player2Context.close();
      await player1Context.close();
    }
  });
});

