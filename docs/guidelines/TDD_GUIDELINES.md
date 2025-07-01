# テスト駆動開発（TDD）ガイドライン

## 【重要】テスト駆動開発（TDD）の徹底

**このプロジェクトでは厳格なテスト駆動開発を必須とします。すべての機能実装はTDDサイクルに従って行ってください。**

## 🔴 TDDの厳格な遵守

### 必須ルール
1. **テストファースト**: 実装コードを書く前に必ずテストを書く
2. **失敗確認**: テストが失敗することを確認してから実装開始
3. **最小実装**: テストを通すための最小限の実装のみ
4. **リファクタリング必須**: 実装後は必ずコードの改善を行う
5. **完全テスト**: 全テストが通ることを確認してから完了

### TDDサイクル（厳格版）
```
1. 🔴 RED: 失敗するテストを書く
   ├── 要件を理解してテストケースを設計
   ├── テストを実装（まだ機能は存在しない）
   └── テストが失敗することを確認
   
2. 🟢 GREEN: テストを通すための最小実装
   ├── テストを通すための最小限のコードを書く
   ├── 美しさや効率は無視、とにかく通す
   └── テストが通ることを確認
   
3. 🔵 REFACTOR: コードの改善
   ├── 重複の除去
   ├── 意図の明確化
   ├── パフォーマンスの改善
   └── すべてのテストが引き続き通ることを確認

4. 🔍 QUALITY CHECK: 品質確認
   ├── エラーハンドリングの追加
   ├── エッジケースのテスト追加
   ├── セキュリティチェック
   └── ドキュメント更新
```

## 🧪 機能実装の必須手順

### 新機能開発プロセス
```bash
# === STEP 1: テスト設計 ===
# 1. 要件を理解し、テストケースを設計
# 2. test_*.py ファイルに失敗するテストを作成

# === STEP 2: RED フェーズ ===
# 3. テストが失敗することを確認
python3 manage.py test path.to.your.TestCase.test_method_name -v 2

# === STEP 3: GREEN フェーズ ===
# 4. 最小実装でテストを通す
# 5. テストが通ることを確認
python3 manage.py test path.to.your.TestCase.test_method_name -v 2

# === STEP 4: REFACTOR フェーズ ===
# 6. コードの改善とリファクタリング
# 7. 全テストが通ることを確認
python3 manage.py test

# === STEP 5: 統合確認 ===
# 8. 統合テストの実行
python3 test_complete_suite.py

# === STEP 6: 品質確認 ===
# 9. カバレッジ確認
python3 test_runner.py --coverage

# 10. リンティングとセキュリティチェック
python3 test_runner.py --lint --security
```

## 📋 テストケース設計の必須項目

### APIエンドポイントのテストパターン（完全版）
```python
class NewFeatureTestCase(APITestCase):
    """新機能のテストケース - TDD完全版"""
    
    def setUp(self):
        """テストデータの準備"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_endpoint_success_case(self):
        """正常系: 成功ケースのテスト"""
        response = self.client.post('/api/new-endpoint/', {
            'required_field': 'valid_value'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
    
    def test_endpoint_authentication_required(self):
        """認証: 未認証でのアクセス拒否"""
        self.client.logout()
        response = self.client.post('/api/new-endpoint/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_endpoint_permission_denied(self):
        """認可: 権限なしでのアクセス拒否"""
        other_user = User.objects.create_user('other', 'pass')
        self.client.force_authenticate(user=other_user)
        response = self.client.post('/api/new-endpoint/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_endpoint_validation_errors(self):
        """バリデーション: 不正データでのエラー"""
        response = self.client.post('/api/new-endpoint/', {
            'required_field': ''  # 空文字
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('required_field', response.data)
    
    def test_endpoint_edge_cases(self):
        """エッジケース: 境界値のテスト"""
        # 最大値、最小値、特殊文字等
        pass
    
    def test_endpoint_error_handling(self):
        """エラーハンドリング: 異常系のテスト"""
        # 存在しないIDアクセス等
        pass
```

### モデルテストの必須項目
```python
class ModelTestCase(TestCase):
    """モデルテストの完全版"""
    
    def test_model_creation_success(self):
        """正常系: モデル作成成功"""
        pass
    
    def test_model_validation_errors(self):
        """バリデーション: フィールド制約エラー"""
        pass
    
    def test_model_str_representation(self):
        """__str__メソッドのテスト"""
        pass
    
    def test_model_custom_methods(self):
        """カスタムメソッドのテスト"""
        pass
    
    def test_model_relationships(self):
        """リレーションシップのテスト"""
        pass
```

## 🚫 TDD違反時の対応

### 禁止事項
- ❌ テストなしでの実装コード作成
- ❌ テスト失敗確認なしでの開発開始
- ❌ リファクタリングフェーズのスキップ
- ❌ エラーハンドリングの後回し
- ❌ テストカバレッジの無視

