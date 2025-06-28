# Arkham Nexus テスト構造ドキュメント

## 概要
2025年6月26日にテストファイルを体系的に整理し、カテゴリ別に分類しました。

## 新しいテスト構造

```
tests/
├── unit/           # 単体テスト（15ファイル）
├── integration/    # 統合テスト（10ファイル）
├── system/         # システムテスト（3ファイル）
├── ui/            # UIテスト（4ファイル）
├── performance/    # パフォーマンステスト（準備中）
├── utils/         # テストユーティリティ（3ファイル）
└── results/       # テスト結果、レポート、ログ（6ファイル）
```

## 移動されたファイル

### 単体テスト (tests/unit/)
- test_character_calculation.py
- test_character_creation_skills.py
- test_character_skill_calculation.py
- test_character_validation.py
- test_ability_limits_removed.py
- test_form_submit.py
- test_group_functionality.py
- test_groups_debug.py
- test_export_manual.py
- test_api_debug.py
- test_url_debug.py
- test_js_errors.py

### 統合テスト (tests/integration/)
- test_integration.py
- test_system_integration.py
- test_workflow_integration.py
- test_character_session_integration.py
- test_character_skills_integration.py
- test_simple_workflow.py
- test_workflow_django.py

### システムテスト (tests/system/)
- test_complete_suite.py
- test_additional_features.py
- test_character_session_simple.py

### UIテスト (tests/ui/)
- test_ui_functionality.py
- test_ui_navigation.py
- test_character_js.html
- test_sidemenu.html

### ユーティリティ (tests/utils/)
- test_runner.py
- test_runner_comprehensive.py
- run_all_tests.py (新規作成)

### テスト結果 (tests/results/)
- TEST_RESULTS_CHARACTER_SESSION.md
- TEST_RESULTS_CHARACTER_SESSION_HO_INTEGRATION.md
- TEST_RESULTS_PLAYER_SLOTS_HANDOUTS.md
- TEST_RESULTS_SESSION_FEATURES.md
- test_results.log
- README.md (新規作成)

## アプリケーション内のテスト
各アプリケーション（accounts, schedules, scenarios）内の`test_*.py`ファイルは、Django標準の構造に従って維持されています。

### accounts/
- 単体テスト: 23ファイル
- 統合テスト: 5ファイル

### schedules/
- 単体テスト: 10ファイル
- 統合テスト: 3ファイル

### scenarios/
- 単体テスト: 2ファイル

## テスト実行方法

### 新しい構造でのテスト実行
```bash
# カテゴリ別
python manage.py test tests.unit
python manage.py test tests.integration
python manage.py test tests.system
python manage.py test tests.ui

# 全カテゴリ実行
python tests/utils/run_all_tests.py
```

### 従来の方法（アプリケーション別）
```bash
python manage.py test accounts
python manage.py test schedules
python manage.py test scenarios
```

## 利点
1. **明確な分類**: テストの種類が一目でわかる
2. **実行時間の最適化**: 単体テストのみを高速実行可能
3. **保守性の向上**: 新しいテストの配置が明確
4. **CI/CD対応**: カテゴリ別にパイプラインを構築可能