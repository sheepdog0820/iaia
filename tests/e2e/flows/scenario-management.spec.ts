import { test, expect } from '@playwright/test';
import { devLogin, setInputValue } from './helpers';

test.describe('scenarios', () => {
  test.describe.configure({ timeout: 60000 });

  test('create a scenario from the archive view', async ({ page }) => {
    await devLogin(page);
    await page.goto('/api/scenarios/archive/view/');

    await page.click('button[data-bs-target="#addScenarioModal"]');
    await expect(page.locator('#addScenarioModal')).toBeVisible();

    const scenarioTitle = `E2E Scenario ${Date.now()}`;

    await setInputValue(page, '#scenarioTitle', scenarioTitle);
    await page.selectOption('#scenarioSystem', 'coc');
    await setInputValue(page, '#scenarioAuthor', 'Playwright');
    await setInputValue(page, '#scenarioSummary', 'Smoke scenario created by Playwright tests.');

    await Promise.all([
      page.waitForResponse(response =>
        response.url().includes('/api/scenarios/scenarios/') &&
        response.request().method() === 'POST',
      { timeout: 60000 }),
      page.click('#saveScenarioBtn'),
    ]);

    const scenarioCard = page.locator('.scenario-card', { hasText: scenarioTitle });
    await expect(scenarioCard).toBeVisible();
  });

  test('recommended skills empty shows no warning', async ({ page }) => {
    await devLogin(page);
    await page.goto('/api/scenarios/archive/view/');

    await page.click('button[data-bs-target="#addScenarioModal"]');
    await expect(page.locator('#addScenarioModal')).toBeVisible();

    await setInputValue(page, '#scenarioTitle', `E2E Scenario Empty Skills ${Date.now()}`);
    await page.selectOption('#scenarioSystem', 'coc');
    await setInputValue(page, '#scenarioAuthor', 'Playwright');
    await setInputValue(page, '#scenarioSummary', 'Scenario without recommended skills.');

    await setInputValue(page, '#scenarioRecommendedSkills', '');
    await page.locator('#scenarioRecommendedSkills').blur();

    await expect(page.locator('#scenarioRecommendedSkillsWarning')).toBeHidden();
  });
});
