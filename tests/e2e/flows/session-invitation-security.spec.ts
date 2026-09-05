import { expect, test } from '@playwright/test';
import { devLogin } from './helpers';

test('session invitations render titles and inviter names as text', async ({ page }) => {
  const markup = '<img src=x onerror="window.__sessionInviteXss=1">';
  await page.route('**/api/schedules/session-invitations/?status=pending', route => route.fulfill({ json: [{
    id: 1, session_id: 1, session_title: markup, session_date: '2026-09-06T12:00:00Z',
    inviter: { nickname: markup, username: 'inviter' }, message: markup,
  }] }));
  await devLogin(page, 'admin', '/api/schedules/sessions/web/');
  const invitations = page.locator('#sessionInvitationsContainer');
  await expect(invitations.locator('.fw-bold')).toHaveText(markup);
  await expect(invitations.locator('span.ms-2')).toContainText(markup);
  await expect(invitations.locator('.small.mt-1')).toHaveText(markup);
  await expect(invitations.locator('img')).toHaveCount(0);
  expect(await page.evaluate(() => (window as any).__sessionInviteXss)).toBeUndefined();
  await expect(invitations.getByRole('button', { name: '承認して参加', exact: true })).toBeVisible();
  await expect(invitations.getByRole('button', { name: '辞退', exact: true })).toBeVisible();
});
