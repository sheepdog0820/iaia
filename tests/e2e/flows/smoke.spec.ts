import { test, expect } from '@playwright/test';
import { devLogin } from './helpers';

test.describe('smoke', () => {
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

    await Promise.all([
      page.waitForURL(/\/api\/schedules\/calendar\/view\//),
      createSessionBtn.click(),
    ]);
    await expect(page.locator('h1')).toContainText('Chrono Abyss');

    await page.goto('/');

    await Promise.all([
      page.waitForURL(/\/api\/schedules\/sessions\/view\//),
      joinSessionBtn.click(),
    ]);
    await expect(page.locator('h1')).toContainText("R'lyeh Log");

    await page.goto('/');

    await Promise.all([
      page.waitForURL(/\/api\/scenarios\/archive\/view\//),
      addScenarioBtn.click(),
    ]);
    await expect(page.locator('h1')).toContainText('Mythos Archive');
  });

  test('navbar links open the main views', async ({ page }) => {
    await devLogin(page);

    await Promise.all([
      page.waitForURL(/\/api\/schedules\/calendar\/view\//),
      page.click('#calendar-link'),
    ]);
    await expect(page.locator('h1')).toContainText('Chrono Abyss');

    await Promise.all([
      page.waitForURL(/\/api\/schedules\/sessions\/view\//),
      page.click('#sessions-link'),
    ]);
    await expect(page.locator('h1')).toContainText("R'lyeh Log");

    await Promise.all([
      page.waitForURL(/\/api\/scenarios\/archive\/view\//),
      page.click('#scenarios-link'),
    ]);
    await expect(page.locator('h1')).toContainText('Mythos Archive');

    await Promise.all([
      page.waitForURL(/\/accounts\/groups\/view\//),
      page.click('#groups-link'),
    ]);
    await expect(page.locator('h1')).toContainText('Cult Circle');

    await page.click('#navbarDropdown');
    await expect(page.locator('#statistics-link')).toBeVisible();
    await Promise.all([
      page.waitForURL(/\/accounts\/statistics\/view\//),
      page.click('#statistics-link'),
    ]);
    await expect(page.locator('h1')).toContainText('Tindalos Metrics');
  });
});
