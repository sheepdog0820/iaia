# 🎯 タブレノ - 完了済み課題アーカイブ

## 📋 概要
完了済みの課題とチケットのアーカイブです。現在進行中の課題は`ISSUES.md`を参照してください。

---

## ✅ 完了済み課題一覧

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
- **仕様書記載箇所**: `SPECIFICATION.md` - 4.2.3 グループ機能（Cult Circle）

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
- **仕様書記載箇所**: `SPECIFICATION.md` - 6.6 統計・エクスポート機能

### ✅ ISSUE-003: CCFOLIA連携機能の実装（解決済み）
- **カテゴリ**: 新機能実装
- **影響範囲**: キャラクターシート機能
- **詳細**:
  - CocoholiaからCCFOLIAへの完全移行
  - `/api/accounts/character-sheets/{id}/ccfolia-json/` - CCFOLIA形式エクスポートAPI
  - CCFOLIA公式仕様準拠のデータ形式実装
- **該当ファイル**:
  - `accounts/models.py` - export_ccfolia_format()メソッド
  - `accounts/views.py` - ccfolia_json APIアクション
  - `accounts/urls.py` - URL更新
  - `accounts/migrations/0009_rename_cocoholia_to_ccfolia.py` - フィールド名変更
  - `accounts/test_character_6th_api.py` - テストケース更新
- **実装内容**:
  - フィールド名変更: `cocoholia_*` → `ccfolia_*`
  - CCFOLIA標準形式準拠: `{"kind": "character", "data": {...}}`
  - コマンド文字列生成: 技能ロール、正気度ロール、基本判定
  - ステータス配列: HP/MP/SAN
  - パラメータ配列: 8種能力値
  - 同期機能: sync_to_ccfolia()メソッド
  - 一括エクスポート機能: bulk_export_ccfolia()
- **技術詳細**:
  - CCFOLIA形式仕様完全準拠
  - 28件のテストケース全て成功
  - 技能値計算にbonus_pointsを含める修正
  - CharacterSheetモデルのexport_ccfolia_format()メソッド完全実装
  - ViewSetカスタムアクションとしてccfolia_json実装
- **解決日**: 2025年6月18日
- **仕様書記載箇所**: `SPECIFICATION.md` - 4.2.1 キャラクターシート機能、`CHARACTER_SHEET_COC6TH.md` - CCFOLIA連携

### ✅ ISSUE-004: クトゥルフ神話TRPG 6版キャラクターシート機能強化（解決済み）
- **カテゴリ**: 新機能実装
- **影響範囲**: キャラクターシート機能
- **詳細**:
  - `CHARACTER_SHEET_COC6TH.md`仕様書に基づく機能拡張
  - 現在基本的なキャラクター作成は実装済み、詳細機能が未実装
- **該当ファイル**:
  - `accounts/character_models.py` - CharacterSheet, CharacterSkill, CharacterEquipment
  - `templates/accounts/character_sheet_6th.html` - 6版作成画面
  - `accounts/views/character_views.py` - CharacterSheetViewSet
- **実装内容**:
  - ✅ **基本キャラクター作成機能** - 実装済み
  - ✅ **CCFOLIA連携機能** - 実装済み（export_ccfolia_format）
  - ✅ **カスタム技能追加機能** - 実装済み（create_custom_skill）
  - ✅ **ダイスロール設定機能** - 実装済み（CharacterDiceRollSetting）
  - ✅ **バージョン管理機能** - 実装済み（CharacterVersionManager）
  - ✅ **職業テンプレート機能** - 部分実装（apply_occupation_template）
  - ✅ **技能ポイント管理システム** - 実装完了（2025年6月20日）
  - ✅ **戦闘データ管理** - 実装完了（2025年6月20日）
  - ✅ **所持品・装備管理** - 実装完了（2025年6月20日）
  - ✅ **背景情報詳細化** - 実装完了（2025年6月20日）
  - ✅ **成長記録システム** - 実装完了（2025年7月13日）
- **解決日**: 2025年7月13日

### ✅ ISSUE-005: Tindalos統計APIの詳細実装（解決済み）
- **カテゴリ**: 機能強化
- **影響範囲**: 統計機能
- **詳細**:
  - `/api/accounts/statistics/tindalos/` - Tindalos指標API
  - 現在基本実装済み、詳細機能の追加が必要
