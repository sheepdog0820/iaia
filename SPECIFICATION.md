# Arkham Nexus - システム仕様書

**Gate of Yog-Sothoth** - 時空を超えるTRPGスケジュール管理サービス

## 1. システム概要

### 1.1 プロジェクト概要
Arkham Nexusは、クトゥルフ神話をテーマにしたTRPGスケジュール管理Webサービスです。TRPGセッションの管理、参加者の管理、プレイ履歴の記録など、TRPGライフを豊かにする機能を提供します。

### 1.2 技術スタック
- **Backend**: Django 4.2+, Django REST Framework
- **Database**: SQLite（開発）, **MySQL（本番）**
- **Frontend**: Bootstrap 5, カスタムCSS/JS（クトゥルフテーマ）
- **認証**: django-allauth（Google/Twitter OAuth）
- **インフラ**: Docker, Nginx, Gunicorn, Redis, Celery

## 2. システムアーキテクチャ

### 2.1 アプリケーション構成
```
arkham_nexus/
├── accounts/      # ユーザー管理アプリ
├── schedules/     # スケジュール管理アプリ  
├── scenarios/     # シナリオ管理アプリ
├── templates/     # HTMLテンプレート
├── static/        # 静的ファイル（CSS/JS）
└── media/         # アップロードファイル
```

### 2.2 データベース設計

#### 2.2.1 accounts アプリ

**CustomUser（カスタムユーザーモデル）**
- AbstractUserを継承
- 追加フィールド:
  - nickname: ニックネーム
  - trpg_history: TRPG参加履歴
  - profile_image: プロフィール画像
  - created_at/updated_at: タイムスタンプ

**Friend（フレンド関係）**
- user: ユーザー（FK）
- friend: フレンドユーザー（FK）
- created_at: 作成日時

**Group（グループ/Cult Circle）**
- name: グループ名
- description: 説明
- visibility: 可視性（private/public）
- members: メンバー（M2M through GroupMembership）
- created_by: 作成者（FK）
- created_at: 作成日時

**GroupMembership（グループメンバーシップ）**
- user: ユーザー（FK）
- group: グループ（FK）
- role: 役割（admin/member）
- joined_at: 参加日時

**GroupInvitation（グループ招待）**
- group: グループ（FK）
- inviter: 招待者（FK）
- invitee: 被招待者（FK）
- status: ステータス（pending/accepted/declined/expired）
- message: 招待メッセージ
- created_at/responded_at: タイムスタンプ

#### 2.2.2 schedules アプリ

**TRPGSession（セッション）**
- title: タイトル
- description: 説明
- date: 開催日時
- location: 場所
- youtube_url: YouTube配信URL
- status: ステータス（planned/ongoing/completed/cancelled）
- visibility: 可視性（private/group/public）
- gm: GM（FK）
- group: グループ（FK）
- participants: 参加者（M2M through SessionParticipant）
- duration_minutes: セッション時間（分）
- created_at/updated_at: タイムスタンプ

**SessionParticipant（セッション参加者）**
- session: セッション（FK）
- user: ユーザー（FK）
- role: 役割（gm/player）
- character_name: キャラクター名
- character_sheet_url: キャラクターシートURL

**HandoutInfo（ハンドアウト情報）**
- session: セッション（FK）
- participant: 参加者（FK）
- title: タイトル
- content: 内容
- is_secret: 秘匿フラグ
- created_at/updated_at: タイムスタンプ

#### 2.2.3 scenarios アプリ

**Scenario（シナリオ）**
- title: タイトル
- author: 作者
- game_system: ゲームシステム（coc/dnd/sw/insane/other）
- difficulty: 難易度（beginner/intermediate/advanced/expert）
- estimated_duration: 推定プレイ時間（short/medium/long/campaign）
- summary: 概要
- url: 参照URL
- recommended_players: 推奨人数
- player_count: 推奨プレイヤー数
- estimated_time: 推定プレイ時間（分）
- created_by: 作成者（FK）
- created_at/updated_at: タイムスタンプ

