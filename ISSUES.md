# 🎯 タブレノ - 課題管理チケット（未完了）

## 📋 概要
未完了の課題のみを管理します。完了済みは `ISSUES_CLOSED.md` に移動済みです。
`SESSION_FUTURE_DEVELOPMENT.md` はアイデア段階のため、原則チケット化対象外です。

## 🧾 棚卸しメモ（2026-01-18）

- ISSUE-023: Epic化して ISSUE-039/040/041/042 に分割（MVP/後続を明確化）
- ISSUE-026: Epic化して ISSUE-034/035/036/037 に分割（MVP/後続を明確化）。ICSエクスポート（ファイルDL）は実装済み
- ISSUE-019: `schedules/analytics_views.py` / `templates/schedules/analytics_dashboard.html` は未作成
- 既存機能のUI未整備（通知一覧、画像の並び替え）を ISSUE-043/044/045 として起票

---

## ✅ 優先度ランキング（1が最優先）
1. ISSUE-043: 通知一覧/設定UI（専用UI + ナビ未読バッジ）
2. ISSUE-044: セッション画像の並び替えUI
3. ISSUE-045: シナリオ画像の並び替えUI
4. ISSUE-039: セッション準備チェックリスト（MVP）
5. ISSUE-034: Discord Webhook通知（MVP）
6. ISSUE-035: カレンダー購読（ICSフィードURL）（MVP）
7. ISSUE-040: セッション後フィードバック（MVP）
8. ISSUE-011: APIドキュメント自動生成
9. ISSUE-010: テストカバレッジの向上
10. ISSUE-006: グループ統計APIの詳細実装
11. ISSUE-007: ユーザーランキングAPIの詳細実装
12. ISSUE-012: 非同期処理の導入検討
13. ISSUE-046: セッション側キャラクター状態のスナップショット/差分履歴
14. ISSUE-028: グループ間連携機能
15. ISSUE-019: セッション分析ダッシュボード
16. ISSUE-041: 経験値配布（後続）
17. ISSUE-042: セッションテンプレート（後続）
18. ISSUE-036: カレンダー同期（Google Calendar等）（後続）
19. ISSUE-037: 外部シート連携API（外部キャラクターシート等）（後続）
20. ISSUE-047: リアルタイム通知（WebSocket）
21. ISSUE-038: キャラクター作成画面 - 武器・防具登録UI
22. ISSUE-027: モバイルアプリ
23. ISSUE-029: AI分析/推奨機能

---

## 🟡 優先度: 中

※ 優先度順位は上部の「優先度ランキング」を正とします。

### ISSUE-012: 非同期処理の導入検討

- **優先度順位**: 12
- **カテゴリ**: パフォーマンス改善
- **影響範囲**: 統計処理、エクスポート機能
- **詳細**:
  - 重い統計処理やエクスポート処理の非同期化
- **実装内容**:
  - ❌ **Celery導入** - 未実装
  - ❌ **バックグラウンドタスク** - 未実装
  - ❌ **進捗表示機能** - 未実装

### ISSUE-006: グループ統計APIの詳細実装

- **優先度順位**: 10
- **カテゴリ**: 機能強化
- **影響範囲**: グループ管理機能
- **詳細**:
  - `/api/accounts/statistics/groups/` - グループ統計API
  - 現在基本実装済み、詳細機能の追加が必要
- **該当ファイル**:
  - `accounts/statistics_views.py` - GroupStatisticsView実装済み
- **実装内容**:
  - ✅ **基本グループ統計** - 実装済み
  - ✅ **グループ活動サマリー（合計/平均/アクティブ/Top GM）** - 実装済み
  - ✅ **メンバー別貢献度（GM/PL回数・プレイ時間）** - 実装済み
  - ❌ **メンバー参加率（%の算出・表示）** - 未実装
  - ❌ **人気シナリオランキング（グループ内）** - 未実装

### ISSUE-007: ユーザーランキングAPIの詳細実装

