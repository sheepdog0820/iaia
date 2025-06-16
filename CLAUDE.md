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

## 6版ダイスロール設定仕様

### 動的ダイス設定システム

**6版キャラクター作成では、各能力値のダイス設定を動的に変更可能です。**

#### 基本仕様
- **対象能力値**: STR, CON, POW, DEX, APP, SIZ, INT, EDU（全8つ）
- **設定項目**: ダイス数（1-10）、ダイス面数（2-100）、ボーナス値（-50〜+50）
- **初期値**: 6版標準ルール（STR:3D6, SIZ:2D6+6, INT:2D6+6, EDU:3D6+3等）
- **変更可能**: ユーザーがリアルタイムで任意の値に変更可能

#### 実装要件
1. **動的計算**: ダイス設定変更時に即座にダイスロール計算ロジックに反映
2. **固定値禁止**: ハードコードされた固定値は使用しない
3. **設定永続化**: ユーザーの設定は名前付きで保存・管理可能
4. **リアルタイム更新**: 設定変更時に画面表示も即座に更新

#### ダイス計算ロジック
```javascript
// 動的なダイス計算関数（固定値使用禁止）
function rollAbility(abilityName) {
    const count = getDiceCount(abilityName);  // 動的取得
    const sides = getDiceSides(abilityName);  // 動的取得  
    const bonus = getDiceBonus(abilityName);  // 動的取得
    
    let total = 0;
    for (let i = 0; i < count; i++) {
        total += Math.floor(Math.random() * sides) + 1;
    }
    return total + bonus;
}
```

#### 標準プリセット値
- **STR (筋力)**: 3D6+0
- **CON (体力)**: 3D6+0  
- **POW (精神力)**: 3D6+0
- **DEX (敏捷性)**: 3D6+0
- **APP (外見)**: 3D6+0
- **SIZ (体格)**: 2D6+6
- **INT (知識)**: 2D6+6
- **EDU (教育)**: 3D6+3

#### 高能力値プリセット値
- **STR**: 4D6-3 (4D6の最良3個相当)
- **CON**: 4D6-3
- **POW**: 4D6-3
- **DEX**: 4D6-3
- **APP**: 4D6-3
- **SIZ**: 3D6+3
- **INT**: 3D6+3
- **EDU**: 4D6+0

#### 禁止事項
- ❌ ハードコードされた固定ダイス値の使用
- ❌ 設定無視した決め打ちダイス計算
- ❌ 設定変更が反映されない実装
- ❌ リアルタイム更新されないUI

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

## 【重要】画面リファクタリング・大規模変更の注意事項

### 🚨 画面リファクタリング時の必須ルール

**UI/UXの大幅な変更や画面構造の変更時は、以下のルールを厳格に遵守してください**

#### ❌ 禁止事項：大規模変更の一括実行
- **アコーディオン・タブ構造の一括変換禁止**: HTMLの基本構造を大幅に変更する際は段階的に実行
- **複数セクションの同時変換禁止**: カード→アコーディオンなどの変換は1セクションずつ実行
- **テンプレートファイルの完全書き換え禁止**: 既存の動作するコードを一度に大量変更しない
- **git restore なしでの強行禁止**: バックアップなしでの大規模変更は禁止

#### ✅ 推奨事項：段階的改善アプローチ
1. **最小限改善ファースト**: フッター余白、必須マーカーなど小さな改善から開始
2. **動作確認必須**: 各変更後に必ず画面表示とJavaScript動作を確認
3. **git commit 分割**: 機能ごとに細かくcommitし、問題時に部分的restore可能にする
4. **バックアップ作成**: 大規模変更前に必ずgit branchまたは手動バックアップを作成
5. **段階的実装**: 1つのセクション変更→動作確認→次のセクション変更

#### 🔄 画面リファクタリングの正しい手順
```bash
# STEP 1: バックアップ作成
git branch backup-before-refactor
git add . && git commit -m "リファクタリング開始前のバックアップ"

# STEP 2: 最小限改善から開始
# フッター余白、必須マーカー、レスポンシブ調整など

# STEP 3: 動作確認
# ブラウザで画面表示とJavaScript動作を確認

# STEP 4: 段階的変更
# 1セクションずつアコーディオン化やUI変更

# STEP 5: 各段階でcommit
git add . && git commit -m "セクション1: アコーディオン化完了"

# STEP 6: 問題発生時の即座復旧
git restore <problematic-file>  # または
git reset --hard backup-before-refactor
```

#### 🚫 失敗パターンと回避策

**失敗パターン1: HTMLの完全書き換え**
```html
<!-- ❌ 悪い例: 既存の複雑な構造を一括変換 -->
<!-- 全てのカードを一度にアコーディオンに変換 -->
```
**回避策**: 1つのカードをアコーディオンに変換→動作確認→次のカード変換