**ScenarioNote（シナリオメモ）**
- scenario: シナリオ（FK）
- user: ユーザー（FK）
- title: タイトル
- content: 内容
- is_private: プライベートフラグ
- created_at/updated_at: タイムスタンプ

**PlayHistory（プレイ履歴）**
- scenario: シナリオ（FK）
- user: ユーザー（FK）
- session: セッション（FK、nullable）
- played_date: プレイ日
- role: 役割（gm/player）
- notes: メモ
- created_at: 作成日時

## 3. 機能仕様

### 3.1 認証・認可

#### 3.1.1 ソーシャル認証
- Google OAuth認証
- Twitter OAuth認証
- django-allauthを使用した実装
- カスタムアダプターでプロフィール情報を自動取得

#### 3.1.2 デモログイン機能（開発環境のみ）
- `/accounts/demo/`でアクセス可能
- 実際のOAuth APIを使用せずに疑似ログイン
- Google/Twitterの固定デモアカウント

#### 3.1.3 権限管理
- Django標準の認証システム
- グループベースのアクセス制御
- セッション単位での参加者管理

### 3.2 ユーザー管理機能

#### 3.2.1 プロフィール管理
- プロフィール編集（`/accounts/profile/edit/`）
- ニックネーム、TRPG歴、プロフィール画像の管理
- ダッシュボード表示（`/accounts/dashboard/`）

#### 3.2.2 フレンド機能
- フレンド追加・削除
- フレンドリスト表示
- APIエンドポイント: `/api/accounts/friends/`

#### 3.2.3 グループ機能（Cult Circle）**【✅ 完全実装済み】**
- **グループ管理画面** (`/accounts/groups/view/`)
  - リアルタイムでのグループ作成・編集・削除
  - メンバー管理（admin/member権限）
  - グループ招待システム（招待送信・受諾・拒否）
  - 可視性設定（private/public）
  - CSRF保護とAJAXベースのUI
- **グループ権限管理**
  - admin: グループ設定変更、メンバー招待・除名権限
  - member: グループ閲覧・参加権限
- **招待システム**
  - 招待の送信・受諾・拒否機能
  - 招待ステータス管理（pending/accepted/declined/expired）
  - フレンド間での簡単招待機能

### 3.3 スケジュール管理機能

#### 3.3.1 セッション管理
- セッション作成・編集・削除
- ステータス管理（予定/進行中/完了/キャンセル）
- 可視性設定（プライベート/グループ内/公開）
- YouTube配信URL対応

#### 3.3.2 参加者管理
- GM/プレイヤー役割管理
- キャラクター情報管理
- キャラクターシートURL登録

#### 3.3.3 ハンドアウト機能
- セッション別ハンドアウト作成
- 秘匿ハンドアウト機能
- 参加者別の閲覧権限管理

#### 3.3.4 カレンダー表示
- 月間カレンダービュー
- セッション一覧表示
- 次回セッション表示

### 3.4 シナリオ管理機能

#### 3.4.1 シナリオアーカイブ（Mythos Archive）
- シナリオ情報登録・編集
- ゲームシステム別分類
- 難易度・推定プレイ時間設定

#### 3.4.2 プレイ履歴管理
- GM/プレイヤーとしてのプレイ記録
- プレイ日時・メモの記録
- セッションとの紐付け

#### 3.4.3 シナリオメモ機能
- 個人用メモ（プライベート）
- 共有メモ（パブリック）
- シナリオ別管理

### 3.5 統計・分析機能

#### 3.5.1 Tindalos Metrics（年間プレイ時間集計）
- 年間総プレイ時間
- 月別プレイ時間推移
- ゲームシステム別統計

#### 3.5.2 ユーザーランキング
- プレイ時間ランキング
- GM回数ランキング
- 参加セッション数ランキング

#### 3.5.3 グループ統計
- グループ別活動統計
- メンバー別貢献度

## 4. APIエンドポイント

