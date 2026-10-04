import { expect, test, Page } from '@playwright/test';
import path from 'node:path';

const modalSelector = '[id^="arkham-confirm-"]';

test.beforeEach(async ({ page }, testInfo) => {
  if (process.env.ARKHAM_CONFIRM_COVERAGE === '1' && testInfo.project.name === 'chromium') {
    await page.coverage.startJSCoverage({ resetOnNavigation: false, reportAnonymousScripts: true });
  }
});

test.afterEach(async ({ page }, testInfo) => {
  if (process.env.ARKHAM_CONFIRM_COVERAGE === '1' && testInfo.project.name === 'chromium') {
    const entries = await page.coverage.stopJSCoverage();
    await testInfo.attach('confirm-js-coverage', {
      body: Buffer.from(JSON.stringify(entries.filter(entry => entry.source?.includes('const ARKHAM =')))),
      contentType: 'application/json',
    });
  }
});

async function loadConfirm(page: Page, bootstrap: boolean) {
  await page.setContent('<!doctype html><html lang="ja"><body><button id="origin">確認を開く</button></body></html>');
  await page.addStyleTag({ path: path.resolve('static/vendor/bootstrap/5.3.0/bootstrap.min.css') });
  if (bootstrap) {
    await page.addScriptTag({ path: path.resolve('static/vendor/bootstrap/5.3.0/bootstrap.bundle.min.js') });
  }
  await page.evaluate(() => { (window as any).axios = { defaults: {} }; });
  await page.addScriptTag({ path: path.resolve('static/js/arkham.js') });
  await page.evaluate(() => {
    (window as any).confirmResults = [];
    (window as any).confirmShown = false;
    (window as any).openConfirm = () => {
      const result = (window as any).ARKHAM.confirm('削除してもよろしいですか？');
      const modal = document.querySelector('[id^="arkham-confirm-"]');
      if ((window as any).bootstrap) {
        modal!.addEventListener('shown.bs.modal', () => { (window as any).confirmShown = true; }, { once: true });
      } else {
        (window as any).confirmShown = true;
      }
      result.then(
        (value: boolean) => (window as any).confirmResults.push({
          value,
          modalCount: document.querySelectorAll('[id^="arkham-confirm-"]').length,
          backdropCount: document.querySelectorAll('.modal-backdrop').length,
          locked: document.body.classList.contains('modal-open'),
          disposed: !(window as any).bootstrap || (window as any).bootstrap.Modal.getInstance(modal) === null,
        }),
        (error: Error) => (window as any).confirmResults.push({ error: error.message }),
      );
    };
    document.getElementById('origin')!.onclick = (window as any).openConfirm;
  });
}

async function expectClosed(page: Page, value: boolean) {
  await expect.poll(() => page.evaluate(() => (window as any).confirmResults)).toEqual([
    { value, modalCount: 0, backdropCount: 0, locked: false, disposed: true },
  ]);
  await expect(page.locator(modalSelector)).toHaveCount(0);
  await expect(page.locator('.modal-backdrop')).toHaveCount(0);
}

