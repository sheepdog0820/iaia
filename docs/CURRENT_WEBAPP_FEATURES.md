# タブレノ（Tableno）現状のWEBアプリ機能一覧（2026-01-07 時点）

この文書は、リポジトリ内の `urls.py` / モデル / テンプレート / 既存ドキュメントをもとに「現時点で利用できる機能」を整理したものです。

## 凡例（完成度）

- **完成**: UI（画面）とAPI（バックエンド）が揃い、主要フローが一通り動く
- **一部完成**: 実装はあるが、UI未対応・運用設定が未設定だと使えない・機能範囲が限定的
- **未完成**: 仕様/設計はあるが未実装、または将来案のみ

## 0. アプリ全体の構成（概要）

- **方式**: Django（テンプレート + Bootstrap + JS/Axios）を中心に、DRF（API）を併設
- **認証**:
  - **Web**: セッション認証（ログイン/ログアウト）
  - **API**: DRF Token 認証（`Authorization: Token ...`）も利用可能
- **主要画面導線**: `templates/base.html` のナビゲーション + `static/js/arkham.js` による画面遷移
  - カレンダー: `/api/schedules/calendar/view/`
  - セッション: `/api/schedules/sessions/view/`
  - シナリオ: `/api/scenarios/archive/view/`
  - グループ: `/accounts/groups/view/`
  - 統計: `/accounts/statistics/view/`

---

## 1. 認証・アカウント

### 1.1 ログイン/サインアップ（メール/パスワード）

- **内容**
  - サインアップ（ユーザー作成）
  - ログイン/ログアウト
  - ログイン後の遷移（ダッシュボード）
- **画面**
  - ログイン: `/login/`（カスタムログイン画面）
  - サインアップ: `/signup/`
  - ログアウト: `/accounts/logout/`
- **状態**: **完成**

### 1.2 プロフィール管理/アカウント削除

- **内容**
  - プロフィール編集（ニックネーム、TRPG歴、プロフィール画像）
  - ダッシュボード（今年のセッション数/時間、参加グループ数、フレンド数、最近履歴など）
    - メールアドレスはセキュリティのため非表示
  - TRPG自己紹介シート（プレイスタイル/嗜好/NG要素など）※仕様あり、未実装
  - アカウント削除（確認語 + パスワード確認 ※パスワードを持つ場合）
- **画面**
  - ダッシュボード: `/accounts/dashboard/`
  - プロフィール編集: `/accounts/profile/edit/`
  - アカウント削除: `/accounts/profile/delete/`
- **状態**: **一部完成**

### 1.3 ソーシャルログイン（Google）

- **内容**
  - **Web**: django-allauth を用いた Google OAuth ログイン
  - **API**: `POST /api/auth/google/`（`code`/`access_token`/`id_token` のいずれかで認証 → DRFトークン発行）
- **必要設定（代表）**
  - `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`
  - allauth の `SocialApp` 設定（スクリプト/管理画面で作成）
- **状態**: **一部完成**（実装はあるが、OAuth設定がないと利用不可）

### 1.4 ソーシャルログイン（X / Twitter OAuth2）

- **内容**
  - **Web**: django-allauth を用いた X OAuth2 ログイン
  - **API**: `POST /api/auth/twitter/`（`code` + `code_verifier` でPKCE対応 → DRFトークン発行）
  - **APIでの手動連携**:
    - 認証済みユーザーが `POST /api/auth/twitter/` を叩くと、現在ユーザーへ X を紐付け
    - 既に別ユーザーへ紐付いている場合は 409（Conflict）
- **必要設定（代表）**
  - `TWITTER_CLIENT_ID` / `TWITTER_CLIENT_SECRET`（PKCEのみなら Secret は任意扱い）
  - `TWITTER_REDIRECT_URI`（環境に合わせた callback）
  - allauth の `SocialApp` 設定
- **状態**: **一部完成**（実装はあるが、OAuth設定がないと利用不可）

### 1.5 ??????????Discord?
- **??**:
  - **Web**: django-allauth ???? Discord OAuth ????
  - **API**: `POST /api/auth/discord/`?code + code_verifier ??? access_token ? DRF???????
- **??????????**
  - `DISCORD_CLIENT_ID` / `DISCORD_CLIENT_SECRET` / `DISCORD_REDIRECT_URI`
  - allauth ? `SocialApp` ????????/????????
