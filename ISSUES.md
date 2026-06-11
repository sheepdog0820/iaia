# 🎯 タブレノ - 課題管理チケット（未完了）

## 📋 概要
未完了の課題のみを管理します。完了済みは `ISSUES_CLOSED.md` に移動済みです。
`SESSION_FUTURE_DEVELOPMENT.md` はアイデア段階のため、原則チケット化対象外です。

### 状態の扱い

- **実装済み**: 完了後に `ISSUES_CLOSED.md` へ移動する
- **部分実装**: 実装済み範囲と残作業を同じチケット内で明記する
- **未実装**: 本書で優先順位と受け入れ範囲を管理する
- **将来候補**: `SESSION_UNIMPLEMENTED_FEATURES_SPEC.md` 等に分離し、本書へ起票するまで優先順位を付けない
- **取り下げ**: `ISSUES_CLOSED.md` に経緯を残し、未実装課題へ戻さない
- **Epic内の完了サブタスク**: Epicの残作業を把握するため、完了済みでもEpic節内に実績として残す場合がある

## 🧾 棚卸しメモ（2026-06-12）

- ISSUE-051/053: アプリ設定と運用文書まで実装済み。ISSUE-050の実績として節を保持し、優先度ランキングから除外
- ISSUE-052/054/055: アプリ側設定は実装済み。移行、CloudWatch実環境定義、バックアップ/復旧手順が残存
- ISSUE-048: ゲスト参加者のMVPは実装済み。招待トークン、claim、募集統合が残存
- ISSUE-012: Celery依存関係とComposeサービス定義のみ存在。業務タスクとアプリ統合は未実装
- ISSUE-023: Epic化して ISSUE-041/042 に分割（MVP/後続を明確化） → 実装済み（`ISSUES_CLOSED.md` に移動）
- ISSUE-026: Epic化して ISSUE-034/035/036/037 に分割（MVP/後続を明確化）。ICSエクスポート（ファイルDL）は実装済み
- ISSUE-019: `schedules/analytics_views.py` / `templates/schedules/analytics_dashboard.html` を実装 → 実装済み（`ISSUES_CLOSED.md` に移動）
- 既存機能のUI未整備（通知一覧、画像の並び替え）を ISSUE-043/044/045 として起票 → 実装済み（`ISSUES_CLOSED.md` に移動）
- ISSUE-006/007: 実装済み（`ISSUES_CLOSED.md` に移動）
- ISSUE-042: 実装済み（`ISSUES_CLOSED.md` に移動）
- ISSUE-038: 武器・防具登録UI - ソース確認の結果、実装済みと判明（`ISSUES_CLOSED.md` に移動、仕様書作成）

---

## ✅ 優先度ランキング（1が最優先）
1. ISSUE-052: 既存メディアのS3移行手順
2. ISSUE-055: RDS/ElastiCache移行・バックアップ・復旧運用
3. ISSUE-054: CloudWatchログ・監視・アラート・Runbook
4. ISSUE-034: Discord Webhook通知（MVP）
5. ISSUE-035: カレンダー購読（ICSフィードURL）（MVP）
6. ISSUE-011: APIドキュメント自動生成
7. ISSUE-010: テストカバレッジの向上
8. ISSUE-012: 非同期処理のアプリ統合
9. ISSUE-028: グループ間連携機能
10. ISSUE-036: カレンダー同期（Google Calendar等）（後続）
11. ISSUE-037: 外部シート連携API（外部キャラクターシート等）（後続）
12. ISSUE-047: リアルタイム通知（WebSocket）
13. ISSUE-048: ゲスト参加リンク・claim・募集統合
14. ISSUE-027: モバイルアプリ
15. ISSUE-029: AI分析/推奨機能

---

## 🔴 優先度: 高（AWSリリース）

### ISSUE-050: AWSリリース設定整備（Epic）

- **優先度順位**: -（Epic）
- **カテゴリ**: リリース準備（AWS）
- **影響範囲**: インフラ設定 / セキュリティ / ファイル配信 / 監視運用
- **背景**:
  - 現行の本番運用は `docs/DEPLOYMENT_GUIDE.md` の通り **Lightsail + Docker Compose + host certbot** 前提
  - `docker-compose.mysql.yml` は DB/Redis をコンテナ同居で運用する想定
  - `tableno/settings_production.py` はローカルファイル（`MEDIA_ROOT` / `LOG_DIR`）前提
  - AWSマネージド構成（ECS/RDS/ElastiCache/ALB/CloudWatch）で不足設定がある
