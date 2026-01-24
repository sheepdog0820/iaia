# タブレノ - システム仕様書

**Gate of Yog-Sothoth** - 時空を超えるTRPGスケジュール管理サービス

## 1. システム概要

### 1.1 プロジェクト概要
タブレノは、クトゥルフ神話をテーマにしたTRPGスケジュール管理Webサービスです。TRPGセッションの管理、参加者の管理、プレイ履歴の記録など、TRPGライフを豊かにする機能を提供します。

### 1.2 技術スタック
- **Backend**: Django 4.2+, Django REST Framework
- **Database**: SQLite3（開発環境）, MySQL/PostgreSQL（本番環境）
- **Frontend**: Bootstrap 5, カスタムCSS/JS（クトゥルフテーマ）, FullCalendar
- **認証**: django-allauth（Google/X/Discord OAuth）+ Django REST Framework（API経由）
- **インフラ**: Docker, Nginx, Gunicorn, Redis, Celery
- **環境設定**: ENV_FILE による明示的な環境切り替え

### 1.3 開発環境データベース

#### データベース構成
- **データベースエンジン**: SQLite3
- **データベースファイル**: `db.sqlite3`（プロジェクトルート）
- **文字コード**: UTF-8
- **タイムゾーン**: Asia/Tokyo

#### 開発用データ
- **管理者アカウント**: 
  - ユーザー名: admin
  - パスワード: arkham_admin_2024
- **サンプルデータ**:
  - ユーザー数: 12名
  - キャラクター数: 43体
  - セッション数: 11件
  - シナリオ数: 5本

#### データベース初期化コマンド
```bash
# データベースマイグレーション
python3 manage.py migrate

# スーパーユーザー作成
python3 create_admin.py

# サンプルデータ生成
python3 manage.py create_sample_data
```

### 1.4 環境設定管理

#### 環境別設定ファイル
- **開発環境**: `.env.development`
- **本番環境**: `.env.production`
- **テンプレート**: `.env.example`

#### 環境切り替え方法
```bash
# 開発環境（ENV_FILE で明示指定）
ENV_FILE=.env.development python3 manage.py runserver

# Stg/Prod（settings_production を使用）
ENV_FILE=.env.production python3 manage.py migrate --settings=tableno.settings_production
```

#### 設定ファイル構成
- `settings.py` は `.env` を自動で読み込まない
- `ENV_FILE` を指定した場合のみ `.env` を読み込み
- Stg/Prod は `ENV_FILE` + `tableno.settings_production` で明示的に切り替え

## 2. システムアーキテクチャ

### 2.1 アプリケーション構成
```
tableno/
├── accounts/      # ユーザー管理アプリ
├── schedules/     # スケジュール管理アプリ  
├── scenarios/     # シナリオ管理アプリ
├── templates/     # HTMLテンプレート
├── static/        # 静的ファイル（CSS/JS）
└── media/         # アップロードファイル
```

### 2.2 データベース設計

#### テーブル構成概要
現在のデータベースには40のテーブルが存在：

**アカウント関連テーブル**
- `accounts_customuser` - ユーザー情報
- `accounts_charactersheet` - キャラクターシート基本情報
- `accounts_charactersheet6th` - 6版キャラクターシート（レガシー）
- `accounts_characterskill` - キャラクタースキル
- `accounts_characterequipment` - キャラクター装備
- `accounts_characterimage` - キャラクター画像
- `accounts_characterbackground` - キャラクター背景情報
- `accounts_characterdicerollsetting` - ダイスロール設定
- `accounts_growthrecord` - 成長記録
- `accounts_skillgrowthrecord` - スキル成長記録
- `accounts_group` - グループ
- `accounts_groupmembership` - グループメンバーシップ
- `accounts_groupinvitation` - グループ招待
- `accounts_friend` - フレンド関係

**スケジュール関連テーブル**
- `schedules_trpgsession` - TRPGセッション
- `schedules_sessionparticipant` - セッション参加者
- `schedules_sessioninvitation` - セッション招待
- `schedules_sessionoccurrence` - セッション出現（複数日程対応）
- `schedules_sessionoccurrenceparticipant` - セッション出現参加者
- `schedules_sessionnote` - セッションノート
- `schedules_sessionlog` - セッションログ
- `schedules_sessionimage` - セッション画像
- `schedules_sessionyoutubelink` - YouTubeリンク
- `schedules_handoutinfo` - ハンドアウト情報
- `schedules_handoutattachment` - ハンドアウト添付ファイル
- `schedules_handoutnotification` - ハンドアウト/セッション通知
- `schedules_usernotificationpreferences` - ユーザー通知設定
- `schedules_sessionseries` - 定期セッション/キャンペーン
- `schedules_sessionavailability` - 参加可能日投票
- `schedules_datepoll` - 日程調整投票
- `schedules_datepolloption` - 日程調整候補日時
- `schedules_datepollvote` - 日程調整投票記録
- `schedules_datepollcomment` - 日程調整コメント

