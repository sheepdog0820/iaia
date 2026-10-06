import { test, expect } from '@playwright/test';
import { execFile } from 'node:child_process';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { promisify } from 'node:util';

const exec = promisify(execFile);

for (const scenario of [
  { name: 'ページ作成時間は操作の予算を消費しない', setup: 350, body: 350, fixture: 1000, expected: 'passed', error: '' },
  { name: '操作のtimeoutは維持する', setup: 0, body: 900, fixture: 1000, expected: 'timedOut', error: 'Test timeout of 500ms exceeded' },
  { name: 'ページ作成にも有限のtimeoutがある', setup: 900, body: 0, fixture: 250, expected: 'timedOut', error: 'Fixture "page" timeout of 250ms exceeded during setup' },
]) {
  test(scenario.name, async () => {
    const root = await mkdtemp(path.join(tmpdir(), 'tableno-page-budget-'));
    try {
      const fixture = JSON.stringify(path.resolve('tests/e2e/fixtures/page-budget.ts').replaceAll('\\', '/'));
      await writeFile(path.join(root, 'playwright.config.cjs'), `module.exports = {
        testDir: ${JSON.stringify(root)}, timeout: 500, retries: 0, workers: 1,
        reporter: 'json', outputDir: ${JSON.stringify(path.join(root, 'results'))},
      };`, 'utf8');
      await writeFile(path.join(root, 'budget.spec.ts'), `
        import { withPageSetupBudget, expect } from ${fixture};
        const test = withPageSetupBudget(${scenario.fixture}).extend({
          context: async ({}, use) => {
            await use({ newPage: async () => {
              await new Promise(resolve => setTimeout(resolve, ${scenario.setup}));
              return { syntheticPage: true };
            } } as any);
          },
        });
        test('synthetic budget contract', async ({ page }, testInfo) => {
          expect(testInfo.timeout).toBe(500);
          expect((page as any).syntheticPage).toBe(true);
          await new Promise(resolve => setTimeout(resolve, ${scenario.body}));
        });
      `, 'utf8');
      let stdout: string;
      let code = 0;
      try {
        ({ stdout } = await exec(process.execPath, [path.resolve('node_modules/playwright/cli.js'), 'test', '--config', path.join(root, 'playwright.config.cjs')], {
          cwd: path.resolve('.'), env: { ...process.env, CI: '1', FORCE_COLOR: '0' }, timeout: 15_000,
        }));
      } catch (error: any) {
        expect(typeof error.code).toBe('number');
        code = error.code;
        stdout = error.stdout;
      }
      const report = JSON.parse(stdout!);
      const result = report.suites[0].specs[0].tests[0].results[0];
      expect(code).toBe(scenario.expected === 'passed' ? 0 : 1);
      expect(result.status).toBe(scenario.expected);
      if (scenario.error) expect(result.error.message).toContain(scenario.error);
      // These nested runner probes use a synthetic context: no server, DB,
      // browser, credentials, or network operation is involved.
      expect(report.config.projects[0].timeout).toBe(500);
    } finally {
      // root is the exact directory returned by mkdtemp, never a repository
      // path or a user-supplied glob; remove only this disposable probe.
      expect(path.dirname(root)).toBe(path.resolve(tmpdir()));
      expect(path.basename(root)).toMatch(/^tableno-page-budget-/);
      await rm(root, { recursive: true, force: true });
    }
  });
}
