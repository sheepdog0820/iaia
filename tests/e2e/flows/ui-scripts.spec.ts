import { test, expect, Page } from '@playwright/test';
import { devLogin } from './helpers';

type JsErrorTracker = {
  errors: string[];
  clear: () => void;
  assertNoErrors: (context: string) => void;
};

function trackJsErrors(page: Page): JsErrorTracker {
  const errors: string[] = [];
  const ignoredConsolePatterns = [
    /downloadable font/i,
    /fonts\.gstatic\.com/i,
    /fonts\.googleapis\.com/i,
  ];

  page.on('pageerror', error => {
    errors.push(`pageerror: ${error.message}`);
  });

  page.on('console', msg => {
    if (msg.type() !== 'error') return;
    const text = msg.text();
    if (ignoredConsolePatterns.some(pattern => pattern.test(text))) return;
    const location = msg.location();
    const locationSuffix = location?.url
      ? ` (${location.url}:${location.lineNumber}:${location.columnNumber})`
      : '';
    errors.push(`console.error: ${text}${locationSuffix}`);
  });

  return {
    errors,
    clear: () => {
      errors.length = 0;
    },
    assertNoErrors: (context: string) => {
      expect(
        errors,
        `JavaScript errors detected on ${context}:\n${errors.join('\n')}`
      ).toEqual([]);
      errors.length = 0;
    }
  };
}

async function fetchFirstId(page: Page, endpoint: string): Promise<number | null> {
  const response = await page.request.get(endpoint);
  if (!response.ok()) return null;
  const data = await response.json();
  const items = Array.isArray(data) ? data : data?.results ?? [];
  const first = items?.[0];
  return typeof first?.id === 'number' ? first.id : null;
}

async function waitForBootstrapModal(page: Page): Promise<void> {
  await page.waitForFunction(() => {
    return Boolean((window as any).bootstrap?.Modal);
  });
}

async function showBootstrapModal(page: Page, modalId: string): Promise<void> {
  await waitForBootstrapModal(page);
  await page.evaluate((id) => {
    const modalEl = document.getElementById(id);
    if (!modalEl) throw new Error(`Missing modal: ${id}`);
    const bootstrap = (window as any).bootstrap;
    if (!bootstrap?.Modal) throw new Error('Bootstrap Modal not available');
    const modal = new bootstrap.Modal(modalEl);
    modal.show();
  }, modalId);
}

async function hideBootstrapModal(page: Page, modalId: string): Promise<void> {
  await waitForBootstrapModal(page);
  await page.evaluate((id) => {
    const modalEl = document.getElementById(id);
    if (!modalEl) throw new Error(`Missing modal: ${id}`);
    const bootstrap = (window as any).bootstrap;
    if (!bootstrap?.Modal) throw new Error('Bootstrap Modal not available');
    const instance = bootstrap.Modal.getInstance(modalEl) ?? new bootstrap.Modal(modalEl);
    instance.hide();
  }, modalId);
}

async function closeBootstrapModal(page: Page, modalId: string): Promise<void> {
  const closeButton = page.locator(`#${modalId} .btn-close`);
  if (await closeButton.count()) {
    await closeButton.click();
  } else {
    await hideBootstrapModal(page, modalId);
  }
  await page.waitForFunction(
    (id) => !document.getElementById(id)?.classList.contains('show'),
    modalId
  );
}

async function setAbilityValues(page: Page, values: Record<string, string>): Promise<void> {
  await page.evaluate((abilityValues) => {
    const entries = Object.entries(abilityValues);
    entries.forEach(([id, value]) => {
      const input = document.getElementById(id) as HTMLInputElement | null;
      if (!input) throw new Error(`Missing ability input: ${id}`);
      input.value = value;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });
  }, values);
}

async function waitForSpinnerToDisappear(page: Page, containerSelector: string): Promise<void> {
  const container = page.locator(containerSelector);
  if (!(await container.count())) return;
  const spinner = container.locator('.spinner-border');
  if (await spinner.count()) {
    await expect(spinner).toHaveCount(0, { timeout: 15000 });
  }
}

