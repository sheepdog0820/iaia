import { expect, test } from '@playwright/test';
import { devLogin } from './helpers';

for (const guest of [false, true]) {
  test(`participant management safely displays ${guest ? 'guest' : 'registered'} names and links`, async ({ page }) => {
    const markup = '<img src=x onerror="window.__participantXss=1">';
    const safeUrl = 'https://example.test/character?name=%22%3E&sheet=1';
    const participant = { id: 1, display_name: guest ? markup : '', user_detail: guest ? null : { nickname: markup },
      character_name: markup, character_sheet_url: guest ? safeUrl : 'javascript:window.__participantXss=1', roles: [] };
    const session = { id: 1, title: '参加者の表示確認', gm: 1, my_role: 'gm', status: 'planned',
      date: '2030-01-01T19:00:00Z', participants_detail: [participant] };
    await page.route('**/api/schedules/sessions/my-sessions/?*', route => route.fulfill({ json: { results: [session], page_size: 20 } }));
    await page.route('**/api/schedules/sessions/1/', route => route.fulfill({ json: session }));
    await devLogin(page, 'admin', '/api/schedules/sessions/web/');
    await page.locator('#mySessionsList button[onclick="manageParticipants(1)"]').click();
    const modal = page.locator('#participantsModal');
    await expect(modal).toBeVisible();
    await expect(modal.locator('.participant-item strong')).toHaveText(markup);
    await expect(modal.locator('.participant-item small')).toHaveText(`キャラクター: ${markup}`);
    await expect(modal.locator('img')).toHaveCount(0);
    expect(await page.evaluate(() => (window as any).__participantXss)).toBeUndefined();
    const link = modal.locator('.character-sheet-link');
    if (guest) {
      await expect(link).toHaveAttribute('href', safeUrl);
      await expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    } else {
      await expect(link).toHaveCount(0);
    }
  });
}

test('participant management handles unnamed guests and invalid or internal links', async ({ page }) => {
  const participants = [
    { id: 1, user_detail: null, character_sheet_url: '' },
    { id: 2, user_detail: { username: 'username-only' }, character_sheet_url: 'http://[' },
    { id: 3, user_detail: null, display_name: '内部リンク', character_sheet_url: '/accounts/character/list/' },
    { id: 4, user_detail: null, display_name: '無効なリンク', character_sheet_url: 'data:text/html,<script>alert(1)</script>' },
  ];
  const session = { id: 1, title: '参加者のリンク確認', gm: 1, my_role: 'gm', status: 'planned',
    date: '2030-01-01T19:00:00Z', participants_detail: participants };
  await page.route('**/api/schedules/sessions/my-sessions/?*', route => route.fulfill({ json: { results: [session], page_size: 20 } }));
  await page.route('**/api/schedules/sessions/1/', route => route.fulfill({ json: session }));
  await devLogin(page, 'admin', '/api/schedules/sessions/web/');
  await page.locator('#mySessionsList button[onclick="manageParticipants(1)"]').click();
  const modal = page.locator('#participantsModal');
  await expect(modal).toBeVisible();
  await expect(modal.locator('.participant-item strong')).toHaveText(['ゲスト', 'username-only', '内部リンク', '無効なリンク']);
  await expect(modal.locator('.character-sheet-link')).toHaveCount(1);
  await expect(modal.locator('.character-sheet-link')).toHaveAttribute('href', new URL('/accounts/character/list/', page.url()).href);
});