**シナリオ関連テーブル**
- `scenarios_scenario` - シナリオ
- `scenarios_playhistory` - プレイ履歴
- `scenarios_scenarionote` - シナリオメモ

**Django標準テーブル**
- `auth_*` - 認証関連
- `django_*` - Django管理関連
- `account_*` - django-allauth関連
- `socialaccount_*` - ソーシャル認証関連
- `authtoken_token` - APIトークン管理

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

**CharacterSheet（キャラクターシート）**
- user: 作成者（FK）
- edition: 版（6th）
- name: 探索者名
- recommended_skills: 推奨技能（JSON）
- source_scenario: 元シナリオ（FK、nullable）
- source_scenario_title: 元シナリオ名（キャッシュ）
- source_scenario_game_system: 元シナリオシステム（キャッシュ）
- created_at/updated_at: タイムスタンプ

#### 2.2.2 schedules アプリ

**TRPGSession（セッション）**

- title: タイトル
- description: 説明
- date: 開催日時（nullable、日程未定対応）
- location: 場所
- youtube_url: YouTube配信URL（単一URL）
- status: ステータス（planned/ongoing/completed/cancelled）
- visibility: 可視性（private/group/public）
- coc_edition: CoC版（6th/7th）
- gm: GM（FK）
- group: グループ（FK）
- scenario: シナリオ（FK、nullable）
- series: 定期セッションシリーズ（FK、nullable）
- participants: 参加者（M2M through SessionParticipant）
- duration_minutes: セッション時間（分）
- share_token: 公開共有トークン（UUID）
- created_at/updated_at: タイムスタンプ

**SessionParticipant（セッション参加者）**

- session: セッション（FK）
- user: ユーザー（FK）
- role: 役割（gm/player）
- player_slot: プレイヤー枠（1-4）
- character_sheet: キャラクターシート（FK、nullable）

**SessionInvitation（セッション招待）**

- session: セッション（FK）
- inviter: 招待者（FK）
- invitee: 被招待者（FK）
- status: ステータス（pending/accepted/declined/expired）
- created_at/responded_at: タイムスタンプ

**SessionOccurrence（セッション出現・複数日程対応）**

- session: セッション（FK）
- start_at: 開始日時
- content: セッション内容
- is_primary: プライマリ出現フラグ
- participants: 参加者（M2M）

**SessionNote（セッションノート）**

- session: セッション（FK）
- user: 作成者（FK）
- note_type: 種別（gm_private/public_summary/player_note/npc_memo/handover）
- title: タイトル
- content: 内容
- is_pinned: ピン留めフラグ

**SessionLog（セッションログ）**

- session: セッション（FK）
- user: 作成者（FK）
- event_type: イベント種別
- content: 内容
- timestamp: イベント時刻

**SessionImage（セッション画像）**

- session: セッション（FK）
- image: 画像ファイル
- order: 表示順序
- uploaded_by: アップロード者（FK）

**SessionYouTubeLink（YouTubeリンク）**

- session: セッション（FK）
- url: YouTube URL
- video_id: 動画ID
- title: タイトル
- duration_seconds: 再生時間
- thumbnail_url: サムネイルURL
- perspective: 視点（GM/PL1/全体など）
- part_number: パート番号
- note: 備考

**HandoutInfo（ハンドアウト情報）**

- session: セッション（FK）
- handout_number: ハンドアウト番号（HO1-HO4）
- assigned_player_slot: 割り当てプレイヤー枠
- title: タイトル
- content: 内容
- recommended_skills: 推奨技能
- is_secret: 秘匿フラグ
- created_at/updated_at: タイムスタンプ

**HandoutAttachment（ハンドアウト添付ファイル）**

- handout: ハンドアウト（FK）
- file: ファイル
- file_type: ファイルタイプ（image/pdf/audio/video/document）
- file_size: ファイルサイズ

**HandoutNotification（通知）**

- user: ユーザー（FK）
- notification_type: 通知種別（handout_created/published/updated/session_invitation/schedule_change/session_cancelled/session_reminder/group_invitation/friend_request/friend_request_accepted）
- is_read: 既読フラグ
- read_at: 既読日時
- metadata: メタデータ（JSON）

**UserNotificationPreferences（通知設定）**

- user: ユーザー（OneToOne）
- handout_notifications_enabled: ハンドアウト通知
- session_notifications_enabled: セッション通知
- group_notifications_enabled: グループ通知
- friend_notifications_enabled: フレンド通知
- email_notifications_enabled: メール通知
- browser_notifications_enabled: ブラウザ通知