**失敗パターン2: JavaScript構造の大幅変更**
```javascript
// ❌ 悪い例: 既存のイベントリスナーを大量削除・変更
// onclick属性を一括でaddEventListenerに変換
```
**回避策**: 既存のJavaScriptが動作する状態を維持し、段階的に改善

**失敗パターン3: CSS構造の完全刷新**
```css
/* ❌ 悪い例: 既存のスタイルを大量削除・変更 */
/* Bootstrap classを独自CSSで完全置換 */
```
**回避策**: 既存スタイルを保持し、追加・改善のみ実行

#### 🛡️ 緊急復旧手順
画面が表示されない・JavaScript エラーが発生した場合：

```bash
# 1. 即座に元のファイルを復元
git restore <broken-file>

# 2. サーバー再起動
python3 manage.py runserver

# 3. 動作確認
# ブラウザで画面表示を確認

# 4. 最小限の改善のみ再実装
# フッター余白、必須マーカーなど安全な変更のみ

# 5. 段階的再挑戦
# 1セクションずつ慎重に変更
```

#### 📋 画面リファクタリング チェックリスト
**変更前チェック**
- [ ] git状態確認（未コミット変更の有無）
- [ ] バックアップブランチ作成
- [ ] 現在の画面表示・JavaScript動作確認
- [ ] 変更対象セクションの明確化（1セクションのみ）

**変更中チェック**
- [ ] HTMLタグの開始・終了の整合性確認
- [ ] JavaScript関数の重複・削除の有無確認
- [ ] CSSクラスの衝突・削除の有無確認
- [ ] 各変更後の動作確認実行

**変更後チェック**
- [ ] ブラウザでの画面表示確認
- [ ] JavaScript console エラーの有無確認
- [ ] モバイル・デスクトップでの表示確認
- [ ] 全機能の動作確認（ダイスロール、フォーム送信等）
- [ ] git commit で変更を保存

#### 🎯 成功のポイント
1. **保守的アプローチ**: 「動作するものを壊さない」を最優先
2. **段階的改善**: 小さな改善の積み重ねで大きな改善を実現
3. **即座の動作確認**: 各変更後すぐにブラウザで確認
4. **git活用**: 問題時に即座に復旧できる体制維持
5. **ユーザー体験優先**: 見た目より動作の安定性を優先

---

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

## 🔧 JavaScript開発ガイドライン

### ⚠️ JavaScriptエラー予防の必須ルール

**この章は、JavaScriptスコープエラーの再発防止のために必須で遵守してください。**

#### 🚨 スコープエラーの根本原因と対策

##### ❌ 典型的な失敗パターン
```javascript
// 悪い例: DOMContentLoaded内で関数定義
document.addEventListener('DOMContentLoaded', function() {
    function toggleDiceSettings() {
        // この関数はonclick="toggleDiceSettings()"から呼び出せない
    }
});

// HTML側でエラーが発生
<button onclick="toggleDiceSettings()">表示</button>
```

##### ✅ 正しい実装パターン
```javascript
// 良い例: グローバルスコープで関数定義
function toggleDiceSettings() {
    // この関数はonclickから呼び出し可能
}

// または、イベントリスナーを使用
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('toggleBtn')?.addEventListener('click', toggleDiceSettings);
});

// HTML側
<button id="toggleBtn">表示</button>
```

#### 📋 JavaScript実装チェックリスト

##### 必須チェック項目（実装前）
- [ ] **関数スコープ確認**: onclickから呼び出す関数はグローバルスコープに配置
- [ ] **HTML要素ID確認**: 対応するHTML要素が存在することを確認
- [ ] **重複関数チェック**: 同名関数が複数定義されていないか確認
- [ ] **依存関数チェック**: 呼び出す他の関数もグローバルに配置されているか確認

##### 必須チェック項目（実装後）
- [ ] **ブラウザテスト**: 実際にボタンクリックして動作確認
- [ ] **開発者ツール確認**: Console Errorが発生しないことを確認
- [ ] **関数可視性テスト**: `console.log(typeof functionName)`でundefinedでないことを確認

#### 🔧 JavaScript関数配置ルール

##### Rule 1: onclick用関数はグローバル配置
```javascript
// ❌ 悪い例: DOMContentLoaded内
document.addEventListener('DOMContentLoaded', function() {
    function handleClick() { /* onclick から呼べない */ }
});

// ✅ 良い例: グローバルスコープ
function handleClick() { /* onclick から呼べる */ }
```

##### Rule 2: イベントリスナーパターンを推奨
```javascript
// ✅ 推奨: onclick属性を避ける
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('myButton')?.addEventListener('click', handleClick);
});
```

