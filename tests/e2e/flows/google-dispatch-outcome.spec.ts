import { expect, test } from '@playwright/test';
import { devLogin } from './helpers';

const unknownMessage = 'ジョブを作成しましたが、開始状況を確認できません。重複を避けるため、同じ操作を繰り返す前にジョブ履歴で結果を確認してください。ジョブID: new-google-job';
const refreshMessage = '一覧を更新できませんでした。ページを再読み込みして結果を確認してください。';
const communicationMessage = '操作結果を確認できませんでした。処理が進んでいる可能性があります。重複を避けるため、同じ操作を繰り返す前にジョブ履歴を更新して結果を確認してください。';

const actions = [
  { name: 'Calendar', button: '#sync-google-calendar', path: '/api/sessions/10/google-calendar/sync/', success: '同期ジョブを作成しました', type: 'google_calendar_sync' },
  { name: 'Sheets', button: '#export-google-sheets', path: '/api/character-sheets/google-sheets/export/', success: '出力ジョブを作成しました', type: 'google_sheets_export' },
  { name: 'retry', button: '[data-retry-job="old-google-job"]', path: '/api/jobs/old-google-job/retry/', success: '再試行ジョブを作成しました', type: 'google_calendar_sync' },
];

for (const action of actions) {
  for (const outcome of ['queued', 'unknown-running', 'unknown-succeeded', 'unknown-refresh', 'queued-refresh', 'network', 'server', 'permission', 'authentication', 'forbidden', 'invalid-detail', 'pending']) {
    test(`Google ${action.name} dispatch reports ${outcome} without assuming no delivery`, async ({ page }) => {
      const errors: string[] = [];
      page.on('pageerror', error => errors.push(error.message));
      let posts = 0;
      let refreshed = 0;
      let release!: () => void;
      const pending = new Promise<void>(resolve => { release = resolve; });
      const oldJob = { id: 'old-google-job', job_type: action.type, status: 'failed', progress: 0, error: '試験用エラー', created_at: '2026-10-06T00:00:00Z' };
      const newJob = { ...oldJob, id: 'new-google-job', status: outcome === 'unknown-succeeded' ? 'succeeded' : 'running', error: '', progress: 50 };
      await page.route('**/api/**', async route => {
        const request = route.request();
        const url = new URL(request.url());
        if (request.method() === 'POST' && url.pathname === action.path) {
          posts += 1;
          if (action.name === 'Sheets') {
            expect(request.postDataJSON()).toEqual({ spreadsheet_id: 'isolated-sheet', range: 'Characters!A1' });
          }
          if (outcome === 'pending') await pending;
          if (outcome === 'network') {
            await route.abort('failed');
          } else if (['server', 'permission', 'authentication', 'forbidden', 'invalid-detail'].includes(outcome)) {
            const status = outcome === 'server' ? 503 : outcome === 'authentication' ? 401 : outcome === 'forbidden' ? 403 : 400;
            await route.fulfill({ status, json: { detail: outcome === 'permission' ? 'Google連携を確認してください。' : outcome === 'invalid-detail' ? { secret: 'credential-detail' } : '<img src=x onerror=alert(1)> credential-detail' } });
          } else {
            await route.fulfill({ status: 202, json: { job_id: 'new-google-job', queued: !outcome.startsWith('unknown') } });
          }
          return;
        }
        if (url.pathname === '/api/accounts/groups/') {
          await route.fulfill({ json: [] });
        } else if (url.pathname === '/api/schedules/sessions/') {
          await route.fulfill({ json: [{ id: 10, title: '隔離セッション' }] });
        } else if (url.pathname === '/api/google/integration/') {
          await route.fulfill({ json: { connected: true, calendar_enabled: true, sheets_enabled: true, scopes: [] } });
        } else if (url.pathname === '/api/schedules/notifications/unread_count/') {
          await route.fulfill({ json: { unread_count: 0 } });
        } else if (url.pathname === '/api/jobs/') {
          if (posts) {
            refreshed += 1;
            if (outcome.endsWith('refresh')) {
              await route.fulfill({ status: 503, json: { detail: 'credential-detail' } });
              return;
            }
          }
          await route.fulfill({ json: url.searchParams.get('job_type') === action.type ? [posts ? newJob : oldJob] : [] });
        } else {
          throw new Error(`Unexpected fixture API: ${request.method()} ${url.pathname}`);
        }
      });
      await devLogin(page, 'admin', '/integrations/');
      await expect(page.locator('#integration-jobs')).toContainText('試験用エラー');
      await page.locator('#sheets-spreadsheet-id').fill('isolated-sheet');
      const button = page.locator(action.button);
      await button.click();
      if (outcome === 'pending') {
        try {
          await expect(button).toBeDisabled();
          await button.dispatchEvent('click');
          await expect.poll(() => posts).toBe(1);
        } finally {
          release();
        }
      }
      const message = page.locator('#integration-message');
      if (outcome.startsWith('unknown')) {
        await expect(message).toHaveText(unknownMessage + (outcome.endsWith('refresh') ? ` ${refreshMessage}` : ''));
        await expect(message).toHaveClass(/alert-warning/);
        await expect(message).toHaveClass(/text-dark/);
      } else if (outcome === 'network' || outcome === 'server') {
        await expect(message).toHaveText(communicationMessage);
        await expect(message).toHaveClass(/alert-warning/);
        await expect(message).toHaveClass(/text-dark/);
      } else if (outcome === 'permission') {
        await expect(message).toHaveText('Google連携を確認してください。');
        await expect(message).toHaveClass(/alert-danger/);
      } else if (outcome === 'authentication' || outcome === 'forbidden') {
        await expect(message).toHaveText('ログイン状態または操作権限を確認できません。再ログインしてから連携状態を確認してください。');
        await expect(message).toHaveClass(/alert-danger/);
      } else if (outcome === 'invalid-detail') {
        await expect(message).toHaveText('操作を受け付けられませんでした。入力内容と連携状態を確認してください。');
        await expect(message).toHaveClass(/alert-danger/);
      } else {
        await expect(message).toHaveText(`${action.success}: new-google-job` + (outcome.endsWith('refresh') ? ` ${refreshMessage}` : ''));
        await expect(message).toHaveClass(outcome.endsWith('refresh') ? /alert-warning/ : /alert-success/);
      }
      if (['queued', 'pending', 'unknown-running', 'unknown-succeeded'].includes(outcome)) {
        await expect(page.locator('#integration-jobs')).toContainText(newJob.status);
        await expect(page.locator('[data-retry-job="new-google-job"]')).toHaveCount(0);
        expect(refreshed).toBe(2);
      }
      await expect(message.locator('img')).toHaveCount(0);
      await expect(message).not.toContainText('credential-detail');
      if (action.name !== 'retry' || ['network', 'server', 'permission', 'authentication', 'forbidden', 'invalid-detail', 'unknown-refresh', 'queued-refresh'].includes(outcome)) {
        await expect(button).toBeEnabled();
      }
      expect(posts).toBe(1);
      expect(errors).toEqual([]);
    });
  }
}