for (const bootstrap of [true, false]) {
  test.describe(bootstrap ? 'Bootstrap確認ダイアログ' : 'Bootstrapなしの確認ダイアログ', () => {
    for (const action of ['confirm', 'cancel', 'close', 'escape', 'backdrop']) {
      test(`${action}は選択結果と後片付けを一度だけ返す`, async ({ page }) => {
        const errors: string[] = [];
        page.on('pageerror', error => errors.push(error.message));
        await loadConfirm(page, bootstrap);
        await page.locator('#origin').click();
        const modal = page.locator(modalSelector);
        await expect(modal).toBeVisible();
        await expect(modal.locator('.modal-title')).toHaveText('確認');
        await expect(modal.locator('[data-confirm-message]')).toHaveText('削除してもよろしいですか？');
        await modal.press('Tab');
        expect(await page.evaluate(() => (window as any).confirmResults)).toEqual([]);
        if (bootstrap) {
          await page.waitForFunction(() => (window as any).confirmShown);
        }
        if (action === 'escape') {
          await modal.press('Escape');
        } else if (action === 'backdrop') {
          await modal.click({ position: { x: 5, y: 5 } });
        } else {
          const selector = action === 'confirm' ? '[data-confirm-action]' : action === 'close' ? '.btn-close' : '.btn-outline-secondary';
          await modal.locator(selector).click();
        }
        await expectClosed(page, action === 'confirm');
        expect(errors).toEqual([]);
      });
    }
  });

  test(`${bootstrap ? 'Bootstrap' : 'Bootstrapなし'}でダイアログ内から外へのドラッグはキャンセルしない`, async ({ page }) => {
    await loadConfirm(page, bootstrap);
    await page.locator('#origin').click();
    await expect(page.locator(modalSelector)).toBeVisible();
    await page.waitForFunction(() => (window as any).confirmShown);
    await page.evaluate(() => {
      const modal = document.querySelector('[id^="arkham-confirm-"]') as HTMLElement;
      modal.querySelector('.modal-body')!.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
      modal.click();
    });
    expect(await page.evaluate(() => (window as any).confirmResults)).toEqual([]);
    await expect(page.locator(modalSelector)).toHaveClass(/show/);
    await page.locator(modalSelector).getByRole('button', { name: 'キャンセル', exact: true }).click();
    await expectClosed(page, false);
  });
}

test('Bootstrapなしの背景そのものを押してもキャンセルできる', async ({ page }) => {
  await loadConfirm(page, false);
  await page.locator('#origin').click();
  await page.evaluate(() => {
    const backdrop = document.querySelector('.modal-backdrop') as HTMLElement;
    backdrop.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
    backdrop.click();
  });
  await expectClosed(page, false);
});

test('外部から閉じられた場合も実行扱いにせず、繰り返し開ける', async ({ page }) => {
  await loadConfirm(page, true);
  await page.locator('#origin').click();
  await page.waitForFunction(() => (window as any).confirmShown);
  await page.evaluate(() => {
    (window as any).bootstrap.Modal.getInstance(document.querySelector('[id^="arkham-confirm-"]')).hide();
  });
  await expectClosed(page, false);
  await page.evaluate(() => {
    (window as any).confirmResults = [];
    (window as any).confirmShown = false;
  });
  await page.locator('#origin').click();
  await page.waitForFunction(() => (window as any).confirmShown);
  await page.locator(`${modalSelector} [data-confirm-action]`).click();
  await expectClosed(page, true);
});

for (const action of ['confirm', 'cancel', 'close', 'escape', 'backdrop']) {
  test(`表示アニメーション中の${action}も失われない`, async ({ page }) => {
    await loadConfirm(page, true);
    // Enlarge the real CSS transition window, not the test timeout or expectations.
    await page.addStyleTag({ content: '.modal.fade .modal-dialog { transition-duration: 1s !important; }' });
    await page.evaluate(async (action) => {
      (window as any).openConfirm();
      const modal = document.querySelector('[id^="arkham-confirm-"]') as HTMLElement;
      while (!modal.classList.contains('show')) {
        await new Promise<void>(resolve => requestAnimationFrame(() => resolve()));
      }
      if (!(window as any).bootstrap.Modal.getInstance(modal)._isTransitioning) {
        throw new Error('表示アニメーション中の操作を再現できませんでした');
      }
      if (action === 'escape') {
        modal.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
      } else {
        const selector = action === 'confirm' ? '[data-confirm-action]' : action === 'close' ? '.btn-close' : '.btn-outline-secondary';
        const target = action === 'backdrop' ? modal : modal.querySelector(selector) as HTMLElement;
        target.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
        target.click();
        // A second, opposing action must not change the accepted decision.
        (modal.querySelector(action === 'confirm' ? '.btn-outline-secondary' : '[data-confirm-action]') as HTMLElement).click();
      }
    }, action);
    await expectClosed(page, action === 'confirm');
  });
}