##### Rule 3: 関数重複の回避
```javascript
// ❌ 悪い例: 関数の重複定義
function myFunction() { /* グローバル */ }
document.addEventListener('DOMContentLoaded', function() {
    function myFunction() { /* 重複！ */ }
});

// ✅ 良い例: 一箇所での定義
function myFunction() { /* グローバルで一度だけ */ }
```

#### 🧪 JavaScript動作確認手順

##### 開発時確認ステップ
1. **構文チェック**: ブラウザの開発者ツールでエラーなし
2. **関数存在確認**: `console.log(typeof functionName)` → `'function'`
3. **クリックテスト**: 実際にボタンをクリックして動作確認
4. **ネットワークエラー確認**: 404やJSエラーがないことを確認

##### エラー発生時のデバッグ手順
```javascript
// デバッグ用コード例
console.log('=== デバッグ開始 ===');
console.log('toggleDiceSettings type:', typeof toggleDiceSettings);
console.log('rollCustomDice type:', typeof rollCustomDice);
console.log('Element exists:', document.getElementById('targetElement'));
console.log('=== デバッグ終了 ===');
```

#### 🔄 JavaScript修正時の必須手順

##### 修正ワークフロー
1. **🔍 問題特定**: Console Errorメッセージの確認
2. **🧩 スコープ分析**: 関数がどこで定義されているか確認
3. **✂️ 重複削除**: 同じ関数の重複定義を削除
4. **🌐 グローバル移動**: onclick用関数をグローバルスコープに移動
5. **🔗 イベント接続**: DOMContentLoaded内でイベントリスナー設定
6. **✅ 動作確認**: ブラウザで実際にテスト実行

##### テンプレート（理想的な構造）
```javascript
// === グローバル関数群（onclick用） ===
function toggleDiceSettings() { /* ... */ }
function rollCustomDice() { /* ... */ }
function applyPresets() { /* ... */ }

// === DOMContentLoaded（初期化・イベント接続） ===
document.addEventListener('DOMContentLoaded', function() {
    // イベントリスナー設定
    document.getElementById('toggleBtn')?.addEventListener('click', toggleDiceSettings);
    document.getElementById('rollBtn')?.addEventListener('click', rollCustomDice);
    
    // 初期化処理
    initializeComponents();
    
    // ローカル関数（onclickからは呼ばない）
    function initializeComponents() { /* ... */ }
});
```

#### 🚨 緊急時対応プロトコル

##### 本番環境でJavaScriptエラーが発生した場合
1. **即座確認**: ブラウザ開発者ツールでエラー内容確認
2. **一時回避**: onclick → addEventListener に変更
3. **根本修正**: グローバル関数配置とスコープ整理
4. **動作テスト**: 全ボタン・機能の動作確認
5. **デプロイ**: 修正版のデプロイ

#### 📚 関連ドキュメント