**SessionSeries（定期セッション・キャンペーン）**

- name: 名称
- group: グループ（FK）
- scenario: シナリオ（FK、nullable）
- recurrence: 繰り返しパターン（none/weekly/biweekly/monthly/custom）
- weekday: 曜日（毎週/隔週の場合）
- day_of_month: 日（毎月の場合）
- start_time: 開始時刻
- duration_minutes: 予定時間
- custom_interval_days: カスタム間隔（日数）
- start_date/end_date: シリーズ期間
- auto_create_sessions: 自動生成フラグ
- auto_create_weeks_ahead: 自動生成週数

**SessionAvailability（参加可能日投票）**

- user: ユーザー（FK）
- session: セッション（FK、nullable）
- occurrence: セッション出現（FK、nullable）
- proposed_date: 候補日時（nullable）
- status: ステータス（available/maybe/unavailable）
- comment: コメント

**DatePoll（日程調整投票）**

- title: タイトル
- description: 説明
- group: グループ（FK）
- created_by: 作成者（FK）
- deadline: 投票締め切り
- is_closed: 締め切りフラグ
- selected_date: 確定日時
- create_session_on_confirm: 確定時にセッション自動作成

**DatePollOption（日程調整候補）**

- poll: 投票（FK）
- datetime: 候補日時
- note: 備考

**DatePollVote（日程調整投票記録）**

- option: 候補（FK）
- user: ユーザー（FK）
- status: ステータス（available/maybe/unavailable）
- comment: コメント

**DatePollComment（日程調整コメント）**

- poll: 投票（FK）
- user: ユーザー（FK）
- content: コメント内容
- created_at: 作成日時

#### 2.2.3 scenarios アプリ

**Scenario（シナリオ）**
- title: タイトル
- author: 作者
- game_system: ゲームシステム（coc/dnd/sw/insane/other）
- difficulty: 難易度（beginner/intermediate/advanced/expert）
- estimated_duration: 推定プレイ時間（short/medium/long/campaign）
- summary: 概要
- recommended_skills: 推奨技能（カンマ区切り）
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

#### 3.1.1 OAuth認証（API経由）
- Google OAuth認証（API経由）
- X（Twitter）OAuth認証（API経由）
- django-allauthとDjango REST Frameworkの統合
- OAuthトークンを使用したAPIアクセス

#### 3.1.2 API認証フロー
- OAuthプロバイダーでの認証後、APIトークンを発行
- トークンベース認証（rest_framework.authtoken）
- 認証ヘッダー: `Authorization: Token <token>`

#### 3.1.3 権限管理
- Django標準の認証システム
- グループベースのアクセス制御
- セッション単位での参加者管理

### 3.2 ユーザー管理機能

#### 3.2.1 プロフィール管理
- ダッシュボード表示（`/accounts/dashboard/`）
  - 統計（今年のセッション数/プレイ時間、参加グループ数、フレンド数）
  - 次回セッション、最近のアクティビティ
  - プロフィール概要（ユーザー名、ニックネーム、TRPG歴、プロフィール画像など）
  - **メールアドレスはセキュリティのため画面に表示しない**
- プロフィール編集（`/accounts/profile/edit/`）
  - ニックネーム、TRPG歴、プロフィール画像などの管理
  - （将来）TRPG自己紹介シート（3.2.4）の編集

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
- **アクセス制御修正**（ISSUE-001完了）
  - パブリックグループへの非メンバーアクセス制御修正
  - GroupViewSetのget_querysetメソッド改修
  - 管理者権限チェックの追加実装
- **実装上の補足**
  - 「リアルタイム」はAJAXによる再取得を指し、WebSocket等によるPush更新は未実装
  - `DELETE /api/accounts/groups/<id>/remove_member/` は `user_id` または `username` の指定が必須

#### 3.2.4 TRPG自己紹介シート（プロフィール詳細）
- **目的**
  - 卓参加前にプレイスタイル/嗜好/NG（地雷）を共有し、KP/PL間の期待値ズレを減らす
  - KPのシナリオ選定・演出調整の補助
- **想定利用シーン**
  - オンラインセッション（Discord / CCFOLIA 等）
  - 募集卓・身内卓・キャンペーン卓
- **公開範囲**
  - 全体公開 / 卓参加者のみ / KPのみ
