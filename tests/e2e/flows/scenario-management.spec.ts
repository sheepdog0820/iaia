import { test, expect } from '@playwright/test';
import { devLogin } from './helpers';

test.describe('scenarios', () => {
  test('create a scenario from the archive view', async ({ page }) => {
    await devLogin(page);
    await page.goto('/api/scenarios/archive/view/');

    await page.click('button[data-bs-target="#addScenarioModal"]');
    await expect(page.locator('#addScenarioModal')).toBeVisible();

    const scenarioTitle = `E2E Scenario ${Date.now()}`;

    await page.fill('#scenarioTitle', scenarioTitle);
    await page.selectOption('#scenarioSystem', 'coc');
    await page.fill('#scenarioAuthor', 'Playwright');
    await page.fill('#scenarioSummary', 'Smoke scenario created by Playwright tests.');

    page.once('dialog', async dialog => {
      await dialog.accept();
    });

    await Promise.all([
      page.waitForResponse(response =>
        response.url().includes('/api/scenarios/scenarios/') &&
        response.request().method() === 'POST'
      ),
      page.click('#saveScenarioBtn'),
    ]);

    const scenarioCard = page.locator('.scenario-card', { hasText: scenarioTitle });
    await expect(scenarioCard).toBeVisible();
  });
});