- **優先度順位**: 11
- **カテゴリ**: 機能強化
- **影響範囲**: 統計機能
- **詳細**:
  - `/api/accounts/statistics/ranking/` - ユーザーランキングAPI
  - 現在基本実装済み、詳細機能の追加が必要
- **該当ファイル**:
  - `accounts/statistics_views.py` - UserRankingView実装済み
- **実装内容**:
  - ✅ **基本ランキング機能（hours/sessions/gm + year指定）** - 実装済み
  - ❌ **期間別ランキング（year以外の範囲指定）** - 未実装
  - ❌ **カテゴリ別ランキング（システム/シナリオ等）** - 未実装
  - ❌ **ランキング推移（時系列）** - 未実装

### ISSUE-010: テストカバレッジの向上

- **優先度順位**: 9
- **カテゴリ**: テスト改善
- **影響範囲**: 全体
- **詳細**:
  - 現在基本テストは実装済み、詳細テストの追加が必要
- **該当ファイル**:
  - 各種テストファイル (test_*.py)
- **実装内容**:
  - ✅ **基本機能テスト** - 実装済み
  - ✅ **統合テスト** - 実装済み (100%成功率)
  - ❌ **境界値テスト** - 未実装
  - ❌ **エラーケーステスト強化** - 未実装
  - ❌ **パフォーマンステスト** - 未実装

### ISSUE-011: APIドキュメント自動生成

- **優先度順位**: 8
- **カテゴリ**: ドキュメント
- **影響範囲**: API全般
- **詳細**:
  - OpenAPI/Swagger対応でAPI仕様書の自動生成
- **実装内容**:
  - ❌ **drf-spectacular導入** - 未実装
  - ❌ **エンドポイント説明追加** - 未実装
  - ❌ **スキーマ生成設定** - 未実装

### ISSUE-023: セッション準備・事後処理ツール（Epic）

- **優先度順位**: -（Epic）
- **カテゴリ**: 新機能実装
- **影響範囲**: セッション管理機能
- **備考**: 旧ISSUE-018（番号重複のため再割当）
- **目的**:
  - GM向けセッション準備支援
  - セッション後のフィードバック/配布の効率化
- **分割（MVP/後続）**:
  - MVP:
    - ISSUE-039: セッション準備チェックリスト（MVP）
    - ISSUE-040: セッション後フィードバック（MVP）
  - 後続:
    - ISSUE-041: 経験値配布（後続）
    - ISSUE-042: セッションテンプレート（後続）
- **棚卸しメモ**:
  - 旧チケット記載の `SessionPreparation/SessionFeedback` / `templates/schedules/session_preparation.html` は現状存在しないため、上記の分割チケットとして新規実装する

### ISSUE-039: セッション準備チェックリスト（MVP）

- **優先度順位**: 4
- **カテゴリ**: 新機能実装
- **影響範囲**: セッション管理（GM運用）
- **詳細**:
  - セッションごとに「準備項目」を作成し、完了/未完了を管理する
- **該当ファイル（予定）**:
  - `schedules/models.py` - SessionChecklistItem
  - `schedules/serializers.py` - SessionChecklistItemSerializer
  - `schedules/views.py` - SessionChecklistItemViewSet
  - `templates/schedules/session_detail.html` - チェックリストUI
- **実装内容（MVP）**:
  - ❌ **チェック項目CRUD（GM）** - 未実装
  - ❌ **チェックの完了/未完了トグル（GM）** - 未実装
  - ❌ **表示（参加者: 閲覧のみ）** - 未実装

### ISSUE-040: セッション後フィードバック（MVP）

- **優先度順位**: 7
- **カテゴリ**: 新機能実装
- **影響範囲**: セッション管理（事後処理）
- **詳細**:
  - 参加者がセッション後に感想/評価を入力し、GMが集計できる
