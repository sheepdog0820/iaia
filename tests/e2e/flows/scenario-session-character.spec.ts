import { test, expect } from '@playwright/test';
import { devLogin } from './helpers';

test.describe('scenario-session flow', () => {
  test('scenario detail to session and character creation', async ({ page }) => {
    await devLogin(page);
    await page.waitForFunction(() => (window as any).axios?.post);

    const timestamp = Date.now();
    const scenarioTitle = `E2E Scenario Flow ${timestamp}`;
    const groupName = `E2E Group Flow ${timestamp}`;

    const { scenario, group } = await page.evaluate(async ({ scenarioTitle, groupName }) => {
      const scenarioResp = await (window as any).axios.post('/api/scenarios/scenarios/', {
        title: scenarioTitle,
        game_system: 'coc',
        author: 'Playwright',
        summary: 'Flow test scenario.',
        recommended_skills: 'Spot Hidden, Listen'
      });
      const groupResp = await (window as any).axios.post('/api/accounts/groups/', {
        name: groupName,
        visibility: 'private'
      });
      return { scenario: scenarioResp.data, group: groupResp.data };
    }, { scenarioTitle, groupName });

    await page.goto('/api/scenarios/archive/view/');
    const scenarioCard = page.locator('.scenario-card', { hasText: scenarioTitle }).first();
    await expect(scenarioCard).toBeVisible();
    await scenarioCard.click();
    await expect(page.locator('#scenarioDetailModal.show')).toBeVisible();

    const planButton = page
      .locator('#scenarioDetailModal button[onclick^="createSessionFromScenario"]')
      .first();
    await Promise.all([
      page.waitForURL('**/api/schedules/calendar/view/**'),
      planButton.click()
    ]);

    await expect(page.locator('#newSessionModal.show')).toBeVisible();
    await expect(page.locator('#sessionScenarioId')).toHaveValue(String(scenario.id));
    await expect(page.locator('#sessionScenarioTitle')).toHaveValue(scenarioTitle);

    await page.waitForFunction(groupId => {
      const select = document.querySelector('#sessionGroup') as HTMLSelectElement | null;
      if (!select) return false;
      return Array.from(select.options).some(option => option.value === groupId);
    }, String(group.id));

    await page.fill('#sessionTitle', `Flow Session ${timestamp}`);
    await page.fill('#sessionDate', '2030-01-01T19:00');
    await page.selectOption('#sessionGroup', String(group.id));
    await page.selectOption('#sessionCocEdition', '7th');
    await page.fill('#sessionDescription', 'Scenario linked session.');

    page.once('dialog', async dialog => {
      await dialog.accept();
    });

    const [sessionResp] = await Promise.all([
      page.waitForResponse(resp =>
        resp.url().includes('/api/schedules/sessions/') &&
        resp.request().method() === 'POST'
      ),
      page.click('#saveSessionBtn')
    ]);

    expect(sessionResp.ok()).toBeTruthy();
    const session = await sessionResp.json();
    expect(session.scenario).toBe(scenario.id);

    await page.goto(`/api/schedules/sessions/${session.id}/detail/`);
    await expect(page.locator(`text=${scenarioTitle}`)).toBeVisible();

    const nextContextResponsePromise = page.waitForResponse(resp => {
      if (resp.request().method() !== 'GET') return false;
      const url = resp.url();
      return (
        url.includes('/api/schedules/sessions/next-context/') &&
        url.includes(`session_id=${session.id}`)
      );
    });

    await Promise.all([
      page.waitForURL('**/accounts/character/create/7th/**'),
      page.click('#createCharacterFromScenario')
    ]);
    await expect(page).toHaveURL(new RegExp(`scenario_id=${scenario.id}`));
    await expect(page.locator('#recommendedSkillInput')).toBeAttached();

    const nextContextResponse = await nextContextResponsePromise;
    expect(nextContextResponse.ok()).toBeTruthy();
    const nextContext = await nextContextResponse.json();
    expect(nextContext?.scenario?.id).toBe(scenario.id);
    expect(nextContext?.scenario?.recommended_skills).toContain('Spot Hidden');
  });

  test('scenario detail to session and character creation (CoC 6th)', async ({ page }) => {
    await devLogin(page);
    await page.waitForFunction(() => (window as any).axios?.post);

    const timestamp = Date.now();
    const scenarioTitle = `E2E Scenario Flow 6th ${timestamp}`;
    const groupName = `E2E Group Flow 6th ${timestamp}`;

    const { scenario, group } = await page.evaluate(async ({ scenarioTitle, groupName }) => {
      const scenarioResp = await (window as any).axios.post('/api/scenarios/scenarios/', {
        title: scenarioTitle,
        game_system: 'coc',
        author: 'Playwright',
        summary: 'Flow test scenario.',
        recommended_skills: 'Spot Hidden, Listen'
      });
      const groupResp = await (window as any).axios.post('/api/accounts/groups/', {
        name: groupName,
        visibility: 'private'
      });
      return { scenario: scenarioResp.data, group: groupResp.data };
    }, { scenarioTitle, groupName });

    await page.goto('/api/scenarios/archive/view/');
    const scenarioCard = page.locator('.scenario-card', { hasText: scenarioTitle }).first();
    await expect(scenarioCard).toBeVisible();
    await scenarioCard.click();
    await expect(page.locator('#scenarioDetailModal.show')).toBeVisible();

    const planButton = page
      .locator('#scenarioDetailModal button[onclick^="createSessionFromScenario"]')
      .first();
    await Promise.all([
      page.waitForURL('**/api/schedules/calendar/view/**'),
      planButton.click()
    ]);

    await expect(page.locator('#newSessionModal.show')).toBeVisible();
    await expect(page.locator('#sessionScenarioId')).toHaveValue(String(scenario.id));
    await expect(page.locator('#sessionScenarioTitle')).toHaveValue(scenarioTitle);

    await page.waitForFunction(groupId => {
      const select = document.querySelector('#sessionGroup') as HTMLSelectElement | null;
      if (!select) return false;
      return Array.from(select.options).some(option => option.value === groupId);
    }, String(group.id));

    await page.fill('#sessionTitle', `Flow Session 6th ${timestamp}`);
    await page.fill('#sessionDate', '2030-01-01T19:00');
    await page.selectOption('#sessionGroup', String(group.id));
    await page.selectOption('#sessionCocEdition', '6th');
    await page.fill('#sessionDescription', 'Scenario linked session.');

    page.once('dialog', async dialog => {
      await dialog.accept();
    });

    const [sessionResp] = await Promise.all([
      page.waitForResponse(resp =>
        resp.url().includes('/api/schedules/sessions/') &&
        resp.request().method() === 'POST'
      ),
      page.click('#saveSessionBtn')
    ]);

    expect(sessionResp.ok()).toBeTruthy();
    const session = await sessionResp.json();
    expect(session.scenario).toBe(scenario.id);

    await page.goto(`/api/schedules/sessions/${session.id}/detail/`);
    await expect(page.locator(`text=${scenarioTitle}`)).toBeVisible();

    const nextContextResponsePromise = page.waitForResponse(resp => {
      if (resp.request().method() !== 'GET') return false;
      const url = resp.url();
      return (
        url.includes('/api/schedules/sessions/next-context/') &&
        url.includes(`session_id=${session.id}`)
      );
    });

    await Promise.all([
      page.waitForURL('**/accounts/character/create/6th/**'),
      page.click('#createCharacterFromScenario')
    ]);
    await expect(page).toHaveURL(new RegExp(`scenario_id=${scenario.id}`));
    await expect(page.locator('#recommendedSkillInput')).toBeAttached();

    const nextContextResponse = await nextContextResponsePromise;
    expect(nextContextResponse.ok()).toBeTruthy();
    const nextContext = await nextContextResponse.json();
    expect(nextContext?.scenario?.id).toBe(scenario.id);
    expect(nextContext?.scenario?.recommended_skills).toContain('Spot Hidden');
  });
});
