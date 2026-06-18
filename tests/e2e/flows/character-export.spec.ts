import { expect, test } from '@playwright/test';
import { devLogin } from './helpers';

test.describe('character export release flows', () => {
  test('6th edition character can be exported as CCFOLIA JSON', async ({ page }) => {
    await devLogin(page);
    await page.waitForFunction(() => (window as any).axios?.post);

    const timestamp = Date.now();
    const character = await page.evaluate(async (suffix: number) => {
      const axios = (window as any).axios;
      const characterResponse = await axios.post('/api/accounts/character-sheets/create_6th_edition/', {
        name: `CCFOLIA E2E Investigator ${suffix}`,
        player_name: 'admin',
        age: 34,
        gender: 'unknown',
        occupation: 'Investigator',
        birthplace: 'Arkham',
        residence: 'Tokyo',
        str_value: 13,
        con_value: 12,
        pow_value: 14,
        dex_value: 11,
        app_value: 10,
        siz_value: 15,
        int_value: 16,
        edu_value: 17,
        notes: 'CCFOLIA export release check.',
      });

      await axios.post(`/api/accounts/character-sheets/${characterResponse.data.id}/skills/`, {
        skill_name: 'Spot Hidden',
        base_value: 25,
        occupation_points: 40,
        interest_points: 10,
        other_points: 0,
      });

      return characterResponse.data;
    }, timestamp);

    const exportResponse = await page.request.get(`/api/accounts/character-sheets/${character.id}/ccfolia_json/`);
    expect(exportResponse.ok()).toBeTruthy();

    const payload = await exportResponse.json();
    expect(payload.kind).toBe('character');
    expect(payload.data.name).toBe(character.name);
    expect(payload.data.params).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ label: 'STR', value: '13' }),
        expect.objectContaining({ label: 'POW', value: '14' }),
      ])
    );
    expect(payload.data.status).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ label: 'HP' }),
        expect.objectContaining({ label: 'MP', max: 14 }),
        expect.objectContaining({ label: 'SAN' }),
      ])
    );
    expect(payload.data.commands).toContain('Spot Hidden');
  });
});