- **該当ファイル（予定）**:
  - `schedules/models.py` - SessionFeedback
  - `schedules/serializers.py` - SessionFeedbackSerializer
  - `schedules/views.py` - SessionFeedbackViewSet
  - `templates/schedules/session_detail.html` - フィードバックUI
- **実装内容（MVP）**:
  - ❌ **参加者のフィードバック投稿/更新（自分の分のみ）** - 未実装
  - ❌ **GMの一覧閲覧（セッション単位）** - 未実装
  - ❌ **平均評価など簡易サマリー** - 未実装

### ISSUE-041: 経験値配布（後続）

- **優先度順位**: 16
- **カテゴリ**: 新機能実装
- **影響範囲**: セッション管理 / キャラクター管理
- **詳細**:
  - GMが参加者にXP/成長ポイント/報酬などを記録し、セッション記録として残す
- **実装内容**:
  - ❌ **配布内容の記録モデル** - 未実装
  - ❌ **GMによる入力UI** - 未実装
  - ❌ **キャラクター成長記録への反映（必要なら）** - 未実装

### ISSUE-042: セッションテンプレート（後続）

- **優先度順位**: 17
- **カテゴリ**: 新機能実装
- **影響範囲**: セッション作成
- **詳細**:
  - よく使う設定（場所/所要時間/告知文など）をテンプレ化してセッション作成を短縮
- **棚卸しメモ**:
  - 現状「セッションテンプレート」に該当するモデル/API/UIは存在しない（`SessionTemplate` 等の実装なし）
  - 類似機能として `SessionSeries`（定期セッション/キャンペーン、`/api/schedules/session-series/{id}/generate_sessions/`）があるが、これは「繰り返し生成」が主目的で、任意テンプレの選択/適用とは別物
- **実装内容**:
  - ❌ **テンプレートCRUD** - 未実装
  - ❌ **テンプレからセッション作成** - 未実装

### ISSUE-043: 通知一覧/設定UI（専用UI + ナビ未読バッジ）

- **優先度順位**: 1
- **カテゴリ**: UI/UX改善
- **影響範囲**: 通知/ナビゲーション
- **詳細**:
  - 通知一覧の専用UIを追加（未読/全件、ページング、既読化）
  - ナビゲーションに未読件数バッジを表示
  - 通知設定（UserNotificationPreferences）をUIから変更可能にする
- **API（既存）**:
  - `GET /api/schedules/notifications/`（`unread_only=true` 対応）
  - `PATCH /api/schedules/notifications/{id}/mark_read/`
  - `PATCH /api/schedules/notifications/mark_all_read/`
  - `GET /api/schedules/notifications/unread_count/`
  - `GET/PATCH /api/schedules/notification-preferences/`
- **該当ファイル（予定）**:
  - `templates/base.html` - 通知アイコン/未読バッジ/導線
  - `templates/schedules/notifications.html` - 通知一覧/設定UI（新規）
  - `schedules/urls.py` - Web URLの追加（例: 通知ページの追加）
- **実装内容**:
  - ❌ **通知一覧UI（未読/全件 + ページング）** - 未実装
  - ❌ **既読化（単体/一括）** - 未実装
  - ❌ **未読件数バッジ（初期表示 + 更新）** - 未実装
  - ❌ **通知設定UI（ON/OFF + 保存）** - 未実装
  - ❌ **導線（ナビ/プロフィール/ダッシュボード）** - 未実装

### ISSUE-044: セッション画像の並び替えUI

- **優先度順位**: 2
- **カテゴリ**: UI/UX改善
- **影響範囲**: セッション詳細（画像）
- **詳細**:
  - セッション詳細の画像一覧でドラッグ&ドロップによる並び替えを提供
  - 並び替え結果をAPIに保存する
  - 権限はAPI仕様に合わせてGMのみ（`SessionImageViewSet.reorder`）
- **API（既存）**:
  - `POST /api/schedules/session-images/{id}/reorder/`（body: `order`）
