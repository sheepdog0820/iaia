import { expect, type Page } from '@playwright/test';

export async function openSignup(page: Page) {
  // The signup handlers initialize on DOMContentLoaded. Image load is not
  // the contract for starting registration; the real form must be usable.
  const response = await page.goto('/signup/', { waitUntil: 'domcontentloaded' });
  expect(response).not.toBeNull();
  expect(response!.status()).toBe(200);
  await expect(page.locator('#email-signup-form')).toBeVisible();
  await expect(page.locator('#id_username')).toBeEditable();
  await expect(page.locator('#signup-btn')).toBeEnabled();
}
