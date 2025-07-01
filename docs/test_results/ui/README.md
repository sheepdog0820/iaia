# UIテストケース・結果ドキュメント

このディレクトリには、キャラクター作成画面のUIテストケースとテスト結果を格納しています。

## 📁 ファイル構成

### テストケース
- **test_character_create_ui.py**
  - 基本的なUIテストケース（14個）
  - 非Seleniumテスト（4個）とSeleniumテスト（10個）
  - ページレンダリング、フォーム検証、JavaScript機能のテスト

- **test_character_create_advanced_ui.py**
  - 高度なUIテストケース（7個）
  - 複数技能を持つキャラクター作成のテスト
  - DEX→回避技能連動、技能初期値編集機能のテスト

### テスト結果
- **test_result_character_create_ui.md**
  - 基本UIテストの実施結果
  - テストカバレッジと実行結果のサマリー

- **CHARACTER_CREATE_UPDATE_RESULT.md**
  - 2025年7月1日実施の機能改修結果
  - DEX連動、技能初期値編集、HP表示修正の詳細

## 🧪 テスト実行方法

### 基本UIテスト
```bash
python3 manage.py test tests.ui.test_character_create_ui
```

### 高度なUIテスト
```bash
python3 manage.py test tests.ui.test_character_create_advanced_ui
```

### 特定のテストのみ実行
```bash
# 非Seleniumテストのみ
python3 manage.py test tests.ui.test_character_create_ui.CharacterCreateUITest

# Seleniumテストのみ（要ChromeDriver）
python3 manage.py test tests.ui.test_character_create_ui.CharacterCreateSeleniumTest
```

## 📊 テストカバレッジ

### 基本UIテスト
- ✅ ページレンダリング
- ✅ フォームフィールド確認
- ✅ JavaScript関数定義
- ✅ ダイスロール機能
- ✅ 自動計算機能
- ✅ 職業テンプレート
- ✅ 技能管理
- ✅ フォームバリデーション
- ✅ レスポンシブレイアウト

### 高度なUIテスト  
- ✅ DEX→回避技能同期
- ✅ カスタム技能基本値編集
- ✅ 複数技能へのポイント割り振り
- ✅ 職業テンプレート適用
- ✅ 割り振り済み技能タブ
- ✅ 完全なキャラクター作成フロー

## 🔧 環境要件

### Seleniumテスト実行時
- ChromeDriver または Chromium
- Python selenium パッケージ
- ヘッドレスモード対応（CI/CD環境でも実行可能）

### 詳細設定
- [Seleniumインストールガイド](../../SELENIUM_INSTALLATION_GUIDE.md)
- [E2Eテストセットアップ](../../E2E_TEST_SETUP.md)