- **入力項目（案）**
  - **プレイヤー基本情報**
    - プレイヤー名（HN、表示名）
    - TRPG歴（年数/初心者/経験者など）
    - 主なプレイ環境（オンライン/オフライン）
    - 使用ツール（Discord / CCFOLIA / Roll20 等、複数）
  - **対応システム**
    - プレイ経験システム（複数 + その他自由記述）
    - 得意/好きなシステム（複数）
  - **シナリオ傾向の好み**
    - シナリオ構造（一本道/半自由/完全自由）
    - プレイ感（エスカレーター型/探索重視）
    - ボリューム（短編/中編/長編）
    - 嗜好（複数）：ストーリー重視/キャラロール重視/ギミック・謎解き重視/バトル重視/ホラー演出重視
    - 結末の好み（ハッピー/ビター/バッド）
    - ロスト（OK/条件付きOK/NG）※条件付きの場合は補足欄
  - **キャラクタープレイ傾向**
    - ロールプレイスタイル（複数）：積極的に喋る/控えめ/内面描写が好き/セリフ重視/行動重視
    - 得意・好きな役割（複数）：ムードメーカー/ツッコミ役/シリアス枠/狂気・異常枠/サポート役
  - **PvP・対立要素**
    - 軽度の対立（OK/NG）
    - PvP（OK/条件付きOK/NG）
    - 裏切り・秘密（OK/条件付きOK/NG）
    - 条件付きの補足（自由記述）
  - **NG要素（安全設計）**
    - 表現面のNG（複数）：過度なグロ/性的表現/児童への加害描写/精神疾患の強調描写/動物虐待描写
    - プレイ面のNG（複数）：PL間の煽り・暴言/キャラ否定/無断PvP/強制ロスト
    - 事前共有方法（セッション前に共有してほしい/KPのみ把握でOK）
  - **セッション進行の希望**
    - セッションテンポ（ゆっくり/普通/テンポ重視）
    - 演出量（多め/普通/最小限）
    - KP裁定へのスタンス（KP裁定を尊重/相談しながら進めたい）
  - **フリーコメント**
    - 自己PR、補足、KPへの一言など
- **実装・運用補足（WEB向け）**
  - DB管理前提（チェック項目は列挙型、自由記述は文字数制限）
  - 一部項目は「条件付き」の場合のみ補足入力を表示（例：ロスト/PvP/裏切り）

### 3.3 スケジュール管理機能

#### 3.3.1 セッション管理

- セッション作成・編集・削除
- ステータス管理（予定/進行中/完了/キャンセル）
- 可視性設定（プライベート/グループ内/公開）
- 日程未定セッション対応（date nullable）
- CoC版指定（6th/7th）
- YouTube配信URL対応（単一URL）
- シナリオ連携（任意）
  - シナリオからセッション作成時にscenario_idを保持
  - セッション詳細で元シナリオ情報を表示
- **セッション画像機能**【✅ 実装済み】
  - 複数画像のアップロード（単体/一括）
  - 画像の表示順序管理
  - 権限ベースの削除機能
- **YouTubeリンク機能**【✅ 実装済み】
  - 複数のYouTube動画リンク管理
  - 動画情報の自動取得（タイトル、再生時間、サムネイル）
  - 視点情報（GM視点/PL視点など）
  - パート番号管理（分割動画対応）
  - 各動画への備考追加
  - UI実装済み（並び替えUI含む）
- **セッションノート・ログ機能**【✅ 実装済み】
  - GMプライベートノート、公開サマリー、プレイヤーノート
  - NPCメモ、引き継ぎノート
  - 時系列イベントログ
  - ピン留め機能
- **公開共有機能**【✅ 実装済み】
  - share_tokenによる認証なし閲覧

#### 3.3.2 参加者管理

- GM/プレイヤー役割管理
- プレイヤー枠（1-4）と重複チェック
- キャラクターシート直接紐付け
- 協力GM（Co-GM）追加機能
- セッション招待機能（通知連携）

#### 3.3.3 ハンドアウト機能

- セッション別ハンドアウト作成（HO1-HO4）
- 秘匿ハンドアウト機能
- プレイヤー枠への割り当て
- 推奨技能設定
- 添付ファイル機能（画像/PDF/音声/動画/文書）
- ファイルサイズ制限・MIMEタイプ検証

#### 3.3.4 カレンダー表示

- 月間カレンダービュー（FullCalendar）
- セッション一覧表示
- 次回セッション表示
- シナリオ連携時はクエリからシナリオ情報を受け取り、セッション作成モーダルを自動表示
- iCalエクスポート機能

#### 3.3.5 高度なスケジューリング機能【✅ 実装済み】

- **定期セッション（SessionSeries）**
  - 繰り返しパターン（毎週/隔週/毎月/カスタム）
  - 自動セッション生成
  - キャンペーン管理
- **参加可能日投票（SessionAvailability）**
  - ◯/△/✕での回答
  - コメント機能（遅刻/早退など）
- **日程調整投票（DatePoll）**
  - 複数候補日時への投票
  - 投票サマリー取得
  - 日程確定時にセッション自動作成
  - チャットコメント機能