- **分割（AWSリリース向け）**:
  - ISSUE-051: Secrets Manager/SSM 連携 + 必須環境変数の厳格化
  - ISSUE-052: S3/CloudFront による静的/メディア配信設定
  - ISSUE-053: ALB/ACM 前提のプロキシ/ヘルスチェック設定
  - ISSUE-054: CloudWatch ログ/監視/アラート整備
  - ISSUE-055: RDS/ElastiCache 接続設定 + 移行/バックアップ運用
- **作業計画**:
  - `docs/specifications/AWS_RELEASE_WORKPLAN.md`
- **実装内容**:
  - ✅ **AWS向け設定方針の確定** - 実装済み（ECS/Fargate + ALB/ACM + RDS + ElastiCache + S3/CloudFront）
  - 🔄 **個別チケットの完了** - 一部実装（運用監視、移行、復旧手順が残存）

### ISSUE-051: AWS Secrets Manager/SSM 連携 + 必須環境変数の厳格化

- **優先度順位**: 完了済み（ランキング対象外）
- **カテゴリ**: セキュリティ / 設定管理
- **影響範囲**: 認証、DB接続、外部API鍵、運用手順
- **詳細**:
  - 現状は `.env.production` に秘匿値を直接保持する運用
  - AWSリリース向けに、Secrets Manager/SSM を一次情報源に統一する
  - 本番起動時に必須環境変数不足を fail-fast で検出する
- **該当ファイル（予定）**:
  - `.env.production.example` / `.env.staging.example`
  - `tableno/settings.py` / `tableno/settings_production.py`
  - `docs/DEPLOYMENT_GUIDE.md` / `REQUIRED_SETTINGS.md`
- **実装内容**:
  - ✅ **Secretsの保管先定義（Secrets Manager / SSM）** - 実装済み（`REQUIRED_SETTINGS.md` / `docs/DEPLOYMENT_GUIDE.md`）
  - ✅ **必須キー検証（DB_PASSWORD, REDIS_URL, OAuth鍵 など）** - 実装済み（`tableno/settings_production.py`）
  - ✅ **秘密情報ローテーション手順の文書化** - 実装済み（`docs/SECRETS_ROTATION_RUNBOOK.md`）
  - ✅ **平文 `.env` 依存を最小化する起動手順** - 実装済み（JSON Secret読込対応: `AWS_SECRETS_JSON` / `AWS_SECRETS_FILE`）

### ISSUE-052: S3/CloudFront による静的/メディア配信設定

- **優先度順位**: 1
- **カテゴリ**: リリース準備（配信基盤）
- **影響範囲**: 画像アップロード、静的配信、パフォーマンス
- **詳細**:
  - 現状は `MEDIA_ROOT` と `nginx` のローカルボリューム配信
  - ECS/Fargate等ではローカル永続を前提にできないため、S3配信へ移行する
  - CloudFront を利用する場合の `MEDIA_URL` / `STATIC_URL` 設計が未整備
- **該当ファイル（予定）**:
  - `requirements.txt`
  - `tableno/settings_production.py`
  - `.env.production.example` / `.env.staging.example`
  - `docs/DEPLOYMENT_GUIDE.md`
- **実装内容**:
  - ✅ **`django-storages` + `boto3` 導入** - 実装済み
  - ✅ **S3バケット設定（static/media）** - 実装済み（`USE_S3_STORAGE=True` で有効）
  - ✅ **CloudFront配信URL設定** - 実装済み（`AWS_S3_CUSTOM_DOMAIN`）
  - ❌ **既存メディア移行手順（同期 + 切替）** - 未実装

### ISSUE-053: ALB/ACM 前提のプロキシ/ヘルスチェック設定

- **優先度順位**: 完了済み（ランキング対象外）
- **カテゴリ**: リリース準備（ネットワーク）
- **影響範囲**: SSL終端、リバースプロキシ、可用性
- **詳細**:
  - 現状の `nginx.conf` / `docs/DEPLOYMENT_GUIDE.md` は certbot + サーバー内SSL終端が前提
  - AWSでは ALB + ACM 終端を採用する場合が多く、設定責務の分離が必要
  - 監視用のアプリ実体ヘルスチェック（DB/Redis含む）の定義が不足