- **該当ファイル**:
  - `templates/schedules/session_detail.html` - 画像グリッドUI/JS
  - `schedules/views.py` - `SessionImageViewSet.reorder`（実装済み）
- **実装内容**:
  - ❌ **並び替えUI（ドラッグ&ドロップ）** - 未実装
  - ❌ **並び替え保存（全画像のorder更新）** - 未実装
  - ❌ **UIでの権限制御（GMのみ表示）** - 未実装

### ISSUE-045: シナリオ画像の並び替えUI

- **優先度順位**: 3
- **カテゴリ**: UI/UX改善
- **影響範囲**: シナリオ詳細（画像）
- **詳細**:
  - シナリオ詳細（アーカイブのモーダル）でドラッグ&ドロップによる並び替えを提供
  - 並び替え結果をAPIに保存する
  - 権限はAPI仕様に合わせてシナリオ作成者のみ（`ScenarioImageViewSet.reorder`）
- **API（既存）**:
  - `POST /api/scenarios/scenario-images/{id}/reorder/`（body: `order`）
- **該当ファイル**:
  - `templates/scenarios/archive.html` - 画像グリッドUI/JS
  - `scenarios/views.py` - `ScenarioImageViewSet.reorder`（実装済み）
- **実装内容**:
  - ❌ **並び替えUI（ドラッグ&ドロップ）** - 未実装
  - ❌ **並び替え保存（全画像のorder更新）** - 未実装
  - ❌ **UIでの権限制御（作成者のみ）** - 未実装

### ISSUE-019: セッション分析ダッシュボード

- **優先度順位**: 15
- **カテゴリ**: 新機能実装
- **影響範囲**: 統計・分析機能
- **詳細**:
  - セッションデータの統計分析とビジュアライゼーション
  - 参加率、人気時間帯、GM負荷分析
- **該当ファイル**:
  - `schedules/analytics_views.py` - 分析API（未作成）
  - `templates/schedules/analytics_dashboard.html` - ダッシュボードUI（未作成）
- **実装内容**:
  - ❌ **参加率分析機能** - 未実装
  - ❌ **人気時間帯分析** - 未実装
  - ❌ **セッション時間推移グラフ** - 未実装
  - ❌ **GM負荷分析** - 未実装
  - ❌ **プレイヤー相性分析** - 未実装

---

## 🟢 優先度: 低

### ISSUE-046: セッション側キャラクター状態のスナップショット/差分履歴

- **優先度順位**: 13
- **カテゴリ**: 機能強化
- **影響範囲**: セッション管理 / キャラクター管理
- **詳細**:
  - 現状はセッション詳細で「キャラクターの現在値」を参照できるが、セッション開始時点/終了時点の記録・差分履歴が残らない
  - セッション開始時スナップショット、セッション後の差分表示、必要ならセッション中の変動履歴（任意）を追加する
- **該当ファイル（予定）**:
  - `schedules/models.py` - `SessionCharacterSnapshot` 等の追加
  - `schedules/serializers.py` - APIシリアライザ
  - `schedules/views.py` - ViewSet/アクション追加
  - `templates/schedules/session_detail.html` - 差分表示UI
- **実装内容（MVP案）**:
  - ❌ **スナップショットモデル追加** - 未実装
  - ❌ **スナップショット作成タイミング（ongoing/completed等）** - 未実装
  - ❌ **差分表示（増減の可視化）** - 未実装
  - ❌ **権限/対象キャラの扱い（参加者・公開範囲）** - 未実装
  - ❌ **テスト** - 未実装

### ISSUE-028: グループ間連携機能

- **優先度順位**: 14
- **カテゴリ**: 新機能実装
- **影響範囲**: グループ管理機能
- **詳細**:
  - グループ間の連携/共有設定（相互リンク、共有セッションなど）
- **該当ファイル**:
  - `accounts/models.py` - GroupLinkモデル追加
  - `accounts/views.py` - 連携管理API
  - `templates/groups/management.html` - 連携UI