- **??**: **????**????????OAuth???????????

### 1.6 ソーシャルアカウント連携/解除（Web）

- **内容**
  - ログイン中ユーザーが Google/X を追加連携
  - 連携解除（複数連携がある場合のみUI上で解除可能）
- **画面**
  - 連携管理: `/accounts/social/connections/`
- **状態**: **完成**

### 1.7 開発用ログイン/モック（開発支援）

- **内容**
  - 開発環境向けの簡易ログイン
  - モックのソーシャルログイン（デモユーザー生成）
- **画面**
  - 開発用ログイン: `/accounts/dev-login/`
  - デモ: `/accounts/demo/`
  - モック: `/accounts/mock-social/google/` / `/accounts/mock-social/twitter_oauth2/`
- **状態**: **完成**（ただし開発用途）

---

## 2. グループ（Cult Circle）/フレンド

### 2.1 グループ管理

- **内容**
  - グループ作成（名称/説明/公開設定）
  - 公開グループの検索・参加（join）
  - 参加中グループ一覧、全体一覧（参加中 + 公開）
  - グループ編集/削除（管理者のみ）
  - メンバー一覧、退出（leave）
  - メンバー招待（管理者のみ）・招待の再送/更新
  - メンバー強制削除（管理者のみ、ただし作成者は削除不可）
  - 招待の期限切れ自動処理（pending → expired）
- **画面**
  - 管理画面: `/accounts/groups/view/`
- **API（代表）**
  - `/api/accounts/groups/`（CRUD + join/leave/invite 等）
  - `/api/accounts/invitations/`（招待一覧 + accept/decline）
- **状態**: **完成**

### 2.2 フレンド管理

- **内容**
  - ユーザー名によるフレンド追加
  - フレンド一覧表示
  - グループ招待時のフレンド一覧活用（UI側）
- **画面**
  - `/accounts/groups/view/` 内に統合
- **API（代表）**
  - `/api/accounts/friends/`（CRUD）
  - `/api/accounts/users/{id}/friends/`（参照）
- **状態**: **完成**

---

## 3. キャラクターシート（クトゥルフ神話TRPG 6版）

### 3.1 対応システム/版

- **内容**
  - クトゥルフ神話TRPG **6版**のキャラクターシートに対応
  - **7版は保留**（関連ドキュメントあり）
- **状態**
  - 6版: **完成**
  - 7版: **未完成**

### 3.2 画面（一覧/詳細/編集/新規）

- **内容**
  - キャラクター一覧（カード表示、検索/絞り込み、画像表示）
  - 詳細表示（画像ギャラリー、各ステータス/技能/所持品表示）
  - 編集・新規作成（フォーム）
  - 6版用の作成画面（タブ式UI）
- **画面**
  - 一覧: `/accounts/character/list/`
  - 詳細: `/accounts/character/{character_id}/`
  - 編集: `/accounts/character/{character_id}/edit/`
  - 新規（6版）: `/accounts/character/create/6th/`
- **状態**: **完成**

### 3.3 能力値・派生ステータス

- **内容**
  - STR/CON/POW/DEX/APP/SIZ/INT/EDU の入力
  - HP/MP/SAN などの派生値計算・現在値管理
  - ダイスロール設定（方式/式）に基づく能力値生成（後述）
- **状態**: **完成**

### 3.4 技能管理（ポイント配分/集計/補助）

- **内容**
  - 技能の作成/更新/削除（ベース値 + 職業P + 趣味P + その他P）
  - 残ポイント/合計のサマリー
  - 一括配分（batch allocate）、リセット
- **API（代表）**
  - `/api/accounts/character-sheets/{id}/skills/`
  - `/api/accounts/character-sheets/{id}/allocate-skill-points/`
  - `/api/accounts/character-sheets/{id}/batch-allocate-skill-points/`
  - `/api/accounts/character-sheets/{id}/reset-skill-points/`
- **状態**: **完成**

### 3.5 装備/武器/防具（所持品）

- **内容**
  - 装備・武器・防具などの登録/更新/削除
- **API（代表）**
  - `/api/accounts/character-sheets/{id}/equipment/`
- **状態**: **完成**