### 4.1 認証関連
- `POST /accounts/login/` - ログイン
- `POST /accounts/signup/` - サインアップ
- `POST /accounts/logout/` - ログアウト
- `GET /accounts/demo/` - デモログインページ
- `GET /accounts/mock-social/<provider>/` - デモソーシャルログイン

### 4.2 ユーザー・グループ関連**【✅ 完全実装・動作確認済み】**
- `GET/POST /api/accounts/users/` - ユーザー管理
- `GET/POST /api/accounts/groups/` - グループ管理（権限チェック付き）
- `GET /api/accounts/groups/public/` - 公開グループ一覧
- `GET /api/accounts/groups/private/` - プライベートグループ一覧
- `GET /api/accounts/groups/all_groups/` - 全グループ一覧
- `POST /api/accounts/groups/<id>/join/` - 公開グループ参加
- `POST /api/accounts/groups/<id>/invite/` - メンバー招待
- `POST /api/accounts/groups/<id>/leave/` - グループ退出
- `DELETE /api/accounts/groups/<id>/remove_member/` - メンバー除名
- `GET/POST /api/accounts/friends/` - フレンド管理
- `GET/POST /api/accounts/invitations/` - 招待管理（自動inviter設定）
- `POST /api/accounts/invitations/<id>/accept/` - 招待受諾
- `POST /api/accounts/invitations/<id>/decline/` - 招待拒否
- `GET /api/accounts/profile/` - プロフィール取得
- `POST /api/accounts/friends/add/` - フレンド追加

### 4.3 統計・エクスポート関連
- `GET /api/accounts/statistics/tindalos/` - Tindalos Metrics
- `GET /api/accounts/statistics/ranking/` - ユーザーランキング
- `GET /api/accounts/statistics/groups/` - グループ統計
- `GET /api/accounts/export/statistics/` - 統計データエクスポート
- `GET /api/accounts/export/formats/` - エクスポート形式一覧

### 4.4 セッション関連**【✅ 実装済み】**
- `GET/POST /api/schedules/sessions/` - セッション管理
- `GET /api/schedules/sessions/view/` - セッション一覧API
- `GET /api/schedules/sessions/upcoming/` - 次回セッション
- `GET /api/schedules/sessions/statistics/` - セッション統計
- `GET /api/schedules/sessions/<id>/detail/` - セッション詳細
- `POST /api/schedules/sessions/<id>/join/` - セッション参加
- `DELETE /api/schedules/sessions/<id>/leave/` - セッション離脱
- `GET/POST /api/schedules/participants/` - 参加者管理
- `GET/POST /api/schedules/handouts/` - ハンドアウト管理
- `GET /api/schedules/calendar/` - カレンダー情報
- `POST /api/schedules/sessions/create/` - セッション作成

#### 4.4.1 Webビュー
- `GET /schedules/calendar/view/` - カレンダービュー
- `GET /schedules/sessions/web/` - セッション一覧ビュー

### 4.5 GM専用ハンドアウト管理**【✅ 実装済み】**
- `GET/POST /api/schedules/gm-handouts/` - GMハンドアウト管理
- `POST /api/schedules/gm-handouts/bulk_create/` - 一括ハンドアウト作成
- `GET /api/schedules/gm-handouts/by_session/` - セッション別ハンドアウト取得
- `POST /api/schedules/gm-handouts/toggle_visibility/` - 公開/秘匿切り替え
- `GET /api/schedules/handout-templates/` - ハンドアウトテンプレート一覧
- `POST /api/schedules/handout-templates/` - テンプレートからハンドアウト生成
- `GET /schedules/sessions/<int:session_id>/handouts/manage/` - GMハンドアウト管理画面

**ハンドアウト管理機能詳細**:
- 専用管理画面でのリアルタイム編集
- 参加者別ハンドアウト整理表示
- 秘匿/公開ステータスの即座切り替え
- テンプレートベースの効率的作成