- **該当ファイル**:
  - `accounts/statistics_views.py` - SimpleTindalosMetricsView実装済み
- **実装内容**:
  - ✅ **基本統計機能** - 実装済み
  - ✅ **年度・月別詳細集計** - 実装完了（2025年6月20日）
  - ✅ **ゲームシステム別統計** - 実装完了（2025年6月20日）
  - ✅ **期間指定フィルタ** - 実装完了（2025年6月20日）
- **解決日**: 2025年6月20日

### ✅ ISSUE-008: カレンダー統合APIの実装（解決済み）
- **カテゴリ**: 新機能実装
- **影響範囲**: スケジュール管理機能
- **詳細**:
  - `/api/schedules/calendar/view/` - カレンダービューAPI
  - 現在Web画面は実装済み、API機能が未実装
- **該当ファイル**:
  - `schedules/views.py` - Web画面実装済み
- **実装内容**:
  - ✅ **カレンダーWeb画面** - 実装済み
  - ✅ **月別イベント一覧API** - 実装完了（2025年6月20日）
  - ✅ **セッション予定集約API** - 実装完了（2025年6月20日）
  - ✅ **iCal形式エクスポート** - 実装完了（2025年6月20日）
- **実装詳細**:
  - MonthlyEventListView: 月別イベントを日付別にグループ化して返すAPI
  - SessionAggregationView: セッションをグループ別、週別、役割別に集約
  - ICalExportView: iCal形式でセッションをエクスポート（リマインダー付き）
- **解決日**: 2025年6月20日

### ✅ ISSUE-009: ハンドアウト一括管理機能（実装済み）
- **カテゴリ**: 機能強化
- **影響範囲**: セッション管理機能
- **詳細**:
  - GMがセッション単位でハンドアウトを一括管理できる機能
  - `/schedules/sessions/{id}/handouts/manage/` - 管理画面
- **該当ファイル**:
  - `schedules/handout_views.py` - 実装済み
  - `schedules/models.py` - HandoutAttachment実装済み
  - `schedules/notification_views.py` - 通知機能実装済み
- **実装内容**:
  - ✅ **ハンドアウト一括作成** - 実装済み
  - ✅ **配布状況の確認** - 実装済み
  - ✅ **秘匿/公開切り替え** - 実装済み
  - ✅ **ファイル添付機能** - 実装済み
  - ✅ **通知機能** - 実装済み
- **解決日**: 2025年6月18日
- **仕様書記載箇所**: `SPECIFICATION.md` - 6.5 ハンドアウト管理機能

### ✅ ISSUE-013: 通知機能の拡張（解決済み）

- **カテゴリ**: 新機能実装
- **影響範囲**: 全体
- **詳細**:
  - ハンドアウト通知、セッション招待通知、スケジュール変更通知、フレンドリクエスト通知
- **該当ファイル**:
  - `schedules/notifications.py` - 各種通知サービスクラス
  - `schedules/models.py` - HandoutNotification, UserNotificationPreferences
  - `accounts/views/user_views.py` - フレンドリクエスト通知連携
- **実装内容**:
  - ✅ **ハンドアウト通知** - 実装済み
  - ✅ **セッション招待通知** - 実装完了（2025年6月20日）
  - ✅ **スケジュール変更通知** - 実装完了（2025年6月20日）
  - ✅ **フレンドリクエスト通知** - 実装完了（2026年1月16日）
- **実装詳細**:
  - HandoutNotificationService: ハンドアウト通知
  - SessionNotificationService: セッション招待、スケジュール変更、キャンセル、リマインダー通知
  - GroupNotificationService: グループ招待通知
  - FriendNotificationService: フレンドリクエスト送信/承認通知
- **解決日**: 2026年1月16日
- **備考**: リアルタイム通知（WebSocket）は将来の別課題として分離

### ✅ ISSUE-030: 参加予定セッション一覧（解決済み）

- **カテゴリ**: UX改善
- **影響範囲**: スケジュール管理 / ダッシュボード
- **詳細**:
  - 参加予定のセッションを一覧で閲覧できる画面/タブを追加
  - GM/参加者いずれも対象、予定/進行中を中心に表示
  - 既存の「次回セッション（最大5件）」とは別に、全件を見られる導線を用意