- **実装内容**:
  - ❌ **グループ連携モデル** - 未実装
  - ❌ **連携申請/承認フロー** - 未実装
  - ❌ **共有範囲設定** - 未実装
  - ❌ **UI** - 未実装

### ISSUE-026: 外部連携（Epic: Discord/カレンダー/外部シート）

- **優先度順位**: -（Epic）
- **カテゴリ**: 外部連携
- **影響範囲**: 通知/スケジュール/キャラクター管理
- **目的**:
  - Discord通知、外部カレンダー同期、外部キャラクターシート/外部シート連携
- **分割（MVP/後続）**:
  - MVP:
    - ISSUE-034: Discord Webhook通知（MVP）
    - ISSUE-035: カレンダー購読（ICSフィードURL）（MVP）
  - 後続:
    - ISSUE-036: カレンダー同期（Google Calendar等）（後続）
    - ISSUE-037: 外部シート連携API（外部キャラクターシート等）（後続）
- **棚卸しメモ**:
  - ICSエクスポート（ファイルDL）は実装済み: `/api/schedules/calendar/export/ical/`

### ISSUE-034: Discord Webhook通知（MVP）

- **優先度順位**: 5
- **カテゴリ**: 外部連携
- **影響範囲**: 通知/セッション運用
- **詳細**:
  - セッション招待/更新/キャンセル等のイベントをDiscordに通知（Webhook）
- **該当ファイル（予定）**:
  - `schedules/notifications.py` - Discord送信の追加（既存の通知フローに合流）
  - `accounts/models.py` or `schedules/models.py` - Webhook設定の保存（スコープ: group or session）
  - `templates/` - 設定UI（GMのみ）
- **実装内容（MVP）**:
  - ❌ **Webhook URL保存（GM）** - 未実装
  - ❌ **通知イベント送信（招待/変更/キャンセル）** - 未実装
  - ❌ **失敗時のフォールバック（最低限の無効化/ログ）** - 未実装

### ISSUE-035: カレンダー購読（ICSフィードURL）（MVP）

- **優先度順位**: 6
- **カテゴリ**: 外部連携
- **影響範囲**: スケジュール
- **詳細**:
  - カレンダーアプリに「購読」できる安定URL（ICSフィード）を提供する
  - 認証ヘッダー不要で購読できるよう、専用トークンURLで提供（private/groupセッションの漏洩防止）
- **該当ファイル（予定）**:
  - `schedules/views.py` - ICSフィードエンドポイント（購読用）
  - `accounts/models.py` or `schedules/models.py` - フィードトークン管理
  - `templates/` - URLコピーUI
- **実装内容（MVP）**:
  - ❌ **購読用ICSフィードエンドポイント** - 未実装
  - ❌ **購読トークン発行/再発行** - 未実装
  - ❌ **フィードに含める範囲（例: 今後90日）** - 未実装

### ISSUE-036: カレンダー同期（Google Calendar等）（後続）

- **優先度順位**: 18
- **カテゴリ**: 外部連携
- **影響範囲**: スケジュール
- **詳細**:
  - OAuth連携でGoogle Calendar等へイベントを作成/更新/削除（双方向 or 片方向）
- **実装内容**:
  - ❌ **OAuth認可フロー** - 未実装
  - ❌ **イベント作成/更新の同期処理** - 未実装

### ISSUE-037: 外部シート連携API（外部キャラクターシート等）（後続）

- **優先度順位**: 19
- **カテゴリ**: 外部連携
- **影響範囲**: キャラクター管理/セッション管理
- **詳細**:
  - 外部サービス/スプレッドシート等との連携（参照/取込/エクスポート）
- **実装内容**:
  - ❌ **連携対象の確定（Google Sheets等）** - 未実装
  - ❌ **連携API/認可方式の設計** - 未実装

### ISSUE-047: リアルタイム通知（WebSocket）

