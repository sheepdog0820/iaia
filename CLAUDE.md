# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリで作業する際のガイダンスを提供します。

## 重要な制限事項

### キャラクターシート機能の対象システム

**このプロジェクトのキャラクターシート機能は、クトゥルフ神話TRPG 6版・7版専用です。**

- ✅ **対応システム**: クトゥルフ神話TRPG 6版、7版のみ
- ❌ **非対応システム**: D&D、ソード・ワールド、インセイン、その他のTRPGシステム

#### 実装制限の理由
1. **システム固有の複雑性**: 各TRPGシステムには独自のルール、能力値計算、技能体系があり、汎用的な実装は困難
2. **6版・7版の特化設計**: 現在のモデル構造は6版・7版の仕様に最適化されている
3. **開発効率**: 特定システムに集中することで、高品質な機能を提供

#### 新しいTRPGシステムの要求について
他のTRPGシステム（D&D、ソード・ワールド等）のキャラクターシート機能を要求された場合：
- **理由を説明**: 上記の制限事項を伝える
- **代替案の提示**: シナリオ管理機能での対応を提案
- **実装拒否**: 「申し訳ございませんが、キャラクターシート機能はクトゥルフ神話TRPG専用です」と回答

#### 許可される作業範囲
- クトゥルフ神話TRPG 6版・7版のキャラクターシート機能の改善・修正
- 6版・7版間の機能差の実装・調整
- キャラクターシート関連のバグ修正
- プレイ履歴・統計機能の改善（クトゥルフ以外のシステムも対象）

## コマンド集

### 開発環境セットアップ
```bash
# 仮想環境の作成と有効化
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt

# データベースセットアップ
python3 manage.py migrate

# スーパーユーザー作成（自動化済み）
python3 create_admin.py  # ユーザー名: admin, パスワード: arkham_admin_2024

# サンプルデータ生成
python3 manage.py create_sample_data

# 開発サーバー起動
python3 manage.py runserver
```

### テストコマンド
```bash
# 全テスト実行
python3 manage.py test

# 特定のテストモジュール実行
python3 manage.py test accounts.test_authentication
python3 manage.py test schedules.test_schedules
python3 manage.py test scenarios.test_scenarios

# 統合テストのみ実行
python3 test_runner_comprehensive.py --integration-only

# カテゴリ別テストスイート実行
python3 test_complete_suite.py              # 全テスト
python3 test_complete_suite.py integration  # 統合テストのみ
python3 test_complete_suite.py system       # システム統合テストのみ
python3 test_complete_suite.py additional   # 追加機能テストのみ
python3 test_complete_suite.py individual   # 個別モジュールテストのみ

# カバレッジ付きテスト実行
python3 test_runner.py --coverage

# 特定テストを詳細出力で実行
python3 manage.py test test_integration.UserGroupIntegrationTestCase -v 2

# テストDB保持（デバッグ用）
python3 manage.py test --keepdb
```

### リンティングと品質チェック
```bash
# 全チェック実行（テスト + カバレッジ + リント + セキュリティ）
python3 test_runner.py --all

# リンティングのみ
python3 test_runner.py --lint

# セキュリティチェック
python3 test_runner.py --security

# 高速テスト実行（failfast）
python3 test_runner.py --fast
```

### データベース管理
```bash
# モデル変更後のマイグレーション作成
python3 manage.py makemigrations

# マイグレーション適用
python3 manage.py migrate

# データベースリセット（開発環境のみ）
rm db.sqlite3
python3 manage.py migrate
python3 manage.py create_sample_data

# データベースシェルアクセス
python3 manage.py dbshell
```

### 静的ファイル管理
```bash
# 静的ファイル収集
python3 manage.py collectstatic --noinput

# クリアして静的ファイル収集
python3 manage.py collectstatic --noinput --clear
```

## アーキテクチャ概要

### 主要Djangoアプリ構造

プロジェクトは3つの主要アプリでドメイン駆動設計を採用：

