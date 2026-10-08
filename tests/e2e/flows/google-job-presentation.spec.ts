import { expect, test } from '@playwright/test';
import { devLogin } from './helpers';

const states = [
  ['queued', '処理待ち'], ['target_waiting', '対象待ち'], ['running', '処理中'],
  ['succeeded', '完了'], ['failed', '失敗'], ['needs_review', '確認が必要'],
  ['expired', '期限切れ'], ['superseded', '再試行受付済み'], ['unknown', '状態不明'],
  ['legacy-failed', '失敗'],
];

for (const width of [1280, 390]) {
  test(`Google history distinguishes owned states and fails closed at width ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(error.message));
    let reads = 0;
    const jobs = states.map(([state], index) => ({
      id: `owned-${state}`, job_type: index % 2 ? 'google_sheets_export' : 'google_calendar_sync',
      status: ['failed', 'needs_review', 'expired', 'superseded', 'legacy-failed'].includes(state) ? 'failed' : state,
      ...(state === 'legacy-failed' ? {} : { display_state: state, can_retry: state === 'failed' }),
      status_message: state === 'target_waiting' ? '同じ対象への先行処理を待っています。' :
        state === 'needs_review' ? '結果を確認できないため、再試行できません。' :
        state === 'unknown' ? '<img src=x onerror="window.presentationInjected=1">' : '',
      error: '', progress: 17, created_at: `2026-10-09T00:00:${String(59 - index).padStart(2, '0')}Z`,
    }));
    await page.route('**/api/**', async route => {
      const request = route.request();
      const url = new URL(request.url());
      expect(request.method()).toBe('GET');
      if (url.pathname === '/api/jobs/') {
        reads += 1;
        await route.fulfill({ json: jobs.filter(job => job.job_type === url.searchParams.get('job_type')) });
      } else if (['/api/accounts/groups/', '/api/schedules/sessions/', '/api/schedules/sessions/upcoming/',
        '/api/scenarios/history/'].includes(url.pathname)) {
        await route.fulfill({ json: [] });
      } else if (url.pathname === '/api/schedules/sessions/statistics/') {
        await route.fulfill({ json: { total_hours: 0, session_count: 0 } });
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
    await expect(history.locator('tr')).toHaveCount(10);
    await expect(history.locator('.badge')).toHaveText(states.map(([, label]) => label));
    await expect(history.locator('[data-retry-job]')).toHaveCount(1);
    await expect(history.locator('[data-retry-job]')).toHaveAttribute('data-retry-job', 'owned-failed');
    await expect(history).toContainText('Google Calendar同期');
    await expect(history).toContainText('Google Sheets出力');
    await expect(history).toContainText('同じ対象への先行処理を待っています。');
    await expect(history).toContainText('再試行できません。');
    await expect(history).toContainText('<img src=x onerror="window.presentationInjected=1">');
    await expect(history.locator('img')).toHaveCount(0);
    expect(await page.evaluate(() => (window as any).presentationInjected)).toBeUndefined();
    for (const badge of await history.locator('.bg-warning, .bg-info').all()) {
      await expect(badge).toHaveClass(/text-dark/);
      await expect(badge).toHaveCSS('color', 'rgb(33, 37, 41)');
    }
    if (width === 390) {
      const region = page.getByRole('region', { name: '連携ジョブ一覧', exact: true });
      await region.focus();
      await page.keyboard.press('ArrowRight');
      await expect.poll(() => region.evaluate(element => element.scrollLeft)).toBeGreaterThan(0);
    }
    await page.locator('#reload-jobs').focus();
    await page.keyboard.press('Enter');
    await expect.poll(() => reads).toBe(4);
    await expect(history.locator('.badge')).toHaveText(states.map(([, label]) => label));
    await page.screenshot({ path: test.info().outputPath(`google-history-${width}.png`), fullPage: true });
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await page.goBack({ waitUntil: 'domcontentloaded' });
    await expect(history.locator('.badge')).toHaveText(states.map(([, label]) => label));
    await page.reload({ waitUntil: 'domcontentloaded' });
    await expect(history.locator('[data-retry-job]')).toHaveCount(1);
    expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
    expect(errors).toEqual([]);
  });
}