- **セッション出現（SessionOccurrence）**
  - 単一セッションで複数日程対応

#### 3.3.6 通知機能【✅ 実装済み】

- **通知種別**
  - ハンドアウト作成/公開/更新通知
  - セッション招待/スケジュール変更/キャンセル/リマインダー通知
  - グループ招待通知
  - フレンドリクエスト/承認通知
- **通知管理**
  - 未読/既読管理
  - 通知設定（種別ごとのON/OFF）
  - メール/ブラウザ通知設定

### 3.4 シナリオ管理機能

#### 3.4.1 シナリオアーカイブ（Mythos Archive）
- シナリオ情報登録・編集
- ゲームシステム別分類
- 難易度・推定プレイ時間設定
- 詳細モーダルから「このシナリオでセッションを計画」導線
  - scenario_id / scenario_title / game_system を引き継ぎ

#### 3.4.2 プレイ履歴管理
- GM/プレイヤーとしてのプレイ記録
- プレイ日時・メモの記録
- セッションとの紐付け

#### 3.4.3 シナリオメモ機能
- 個人用メモ（プライベート）
- 共有メモ（パブリック）
- シナリオ別管理

#### 3.4.4 シナリオ→セッション→キャラ作成連携（推奨技能）
- シナリオ詳細から「このシナリオでセッションを計画」でカレンダーへ遷移
  - URLクエリとlocalStorageで scenario_id / scenario_title / game_system を保持
- セッション作成時にscenario_idを保存し、セッション詳細でシナリオ情報を表示
- セッション詳細から「探索者作成」でキャラクター作成へ遷移
  - scenario_id / scenario_title / game_system / recommended_skills を引き継ぎ
- キャラクター保存時に source_scenario / source_scenario_title / source_scenario_game_system を保持
- 推奨技能はCoC 6版の技能キー/名称に対応（未知キーは警告対象）
- 推奨技能が未指定の場合はscenario_idからAPI取得
  - 非同期取得で操作を阻害しない
  - 8秒タイムアウト、失敗時は再試行導線
  - 推奨技能が空の場合は「推奨技能なし」のヒント表示
- 推奨技能UI: 手動追加 / クリア / シナリオ反映（自動反映は未設定時のみ）

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
- `POST /api/auth/google/` - Google OAuth認証（API経由）
- `POST /api/auth/twitter/` - X（Twitter）OAuth認証（API経由）
- `POST /api/auth/logout/` - APIログアウト（トークン無効化）
- `GET /api/auth/user/` - 現在のユーザー情報取得
- `POST /api/auth/token/refresh/` - トークン更新

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
  - リクエストボディ: `user_id` または `username`
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
  - レスポンス: `group(id,name)` / `group_id` / `group_name` / `member_count` / `session_count` / `total_play_time`
  - 追加: `total_hours` / `average_session_hours` / `active_members` / `top_gm` / `top_gm_sessions` / `member_contributions`
  - 完了セッションが無いグループは返却対象外
- `GET /api/accounts/export/statistics/` - 統計データエクスポート
- `GET /api/accounts/export/formats/` - エクスポート形式一覧

### 4.4 セッション関連【✅ 実装済み】

- `GET/POST /api/schedules/sessions/` - セッション管理
- `GET /api/schedules/sessions/view/` - セッション一覧API
- `GET /api/schedules/sessions/upcoming/` - 次回セッション
- `GET /api/schedules/sessions/statistics/` - セッション統計
- `GET /api/schedules/sessions/<id>/detail/` - セッション詳細
- `GET /api/schedules/sessions/<id>/date-poll/` - セッション日程調整投票
- `POST /api/schedules/sessions/<id>/join/` - セッション参加
- `POST /api/schedules/sessions/<id>/register/` - セッション登録
- `DELETE /api/schedules/sessions/<id>/leave/` - セッション離脱
- `POST /api/schedules/sessions/<id>/invite/` - 参加者招待
- `POST /api/schedules/sessions/<id>/add_co_gm/` - 協力GM追加
- `POST /api/schedules/sessions/<id>/assign_player/` - プレイヤー枠割り当て
- `GET/POST /api/schedules/participants/` - 参加者管理
- `GET/POST /api/schedules/handouts/` - ハンドアウト管理
- `GET /api/schedules/calendar/` - カレンダー情報
- `POST /api/schedules/sessions/create/` - セッション作成
- セッション作成/更新時に `scenario`（id）を指定可能
- `GET /api/schedules/sessions/<id>/detail/` は `scenario_detail`（id/title/game_system/recommended_skills）を返却

#### 4.4.1 セッション出現（複数日程）

- `GET/POST /api/schedules/occurrences/` - 出現一覧・作成
- `GET/PATCH/DELETE /api/schedules/occurrences/<id>/` - 出現詳細・更新・削除

