import { expect, test } from '@playwright/test';
import { devLogin } from './helpers';

for (const choice of ['occurrence', 'character']) {
  test(`session ${choice} choices display names as text`, async ({ page }) => {
    await devLogin(page);
    const markup = '<img src=x onerror="window.__sessionChoiceXss=1">';
    const created = await page.evaluate(async () => {
      const client = (window as any).axios;
      const group = (await client.post('/api/accounts/groups/', { name: '日程選択の検証', visibility: 'private' })).data;
      const session = (await client.post('/api/schedules/sessions/', { title: '参加者選択の検証', group: group.id,
        visibility: 'group', as_gm: true, date: '2030-01-01T19:00:00Z' })).data;
      return { groupId: group.id, sessionId: session.id };
    });
    await page.route(`**/api/accounts/groups/${created.groupId}/members/`, route => route.fulfill({ json: [
      { user: 1, user_detail: { nickname: markup, username: 'member' } },
    ] }));
    await page.route('**/api/accounts/character-sheets/', route => route.fulfill({ json: [{ id: 1, name: markup }] }));
    await page.goto(`/api/schedules/sessions/${created.sessionId}/detail/`);
    if (choice === 'occurrence') {
      await page.locator('button[onclick="openOccurrenceModal(null)"]').click();
      await expect(page.locator('#occurrenceModal')).toBeVisible();
      await expect(page.locator('#occurrenceParticipants label span')).toHaveText(markup);
      await expect(page.locator('#occurrenceParticipants img')).toHaveCount(0);
      const checkbox = page.locator('#occurrenceParticipants input[value="1"]');
      await checkbox.check();
      await expect(checkbox).toBeChecked();
    } else {
      await expect(page.locator('#edit_character_sheet_id option[value="1"]')).toHaveText(markup);
    }
    expect(await page.evaluate(() => (window as any).__sessionChoiceXss)).toBeUndefined();
  });
}
