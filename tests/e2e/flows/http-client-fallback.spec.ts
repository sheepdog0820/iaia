import { expect, test } from '@playwright/test';

for (const [clientMode, mode] of [
  ['bundled', 'object'], ['bundled', 'searchParams'],
  ['fallback', 'object'], ['fallback', 'searchParams'],
]) {
  test(`HTTP ${clientMode} preserves query values (${mode})`, async ({ page }) => {
    await page.route('https://**/*', route => route.abort());
    if (clientMode === 'fallback') {
      await page.route('**/static/vendor/axios/**', route => route.abort());
    }
    await page.route('**/http-query-probe?**', route => route.fulfill({
      contentType: 'application/json', body: JSON.stringify({ url: route.request().url() }),
    }));
    await page.goto('/signup/');
    expect(await page.evaluate(() => (window as any).axios.VERSION))
      .toBe(clientMode === 'bundled' ? '1.20.0' : undefined);
    const url = await page.evaluate(async mode => {
      const params = mode === 'object'
        ? { q: '日本語 +&?', zero: 0, disabled: false, omitted: null,
            missing: undefined, tags: ['一', '二'], date: new Date('2026-09-05T00:00:00Z') }
        : new URLSearchParams([['q', '日本語 +&?'], ['tags', '一'], ['tags', '二']]);
      const client = (window as any).axios;
      const response = await client.get('/http-query-probe?existing=keep', { params });
      return response.data.url;
    }, mode);
    const query = new URL(url).searchParams;
    expect(query.get('existing')).toBe('keep');
    expect(query.get('q')).toBe('日本語 +&?');
    if (mode === 'object') {
      expect(query.get('zero')).toBe('0');
      expect(query.get('disabled')).toBe('false');
      expect(query.has('omitted')).toBe(false);
      expect(query.has('missing')).toBe(false);
      expect(query.getAll('tags[]')).toEqual(['一', '二']);
      expect(query.get('date')).toBe('2026-09-05T00:00:00.000Z');
    } else {
      expect(query.getAll('tags')).toEqual(['一', '二']);
    }
  });
}