### 3.6 画像管理（複数枚・メイン画像・並び替え）

- **内容**
  - 複数画像アップロード（上限あり）
  - メイン画像の切替
  - 画像の並び替え
  - 詳細画面でのギャラリー表示（サムネイル + 拡大）
- **API（代表）**
  - `/api/accounts/character-sheets/{id}/images/`
  - `/api/accounts/character-sheets/{id}/images/{pk}/set_main/`
  - `/api/accounts/character-sheets/{id}/images/reorder/`
- **状態**: **完成**

### 3.7 成長・バージョン管理

- **内容**
  - キャラクターシートのバージョン作成（履歴として複製）
  - 成長記録（成長ロール、技能成長の紐付け）
  - 成長サマリーの取得
- **API（代表）**
  - `/api/accounts/character-sheets/{id}/create_version/`
  - `/api/accounts/character-sheets/{id}/growth-records/`
  - `/api/accounts/character-sheets/{id}/growth-summary/`
- **状態**: **完成**

### 3.8 ダイスロール設定（プリセット管理）

- **内容**
  - ダイスロール設定の保存（ユーザー単位）
  - デフォルト設定の切替
- **API（代表）**
  - `/api/accounts/dice-roll-settings/`
  - `/api/accounts/dice-roll-settings/{id}/set-default/`
- **状態**: **完成**

### 3.9 エクスポート（CCFOLIA向けJSON）

- **内容**
  - キャラクターを CCFOLIA 形式 JSON として出力
- **API（代表）**
  - `/api/accounts/character-sheets/{id}/ccfolia_json/`
- **状態**: **完成**

---

## 4. セッション/スケジュール（Chrono Abyss / R'lyeh Log）

### 4.1 セッション一覧・検索/フィルタ

- **内容**
  - セッション一覧表示（ページング）
  - ステータス、期間、役割（GM/PL）などで絞り込み
  - サイドバーに統計（概要）表示
- **画面**
  - セッション一覧: `/api/schedules/sessions/view/`
- **API（代表）**
  - `/api/schedules/sessions/`（CRUD）
  - `/api/schedules/sessions/statistics/`（一覧用統計）
- **状態**: **完成**

### 4.2 セッション作成/編集

- **内容**
  - セッション作成（タイトル、日時、予定時間、場所、説明、公開設定、関連シナリオ、YouTube配信URL）
  - セッション編集（同上）
  - GM作成時、参加者としてGMを自動追加
- **画面**
  - カレンダー画面の「新規セッション」モーダル
  - セッション一覧の「新規セッション」モーダル
  - セッション詳細の編集モーダル
- **API（代表）**
  - `/api/schedules/sessions/`
  - `/api/schedules/sessions/create/`
- **状態**: **完成**

### 4.3 参加者管理（参加/退出/枠/招待）

- **内容**
  - 参加（join）
  - 退出（leave）
  - プレイヤー枠（1〜4）と重複チェック
  - キャラクターシートの紐付け（参加者 → キャラ）
  - 協力GM（co-GM）追加
  - 参加者招待（GMのみ、通知連携）
  - 公開設定による参加制御（private/group/public）
- **画面**
  - セッション詳細: `/api/schedules/sessions/{id}/detail/`
- **API（代表）**
  - `/api/schedules/sessions/{id}/join/`（ViewSet action）
  - `/api/schedules/sessions/{id}/invite/`（参加者招待）
  - `/api/schedules/sessions/{id}/add_co_gm/`（協力GM）
- **状態**: **完成**

### 4.4 セッション詳細（参加者・キャラ状態参照）

- **内容**
  - セッションの基本情報表示
  - 参加者一覧（GM/PL、キャラ名、キャラシートへのリンク）
  - キャラクターシート紐付けがある場合、HP/MP/SANの参照表示（KP向けの説明あり）
- **画面**
  - `/api/schedules/sessions/{id}/detail/`
- **状態**: **完成**

### 4.5 カレンダー（FullCalendar）

- **内容**
  - カレンダー表示（月表示/クリック表示）
  - 表示フィルター（自分がGM / 参加中 / 公開）
  - カレンダーからセッション作成
  - 次回セッション一覧表示
- **画面**
  - `/api/schedules/calendar/view/`