- **JavaScript基礎**: [MDN - Functions](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Functions)
- **イベント処理**: [MDN - Event Handling](https://developer.mozilla.org/en-US/docs/Web/API/EventTarget/addEventListener)
- **スコープ**: [MDN - Variable Scope](https://developer.mozilla.org/en-US/docs/Glossary/Scope)

**重要**: 今後、JavaScriptでonclick関数エラーが発生した場合は、必ずこのガイドラインに従って修正してください。

### 🚨 JavaScript重複・スコープエラーの完全予防ガイド

#### 最重要ルール
1. **変数重複の絶対禁止**: 同じ変数名（特に`const abilities`）を複数箇所で宣言しない
2. **グローバル定数の活用**: 共通で使用する配列はグローバル定数として定義
3. **関数重複の完全排除**: 同名関数を複数箇所で定義しない
4. **onclick属性の段階的廃止**: addEventListener方式への全面移行

#### 🔍 エラーパターンと対策

##### パターン1: 変数重複エラー
```javascript
// ❌ 危険: 変数の重複宣言
const abilities = ['str', 'con', 'pow'];  // グローバル
function myFunction() {
    const abilities = ['STR', 'CON', 'POW'];  // エラー: 重複
}

// ✅ 安全: グローバル定数の活用
const ABILITIES_LOWER = ['str', 'con', 'pow'];
const ABILITIES_UPPER = ['STR', 'CON', 'POW'];
function myFunction() {
    ABILITIES_UPPER.forEach(ability => { /* ... */ });
}
```

##### パターン2: 関数重複エラー
```javascript
// ❌ 危険: 関数の重複定義
function loadDiceSetting() { /* グローバル */ }
document.addEventListener('DOMContentLoaded', function() {
    function loadDiceSetting() { /* 重複エラー */ }
});

// ✅ 安全: 一箇所での定義
function loadDiceSetting() { /* グローバルで一度だけ */ }
document.addEventListener('DOMContentLoaded', function() {
    // 重複定義なし
});
```

##### パターン3: スコープアクセスエラー
```javascript
// ❌ 危険: onchangeから呼び出せない
document.addEventListener('DOMContentLoaded', function() {
    function handleChange() { /* onchangeから見えない */ }
});

// ✅ 安全: グローバル関数 + イベントリスナー
function handleChange() { /* グローバルで定義 */ }
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('mySelect')?.addEventListener('change', handleChange);
});
```

#### 📋 JavaScript品質チェックリスト（拡張版）

##### コード作成前チェック
- [ ] **グローバル定数確認**: 共通配列をグローバル定数で定義済みか
- [ ] **関数配置計画**: どの関数をグローバル、どの関数をローカルにするか明確化
- [ ] **イベント戦略**: onclick vs addEventListener のどちらを使用するか決定

##### コード作成中チェック  
- [ ] **変数名重複チェック**: 同じ変数名を複数箇所で宣言していないか
- [ ] **関数名重複チェック**: 同じ関数名を複数箇所で定義していないか
- [ ] **スコープ一貫性**: HTML属性から呼び出す関数がグローバルスコープにあるか

##### コード完成後チェック
- [ ] **ブラウザConsoleテスト**: 一切のSyntaxErrorとReferenceErrorがないか
- [ ] **全ボタン動作確認**: すべてのクリック可能要素が正常動作するか
- [ ] **ドロップダウン動作確認**: すべてのselect要素のonchangeが正常動作するか

#### 🛠️ 修正作業時の標準手順

##### Step 1: エラー種別の特定
```javascript
// Console Errorメッセージから判断
// "Identifier 'abilities' has already been declared" → 変数重複
// "ReferenceError: loadDiceSetting is not defined" → スコープエラー
// "SyntaxError: Unexpected token" → 構文エラー
```

##### Step 2: 重複要素の洗い出し
```bash
# 重複変数の検索
rg -n "const abilities.*=.*\[" file.html

# 重複関数の検索  
rg -n "function functionName" file.html

# onclick属性の検索
rg -n "onclick=" file.html
```

##### Step 3: 統一・整理作業
1. **グローバル定数化**: 共通配列をファイル先頭で定義
2. **関数統合**: 重複関数を削除、グローバル関数を一箇所に統合
3. **イベントリスナー化**: onclick属性をaddEventListener方式に変更

##### Step 4: 完全性確認
```javascript
// 全関数の存在確認
console.log('Function checks:');
console.log('toggleDiceSettings:', typeof toggleDiceSettings);
console.log('loadDiceSetting:', typeof loadDiceSetting);
console.log('rollCustomDice:', typeof rollCustomDice);

// 全グローバル定数の確認
console.log('Constants checks:');
console.log('ABILITIES_LOWER:', ABILITIES_LOWER);
console.log('ABILITIES_UPPER:', ABILITIES_UPPER);
```

#### 📚 推奨テンプレート構造

```javascript
// === ファイル先頭: グローバル定数群 ===
const ABILITIES_LOWER = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu'];
const ABILITIES_UPPER = ['STR', 'CON', 'POW', 'DEX', 'APP', 'SIZ', 'INT', 'EDU'];

// === グローバル関数群 ===
function toggleDiceSettings() { /* ... */ }
function loadDiceSetting() { /* ... */ }
function rollCustomDice() { /* ... */ }

// === DOMContentLoaded: 初期化のみ ===
document.addEventListener('DOMContentLoaded', function() {
    // イベントリスナー設定のみ
    document.getElementById('btn1')?.addEventListener('click', toggleDiceSettings);
    document.getElementById('select1')?.addEventListener('change', loadDiceSetting);
    
    // 初期化処理
    initializeApp();
    
    // ローカル関数（HTML要素から直接呼ばれない）
    function initializeApp() { /* ... */ }
});
```

#### 🚨 緊急修正プロトコル（更新版）

JavaScriptエラーが発生した場合の対応順序：

1. **🔍 即座診断**: Console Errorメッセージの完全確認
2. **🧩 エラー分類**: 重複エラー / スコープエラー / 構文エラーの判別
3. **✂️ 重複削除**: 同名変数・関数の重複をすべて削除
4. **🌐 構造整理**: グローバル定数・関数の適切な配置
5. **🔗 イベント変換**: onclick属性をaddEventListener方式に統一
6. **✅ 全面テスト**: 全ボタン・ドロップダウンの動作確認
7. **📝 文書更新**: 修正内容をCLAUDE.mdに反映

**絶対ルール**: 同じエラーを二度と発生させないよう、このガイドラインを厳格に遵守してください。
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