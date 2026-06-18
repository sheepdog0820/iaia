import { test, expect } from '@playwright/test';
import { devLogin } from './helpers';

test.describe('integration settings', () => {
  test('operational integration controls call the public APIs', async ({ page }) => {
    const requests: Array<{ method: string; path: string; body?: unknown }> = [];
    let discordDeliveries = [
      {
        id: 77,
        event_type: 'session_updated',
        status: 'failed',
        attempts: 2,
        last_error: 'Discord returned 500',
        created_at: '2026-06-18T00:00:00Z',
        sent_at: null,
        payload: { content: 'failed' },
        idempotency_key: 'session-updated:77',
      },
      {
        id: 78,
        event_type: 'handout_released',
        status: 'failed',
        attempts: 1,
        last_error: 'Background task broker is unavailable.',
        created_at: '2026-06-18T00:01:00Z',
        sent_at: null,
        payload: { content: 'broker unavailable' },
        idempotency_key: 'handout-released:78',
      },
    ];

    await page.route('**/api/accounts/groups/', route => route.fulfill({
      json: [{ id: 1, name: '<Admin Group>', member_role: 'admin' }],
    }));
    await page.route('**/api/schedules/sessions/', route => route.fulfill({
      json: [{ id: 10, title: '<Integration Session>' }],
    }));
    await page.route('**/api/google/integration/', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          json: {
            connected: true,
            calendar_enabled: true,
            sheets_enabled: true,
            scopes: ['calendar', 'sheets'],
          },
        });
        return;
      }
      await route.fulfill({ json: { connected: true } });
    });
    await page.route('**/api/groups/1/discord-settings/', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          json: {
            enabled: true,
            event_types: ['session_updated'],
            configured: true,
          },
        });
        return;
      }
      requests.push({
        method: route.request().method(),
        path: new URL(route.request().url()).pathname,
        body: route.request().postDataJSON(),
      });
      await route.fulfill({ json: route.request().postDataJSON() });
    });
    await page.route('**/api/groups/1/discord-deliveries/?status=failed', route => route.fulfill({
      json: discordDeliveries,
    }));
    await page.route('**/api/groups/1/discord-deliveries/77/retry/', async route => {
      requests.push({
        method: route.request().method(),
        path: new URL(route.request().url()).pathname,
      });
      discordDeliveries = discordDeliveries.filter(delivery => delivery.id !== 77);
      await route.fulfill({ status: 202, json: { delivery_id: 77, queued: true } });
    });
    await page.route('**/api/groups/1/discord-deliveries/78/retry/', async route => {
      requests.push({
        method: route.request().method(),
        path: new URL(route.request().url()).pathname,
      });
      discordDeliveries = [];
      await route.fulfill({ status: 202, json: { delivery_id: 78, queued: false } });
    });
    await page.route('**/api/groups/1/links/', route => route.fulfill({ json: [] }));
    await page.route('**/api/calendar/subscription-token/rotate/', async route => {
      requests.push({
        method: route.request().method(),
        path: new URL(route.request().url()).pathname,
      });
      await route.fulfill({
        json: { subscription_url: 'http://localhost:8000/calendar/subscribe/test.ics' },
      });
    });
    await page.route('**/api/character-sheets/google-sheets/import/', async route => {
      const body = route.request().postDataJSON();
      requests.push({
        method: route.request().method(),
        path: new URL(route.request().url()).pathname,
        body,
      });
      if (body.preview) {
        await route.fulfill({
          json: {
            rows: [{
              row: 2,
              data: { name: '<Investigator>', edition: '6th' },
              errors: {},
            }],
          },
        });
        return;
      }
      await route.fulfill({ status: 201, json: { imported_ids: [99] } });
    });
    await page.route('**/api/character-sheets/google-sheets/export/', async route => {
      requests.push({
        method: route.request().method(),
        path: new URL(route.request().url()).pathname,
        body: route.request().postDataJSON(),
      });
      await route.fulfill({ status: 202, json: { job_id: 'job-1' } });
    });

    await devLogin(page, 'admin', '/integrations/');

    await expect(page.locator('#discord-group option')).toHaveText('<Admin Group> (#1)');
    await expect(page.locator('#integration-session option')).toHaveText('<Integration Session> (#10)');
    await expect(page.locator('#discord-session-updated')).toBeChecked();
    await expect(page.locator('h2')).toContainText('Discord通知失敗履歴');
    await expect(page.locator('#discord-deliveries')).toContainText('Discord returned 500');
    await expect(page.locator('#discord-deliveries')).toContainText('Background task broker is unavailable.');
    await expect(page.locator('[data-retry-discord-delivery="77"]')).toHaveText('再送');

    await page.check('#discord-handout-released');
    await page.click('#save-discord-settings');
    await expect.poll(() =>
      requests.some(item =>
        item.path === '/api/groups/1/discord-settings/' &&
        (item.body as { event_types?: string[] })?.event_types?.includes('handout_released')
      )
    ).toBeTruthy();

    await page.click('[data-retry-discord-delivery="77"]');
    await expect.poll(() =>
      requests.some(item =>
        item.method === 'POST' &&
        item.path === '/api/groups/1/discord-deliveries/77/retry/'
      )
    ).toBeTruthy();
    await expect(page.locator('#integration-message')).toContainText('Discord通知の再送を開始しました: 77');

    await page.click('[data-retry-discord-delivery="78"]');
    await expect.poll(() =>
      requests.some(item =>
        item.method === 'POST' &&
        item.path === '/api/groups/1/discord-deliveries/78/retry/'
      )
    ).toBeTruthy();
    await expect(page.locator('#integration-message')).toContainText(
      'Discord通知を再送キューに登録できませんでした: 78'
    );
    await page.click('#reload-discord-deliveries');
    await expect(page.locator('#discord-deliveries')).toContainText('Discord通知失敗はありません。');

    await page.click('#rotate-calendar-token');
    await expect(page.locator('#calendar-subscription-url')).toHaveValue(
      'http://localhost:8000/calendar/subscribe/test.ics'
    );

    await page.fill('#sheets-spreadsheet-id', 'sheet-1');
    await page.click('#preview-google-sheets');
    await expect(page.locator('#sheets-preview-body')).toContainText('<Investigator>');
    await expect(page.locator('#import-google-sheets')).toBeEnabled();
    await page.click('#import-google-sheets');
    await expect(page.locator('#integration-message')).toContainText('1件を取り込みました');

    await page.click('#export-google-sheets');
    await expect(page.locator('#integration-message')).toContainText('job-1');
  });

  test('guest invitation landing and claim complete the ownership handoff', async ({ page }) => {
    await devLogin(page);
    await page.waitForFunction(() => (window as any).axios?.post);

    const suffix = Date.now();
    const setup = await page.evaluate(async (value: number) => {
      const groupResponse = await (window as any).axios.post('/api/accounts/groups/', {
        name: `Guest E2E Group ${value}`,
        visibility: 'private',
      });
      const sessionResponse = await (window as any).axios.post('/api/schedules/sessions/', {
        title: `Guest E2E Session ${value}`,
        date: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
        group: groupResponse.data.id,
        duration_minutes: 120,
        visibility: 'group',
      });
      const invitationResponse = await (window as any).axios.post(
        `/api/sessions/${sessionResponse.data.id}/guest-invitations/`,
        { expires_in_hours: 1 }
      );
      return {
        sessionTitle: sessionResponse.data.title,
        invitationUrl: invitationResponse.data.invitation_url,
      };
    }, suffix);

    await page.goto(setup.invitationUrl);
    await expect(page.locator('h1')).toContainText(setup.sessionTitle);
    await page.fill('#guest-name', 'E2E Guest');
    await page.selectOption('#player-slot', '1');
    await page.fill('#character-name', 'E2E Investigator');

    const responsePromise = page.waitForResponse(response =>
      response.url().includes('/api/guest-invitations/') &&
      response.url().endsWith('/respond/') &&
      response.request().method() === 'POST'
    );
    await page.click('#guest-response-form button[type="submit"]');
    const response = await responsePromise;
    expect(response.status()).toBe(201);
    const participantId = (await response.json()).participant_id;
    await expect(page.locator('#guest-response-message')).toContainText('参加を登録しました');

    const claimResult = await page.evaluate(async (id: number) => {
      const claimResponse = await (window as any).axios.post(`/api/participants/${id}/claim/`);
      return claimResponse.data;
    }, participantId);
    expect(claimResult.participant_id).toBe(participantId);
    expect(claimResult.character_name).toBe('E2E Investigator');
  });
});