#### 4.4.2 セッション招待

- `GET /api/schedules/session-invitations/` - 招待一覧
- `POST /api/schedules/session-invitations/<id>/accept/` - 招待受諾
- `POST /api/schedules/session-invitations/<id>/decline/` - 招待辞退

#### 4.4.3 セッションノート・ログ

- `GET/POST /api/schedules/notes/` - ノート一覧・作成
- `GET/POST /api/schedules/sessions/<id>/notes/` - セッションのノート一覧・作成
- `GET/POST /api/schedules/logs/` - ログ一覧・作成
- `GET/POST /api/schedules/sessions/<id>/logs/` - セッションのログ一覧・作成

#### 4.4.4 セッション画像

- `GET/POST /api/schedules/session-images/` - 画像一覧・アップロード
- `DELETE /api/schedules/session-images/<id>/` - 画像削除
- `PATCH /api/schedules/session-images/<id>/reorder/` - 画像並び替え
- `POST /api/schedules/session-images/bulk_upload/` - 一括アップロード

#### 4.4.5 YouTubeリンク

- `GET/POST /api/schedules/youtube-links/` - 動画リンク一覧・追加
- `GET/POST /api/schedules/sessions/<id>/youtube-links/` - セッションの動画一覧・追加
- `GET /api/schedules/sessions/<id>/youtube-links/statistics/` - 動画統計
- `PATCH /api/schedules/youtube-links/<id>/reorder/` - 動画並び替え
- `POST /api/schedules/youtube-links/<id>/fetch_info/` - YouTube情報取得

#### 4.4.6 高度なスケジューリング

- `GET/POST /api/schedules/session-series/` - シリーズ一覧・作成
- `GET/PATCH/DELETE /api/schedules/session-series/<id>/` - シリーズ詳細・更新・削除
- `POST /api/schedules/session-series/<id>/generate_sessions/` - セッション自動生成
- `GET /api/schedules/session-series/<id>/sessions/` - シリーズのセッション一覧
- `GET/POST /api/schedules/availability/` - 参加可能日投票一覧・作成
- `GET /api/schedules/availability/for_session/` - セッションの投票
- `POST /api/schedules/availability/vote/` - 投票を記録
- `GET/POST /api/schedules/date-polls/` - 日程調整一覧・作成
- `GET/PATCH /api/schedules/date-polls/<id>/` - 日程調整詳細・更新
- `POST /api/schedules/date-polls/<id>/vote/` - 日程調整投票
- `POST /api/schedules/date-polls/<id>/confirm/` - 日程確定
- `POST /api/schedules/date-polls/<id>/add_option/` - 候補日時追加
- `GET /api/schedules/date-polls/<id>/summary/` - 投票サマリー
- `GET/POST /api/schedules/date-polls/<id>/comments/` - コメント一覧・投稿

#### 4.4.7 カレンダー機能

- `GET /api/schedules/calendar/` - カレンダー情報
- `GET /api/schedules/calendar/view/` - カレンダーHTML
- `GET /api/schedules/calendar/monthly/` - 月別イベント一覧
- `GET /api/schedules/calendar/aggregation/` - セッション集計
- `GET /api/schedules/calendar/export/ical/` - iCal形式エクスポート

#### 4.4.8 通知

- `GET /api/schedules/notifications/` - 通知一覧（未読フィルター対応）
- `PATCH /api/schedules/notifications/<id>/mark_read/` - 通知を既読化
- `PATCH /api/schedules/notifications/mark_all_read/` - 全通知を既読化
- `GET /api/schedules/notifications/unread_count/` - 未読件数
- `GET/PATCH /api/schedules/notification-preferences/` - 通知設定取得・更新

#### 4.4.9 Webビュー

- `GET /schedules/calendar/view/` - カレンダービュー
- `GET /schedules/sessions/web/` - セッション一覧ビュー
- `GET /schedules/sessions/<id>/date-poll/` - 日程調整投票画面
- `GET /s/<uuid:share_token>/` - 公開セッション詳細

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
- セッション詳細（`/api/schedules/sessions/<id>/detail/`）
- カレンダー（`/schedules/calendar/view/`）
- シナリオアーカイブ（`/scenarios/archive/view/`）
- 6版キャラクター作成（`/accounts/character/create/6th/`）
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
- OAuth認証（Google/X）とAPIトークンの統合
- CORS設定（認証ヘッダー許可）
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

## 6.5 ハンドアウト管理機能**【✅ 完全実装済み】**

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

#### 6.5.4 実装詳細**（ISSUE-009完了）**
- **ファイル構成**
  - `schedules/handout_views.py` - GMハンドアウト管理API
  - `schedules/models.py` - HandoutAttachment, UserNotificationPreferences
  - `schedules/notification_views.py` - 通知機能