- **該当ファイル**:
  - `schedules/views.py` - my_sessionsアクション追加
  - `templates/schedules/sessions.html` - 参加予定タブ/フィルタ追加
  - `templates/account/dashboard.html` - 一覧への導線追加
- **実装内容**:
  - ✅ **一覧画面/タブ** - 実装済み（参加予定/すべてのタブ切り替え）
  - ✅ **ページング/絞り込み** - 実装済み（ロール、ステータス、期間フィルター）
  - ✅ **一覧への導線** - 実装済み（ダッシュボードにリンク追加）
- **解決日**: 2026年1月15日

### ✅ ISSUE-031: セッション一覧から詳細画面への遷移不具合（解決済み）

- **カテゴリ**: バグ修正
- **影響範囲**: セッション一覧 / セッション詳細
- **詳細**:
  - セッション一覧から詳細画面への遷移が失敗する
  - 詳細リンク/ボタンの導線が不安定
- **該当ファイル**:
  - `templates/schedules/sessions_list.html`
  - `templates/schedules/sessions.html`
  - `tests/ui/test_ui_navigation.py`
- **実装内容**:
  - ✅ **詳細リンクの遷移修正** - 実装済み
  - ✅ **詳細導線の一貫性確保** - 実装済み
  - ✅ **遷移チェックの更新** - テスト追加済み
- **解決日**: 2026年1月1日

### ✅ ISSUE-014: セッションノート・ログシステム（UI統合）（解決済み）
- **カテゴリ**: 新機能実装
- **影響範囲**: セッション管理機能（セッション詳細）
- **詳細**:
  - セッション終了後の記録管理機能
  - GMプライベートノート、公開サマリー、プレイログをセッション詳細UIに統合
- **該当ファイル**:
  - `templates/schedules/session_detail.html` - UI統合
  - `schedules/test_session_notes_logs.py` - テスト追加
  - `docs/CURRENT_WEBAPP_FEATURES.md` - ステータス更新
- **実装内容**:
  - ✅ **セッション詳細UIへの組み込み** - 実装済み
  - ✅ **GMプライベートノート** - UI統合済み
  - ✅ **公開サマリー** - UI統合済み
  - ✅ **プレイログ時系列記録** - UI統合済み
  - ✅ **NPCメモ管理** - UI統合済み
- **解決内容**:
  - セッション詳細画面にノート/ログUIを追加し、既存APIを使って作成・更新・削除・表示できるようにした
- **解決日**: 2026年01月15日
- **関連コミット**: `7fb27f1` - feat(schedules): セッションノート/ログUIを統合 (ISSUE-014)

### ✅ ISSUE-015: キャラクターシートセッション統合（解決済み）
- **カテゴリ**: 機能統合
- **影響範囲**: セッション管理・キャラクター管理
- **詳細**:
  - キャラクターシートの現在値をセッション詳細で参照表示
  - セッション運用はココフォリア想定（更新機能は不要）
- **該当ファイル**:
  - `templates/schedules/session_detail.html` - セッション詳細UI（参照のみ）
- **実装内容**:
  - ⚪️ **HP/MP/SANトラッキング** - 不要（ココフォリア運用想定）
  - ⚪️ **ステータスエフェクト管理** - 不要（ココフォリア運用想定）
  - ✅ **セッション詳細UIへの組み込み** - 参照のみ実装済み
- **解決日**: 2025年12月30日（整理日）

### ✅ ISSUE-020: Google OAuth API認証の実装（解決済み）
- **カテゴリ**: 新機能実装
- **影響範囲**: API認証
- **詳細**:
  - Google OAuthをAPI経由で利用するための認証機能
  - django-allauthとDjango REST Frameworkの統合
  - Google Cloud Consoleの設定確認（手動実施済み）
- **該当ファイル**:
  - `tableno/settings.py` - Google OAuth設定、rest_framework.authtokenの追加
  - `accounts/views/api_auth_views.py` - Google OAuth認証API（code/access_token/id_token対応）
  - `api/urls.py` - `/api/auth/google/` ルーティング
  - `accounts/test_api_auth_google.py` - API向けテスト追加