- **API（代表）**
  - `/api/schedules/calendar/`（期間指定 or month 指定）
  - `/api/schedules/sessions/upcoming/`（次回セッション）
- **状態**: **完成**

### 4.6 カレンダー連携API（集約/月別/iCal）

- **内容**
  - 月別イベント一覧（date単位でグルーピング）
  - 今後n日分の集約（グループ別/週別/役割別、直近セッションも付与）
  - iCal（.ics）エクスポート（リマインダー付与）
- **API（代表）**
  - `GET /api/schedules/calendar/monthly/?month=YYYY-MM`
  - `GET /api/schedules/calendar/aggregation/?days=30`
  - `GET /api/schedules/calendar/export/ical/?days=90`
- **状態**: **完成**

### 4.7 ハンドアウト（秘匿/公開）+ GM管理画面

- **内容**
  - 参加者ごとのハンドアウト作成/編集/削除
  - 秘匿/公開の切替、まとめて公開切替
  - HO番号（HO1〜HO4）・プレイヤー枠への割当
  - テンプレート利用（UI上の機能）
- **画面**
  - GMハンドアウト管理: `/api/schedules/sessions/{id}/handouts/manage/`
- **API（代表）**
  - `/api/schedules/handouts/`（CRUD）
  - `/api/schedules/gm-handouts/`（GM向け操作）
- **状態**: **完成**

### 4.8 ハンドアウト添付ファイル（画像/PDF/音声/動画/文書）

- **内容**
  - ハンドアウトへのファイル添付
  - ファイルタイプ判定、サイズ上限、MIMEチェック
  - ダウンロードURL提供
- **状態**: **完成**

### 4.9 セッション通知（招待/変更/キャンセル/リマインダー）

- **内容**
  - 通知レコードの作成（既読/未読、未読件数）
  - 通知設定（ユーザーごとにON/OFF）
  - セッション更新時の変更通知、キャンセル通知、招待通知など
- **API（代表）**
  - `/api/schedules/notifications/`（一覧・既読化・未読数）
  - `/api/schedules/notification-preferences/`（通知設定）
- **状態**: **一部完成**（API/DBはあるが、通知一覧の専用UIは未整備）

### 4.10 セッションノート/ログ

- **内容**
  - セッションノート（種別付き、ピン留め）
  - セッションログ（タイムスタンプ付きイベント）
- **API（代表）**
  - `/api/schedules/notes/` / `/api/schedules/logs/`
  - `/api/schedules/sessions/{session_id}/notes/` / `/api/schedules/sessions/{session_id}/logs/`
- **状態**: **一部完成**（API/DBはあるが、UIは未整備）

### 4.11 セッション画像（添付画像）

- **内容**
  - セッションへの画像アップロード（単体/一括、並び替え）
- **API（代表）**
  - `/api/schedules/session-images/`
  - `/api/schedules/session-images/{id}/bulk_upload/`
  - `/api/schedules/session-images/{id}/reorder/`
- **状態**: **一部完成**（API/DBはあるが、専用UIは未整備）

### 4.12 YouTube連携

- **(A) セッションのYouTube配信URL（単一URL）**
  - セッションに `youtube_url` を1つ紐付け
  - UI上で編集可能
  - **状態**: **完成**

- **(B) 複数YouTubeリンク管理（SessionYouTubeLink）**
  - 1セッションに複数動画をリンク
  - YouTube API から動画情報取得（タイトル/時間/サムネ等）
  - 追加者/GMの権限に基づく編集・削除
  - **必要設定**: `YOUTUBE_API_KEY`
  - **状態**: **一部完成**（API/DBはあるが、UIは未整備）

### 4.13 セッション完了時の自動記録（プレイ履歴）

- **内容**
  - セッションが `completed` に変更されたタイミングで、参加者ごとのプレイ履歴を作成
  - 参加者のキャラクターに紐付いている場合、キャラ側のセッション回数を更新
  - シナリオ未連携の場合はダミーシナリオを自動作成して紐付け
- **状態**: **完成**

### 4.14 キャラクターシート統合（セッション側）

- **実装済み範囲**
  - 参加者にキャラクターシートを紐付け（`SessionParticipant.character_sheet`）
  - セッション詳細で HP/MP/SAN の参照表示（キャラクターシート側の現在値を参照）
