import { expect, test } from '@playwright/test';
import { devLogin } from './helpers';

const guidance = '処理結果を確認できません。Google側に反映されている可能性があります。重複を避けるため、再実行する前にGoogle CalendarまたはGoogle Sheetsの結果を確認してください。';

for (const width of [1280, 390]) {
  test(`Google stale execution has Japanese unknown result and no retry at width ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const errors: string[] = [];
    let jobReads = 0;
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/api/**', async route => {
      const request = route.request();
      const url = new URL(request.url());
      expect(request.method()).toBe('GET');
      if (url.pathname === '/api/jobs/') {
        jobReads += 1;
        if (process.env.TABLENO_EXECUTION_REAL_JOBS === '1') {
          // Isolated local run: real Django classification, owner filter and serializer.
          await route.continue();
        } else {
          // Ordinary CI needs no synthetic database setup beyond its existing users.
          await route.fulfill({ json: [{ id: 'uncertain-fixture', job_type: url.searchParams.get('job_type'),
            status: 'uncertain', progress: 10, error: guidance, created_at: '2026-10-06T00:00:00Z' }] });
        }
      } else if (url.pathname === '/api/accounts/groups/' || url.pathname === '/api/schedules/sessions/') {
        await route.fulfill({ json: [] });
      } else if (url.pathname === '/api/google/integration/') {
        await route.fulfill({ json: { connected: false, calendar_enabled: false, sheets_enabled: false, scopes: [] } });
      } else if (url.pathname === '/api/schedules/notifications/unread_count/') {
        await route.fulfill({ json: { unread_count: 0 } });
      } else {
        throw new Error(`Unexpected fixture API: ${url.pathname}`);
      }
    });
    await devLogin(page, 'admin', '/integrations/');
    const history = page.locator('#integration-jobs');
    await expect(history.locator('tr')).toHaveCount(2);
    await expect(history.locator('.badge')).toHaveText(['結果不明', '結果不明']);
    for (const badge of await history.locator('.badge').all()) {
      await expect(badge).toHaveClass(/bg-warning/);
      await expect(badge).toHaveClass(/text-dark/);
      await expect(badge).toHaveCSS('color', 'rgb(33, 37, 41)');
    }
    await expect(history).toContainText('Google Calendar同期');
    await expect(history).toContainText('Google Sheets出力');
    await expect(history.locator('[data-job-error]')).toHaveText([guidance, guidance]);
    await expect(history.locator('[data-retry-job]')).toHaveCount(0);
    await expect(history.locator('img')).toHaveCount(0);
    await expect(history).not.toContainText('fixture-private-input');
    await expect(page.getByRole('columnheader', { name: '処理結果・案内', exact: true })).toBeVisible();
    if (width === 390) {
      await expect(page.locator('#integration-jobs-table')).toHaveCSS('min-width', '900px');
      expect(await history.locator('tr').first().evaluate(row => row.getBoundingClientRect().height)).toBeLessThan(150);
      const region = page.getByRole('region', { name: '連携ジョブ一覧', exact: true });
      await region.focus();
      await page.keyboard.press('ArrowRight');
      await expect.poll(() => region.evaluate(element => element.scrollLeft)).toBeGreaterThan(0);
    }
    await page.locator('#reload-jobs').focus();
    await page.keyboard.press('Enter');
    await expect.poll(() => jobReads).toBe(4);
    await expect(history.locator('.badge')).toHaveText(['結果不明', '結果不明']);
    expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
    expect(errors).toEqual([]);
  });
}