- **該当ファイル（予定）**:
  - `nginx.conf`
  - `docker-compose.mysql.yml`
  - `tableno/settings.py` / `tableno/settings_production.py`
  - `docs/DEPLOYMENT_GUIDE.md` / `REQUIRED_SETTINGS.md`
- **実装内容**:
  - ✅ **ALB前提の `X-Forwarded-*` / HTTPS判定の設定・単体検証** - 実装済み
  - ✅ **`/health/live` / `/health/ready` のアプリ側実装** - 実装済み
  - ✅ **ALBヘルスチェックパス・タイムアウト値の定義** - 実装済み（`docs/DEPLOYMENT_GUIDE.md`）
  - ✅ **ACM運用（AWSではcertbotを使用しない）の手順化** - 実装済み（`docs/AWS_ECS_SETUP_GUIDE.md`）

### ISSUE-054: CloudWatch ログ/監視/アラート整備

- **優先度順位**: 3
- **カテゴリ**: 運用監視
- **影響範囲**: 障害検知、保守、SLA
- **詳細**:
  - `tableno/settings_production.py` はローカルファイルロギング前提
  - AWS運用で必要な CloudWatch Logs / Metrics / Alarm の定義が未整備
  - エラー率・応答遅延・タスク異常停止の検知基準を明文化する必要がある
- **該当ファイル（予定）**:
  - `tableno/settings_production.py`
  - `docs/DEPLOYMENT_GUIDE.md`
  - （必要なら）運用Runbook新規作成
- **実装内容**:
  - ✅ **アプリログの標準出力化（JSON/構造化を含む）** - 実装済み（`LOG_TO_STDOUT`）
  - ❌ **CloudWatch Logs連携（web/celery/nginx）** - 未実装
  - ❌ **主要アラーム定義（5xx、CPU/Memory、DB接続失敗）** - 未実装
  - ❌ **一次対応Runbook作成** - 未実装

### ISSUE-055: RDS/ElastiCache 接続設定 + 移行/バックアップ運用

- **優先度順位**: 2
- **カテゴリ**: データ基盤
- **影響範囲**: DB/キャッシュ、可用性、障害復旧
- **詳細**:
  - 現状は `docker-compose.mysql.yml` でアプリとDB/Redis同居運用が基本
  - AWS本番で RDS / ElastiCache を使う場合の接続・TLS・移行・復旧手順が不足
- **該当ファイル（予定）**:
  - `.env.production.example` / `.env.staging.example`
  - `tableno/settings_production.py`
  - `docs/DEPLOYMENT_GUIDE.md` / `REQUIRED_SETTINGS.md`
- **実装内容**:
  - ✅ **RDS接続設定の必須化（HOST/PORT/USER/PASSWORD/SSL）** - 実装済み（`DB_SSL_MODE` / `DB_SSL_CA` 対応）
  - ✅ **ElastiCache接続設定（`rediss://` を含む）** - 実装済み（`REDIS_SSL_CERT_REQS` 対応）
  - ❌ **データ移行計画（dump/restore/切替手順）** - 未実装
  - ❌ **バックアップ/復旧手順（RPO/RTO基準）** - 未実装

---

## 🟡 優先度: 中

※ 優先度順位は上部の「優先度ランキング」を正とします。

### ISSUE-012: 非同期処理の導入検討

- **優先度順位**: 8
- **カテゴリ**: パフォーマンス改善
- **影響範囲**: 統計処理、エクスポート機能
- **詳細**:
  - 重い統計処理やエクスポート処理の非同期化
- **実装内容**:
  - 🔄 **Celery実行基盤** - 依存パッケージとComposeのworker/beat定義のみ
  - ❌ **バックグラウンドタスク** - 未実装
  - ❌ **進捗表示機能** - 未実装

### ISSUE-010: テストカバレッジの向上

- **優先度順位**: 7
- **カテゴリ**: テスト改善
- **影響範囲**: 全体
- **詳細**:
  - 現在基本テストは実装済み、詳細テストの追加が必要
- **該当ファイル**:
  - 各種テストファイル (test_*.py)
- **実装内容**:
  - ✅ **基本機能テスト** - 実装済み
  - ✅ **統合テスト** - 実装済み（個別実行結果は各テスト記録を参照）
  - ❌ **境界値テスト** - 未実装
  - ❌ **エラーケーステスト強化** - 未実装
  - ❌ **パフォーマンステスト** - 未実装

