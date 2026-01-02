# タブレノ テストスイート

## 概要
このディレクトリには、タブレノプロジェクトのすべてのテストが体系的に整理されています。

## ディレクトリ構造

```
tests/
├── unit/           # 単体テスト（個別の関数、クラス、モデル）
├── integration/    # 統合テスト（複数コンポーネントの連携）
├── system/         # システムテスト（エンドツーエンド）
├── ui/            # UIテスト（画面表示、ナビゲーション）
├── performance/    # パフォーマンステスト（負荷、速度）
└── utils/         # テストユーティリティ（ランナー、ヘルパー）
```

## テストの実行方法

### カテゴリ別実行
```bash
# 単体テストのみ
python -m pytest tests/unit/

# 統合テストのみ
python -m pytest tests/integration/

# システムテストのみ
python -m pytest tests/system/

# UIテストのみ
python -m pytest tests/ui/
```

### Django テストランナーでの実行
```bash
# すべてのテスト
python manage.py test

# 特定のカテゴリ
python manage.py test tests.unit
python manage.py test tests.integration
python manage.py test tests.system
python manage.py test tests.ui
```

### テストランナーツール
```bash
# 基本的なテストランナー（カバレッジ、リンティング含む）
python tests/utils/test_runner.py

# 包括的テストランナー
python tests/utils/test_runner_comprehensive.py

# 完全テストスイート
python tests/system/test_complete_suite.py
```

## テストカテゴリの説明

### Unit Tests (単体テスト)
- 個別の関数、メソッド、クラスのテスト
- 外部依存を最小限に抑えたテスト
- 高速実行が可能

### Integration Tests (統合テスト)
- 複数のコンポーネント間の連携テスト
- データベースアクセスを含むテスト
- APIエンドポイントのテスト

### System Tests (システムテスト)
- エンドツーエンドのシナリオテスト
- 実際のユーザーワークフローのテスト
- 全機能の包括的なテスト

### UI Tests (UIテスト)
- 画面表示の確認
- ナビゲーションのテスト
- レスポンシブデザインのテスト
- JavaScriptの動作確認

### Performance Tests (パフォーマンステスト)
- 負荷テスト
- レスポンス時間の測定
- リソース使用量の監視

## テスト作成ガイドライン

### 新しいテストの配置
1. テストの性質を判断（単体/統合/システム/UI/パフォーマンス）
2. 適切なディレクトリに配置
3. わかりやすいファイル名を使用（test_機能名_テスト種別.py）

### 命名規則
- 単体テスト: `test_<feature>_unit.py`
- 統合テスト: `test_<feature>_integration.py`
- システムテスト: `test_<feature>_system.py`
- UIテスト: `test_<feature>_ui.py`

### テストの品質基準
- 各テストは独立して実行可能
- テストは冪等性を保つ（何度実行しても同じ結果）
- 明確なアサーションとエラーメッセージ
- 適切なセットアップとクリーンアップ

## 継続的インテグレーション
- プッシュ前に全テストを実行
- プルリクエストには必ずテストを含める
- カバレッジ目標: 80%以上