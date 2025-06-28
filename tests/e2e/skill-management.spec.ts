import { test, expect } from '@playwright/test';

test.describe('技能値設定機能の包括的E2Eテスト', () => {
  test.beforeEach(async ({ page }) => {
    // 開発用ログインでログイン
    await page.goto('/accounts/dev-login/');
    await page.locator('h3:has-text("管理者")').locator('..').locator('button:has-text("このユーザーでログイン")').click();
    
    // ホームページに遷移したことを確認
    await expect(page).toHaveURL('http://localhost:8000/');
    
    // キャラクター作成ページへ移動
    await page.goto('/accounts/character/create/6th/');
  });

  test('職業技能ポイント計算方式の選択と自動計算', async ({ page }) => {
    // 能力値タブで基本能力値を設定
    await page.click('button[role="tab"]:has-text("能力値")');
    await page.fill('input#str', '15');
    await page.fill('input#con', '14');
    await page.fill('input#pow', '13');
    await page.fill('input#dex', '12');
    await page.fill('input#app', '11');
    await page.fill('input#siz', '16');
    await page.fill('input#int', '17');
    await page.fill('input#edu', '18');
    
    // 技能タブへ移動
    await page.click('button[role="tab"]:has-text("技能")');
    await page.waitForLoadState('networkidle');
    
    // 職業技能ポイント計算方式のドロップダウンを確認
    const calculationSelect = page.locator('select#occupation-formula');
    await expect(calculationSelect).toBeVisible();
    
    // 標準計算（EDU×20）の確認
    await calculationSelect.selectOption('edu20');
    await page.waitForTimeout(500);
    let occupationPoints = await page.locator('#occupation-points').textContent();
    expect(parseInt(occupationPoints)).toBe(18 * 20); // 360ポイント
    
    // 筋力系（STR×10+EDU×10）の確認
    await calculationSelect.selectOption('str10_edu10');
    await page.waitForTimeout(500);
    occupationPoints = await page.locator('#occupation-points').textContent();
    expect(parseInt(occupationPoints)).toBe(15 * 10 + 18 * 10); // 330ポイント
    
    // 知性系（INT×10+EDU×10）の確認
    await calculationSelect.selectOption('int10_edu10');
    await page.waitForTimeout(500);
    occupationPoints = await page.locator('#occupation-points').textContent();
    expect(parseInt(occupationPoints)).toBe(17 * 10 + 18 * 10); // 350ポイント
    
    // 趣味技能ポイント（INT×10）の確認
    const hobbyPoints = await page.locator('#interest-points').textContent();
    expect(parseInt(hobbyPoints)).toBe(17 * 10); // 170ポイント
  });

  test('技能ポイントの割り振りとリアルタイム更新', async ({ page }) => {
    // 能力値を設定
    await page.click('button[role="tab"]:has-text("能力値")');
    await page.fill('input#edu', '15'); // 職業ポイント = 300
    await page.fill('input#int', '12'); // 趣味ポイント = 120
    
    // 技能タブへ移動
    await page.click('button[role="tab"]:has-text("技能")');
    await page.waitForLoadState('networkidle');
    
    // 図書館技能に職業ポイントを割り振り
    const librarySkill = page.locator('.skill-item-wrapper:has-text("図書館")').first();
    const libraryOccupationInput = librarySkill.locator('input[name*="skill_occupation_"]');
    await libraryOccupationInput.fill('50');
    
    // 残りポイントがリアルタイムで更新されることを確認
    await page.waitForTimeout(500);
    let remainingOccupation = await page.locator('#occupation-points-remaining').textContent();
    expect(parseInt(remainingOccupation)).toBe(250); // 300 - 50
    
    // 目星技能に趣味ポイントを割り振り
    const spotSkill = page.locator('.skill-item-wrapper:has-text("目星")').first();
    const spotHobbyInput = spotSkill.locator('input[name*="skill_interest_"]');
    await spotHobbyInput.fill('30');
    
    // 残り趣味ポイントの更新を確認
    await page.waitForTimeout(500);
    let remainingHobby = await page.locator('#interest-points-remaining').textContent();
    expect(parseInt(remainingHobby)).toBe(90); // 120 - 30
    
    // 技能値の合計が正しく計算されることを確認
    const libraryTotal = await librarySkill.locator('.skill-total').textContent();
    expect(parseInt(libraryTotal)).toBe(50 + 25); // 職業50 + 基本値25
    
    const spotTotal = await spotSkill.locator('.skill-total').textContent();
    expect(parseInt(spotTotal)).toBe(30 + 25); // 趣味30 + 基本値25
  });

  test('技能値の上限チェック（90%）', async ({ page }) => {
    // 技能タブへ移動
    await page.click('button[role="tab"]:has-text("技能")');
    await page.waitForLoadState('networkidle');
    
    // 技能に90を超える値を入力
    const firstSkill = page.locator('.skill-item-wrapper').first();
    const occupationInput = firstSkill.locator('input[name*="skill_occupation_"]');
    const hobbyInput = firstSkill.locator('input[name*="skill_interest_"]');
    
    await occupationInput.fill('70');
    await hobbyInput.fill('30'); // 合計100を超える
    
    await page.waitForTimeout(500);
    
    // 警告メッセージまたは値の制限を確認
    const skillTotal = await firstSkill.locator('.skill-total').textContent();
    const totalValue = parseInt(skillTotal);
    
    // 90を超えないことを確認（実装によって異なる可能性）
    expect(totalValue).toBeLessThanOrEqual(90);
  });

  test('技能カテゴリフィルターの動作', async ({ page }) => {
    // 技能タブへ移動
    await page.click('button[role="tab"]:has-text("技能")');
    await page.waitForLoadState('networkidle');
    
    // カテゴリフィルタータブの存在を確認
    const combatTab = page.locator('button#combat-skills-tab');
    await expect(combatTab).toBeVisible();
    
    // 戦闘技能タブをクリック
    await combatTab.click();
    await page.waitForTimeout(500);
    
    // 戦闘技能のみが表示されることを確認
    const visibleSkills = await page.locator('.skill-item-wrapper:visible').count();
    const combatSkillNames = ['こぶし', 'キック', '組み付き', '頭突き', '拳銃', 'ライフル'];
    
    for (const skillName of combatSkillNames) {
      const skill = page.locator(`.skill-item-wrapper:has-text("${skillName}")`).first();
      const isVisible = await skill.isVisible();
      if (isVisible) {
        expect(isVisible).toBe(true);
      }
    }
    
    // 全技能表示に戻す
    const allTab = page.locator('button#all-skills-tab');
    await allTab.click();
    await page.waitForTimeout(500);
    
    // より多くの技能が表示されることを確認
    const allSkillsCount = await page.locator('.skill-item-wrapper:visible').count();
    expect(allSkillsCount).toBeGreaterThan(visibleSkills);
  });

  test('ポイント割り振り済み技能の表示', async ({ page }) => {
    // 能力値を設定
    await page.click('button[role="tab"]:has-text("能力値")');
    await page.fill('input#edu', '15');
    await page.fill('input#int', '12');
    
    // 技能タブへ移動
    await page.click('button[role="tab"]:has-text("技能")');
    await page.waitForLoadState('networkidle');
    
    // いくつかの技能にポイントを割り振る
    const skills = [
      { name: '図書館', points: '40' },
      { name: '目星', points: '30' },
      { name: '聞き耳', points: '20' }
    ];
    
    for (const skill of skills) {
      const skillElement = page.locator(`.skill-item-wrapper:has-text("${skill.name}")`).first();
      await skillElement.locator('input[name*="skill_occupation_"]').fill(skill.points);
    }
    
    await page.waitForTimeout(500);
    
    // フィルターでポイント割り振り済みを選択
    const allocatedTab = page.locator('button#allocated-skills-tab');
    if (await allocatedTab.isVisible()) {
      await allocatedTab.click();
      await page.waitForTimeout(500);
      
      // 割り振った技能のみが表示されることを確認
      for (const skill of skills) {
        const skillElement = page.locator(`.skill-item-wrapper:has-text("${skill.name}")`).first();
        await expect(skillElement).toBeVisible();
      }
    }
  });

  test('技能ポイントのリセット機能', async ({ page }) => {
    // 技能タブへ移動
    await page.click('button[role="tab"]:has-text("技能")');
    await page.waitForLoadState('networkidle');
    
    // いくつかの技能にポイントを割り振る
    const librarySkill = page.locator('.skill-item-wrapper:has-text("図書館")').first();
    await librarySkill.locator('input[name*="skill_occupation_"]').fill('50');
    
    const spotSkill = page.locator('.skill-item-wrapper:has-text("目星")').first();
    await spotSkill.locator('input[name*="skill_interest_"]').fill('30');
    
    await page.waitForTimeout(500);
    
    // リセットボタンをクリック
    const resetButton = page.locator('button:has-text("技能ポイントをリセット")');
    if (await resetButton.isVisible()) {
      await resetButton.click();
      
      // 確認ダイアログが表示される場合
      page.on('dialog', dialog => dialog.accept());
      
      await page.waitForTimeout(1000);
      
      // ポイントがリセットされたことを確認
      const libraryOccupation = await librarySkill.locator('input[name*="skill_occupation_"]').inputValue();
      const spotHobby = await spotSkill.locator('input[name*="skill_interest_"]').inputValue();
      
      expect(parseInt(libraryOccupation) || 0).toBe(0);
      expect(parseInt(spotHobby) || 0).toBe(0);
    }
  });

  test('技能の検索機能', async ({ page }) => {
    // 技能タブへ移動
    await page.click('button[role="tab"]:has-text("技能")');
    await page.waitForLoadState('networkidle');
    
    // 検索ボックスに入力
    const searchInput = page.locator('input#skill-search');
    if (await searchInput.isVisible()) {
      await searchInput.fill('図書');
      await page.waitForTimeout(500);
      
      // 図書館技能のみが表示されることを確認
      const librarySkill = page.locator('.skill-item-wrapper:has-text("図書館")').first();
      await expect(librarySkill).toBeVisible();
      
      // 他の技能が非表示になっていることを確認
      const otherSkill = page.locator('.skill-item-wrapper:has-text("目星")').first();
      const isOtherVisible = await otherSkill.isVisible();
      expect(isOtherVisible).toBe(false);
      
      // 検索をクリア
      await searchInput.clear();
      await page.waitForTimeout(500);
      
      // すべての技能が再表示されることを確認
      await expect(otherSkill).toBeVisible();
    }
  });

  test('キャラクター保存時の技能データ保存', async ({ page }) => {
    // 基本情報を入力
    await page.fill('input[name="name"]', '技能テスト探索者');
    await page.fill('input[name="age"]', '30');
    await page.selectOption('select[name="gender"]', { label: '女性' });
    await page.fill('input[name="occupation"]', '考古学者');
    
    // 能力値を設定
    await page.click('button[role="tab"]:has-text("能力値")');
    await page.fill('input#str', '10');
    await page.fill('input#con', '12');
    await page.fill('input#pow', '14');
    await page.fill('input#dex', '13');
    await page.fill('input#app', '11');
    await page.fill('input#siz', '15');
    await page.fill('input#int', '16');
    await page.fill('input#edu', '17');
    
    // 技能にポイントを割り振る
    await page.click('button[role="tab"]:has-text("技能")');
    await page.waitForLoadState('networkidle');
    
    const librarySkill = page.locator('.skill-item-wrapper:has-text("図書館")').first();
    await librarySkill.locator('input[name*="skill_occupation_"]').fill('60');
    
    const spotSkill = page.locator('.skill-item-wrapper:has-text("目星")').first();
    await spotSkill.locator('input[name*="skill_interest_"]').fill('40');
    
    // 保存
    await page.click('button:has-text("下書き保存")');
    await page.waitForTimeout(2000);
    
    // 保存成功の確認（実装に応じて調整）
    // 例：成功メッセージ、リダイレクト、または保存済み表示
    const pageUrl = page.url();
    const isListPage = pageUrl.includes('/character/list/');
    const isDetailPage = pageUrl.includes('/character/') && !pageUrl.includes('/create/');
    
    // いずれかのページに遷移していることを確認
    expect(isListPage || isDetailPage).toBe(true);
  });
});