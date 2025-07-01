# 画面遷移チェックガイドライン

## 🚨 画面編集時の必須遷移チェック

**画面を編集する際は、以下の遷移チェックを必ず実行してください**

## 遷移チェックの実行タイミング
- ✅ HTMLテンプレートを編集した場合
- ✅ URL設定を変更した場合  
- ✅ JavaScriptのナビゲーション関数を修正した場合
- ✅ 新しいページやモーダルを追加した場合
- ✅ リンクやボタンを追加・削除した場合

## 📋 必須チェック項目

### 1. ナビゲーションメニューの確認
- [ ] メインナビゲーションの全リンクが正常動作
- [ ] ドロップダウンメニューの全項目が正常動作
- [ ] ユーザー認証状態（ログイン・ログアウト）での表示切り替え

### 2. 画面内リンクの確認  
- [ ] ボタンクリックが正常動作
- [ ] フォーム送信が正常動作
- [ ] AJAX通信が正常動作
- [ ] モーダル表示・非表示が正常動作

### 3. URL遷移の確認
- [ ] 直接URL入力での画面表示
- [ ] 戻る・進むボタンでの正常動作
- [ ] ページリロードでの状態保持

### 4. エラーハンドリングの確認
- [ ] 存在しないURLへのアクセス（404エラー）
- [ ] 権限がない画面へのアクセス（403エラー）  
- [ ] JavaScript関数の存在確認

## 🔍 遷移チェックの実行手順

### Step 1: サーバー起動確認
```bash
# サーバーの起動確認
python3 manage.py runserver 0.0.0.0:8000

# サーバーの動作確認
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/
```

### Step 2: メインナビゲーションのテスト
```bash
# 主要URL の HTTP ステータス確認
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/accounts/character/list/
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/schedules/calendar/view/
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/accounts/groups/view/
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/accounts/statistics/view/
```

### Step 3: ブラウザでの手動確認
1. **ホーム画面**: `http://localhost:8000/`
   - [ ] ログイン状態での表示確認
   - [ ] 未ログイン状態での表示確認
   
2. **メインナビゲーション**
   - [ ] カレンダーリンク: `/api/schedules/calendar/view/`
   - [ ] セッションリンク: `/api/schedules/sessions/view/`  
   - [ ] シナリオリンク: `/api/scenarios/archive/view/`
   - [ ] グループリンク: `/accounts/groups/view/`
   - [ ] キャラクターリンク: `/accounts/character/list/`

3. **キャラクター関連**
   - [ ] 6版キャラクター作成: `/accounts/character/create/6th/`
   - [ ] キャラクター一覧: `/accounts/character/list/`
   - [ ] ユーザープロフィール: `/accounts/dashboard/`

4. **JavaScript関数の確認**
   ```javascript
   // ブラウザのConsoleで実行
   console.log('Navigation Functions Check:');
   console.log('loadCalendarView:', typeof loadCalendarView);
   console.log('loadSessionsView:', typeof loadSessionsView);  
   console.log('loadScenariosView:', typeof loadScenariosView);
   console.log('loadGroupsView:', typeof loadGroupsView);
   console.log('loadStatisticsView:', typeof loadStatisticsView);
   ```

### Step 4: エラー確認
- [ ] ブラウザ開発者ツールでConsole Errorなし
- [ ] ネットワークタブで404・500エラーなし
- [ ] JavaScript関数の未定義エラーなし

## 🚨 遷移エラー発見時の対応

### 即座対応ルール
1. **エラーログ確認**: server.log で詳細エラーを確認
2. **URL設定確認**: urls.py にルートが定義されているか確認
3. **JavaScript確認**: 関数が正しいスコープで定義されているか確認
4. **権限確認**: ログイン必須ページの認証確認

### 修正手順
```bash
# Step 1: エラー特定
tail -f server.log

# Step 2: URL設定確認  
rg -n "name='対象URL名'" --type py

# Step 3: テンプレート確認
rg -n "{% url '対象URL名' %}" templates/

# Step 4: JavaScript確認
rg -n "対象関数名" static/js/
```

## 📝 遷移チェック完了時の記録

遷移チェック完了時は以下の形式で記録：

```markdown
## 遷移チェック完了報告 - [日時]

### ✅ 確認済み項目
- [x] メインナビゲーション（5項目）
- [x] キャラクター関連（3項目）  
- [x] JavaScript関数（5項目）
- [x] エラーハンドリング（404/403/500）

### 🐛 発見・修正した問題
- 問題1: 7版キャラクター作成リンクの削除 → 修正完了
- 問題2: [問題説明] → [修正内容]

### 📋 テスト済みURL一覧
- ✅ / (ホーム)
- ✅ /accounts/character/list/ (キャラクター一覧)
- ✅ /accounts/character/create/6th/ (6版作成) 
- ✅ /api/schedules/calendar/view/ (カレンダー)
- ✅ /accounts/groups/view/ (グループ)
- ✅ /accounts/statistics/view/ (統計)

### 🔧 推奨改善項目
- 改善1: [改善提案]
- 改善2: [改善提案]
```

## 🔄 自動化ツールの活用

### Selenium/Playwright による自動チェック
```python
# 基本的な遷移チェックの自動化例
from selenium import webdriver
from selenium.webdriver.common.by import By

def check_navigation():
    driver = webdriver.Chrome()
    driver.get("http://localhost:8000")
    
    # ナビゲーションリンクの確認
    nav_links = driver.find_elements(By.CSS_SELECTOR, "nav a")
    for link in nav_links:
        href = link.get_attribute("href")
        print(f"Checking: {href}")
        # リンクをクリックして遷移確認
    
    driver.quit()
```

### URLリストの一括チェック
```python
import requests

urls = [
    "/",
    "/accounts/character/list/",
    "/accounts/character/create/6th/",
    "/api/schedules/calendar/view/",
    "/accounts/groups/view/",
]

for url in urls:
    response = requests.get(f"http://localhost:8000{url}")
    print(f"{url}: {response.status_code}")
```

## 📊 チェック頻度とタイミング

### 必須チェックタイミング
- **リリース前**: 全画面の完全チェック
- **大規模変更後**: 影響範囲の全チェック
- **定期チェック**: 週次での主要画面チェック

### 効率的なチェック方法
1. **優先度設定**: 利用頻度の高い画面から確認
2. **バッチ処理**: 自動化ツールで基本チェック
3. **手動確認**: 複雑な画面遷移は手動で確認

**重要**: このガイドラインに従い、画面編集後は必ず遷移チェックを実行してください。