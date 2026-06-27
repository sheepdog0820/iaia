import { test, expect } from '@playwright/test';
import { devLogin, setInputValue } from './helpers';

test.describe('scenarios', () => {
  test.describe.configure({ timeout: 60000 });

  test('create a scenario from the archive view', async ({ page }) => {
    await devLogin(page);
    await page.goto('/api/scenarios/archive/view/?show_test_data=1');

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
    await page.goto('/api/scenarios/archive/view/?show_test_data=1');

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

  test('scenario supports structured skills and multiple handouts', async ({ page }) => {
    await devLogin(page);
    await page.waitForFunction(() => (window as any).axios?.post);

    const scenarioTitle = `E2E Scenario Structured ${Date.now()}`;
    const scenario = await page.evaluate(async ({ scenarioTitle }) => {
      const response = await (window as any).axios.post('/api/scenarios/scenarios/', {
        title: scenarioTitle,
        game_system: 'coc',
        author: 'Playwright',
        summary: 'Structured scenario data.',
        recommended_skills: 'Spot Hidden',
        recommended_skill_items: [
          { name: 'Spot Hidden', level: 'recommended', description: 'Find clues.', order: 1 },
          { name: 'Library Use', level: 'optional', description: 'Read documents.', order: 2 },
        ],
        handout_templates: [
          {
            code: 'HO1',
            name: 'Archivist',
            title: 'Archivist',
            content: 'You know the archive.',
            recommended_skills: 'Library Use',
            is_secret: true,
            handout_number: 1,
            assigned_player_slot: 1,
            order: 1,
            recommended_skill_items: [
              { name: 'Library Use', level: 'recommended', description: 'Read documents.', order: 1 },
            ],
          },
          {
            code: 'HO2',
            name: 'Witness',
            title: 'Witness',
            content: 'You saw the sign.',
            recommended_skills: 'Spot Hidden',
            is_secret: true,
            handout_number: 2,
            assigned_player_slot: 2,
            order: 2,
            recommended_skill_items: [
              { name: 'Spot Hidden', level: 'recommended', description: 'Find clues.', order: 1 },
            ],
          },
        ],
      });
      return response.data;
    }, { scenarioTitle });

    await page.goto('/api/scenarios/archive/view/?show_test_data=1');
    await expect(page.locator('.scenario-card', { hasText: scenarioTitle })).toBeVisible();

    const detail = await page.evaluate(async scenarioId => {
      const response = await (window as any).axios.get(`/api/scenarios/scenarios/${scenarioId}/`);
      return response.data;
    }, scenario.id);

    expect(detail.recommended_skill_items.map((skill: any) => skill.name)).toEqual([
      'Spot Hidden',
      'Library Use',
    ]);
    expect(detail.handout_templates.map((handout: any) => handout.code)).toEqual(['HO1', 'HO2']);
    expect(detail.handout_templates[0].recommended_skill_items[0].name).toBe('Library Use');
  });
});