### TDD違反を発見した場合の対応
1. **即座に実装を停止**
2. **不足しているテストを作成**
3. **既存実装をテストケースで検証**
4. **必要に応じてリファクタリング実施**
5. **全テストが通ることを確認**

## 📊 品質ゲートの設定

### 完了条件
機能実装は以下の条件をすべて満たした場合のみ完了とする：

✅ **テストカバレッジ**: 新規コードは100%カバレッジ  
✅ **テスト成功**: 全テストが成功  
✅ **リンティング**: コード品質チェック通過  
✅ **セキュリティ**: セキュリティチェック通過  
✅ **統合テスト**: エンドツーエンドテスト成功  
✅ **エラーハンドリング**: 異常系のテスト完備  
✅ **ドキュメント**: 実装内容の文書化完了  

### 品質確認コマンド
```bash
# 完了前の必須チェックリスト
python3 manage.py test                    # 全テスト実行
python3 test_runner.py --coverage        # カバレッジ確認
python3 test_runner.py --lint            # リンティング
python3 test_runner.py --security        # セキュリティチェック
python3 test_complete_suite.py           # 統合テスト
```

## 🚀 TDD駆動による開発フロー

**すべての作業は以下のTDDフローに従って実行してください**

### 必須作業フロー
```
📋 1. 要件理解 → 🔴 2. テスト作成 → ❌ 3. 失敗確認 → 
🟢 4. 最小実装 → ✅ 5. テスト成功 → 🔵 6. リファクタリング → 
🔍 7. 品質確認 → 📝 8. ドキュメント → 🎉 9. 完了報告
```

### 1. 📋 要件理解フェーズ
- **機能要件の明確化**: 何を実装するかを正確に理解
- **受け入れ条件の定義**: 完了条件を明確に設定
- **テストケースの設計**: 正常系・異常系・エッジケースを設計

### 2. 🔴 RED フェーズ（テスト作成）
- **テストファイルの作成**: 適切な `test_*.py` ファイルに実装
- **失敗するテストの作成**: 機能が存在しない状態でのテスト
- **テスト実行**: 必ず失敗することを確認

### 3. 🟢 GREEN フェーズ（最小実装）
- **最小限の実装**: テストを通すための最低限のコード
- **美しさは無視**: まずは動作することを最優先
- **テスト成功確認**: 作成したテストが通ることを確認

### 4. 🔵 REFACTOR フェーズ（改善）
- **コードの改善**: 重複排除、可読性向上、パフォーマンス改善
- **設計の改善**: SOLID原則に従った設計の見直し
- **全テスト実行**: リファクタリング後も全テストが通ることを確認

### 5. 🔍 QUALITY CHECK フェーズ（品質確認）
- **エラーハンドリング**: 異常系への対処を追加
- **セキュリティチェック**: 脆弱性の確認と対策
- **パフォーマンステスト**: 必要に応じて性能テストを実施
- **カバレッジ確認**: 新規コードの100%カバレッジを確認

## 📊 品質ゲートチェックリスト

### 機能完了の必須条件
各機能の実装完了前に以下を必ずチェック：

```bash
# ✅ チェックリスト実行コマンド
python3 manage.py test                           # 全テスト成功
python3 test_runner.py --coverage               # カバレッジ100%
python3 test_runner.py --lint                   # リンティング合格
python3 test_runner.py --security               # セキュリティチェック合格
python3 test_complete_suite.py                  # 統合テスト成功
```

### TDD違反の即座対応
以下を発見した場合は即座に作業を停止し、修正：
- ❌ テストなしの実装コード
- ❌ 失敗しないテスト
- ❌ カバレッジ不足
- ❌ エラーハンドリング不備
- ❌ セキュリティ脆弱性

## 📝 結果報告の必須項目

### 完了報告テンプレート
```markdown
## 🎯 実装完了報告

### 📋 実装概要
- **機能名**: [実装した機能]
- **TDDサイクル**: 完了 (RED → GREEN → REFACTOR → QUALITY CHECK)
- **テストケース数**: [作成したテスト数]

### ✅ 品質確認結果
- **テスト成功**: ✅ 全 [X] 件成功
- **カバレッジ**: ✅ [XX]% (新規コード100%)
- **リンティング**: ✅ 合格
- **セキュリティ**: ✅ 脆弱性なし
- **統合テスト**: ✅ 成功

### 🔧 実装詳細
[実装内容の説明]

### 🧪 テストケース
[テストケースの説明]

### 📚 関連ドキュメント
[更新した仕様書やドキュメント]
```

## 🧪 テスト構造

### ディレクトリ構成
```
tests/
├── unit/           # 単体テスト（個別の関数、クラス、モデル）
├── integration/    # 統合テスト（複数コンポーネントの連携）
├── system/         # システムテスト（エンドツーエンド）
├── ui/            # UIテスト（画面表示、ナビゲーション）
├── performance/    # パフォーマンステスト（負荷、速度）
├── utils/         # テストユーティリティ（ランナー、ヘルパー）
└── results/       # テスト結果、レポート、ログファイル
```