- **未実装/不足しやすい範囲**
  - セッション開始時スナップショット
  - セッション中のリアルタイム追跡（セッション専用のHP/SAN変動履歴）
  - セッション後の差分履歴・アイテム獲得管理
- **状態**: **一部完成**

---

## 5. シナリオ（Mythos Archive）

### 5.1 シナリオ登録・検索・フィルタ

- **内容**
  - シナリオCRUD（タイトル、作者、ゲームシステム、難易度、想定時間、推奨技能、URLなど）
  - 検索（title/author/summary）
  - フィルタ（ゲームシステム、難易度、想定時間、人数など）
- **画面**
  - `/api/scenarios/archive/view/`（一覧 + 登録モーダル + フィルタ）
- **API（代表）**
  - `/api/scenarios/scenarios/`
- **状態**: **完成**

### 5.2 シナリオメモ（GMメモ/公開メモ）

- **内容**
  - メモの作成/閲覧（自分のメモ + 公開メモ）
  - 非公開メモは本人のみ参照可能（他者は404扱い）
- **API（代表）**
  - `/api/scenarios/notes/`
  - `/api/scenarios/scenarios/{id}/notes/`
- **状態**: **完成**

### 5.3 プレイ履歴（PlayHistory）/アーカイブ統計

- **内容**
  - プレイ履歴の登録（セッション連携可）
  - アーカイブ表示（プレイ回数、総プレイ時間、プレイ済みフラグ）
  - 年別統計（役割別、月別など）
- **API（代表）**
  - `/api/scenarios/history/`
  - `/api/scenarios/archive/`
  - `/api/scenarios/statistics/`
- **状態**: **完成**

---

## 6. 統計（Tindalos Metrics）/エクスポート

### 6.1 Tindalos Metrics（統計ダッシュボード）

- **内容**
  - 年間サマリー（総セッション数、総プレイ時間、GM/PL内訳、達成度など）
  - 月別推移、システム別、曜日別、時間帯別、ランキング、グループ活動などの可視化
- **画面**
  - `/accounts/statistics/view/`
- **API（代表）**
  - `/api/accounts/statistics/tindalos/`
  - `/api/accounts/statistics/ranking/`
  - `/api/accounts/statistics/groups/`
  - `/api/accounts/statistics/tindalos/detailed/`
- **状態**: **完成**

### 6.2 統計エクスポート（CSV/JSON/PDF）

- **内容**
  - 統計をCSV/JSONでダウンロード
  - PDFは `reportlab` が無い場合はプレースホルダPDFを返す挙動
- **API（代表）**
  - `/api/accounts/export/?type=tindalos&format=csv|json|pdf`
  - `/api/accounts/export/?type=ranking&format=csv|json`
  - `/api/accounts/export/?type=groups&format=csv|json`
- **状態**: **一部完成**（PDFは依存ライブラリ有無で品質が変動）

---

## 7. 管理/運用

### 7.1 Django管理画面

- **内容**
  - Django Admin による各種モデルの確認・管理
  - allauth の `SocialApp` や `Site` の管理（ソーシャルログイン設定）
- **画面**
  - `/admin/`
- **状態**: **完成**

### 7.2 管理者向けAPI（ユーザー管理）

- **内容**
  - 管理者向けのユーザー参照/操作（ViewSet）
- **API（代表）**
  - `/api/accounts/admin/users/`
- **状態**: **一部完成**（UIはDjango admin中心、運用フローは要設計）

---

## 8. 未実装機能（現状の仕様書ベース）

以下は `SESSION_UNIMPLEMENTED_FEATURES_SPEC.md` 等で挙げられている「今後の候補」で、現時点では未実装（または部分実装）になりやすい領域です。

- **高度なスケジューリング**
  - 定期セッション（RRULE等）、キャンペーン管理、参加可能日投票、タイムゾーン対応 など
  - **状態**: **未完成**
- **セッション素材ライブラリ（マップ/BGM/外部リンクの体系化）**
  - **状態**: **未完成**
- **リアルタイム通知/チャット**
  - WebSocket によるリアルタイム、掲示板、投票、チャット等
  - **状態**: **未完成**
- **外部サービス連携の拡張**
  - Discord/VTT/Google Calendar/配信サービスとの高度連携
  - **状態**: **未完成**

