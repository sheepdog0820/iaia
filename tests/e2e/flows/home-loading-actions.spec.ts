import { test, expect } from '@playwright/test';
import { devLogin } from './helpers';

for (const viewport of [{ width: 1280, height: 900 }, { width: 390, height: 844 }]) {
  test(`home actions survive sessions loading during click at ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    let releaseSessions!: () => void;
    const sessionsReady = new Promise<void>(resolve => { releaseSessions = resolve; });
    await page.route('**/api/schedules/sessions/upcoming/', async route => {
      await sessionsReady;
      await route.fulfill({ json: Array.from({ length: 5 }, (_, index) => ({
        id: index + 1, title: `読み込み検証セッション${index + 1}`,
        date: '2026-10-01T12:00:00+09:00', status: 'planned',
        visibility: 'private', participant_count: 3, gm_name: '検証GM',
      })) });
    });
    try {
      await devLogin(page);
      await expect(page.locator('#play-statistics .spinner-border')).toHaveCount(0);
      const button = page.locator('#create-character-btn');
      await button.scrollIntoViewIfNeeded();
      const before = await button.boundingBox();
      if (!before) throw new Error('Expected the character creation button');
      await page.mouse.move(before.x + before.width / 2, before.y + before.height / 2);
      await page.mouse.down();
      releaseSessions();
      await expect(page.locator('#upcoming-sessions')).toContainText('読み込み検証セッション5');
      await page.mouse.up();
      await expect(page.locator('#characterCreationModal')).toHaveClass(/show/);
      await page.locator('#characterCreationModal .btn-close').click();
      await expect(page.locator('#characterCreationModal')).not.toHaveClass(/show/);
      await expect(page.locator('#characterCreationModal')).toBeHidden();
    } finally {
      releaseSessions();
    }
  });
}