- **実装内容**:
  - ✅ **Google OAuth APIエンドポイント** - /api/auth/google/
  - ✅ **トークン検証** - IDトークン/アクセストークン/認証コードに対応
  - ✅ **ユーザー情報取得** - Googleプロフィール情報取得
  - ✅ **新規ユーザー自動作成** - 初回ログイン時の作成
  - ✅ **DRFトークン発行** - 認証成功後のトークン生成
  - ✅ **APIテスト追加** - 成功/失敗ケースの単体テスト
- **解決日**: 2025年12月30日

### ✅ ISSUE-021: リリース前必須タスク（解決済み）
- **カテゴリ**: リリース準備
- **影響範囲**: システム全体
- **詳細**:
  - キャラクター作成機能までの最小限リリースに必要なタスク
  - 本番環境へのデプロイ準備
- **該当ファイル**:
  - `tableno/settings_production.py` - 本番設定、セキュリティ、ロギング
  - `tableno/settings.py` - python-decouple導入、環境変数管理
  - `deploy.sh` - マイグレーション/静的ファイル収集を含むデプロイ
  - `templates/404.html` - 404エラーページ
  - `templates/500.html` - 500エラーページ
  - `accounts/views/admin_views.py` - 管理者ユーザー管理API
  - `accounts/urls/__init__.py` - 管理者APIのルーティング
- **実装内容**:
  - ✅ **OAuth経由の新規ユーザー自動作成** - 初回OAuth認証時の自動作成
  - ✅ **管理者用ユーザー管理API** - ユーザー管理・権限設定
  - ✅ **本番環境設定** - PostgreSQL設定、セキュリティ設定
  - ✅ **静的ファイル配信設定** - WhiteNoise設定
  - ✅ **環境変数管理** - python-decouple導入
  - ✅ **デプロイスクリプト** - マイグレーション、静的ファイル収集
  - ✅ **セキュリティ設定** - DEBUG=False、ALLOWED_HOSTS設定
  - ✅ **エラーページ作成** - 404、500エラーページ
  - ✅ **ロギング設定** - 本番環境用ログ設定
- **解決日**: 2025年12月30日

### ✅ ISSUE-022: X（Twitter）OAuth API認証の実装（解決済み）
- **カテゴリ**: 新機能実装
- **影響範囲**: API認証
- **詳細**:
  - X（Twitter）OAuthをAPI経由で利用するための認証機能
  - django-allauthとDjango REST Frameworkの統合
- **該当ファイル**:
  - `tableno/settings.py` - X OAuth設定
  - `accounts/views/api_auth_views.py` - X OAuth認証API実装
  - `api/urls.py` - ルーティング追加
  - `accounts/test_api_auth_twitter.py` - APIテスト追加
- **実装内容**:
  - ✅ **X OAuth APIエンドポイント** - /api/auth/twitter/
  - ✅ **Xトークン検証** - OAuth2の認可コード/PKCEでトークン交換
  - ✅ **ユーザー情報取得** - Xプロフィール情報の取得
  - ✅ **アカウント連携** - SocialAccount (twitter_oauth2) の作成/連携
  - ✅ **APIトークン生成** - 認証成功後のDRFトークン生成
  - ✅ **APIテスト追加** - 成功/失敗/連携の単体テスト
- **解決日**: 2025年12月31日

### ✅ ISSUE-024: セッション機能の統合テスト失敗修正（解決済み）
- **カテゴリ**: バグ修正
- **影響範囲**: セッション機能、キャラクター管理
- **備考**: 旧ISSUE-009（番号重複のため再割当）
- **詳細**:
  - セッション統合テストで多数の失敗が発生
  - CharacterSheetモデルにリアルタイムステータス属性が不足
  - APIエンドポイントの不具合
- **該当ファイル**:
  - `accounts/character_models.py` - hp_current, mp_current, san_current 追加
  - `accounts/views/mixins.py` - character_sheet_id 処理修正
  - `accounts/test_session_integration.py` - テストケース
  - `schedules/views.py` - 参加権限/統計更新/協力GMの実装
- **実装内容**:
  - ✅ **リアルタイムステータス属性追加** - hp_current, mp_current, san_current（プロパティエイリアス）
  - ✅ **character_sheet_id 取得ロジック修正** - IDから直接取得（リクエストデータからも取得可能）
  - ✅ **クロス参加権限管理** - 公開/グループ/GMで参加制御
  - ✅ **複数GM協力セッション** - add_co_gmと権限チェック
  - ✅ **統計更新機能** - セッション完了時の統計処理
  - ✅ **統合テスト通過** - `accounts.test_session_integration` / `tests.integration.test_character_session_integration`
