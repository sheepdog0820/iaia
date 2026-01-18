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
    await page.selectOption('#status', 'ongoing');

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
  });
});
