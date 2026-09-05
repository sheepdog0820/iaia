# 正式公開の初回監査（2026-09-05）

対象の基点: `e12c92a9d4601007c6b492c35d7698572b37a8f7`
作業ブランチ: `codex/delegated-workflow-rules`
判定: **正式公開は未承認。必須の実サービス検証・運用検証の証拠が不足している。**

## 今回確認できたこと

- Python 3.11.1、Django 5.2.15、pytest 9.1.1でローカル検証を開始した。
- 課金・共有リンク・Google/Discord連携・HO・セッション公開範囲・本番設定・公開文書の対象テストは、初回292件成功、1件失敗、subtests 2件成功。失敗した本番キャッシュ設定テストには、検証コマンドが設定した `USE_REDIS_CACHE=False` の継承が影響した。アプリ不具合とは確定せず、当該環境変数を除いて再検証する。
- 対象テストのDBは一時ディレクトリの専用SQLite。既存のローカルDB、共有DB、本番DBには適用していない。
- 修正後・環境変数是正後の再実行は **294件成功、失敗0件、subtests 2件成功、119.97秒**。JUnitは `tmp/formal-release-targeted-fixed-20260905.xml`。既存のDjango 6.0向け非推奨警告が9件ある。全体テスト・E2E・PostgreSQL・実Stripeはこの結果に含まない。
- 変更Python 2ファイルのBlack、isort、Flake8と差分の空白チェックは成功。UI文言は変更していない。
- `flake8 accounts schedules scenarios support tableno --statistics --count`: 指摘0件、終了コード0。
- Banditは上記アプリ範囲でHIGH 0件、MEDIUM 6件、LOW指摘あり。終了コード1であり、セキュリティチェック合格ではない。テストコードも含むため指摘の実害を個別に確認する。
- Docker CLIは利用可能だがdaemon接続に失敗。Dockerビルド・PostgreSQL実行は未検証。
- GitHub連携の未完了Issue検索で [#1](https://github.com/sheepdog0820/iaia/issues/1) を取得。これはキャラクター詳細のレスポンシブなボタン配置改善であり、正式公開に必要な全課題の一覧ではない。
- 基点コミットのPR起動ワークフロー照会結果は空。使用したAPIはPR起動分のみを返すため、main起動CIの未実行を意味しない。現在のCI成功証拠は未取得。
- Stripe連携ツールは再認証が必要。アカウント・モード・Price・実イベントの照会は未実施。

## 発見して修正した課金不具合

Webhook処理トランザクション内の `IntegrityError` をすべて重複としてHTTP 200で返す分岐が存在した。業務データ保存の整合性エラーでも成功応答になり、失敗記録も残らない。

- 再現: 実DBの一意制約違反を処理ハンドラー内で発生させるテストを追加し、期待HTTP 500に対してHTTP 200となる失敗を確認した。
- 修正: 当該分岐を除き、既存の失敗処理でHTTP 500と失敗状態を記録する。登録済み成功イベントの重複判定は維持する。
- 回帰条件: 失敗後の同一イベント再送が成功し、イベント記録は1件、エラー情報が解消されること。
- DBスキーマ、設定、料金、外部APIバージョンの変更はない。
- [StripeのWebhook配信仕様](https://docs.stripe.com/webhooks?lang=node)ではHTTP 200を配信成功として扱い、配信失敗時の再試行を説明している。ローカル再現は実Stripeイベントでの検証を代替しない。

## 正式公開に向けた証跡表

「実装あり」はコード・テストの存在を示す。実サービスで合格したことは示さない。

| 領域 | 現時点の証拠 | 次に必要な証拠・作業 |
| --- | --- | --- |
| 有料プラン | Checkout、Portal、署名検証、重複処理、課金状態、監査の実装とテストあり | 修正後回帰、実Stripeテストモードの月額/年額・更新・解約・失敗/回復・返金/異議、実DB状態とイベントID、公開料金の確定 |
| 課金公開判定 | `billing_release_gate` はCheckout無効なら成功する。CIも無効設定 | CIの緑を有料正式公開の証拠にしない。有効状態の外部検証記録と本番設定の別判定が必要 |
| Google連携 | Calendar同期のジョブ・冪等性・トークン更新、Sheets出力のテストあり | 実認可・権限失効・再接続・同期/出力・障害と再試行の受入確認 |
| Discord/ICS | 通知の重複防止・失敗一覧/再試行、購読トークン発行/失効のテストあり | 承認された検証先で実配信・購読・解除・権限変更時の確認 |
| その他の既存連携 | YouTubeメタデータ取得、LINE障害受付の実装を確認 | 正式公開範囲・失敗時動作・実サービスの確認を追加。ココフォリア出力の受け取り確認も必要 |
| 権限/秘匿情報 | HO・セッション・共有リンクの対象テストあり | ロール別の画面/API/添付/通知/外部出力の確認表と回帰証拠 |
| UI/中核機能 | 既存E2E定義あり、Issue #1あり | 全主要導線・3ブラウザ・スマートフォン、代表的な実利用確認 |
| 本番DB/性能 | PostgreSQL CI定義あり。現行DBジョブ対象はキャラクター版管理と共有リンクのみ | 課金の競合処理等の本番DB検証を拡張。想定負荷を決めて測定 |
| 運用 | 既存RunbookとIaCあり | 実環境の監視通知、復元、ロールバック、公開設定の確認と承認 |
| 対外方針 | 既存の料金・規約テンプレートあり | 料金・機能差・費用上限・保存期間・問い合わせ先・正式表示の人間による確定 |

## 静的解析で次に調べる箇所

- `accounts/views/api_auth_views.py`: Google userinfo取得にタイムアウト指定なし（B113）。
- `schedules/services.py`: YouTube取得にタイムアウト指定なし（B113）。APIキー未設定時のモック表示も公開時の扱いを確認する。
- `accounts/utils/dice.py`: 入力検証後の `eval`（B307）。入力制約と計算量を調べ、安全な算術評価への置換を検討する。
- `support/services.py`: LINE HTTPクライアント2箇所（B310）。現行URLは固定HTTPSだが、リダイレクト等を含めて安全性を評価する。
- `schedules/management/commands/reset_dev_session_data.py`: DBメタデータから生成するSQL（B608）。開発専用制限と識別子の扱いを確認する。

## 証拠の保存と復旧

JUnit XMLとBandit JSONはローカルの `tmp/formal-release-*-20260905.*` に保存する。未確認・失敗結果も削除して合格扱いにしない。継続監査ではその時点の対象コミットと結果を追記する。

今回のアプリ修正の復旧はWebhook例外処理の差分を戻すコードのリバートで可能。ただし元の不具合が再発するため、本番適用前の候補修正として扱う。

## 継続監査: 外部通信と本番DB（2026-09-05）

- Google userinfoとYouTube取得のタイムアウト未指定を修正した。接続・読み取りの無応答を10秒で打ち切る指定であり、応答全体の所要時間の上限を保証するものではない（[Requests仕様](https://requests.readthedocs.io/en/latest/user/quickstart/#timeouts)）。
- Google userinfoの通信エラーは日本語のHTTP 503を返し、例外本文を応答・当該ログに含めない。YouTubeの例外ログにもAPIキーを含み得るURL・トレースバックを記録せず、例外種類を記録する。
- 新規4テストは変更前に失敗を再現。修正後、Google/X/Discord認証・YouTubeリンク・新規通信テストは **53件成功、subtests 30件成功**。`tmp/formal-release-http-20260905.xml`。
- 変更3 PythonファイルのBlack/isort/Flake8は成功。新規表示文言は日本語。DBスキーマ、料金、外部設定は変更していない。
- 変更した通信2ファイルのBandit再検査はHIGH/MEDIUM 0件、LOW B105 1件（変数名への指摘）が残る。全アプリの安全性を示す結果ではない。
- `pip-audit -r requirements.lock.txt --disable-pip --no-deps` は111依存を検査し、既知脆弱性0件・スキップ0件。`tmp/formal-release-dependencies-20260905.json`。
- Docker Desktopを起動し、`desktop-linux` コンテキストのDocker 25.0.3へ接続できた。通常/MySQLのCompose設定チェックはともに成功。
- 専用PostgreSQL 16コンテナを127.0.0.1の検証用ポートだけに公開し、CIのproduction設定で `accounts/test_billing.py`、`accounts/test_share_links.py`、`accounts/test_character_6th_versioning.py` を実行。**208件成功、110.44秒**。`tmp/formal-release-postgres-20260905.xml`。本番データは使用していない。
- PostgreSQLのCI対象に課金テストを追加した。ただし、同時実行の競合を網羅した証明や実Stripeの検証とは区別する。
- SSHでリモートmainの基点SHA一致を確認した。GitHubのcommit status APIも空であり、CI成功証拠は引き続き未取得。
- AWS profile `tableno-pre` のSTS照会は成功し、期待する開発アカウントと一致した。リソース・Secrets・DBは変更していない。
- 開発ECSサービスはACTIVE、タスク定義リビジョン40、desired/runningとも0。`https://stg.tableno.jp/health/ready/` は503。意図的な停止の可能性があり、起動・デプロイは未実施。
- 検証専用PostgreSQLコンテナはテスト後に停止し、作成時の `--rm` により削除した。Docker Desktopは起動状態を維持している。
- CIと同じアプリ・単体・結合テスト範囲の全体実行は進行中。完走結果は別途追記する。E2E・実Stripe・本番反映は未実施。

## 継続監査: コンテナ成果物（2026-09-05）

- ローカルの `.codex*` ディレクトリ、`ngrok.exe`、`skills/`、`coverage.xml` をDockerビルド対象から除外した。認証設定を含み得るローカル作業ディレクトリの混入防止を目的とする。除外不足を検出するテストは変更前に失敗し、修正後のリポジトリ衛生・テキスト品質テストは10件、subtests 4件成功。
- 初回ビルドはアプリケーションのCOPY前に停止した。修正後のビルドは成功し、イメージIDは `sha256:8baff73e9de76bf94ab04d787a9ecf0c9a680591938890bdbb7b08f8d4adfb65`。この成果物はコミット `672d738f` に上記除外修正を加えたもの。
- イメージ内でアプリケーションの存在と上記除外対象の不在を確認した。ローカル用の仮設定とエントリーポイントの上書きで `manage.py check` は問題0件。DB移行・外部公開・レジストリへのpushは実施していない。
- コンテナはロックファイルのDjango 5.2.17を使用し、ローカルテスト環境の5.2.15とは異なる。ビルドと設定チェックの成功を、固定依存関係での全機能テスト成功とは扱わない。
- 作業ブランチはGitHubへpush済み。Draft PR作成はGitHub連携の403（Resource not accessible by integration）で失敗した。ブラウザのGitHubも未ログインであり、PRとCI成功の証跡は未取得。

## 継続監査: カスタム計算式（2026-09-05）

- `accounts/utils/dice.py` の入力検証が式の未認識部分を読み飛ばし、条件式・配列アクセス・比較などを受理する不具合を18の失敗ケースで再現した。実サービスの入力経路での悪用可能性までは確認していない。現行コード検索では当該ヘルパーのテスト外の呼び出し経路は見つかっていないため、公開APIの脆弱性を実証したとは扱わない。
- 式全体を200文字以内の許可文字と構文で検証し、能力値・整数・四則演算・括弧・単項符号だけを明示的に計算する処理に置換した。Pythonの `eval` は削除した。既存の能力値変換、演算順序、小数部分の切り捨て、最小値0、日本語のゼロ除算エラーは維持する。
- 専用の一時SQLiteで、カスタム式・6版・ダイス設定の回帰テスト **56件、subtests 31件成功（60.04秒）**。`tmp/formal-release-formula-20260905.xml`。追加した指数表記等の拒否ケースも含め、新規単体テストは別途4件、subtests 34件成功。
- 変更4関数の行カバレッジは各100%。`tmp/formal-release-formula-coverage-20260905.json`。モジュール全体・分岐カバレッジを100%とする証拠ではない。
- 対象ファイルのBandit HIGH/MEDIUMは0件で、B307は解消。ダイス用擬似乱数のLOW指摘は残る。DB・外部設定・画面構成は変更していない。
- 先行して実行中の全体テストは修正前のモジュールを読み込み済みのため、本修正の証跡は上記の個別回帰テストとして区別する。

## 継続監査: 全体テスト完走・有料公開条件（2026-09-05）

- ローカルSQLiteでCIと同じ対象パスのテストが **1,497件、subtests 179件成功（1,406.65秒）**。`tmp/formal-release-full-20260905.xml` はerrors/failures/skippedすべて0、subtests込み1,676件を記録。対象は `accounts api scenarios schedules support tableno tests/unit tests/integration`。カバレッジ測定・E2E・固定依存関係のコンテナ内実行・リモートCIを含まない。
- 全体テストの実行開始時は `beac68f2` に外部HTTP修正を加えた状態（後の `672d738f` 相当のアプリコード）。実行中に追加したコンテナ除外・計算式・課金ゲートの修正は個別の検証記録を参照する。最新コミット全体を一括実行した結果とは扱わない。
- 警告165件にはDjango廃止予定API、タイムゾーン未指定の日時、テストメソッドの戻り値が含まれる。特に戻り値で成否を返している旧テストは、失敗をアサーションで検出しているか追加確認が必要。
- 有料正式公開用に `billing_release_gate --require-paid-checkout` を追加。Checkout無効では失敗し、有効でも外部検証記録を必須とする。従来の無効状態を確認するCI用途は維持。目標文書・本番Go/No-Go・スモーク手順を有料必須条件へ更新した。
- 文書テスト38件、subtests 2件成功。`tmp/formal-release-paid-docs-20260905.xml`。検証記録ゲートは形式検査であり、実イベントの真偽・課金ライフサイクルの成立・人間による料金承認を代替しない。
- 課金ゲート7件成功（20.81秒）。`tmp/formal-release-paid-gate-final-20260905.xml`。追加オプション未実装時の3件失敗を確認後に実装し、無効・有効かつ証跡なし・形式を満たしたテスト用証跡ありを検証した。実Stripeを検証した結果ではない。

## 継続監査: 利用フローテストの失敗検出（2026-09-05）

- `tests/integration/test_workflow_integration.py` のCSVエクスポートをテストプロセス内だけでHTTP 500に置換したところ、旧テストは成功した。エラー時にログを出すだけでアサーションがないため、全体テストの成功だけではこの導線の健全性を証明できなかった。
- CSVはHTTP 200、CSV Content-Type、空でない本文を必須とした。プレイヤー・GMの参加者一覧を確認してからHO配布を検証し、JSONエクスポート・統計の失敗を条件分岐でスキップしないよう修正した。6テストの不要な戻り値も削除した。
- 同じHTTP 500の注入で、修正後は `500 != 200` のアサーション失敗を確認。`tmp/formal-release-workflow-injected-failure-20260905.xml` はこの意図的な失敗検出の証拠であり、現行アプリの障害記録ではない。
- 置換なしの一時SQLiteによる統合テストは **6件成功（26.52秒）**。`tmp/formal-release-workflow-20260905.xml`。残る警告9件はDjango廃止予定API。ブラウザE2Eや実外部サービスの検証は含まない。他の古いテストの条件付き検証や戻り値の監査は未完了。

## 継続監査: ブラウザ操作（2026-09-05）

- コミット `8b2a9420` をローカルの専用SQLite・media・メモリ内メール/キャッシュで起動。専用設定は `tmp/formal_release_e2e_settings.py`、DBは `tmp/formal-release-e2e-20260905/db.sqlite3`。8019番ポートだけを使い、通常の `db.sqlite3` と共有環境を変更しない。テスト専用の高速ハッシュ設定を使用しており、性能・本番設定の証拠ではない。
- 初回は開発ログインが前提とするユーザー不足を確認し、後続の失敗を繰り返さず停止。専用DBに `admin`、`investigator1`、`investigator2` を追加後、Playwright 1.53.1 / Chromiumで **26件成功（51.0秒）**。`tmp/tmp/formal-release-e2e-seeded-20260905.json`。初回の失敗証跡は別の出力先に維持。
- 登録・メール資格情報ログイン、日程調整、秘匿HO、シナリオ・セッション・6版/7版キャラクターの導線、CCFOLIA JSON出力、ゲスト所有権引継ぎ、主要画面JavaScript、法務リンク、390/412px幅のセッション・キャラクター画面を確認した。スマートフォン実機や実CCFOLIAへの取り込みは未確認。
- 登録テスト以外は主に開発ログインとadminを使用する。全機能の通常ユーザー権限・課金契約のE2Eを証明するものではない。外部連携設定テストはGoogle/Discord/Sheets/ICSのAPI応答を模擬しており、実サービスの認可・通知成功とは区別する。
- Firefox / WebKitの同じ26件ずつ、計52件も成功（約3.5分）。`tmp/tmp/formal-release-e2e-crossbrowser-20260905.json`。Chromiumと合わせて78件成功、skip/flaky/unexpectedはいずれも0。Windows上のPlaywrightブラウザであり、macOS/iOSのSafari実機とは区別する。
- 検証後、スキルが記録した専用8019番ポートのサーバーを停止。テスト用DB・設定・ログ・失敗時の画像/traceはローカルの証跡として保持し、リポジトリには追加しない。

## 継続監査: 固定依存関係のコンテナ検証（2026-09-05）

- コミット `c6d280d8` を現行Dockerfileと `requirements.lock.txt` でビルド。イメージは `sha256:eaf05e815671db51d613bef0c7b7d37b1fe193bfc38bff442ea6b4377132cf49`、ローカルタグは `tableno-formal-release:c6d280d8`。レジストリには送信していない。
- Python 3.11.16、Django 5.2.17、Stripe 15.5.1。`python -m pip check` は依存不整合なし。イメージ内に `.codex*` と `tmp/` がないことを確認し、専用E2E設定/DBの混入も除外した。
- エントリーポイントをPythonへ上書きし、仮のSECRET_KEY・APP_ENV=local・ENV_FILE空・DB_ENGINE=sqliteで `manage.py test accounts.test_billing tests.unit.test_custom_formula_safety tests.unit.test_external_http_resilience accounts.test_character_6th_custom_formula --noinput --verbosity 1` を実行。**203件成功（40.228秒）、終了コード0**。実行コンテナ内だけのSQLiteを使用し、テストDBと `--rm` コンテナは終了時に削除された。
- この203件には課金公開ゲート・DB例外再試行・通信失敗・算術構文の修正が含まれる。失敗系テストの500/503ログは期待する障害注入であり、テスト結果はOK。固定依存関係での全体CI・PostgreSQL・ブラウザE2E・実Stripeを完了した証拠ではない。

## 継続監査: LINE HTTP転送（2026-09-05）

- LINEの返信・push・画像取得がHTTP転送を追従するケースをメモリ内のHTTPSハンドラーで再現。修正前は15ケース中11ケースで転送拒否の期待に失敗した。実ネットワーク・実トークン・実宛先は使用していない。
- 認証付きリクエスト専用のリダイレクト拒否ハンドラーを追加し、301/302/303/307/308を追従せずHTTPエラーとして既存の失敗処理へ渡す。正規APIの直接応答、認証ヘッダー、タイムアウト、添付取得を維持する。実LINEが転送を返すかは未確認であり、転送発生時は黙って追従せず運用側で確認する。
- サポート受付・再試行と新規HTTPテストは **12件、subtests 18件成功（27.83秒）**。`tmp/formal-release-line-20260905.xml`。新規2関数の行カバレッジは100%。`tmp/formal-release-line-coverage-20260905.json`。対象ファイルのBandit HIGH/MEDIUMは0件。
- 開発用リセットコマンドのSQL指摘も確認。識別子はSQLite自身の外部キーメタデータ由来で、行IDはパラメーター化され、コマンド入口はDEBUGを確認している。外部APIからの直接入力経路はこのコード内にはない。コマンドは破壊的なため実行せず、DEBUGだけに依存する環境制限と識別子処理の改善検討は残す。

## 継続監査: 開発環境の状態変化と配備差分（2026-09-05）

- 読み取りでaws-preを再確認し、ECS desired/running=1/1、タスク定義40、稼働イメージ `aws-pre-8cf3c7f7`、ヘルス200（DB/cache ok）を確認。このタスクから起動操作は行っていない。先の0/0・503は過去時点の結果。
- 稼働コミットから候補 `f0f443f0` への比較で、新規 `schedules.0055`、既存 `accounts.0058` の実装変更、static/templates等を確認。今回の分岐元mainとの比較だけでは共有環境の配備影響を見落とすため、稼働版を基点とした移行・復旧確認が必要。
- ECS Execとdeployment circuit breaker/自動rollbackは無効。現時点で実DBの適用履歴や復元を検証したとは扱わない。共有DBへの接続・変更、Secretsの値取得、サービス更新は未実施。
- [aws-pre配備準備計画](AWS_PRE_FORMAL_RELEASE_VALIDATION_PLAN.md)を作成。イメージdigest、実DB履歴、バックアップ/復元、追加費用とテスト宛先が揃うまで配備承認案は未完成と明示した。

## 継続監査: 参加者ロールの移行・逆移行（2026-09-05）

- `MigrationExecutor` で実際の `schedules.0054` と `0055` を往復するテストを追加。単一ロールのデータ保持、複数ロール許可、同一ロール重複拒否、複数ロール存在時の逆移行失敗とデータ/適用履歴保持を確認する。
- 専用SQLiteで2件・subtests 2件成功（17.74秒）、専用PostgreSQL 16で2件・subtests 2件成功（21.57秒）。`tmp/formal-release-role-migration-sqlite-20260905.xml`、`tmp/formal-release-role-migration-postgres-20260905.xml`。共有データは使用していない。
- PostgreSQL用CIの対象にも追加した。リモートCIの成功証拠は引き続き未取得。実データの移行時間、ロック競合、バックアップ復元の証拠ではない。

## 継続監査: セッション一覧の基礎性能（2026-09-05）

- コミット `495ef037` の `/api/schedules/sessions/?period=all` を、通常ユーザー（グループメンバーかつ対象セッションのGM）で測定した。専用SQLite、Django 5.2.15、DEBUG=False、APIClientの認証注入、同時実行1、各規模3回。空でない戻り件数が保存件数に一致することを検証した。セッションはbulk_create、参加者・HO・画像なしの最小構成であり、本番データ量の代表値とは断定しない。
- SQLは `connection.execute_wrapper` で数えた。最初の測定では既定の未来フィルターで0件となり無効、次の測定ではSQLログ上限9,000件に達して件数が不正確だったため、条件・計数方式を修正して再測定した。以下は修正後の結果のみ。

| 保存/応答セッション数 | 1要求あたりSQL数 | 応答中央値 | 応答本文サイズ |
| --- | --- | --- | --- |
| 10 | 141 | 0.0868秒 | 8,992 bytes |
| 100 | 1,401 | 0.8049秒 | 90,083 bytes |
| 1,000 | 14,001 | 8.1570秒 | 902,784 bytes |

- 証跡: `tmp/formal-release-session-list-profile-20260905.json`、測定用コード `tmp/formal_release_list_profile.py`。時刻にはAPIClient処理・JSON解析を含み、ネットワーク/ブラウザ描画/ログインハッシュは含まない。共有DBと外部サービスを使用していない。
- 関連データのセッション単位の取得でSQLが増えている。`TRPGSessionViewSet.get_queryset` はscenario以外を一括取得せず、serializerは参加者・HO・画像・動画・件数等を参照する。未修正の性能課題として扱う。改善ではAPI項目を削る、権限フィルターを省く、返却件数を黙って減らす方法を採用しない。一括取得とキャッシュ利用を検証し、内容/秘匿保護の回帰テストと同条件の再測定を行う。
- 登録人数・同時利用人数の合意、PostgreSQL/本番相当構成、同時10人等の負荷試験は未実施。この基礎測定を公開性能の合格証拠としない。

## 継続監査: セッション一覧の一括取得（2026-09-05）

- 一覧でGM/作成者/グループ、参加者とロール・6版/7版のキャラクター、HO、画像、動画、シナリオ推奨技能をまとめて取得するようにした。件数と動画時間は取得済みデータを使用。HOは閲覧可否を判定してから一度だけシリアライズする。一覧以外の権限判定は従来どおりDBを参照する。
- 新規回帰テストは、2件から10件へ増やした場合のSQL増加を検出し、修正前に最小構成29→141回、関連情報あり85→421回で失敗した。最初のHOテストデータにNOT NULL違反があり、割当先をゲスト参加者へ修正してからこの失敗を確認した。
- 修正後、新規3テスト・subtests 8件が成功。最小構成と関連情報ありのSQL増加抑止、一覧と通常取得の全フィールド一致、GM/PL/部外者、GMロール、owner/managerロールの秘匿制限、参加者・ゲスト件数、動画時間、推奨技能順を確認。性能テストには6版/7版両方のキャラクターを含む。
- coverage実行でも同じ3テスト・subtests 8件成功。追加された実行対象行28行はすべて実行された（handout_access 11、models 3、serializers 12、views 2）。これは変更行の行カバレッジであり、モジュール全体や分岐100%の意味ではない。証跡は `tmp/formal-release-session-list-coverage.json`。
- 先の測定スクリプトを出力先だけ変えて再実行。専用SQLite、Django 5.2.15、DEBUG=False、通常ユーザー、同時要求1、最小構成、各3回。保存/応答件数10・100・1,000のすべてでSQLは5回、本文サイズはそれぞれ8,992・90,083・902,784 bytesで前回と同じだった。中央値は0.0242・0.0831・0.8881秒。この実行中には別の専用DBで回帰テストも動いていたため、応答時間は参考値とする。
- 測定証跡は `tmp/formal-release-session-list-profile-after-20260905.json`。変更前の結果ファイルは保持した。レスポンス件数の制限やAPI項目削除による短縮は行っていない。
- 合意した利用規模でのPostgreSQL/同時負荷試験、ネットワークとブラウザを含む評価は引き続き未実施。正式公開の性能合格判定には不足する。
- `schedules` 全体、新規一覧回帰テスト、`test_workflow_integration.py` を専用SQLiteで実行し、398件・subtests 55件成功（563.12秒、警告9件）。証跡は `tmp/formal-release-session-query-regressions-20260905.xml`。対象は `88926aec` に今回のコード差分を適用した状態。リモートCIや最新コード全体のE2E成功を意味しない。
- 変更PythonのBlack/isort確認、flake8の実行不能エラー検査、差分レビュー、対象7ファイルのUTF-8/LF/差分チェックが成功。変更に新しいユーザー表示文言はない。レビューで追加の修正事項は見つからなかった。

## 継続監査: 実SDKを通した課金権限の統合検証（2026-09-05）

- `e118f665` を起点に、通常ユーザー（staff/superuserともFalse）の署名付きローカルWebhookを、実Stripe SDKの署名検証・Webhookビュー・DB更新・画面/API権限まで通すテストを追加した。Stripeから取得したイベントではなく、試験用secretで作ったfixtureである。APIClientはDjangoセッション認証を使用し、ユーザーの `is_premium` を試験側で直接変更しない。
- 最初の実行は月額/年額の両方で失敗。SDK 15.2.1の `Event` はdictではなく、署名検証後の `event.get("id")` で例外となった。既存テストの辞書モックでは発見できなかった。署名検証が成功したイベントを、必要な場合に公開メソッド `to_dict()` で再帰変換するよう修正した。署名不一致の拒否は維持する。[SDKの公式パッケージ資料](https://pypi.org/project/stripe/15.6.1/)
- さらに現行APIのfixtureへ合わせると、`current_period_end` が保存されず8 subtestsが失敗した。Basil以降の明細内の期間終了日時を、従来のPrice抽出と同じ先頭明細から取得するよう修正。旧形式のトップレベル値も引き続き扱う。現在のCheckoutは単一プランであり、混在周期・複数有料商品の統合判定は今回の検証対象ではない。[Stripe公式変更履歴](https://docs.stripe.com/changelog/basil/2025-03-31/deprecate-subscription-current-period-start-and-end)
- Stripe DocsスキルのCLIを試したが、CLI側のdocs pluginが利用不可と返したため公式Web資料へフォールバックした。CLI plugin追加、Stripe設定変更、実課金、外部通知は実施していない。
- 新規2テストは月額+6版、年額+7版で、無料時拒否、不正署名拒否、activeでの権限付与、CCFOLIAインポート成功、重複イベントの監査ログ重複抑止、期間末解約予約中の利用継続、past_dueで失効、activeで回復、canceledで失効、失効時の新規インポート拒否と既存キャラクター閲覧・保持を確認する。有料化しても他人のprivateシナリオは404のままであることも確認した。invoice、返金、異議、退会の全経路や実Checkout成功の証拠ではない。
- 専用SQLite、Django 5.2.15/Stripe 15.2.1で `accounts/test_billing.py` と新規統合テストの190件・subtests 8件成功（69.75秒、警告9件）。追加実行対象7行は行カバレッジ100%（billing 5、billing_views 2）。モジュール全体/分岐100%ではない。証跡: `tmp/formal-release-paid-feature-lifecycle-20260905.xml`、`tmp/formal-release-paid-lifecycle-coverage.json`。
- 固定依存の既存イメージ `sha256:eaf05e815671db51d613bef0c7b7d37b1fe193bfc38bff442ea6b4377132cf49`（Django 5.2.17/Stripe 15.5.1）に、今回のbilling.py・billing_views.py・新規テストを読み取り専用でマウントし、`--network none` の専用コンテナ内SQLiteで同じ190件成功（33.552秒）。コンテナは `--rm` で終了。これは当該ソースと固定依存関係の互換性確認であり、最新コード全体のビルド/配備証明ではない。
- 新規統合テストをPostgreSQL用CIにも追加した。リモートCI結果、実WebhookのAPIバージョン設定と実配送、実Priceとの一致は引き続き未確認。
- 有料境界の照合で、アーカイブ画面のみ有料制限があり、シナリオAPI自体はログイン・可視性・所有権を使用することを確認した。シナリオ画像の既定上限は無料/有料とも5 MiB・1回10枚。販売条件の確定前にこの差を整理する。今回、未合意のAPI制限追加や無料機能の削除は行っていない。
- 変更PythonのBlack/isort・flake8実行不能エラー検査、YAML構文、差分レビューを確認。既存billing.pyのBOMを取り除き、対象6ファイルのUTF-8/LFチェックに成功した。新しいユーザー表示文言はなく、レビューで追加の修正事項は見つからなかった。

## 継続監査: Google出力ジョブの実行時権限（2026-09-05）

- `451d5a90` を起点に外部出力を調査。Calendar/Sheetsは受付時に連携設定を確認する一方、workerは現在の有効設定・スコープ・ユーザー有効状態を再確認していなかった。Calendarでは待機中に参加資格を失ってもセッションの最新説明を取得して送る経路があった。
- 先に追加した回帰テストで、Calendar/Sheetsそれぞれの連携無効化、保存済みスコープ削除、連携設定削除、ユーザー無効化の8 subtestsと、Calendarの参加者削除ケースが失敗した。いずれもジョブが成功扱いになり、模擬送信へ進んだ。外部HTTPとトークン取得はモックで、実サービスへの送信はしていない。
- workerはトークン取得・更新や外部HTTPの前に有効設定・スコープ・ユーザー状態を確認し、許可されない場合は日本語の理由を持つ失敗状態にする。Calendarは受付・ICSで使う既存のセッション可視性関数を `integration_access.py` へ移し、実行時にも同じ条件を使う。可視性の条件自体は変更していない。
- 新規テストは拒否時にトークン取得とHTTPのいずれも呼ばれないことを確認。有効時は初回作成後に同じ外部イベントIDを更新し、新規作成を繰り返さないこと、SheetsのRAW指定を維持することを確認した。
- 専用SQLiteで新規テスト、既存の外部連携、AsyncJob、Discord/HO公開、Calendar APIを実行し、51件・subtests 8件成功（68.44秒、警告9件）。証跡: `tmp/formal-release-google-job-authorization-20260905.xml`、`tmp/formal-release-google-job-coverage.json`。変更行15行（views 2、tasks 13）と移動先関数を含む新規moduleの6実行対象行をすべて実行した。行カバレッジの記録であり、モジュール全体/分岐100%ではない。
- この確認は実行開始時の再認可に限定する。すでに送信中のHTTPを取り消すこと、送信済みの外部コピー削除、Google側の実権限失効・回復、実配送、全秘匿HO/GMメモの出力経路網羅は引き続き未検証。各試行の開始時には新しいDB状態を読むため、後続リトライにも同じ判定を適用する。
- 変更PythonのBlack/isort、flake8実行不能エラー検査、差分レビュー、対象6ファイルのUTF-8/LFチェックが成功。追加のエラー文言は日本語で、レビューで追加の修正事項は見つからなかった。

## 継続監査: ICSの日本語長文と改行（2026-09-05）

- `f68e0a35` を起点に購読フィードの出力形式を確認。[RFC 5545の3.1節・3.3.11節](https://www.rfc-editor.org/rfc/rfc5545)に基づき、CRLFでの行区切り、75 octets以内の折り返し、TEXT値内の改行・区切り文字を検証した。75 octetsの折り返しはRFCのSHOULDに対応する。
- 新規2テストを先に追加し、143バイトの物理行がそのまま出力されること、CRLF/CR入力から裸のCRが残ることを再現して失敗を確認した。
- TEXTのCRLF/CR/LFをエスケープ表現へ統一し、UTF-8の各文字を分割せず継続行の先頭空白も含め75バイト以内に折り返す。本文、タイトル、場所、カレンダー名に適用する。利用者データそのものは変更しない。
- 専用SQLiteで新規テストと既存外部連携テストの15件成功（37.27秒、警告9件）。日本語・絵文字のUTF-8復号、折り返し解除後の値一致、VEVENT/VTODO各1件の維持、区切り文字のエスケープ、private/no-store、既存の購読トークン更新時の旧URL失効を確認した。証跡: `tmp/formal-release-ics-encoding-20260905.xml`、`tmp/formal-release-ics-coverage.json`。
- エスケープ関数の3実行対象行と折り返し関数の14実行対象行はすべて実行された。行カバレッジであり、RFC全体への適合や各カレンダーアプリの受け入れを証明するものではない。実購読先での確認は残る。
- 変更PythonのBlack/isort、flake8実行不能エラー検査、差分レビューを確認。新しいユーザー表示文言はなく、レビューで追加の修正事項は見つからなかった。

## 継続監査: 固定依存関係のLinux全体検証（2026-09-05）

- `e7734d51` の追跡ファイルを隔離して検証用コンテナを作成したところ、`requirements-test.lock.txt` のハッシュ検証付きインストールが失敗した。Windowsで生成したロックにはIPythonのPOSIX依存 `pexpect` と、その依存 `ptyprocess` がなかった。ハッシュ検証を外して回避することはしなかった。
- `requirements-dev.txt` にWindowsでの再生成でもPOSIX依存を含めるための `pexpect>=4.9.0` を明記し、既存バージョンを維持したままpip-compileでdev/test両ロックを再生成した。追加は `pexpect==4.9.0` と `ptyprocess==0.7.0` のハッシュ付きエントリーだけで、3ファイル18行。`requirements.lock.txt` は変更していない。[pexpectの配布情報](https://pypi.org/pypi/pexpect/4.9.0/json)、[ptyprocessの配布情報](https://pypi.org/pypi/ptyprocess/0.7.0/json)
- 修正後、Linuxで `pip install --require-hashes -r requirements-test.lock.txt` と `pip check` が成功した。Windowsでも `requirements-dev.lock.txt` の `--dry-run --require-hashes` が成功し、実環境のパッケージ変更は行っていない。ログ: `tmp/formal-release-test-runtime-build.log`、`tmp/formal-release-windows-dev-lock.log`、予行レポート `tmp/formal-release-windows-dev-lock-report.json`。
- 検証ソースは `e7734d51` に今回のrequirements 3ファイルを適用したもの。`git archive` の追跡ファイルから作り、検証用Git indexを再構築してリポジトリ衛生テストも実行した。通常の作業DB・未追跡設定ファイルを使用していない。検証用Dockerfileは `tmp/formal-release-test-runtime/` に置いた。イメージ `sha256:c1585cf1aaac7786fb005b5f4fd25e0aebe7240ff40a7797909498c9481ae85a`、Python 3.11.16/Django 5.2.17/Stripe 15.5.1。
- `accounts api scenarios schedules support tableno tests/unit tests/integration` をCIと同じcoverage対象・70%ゲートで実行。外部通信なしの専用コンテナ内SQLiteで1,510件成功、4件失敗、3件セットアップエラー、subtests 257件成功（1,142.40秒、警告159件）。カバレッジは85.42%で70%ゲートを満たしたが、コマンドの終了コードは1であり、全体実行成功とは扱わない。JUnitの1,774件にはsubtestsを含む。
- 4件の失敗はCCFOLIAブラウザ出力テストの `FileNotFoundError: node`、3件のエラーはSeleniumのChrome Driver不足だった。アプリコードの失敗と区別して、検証環境を補完した。
- Node.js 20.20.2を追加したイメージ `sha256:5cfd026b464bb16a5dd09f0dfcd0223867a2bc99714b1688784c87a26580c2dc` で該当ファイル16件・subtests 10件成功（27.97秒、外部通信なし）。Chromium/ChromeDriver 152.0.7977.75を追加したイメージ `sha256:e85308d15236d0b2f33c19923a0f3e3ed8466ca20746338b95647f338873c8fa` では該当ブラウザ3件成功（85.64秒）。後者は画面の公開CDN資産を読み込むため通常のコンテナネットワークを使用し、DB・ユーザーは専用fixtureのみ。両方とも元の全体実行と重複する対象があるため、単純加算しない。
- 証跡ディレクトリは `tmp/formal-release-full-e773-output/`。全体は `run.log`、`junit.xml`、`coverage.xml`、`coverage.json`、再確認は `node-export-recheck.xml`、`browser-recheck.xml`。全体のflake8・Black・isortはすべて終了コード0（`static-checks.json`と各ログ）。Django check、makemigrations --check --dry-run、新規SQLiteへのmigrate、migrate --checkも成功（`migrations.log`）。終了したコンテナは `--rm` で除去された。
- Stripe接続を再確認したが `oauth_token_invalid_grant` のまま。対象ブランチのPR検索結果も0件。最新候補のリモートCI・PostgreSQL全体検証・本番相当実サービス検証は引き続き未完了。

## 継続監査: 販売条件と機能制限の棚卸し（2026-09-05）

- `c50b5fc6` のコード・既存テストから、[料金・有料機能の確定資料](FORMAL_RELEASE_PLAN_DECISIONS.md)を作成した。画像枚数の無料2枚/有料10枚、背景透過の有料限定・既定1日10回、作成済みセッションのシナリオ変更制限が、現行料金比較表に掲載されていなかった。
- シナリオアーカイブ画面は有料限定だが、作成・編集APIはログイン・可視性・所有権を確認し、有料判定を行わない。セッション作成時の関連付けにも有料判定がない。正式公開時の有料範囲についてユーザーに質問し、回答待ちとして記録した。
- 有料失効後に画像が無料上限を超えている場合、既存画像の更新もserializerの枚数制限で拒否し得る。既存データ保持と追加・編集制限を販売条件として確定する必要がある。背景透過の失敗ジョブも日次枠に含まれること、保持期間は既定設定であり削除運用の証明ではないことも明記した。
- 今回は文書のみの変更。新しいAPI制限、料金変更、データ削除、外部操作は行っていない。新規の動的テストは実行せず、全APIの検証完了とは扱わない。公開判定B01に未決事項への参照を追加した。

## 継続監査: DB・メディアの隔離復元試験（2026-09-05）

- `792270bd` の作業ツリーがcleanであることを確認し、既存の[復旧手順](../infrastructure/backup.md)を点検した。DBと画像を別時点で取得する場合の整合性確認、復元先の分離、復元後の配送再開条件が不足していたため追記した。pg_restoreは空の専用DBに単一トランザクションで復元し、失敗時に部分復元のまま進まない手順へ変更した。S3例は世代別の取得先と専用復元先を使い、syncだけではVersionIdによる過去時点復元にならないことを明記した。
- 実環境のバックアップには接続せず、Dockerの専用internal network、公開ポートなし、tmpfs上のPostgreSQLで試験した。PostgreSQL 16.15、イメージ `sha256:80f4c7a5e91618546dce5b4fe60cf03b14c0f9efa7e40157278d122772ced8d2`。アプリは固定依存の検証イメージ `sha256:c1585cf1aaac7786fb005b5f4fd25e0aebe7240ff40a7797909498c9481ae85a` を使用した。`e7734d51` から `792270bd` までの差分がdev/test依存ロックと文書だけで、アプリ・migrationに差がないことを確認した。
- 空DB `drill_source` に全migrationを適用し、通常GM/PL各1人、privateグループとセッション、PL役割、秘匿HO、日本語・絵文字のタイトル、PNG添付1件を作成した。連携資格情報は投入せず、worker/beatを起動せず、メールはlocmem・メディアは試験専用ローカル領域を使用した。試験データ作成後は元DB/画像への書き込みを行っていない。
- `pg_dump --format=custom --no-owner --no-acl` とtarで取得し、別の空DB `drill_restored` に `pg_restore --exit-on-error --single-transaction --no-owner --no-acl` で復元した。全91テーブルの行数・行JSONのSHA-256（合計607行、migration/auth等の初期データを含む）、87個のsequenceの値とis_calledが一致した。権限付与ACL/DBロールの復元検証ではない。
- DBだけ復元した段階では `media manifest differs` で検証が終了コード1となることを確認した。その後、tarを専用復元先へ展開すると画像の相対パス・SHA-256が一致し、DB参照先での存在確認・画像デコードも成功した。秘匿フラグ、HO対象PL、セッションGMの関連が復元され、新規ユーザーの採番も既存最大IDを超えた。HTTP経由の閲覧権限や全添付種別の試験ではない。
- 復元先で `migrate --check` とDjango `check` が成功した。DB復元コマンド0.422秒、画像展開0.172秒、内容照合1.953秒。この最小fixtureの操作時間は障害検知・環境準備・切替を含まず、本番RTOを示さない。実RDS snapshot/PITR、実S3 VersionId、暗号鍵・最小DB権限、公開規模の復元、課金/配送の再照合、合意RPO/RTOは未確認。
- 証跡は `tmp/restore-drill-20260905/` の `run.py`、`probe.py`、`drill_settings.py`、`results.json`、`expected.json` と各操作ログ。試験dumpのSHA-256は `a9ba7b71729dea2e73b7ad8547f4c586dc6bb38f90ab1b656280d8c65204c38e`、メディアtarは `9a1c7ac73eef21c83bec3aac50b1d8d6eec242b7e082253c5cf83d4576f9292b`。これらは専用の合成データで、リポジトリには追加しない。試験コンテナ停止・専用network削除が成功し、同名コンテナが残っていないことを確認した。

## 継続監査: 秘匿HO添付の直接URL（2026-09-05）

- `4d75e043` のclean状態から監査。添付一覧には `can_view_handout` がある一方、serializerの `file` / `file_url` とモデルのダウンロードURLがstorageのURLを返していた。既存の固定依存イメージで、通常GMが試験用textファイルをアップロードし、対象PL・無関係ユーザー・匿名でそのURLを取得した。無関係ユーザーの一覧は403、匿名は401だが、ファイル直URLは両方200で試験用秘匿内容と完全一致し、Cache-Controlもなかった。
- 再現はDEBUG=True、専用SQLite/TemporaryDirectory、外部通信なしのコンテナで実施。実環境の添付を取得していない。スクリプトは `tmp/handout-direct-url-audit-20260905.py`、初回再現の結果はタスクのコマンド出力に記録した。本番設定では既定querystring_auth=FalseとCloudFrontへの全オブジェクトGetObject許可を確認したが、実配信の同じ不備を動的に確認した証拠ではない。
- 新規回帰テストを先に実行し失敗を確認。その後、認可付きダウンロードAPI、既存URLの認可、serializer両フィールドのAPI URL化を実装した。取得ごとに最新HOの対象者/GM判定を使い、拒否・欠損・成功すべてにno-storeを付ける。成功はattachment・application/octet-stream・nosniffで返し、保存済みファイル名を直接配信しない。
- 旧メディアURLはパスの正規化後に秘匿プレフィックスを判定する。`other/../handouts/` やエンコードされた同等パスを、静的ファイル配信への迂回に使えないようにした。一般メディアの開発時配信とDEBUG=False時の非配信も検証した。
- TerraformでCloudFrontからのhandoutsオブジェクトGetObjectを拒否する構成を用意し、fmt/validate成功。構成の適用とキャッシュ失効は別途必要であり、[配備準備計画](AWS_PRE_FORMAL_RELEASE_VALIDATION_PLAN.md)へ手順と残リスクを追加した。権限変更・配備・invalidation・実ファイルの移動は実施していない。
- 修正ファイルを固定依存イメージへ読み取り専用でマウントし、新規6件と既存の添付・HO権限・PL枠を合わせて37件成功（23.994秒）。専用SQLite、外部通信なし。証跡 `tmp/handout-download-access-green.log`。途中の試験コードはストリーミングレスポンスを二重にcloseしてDBを閉じたため修正し、Djangoテストクライアントの自動closeを利用した。製品コードでDB接続エラーを無視していない。
- ローカル修正の成功は、実CloudFrontキャッシュの失効、S3実権限、大容量/同時ダウンロード、全添付種別の閲覧UI、他のCDN/サーバー直配信経路を証明しない。この対策の実環境検証が終わるまでF05/Q04は公開阻害事項として残す。
- 新規6件をカバレッジ取得付きで再確認し成功（0.716秒）。新しいダウンロードビューの実行対象行はすべて実行され、`tableno/media_views.py` は12/12行。既存の一覧/削除を含むattachment_views全体は45/69行であり、モジュール全体/分岐100%ではない。証跡 `tmp/handout-download-coverage.json` / `tmp/handout-download-coverage.log`。変更PythonのBlack/isort/flake8確認が成功し、新しいUI文言はない。差分レビューで追加の修正事項は見つからなかった。

## 継続監査: 開発環境の添付配信設定と停止案（2026-09-05）

- `69d4468a` のclean状態から、AWSアカウント・稼働ECS・S3ポリシー・Public Access Block・CloudFront behavior/署名設定・Task Roleを読み取り確認した。CloudFrontへの全GetObject許可と署名者/鍵グループ無効を確認し、設定上の懸念を実環境の構成でも確認できた。実ファイルのHTTP取得や漏えい発生の調査は行っていない。
- 添付プレフィックスの一覧は件数だけを出力し486オブジェクト、切り詰めなしだった。ユーザー数、秘匿HO数、実データ/試験データの区分は不明。現行CloudFrontのTTLはすべて0であり、以前の一般的なinvalidation手順をこの環境へ無条件に実施せず、応急措置をポリシー変更だけに絞った。
- 実ポリシーからDenyのみを追加したレビュー可能なJSONを作り、AWS Access Analyzerのポリシー検証で指摘0件。変更対象・JSONハッシュ・既存添付停止の影響・適用直前の再照合を[配備準備計画](AWS_PRE_FORMAL_RELEASE_VALIDATION_PLAN.md)へ記録した。`tmp/prepare-handout-containment.py` は読み取りとローカルファイル作成だけを行う。
- 権限変更の承認境界に基づき、応急措置を先行適用するかアプリと同時反映するかをユーザーに確認中。回答を待たずにポリシーを変えたり、実データを変更したりしていない。今回の進捗は実環境設定の証拠取得と検証済み変更案の準備であり、対策完了ではない。

## 継続監査: 最新候補イメージのPostgreSQL検証（2026-09-05）

- `b8fad941` のclean状態を確認し、git archiveを専用ディレクトリへ展開してDockerfileからビルドした。ローカルイメージID `sha256:45e2df5a6ada21fbe0209ca4943005b4ad969f08f58619ac21b0511194f39b27`。実行ユーザーtableno、Python 3.11.16/Django 5.2.17/Stripe 15.5.1。pip check成功、makemigrations --check --dry-runは変更なし。ホスト作業ツリーのソースをイメージへ上書きしていない。
- Docker internal network、公開ポートなし、tmpfsのPostgreSQL 16を用意し、イメージ内の添付ダウンロード・既存添付・HO権限・PL枠・billing・paid_feature_lifecycleを実行して227件成功（55.953秒）。課金イベントは引き続き試験用署名fixtureであり、実Stripeサービスには接続していない。
- 同じイメージを通常entrypointで起動し、専用の空DBに全migrationを適用した。最初のヘルス確認は起動途中で接続失敗だったが、同じコンテナのDaphne起動後にHTTP 200、database/cacheともokとなった。コンテナを作り直して失敗を隠していない。APP_ENV=local、外部サービスなしの確認で、aws-preの実Secrets・S3・Redis・公開ルーティングの検証ではない。
- 証跡は `tmp/formal-release-b8fad941-` で始まるbuild/postgres/runtimeログ、ready.json、image.json。app/PGコンテナ停止、専用network削除、同名の稼働コンテナがないことを確認した。ローカルイメージIDと未取得のECR manifest digestを区別し、配備準備資料の候補と差分を `8cf3c7f7..b8fad941`（121ファイル）へ更新した。
- 今回は候補イメージの作成と対象を絞ったPostgreSQL検証が進捗。全体CI、全機能/外部サービス検証、配備承認、秘匿添付ポリシーの応急措置への回答は引き続き未完了。

## 継続監査: 静的指摘とサンプル作成コマンド（2026-09-05）

- `9f9139ec` のclean状態でBandit 1.9.4を `accounts schedules scenarios support tableno api` に再実行。HIGH 0、MEDIUM 1、LOW 536、解析エラー0、終了コード1。証跡 `tmp/formal-release-bandit-9f9139ec.json` / `.log`。過去のMEDIUM 6件のうち、eval・タイムアウト・LINE HTTPの5件はこの再実行でも残っていない。全指摘を解決済みとは扱わない。
- 残るMEDIUM B608は `reset_dev_session_data.py` のSQLite外部キー診断SQL。識別子はPRAGMAのDBメタデータから、rowidはバインド値から来る。handleはDEBUG=Falseを拒否し、診断自体はSQLiteでのみ実行される。Web入力由来のSQL注入経路はこの確認では見つからなかったが、スキーマ識別子の引用符処理には改善余地があり、指摘は抑制せず残した。
- LOW B105の4件はOAuthトークン取得先URL2件、公開セッションの権限False値、パスワード復旧フォームのクラスパスであり、埋め込み認証情報ではない。ダイス用randomのB311も暗号用途とは別である。一方、例外握りつぶしや管理コマンドの固定パスワードは、ファイル名にtestがあるだけでテスト専用として除外しない。
- `create_sample_data` は固定パスワードでユーザーを作成し、`--clear` ではユーザー・シナリオ・セッション等を削除するが、実行環境の制限がなかった。コマンドを実行できる運用者による誤操作の問題であり、未認証HTTPから直接実行できるという指摘ではない。
- 先にSimpleTestCaseを追加すると、拒否すべき10条件でCommandErrorが発生せず、モックされたユーザー作成後の処理へ進んで失敗した。実データにはアクセスしていない。DEBUG=True、APP_ENVがlocal/dev/development、ENVIRONMENTがlocal/developmentの場合だけ通すガードをデータ削除・作成の前に追加した。新しい拒否メッセージとhelpは日本語。
- 固定依存の `b8fad941` 配備用イメージに変更コマンドとテストだけを読み取り専用で適用し、2テスト・13 subtests成功（0.013秒）。共有/本番/不明環境、DEBUG=False、--clear有無の拒否と、ローカル3別名での従来処理呼び出しを確認した。DB処理はモックで、今回の変更でサンプルデータ自体を作成・削除していない。証跡 `tmp/sample-data-guard-red.log` / `tmp/sample-data-guard-green.log`。
- ローカルで同じ2テストを再確認し、追加ガードの実行対象2行（if/raise）を両方実行した。モジュール全体のカバレッジ100%ではない。証跡 `tmp/sample-data-guard-coverage.json`。Black/isort/flake8と差分・日本語文言レビューを確認した。
- `create_test_data`、`create_session_test_data`、`create_flow_test_data` 等は別の管理コマンドであり、今回のガードで一括保護されたとは扱わない。LOW指摘の残りとこれらの運用制限は引き続き確認対象。今回のコマンド修正は未配備で、既存アカウントの有無やパスワード変更も実施していない。

## 継続監査: 一括テストデータコマンドの環境境界（2026-09-05）

- `44bb888c` のclean状態から、残る一括作成コマンドとリセット処理を確認。create_test_data、create_test_characters、create_session_test_data、create_flow_test_data、create_advanced_scheduling_test_dataは環境判定がなく、reset_dev_session_dataはDEBUG判定より先にtransaction.atomicへ入っていた。
- 7コマンド×8環境条件のテストを先に追加。既に保護したcreate_sample_dataの8条件以外、48条件で期待する拒否にならず、SimpleTestCaseがDBアクセスを検出して失敗した。実データ操作はしていない。`tmp/development-command-boundaries-red.log`。
- `tableno/development_commands.py` に共通デコレータを設け、7コマンドに適用した。条件は前回のsampleと同じで、transaction.atomicを使うコマンドではその外側に置き、接続開始前に判定する。既存のデータ生成・削除本体は変更せず、拒否メッセージは日本語。共有環境を許可する例外フラグは追加していない。
- 固定依存イメージb8fad941へ変更Pythonと既存sampleテストを読み取り専用マウントして、3テスト・69 subtests成功（0.055秒）。内訳は全7コマンドの拒否56条件と既存sampleの13条件。後者はローカル3別名で従来の処理群が呼ばれることも確認する。6つの追加コマンドの全データ生成機能を実行したという意味ではない。`tmp/development-command-boundaries-green.log`。
- ローカルのカバレッジ付き再確認でも3件成功（0.136秒）、共通デコレータは10/10実行対象行。証跡 `tmp/development-command-boundaries-coverage.json`。変更PythonのBlack/isort/flake8と差分レビューを確認した。新規デコレータの行カバレッジであり、各コマンド本体や全分岐100%ではない。
- [テストデータ管理ガイド](../testing/TEST_DATA_MANAGEMENT.md)に対象7コマンドと適用条件を明記した。宣言された環境設定が実DB接続先と一致することは運用時に別途確認する。ensure_dev_login_userの既存の明示オプションは今回変更していない。共有DB/アカウント/画像・実環境設定への変更は実施せず、対策は未配備。

## 継続監査: SQLite外部キー診断の動的SQL（2026-09-05）

- `1b80f66e` のclean状態からB608の対象を動的に確認した。リセット本体を実行せず、独立したインメモリSQLite接続に試験用の親/子テーブルを作って診断メソッドだけを呼び出した。引用符を含むテーブル名では追加PRAGMAの構文エラー、WITHOUT ROWIDテーブルでは追加SELECTの `no such column: rowid` を再現。3件中2件がエラーになった。`tmp/dev-foreign-key-diagnostics-red.log`。
- SQLiteのforeign_key_checkは違反ごとにテーブル・rowid・参照先・制約番号を返し、WITHOUT ROWIDではrowidがNULLになる。[SQLite公式仕様](https://www.sqlite.org/pragma.html#pragma_foreign_key_check)に合わせ、返された4項目を直接表示してCommandErrorを出すよう変更した。識別子を補間する追加SQLと行内容の再取得を削除し、先頭50件の表示制限と整合性エラーでの停止を維持した。エラー文言は日本語にした。
- 固定依存イメージb8fad941へ変更コマンド・共通ガード・新規テストを読み取り専用で適用し、3件成功（0.002秒）。正常な参照では無出力、引用符付き識別子とWITHOUT ROWIDではSQLエラーではなくCommandErrorと違反情報が出ること、試験行が削除されないことを確認した。`tmp/dev-foreign-key-diagnostics-green.log`。
- ローカルでは環境境界テストを含む6件も成功（0.090秒）。追加したfor/出力/raiseの3実行対象行をすべて実行した。`tmp/dev-foreign-key-diagnostics-coverage.json`。非SQLiteの診断やコマンド全体のカバレッジ100%ではない。通常の作業DB・共有DB・実データは使っていない。
- 変更後にBandit 1.9.4をaccounts/schedules/scenarios/support/tableno/apiへ再実行し、HIGH 0・MEDIUM 0・LOW 536、解析エラー0。指摘抑制設定は追加していない。全重要度での終了コードはLOWが残るため1で、全セキュリティ検査合格とは扱わない。証跡 `tmp/formal-release-bandit-fk-fix.json` / `.log`。コード品質と日本語文言・差分レビューを確認し、秘匿添付の実環境対策を含む公開条件は引き続き未完了。

## 継続監査: LOW指摘と添付削除の再試行（2026-09-05）

- `dd92a2da` のclean状態から前回のLOW 536件を分類した。test_*.py/tests.py/tests配下に448件、それ以外に88件（B311 66、B110 11、B106 6、B105 4、B112 1）。管理コマンドは名前にtestを含んでも通常の処理として確認した。分類は指摘の一括抑制や、全件の無害判定ではない。
- B105は前記のURL・False値・クラスパス、B311はダイス/テストデータ用の乱数、B106 6件は今回までにローカル専用とした一括生成コマンドの固定資格情報だった。例外抑制は別途確認し、添付削除でストレージ失敗を無視してDB行を消す不備を見つけた。
- 試験用添付に対してstorage.deleteを失敗させる回帰テストを先に追加すると、期待503に対し204が返った。serviceとHandoutAttachment.deleteの両方が例外を握りつぶすため、失敗したファイルの参照を失う経路だった。実S3や実利用者の添付ではなく、専用のローカルメディアと試験DBを使用した。証跡 `tmp/handout-deletion-retry-red.log`。
- ファイル削除をモデル側の1回にまとめ、成功してからDB削除へ進むよう修正した。serviceは失敗時に一般的な日本語の再試行案内を503で返す。ログは添付IDと例外型のみとし、バックエンドの例外本文を返さない。ローカルfilesystemとS3 storageは既に存在しないファイルの削除を成功として扱うため、事前existsチェックも不要にした。
- 固定依存イメージb8fad941へ変更model/service/テストを読み取り専用適用し、新規3件と既存の添付・ダウンロード権限を合わせて26件成功（0.604秒）。削除失敗時にDB参照とファイルを保持すること、復旧後の再試行で両方削除すること、PLはstorage削除を呼べないこと、ファイル欠損時でもDB削除できることを確認した。`tmp/handout-deletion-retry-green.log`。
- カバレッジ取得用の固定依存テストイメージでも新規3件成功（0.162秒）。追加した503例外定義・try/catch/ログとmodelの削除行はすべて実行された。モジュール全体/全分岐100%ではない。`tmp/handout-deletion-coverage.json` / `.log`。変更PythonのBlack/isort/flake8、差分、日本語API文言を確認した。
- 再度Banditを同じアプリ範囲へ実行し、HIGH 0・MEDIUM 0・LOW 534、解析エラー0。全重要度での終了コードは1のまま。`tmp/formal-release-bandit-deletion-fix.json` / `.log`。
- 今回は添付単体削除の失敗/再試行を修正した。QuerySetによる一括削除・親からのカスケード・storage削除成功後のDB障害の整合性・S3旧バージョンの保持/消去まで解決したわけではない。ScenarioImage/SessionImageの類似例外抑制、既存migrationのメディア処理、ログイン/画像serializerのフォールバック、技能一括更新の部分失敗は引き続き確認対象。実環境のデータ削除や配備は行っていない。

## 継続監査: シナリオ・セッション画像削除の再試行（2026-09-05）

- `5ba57724` のclean状態から、ScenarioImageとSessionImageの単体DELETEを確認。新規テストでstorage.deleteを失敗させると、両方で503を期待したところ204になり、前回の秘匿添付と同じ失敗の握りつぶしを再現した。`tmp/image-deletion-retry-red.log`。
- 両モデルはstorageの削除が成功してからDB行を削除するよう変更し、各APIは既存の権限確認後に共通の `delete_media_instance` を使う。前回の秘匿添付もこの共通処理へ移し、503と日本語の再試行案内を揃えた。ログにはモデル名・ID・例外型だけを記録し、バックエンド本文をAPIへ返さない。画像の公開範囲や削除権限は変更していない。
- 固定依存の配備用イメージb8fad941へ変更ソースとテストを読み取り専用で適用し、画像削除再試行、秘匿添付再試行、既存のシナリオ/セッション画像・添付テスト計50件成功（39.274秒）。新規画像テストは2種それぞれで失敗時のDB参照/ファイル保持、復旧後の削除成功、無関係ユーザーの拒否、既にファイルがない場合のDB削除を確認した。専用SQLite/TemporaryDirectory、外部通信なしであり、実S3は使用していない。`tmp/image-deletion-retry-green.log`。
- カバレッジ取得用の固定依存イメージで新規画像3件と秘匿添付3件も成功（0.701秒）。共通処理は14/14実行対象行。モデル全体や全分岐100%ではない。`tmp/image-deletion-coverage.json` / `.log`。変更PythonのBlack/isort/flake8と差分レビューを確認した。
- シナリオ/セッション画面はaxios.delete成功後だけ削除成功表示・再読み込みへ進み、catch側はAPIのdetailを表示することをソースで確認した。新しい日本語503メッセージを既存画面へ渡せる構造であり、今回はブラウザ描画による検証や画面変更は行っていない。
- 親削除時のカスケード、QuerySet一括削除、過去migrationのメディア削除、storageとDBをまたぐ原子性、S3旧バージョンの保持方針は引き続き別の確認事項。実環境への配備・データ変更は行っていない。

## 継続監査: de049c7bの全体検証環境と静的検査（2026-09-05）

- `de049c7bfe58155869d2ad527269998c219604f9` のgit archiveからテスト用ソースを展開し、固定依存とNode/Chromium/ChromeDriverを備えた隔離イメージを作成した。タグは `tableno-formal-release-test:de049c7b-browser`、ローカルイメージIDは `sha256:dacc4de696bab40796db34c98fc1ce9aa57023fe9b832791298feaba108873e4`。本番配備用イメージやECRのmanifest digestとは別である。
- 同イメージの `accounts api scenarios schedules support tableno tests` に対するflake8、Black --check、isort --check-onlyはすべて終了コード0。自動整形は行っていない。証跡は `tmp/formal-release-de049-full-output/quality.json` と各検査ログ。
- 同イメージで `python -m bandit -r accounts schedules scenarios support tableno api -f json` をネットワークなしで実行し、HIGH 0・MEDIUM 0・LOW 532、解析エラー0。LOWが残るため終了コードは1。抑制を追加せず、セキュリティ検査全体の合格とは扱わない。証跡は `tmp/formal-release-de049-full-output/bandit.json`。
- SQLite全体テストはCIのUnit / Integrationと同じ対象（`accounts api scenarios schedules support tableno tests/unit tests/integration`）で、1,532件成功・3件失敗・341 subtests成功、1,101.26秒、終了コード1。カバレッジは86.37%で70%閾値を超えたが、全体テスト成功ではない。証跡は同ディレクトリの `run.log`、`junit.xml`、`coverage.xml`、`coverage.json`。ブラウザ資材のCDN取得を許す隔離コンテナで実行し、実サービスの資格情報や共有DBは使用していない。
- 失敗3件は `DevelopmentForeignKeyDiagnosticsTest` がunittest.TestCaseを継承し、pytest-djangoが独立SQLite接続も拒否するため、診断処理に到達する前にRuntimeErrorとなったもの。テストをDjango TestCaseへ変更し、専用のインメモリSQLiteで実際の制約違反を再現する内容と判定は維持した。同イメージへこのテストファイルだけを読み取り専用で適用したpytest再検証は、環境制限を含む6件・69 subtests成功（16.36秒）。`fk-runner-pytest.log`。この部分再実行を元の全体実行成功に読み替えない。
- 同じde049c7bイメージでCIの別枠 `pytest tests/system -q -rs` もネットワークなしで実行し、12件成功（24.16秒、警告11件、終了コード0）。`system.log` / `system-junit.xml`。コマンド名がsystemでも実Stripe/OAuth/外部配送・ブラウザでの利用者操作を実証するものではない。
- 修正後のDjango標準ランナーも同じ隔離イメージとテストファイル適用で関連6件成功（0.046秒）。`fk-runner-django.log`。変更PythonのBlack/isort/flake8は成功し、ユーザー向け文言の変更はない。修正を含む単一全体実行・リモートCI・PostgreSQL全体検証はまだ未取得。

## 継続監査: 通常ユーザーのグループ・セッション画面操作（2026-09-05）

- 既存の作成E2Eは主に開発用adminログインだったため、`regular-user-session.spec.ts` を追加。アプリは `0ea0e747` の固定依存テストイメージで、専用の一時SQLiteと127.0.0.1:8029だけに公開したローカルサーバーを使用した。メールはコンソール出力、外部サービス資格情報なし。通常のサインアップ画面から作成し、開発用ログイン・APIでの作成代行・通信モックは使用していない。
- 新規登録、非公開グループの画面作成、グループ内セッションの画面作成、完了への更新、再読み込み後の完了表示とAPI保存値（予定2時間=120分）を確認した。別ブラウザコンテキストの新規登録者はグループ/セッションAPIが404、詳細画面が403で、日本語拒否メッセージが出てセッション名が含まれないことを確認。所有者ページのJavaScript pageerrorは0件。
- 最終版をChromium・Firefox・WebKitで実行して3件成功（45.9秒、終了コード0）。証跡 `tmp/formal-release-regular-user-final.log`、`tmp/formal-release-regular-user.json` と `tmp/formal-release-regular-user-results/` の画面画像。最初は試験パスワードのユーザー名類似性で登録拒否、次に詳細画面403を404とした試験期待値の誤り、WebKitでモーダル直後の入力が空になる試験操作を確認し、パスワードを独立生成、画面の既存403契約に合わせ、入力欄をクリックして入力値も検証するよう直した。アプリの権限や入力検証を緩和していない。
- 専用DBの試験アカウント15件（再試行を含む）はstaff 0・superuser 0、完了セッション7件。`tmp/formal-release-regular-user-fixtures.json`。終了後に今回の専用サーバーコンテナを停止・自動削除し、その中のDB/メディアも破棄した。通常の作業DBや共有環境は変更していない。
- 画面画像では完了・グループ内・2時間を確認した。一方、拒否画面はDRFの開発者向けAPI表示であり、セッション詳細のハンドアウト見出し/操作が狭い幅で不自然に折り返される点も残る。公開用UIとしての改善対象で、全画面の視覚品質合格とは扱わない。グループ招待・所有権引継ぎ・PL参加・実プレイ履歴・実メール・有料契約の操作を今回すべて検証したわけではない。

## 継続監査: 0ea0e747のSQLite全体実行成功（2026-09-05）

- `0ea0e747` のgit archiveからテストイメージを再構築。タグ `tableno-formal-release-test:0ea0e747-browser`、ローカルID `sha256:63f29e25b27b8241f8bf7ca50cc8cb7506130b7379ab2d8c16be038cdd38d6db`。前回失敗したSQLite診断テストのDjango TestCase修正を含む。
- CIのUnit / Integrationと同じ対象 `accounts api scenarios schedules support tableno tests/unit tests/integration` に対する単一pytest実行が、1,535件・341 subtests成功、失敗/エラー/skip 0、1,237.92秒、終了コード0で完了した。JUnitのtests=1,876はsubtestsを含む件数。警告159件あり。全体カバレッジは30,805/35,627行=86.47%で、設定された70%閾値を満たした。新規コード全分岐100%や全製品機能の網羅を意味しない。
- 証跡は `tmp/formal-release-0ea0e747-full-output/run.log`、`junit.xml`、`coverage.xml`、`coverage.json`、`build.log`。`tableno.settings`、ローカル専用SQLite、固定依存・Node・Chromium/ChromeDriverを使用した。system/E2E別枠、リモートCI、実外部サービス、本番設定での動作はこの全体実行に含まない。
- 後続fcce666cは通常ユーザーE2Eと文書の追加であり、今回のアプリ/単体・統合対象のソース変更はない。SQLite成功だけで本番DB検証やQ03を合格にしない。

## 継続監査: PostgreSQL全体実行で判明した失敗（2026-09-05）

- 同じ0ea0e747イメージ・同じUnit / Integration範囲で、PostgreSQL 16.15の全体pytestを実行した。`tableno.settings` のDB_ENGINEをpostgresに変更し、外部公開ポートなしの専用DBコンテナ・専用ネットワーク・tmpfsデータ領域を使用。本番設定全体や実RDSの検証ではない。
- 結果は通常テスト1,526件成功・9件失敗、subtests 338件成功・3件失敗、1,287.14秒、終了コード1。pytest表示の `12 failed` は失敗subtestsを含む。警告159件、カバレッジ86.02%。証跡は `tmp/formal-release-0ea0e747-full-output/postgres-run.log`、`postgres-junit.xml`、`postgres-coverage.xml`、`postgres-coverage.json`。失敗本文を `postgres-failures.json` に抽出した。
- 参加者の紐付け承認（グループ経由/セッション経由の2件）とセッション報酬反映（1件）は、NULLを許す関連の外部結合にFOR UPDATEが適用され、PostgreSQLのNotSupportedErrorになる。`schedules/participant_claims.py` の承認処理と `schedules/reward_views.py` の反映処理で再現した。同形の却下処理も確認対象。ロックを単に取り除かず、同時操作時の整合性を維持して修正する必要がある。
- 他の失敗は技能保存失敗ログのキャラクターID不一致（1件）、所持品/財産APIの期待200/201に対する404（5件）、一覧と詳細serializerの参加者並びを含む比較不一致（owner/manager/gmの3 subtests）。IDの採番や並び順への依存と実装不備を切り分ける。秘匿HOのtitle集合の判定自体は通過しており、この比較失敗だけで漏えい発生とは扱わない。
- PostgreSQL全体の失敗は未解消。SQLite全体成功や、過去のPostgreSQL関連テスト成功を代替証拠にせず、原因別の修正・回帰テストと修正後の全体確認を続ける。

## 継続監査: PostgreSQLの報酬反映ロック修正（2026-09-05）

- 報酬反映はnullableな関連を含むselect_relatedにFOR UPDATEを付けていた。PostgreSQL全体での既存テスト失敗に加え、独立した2接続から同じ報酬へ同時POSTするTransactionTestCaseを追加し、修正前に同じNotSupportedErrorを再現した。`tmp/reward-concurrency-red.log`。SQLiteの行ロック無効状態を並行性の証明に使わず、このケースはhas_select_for_updateを持つDBに限定した。
- `SessionRewardViewSet.apply` は報酬行、参加者行、更新する既存成長記録を個別にselect_for_updateで取得する。nullableな関連への結合ロックを除き、報酬の反映判定から記録更新までのtransaction.atomicと、同一報酬への反映の直列化を維持した。
- 0ea0e747の固定依存イメージへ変更view/新規テストを読み取り専用で適用し、専用PostgreSQL 16の既存報酬テストと新規並行テスト4件成功（9.16秒）。証跡保存の実行も4件成功（9.89秒）。2件の同時反映は両方200、成長記録1件、経験点7を確認した。`tmp/reward-concurrency-green.log`、`tmp/reward-fix-postgres-proof.log`、`tmp/formal-release-0ea0e747-full-output/reward-fix-junit.xml`。
- 同ディレクトリの `reward-fix-coverage.json` で、applyの実行対象行に未実行行なし。reward_views全体は99/112行=88.39%で、全モジュール100%という主張ではない。SQLiteの既存報酬テスト3件も成功（23.57秒）。`tmp/reward-fix-sqlite.log`。Black/isort/flake8、差分と日本語の試験表示を確認し、アプリのユーザー向け文言は変更していない。
- 専用PostgreSQLコンテナとネットワークを停止・削除した。実RDS、共有DB、外部サービスの変更なし。参加承認/却下のロック、キャラクターID関連、一覧serializer比較の不一致は別の未完了作業であり、PostgreSQL全体成功の証拠はまだない。

## 継続監査: PostgreSQLの参加者紐付け承認・却下（2026-09-05）

- 全体実行で失敗した承認処理に加え、nullableな対象を持つ却下処理、同じ一時参加者情報へのグループ/セッション経由の同時申請、共通情報を持たない単独ゲストへの同時申請をテストした。修正前は新規3件ともFOR UPDATEのnullable外部結合で失敗。`tmp/claim-concurrency-red.log`。
- 承認では共通のParticipantIdentity（ある場合）、対象SessionParticipant（主キー順）、申請の順で個別に行ロックを取得する。ロック後に申請の最新状態を確認する。競合申請が自分の申請行を先にロックして互いを拒否更新しようとする順序を避け、紐付けと競合申請の却下を同一トランザクションで維持した。却下処理は更新対象の申請行だけをロックし、nullableな関連の結合を外した。
- 0ea0e747固定依存イメージへ変更serviceと新規テストを読み取り専用で適用し、専用PostgreSQL 16で新規3件・既存のグループ/セッション権限テストを合わせ19件成功（30.49秒）。2接続からの競合承認はそれぞれ成功1件・409が1件、申請はapproved/rejected各1件となり、対象参加者とグループ所属は承認されたユーザー1人へ一致した。自己却下403・再却下409とコメント保存も確認。`tmp/claim-concurrency-green.log`、`tmp/formal-release-0ea0e747-full-output/claim-fix-junit.xml`。
- 同ディレクトリの `claim-fix-coverage.json` で、新規ロック取得・対象抽出の実行対象行はすべて実行。モジュール全体は97/117行=82.91%で、全分岐100%ではない。SQLiteは同時行ロックの証明に使わず、却下と既存権限の17件を実行して成功（45.76秒）。`tmp/claim-fix-sqlite.log`。
- Black/isort/flake8、UTF-8/LF、差分と試験用日本語表示を確認。アプリのユーザー向け文言は変更していない。専用DBコンテナとネットワークを削除し、実環境の変更なし。キャラクターID不一致・所持品API404・一覧比較の不一致と、修正後のPostgreSQL全体確認は引き続き未完了。

## 継続監査: 共通キャラクターIDと版別詳細IDの区別（2026-09-05）

- 所持品API5件の404は、試験用URLへ共通CharacterSheetのIDではなくCharacterSheet6thのIDを渡していたためだった。モデル関連は詳細ID、API URLは共通IDという既存の契約へテストを合わせ、API自体のアクセス制御やID解決は変更していない。詳細IDを共通IDと異なる値で作成すると、SQLiteでも変更前の5件が404になることを再現した。`tmp/character-id-red.log`。
- 技能保存失敗のログは実装側の不備で、詳細IDをcharacter_sheet_idとして記録していた。URLの検証済み共通IDと、保存対象技能の詳細IDを別項目として記録するよう変更した。追加のDB照会をエラー記録時に行わず、元の例外を再送出する。ログの試験はID末尾の区切りも確認し、1が1001へ部分一致する偽陽性を防止した。旧実装で厳密な判定が失敗する証跡は `tmp/character-id-log-red.log`。
- 6版/7版とも共通IDと詳細IDを意図的に分け、失敗ログへ共通ID・詳細ID・技能IDが正確に入ることを確認した。0ea0e747の固定依存イメージへ変更view/テスト2ファイルを読み取り専用で適用し、最終版の関連24件はSQLiteで成功（30.82秒）、PostgreSQL 16で成功（18.10秒）。`tmp/character-id-sqlite-final.log`、`tmp/character-id-postgres-accounts.log`、`tmp/formal-release-0ea0e747-full-output/character-id-accounts-junit.xml`。
- PostgreSQLの最終成功実行はCIと同じ `--cov=accounts` 指定で、同ディレクトリの `character-id-accounts-coverage.json` にログ変更行の実行を保存した。先行して `--cov=accounts.views.character_views` とモジュールを直接指定した実行では14件が接続終了等で失敗し、別の最小試験でもDRFスキーマ初期化エラーになった。`tmp/character-id-postgres-final.log` / `tmp/character-id-connection-probe.log`。これらを成功扱いにしない。[Coverage.py公式説明](https://coverage.readthedocs.io/en/7.14.1/source.html)では、計測対象のモジュールが先行・重複インポートされる副作用を説明しており、今回の指定差による初期化異常もこの影響と考えられる。内部原因の完全な証明ではない。
- Black/isort/flake8と差分を確認し、アプリ画面の文言・保存ルールの変更なし。専用PostgreSQLコンテナとネットワークを削除した。残る一覧serializer比較の不一致と、修正群をまとめたPostgreSQL全体確認は未完了。

## 継続監査: セッション参加者配列の安定した順序（2026-09-05）

- PostgreSQL全体で失敗した一覧/詳細比較は、participantsとparticipants_detailがDB取得順のまま返るため、prefetchの有無で順序が変わるケースだった。逆順のprefetchを渡す回帰テストを追加し、SQLiteでも両フィールドのID順判定が失敗した。`tmp/participant-order-red.log`（2 subtests失敗）。
- serializerで参加者を主キー順に並べ、両フィールドから同じ処理を使う。prefetch済みデータを再利用し、取得済みキャッシュを変更しない。participants側のキャラクター詳細展開とparticipants_detail側の元の形式を維持し、後者のOpenAPI定義も元の参加者serializerの配列として明示した。
- 0ea0e747固定依存イメージへ変更serializer/テストを読み取り専用適用し、一覧・詳細の一致、owner/manager/gm別の秘匿HO、ユーザー/ゲスト/キャラクター付き参加者、件数増加に対するクエリ数の検証を実行。PostgreSQLは4件・10 subtests成功（31.08秒）、SQLiteも4件・10 subtests成功（17.72秒）。`tmp/participant-order-postgres.log` / `tmp/participant-order-sqlite.log`、`tmp/formal-release-0ea0e747-full-output/participant-order-junit.xml` / `participant-order-coverage.json`。
- Black/isort/flake8、差分を確認し、専用DBコンテナとネットワークを削除した。前回PostgreSQL全体の失敗は原因別の関連テストで修正確認できたが、修正群をまとめた全体成功はまだ証明していない。実環境の変更なし。

## 継続監査: 9b1c9043の静的検査・移行・API定義（2026-09-05）

- 修正群を含む `9b1c9043` のgit archiveから固定依存テストイメージを作成した。タグ `tableno-formal-release-test:9b1c9043-browser`、ローカルID `sha256:6789e8d1a91d8de85a7d131e98237902f40ea518c1847a9368e42555efca86be`。配備用イメージ/ECR digestとは別である。
- 同イメージで、CIと同じリポジトリ全体の `flake8 .`、`black --check .`、`isort --check-only .` がすべて終了コード0。設定された除外・対象ルールを使用し、自動整形なし。`tmp/formal-release-9b1c9043-output/quality.json` と各検査ログ。
- ネットワークなしの別コンテナで `manage.py check`、`makemigrations --check --dry-run`、専用SQLiteへの `migrate --noinput` と `migrate --check`、`pip check` が成功した。`checks.json` と各検査ログ。移行差分はなく、実データや共有DBへは適用していない。
- `manage.py spectacular --validate --file /proof/schema.yml` が終了コード0。生成されたTRPGSession/PatchedTRPGSessionのparticipants_detailはreadOnly=true、type=array、itemsがSessionParticipantへの参照であることを確認した。APIでの並び順変更に伴い、要素の型を失っていない。`schema.yml` / `schema.log`。
- 同コンテナの `pytest tests/system -q -rs` は12件成功（31.48秒、警告11件、終了コード0）。`system.log` / `system-junit.xml`。SQLite/PostgreSQLのUnit / Integration全体は別実行で継続中。以上をリモートCI、本番設定、実サービスの成功として扱わない。
