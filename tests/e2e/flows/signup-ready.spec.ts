import { expect, test } from '../fixtures/page-budget';
import { openSignup } from '../fixtures/signup-ready';

const form = `<form id="email-signup-form">
  <input id="id_username"><button id="signup-btn">登録して開始</button>
</form>`;

test('登録フォームが利用可能なら画像のload完了を待たない', async ({ page }) => {
  let release!: () => void;
  const pending = new Promise<void>(resolve => { release = resolve; });
  await page.route('**/*', async route => {
    if (new URL(route.request().url()).pathname === '/signup/') {
      await route.fulfill({ contentType: 'text/html', body: `${form}<img src="/pending.png">` });
    } else {
      await pending;
      await route.abort();
    }
  });
  page.setDefaultNavigationTimeout(3_000);
  try {
    await openSignup(page);
    await page.locator('#id_username').fill('合成登録ユーザー');
    await expect(page.locator('#id_username')).toHaveValue('合成登録ユーザー');
    expect(await page.evaluate(() => document.readyState)).not.toBe('complete');
  } finally {
    release();
  }
});

test('遅延した初期化scriptが完了するまで登録を開始しない', async ({ page }) => {
  let release!: () => void;
  const pending = new Promise<void>(resolve => { release = resolve; });
  await page.route('**/*', async route => {
    if (new URL(route.request().url()).pathname === '/signup/') {
      await route.fulfill({ contentType: 'text/html', body: `${form}<script src="/init.js"></script>` });
    } else {
      await pending;
      await route.fulfill({
        contentType: 'application/javascript',
        body: "document.addEventListener('DOMContentLoaded', () => { window.signupInitialized = true; });",
      });
    }
  });
  let completed = false;
  const initialization = page.waitForRequest('**/init.js');
  const opened = openSignup(page).then(() => { completed = true; });
  try {
    await initialization;
    expect(await page.evaluate(() => (window as any).signupInitialized)).toBeUndefined();
    expect(completed).toBe(false);
  } finally {
    release();
    await opened;
  }
  expect(await page.evaluate(() => (window as any).signupInitialized)).toBe(true);
});

test('登録フォームが描画されてもHTTP失敗を成功扱いしない', async ({ page }) => {
  await page.route('**/*', route => route.fulfill({ status: 500, contentType: 'text/html', body: form }));
  await expect(openSignup(page)).rejects.toMatchObject({
    matcherResult: { actual: 500, expected: 200, name: 'toBe', pass: false },
  });
});

test('登録フォームの欠落を成功扱いしない', async ({ page }) => {
  await page.route('**/*', route => route.fulfill({ contentType: 'text/html', body: '<h1>フォームなし</h1>' }));
  await expect(openSignup(page)).rejects.toThrow(/email-signup-form/);
});

test('入力や送信が無効な登録フォームを成功扱いしない', async ({ page }) => {
  for (const unavailable of [form.replace('<input', '<input disabled'), form.replace('<button', '<button disabled')]) {
    await page.route('**/*', route => route.fulfill({ contentType: 'text/html', body: unavailable }));
    await expect(openSignup(page)).rejects.toThrow(/id_username|signup-btn/);
    await page.unrouteAll({ behavior: 'wait' });
  }
});
