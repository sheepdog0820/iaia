import { expect, test } from '@playwright/test';
import { devLogin } from './helpers';

test('calendar and existing session choices preserve titles as text', async ({ page }) => {
  const markup = '<img src=x onerror="window.__calendarTitleXss=1">';
  const session = { id: 1, title: markup, date: '2030-01-01T19:00:00Z' };
  await page.route('**/api/schedules/sessions/upcoming/', route => route.fulfill({ json: [session] }));
  await page.route('**/api/schedules/sessions/editable-choices/', route => route.fulfill({ json: [session] }));
  await devLogin(page, 'admin', '/api/schedules/calendar/view/');
  await expect(page.locator('#upcomingSessions h6')).toHaveText(markup);
  await expect(page.locator('#upcomingSessions img')).toHaveCount(0);
  expect(await page.evaluate(() => (window as any).__calendarTitleXss)).toBeUndefined();
  await page.locator('button[data-bs-target="#newSessionModal"]').click();
  await expect(page.locator('#newSessionModal')).toBeVisible();
  await page.locator('#createModeExisting').check();
  await expect(page.locator('#existingSessionId')).toBeEnabled();
  await expect(page.locator('#existingSessionId option[value="1"]')).toHaveText(markup);
  await page.selectOption('#existingSessionId', '1');
  await expect(page.locator('#existingSessionId')).toHaveValue('1');
  expect(await page.evaluate(() => (window as any).__calendarTitleXss)).toBeUndefined();
});
