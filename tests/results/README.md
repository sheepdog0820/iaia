# テスト結果ディレクトリ

## 概要
このディレクトリには、各種テストの実行結果やレポートが保存されています。

## ファイル一覧

### 統合テスト結果
- `TEST_RESULTS_CHARACTER_SESSION.md` - キャラクター・セッション統合テストの結果
- `TEST_RESULTS_CHARACTER_SESSION_HO_INTEGRATION.md` - キャラクター・セッション・ハンドアウト統合テストの結果
- `TEST_RESULTS_PLAYER_SLOTS_HANDOUTS.md` - プレイヤースロット・ハンドアウトテストの結果
- `TEST_RESULTS_SESSION_FEATURES.md` - セッション機能テストの結果

### ログファイル
- `test_results.log` - テスト実行の詳細ログ

## 結果ファイルの形式

各結果ファイルには以下の情報が含まれます：
- 実行日時
- テスト環境
- 実行したテストケース
- 成功/失敗の詳細
- エラーメッセージ（ある場合）
- 実行時間

## 新しい結果の追加

テスト実行後、結果を保存する場合：
```bash
# 結果をファイルに保存
python manage.py test tests.integration > tests/results/TEST_RESULTS_$(date +%Y%m%d).md

# タイムスタンプ付きで保存
python manage.py test --verbosity=2 | tee tests/results/test_$(date +%Y%m%d_%H%M%S).log
```