- **主要機能**
  - ハンドアウト一括作成・編集・削除
  - 配布状況のリアルタイム確認
  - ファイル添付機能（HandoutAttachment）
  - 通知機能（ハンドアウト配布通知）
  - 秘匿/公開ステータスの即座切り替え

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

#### 6.6.2 データエクスポート機能**【✅ 完全実装済み】**
- **エクスポート形式**
  - CSV形式（Excel互換）
  - JSON形式（プログラム処理用）
  - PDF形式（レポート用、ReportLab使用）
- **エクスポート対象**
  - Tindalos Metrics（個人統計）
  - ユーザーランキング
  - グループ活動統計
- **API実装詳細**（ISSUE-002完了）
  - `/api/accounts/export/formats/` - エクスポート形式一覧API
  - `/api/accounts/export/statistics/` - 統計データエクスポートAPI
  - 日付範囲指定機能（start_date, end_date パラメータ）
  - ユーザーデータ分離とセキュリティ
  - エラーハンドリングとフォールバック機能
  - パフォーマンス最適化（5秒以内処理保証）

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
- **メンバー別貢献度**
  - GM/PL回数とプレイ時間の集計を返却
  - 完了セッションが無いグループは返却対象外

## 7. 未実装・部分実装機能

### 7.1 キャラクターシート機能【✅ 完成】

- **基本キャラクターシート機能**【✅ 実装済み】
  - CharacterSheet, CharacterSkill, CharacterEquipmentモデル実装
  - 6版キャラクター作成画面（`/accounts/character/create/6th/`）
  - 基本能力値・技能・装備管理
  - 技能ポイント管理システム
  - 成長記録システム
  - 戦闘データ管理
  - 所持品・装備管理
  - 背景情報詳細化
- **CCFOLIA連携機能**【✅ 実装済み】
  - CCFOLIA形式エクスポートAPI（`/api/accounts/character-sheets/{id}/ccfolia-json/`）
  - 公式CCFOLIA仕様準拠のデータ形式
  - コマンド文字列生成（技能ロール、正気度ロール、基本判定）
  - 一括エクスポート機能
  - 同期機能（sync_to_ccfolia）
- **7版キャラクターシート**【🔄 開発保留中】
  - 6版完成後に開発予定
- **詳細仕様書**
  - `CHARACTER_SHEET_COC6TH.md` - 6版仕様（完全版）
  - `CHARACTER_SHEET_7TH_DEVELOPMENT_HOLD.md` - 7版開発保留

### 7.2 グループ機能の拡張

- **グループ間連携機能**【❌ 未実装】
  - グループ連携モデル
  - 連携申請/承認フロー
  - 共有範囲設定

### 7.3 ハンドアウト機能の拡張

- **段階的な情報開示機能**【❌ 未実装】
  - 条件付きハンドアウト表示
  - 公開予定日時
  - 閲覧権限の動的判定

### 7.4 YouTubeリンク機能

- **並び替えUI**【✅ 実装済み】
  - ドラッグ&ドロップで並び替え、GMのみ保存可能

### 7.5 外部連携

- **Discord Webhook通知**【❌ 未実装】
  - セッション招待/更新/キャンセル通知
  - Webhook URL保存
- **カレンダー購読（ICSフィード）**【❌ 未実装】
  - 購読用ICSフィードエンドポイント
  - 購読トークン発行/再発行
  - ICSエクスポート（ファイルDL）は実装済み
- **カレンダー同期（Google Calendar等）**【❌ 未実装】
  - OAuth連携
  - イベント作成/更新の同期処理
- **外部シート連携API**【❌ 未実装】
  - 外部サービス/スプレッドシート連携

### 7.6 セッション準備・事後処理

- **セッション準備チェックリスト**【❌ 未実装】
  - チェック項目CRUD
  - 完了/未完了トグル
- **セッション後フィードバック**【❌ 未実装】
  - 参加者のフィードバック投稿
  - 平均評価など簡易サマリー
- **経験値配布**【❌ 未実装】
  - 配布内容の記録
  - キャラクター成長記録への反映
- **セッションテンプレート**【❌ 未実装】
  - テンプレートCRUD
  - テンプレートからセッション作成

### 7.7 統計・分析機能の拡張

- **セッション分析ダッシュボード**【❌ 未実装】
  - 参加率分析
  - 人気時間帯分析
  - GM負荷分析
  - プレイヤー相性分析
- **グループ統計詳細**【🔄 部分実装】
  - 基本統計・メンバー貢献度は実装済み
  - メンバー参加率（%算出）未実装
  - 人気シナリオランキング未実装