### 4.6 シナリオ関連**【✅ 実装済み】**
- `GET/POST /api/scenarios/scenarios/` - シナリオ管理
- `GET/POST /api/scenarios/notes/` - シナリオメモ管理
- `GET/POST /api/scenarios/history/` - プレイ履歴管理
- `GET /api/scenarios/archive/` - シナリオアーカイブ
- `GET /api/scenarios/statistics/` - プレイ統計

#### 4.6.1 Webビュー
- `GET /scenarios/archive/view/` - シナリオアーカイブビュー

## 5. UI/UX仕様

### 5.1 デザインテーマ
- クトゥルフ神話をモチーフにしたダークテーマ
- エルドリッチフォント使用
- グロウエフェクト実装
- レスポンシブデザイン（スマートフォン対応）
- CSRF保護とAJAXベースのリアルタイムUI

### 5.2 主要画面**【✅ 全画面実装・動作確認済み】**
- ホーム画面（`/`）
- ログイン画面（Gate of Yog-Sothoth）
- ダッシュボード（`/accounts/dashboard/`）
- **グループ管理画面（`/accounts/groups/view/`）** - Cult Circle完全動作
- セッション一覧（`/schedules/sessions/web/`）
- カレンダー（`/schedules/calendar/view/`）
- シナリオアーカイブ（`/scenarios/archive/view/`）
- 統計画面（`/accounts/statistics/view/`）
- GMハンドアウト管理（`/schedules/sessions/<int:session_id>/handouts/manage/`）

### 5.3 JavaScript・UX機能
- **グローバルエラーハンドリング** (`static/js/arkham.js`)
  - ARKHAM.showSuccess() / showError() メソッド
  - 統一されたユーザーフィードバック
- **CSRF保護** (`templates/base.html`)
  - Axiosデフォルトヘッダー設定
  - 全AJAX通信でCSRFトークン自動付与

## 6. セキュリティ仕様

### 6.1 認証・認可
- セッションベース認証
- CSRF保護
- XSS対策（テンプレートエスケープ）

### 6.2 アクセス制御
- ログイン必須エリア
- グループベースの権限管理
- プライベートコンテンツの保護

### 6.3 本番環境セキュリティ
- HTTPS強制
- セキュリティヘッダー設定
- レート制限
- CORS設定

## 6.5 ハンドアウト管理機能

#### 6.5.1 GM専用ハンドアウト管理
- **GMハンドアウト管理画面** (`/schedules/sessions/<id>/handouts/manage/`)
  - セッション別ハンドアウト一覧表示
  - 参加者別ハンドアウト整理表示
  - リアルタイムでの作成・編集・削除
  - 公開/秘匿ステータスの切り替え

#### 6.5.2 ハンドアウトテンプレート機能
- **事前定義テンプレート**
  - 基本ハンドアウト（キャラクター情報と導入）
  - 調査ハンドアウト（調査系シナリオ用）
  - 関係性ハンドアウト（PC間関係定義）
- **テンプレートカスタマイズ**
  - プレースホルダー置換機能
  - カスタムフィールド対応

#### 6.5.3 ハンドアウト権限管理
- **GM権限**
  - 全ハンドアウトの閲覧・編集・削除
  - 秘匿/公開ステータスの管理
  - 一括作成・一括編集機能
- **参加者権限**
  - 自分宛ハンドアウトのみ閲覧可能
  - 公開ハンドアウトの閲覧

### 6.6 統計・エクスポート機能

#### 6.6.1 Tindalos Metrics（詳細実装済み）
- **年間プレイ統計**
  - 総セッション数、総プレイ時間
  - GM/PL別セッション数
  - セッション完了率
  - アクティブグループ数
- **月別統計**
  - 月別セッション数とプレイ時間
  - GM/PL別活動推移
- **ゲームシステム別統計**
  - システム別プレイ時間と回数

#### 6.6.2 データエクスポート機能
- **エクスポート形式**
  - CSV形式（Excel互換）
  - JSON形式（プログラム処理用）
  - PDF形式（レポート用、ReportLab使用）