### ISSUE-011: APIドキュメント自動生成

- **優先度順位**: 6
- **カテゴリ**: ドキュメント
- **影響範囲**: API全般
- **詳細**:
  - OpenAPI/Swagger対応でAPI仕様書の自動生成
- **実装内容**:
  - ❌ **drf-spectacular導入** - 未実装
  - ❌ **エンドポイント説明追加** - 未実装
  - ❌ **スキーマ生成設定** - 未実装

---

## 🟢 優先度: 低

### ISSUE-028: グループ間連携機能

- **優先度順位**: 9
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

- **優先度順位**: 4
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

- **優先度順位**: 5
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

- **優先度順位**: 10
- **カテゴリ**: 外部連携
- **影響範囲**: スケジュール
- **詳細**:
  - OAuth連携でGoogle Calendar等へイベントを作成/更新/削除（双方向 or 片方向）
- **実装内容**:
  - ❌ **OAuth認可フロー** - 未実装
  - ❌ **イベント作成/更新の同期処理** - 未実装

### ISSUE-037: 外部シート連携API（外部キャラクターシート等）（後続）

- **優先度順位**: 11
- **カテゴリ**: 外部連携
- **影響範囲**: キャラクター管理/セッション管理
- **詳細**:
  - 外部サービス/スプレッドシート等との連携（参照/取込/エクスポート）
- **実装内容**:
  - ❌ **連携対象の確定（Google Sheets等）** - 未実装
  - ❌ **連携API/認可方式の設計** - 未実装

### ISSUE-047: リアルタイム通知（WebSocket）

- **優先度順位**: 12
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

- **優先度順位**: 14
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

- **優先度順位**: 15
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

### ISSUE-048: KP（GM）単体での卓運用（ゲスト参加/ログイン不要）

- **優先度順位**: 13
- **カテゴリ**: 機能強化
- **影響範囲**: セッション管理 / 募集 / キャラクター管理
- **詳細**:
  - `SessionParticipant.user` のnullable化とゲスト参加者の基本管理は実装済み
  - KP単体で参加者枠と外部キャラクター情報を管理できる
  - ログイン不要の参加表明、既存ゲスト枠のclaim、募集ページ統合は後続
- **該当ファイル（予定）**:
  - `schedules/models.py` - `SessionParticipant`（user nullable + guest fields + 制約見直し）
  - `schedules/serializers.py` - 参加者枠APIの拡張
  - `schedules/views.py` - 参加者枠管理APIの拡張
  - `templates/schedules/session_detail.html` - 参加者枠UI（ゲスト表示/編集）
  - `SESSION_HANDOUT_CHARACTER_SPEC.md` - 既存仕様（参加者枠/キャラ紐付け）との整合
- **実装内容（MVP案）**:
  - ✅ **ゲスト参加者（表示名）の登録/更新（GM）** - 実装済み
  - ✅ **プレイヤー枠（1-4）へのゲスト割当** - 実装済み
  - ✅ **ゲスト枠のキャラクター設定（名前/URL）** - 実装済み（内部 `CharacterSheet` はユーザー参加者のみ）
  - ✅ **DB制約/マイグレーション（user null時のユニーク等）** - 実装済み
  - ✅ **セッション詳細での参加者一覧表示** - 実装済み
  - ✅ **権限/バリデーション（GMのみ編集、既存招待と共存）** - 実装済み
  - ✅ **テスト** - 実装済み
- **後続案**:
  - ❌ **招待リンク/参加トークン（ログイン不要の参加表明）** - 未実装
  - ❌ **ゲスト枠のclaim（ログインユーザーへの紐付け/移行・連携）** - 未実装
    - API案: `POST /api/schedules/participants/{id}/claim/`（GM操作 or 参加者本人 + トークン等）
    - 引継ぎ対象: `player_slot` / `character_name` / `character_sheet_url` / `HandoutInfo.participant` の付け替え
    - 衝突処理: 既に user が参加者の場合、player_slot 重複時の扱い（エラー or 上書き/移動）
    - 監査: claim 実行者/日時の記録（最低限ログ、可能ならDB）
  - ❌ **募集ページへの統合（空き枠表示/締切/承認フロー）** - 未実装

---
