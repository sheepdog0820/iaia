import { test, expect } from '@playwright/test';
import { devLogin, setInputValue } from './helpers';

function formatDateTimeLocal(date: Date): string {
  const pad = (value: number) => value.toString().padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

test.describe('session templates', () => {
  test('save a template and create a session from it', async ({ page }) => {
    await devLogin(page);
    await page.waitForFunction(() => (window as any).axios?.post);

    const groupName = `E2E Template Group ${Date.now()}`;
    const group = await page.evaluate(async (name: string) => {
      const response = await (window as any).axios.post('/api/accounts/groups/', {
        name,
        visibility: 'private',
      });
      return response.data;
    }, groupName);

    await page.goto('/api/schedules/session-templates/view/');
    await expect(page.locator('#createTemplateBtn')).toBeVisible();

    await page.click('#createTemplateBtn');
    await expect(page.locator('#sessionTemplateModal')).toHaveClass(/show/);

    const templateName = `E2E Session Template ${Date.now()}`;
    await setInputValue(page, '#templateName', templateName);
    await page.waitForFunction(groupId => {
      const select = document.querySelector('#templateGroup') as HTMLSelectElement | null;
      if (!select) return false;
      return Array.from(select.options).some(option => option.value === groupId);
    }, String(group.id));
    await page.selectOption('#templateGroup', String(group.id));
    await setInputValue(page, '#templateDuration', '0130');
    await setInputValue(page, '#templateLocation', 'Online');
    await setInputValue(page, '#templateTitle', 'Template Session Title');
    await setInputValue(page, '#templateDescription', 'Created from Playwright template flow.');

    await page.check('#copyHandoutsToSession');
    await page.click('#addTemplateHandoutBtn');
    await setInputValue(page, '[data-field="title"][data-index="0"]', 'HO1');
    await page.selectOption('[data-field="handout_number"][data-index="0"]', '1');
    await page.selectOption('[data-field="assigned_player_slot"][data-index="0"]', '1');
    await setInputValue(page, '[data-field="content"][data-index="0"]', 'Secret handout body');

    const [createTemplateResponse] = await Promise.all([
      page.waitForResponse(response =>
        response.url().includes('/api/schedules/session-templates/') &&
        response.request().method() === 'POST' &&
        response.status() === 201
      ),
      page.click('#saveTemplateBtn'),
    ]);

    const savedTemplate = await createTemplateResponse.json();
    expect(savedTemplate.name).toBe(templateName);
    expect(savedTemplate.duration_hhmm).toBe('0130');
    expect(savedTemplate.handout_templates).toHaveLength(1);

    await page.goto('/api/schedules/calendar/view/');
    page.on('dialog', async dialog => {
      await dialog.accept();
    });

    await page.click('button[data-bs-target="#newSessionModal"]');
    await expect(page.locator('#newSessionModal')).toHaveClass(/show/);
    await page.waitForFunction(templateId => {
      const select = document.querySelector('#sessionTemplate') as HTMLSelectElement | null;
      if (!select) return false;
      return Array.from(select.options).some(option => option.value === templateId);
    }, String(savedTemplate.id));

    await page.selectOption('#sessionTemplate', String(savedTemplate.id));
    await expect(page.locator('#sessionTitle')).toHaveValue('Template Session Title');
    await expect(page.locator('#sessionDuration')).toHaveValue('90');
    await expect(page.locator('#sessionLocation')).toHaveValue('Online');
    await expect(page.locator('#sessionGroup')).toHaveValue(String(group.id));

    const sessionDate = new Date(Date.now() + 24 * 60 * 60 * 1000);
    await setInputValue(page, '#sessionDate', formatDateTimeLocal(sessionDate));

    const [createSessionResponse] = await Promise.all([
      page.waitForResponse(response =>
        response.url().endsWith('/api/schedules/sessions/') &&
        response.request().method() === 'POST' &&
        response.status() === 201
      ),
      page.click('#saveSessionBtn'),
    ]);

    const session = await createSessionResponse.json();
    expect(session.title).toBe('Template Session Title');

    const sessionDetailResponse = await page.request.get(`/api/schedules/sessions/${session.id}/`);
    expect(sessionDetailResponse.ok()).toBeTruthy();
    const sessionDetail = await sessionDetailResponse.json();
    expect(sessionDetail.handouts_detail).toHaveLength(1);
    expect(sessionDetail.handouts_detail[0].title).toBe('HO1');
    expect(sessionDetail.handouts_detail[0].assigned_player_slot).toBe(1);
  });
});