- **ユーザーランキング詳細**【🔄 部分実装】
  - 基本ランキングは実装済み
  - 期間別ランキング（year以外）未実装
  - カテゴリ別ランキング未実装
  - ランキング推移未実装

### 7.8 モバイルアプリ

- **ネイティブモバイルアプリケーション**【❌ 未実装】
  - iOS/Android対応
  - プッシュ通知
  - オフライン機能

### 7.9 高度な分析機能

- **AIを活用した分析・推奨機能**【❌ 未実装】
  - プレイスタイル分析
  - シナリオ推奨機能
  - 最適なセッションマッチング

### 7.10 非同期処理

- **Celery導入**【❌ 未実装】
  - 重い統計処理の非同期化
  - エクスポート処理の非同期化
  - 進捗表示機能

### 7.11 APIドキュメント

- **OpenAPI/Swagger対応**【❌ 未実装】
  - drf-spectacular導入
  - エンドポイント説明追加
  - スキーマ生成設定

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
          'NAME': 'tableno_prod',
          'USER': 'tableno_user',
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
CREATE DATABASE tableno_prod CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- ユーザー作成と権限付与
CREATE USER 'tableno_user'@'%' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON tableno_prod.* TO 'tableno_user'@'%';
FLUSH PRIVILEGES;
```

#### 8.2.4 マイグレーション実行
```bash
# 本番環境でのマイグレーション
python manage.py makemigrations
python manage.py migrate --settings=tableno.settings_production

# 初期データ作成
python manage.py create_sample_data --settings=tableno.settings_production
```

### 8.3 管理コマンド
- `python manage.py create_sample_data` - サンプルデータ作成
- `python create_admin.py` - 管理者アカウント作成
- 詳細コマンド集は`CLAUDE.md`を参照

#### 8.3.1 本番環境専用コマンド
```bash
# MySQL接続テスト
python manage.py dbshell --settings=tableno.settings_production

# データベースバックアップ
mysqldump -u tableno_user -p tableno_prod > backup_$(date +%Y%m%d_%H%M%S).sql

# データベース復元
mysql -u tableno_user -p tableno_prod < backup_file.sql

# 本番環境でのテストデータクリア
python manage.py flush --settings=tableno.settings_production

# Docker ComposeでMySQL版を起動
ENV_FILE=.env.production docker compose -f docker-compose.mysql.yml up -d

# Docker ComposeでPostgreSQL版を起動（互換性用）
docker compose up -d
```

#### 8.3.2 環境別設定ファイル
- **.env.example** - 環境変数テンプレート
- **requirements.txt** - Python依存ライブラリ（mysqlclient含む）
- **docker-compose.mysql.yml** - MySQL版Docker構成
- **tableno/settings_production.py** - MySQL対応本番設定

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

### 2026-01-18 (最新更新)

- **仕様書全面更新**
  - 現在の実装状況を反映
  - スケジュール管理機能の詳細化
  - APIエンドポイント一覧の更新
  - 未実装機能の整理

### 2026-01-16

- **高度なスケジューリング機能完成（ISSUE-017）**
  - 定期セッション（SessionSeries）
  - 参加可能日投票（SessionAvailability）
  - 日程調整投票（DatePoll）+ チャットコメント
  - セッション出現（SessionOccurrence）
- **通知機能拡張完了（ISSUE-013）**
  - フレンドリクエスト/承認通知追加

### 2026-01-15

- **参加予定セッション一覧（ISSUE-030）**
- **セッションノート・ログUI統合（ISSUE-014）**

### 2025-12-31

- **X OAuth認証実装（ISSUE-022）**
- **シナリオ→セッション→キャラ作成連携（ISSUE-024）**
- **推奨技能入力品質向上（ISSUE-025）**

### 2025-12-30

- **Google OAuth API認証実装（ISSUE-020）**
- **リリース前必須タスク完了（ISSUE-021）**
- **セッション統合テスト修正（ISSUE-024）**

### 2025-07-13

- **キャラクターシート6版機能完成（ISSUE-004）**
  - 成長記録システム
  - 技能ポイント管理システム
  - 戦闘データ管理
  - 所持品・装備管理
  - 背景情報詳細化

### 2025-06-20

- **Tindalos統計詳細実装（ISSUE-005）**
- **カレンダー統合API実装（ISSUE-008）**

### 2025-06-18

- **CCFOLIA連携機能実装（ISSUE-003）**
- **ハンドアウト一括管理機能（ISSUE-009）**

### 2025-06-14

- **Cult Circle（グループ管理）機能完全実装**
- **エクスポート機能API実装（ISSUE-002）**
- **パブリックグループアクセス制御修正（ISSUE-001）**

### 2025-06-14 (初版)

- 基本仕様の策定
- データベース設計
- 基本機能の定義

*最終更新日: 2026-01-18*
