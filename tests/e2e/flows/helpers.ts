import { expect, Page } from '@playwright/test';

export async function devLogin(
  page: Page,
  username = 'admin',
  redirectPath = '/'
): Promise<void> {
  const nextPath = redirectPath || '/';
  const nextParam = nextPath ? `?next=${encodeURIComponent(nextPath)}` : '';
  const targetUrl = `/accounts/dev-login/${nextParam}`;
  try {
    await page.goto(targetUrl, { waitUntil: 'commit', timeout: 30000 });
  } catch (error) {
    await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
  }
  await page.waitForSelector('.user-card');

  const csrfToken = await page.getAttribute('input[name="csrfmiddlewaretoken"]', 'value');
  if (!csrfToken) {
    throw new Error('dev login csrf token not found');
  }

  const response = await page.request.post('/accounts/dev-login/', {
    form: {
      username,
      csrfmiddlewaretoken: csrfToken,
      next: nextPath,
    },
    headers: {
      Referer: new URL(targetUrl, page.url()).toString(),
    },
    timeout: 15000,
  });
  if (response.status() >= 400) {
    throw new Error(`dev login failed with status ${response.status()}`);
  }

  if (redirectPath) {
    const currentPath = new URL(page.url()).pathname;
    if (currentPath !== redirectPath) {
      await page.goto(redirectPath, { waitUntil: 'domcontentloaded', timeout: 30000 });
    }
  }

  if (redirectPath === '/') {
    await expect(page.locator('.welcome-section')).toBeVisible();
  }
  await page.waitForLoadState('domcontentloaded');
}

export async function setInputValue(
  page: Page,
  selector: string,
  value: string
): Promise<void> {
  await page.evaluate(({ selector, value }) => {
    const element = document.querySelector(selector) as
      | HTMLInputElement
      | HTMLTextAreaElement
      | null;
    if (!element) {
      throw new Error(`Missing input: ${selector}`);
    }
    element.value = value;
    element.dispatchEvent(new Event('input', { bubbles: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));
  }, { selector, value });
}