- **解決日**: 2025年12月30日

### ✅ ISSUE-024: シナリオ情報のキャラクター作成連携要件整理（解決済み）
- **カテゴリ**: 機能統合
- **影響範囲**: シナリオ管理・キャラクター作成・セッション管理
- **備考**: ISSUE番号重複（別件）
- **詳細**:
  - シナリオの推奨技能やタイトル等をキャラ作成へ引き継ぐ連携仕様の整備
  - セッション作成・詳細画面を含めたシナリオ連携導線を整備
- **該当ファイル**:
  - `templates/scenarios/archive.html`
  - `static/accounts/js/character6th.js`
  - `templates/accounts/character_6th_create.html`
  - `accounts/character_models.py`
  - `accounts/views/character_views.py`
  - `accounts/serializers.py`
  - `schedules/models.py`
  - `schedules/serializers.py`
  - `schedules/views.py`
  - `templates/schedules/calendar.html`
  - `templates/schedules/session_detail.html`
  - `tests/e2e/flows/scenario-session-character.spec.ts`
- **実装内容**:
  - ✅ **最小連携セット定義** - `scenario_id` / `scenario_title` / `game_system` / `recommended_skills`
  - ✅ **キャラクターへのシナリオ由来情報保存** - FK + スナップショット保持
  - ✅ **推奨技能の取得強化** - `scenario_id` からのAPI取得に対応
  - ✅ **セッション経由の連携導線** - シナリオ→セッション→探索者作成
  - ✅ **連携フローのE2Eテスト追加** - Playwright
- **解決日**: 2025年12月31日

### ✅ ISSUE-025: シナリオ推奨技能入力の品質向上（解決済み）
- **カテゴリ**: UI/UX改善
- **影響範囲**: シナリオ管理・キャラクター作成
- **詳細**:
  - 推奨技能の入力補助とバリデーション強化
  - 未対応技能の視覚フィードバックと正規化
- **該当ファイル**:
  - `templates/scenarios/archive.html`
  - `static/accounts/js/character6th.js`
  - `tests/e2e/flows/scenario-management.spec.ts`
- **実装内容**:
  - ✅ **推奨技能入力UIのオートコンプリート** - CoC 6版技能候補
  - ✅ **推奨技能の正規化/検証** - 区切り/重複/表記ゆれ対応
  - ✅ **未知技能のフィードバック表示** - 警告/確認フロー
  - ✅ **空入力の警告除去** - 未入力でも導線を遮断しない
  - ✅ **E2Eテスト追加** - 空入力時の警告非表示
- **解決日**: 2025年12月31日

---

## 📊 完了済み課題統計

### 実装完了サマリー

- **完了済み課題数**: 17件
- **完了期間**: 2024年6月14日 〜 2026年1月16日
- **主要カテゴリ**: バグ修正3件、新機能実装7件、機能強化2件、機能統合2件、UI/UX改善2件、リリース準備1件

### テスト結果
- **統合テスト成功率**: 100% (16/16)
- **CCFOLIA専用テスト**: 100% (28/28)
- **機能カバレッジ**: グループ管理、エクスポート、CCFOLIA連携、ハンドアウト管理、キャラクターシート6版強化、Tindalos詳細統計、カレンダー統合、セッション連携UI、Google/X OAuth API認証、リリース準備、セッション統合テスト修正

### 品質指標
- **セキュリティチェック**: 全て合格
- **パフォーマンステスト**: 全て合格
- **リンティング**: 全て合格
- **ドキュメント化**: 全て完了

---

## 🔄 アーカイブ管理

### アーカイブポリシー
1. **完了条件**: 全機能実装完了、テスト100%成功、仕様書更新完了
2. **移動タイミング**: 機能完了確認後、即座にアーカイブ
3. **参照頻度**: 通常開発では参照不要、リファクタリング時のみ参照

### 関連ドキュメント
- **現在進行中課題**: `ISSUES.md`
- **システム仕様書**: `SPECIFICATION.md`
- **開発ガイドライン**: `CLAUDE.md`
- **キャラクターシート仕様**: `CHARACTER_SHEET_COC6TH.md`

---

*最終更新日: 2026年1月16日*
