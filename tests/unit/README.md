# 単体テスト (Unit Tests)

## 概要
このディレクトリには、個別の関数、クラス、モデルの単体テストが含まれています。

## テストファイル一覧

### キャラクター関連
- `test_character_calculation.py` - キャラクター計算ロジック
- `test_character_creation_skills.py` - キャラクター作成時のスキル
- `test_character_skill_calculation.py` - スキル計算
- `test_character_validation.py` - キャラクターバリデーション
- `test_ability_limits_removed.py` - 能力値制限除去

### フォーム・UI関連
- `test_form_submit.py` - フォーム送信
- `test_js_errors.py` - JavaScriptエラー検出

### グループ機能
- `test_group_functionality.py` - グループ機能
- `test_groups_debug.py` - グループ機能デバッグ

### API・エクスポート
- `test_api_debug.py` - APIデバッグ
- `test_url_debug.py` - URLデバッグ
- `test_export_manual.py` - エクスポート機能

## 実行方法
```bash
# すべての単体テストを実行
python manage.py test tests.unit

# 特定のテストファイルを実行
python manage.py test tests.unit.test_character_calculation
```