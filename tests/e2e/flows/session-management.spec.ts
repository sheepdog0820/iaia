import { test, expect } from '@playwright/test';
import { devLogin, setInputValue } from './helpers';

function formatDateTimeLocal(date: Date): string {
  const pad = (value: number) => value.toString().padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

test.describe('sessions', () => {
  test('create a session from the calendar view', async ({ page }) => {
    await devLogin(page);
    await page.waitForFunction(() => (window as any).axios?.post);

    const groupName = `E2E Session Group ${Date.now()}`;
    const group = await page.evaluate(async (name: string) => {
      const response = await (window as any).axios.post('/api/accounts/groups/', {
        name,
        visibility: 'private',
      });
      return response.data;
    }, groupName);

    await page.goto('/api/schedules/calendar/view/');

    page.on('dialog', async dialog => {
      await dialog.accept();
    });

    await page.click('button[data-bs-target="#newSessionModal"]');
    await expect(page.locator('#newSessionModal')).toHaveClass(/show/);

    const sessionTitle = `E2E Session ${Date.now()}`;
    const sessionDate = new Date(Date.now() + 5 * 60 * 1000);

    await setInputValue(page, '#sessionTitle', sessionTitle);
    await setInputValue(page, '#sessionDate', formatDateTimeLocal(sessionDate));
    await setInputValue(page, '#sessionDuration', '120');
    await setInputValue(page, '#sessionLocation', 'Online');

    await page.waitForFunction(groupId => {
      const select = document.querySelector('#sessionGroup') as HTMLSelectElement | null;
      if (!select) return false;
      return Array.from(select.options).some(option => option.value === groupId);
    }, String(group.id));
    await page.selectOption('#sessionGroup', String(group.id));

    await setInputValue(page, '#sessionDescription', 'Created by Playwright session test.');
    await page.selectOption('#sessionVisibility', 'public');

    const [createSessionResponse] = await Promise.all([
      page.waitForResponse(response =>
        response.url().includes('/api/schedules/sessions/') &&
        response.request().method() === 'POST' &&
        response.status() === 201
      ),
      page.click('#saveSessionBtn'),
    ]);

    const session = await createSessionResponse.json();
    await page.goto(`/api/schedules/sessions/${session.id}/detail/`);
    await expect(page.locator('h3', { hasText: sessionTitle }).first()).toBeVisible();

    await page.click('button[data-bs-target="#editSessionModal"]');
    await expect(page.locator('#editSessionModal')).toHaveClass(/show/);
    await page.selectOption('#editSessionStatus', 'ongoing');

    await Promise.all([
      page.waitForResponse(response =>
        response.url().includes(`/api/schedules/sessions/${session.id}/`) &&
        response.request().method() === 'PATCH' &&
        response.status() === 200
      ),
      page.waitForNavigation({ waitUntil: 'domcontentloaded' }),
      page.click('#editSessionModal button[onclick="updateSession()"]'),
    ]);

    await expect(page.locator('span.badge', { hasText: '進行中' }).first()).toBeVisible();
    const deleteStatus = await page.evaluate(async (sessionId: number) => {
      const response = await (window as any).axios.delete(`/api/schedules/sessions/${sessionId}/`);
      return response.status;
    }, session.id);
    expect(deleteStatus).toBe(204);

    const deletedSessionResponse = await page.request.get(`/api/schedules/sessions/${session.id}/`);
    expect(deletedSessionResponse.status()).toBe(404);
  });

  test('home summary card and sessions list expose created session', async ({ page }) => {
    await devLogin(page);
    await page.waitForFunction(() => (window as any).axios?.post);

    const suffix = Date.now();
    const group = await page.evaluate(async (name: string) => {
      const response = await (window as any).axios.post('/api/accounts/groups/', {
        name,
        visibility: 'private',
      });
      return response.data;
    }, `E2E Session Summary Group ${suffix}`);

    const sessionTitle = `Unified Summary Session ${suffix}`;
    const sessionDate = '2035-01-01T12:00:00.000Z';

    const session = await page.evaluate(async ({ groupId, title, date }) => {
      const response = await (window as any).axios.post('/api/schedules/sessions/', {
        title,
        date,
        group: groupId,
        duration_minutes: 150,
        location: 'Discord',
        visibility: 'group',
        description: 'Shared card renderer',
      });
      return response.data;
    }, { groupId: group.id, title: sessionTitle, date: sessionDate });

    await page.route('**/api/schedules/sessions/upcoming/', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([{
          id: session.id,
          title: sessionTitle,
          date: sessionDate,
          date_display: 'まもなく開始',
          location: 'Discord',
          status: 'planned',
          visibility: 'group',
          visibility_display: 'グループ内',
          gm_name: 'admin',
          group_name: group.name,
          participant_count: 0,
          guest_count: 0,
          participants_summary: 'GM のみ',
          duration_minutes: 150,
          duration_display: '150分',
        }]),
      });
    });
    await page.goto('/');
    const upcomingCard = page.locator('#upcoming-sessions .session-summary-card').filter({ hasText: sessionTitle }).first();
    await expect(upcomingCard).toBeVisible();
    await expect(upcomingCard).toHaveClass(/session-summary-card--planned/);
    await expect(upcomingCard).toContainText('GM:');
    await expect(upcomingCard).toContainText('グループ:');

    await page.goto('/api/schedules/sessions/view/');
    const listLink = page.locator(`a[href="/api/schedules/sessions/${session.id}/detail/"]`).first();
    await expect(listLink).toBeVisible();
    await expect(listLink).toContainText(sessionTitle);
    await expect(page.locator('body')).toContainText('Discord');
  });
});
