import { test, expect } from '@playwright/test';
import { devLogin } from './helpers';

function formatDateTimeLocal(date: Date): string {
  const pad = (value: number) => value.toString().padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

test.describe('sessions', () => {
  test('create a session from the calendar view', async ({ page }) => {
    await devLogin(page);
    await page.goto('/api/schedules/calendar/view/');

    await page.click('button[data-bs-target="#newSessionModal"]');
    await expect(page.locator('#newSessionModal')).toHaveClass(/show/);

    const sessionTitle = `E2E Session ${Date.now()}`;
    const sessionDate = new Date(Date.now() + 24 * 60 * 60 * 1000);

    await page.fill('#sessionTitle', sessionTitle);
    await page.fill('#sessionDate', formatDateTimeLocal(sessionDate));
    await page.fill('#sessionDuration', '120');
    await page.fill('#sessionLocation', 'Online');

    await page.waitForFunction(() =>
      document.querySelectorAll('#sessionGroup option:not([value=""])').length > 0
    );
    const groupValue = await page.$eval(
      '#sessionGroup option:not([value=""])',
      option => (option as HTMLOptionElement).value
    );
    await page.selectOption('#sessionGroup', groupValue);

    await page.fill('#sessionDescription', 'Created by Playwright session test.');
    await page.selectOption('#sessionVisibility', 'public');

    page.once('dialog', async dialog => {
      await dialog.accept();
    });

    await Promise.all([
      page.waitForResponse(response =>
        response.url().includes('/api/schedules/sessions/') &&
        response.request().method() === 'POST' &&
        response.status() === 201
      ),
      page.click('#saveSessionBtn'),
    ]);

    await expect(page.locator('#upcomingSessions')).toContainText(sessionTitle);
  });
});
