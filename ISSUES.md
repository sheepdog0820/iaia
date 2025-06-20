# 🎯 Arkham Nexus - 課題管理チケット

## 📋 概要
統合テスト実施により判明した課題と今後の実装タスクを管理します。

---

## 🔴 優先度: 高

### ✅ ISSUE-001: パブリックグループのアクセス制御修正（解決済み）
- **カテゴリ**: バグ修正
- **影響範囲**: グループ管理機能
- **詳細**: 
  - パブリックグループ（visibility='public'）に対して、非メンバーユーザーがアクセスすると404エラーが返される
  - 期待動作: パブリックグループは誰でも閲覧可能（200 OK）
- **該当ファイル**: 
  - `accounts/views.py` - GroupViewSet
  - `test_integration.py` - test_access_control_by_group_visibility
  - `test_system_integration.py` - test_group_visibility_access_control
- **解決内容**: 
  - GroupViewSetの`get_queryset`メソッドを修正して、参加中のグループと公開グループの両方を取得するよう変更
  - 管理者権限チェックを`get_object`メソッドに追加して、編集・削除・招待機能を管理者のみに制限
- **解決日**: 2024年6月14日

### ✅ ISSUE-002: エクスポート機能のAPI実装（解決済み）
- **カテゴリ**: 新機能実装
- **影響範囲**: 統計・エクスポート機能
- **詳細**:
  - `/api/accounts/export/formats/` - 利用可能なエクスポート形式一覧API
  - `/api/accounts/export/statistics/` - 統計データエクスポートAPI
- **該当ファイル**:
  - `accounts/export_views.py` - StatisticsExportView, ExportFormatsView追加
  - `accounts/urls.py` - URLパターン追加
  - `accounts/test_export.py` - テストケース追加・拡張
- **実装内容**:
  - JSON, CSV, PDF形式でのエクスポート対応
  - 日付範囲指定機能（start_date, end_date パラメータ）
  - プレイ履歴、セッション統計、シナリオ利用状況のエクスポート
  - ユーザーデータの分離（他ユーザーのデータは含まれない）
  - 認証が必要（IsAuthenticated）
  - TDDアプローチでテストケースを先に作成してから実装
- **解決内容**:
  - `StatisticsExportView`クラスを新規作成し、新仕様に対応
  - `ExportFormatsView`クラスを新規作成し、フォーマット一覧API対応
  - 日付範囲フィルタ機能を実装
  - エラーハンドリング（無効なフォーマット、日付形式エラー）
  - PDF未対応時のCSVフォールバック機能
  - 性能テスト対応（大量データでも5秒以内）
- **解決日**: 2024年6月14日

### ISSUE-003: Tindalos統計APIの実装
- **カテゴリ**: 新機能実装
- **影響範囲**: 統計機能
- **詳細**:
  - `/api/accounts/statistics/tindalos/` - Tindalos指標API
  - 総プレイ時間、セッション数、GM/プレイヤー回数などの統計情報
- **該当ファイル**:
  - `accounts/statistics_views.py` - 実装強化が必要
- **実装内容**:
  - ユーザーごとの詳細統計
  - 年度・月別集計
  - ゲームシステム別統計

---

## 🟡 優先度: 中

### ISSUE-004: グループ統計APIの実装
- **カテゴリ**: 新機能実装
- **影響範囲**: グループ管理機能
- **詳細**:
  - `/api/accounts/statistics/groups/` - グループ統計API
  - グループごとのセッション数、メンバー数、活動状況
- **該当ファイル**:
  - `accounts/statistics_views.py`
- **実装内容**:
  - グループ活動サマリー
  - メンバー参加率
  - 人気シナリオランキング

### ISSUE-005: ユーザーランキングAPIの実装
- **カテゴリ**: 新機能実装
- **影響範囲**: 統計機能
- **詳細**:
  - `/api/accounts/statistics/ranking/` - ユーザーランキングAPI
  - プレイ時間、GM回数などでのランキング表示
- **該当ファイル**:
  - `accounts/statistics_views.py`
- **実装内容**:
  - 総プレイ時間ランキング
  - GM回数ランキング
  - 参加セッション数ランキング

### ISSUE-006: カレンダー統合APIの実装
- **カテゴリ**: 新機能実装
- **影響範囲**: スケジュール管理機能
- **詳細**:
  - `/api/schedules/calendar/` - カレンダービューAPI
  - 月別セッション表示用データ提供
- **該当ファイル**:
  - `schedules/views.py`
- **実装内容**:
  - 月別イベント一覧
  - セッション予定の集約
  - iCal形式エクスポート対応

### ISSUE-007: ハンドアウト一括管理機能
- **カテゴリ**: 機能強化
- **影響範囲**: セッション管理機能
- **詳細**:
  - GMがセッション単位でハンドアウトを一括管理できる機能
  - `/api/schedules/sessions/{id}/handouts/manage/`
- **該当ファイル**:
  - `schedules/handout_views.py` - 新規作成が必要
- **実装内容**:
  - ハンドアウト一括作成
  - 配布状況の確認
  - テンプレート機能

---

## 🟢 優先度: 低

### ISSUE-008: テストカバレッジの向上
- **カテゴリ**: テスト改善
- **影響範囲**: 全体
- **詳細**:
  - 境界値テストの追加
  - エラーケースのテスト強化
  - パフォーマンステストの追加
- **該当ファイル**:
  - 各種テストファイル

### ISSUE-009: APIドキュメント自動生成
- **カテゴリ**: ドキュメント
- **影響範囲**: API全般
- **詳細**:
  - OpenAPI/Swagger対応
  - APIドキュメントの自動生成設定
- **実装内容**:
  - drf-spectacular導入
  - エンドポイント説明の追加

### ISSUE-010: 非同期処理の導入検討
- **カテゴリ**: パフォーマンス改善
- **影響範囲**: 統計処理、エクスポート機能
- **詳細**:
  - 重い統計処理の非同期化
  - Celeryの導入検討
- **実装内容**:
  - バックグラウンドタスク
  - 進捗表示機能

---

## 📊 進捗管理

### 統合テスト結果サマリー (2024年6月14日最新)
- **総テストスイート数**: 16
- **成功**: 16 (100.0%)
- **失敗**: 0 (0.0%)

### 主要機能の動作確認状況
- ✅ ユーザー認証・権限管理
- ✅ セッション管理・参加者管理
- ✅ シナリオ管理・プレイ履歴
- ✅ グループ管理（プライベートグループ）
- ✅ グループ管理（パブリックグループ）
- ✅ デモログイン機能
- ✅ APIエラーハンドリング
- ✅ ハンドアウト基本機能
- ✅ 統計・エクスポート機能（新仕様）
- ❌ カレンダー統合
- ❌ ハンドアウト一括管理
- ❌ Tindalos統計機能（既存実装は動作中）

---

## 🚀 次のステップ

1. ✅ **ISSUE-001** の修正を最優先で実施（完了）
2. ✅ **ISSUE-002** エクスポート機能のAPI実装（完了）
3. **ISSUE-003** Tindalos統計APIの実装 - 次の優先課題
4. **ISSUE-006** カレンダー統合APIの実装
5. **ISSUE-007** ハンドアウト一括管理機能の実装
6. 各機能実装後は必ず統合テストを実行して動作確認
7. **統合テスト成功率100%達成済み**