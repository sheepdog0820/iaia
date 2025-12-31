import { test, expect } from '@playwright/test';
import { devLogin } from './helpers';

test.describe('smoke', () => {
  test.describe.configure({ timeout: 60000 });

  async function navigateQuickAction(
    page,
    actionLocator,
    expectedPath: RegExp,
    fallbackPath: string
  ) {
    const href = await actionLocator.getAttribute('href');
    if (href) {
      expect(href).toContain(fallbackPath);
    }
    await actionLocator.evaluate(el => (el as HTMLElement).click());
    await expect(page).toHaveURL(expectedPath, { timeout: 15000 });
  }

  test('home quick actions render and navigate', async ({ page }) => {
    await devLogin(page);

    const createSessionBtn = page.locator('#create-session-btn');
    const joinSessionBtn = page.locator('#join-session-btn');
    const addScenarioBtn = page.locator('#add-scenario-btn');
    const createCharacterBtn = page.locator('#create-character-btn');

    await expect(createSessionBtn).toBeVisible();
    await expect(joinSessionBtn).toBeVisible();
    await expect(addScenarioBtn).toBeVisible();
    await expect(createCharacterBtn).toBeVisible();

    await createCharacterBtn.click();
    await expect(page.locator('#characterCreationModal')).toHaveClass(/show/);
    await page.click('#characterCreationModal .btn-close');
    await expect(page.locator('#characterCreationModal')).not.toHaveClass(/show/);

    await navigateQuickAction(
      page,
      createSessionBtn,
      /\/api\/schedules\/calendar\/view\//,
      '/api/schedules/calendar/view/'
    );
    await expect(page.locator('h1')).toContainText('Chrono Abyss');

    await page.goto('/');

    await navigateQuickAction(
      page,
      joinSessionBtn,
      /\/api\/schedules\/sessions\/view\//,
      '/api/schedules/sessions/view/'
    );
    await expect(page.locator('h1')).toContainText("R'lyeh Log");

    await page.goto('/');

    await navigateQuickAction(
      page,
      addScenarioBtn,
      /\/api\/scenarios\/archive\/view\//,
      '/api/scenarios/archive/view/'
    );
    await expect(page.locator('h1')).toContainText('Mythos Archive');
  });

  test('navbar links open the main views', async ({ page }) => {
    await devLogin(page);

    await Promise.all([
      page.waitForURL(/\/api\/schedules\/calendar\/view\//, { waitUntil: 'domcontentloaded' }),
      page.click('#calendar-link'),
    ]);
    await expect(page.locator('h1')).toContainText('Chrono Abyss');

    await Promise.all([
      page.waitForURL(/\/api\/schedules\/sessions\/view\//, { waitUntil: 'domcontentloaded' }),
      page.click('#sessions-link'),
    ]);
    await expect(page.locator('h1')).toContainText("R'lyeh Log");

    await Promise.all([
      page.waitForURL(/\/api\/scenarios\/archive\/view\//, { waitUntil: 'domcontentloaded' }),
      page.click('#scenarios-link'),
    ]);
    await expect(page.locator('h1')).toContainText('Mythos Archive');

    await Promise.all([
      page.waitForURL(/\/accounts\/groups\/view\//, { waitUntil: 'domcontentloaded' }),
      page.click('#groups-link'),
    ]);
    await expect(page.locator('h1')).toContainText('Cult Circle');

    await page.click('#navbarDropdown');
    await expect(page.locator('#statistics-link')).toBeVisible();
    await Promise.all([
      page.waitForURL(/\/accounts\/statistics\/view\//, { waitUntil: 'domcontentloaded' }),
      page.click('#statistics-link'),
    ]);
    await expect(page.locator('h1')).toContainText('Tindalos Metrics');
  });
});
