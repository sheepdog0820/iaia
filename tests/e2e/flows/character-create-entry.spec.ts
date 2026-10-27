'use strict';

import { expect, test } from '@playwright/test';
import { devLogin } from './helpers';

for (const width of [1280, 390]) {
  test(`unversioned character creation offers both editions at ${width}px`, async ({ page, baseURL }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.route('**/*', route => {
      const origin = new URL(route.request().url()).origin;
      return origin === new URL(baseURL!).origin ? route.continue() : route.abort();
    });
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(error.message));
    const entryPath = '/accounts/character/create/';
    const anonymous = await page.request.get(entryPath, { maxRedirects: 0 });
    expect(anonymous.status()).toBe(302);
    const login = new URL(anonymous.headers().location, baseURL);
    expect(login.pathname).toBe('/accounts/login/');
    expect(login.searchParams.get('next')).toBe(entryPath);

    await devLogin(page, 'investigator1', entryPath);
    const before = await page.request.get('/api/accounts/character-sheets/');
    expect(before.status()).toBe(200);
    const beforeData = await before.json();
    await expect(page.getByRole('heading', { name: 'キャラクターシート作成', exact: true })).toBeVisible();
    const sixth = page.locator('#create-entry-6th');
    const seventh = page.locator('#create-entry-7th');
    await expect(sixth).toHaveText('6版キャラクター作成');
    await expect(seventh).toHaveText('7版キャラクター作成');
    await expect(sixth).toBeVisible();
    await expect(seventh).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: test.info().outputPath('creation-entry.png'), fullPage: true });
    await page.reload({ waitUntil: 'domcontentloaded' });
    await expect(sixth).toBeVisible();
    await sixth.focus();
    await expect(sixth).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/\/accounts\/character\/create\/6th\/$/);
    await expect(page.locator('#character-name')).toBeVisible();
    await page.goBack({ waitUntil: 'domcontentloaded' });
    await expect(sixth).toBeVisible();
    await seventh.click();
    await expect(page).toHaveURL(/\/accounts\/character\/create\/7th\/$/);
    await expect(page.locator('#character-name')).toBeVisible();
    await page.goBack({ waitUntil: 'domcontentloaded' });
    await page.locator('#create-entry-list').click();
    await expect(page).toHaveURL(/\/accounts\/character\/list\/$/);
    await expect(page.getByRole('heading', { name: 'キャラクターシート一覧' })).toBeVisible();
    const after = await page.request.get('/api/accounts/character-sheets/');
    expect(after.status()).toBe(200);
    expect(await after.json()).toEqual(beforeData);
    expect(errors).toEqual([]);
  });
}
