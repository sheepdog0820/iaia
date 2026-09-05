import { expect, test } from '@playwright/test';
import { devLogin } from './helpers';

test('shared alerts display API error and success messages as text and can close', async ({ page }) => {
  await devLogin(page);
  const markup = '<img src=x onerror="window.__alertXss=1">';
  for (const method of ['success', 'error', 'api-detail', 'api-error']) {
    await page.evaluate(({ text, method }) => {
      const ui = (window as any).ARKHAM;
      if (method === 'success') ui.showSuccess(text);
      else if (method === 'error') ui.showError(text);
      else ui.handleError({ response: { data: method === 'api-detail' ? { detail: text } : { error: text } } });
    }, { text: markup, method });
    const alert = page.locator('.alert.position-fixed');
    await expect(alert).toContainText(markup);
    await expect(alert.locator('img')).toHaveCount(0);
    expect(await page.evaluate(() => (window as any).__alertXss)).toBeUndefined();
    await alert.getByRole('button', { name: '閉じる', exact: true }).click();
    await expect(alert).toHaveCount(0);
  }
});