1. **accounts/** - ユーザー管理と認証
   - TRPG固有フィールド付きカスタムUserモデル（ニックネーム、プレイ履歴）
   - 可視性制御付きグループ管理（public/private）
   - ソーシャル接続用フレンドシステム
   - django-allauthによるソーシャル認証統合（Google/Twitter）
   - 統計・エクスポート機能（部分実装）

2. **schedules/** - セッションとスケジュール管理
   - ステータス追跡付きTRPGSessionモデル
   - キャラクターシート付きSessionParticipant
   - 秘匿/公開情報配布用HandoutInfo
   - カレンダー統合（APIエンドポイント未実装）

3. **scenarios/** - ゲームシナリオ管理
   - フィルタリング機能付きシナリオリポジトリ
   - ユーザー統計用PlayHistory追跡
   - GM用ScenarioNote（公開/非公開設定）

### APIアーキテクチャ

全APIはDjango REST Frameworkで一貫したパターンを使用：

- **認証**: 全エンドポイントで`IsAuthenticated`権限必須
- **ViewSets**: カスタムアクション付き標準ModelViewSet
- **Serializers**: 関連データのネストシリアライゼーション
- **権限**: `get_object()`メソッドでのカスタム権限チェック

主要APIパターン：
```python
# グループ可視性チェック (accounts/views.py)
def get_object(self):
    obj = super().get_object()
    if obj.visibility == 'public' or obj.members.filter(id=self.request.user.id).exists():
        return obj
    raise Http404("Group not found")

# 作成時の自動ユーザー設定 (scenarios/views.py)
def perform_create(self, serializer):
    serializer.save(user=self.request.user)
```

### 権限モデル

階層的な権限モデルを使用：

1. **グループ可視性**:
   - `private`: メンバーのみ閲覧/アクセス可能
   - `public`: 認証済みユーザーなら誰でも閲覧可能、参加に招待不要

2. **グループロール**:
   - `admin`: グループ管理、メンバー招待、設定編集が可能
   - `member`: グループコンテンツ閲覧、セッション参加が可能

3. **ハンドアウト可視性**:
   - `is_secret=True`: 受信者とGMのみ閲覧可能
   - `is_secret=False`: 全セッション参加者が閲覧可能

### テストアーキテクチャ

テストは複数カテゴリに整理：

- **ユニットテスト**: 各アプリの`test_*.py`ファイル
- **統合テスト**: `test_integration.py`、`test_system_integration.py`
- **追加機能テスト**: `test_additional_features.py`
- **テストランナー**: 異なるテストシナリオ用カスタムランナー

## 課題管理

すべての課題とチケットは `ISSUES.md` ファイルで管理されています。
新しい課題を発見した場合は、ISSUES.mdファイルに適切な優先度とカテゴリで追加してください。

## 【重要】テスト駆動開発（TDD）の徹底

**このプロジェクトでは厳格なテスト駆動開発を必須とします。すべての機能実装はTDDサイクルに従って行ってください。**

### 🔴 TDDの厳格な遵守

#### 必須ルール
1. **テストファースト**: 実装コードを書く前に必ずテストを書く
2. **失敗確認**: テストが失敗することを確認してから実装開始
3. **最小実装**: テストを通すための最小限の実装のみ
4. **リファクタリング必須**: 実装後は必ずコードの改善を行う
5. **完全テスト**: 全テストが通ることを確認してから完了

#### TDDサイクル（厳格版）
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

### 🧪 機能実装の必須手順

#### 新機能開発プロセス
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

### 📋 テストケース設計の必須項目

#### APIエンドポイントのテストパターン（完全版）
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

#### モデルテストの必須項目
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

### 🚫 TDD違反時の対応

#### 禁止事項
- ❌ テストなしでの実装コード作成
- ❌ テスト失敗確認なしでの開発開始
- ❌ リファクタリングフェーズのスキップ
- ❌ エラーハンドリングの後回し
- ❌ テストカバレッジの無視

#### TDD違反を発見した場合の対応
1. **即座に実装を停止**
2. **不足しているテストを作成**
3. **既存実装をテストケースで検証**
4. **必要に応じてリファクタリング実施**
5. **全テストが通ることを確認**

### 📊 品質ゲートの設定

#### 完了条件
機能実装は以下の条件をすべて満たした場合のみ完了とする：

✅ **テストカバレッジ**: 新規コードは100%カバレッジ  
✅ **テスト成功**: 全テストが成功  
✅ **リンティング**: コード品質チェック通過  
✅ **セキュリティ**: セキュリティチェック通過  
✅ **統合テスト**: エンドツーエンドテスト成功  
✅ **エラーハンドリング**: 異常系のテスト完備  
✅ **ドキュメント**: 実装内容の文書化完了  

#### 品質確認コマンド
```bash
# 完了前の必須チェックリスト
python3 manage.py test                    # 全テスト実行
python3 test_runner.py --coverage        # カバレッジ確認
python3 test_runner.py --lint            # リンティング
python3 test_runner.py --security        # セキュリティチェック
python3 test_complete_suite.py           # 統合テスト
```

## 環境設定

必要な環境変数（`.env.example`参照）：
- `SECRET_KEY`: Djangoシークレットキー
- `DEBUG`: デバッグモードフラグ
- `ALLOWED_HOSTS`: 許可ホストのカンマ区切りリスト
- `GOOGLE_CLIENT_ID/SECRET`: Google OAuth用
- `TWITTER_CLIENT_ID/SECRET`: Twitter OAuth用

## データベーススキーマの主要リレーション

```
CustomUser
  ↓ created_by
  Group ←→ GroupMembership ←→ CustomUser
  ↓ group                     ↓ gm
  TRPGSession ←→ SessionParticipant ←→ CustomUser
      ↓                         ↓
  HandoutInfo              PlayHistory → Scenario
                                      ← ScenarioNote
```

## 現在のテスト状況

統合テスト成功率: 100% (16/16) ✅
- 動作確認済み: 認証、セッション、シナリオ、グループ管理
- ✅ グループ管理機能 (Cult Circle) 完全動作
- ✅ 全てのAPIエンドポイント正常動作

## 【必須】作業方針とガイドライン

### 🚀 TDD駆動による開発フロー

**すべての作業は以下のTDDフローに従って実行してください**

#### 必須作業フロー
```
📋 1. 要件理解 → 🔴 2. テスト作成 → ❌ 3. 失敗確認 → 
🟢 4. 最小実装 → ✅ 5. テスト成功 → 🔵 6. リファクタリング → 
🔍 7. 品質確認 → 📝 8. ドキュメント → 🎉 9. 完了報告
```

#### 1. 📋 要件理解フェーズ
- **機能要件の明確化**: 何を実装するかを正確に理解
- **受け入れ条件の定義**: 完了条件を明確に設定
- **テストケースの設計**: 正常系・異常系・エッジケースを設計

#### 2. 🔴 RED フェーズ（テスト作成）
- **テストファイルの作成**: 適切な `test_*.py` ファイルに実装
- **失敗するテストの作成**: 機能が存在しない状態でのテスト
- **テスト実行**: 必ず失敗することを確認

#### 3. 🟢 GREEN フェーズ（最小実装）
- **最小限の実装**: テストを通すための最低限のコード
- **美しさは無視**: まずは動作することを最優先
- **テスト成功確認**: 作成したテストが通ることを確認

#### 4. 🔵 REFACTOR フェーズ（改善）
- **コードの改善**: 重複排除、可読性向上、パフォーマンス改善
- **設計の改善**: SOLID原則に従った設計の見直し
- **全テスト実行**: リファクタリング後も全テストが通ることを確認

#### 5. 🔍 QUALITY CHECK フェーズ（品質確認）
- **エラーハンドリング**: 異常系への対処を追加
- **セキュリティチェック**: 脆弱性の確認と対策
- **パフォーマンステスト**: 必要に応じて性能テストを実施
- **カバレッジ確認**: 新規コードの100%カバレッジを確認

### 📊 品質ゲートチェックリスト

#### 機能完了の必須条件
各機能の実装完了前に以下を必ずチェック：

```bash
# ✅ チェックリスト実行コマンド
python3 manage.py test                           # 全テスト成功
python3 test_runner.py --coverage               # カバレッジ100%
python3 test_runner.py --lint                   # リンティング合格
python3 test_runner.py --security               # セキュリティチェック合格
python3 test_complete_suite.py                  # 統合テスト成功
```

#### TDD違反の即座対応
以下を発見した場合は即座に作業を停止し、修正：
- ❌ テストなしの実装コード
- ❌ 失敗しないテスト
- ❌ カバレッジ不足
- ❌ エラーハンドリング不備
- ❌ セキュリティ脆弱性

### 📝 結果報告の必須項目

#### 完了報告テンプレート
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

### 🎯 キャラクターシート作業時のTDD手順

#### クトゥルフ神話TRPG専用開発プロセス
1. **📋 仕様確認**: 該当版の仕様書を必ず確認
   - 6版: `CHARACTER_SHEET_6TH_EDITION.md`
   - 7版: `CHARACTER_SHEET_7TH_EDITION.md`

2. **🔴 ルール準拠テスト**: 版別ルールのテストを作成
   - 能力値範囲テスト
   - 計算式テスト
   - バリデーションテスト

3. **🟢 ルール実装**: クトゥルフルールの正確な実装
   - 6版: 3D6（3-18）、×5計算なし
   - 7版: 3D6×5（15-90）、パーセンテージベース

4. **🔵 精度向上**: 計算精度とユーザビリティの改善

5. **🔍 ルール検証**: 公式ルールとの整合性確認

### 🔒 セキュリティとエラーハンドリング

#### 必須セキュリティチェック
- **入力検証**: すべての入力値の検証
- **認証・認可**: 適切なアクセス制御
- **SQLインジェクション**: ORM使用の確認
- **XSS対策**: 出力エスケープの確認
- **CSRF対策**: CSRFトークンの実装

#### エラーハンドリングパターン
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

## 作業完了時の通知設定

### 音声通知コマンド (Linux/WSL)
```bash
# 作業完了時に音を鳴らす
# 基本的なビープ音
echo -e "\a"

# システム音を再生 (pulseaudio利用)
paplay /usr/share/sounds/alsa/Front_Left.wav 2>/dev/null || echo -e "\a"

# 複数回ビープ音
for i in {1..3}; do echo -e "\a"; sleep 0.5; done

# エレガントな完了音（音楽的）
(speaker-test -t sine -f 1000 -l 1 & sleep 0.1s; kill -9 $!) 2>/dev/null || echo -e "\a"
```

### PowerShell用コマンド (Windows)
```powershell
# Windows PowerShellでのビープ音
[console]::beep(800,500)

# 複数音での完了通知
[console]::beep(523,200); [console]::beep(659,200); [console]::beep(784,400)

# システム音を再生
(New-Object Media.SoundPlayer "C:\Windows\Media\chimes.wav").PlaySync()
```

### TDD完了時の音声通知例
```bash
# TDD完全サイクル完了通知
python3 manage.py test && \
python3 test_runner.py --coverage && \
python3 test_runner.py --lint && \
python3 test_runner.py --security && \
python3 test_complete_suite.py && \
echo "🎉 TDD完全サイクル完了!" && \
for i in {1..5}; do echo -e "\a"; sleep 0.3; done

# 品質ゲート通過通知
echo "✅ 品質ゲート通過 - 実装完了!" && echo -e "\a\a\a"

# Arkham Nexus機能完全実装通知
echo "🐙 クトゥルフ神話TRPG機能実装完了!" && \
for i in {1..3}; do echo -e "\a"; sleep 0.5; done
```

### Claude Code TDD作業完了通知の使用方法
TDDサイクルが完了したときに、品質確認と共に以下を実行：
```bash
# TDD RED-GREEN-REFACTOR-QUALITY完了通知
echo "🔴🟢🔵🔍 TDDサイクル完了: [機能名]" && echo -e "\a\a\a"

# 品質ゲート全通過通知
echo "✅ 品質ゲート全通過 - [機能名]実装完了!" && echo -e "\a\a\a"

# クトゥルフ専用機能完了通知
echo "🐙 クトゥルフ神話TRPG機能TDD完了: [機能名]" && echo -e "\a\a\a"
```

### キャラクターシート関連ファイル一覧（クトゥルフ神話TRPG専用）
```
CHARACTER_SHEET_6TH_EDITION.md     # 6版仕様書
CHARACTER_SHEET_7TH_EDITION.md     # 7版仕様書
CHARACTER_SHEET_SPECIFICATION.md   # 共通仕様
CHARACTER_SHEET_TECHNICAL_SPEC.md  # 技術仕様
templates/accounts/character_sheet_6th.html   # 6版テンプレート
templates/accounts/character_sheet_7th.html   # 7版テンプレート
```

**注意**: これらのファイルはすべてクトゥルフ神話TRPG 6版・7版の仕様に基づいています。
他のTRPGシステム用のキャラクターシート機能は実装しません。

## JavaScriptコード修正時の注意事項

### DOM要素アクセス時の安全性確保

JavaScriptでDOM要素にアクセスする際は、以下の点に注意してください：

1. **要素の存在確認**
   ```javascript
   // 悪い例 - 要素が存在しない場合エラーになる
   document.getElementById('some-id').textContent = 'value';
   
   // 良い例 - 要素の存在を確認
   const element = document.getElementById('some-id');
   if (element) {
       element.textContent = 'value';
   }
   
   // または オプショナルチェーンを使用
   document.getElementById('some-id')?.textContent = 'value';
   ```

2. **input要素の値取得/設定**
   ```javascript
   // input要素の場合は value プロパティを使用
   const inputElement = document.getElementById('input-id');
   if (inputElement) {
       inputElement.value = '123';  // textContent ではなく value を使用
   }
   
   // 読み取り時も同様
   const value = document.getElementById('input-id')?.value || '0';
   ```

3. **関数の存在確認**
   ```javascript
   // 関数を呼び出す前に定義されているか確認
   if (typeof someFunction === 'function') {
       someFunction();
   }
   
   // または try-catch を使用
   try {
       someFunction();
   } catch (error) {
       console.error('関数が存在しません:', error);
   }
   ```

4. **イベントリスナー登録時の要素確認**
   ```javascript
   const button = document.getElementById('button-id');
   if (button) {
       button.addEventListener('click', handleClick);
   }
   ```

### エラーハンドリングのベストプラクティス

1. **try-catch の活用**
   ```javascript
   try {
       // リスクのある処理
       const data = JSON.parse(jsonString);
   } catch (error) {
       console.error('JSONパースエラー:', error);
       // 適切なフォールバック処理
   }
   ```

2. **デフォルト値の設定**
   ```javascript
   // parseInt の結果が NaN の場合に備える
   const value = parseInt(element?.value) || 0;
   
   // textContent が null の場合
   const text = element?.textContent || '';
   ```

3. **配列やオブジェクトの安全なアクセス**
   ```javascript
   // 配列の場合
   const firstItem = array?.[0] || defaultValue;
   
   // オブジェクトの場合
   const value = object?.property?.nestedProperty || defaultValue;
   ```

### 修正時のチェックリスト

- [ ] HTMLに該当するIDの要素が存在するか確認
- [ ] input要素は`value`、その他の要素は`textContent`を使用しているか
- [ ] 要素が存在しない場合のエラーハンドリングがあるか
- [ ] 関数呼び出し前に関数が定義されているか確認
- [ ] イベントリスナー登録時に要素の存在確認をしているか
- [ ] 数値変換時のNaN対策（デフォルト値）があるか