- **エクスポート対象**
  - Tindalos Metrics（個人統計）
  - ユーザーランキング
  - グループ活動統計

#### 6.6.3 ユーザーランキング
- **ランキング種別**
  - プレイ時間ランキング
  - セッション参加数ランキング
  - GM回数ランキング
- **期間指定**
  - 年間、月間、全期間対応

#### 6.6.4 グループ統計
- **グループ別活動統計**
  - グループ別セッション数・プレイ時間
  - アクティブメンバー数
  - 上位GM情報

## 7. 未実装機能

### 7.1 キャラクターシート機能**【📋 仕様書作成済み・実装未着手】**
- **専用キャラクターシートアプリ**
  - 現在はSessionParticipantモデルのcharacter_sheet_urlフィールドで外部リンクのみ対応
  - 内蔵キャラクターシート作成・編集機能未実装
  - ゲームシステム別テンプレート未実装
  - 能力値計算・ダイスロール機能未実装
- **詳細仕様書**
  - `CHARACTER_SHEET_6TH_EDITION.md` - 6版仕様
  - `CHARACTER_SHEET_7TH_EDITION.md` - 7版仕様  
  - `CHARACTER_SHEET_TECHNICAL_SPEC.md` - 技術仕様
  - `CHARACTER_SHEET_SPECIFICATION.md` - 統合インデックス

### 7.2 グループ機能の拡張
- **可視性設定による詳細なアクセス制御**
  - パブリック/プライベートグループの表示制御は基本実装済み
  - グループ検索機能未実装
  - グループ間連携機能未実装

### 7.3 ハンドアウト機能の拡張
- **段階的な情報開示機能**
  - 条件付きハンドアウト表示未実装
  - タイムベース情報開示未実装

### 7.4 通知機能
- **リアルタイム通知システム**
  - セッション招待通知
  - スケジュール変更通知
  - フレンドリクエスト通知

### 7.5 モバイルアプリ
- **ネイティブモバイルアプリケーション**
  - iOS/Android対応
  - プッシュ通知
  - オフライン機能

### 7.6 外部連携
- **外部サービスとの連携**
  - Discord連携
  - カレンダーアプリ連携（Google Calendar等）
  - キャラクターシート管理サービス連携

### 7.7 高度な分析機能
- **AIを活用した分析・推奨機能**
  - プレイスタイル分析
  - シナリオ推奨機能
  - 最適なセッションマッチング

## 8. 開発・運用情報

### 8.1 開発環境
- Python 3.10+
- Django 4.2+
- SQLite（ローカル開発）
- Docker対応

### 8.2 デプロイメント
- **Docker Compose構成**
  - `docker-compose.yml` - PostgreSQL版（互換性用）
  - `docker-compose.mysql.yml` - **MySQL版（本番環境推奨）**
- Nginx + Gunicorn
- **MySQL 8.0+（本番DB）**
- Redis（キャッシュ・セッション）
- Celery（バックグラウンドタスク）

#### 8.2.1 本番環境データベース設定
- **データベースエンジン**: MySQL 8.0以上
- **文字エンコーディング**: utf8mb4（絵文字対応）
- **照合順序**: utf8mb4_unicode_ci
- **接続設定**: 
  ```python
  DATABASES = {
      'default': {
          'ENGINE': 'django.db.backends.mysql',
          'NAME': 'arkham_nexus_prod',
          'USER': 'arkham_user',
          'PASSWORD': os.environ.get('DB_PASSWORD'),
          'HOST': os.environ.get('DB_HOST', 'localhost'),
          'PORT': '3306',
          'OPTIONS': {
              'charset': 'utf8mb4',
              'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
          },
      }
  }
  ```

#### 8.2.2 MySQL設定要件
- **必要な権限**: CREATE, DROP, ALTER, SELECT, INSERT, UPDATE, DELETE
- **推奨設定**:
  - `innodb_buffer_pool_size`: 1GB以上
  - `max_connections`: 200以上
  - `character-set-server`: utf8mb4
  - `collation-server`: utf8mb4_unicode_ci

