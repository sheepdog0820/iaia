import { test, expect } from '@playwright/test';
import { devLogin } from './helpers';

test.describe('youtube links', () => {
  test('gm can reorder youtube links', async ({ page }) => {
    await devLogin(page);
    await page.waitForFunction(() => (window as any).axios?.post);

    const sessionId = await page.evaluate(async () => {
      const groupName = `E2E YouTube Group ${Date.now()}`;
      const groupResponse = await (window as any).axios.post('/api/accounts/groups/', {
        name: groupName,
        visibility: 'private',
      });
      const group = groupResponse.data;

      const sessionTitle = `E2E YouTube Session ${Date.now()}`;
      const sessionDate = new Date(Date.now() + 10 * 60 * 1000).toISOString();

      const sessionResponse = await (window as any).axios.post('/api/schedules/sessions/', {
        title: sessionTitle,
        date: sessionDate,
        duration_minutes: 120,
        location: 'Online',
        visibility: 'public',
        group: group.id,
        description: 'Created by Playwright YouTube reorder test.',
      });
      const session = sessionResponse.data;

      const baseUrl = 'https://www.youtube.com/watch?v=yt_reorder_';
      const payloads = [
        { youtube_url: `${baseUrl}001`, perspective: 'GM視点', part_number: 1 },
        { youtube_url: `${baseUrl}002`, perspective: 'GM視点', part_number: 2 },
        { youtube_url: `${baseUrl}003`, perspective: 'GM視点', part_number: 3 },
      ];

      for (const payload of payloads) {
        await (window as any).axios.post(
          `/api/schedules/sessions/${session.id}/youtube-links/`,
          payload
        );
      }

      return session.id as number;
    });

    await page.goto(`/api/schedules/sessions/${sessionId}/detail/`);
    await expect(page.locator('#youtubeLinksContainer .youtube-link-item')).toHaveCount(3);
    await expect(page.locator('#youtubeLinksContainer .youtube-link-drag-handle')).toHaveCount(3);

    const orderBefore = await page.evaluate(() => {
      return Array.from(
        document.querySelectorAll('#youtubeLinksContainer .youtube-link-item[data-youtube-link-id]')
      ).map(el => (el as HTMLElement).dataset.youtubeLinkId || '');
    });
    expect(orderBefore).toHaveLength(3);

    const reorderWaiters = Array.from({ length: orderBefore.length }, () =>
      page.waitForResponse(response => {
        if (response.request().method() !== 'POST') return false;
        const url = new URL(response.url());
        return (
          url.pathname.startsWith('/api/schedules/youtube-links/') &&
          url.pathname.endsWith('/reorder/') &&
          response.status() === 200
        );
      })
    );

    const dragHandle = page.locator('#youtubeLinksContainer .youtube-link-drag-handle').first();
    const lastItem = page.locator('#youtubeLinksContainer .youtube-link-item').nth(2);
    await lastItem.scrollIntoViewIfNeeded();
    const lastBox = await lastItem.boundingBox();
    if (!lastBox) {
      throw new Error('Expected last youtube link item to be visible');
    }

    await dragHandle.dragTo(lastItem, {
      targetPosition: { x: Math.max(1, Math.floor(lastBox.width / 2)), y: Math.max(1, Math.floor(lastBox.height - 2)) },
    });

    await Promise.all(reorderWaiters);
    await expect(page.locator('#youtubeLinksContainer .youtube-link-item')).toHaveCount(3);

    const orderAfter = await page.evaluate(() => {
      return Array.from(
        document.querySelectorAll('#youtubeLinksContainer .youtube-link-item[data-youtube-link-id]')
      ).map(el => (el as HTMLElement).dataset.youtubeLinkId || '');
    });
    expect(orderAfter).toEqual([orderBefore[1], orderBefore[2], orderBefore[0]]);

    await page.reload({ waitUntil: 'domcontentloaded' });
    await expect(page.locator('#youtubeLinksContainer .youtube-link-item')).toHaveCount(3);
    const orderAfterReload = await page.evaluate(() => {
      return Array.from(
        document.querySelectorAll('#youtubeLinksContainer .youtube-link-item[data-youtube-link-id]')
      ).map(el => (el as HTMLElement).dataset.youtubeLinkId || '');
    });
    expect(orderAfterReload).toEqual(orderAfter);
  });
});

