import { test, expect } from '@playwright/test';
import { devLogin } from './helpers';

test.describe('character create scenario select modal', () => {
  test('opens and lists participating scenarios', async ({ page }) => {
    await devLogin(page);
    await page.waitForFunction(() => (window as any).axios?.post);

    const timestamp = Date.now();
    const scenarioTitle = `E2E Scenario Select ${timestamp}`;
    const groupName = `E2E Group Select ${timestamp}`;

    const { scenario, group } = await page.evaluate(async ({ scenarioTitle, groupName }) => {
      const axios = (window as any).axios;

      const scenarioResp = await axios.post('/api/scenarios/scenarios/', {
        title: scenarioTitle,
        game_system: 'coc',
        author: 'Playwright',
        summary: 'Scenario select modal test scenario.',
        recommended_skills: 'Spot Hidden, Listen',
      });

      const groupResp = await axios.post('/api/accounts/groups/', {
        name: groupName,
        visibility: 'private',
      });

      return { scenario: scenarioResp.data, group: groupResp.data };
    }, { scenarioTitle, groupName });

    // Create a planned session within the next 365 days so that participating-scenarios endpoint returns it.
    const sessionDate = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();
    await page.evaluate(async ({ scenarioId, groupId, sessionDate }) => {
      const axios = (window as any).axios;
      await axios.post('/api/schedules/sessions/', {
        title: `E2E Session Select ${Date.now()}`,
        description: 'Scenario select modal test session.',
        date: sessionDate,
        location: 'Playwright',
        status: 'planned',
        visibility: 'private',
        duration_minutes: 60,
        group: groupId,
        scenario: scenarioId,
      });
    }, { scenarioId: scenario.id, groupId: group.id, sessionDate });

    await page.goto('/accounts/character/create/6th/');

    await page.click('#skills-tab');
    await expect(page.locator('#selectScenarioRecommended')).toBeVisible();
    await page.click('#selectScenarioRecommended');

    await expect(page.locator('#scenarioSelectModal.show')).toBeVisible();
    await expect(page.locator('#scenarioSelectList', { hasText: scenarioTitle })).toBeVisible();

    // Debug artifact: if modal layout breaks, this makes it easy to inspect locally.
    await page.locator('#scenarioSelectModal .modal-dialog').screenshot({
      path: 'debug_images/scenario_select_modal.png',
    });
  });
});
