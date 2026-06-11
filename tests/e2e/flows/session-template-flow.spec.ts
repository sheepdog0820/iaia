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
    await page.waitForFunction(groupId => {
      const select = document.querySelector('#sessionGroup') as HTMLSelectElement | null;
      return select?.value === groupId;
    }, String(group.id));
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

  test('save current calendar inputs as a template without leaving the modal', async ({ page }) => {
    await devLogin(page);
    await page.waitForFunction(() => (window as any).axios?.post);

    const groupName = `E2E Calendar Template Group ${Date.now()}`;
    const group = await page.evaluate(async (name: string) => {
      const response = await (window as any).axios.post('/api/accounts/groups/', {
        name,
        visibility: 'private',
      });
      return response.data;
    }, groupName);

    await page.goto('/api/schedules/calendar/view/');
    await page.click('button[data-bs-target="#newSessionModal"]');
    await expect(page.locator('#newSessionModal')).toHaveClass(/show/);

    await setInputValue(page, '#sessionTitle', 'Calendar Prefill Session');
    await setInputValue(page, '#sessionDuration', '150');
    await setInputValue(page, '#sessionLocation', 'Discord');
    await setInputValue(page, '#sessionDescription', 'Prefilled from calendar modal.');
    await setInputValue(page, '#sessionYoutube', 'https://youtube.com/watch?v=dQw4w9WgXcQ');
    await page.selectOption('#sessionVisibility', 'private');
    await page.selectOption('#sessionCocEdition', '7th');
    await page.waitForFunction(groupId => {
      const select = document.querySelector('#sessionGroup') as HTMLSelectElement | null;
      if (!select) return false;
      return Array.from(select.options).some(option => option.value === groupId);
    }, String(group.id));
    await page.selectOption('#sessionGroup', String(group.id));

    await page.click('#saveTemplateFromSession');
    await expect(page.locator('#saveSessionTemplateModal')).toHaveClass(/show/);
    await expect(page.locator('#quickTemplateSummary')).toContainText('Calendar Prefill Session');
    await expect(page.locator('#quickTemplateSummary')).toContainText('0230');
    await expect(page.locator('#quickTemplateSummary')).toContainText('Discord');

    const templateName = `Calendar Prefill Template ${Date.now()}`;
    await setInputValue(page, '#quickTemplateName', templateName);

    const [createTemplateResponse] = await Promise.all([
      page.waitForResponse(response =>
        response.url().includes('/api/schedules/session-templates/') &&
        response.request().method() === 'POST' &&
        response.status() === 201
      ),
      page.click('#confirmSaveTemplateBtn'),
    ]);

    const savedTemplate = await createTemplateResponse.json();
    expect(savedTemplate.name).toBe(templateName);
    expect(savedTemplate.title).toBe('Calendar Prefill Session');
    expect(savedTemplate.duration_hhmm).toBe('0230');
    expect(savedTemplate.location).toBe('Discord');
    expect(savedTemplate.group).toBe(group.id);
    await expect(page.locator('#sessionTemplate')).toHaveValue(String(savedTemplate.id));
  });

  test('open detailed template editor from calendar with current values', async ({ page, context }) => {
    await devLogin(page);
    await page.waitForFunction(() => (window as any).axios?.post);

    const groupName = `E2E Detailed Template Group ${Date.now()}`;
    const group = await page.evaluate(async (name: string) => {
      const response = await (window as any).axios.post('/api/accounts/groups/', {
        name,
        visibility: 'private',
      });
      return response.data;
    }, groupName);

    await page.goto('/api/schedules/calendar/view/');
    await page.click('button[data-bs-target="#newSessionModal"]');
    await expect(page.locator('#newSessionModal')).toHaveClass(/show/);

    await setInputValue(page, '#sessionTitle', 'Detailed Editor Session');
    await setInputValue(page, '#sessionDuration', '150');
    await setInputValue(page, '#sessionLocation', 'Discord');
    await setInputValue(page, '#sessionDescription', 'Prefilled from calendar modal.');
    await setInputValue(page, '#sessionYoutube', 'https://youtube.com/watch?v=dQw4w9WgXcQ');
    await page.selectOption('#sessionVisibility', 'private');
    await page.selectOption('#sessionCocEdition', '7th');
    await page.waitForFunction(groupId => {
      const select = document.querySelector('#sessionGroup') as HTMLSelectElement | null;
      if (!select) return false;
      return Array.from(select.options).some(option => option.value === groupId);
    }, String(group.id));
    await page.selectOption('#sessionGroup', String(group.id));

    await page.click('#saveTemplateFromSession');
    await expect(page.locator('#saveSessionTemplateModal')).toHaveClass(/show/);

    const templatePagePromise = context.waitForEvent('page');
    await page.click('#openTemplateEditorFromSession');
    const templatePage = await templatePagePromise;

    await templatePage.waitForLoadState('domcontentloaded');
    await expect(templatePage.locator('#createTemplateBtn')).toBeVisible();
    await expect(templatePage.locator('#sessionTemplateModal')).toHaveClass(/show/);

    await expect(templatePage.locator('#templateTitle')).toHaveValue('Detailed Editor Session');
    await expect(templatePage.locator('#templateDuration')).toHaveValue('0230');
    await expect(templatePage.locator('#templateLocation')).toHaveValue('Discord');
    await expect(templatePage.locator('#templateDescription')).toHaveValue('Prefilled from calendar modal.');
    await expect(templatePage.locator('#templateYoutube')).toHaveValue('https://youtube.com/watch?v=dQw4w9WgXcQ');
    await expect(templatePage.locator('#templateVisibility')).toHaveValue('private');
    await expect(templatePage.locator('#templateCocEdition')).toHaveValue('7th');
    await expect(templatePage.locator('#templateGroup')).toHaveValue(String(group.id));
  });

  test('sessions web create button routes to the calendar creation UI', async ({ page }) => {
    await devLogin(page);
    await page.goto('/api/schedules/sessions/web/');

    await page.locator('a[href="/api/schedules/calendar/view/?open_create=1"]').first().click();
    await page.waitForURL('**/api/schedules/calendar/view/?open_create=1');
    await expect(page.locator('#newSessionModal')).toHaveClass(/show/);
    await expect(page.locator('#saveTemplateFromSession')).toContainText('テンプレート登録');
  });

  test('session detail edit modal uses the shared session form layout', async ({ page }) => {
    await devLogin(page);
    await page.waitForFunction(() => (window as any).axios?.post);

    const groupName = `E2E Detail Shared Group ${Date.now()}`;
    const group = await page.evaluate(async (name: string) => {
      const response = await (window as any).axios.post('/api/accounts/groups/', {
        name,
        visibility: 'private',
      });
      return response.data;
    }, groupName);

    const session = await page.evaluate(async ({ groupId }) => {
      const response = await (window as any).axios.post('/api/schedules/sessions/', {
        title: 'Shared Detail Session',
        group: groupId,
        visibility: 'group',
        coc_edition: '7th',
        duration_minutes: 180,
        location: 'Shared Room',
        description: 'Shared edit form',
      });
      return response.data;
    }, { groupId: group.id });

    await page.goto(`/api/schedules/sessions/${session.id}/detail/`);
    await page.click('[data-bs-target="#editSessionModal"]');
    await expect(page.locator('#editSessionModal')).toHaveClass(/show/);

    await expect(page.locator('#editSessionTitle')).toHaveValue('Shared Detail Session');
    await expect(page.locator('#editSessionGroupLabel')).toHaveValue(group.name);
    await expect(page.locator('#editSessionCocEdition')).toHaveValue('7th');
    await expect(page.locator('#editSessionVisibility')).toHaveValue('group');
  });
});
