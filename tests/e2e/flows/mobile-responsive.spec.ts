import { expect, Page, test } from '@playwright/test';
import { devLogin } from './helpers';

const mobileViewports = [
  { name: 'iPhone', width: 390, height: 844 },
  { name: 'Android', width: 412, height: 915 },
];

async function expectNoHorizontalOverflow(page: Page): Promise<void> {
  const metrics = await page.evaluate(() => {
    const root = document.documentElement;
    const body = document.body;
    return {
      clientWidth: root.clientWidth,
      scrollWidth: Math.max(root.scrollWidth, body?.scrollWidth ?? 0),
    };
  });

  expect(metrics.scrollWidth, `scrollWidth=${metrics.scrollWidth}, clientWidth=${metrics.clientWidth}`)
    .toBeLessThanOrEqual(metrics.clientWidth + 1);
}

function futureIso(minutesFromNow: number): string {
  return new Date(Date.now() + minutesFromNow * 60 * 1000).toISOString();
}

test.describe('mobile responsive release checks', () => {
  for (const viewport of mobileViewports) {
    test(`sessions list is usable on ${viewport.name}`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await devLogin(page);
      await page.waitForFunction(() => (window as any).axios?.post);

      const suffix = `${viewport.name}-${Date.now()}`;
      const sessionDate = futureIso(10);
      const session = await page.evaluate(async ({ suffixValue, sessionDateValue }) => {
        const axios = (window as any).axios;
        const groupResponse = await axios.post('/api/accounts/groups/', {
          name: `Mobile E2E Group ${suffixValue}`,
          visibility: 'private',
        });
        const sessionResponse = await axios.post('/api/schedules/sessions/', {
          title: `Mobile E2E Session ${suffixValue}`,
          date: sessionDateValue,
          group: groupResponse.data.id,
          duration_minutes: 120,
          location: 'Online',
          visibility: 'group',
          description: 'Mobile responsive release check.',
        });
        return sessionResponse.data;
      }, { suffixValue: suffix, sessionDateValue: sessionDate });

      await page.goto('/api/schedules/sessions/view/?limit=100&period=future');
      await expect(page.locator('h1, h2, h3').filter({ hasText: /セッション|Chrono|R'lyeh/ }).first())
        .toBeVisible();
      await expect(page.locator('body')).toContainText(session.title);
      await expect(page.locator(`a[href="/api/schedules/sessions/${session.id}/detail/"]:visible`).first())
        .toBeVisible();
      await expectNoHorizontalOverflow(page);
    });

    test(`character edit is usable on ${viewport.name}`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await devLogin(page);
      await page.waitForFunction(() => (window as any).axios?.post);

      const character = await page.evaluate(async (suffixValue: string) => {
        const response = await (window as any).axios.post('/api/accounts/character-sheets/create_6th_edition/', {
          name: `Mobile E2E Investigator ${suffixValue}`,
          player_name: 'admin',
          age: 31,
          gender: 'unknown',
          occupation: '探偵',
          birthplace: 'Arkham',
          residence: 'Tokyo',
          str_value: 11,
          con_value: 12,
          pow_value: 13,
          dex_value: 14,
          app_value: 10,
          siz_value: 12,
          int_value: 15,
          edu_value: 16,
          notes: 'Mobile edit release check.',
        });
        return response.data;
      }, `${viewport.name}-${Date.now()}`);

      await page.goto(`/accounts/character/create/6th/?id=${character.id}`);
      await expect(page.locator('#character-sheet-form')).toBeVisible();
      await expect(page.locator('#character-name')).toHaveValue(character.name);
      await expect(page.locator('#occupation')).toBeVisible();
      await expect(page.locator('button[type="submit"], #footerSaveCharacter').first()).toBeVisible();
      await expectNoHorizontalOverflow(page);
    });
  }
});
