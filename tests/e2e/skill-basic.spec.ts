import { test, expect } from '@playwright/test';

test.describe('技能値設定機能の基本動作確認', () => {
  test.beforeEach(async ({ page }) => {
    // 開発用ログインでログイン
    await page.goto('/accounts/dev-login/');
    await page.locator('h3:has-text("管理者")').locator('..').locator('button:has-text("このユーザーでログイン")').click();
    
    // ホームページに遷移したことを確認
    await expect(page).toHaveURL('http://localhost:8000/');
    
    // キャラクター作成ページへ移動
    await page.goto('/accounts/character/create/6th/');
  });

  test('技能タブへの切り替えと基本要素の確認', async ({ page }) => {
    // 技能タブをクリック
    await page.click('button[role="tab"]:has-text("技能")');
    
    // タブの切り替えを待つ
    await page.waitForTimeout(1000);
    
    // タブパネルが表示されることを確認（Bootstrapのshowクラスで判定）
    const skillPanel = page.locator('#skills');
    await expect(skillPanel).toHaveClass(/show/);
    
    // 技能ポイント表示の確認
    await expect(page.locator('#occupation-points')).toBeVisible();
    await expect(page.locator('#interest-points')).toBeVisible();
    
    // 技能リストが表示されることを確認
    const skillItems = page.locator('.skill-item-wrapper');
    const count = await skillItems.count();
    expect(count).toBeGreaterThan(0);
    
    // 検索ボックスの確認
    await expect(page.locator('#skill-search')).toBeVisible();
  });

  test('職業技能ポイント計算方式の変更', async ({ page }) => {
    // 能力値を設定
    await page.click('button[role="tab"]:has-text("能力値")');
    await page.fill('input#edu', '16');
    await page.fill('input#str', '14');
    await page.fill('input#int', '15');
    
    // 技能タブへ移動
    await page.click('button[role="tab"]:has-text("技能")');
    
    // 職業技能ポイント計算方式を確認
    const formulaSelect = page.locator('#occupation-formula');
    
    // 標準計算（EDU×20）
    await formulaSelect.selectOption('edu20');
    await page.waitForTimeout(1000);
    const standardPoints = await page.locator('#occupation-points').textContent();
    expect(parseInt(standardPoints)).toBe(16 * 20); // 320
    
    // 筋力系（STR×10+EDU×10）
    await formulaSelect.selectOption('str10_edu10');
    await page.waitForTimeout(1000);
    const strengthPoints = await page.locator('#occupation-points').textContent();
    expect(parseInt(strengthPoints)).toBe(14 * 10 + 16 * 10); // 300
  });

  test('技能へのポイント割り振り', async ({ page }) => {
    // 能力値を設定してポイントを確保
    await page.click('button[role="tab"]:has-text("能力値")');
    await page.fill('input#edu', '15');
    await page.fill('input#int', '12');
    
    // 技能タブへ移動
    await page.click('button[role="tab"]:has-text("技能")');
    await page.waitForTimeout(1000);
    
    // 図書館技能を探す（技能フィルターで絞り込み）
    await page.fill('#skill-search', '図書館');
    await page.waitForTimeout(500);
    
    // 図書館技能にポイントを割り振る
    const libraryOccupation = page.locator('.skill-item-wrapper:visible input[id*="skill_occupation_"]').first();
    await libraryOccupation.fill('40');
    
    // 技能合計値が更新されることを確認
    await page.waitForTimeout(500);
    const libraryTotal = await page.locator('.skill-item-wrapper:visible .skill-total').first().textContent();
    expect(parseInt(libraryTotal)).toBeGreaterThan(40); // 基本値 + 40
    
    // 残りポイントが減少していることを確認
    const remainingPoints = await page.locator('#occupation-points-remaining').textContent();
    const totalPoints = await page.locator('#occupation-points').textContent();
    expect(parseInt(remainingPoints)).toBe(parseInt(totalPoints) - 40);
  });

  test('技能検索機能', async ({ page }) => {
    // 技能タブへ移動
    await page.click('button[role="tab"]:has-text("技能")');
    await page.waitForTimeout(1000);
    
    // 全技能数を確認
    const allSkillsCount = await page.locator('.skill-item-wrapper:visible').count();
    
    // 「目星」で検索
    await page.fill('#skill-search', '目星');
    await page.waitForTimeout(500);
    
    // 検索結果が絞り込まれることを確認
    const searchResultCount = await page.locator('.skill-item-wrapper:visible').count();
    expect(searchResultCount).toBeLessThan(allSkillsCount);
    expect(searchResultCount).toBeGreaterThan(0);
    
    // 目星技能が表示されていることを確認
    await expect(page.locator('.skill-item-wrapper:visible:has-text("目星")')).toBeVisible();
  });

  test('技能フィルタータブの動作', async ({ page }) => {
    // 技能タブへ移動
    await page.click('button[role="tab"]:has-text("技能")');
    await page.waitForTimeout(1000);
    
    // 技能フィルタータブが表示されることを確認
    const filterTabs = page.locator('.nav-tabs').last(); // 技能フィルタータブ
    await expect(filterTabs).toBeVisible();
    
    // 戦闘タブをクリック
    await filterTabs.locator('button:has-text("戦闘")').click();
    await page.waitForTimeout(500);
    
    // 戦闘技能が表示されることを確認
    const combatSkills = ['こぶし', 'キック', '組み付き'];
    for (const skillName of combatSkills) {
      const skillVisible = await page.locator(`.skill-item-wrapper:visible:has-text("${skillName}")`).count();
      expect(skillVisible).toBeGreaterThan(0);
    }
    
    // 全てタブに戻す
    await filterTabs.locator('button:has-text("全て")').click();
    await page.waitForTimeout(500);
  });

  test('キャラクター保存時の技能データ確認', async ({ page }) => {
    // 基本情報を入力
    await page.fill('input[name="name"]', 'E2Eテスト探索者');
    await page.fill('input[name="age"]', '28');
    
    // 能力値を設定
    await page.click('button[role="tab"]:has-text("能力値")');
    await page.fill('input#str', '12');
    await page.fill('input#con', '13');
    await page.fill('input#pow', '14');
    await page.fill('input#dex', '11');
    await page.fill('input#app', '10');
    await page.fill('input#siz', '15');
    await page.fill('input#int', '16');
    await page.fill('input#edu', '14');
    
    // 技能タブで技能にポイントを割り振る
    await page.click('button[role="tab"]:has-text("技能")');
    await page.waitForTimeout(1000);
    
    // 図書館技能を検索して割り振り
    await page.fill('#skill-search', '図書館');
    await page.waitForTimeout(500);
    const libraryInput = page.locator('.skill-item-wrapper:visible input[id*="skill_occupation_"]').first();
    await libraryInput.fill('50');
    
    // 検索をクリアして目星技能を検索
    await page.fill('#skill-search', '目星');
    await page.waitForTimeout(500);
    const spotInput = page.locator('.skill-item-wrapper:visible input[id*="skill_interest_"]').first();
    await spotInput.fill('25');
    
    // 保存ボタンをクリック
    await page.click('button:has-text("下書き保存")');
    
    // 保存処理を待つ
    await page.waitForTimeout(3000);
    
    // 保存が成功したことを確認（URLの変化またはメッセージ）
    const currentUrl = page.url();
    const isSaved = currentUrl.includes('/character/list/') || 
                   currentUrl.includes('/character/') && !currentUrl.includes('/create/');
    expect(isSaved).toBe(true);
  });
});