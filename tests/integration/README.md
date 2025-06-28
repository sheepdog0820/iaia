# 統合テスト (Integration Tests)

## 概要
このディレクトリには、複数のコンポーネント間の連携をテストする統合テストが含まれています。

## テストファイル一覧

### 基本統合テスト
- `test_integration.py` - ユーザー・グループ・セッション・シナリオの連携
- `test_system_integration.py` - 認証・権限・業務フロー包括テスト

### ワークフロー統合テスト
- `test_workflow_integration.py` - 複雑なワークフローの統合テスト
- `test_simple_workflow.py` - シンプルなワークフローテスト
- `test_workflow_django.py` - Django統合ワークフロー

### キャラクター・セッション統合
- `test_character_session_integration.py` - キャラクター作成からセッション参加まで
- `test_character_skills_integration.py` - キャラクタースキルシステムの統合

## 実行方法
```bash
# すべての統合テストを実行
python manage.py test tests.integration

# 特定のテストファイルを実行
python manage.py test tests.integration.test_integration
```

## 注意事項
- データベースアクセスを含むため、単体テストより実行時間が長い
- テスト間の依存関係に注意
- トランザクションの適切な管理が必要