### テスト実行方法
```bash
# カテゴリ別実行
python3 manage.py test tests.unit          # 単体テストのみ（高速）
python3 manage.py test tests.integration   # 統合テスト
python3 manage.py test tests.system        # システムテスト
python3 manage.py test tests.ui            # UIテスト

# 全カテゴリ順次実行
python3 tests/utils/run_all_tests.py

# カバレッジ付き実行
python3 tests/utils/test_runner.py --coverage

# 結果を保存
python3 manage.py test --verbosity=2 | tee tests/results/test_$(date +%Y%m%d_%H%M%S).log
```

### テスト作成ガイドライン
1. **配置場所の決定**
   - 単一機能のテスト → `tests/unit/`
   - 複数機能の連携テスト → `tests/integration/`
   - ユーザーシナリオテスト → `tests/system/`
   - 画面・UI関連テスト → `tests/ui/`

2. **命名規則**
   - 単体: `test_<feature>_unit.py`
   - 統合: `test_<feature>_integration.py`
   - システム: `test_<feature>_system.py`
   - UI: `test_<feature>_ui.py`

3. **テスト品質基準**
   - 独立性: 他のテストに依存しない
   - 冪等性: 何度実行しても同じ結果
   - 明確性: わかりやすいアサーションとメッセージ
   - 完全性: セットアップとクリーンアップを含む

### テスト結果の管理
- 結果ファイルは `tests/results/` に保存
- 実行ログは日付付きで保存
- 統合テストの詳細レポートを保持

## 🗂️ テストデータの整理方針

### テストデータ作成方法（正式版のみ使用）
```bash
# ✅ 推奨：Django管理コマンドを使用
python3 manage.py create_test_data          # 総合的なテストデータ作成
python3 manage.py create_test_characters    # キャラクターテストデータ作成
python3 manage.py create_sample_data        # サンプルデータ作成

# ❌ 削除済み：ルートディレクトリのスクリプト
# create_test_characters.py（2025-06-26削除）
# create_sample_characters.py（2025-06-26削除）
# create_investigator_history_data.py（2025-06-26削除）
```

### テストデータファイルの配置
```
iaia/
├── accounts/management/commands/    # ✅ 正式な配置場所
│   ├── create_test_data.py         # 総合テストデータ作成
│   ├── create_test_characters.py   # キャラクター専用
│   └── create_sample_data.py       # サンプルデータ作成
├── schedules/management/commands/
│   └── create_session_test_data.py # セッション専用
├── check_test_data.py              # データ確認用ユーティリティ
├── TEST_DATA_README.md             # テストユーザー情報
└── TEST_DATA_MANAGEMENT.md         # このガイドの詳細版
```

### テストデータ管理ルール
1. **新規作成時**: 必ずDjango管理コマンドとして実装
2. **重複禁止**: 同じ機能のスクリプトを複数作成しない
3. **配置場所**: `{app}/management/commands/` に配置
4. **命名規則**: `create_test_{機能名}.py` 形式を使用
5. **削除方針**: 重複・古いスクリプトは削除（履歴はGitで管理）

### テストデータのクリーンアップ
```bash
# データベース内のテストデータをクリア
python3 manage.py create_sample_data --clear

# テストデータの確認
python3 check_test_data.py
```

## 🔒 セキュリティとエラーハンドリング

### 必須セキュリティチェック
- **入力検証**: すべての入力値の検証
- **認証・認可**: 適切なアクセス制御
- **SQLインジェクション**: ORM使用の確認
- **XSS対策**: 出力エスケープの確認
- **CSRF対策**: CSRFトークンの実装

### エラーハンドリングパターン
```python
# 必須エラーハンドリングパターン
try:
    # 処理実装
    result = perform_operation()
    return SuccessResponse(result)
except ValidationError as e:
    return ErrorResponse(status=400, message="入力値エラー", details=e.details)
except PermissionError as e:
    return ErrorResponse(status=403, message="権限エラー")
except Exception as e:
    logger.error(f"予期しないエラー: {e}")
    return ErrorResponse(status=500, message="システムエラーが発生しました")
```

## E2Eテスト (Playwright)

### TDDフローへの統合

E2EテストもTDDサイクルに組み込みます：

1. **🔴 RED**: E2Eテストを先に作成（UI操作のシナリオ）
2. **🟢 GREEN**: 機能を実装してE2Eテストを通す
3. **🔵 REFACTOR**: UIとコードを改善
4. **🔍 QUALITY**: クロスブラウザテストで品質確認

### E2Eテスト実行コマンド
```bash
# 全E2Eテスト実行
npx playwright test

# 特定のテストファイル実行
npx playwright test tests/e2e/character.spec.ts

# デバッグモードで実行
npx playwright test --debug

# ヘッドレスモードを無効化（ブラウザを表示）
npx playwright test --headed

# テストレポート表示
npx playwright show-report
```

詳細は [E2Eテストセットアップ](../E2E_TEST_SETUP.md) を参照してください。