- **優先度順位**: 20
- **カテゴリ**: 機能強化
- **影響範囲**: 通知/UX
- **詳細**:
  - WebSocketによる未読件数バッジ/通知一覧のリアルタイム更新
  - サーバーPushにより「通知が来たこと」を即時反映し、ページ遷移なしで気付けるようにする
  - フォールバックとして既存のポーリング/AJAX再取得も併用可能にする
- **該当ファイル（予定）**:
  - `tableno/asgi.py` / `tableno/settings.py` - ASGI/Channels設定
  - `schedules/consumers.py` 等 - WebSocket consumer（新規）
  - `templates/base.html` - 未読バッジ更新
  - `templates/schedules/notifications.html` - 一覧の自動更新
- **実装内容**:
  - ❌ **技術選定（Django Channels等）** - 未実装
  - ❌ **購読チャンネル設計（user単位）** - 未実装
  - ❌ **サーバーPush実装 + フロント購読** - 未実装
  - ❌ **再接続/エラーハンドリング/フォールバック** - 未実装

### ISSUE-027: モバイルアプリ

- **優先度順位**: 22
- **カテゴリ**: 新プロダクト
- **影響範囲**: 全体
- **詳細**:
  - iOS/Android対応
  - プッシュ通知
  - オフライン機能
- **実装内容**:
  - ❌ **ネイティブアプリ基盤** - 未実装
  - ❌ **プッシュ通知基盤** - 未実装
  - ❌ **オフライン同期** - 未実装

### ISSUE-029: AI分析/推奨機能

- **優先度順位**: 23
- **カテゴリ**: 先進機能
- **影響範囲**: 統計・推薦
- **詳細**:
  - プレイスタイル分析
  - シナリオ推奨機能
  - 最適なセッションマッチング
- **実装内容**:
  - ❌ **プレイスタイル分析** - 未実装
  - ❌ **シナリオ推奨** - 未実装
  - ❌ **セッションマッチング** - 未実装

---

## 🟡 優先度: 中（キャラクターシート関連）

### ISSUE-038: キャラクター作成画面 - 武器・防具登録UI

- **優先度順位**: 21
- **カテゴリ**: UI/UX改善
- **影響範囲**: キャラクターシート作成機能（6版）
- **詳細**:
  - キャラクター作成画面の「戦闘・装備」タブで武器・防具を登録できるようにする
  - 現状は「武器・防具の詳細は作成後に編集画面で設定できます」というメッセージのみ表示
  - バックエンド（API/モデル）は実装済み、フロントエンドUIのみ未実装
- **該当ファイル**:
  - `templates/accounts/character_6th_create.html` - 戦闘・装備タブUI（Line 688-759）
  - `static/accounts/js/character6th.js` - 装備管理JavaScript
  - `accounts/character_models.py` - CharacterEquipmentモデル（実装済み）
  - `accounts/character_serializers.py` - CharacterEquipmentSerializer（実装済み）
  - `accounts/character_views.py` - CharacterEquipmentViewSet（実装済み）
- **実装内容**:
  - ❌ **武器追加UI（テーブル形式/モーダル）** - 未実装
    - 武器名、技能名、ダメージ、射程、攻撃回数、装弾数、故障ナンバー
  - ❌ **防具追加UI（テーブル形式/モーダル）** - 未実装
    - 防具名、装甲ポイント、説明
  - ❌ **所持品追加UI（テーブル形式/モーダル）** - 未実装
    - アイテム名、数量、重量、説明
  - ❌ **装備削除UI** - 未実装
  - ❌ **装備編集UI** - 未実装
  - ❌ **JavaScript: 装備データ管理・API連携** - 未実装
- **備考**:
  - CharacterEquipmentモデルのitem_typeフィールドで武器(weapon)/防具(armor)/所持品(item)を区別
  - 編集画面（`character_6th_edit.html`）の実装を参考にすること
  - APIエンドポイント: `/api/accounts/characters/{id}/equipment/`

---