test.describe('ui script health', () => {
  test.describe.configure({ timeout: 90000 });

  test('core screens load without JS errors', async ({ page }) => {
    await page.route('**/favicon.ico', route => route.fulfill({ status: 204, body: '' }));
    const tracker = trackJsErrors(page);

    await devLogin(page);
    tracker.clear();

    await expect(page.locator('.welcome-section')).toBeVisible();
    await waitForSpinnerToDisappear(page, '#upcoming-sessions');
    await waitForSpinnerToDisappear(page, '#play-statistics');
    await waitForSpinnerToDisappear(page, '#recent-activity');
    await waitForSpinnerToDisappear(page, '#user-groups');
    tracker.assertNoErrors('home');

    const calendarGroupsResponse = page.waitForResponse(response => {
      if (response.request().method() !== 'GET') return false;
      return new URL(response.url()).pathname === '/api/accounts/groups/';
    });
    const calendarEventsResponse = page.waitForResponse(response => {
      if (response.request().method() !== 'GET') return false;
      return new URL(response.url()).pathname === '/api/schedules/calendar/';
    });

    await page.goto('/api/schedules/calendar/view/');
    await expect(page.locator('h1')).toContainText('Chrono Abyss');
    await expect(page.locator('#calendar')).toBeVisible();
    await expect((await calendarGroupsResponse).ok()).toBeTruthy();
    await expect((await calendarEventsResponse).ok()).toBeTruthy();
    await showBootstrapModal(page, 'newSessionModal');
    await expect(page.locator('#newSessionModal')).toHaveClass(/show/);
    await closeBootstrapModal(page, 'newSessionModal');
    await waitForSpinnerToDisappear(page, '#upcomingSessions');
    tracker.assertNoErrors('calendar');

    await page.goto('/api/schedules/sessions/view/');
    await expect(page.locator('h1')).toContainText("R'lyeh Log");
    await waitForSpinnerToDisappear(page, '#statsContainer');
    await waitForSpinnerToDisappear(page, '#sessionsList');
    tracker.assertNoErrors('sessions');

    const sessionId = await fetchFirstId(page, '/api/schedules/sessions/');
    if (sessionId) {
      await page.goto(`/api/schedules/sessions/${sessionId}/detail/`);
      await expect(page.locator('.breadcrumb')).toBeVisible();
      await expect(page.locator('.card-header h3')).toBeVisible();
      tracker.assertNoErrors('session detail');
    }

    await page.goto('/api/scenarios/archive/view/');
    await expect(page.locator('h1')).toContainText('Mythos Archive');
    await waitForSpinnerToDisappear(page, '#scenariosList');
    tracker.assertNoErrors('scenarios');

    const scenarioId = await fetchFirstId(page, '/api/scenarios/scenarios/');
    if (scenarioId) {
      const detailResponse = page.waitForResponse(response => {
        if (response.request().method() !== 'GET') return false;
        return new URL(response.url()).pathname === `/api/scenarios/scenarios/${scenarioId}/`;
      });
      await page.waitForFunction(() => typeof (window as any).showScenarioDetail === 'function');
      await page.evaluate((id) => {
        (window as any).showScenarioDetail?.(id);
      }, scenarioId);
      await expect(page.locator('#scenarioDetailModal')).toHaveClass(/show/);
      await expect((await detailResponse).ok()).toBeTruthy();
      await closeBootstrapModal(page, 'scenarioDetailModal');
      tracker.assertNoErrors('scenario detail modal');
    }

    await page.goto('/accounts/groups/view/');
    await expect(page.locator('h1')).toContainText('Cult Circle');
    await waitForSpinnerToDisappear(page, '#groupsList');
    await waitForSpinnerToDisappear(page, '#groupInvitations');
    await waitForSpinnerToDisappear(page, '#friendsList');
    tracker.assertNoErrors('groups');

    const groupId = await fetchFirstId(page, '/api/accounts/groups/');
    if (groupId) {
      const groupResponse = page.waitForResponse(response => {
        if (response.request().method() !== 'GET') return false;
        return new URL(response.url()).pathname === `/api/accounts/groups/${groupId}/`;
      });
      await page.waitForFunction(() => typeof (window as any).showGroupDetail === 'function');
      await page.evaluate((id) => {
        (window as any).showGroupDetail?.(id);
      }, groupId);
      await expect(page.locator('#groupDetailModal')).toHaveClass(/show/);
      await expect((await groupResponse).ok()).toBeTruthy();
      await closeBootstrapModal(page, 'groupDetailModal');
      tracker.assertNoErrors('group detail modal');
    }

    await page.goto('/accounts/statistics/view/');
    await expect(page.locator('h1')).toContainText('Tindalos Metrics');
    await waitForSpinnerToDisappear(page, '#yearlyStats');
    await waitForSpinnerToDisappear(page, '#groupStats');
    await waitForSpinnerToDisappear(page, '#recentSessions');
    await waitForSpinnerToDisappear(page, '#ranking');
    tracker.assertNoErrors('statistics');
  });

  test('character creation scripts update derived stats', async ({ page }) => {
    await page.route('**/favicon.ico', route => route.fulfill({ status: 204, body: '' }));
    const tracker = trackJsErrors(page);

    await devLogin(page, 'admin', '/accounts/character/create/6th/');
    tracker.clear();

    await expect(page.locator('#character-sheet-form')).toBeVisible();
    await page.click('#abilities-tab');
    await expect(page.locator('#abilities')).toHaveClass(/show/);

    await setAbilityValues(page, {
      con: '10',
      siz: '14',
      pow: '12',
      int: '13',
      edu: '14',
      str: '12',
      dex: '11',
      app: '9',
    });

    await expect(page.locator('#hp')).toHaveValue('12');
    await expect(page.locator('#mp')).toHaveValue('12');
    await expect(page.locator('#san')).toHaveValue('60');
    await expect(page.locator('#idea')).toHaveValue('65');
    await expect(page.locator('#luck')).toHaveValue('60');
    await expect(page.locator('#know')).toHaveValue('70');
    await expect(page.locator('#damage-bonus')).toHaveValue('+1D4');
    await expect(page.locator('#damage_bonus_display')).toHaveText('+1D4');
    await expect(page.locator('#mp_display')).toHaveText('12');
    await expect(page.locator('#san_display')).toHaveText('60');
    await expect(page.locator('#idea_display')).toHaveText('65');
    await expect(page.locator('#luck_display')).toHaveText('60');
    await expect(page.locator('#know_display')).toHaveText('70');
    tracker.assertNoErrors('character creation');
  });
});