#### 8.2.3 データベース初期化手順
```sql
-- データベース作成
CREATE DATABASE arkham_nexus_prod CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- ユーザー作成と権限付与
CREATE USER 'arkham_user'@'%' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON arkham_nexus_prod.* TO 'arkham_user'@'%';
FLUSH PRIVILEGES;
```

#### 8.2.4 マイグレーション実行
```bash
# 本番環境でのマイグレーション
python manage.py makemigrations
python manage.py migrate --settings=arkham_nexus.settings_production

# 初期データ作成
python manage.py create_sample_data --settings=arkham_nexus.settings_production
```

### 8.3 管理コマンド
- `python manage.py create_sample_data` - サンプルデータ作成
- `python create_admin.py` - 管理者アカウント作成
- 詳細コマンド集は`CLAUDE.md`を参照

#### 8.3.1 本番環境専用コマンド
```bash
# MySQL接続テスト
python manage.py dbshell --settings=arkham_nexus.settings_production

# データベースバックアップ
mysqldump -u arkham_user -p arkham_nexus_prod > backup_$(date +%Y%m%d_%H%M%S).sql

# データベース復元
mysql -u arkham_user -p arkham_nexus_prod < backup_file.sql

# 本番環境でのテストデータクリア
python manage.py flush --settings=arkham_nexus.settings_production

# Docker ComposeでMySQL版を起動
docker-compose -f docker-compose.mysql.yml up -d

# Docker ComposeでPostgreSQL版を起動（互換性用）
docker-compose up -d
```

#### 8.3.2 環境別設定ファイル
- **.env.example** - 環境変数テンプレート
- **requirements.txt** - Python依存ライブラリ（mysqlclient含む）
- **docker-compose.mysql.yml** - MySQL版Docker構成
- **arkham_nexus/settings_production.py** - MySQL対応本番設定

### 8.4 テスト**【✅ 包括的テストスイート実装済み】**
- **ユニットテスト** - 各アプリの個別機能テスト
- **統合テスト** - 複数機能連携テスト (`test_integration.py`)
- **システム統合テスト** - エンドツーエンド業務フローテスト (`test_system_integration.py`)
- **テストランナー** - 包括的テスト実行ツール (`test_runner_comprehensive.py`)
- **テスト成功率**: 100% (16/16) - 全機能動作確認済み
- **テストカバレッジ**: 認証、セッション、シナリオ、グループ管理全機能

## 9. 今後の開発計画

### Phase 1（現在）
- 基本機能の実装完了
- デモ環境の構築

### Phase 2（計画中）
- 統計機能の詳細実装
- 通知システムの実装
- パフォーマンス最適化

### Phase 3（将来）
- モバイルアプリ開発
- 外部サービス連携
- AI機能の実装

---

## 更新履歴

### 2025-06-14 (最新更新)
- **Cult Circle（グループ管理）機能完全実装**
  - URL routing問題解決（templates vs API競合）
  - CSRF保護とAJAXベースUI実装
  - グループ招待システム完全動作（送信・受諾・拒否）
  - 権限管理（admin/member）完全実装
- **包括的統合テスト完了**
  - 全16テストスイート成功（100%）
  - ユーザー・グループ・セッション・シナリオ全機能動作確認
  - API実装とテスト整合性確保
- **キャラクターシート仕様書作成**
  - CoC 6版・7版別仕様書作成
  - 技術実装仕様書作成
  - 統合インデックス仕様書作成
- **開発環境最適化**
  - CLAUDE.md更新（音声通知機能追加）
  - デバッグツール群実装
  - URL解決デバッグスクリプト作成
- **API仕様の大幅拡張**
  - グループ管理API（公開/プライベート分離）
  - 招待システムAPI（accept/decline）
  - ハンドアウト管理API
  - エクスポート機能API

### 2025-06-14 (初版)
- 基本仕様の策定
- データベース設計
- 基本機能の定義

*最終更新日: 2025-06-14*