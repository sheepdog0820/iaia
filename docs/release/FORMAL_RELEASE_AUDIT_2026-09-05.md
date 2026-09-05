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

## 継続監査: 9b1c9043の静的セキュリティ検査・非公開画像（2026-09-05）

- 同じ固定イメージをネットワークなしで起動し、Banditをaccounts/schedules/scenarios/support/tableno/apiへ実行した。HIGH 0件、MEDIUM 0件、LOW 532件、解析エラー0件、終了コード1。`tmp/formal-release-9b1c9043-output/bandit.json`。LOW指摘の安全性判定が済んだという意味ではない。
- 専用SQLiteと一時MEDIA_ROOTに8×8の試験PNGを作成し、非公開Scenario/Sessionへ1枚ずつ登録した。所有者、無関係な通常ユーザー、未ログインのDjango Clientで親APIと画像URLをGETした。所有者は両方200。無関係なユーザーは親404、未ログインは親401だったが、画像は両者とも200で保存した全バイトと一致した。画像レスポンスのCache-Controlは未設定だった。
- 証跡は同ディレクトリの `probe-private-images.py`、`private-image-probe.json`、`private-image-probe.log`。APP_ENV=local、DEBUG=True、ALLOWED_HOSTSにtestserverのみ追加、外部ネットワークなし、実サービス認証情報なし。初回はtestserver未許可の400となりアクセス制御の検証にならなかったため、試験ホスト設定を修正して上記の成功/拒否を確認した。試験用DB/画像は終了時に破棄した。実利用者の画像やAWSオブジェクト内容は取得していない。
- 原因として `tableno/media_views.py` はhandouts/だけを認可処理へ分岐させ、その他はDEBUG時に通常の静的配信へ渡している。ScenarioImage/SessionImageのserializerとHTMLにもstorageのimage.urlを直接返す箇所がある。ローカル経由だけを保護しても、本番のS3/CloudFront直URLに対する迂回防止の証明にはならない。
- 対策は未実装。公開シナリオの公開ページ、セッション閲覧者、非公開化や所属解除の反映を維持しつつ、画像取得時の認可、serializer/HTMLの配信URL、旧URLとストレージ/CDN側を一体で確認する必要がある。既存のcan_view_scenarioは所有者/共通グループを扱い、公開ページのvisibility=publicとは別の経路であるため、単に同関数だけを全画像へ適用して公開機能を壊さない。AWSの画像露出は今回未検証であり、ローカル再現と区別する。Q04は未達、正式公開はNo-Goを維持する。

## 継続監査: 9b1c9043のSQLite/PostgreSQL全体検証（2026-09-05）

- 固定テストイメージの9b1c9043で、accounts/api/scenarios/schedules/support/tableno/tests/unit/tests/integrationを同じpytest・カバレッジ設定で実行した。SQLiteは1,538件成功、3件skip、343 subtests成功、1,205.68秒、86.35%、終了コード0。PostgreSQL 16.15は1,541件成功、skipなし、343 subtests成功、1,232.37秒、86.57%、終了コード0。
- JUnitも両DBでfailures=0/errors=0。tests=1,884はsubtestsとskipを含む。SQLiteのskipは参加承認の2件と報酬反映の1件で、has_select_for_updateが必要な実DB並行試験である。同じ3件はPostgreSQLで実行・成功しており、除外して失敗を消したものではない。警告は双方159件。
- `tmp/formal-release-9b1c9043-output/{sqlite,postgres}-run.log`、同じ接頭辞のjunit.xml/coverage.xml/coverage.jsonを確認した。両実行の終了を確認後、専用PostgreSQLコンテナとネットワークを停止・削除した。実RDSや共有DBの変更なし。
- 以前のPostgreSQL全体で発生したロック・ID・参加者順序の不一致は、この単一ソースの全体検証でも解消した。一方、この結果は後続の画像配信修正、配備用イメージ、本番設定全体、リモートCI、実サービス検証を含まない。正式公開の残条件は維持する。

## 継続監査: セッション画像の認可付き配信（2026-09-05）

- セッション画像に `GET /api/schedules/session-images/{id}/content/` を追加した。取得の都度、セッション詳細と同じcan_view_session_basicで閲覧権限を確認する。非公開データの拒否・存在しない画像・保存ファイル欠損は404。公開セッションは同関数の既存仕様に従って匿名でも取得でき、非公開化で同じURLが拒否される。
- serializerのimage/image_urlとセッション詳細HTMLをcontent_urlへ変更し、serializerはstorage.urlを呼ばない。アップロードはImageFieldの検証、モデルにあるファイル名長と説明を維持した。旧MEDIA_URL配下のsession_images/も、正規化後に同じ認可へ分岐する。DEBUG=Falseでもアプリ経由は保護付き配信が可能。S3/CloudFrontへの直アクセスはこの処理を通らないため、別途封鎖が必要である。
- レスポンスはno-store、Vary: Cookie/Authorization、nosniffを持つ。PNG/JPEG/GIF/WebP以外の保存データはoctet-stream添付として扱い、HTML等を画像配信経路で実行させない。既存の画像バイトは変更していない。OpenAPIには各画像MIMEとバイナリ応答を追加し、spectacular --validateは成功。`tmp/session-image-schema.log` と `tmp/formal-release-9b1c9043-output/session-image-schema.yml` の新規パスを確認した。
- 回帰テストを先に追加し、旧実装では新URLの不存在、旧URLの未認可配信、serializerのstorage.url呼び出しで失敗した。`tmp/session-image-red.log`。Cookie/Token認証、非公開・公開、参加解除・グループ脱退、DEBUG両設定、正規化経路、ファイル欠損、不明形式、API/HTMLのURLを試験した。HTML試験は最初に役割のない参加レコードを作っていたため画像欄が表示されず失敗し、通常のcreate_participantでPLを作成するよう試験データを修正した。
- 最終SQLiteは新規14件と既存画像13件の計27件・9 subtests成功（51.43秒、警告9件）。`tmp/session-image-final.log`、同出力ディレクトリのsession-image-final.xml/coverage.json。画像取得view、専用serializerフィールド、content_urlの実行対象行に未実行行なし。PostgreSQL 16.15では、新規13件・既存画像・ハンドアウト添付・セッション可視性を合わせ51件・9 subtests成功（63.25秒、警告9件）。`tmp/session-image-postgres.log`、session-image-postgres.xml/coverage.json。PostgreSQL実行後の変更はOpenAPIへの掲載を伴うGenericAPIView化とファイル名長検証の明示で、最終SQLiteに含めて確認した。
- 固定9b1c9043イメージに変更ファイルを読み取り専用適用し、専用DB/試験画像だけを使用した。専用PostgreSQLは外部公開ポートなし、検証後に停止・ネットワーク削除済み。Black/isort/flake8と差分を確認した。画像URLだけのHTML変更で、表示文言・レイアウトは変更していない。シナリオ画像、S3/CloudFrontの直配信、実環境の配備は未完了であり、正式公開No-Goを維持する。

## 継続監査: シナリオ画像の通常・セッション経由配信（2026-09-05）

- `GET /api/scenarios/scenario-images/{id}/content/` を追加し、公開シナリオ、所有者、既存の共通グループ閲覧条件を満たす利用者だけへ配信する。旧MEDIA_URLのscenario_images/も正規化後に同じ認可を通す。serializerのimage/image_url、公開ページのimg/og:imageをアプリURLへ変更し、storage.urlを呼ばず、ファイル名長・画像アップロード検証を維持した。
- セッション詳細は以前から関連シナリオの画像を表示していたため、その経路を別URL `GET /api/scenarios/scenario-images/{id}/sessions/{session_pk}/content/` で維持した。画像のシナリオとセッションの関連が一致し、ログイン済みで既存のcan_view_session_basicを満たす場合だけ配信する。無関係なセッションIDや匿名の公開セッションIDを使って非公開画像を取得できない。公開シナリオそのものの匿名表示は通常URLで維持する。
- 都度認可、no-store、Vary: Cookie/Authorization、nosniff、既知の画像形式以外はoctet-stream添付とした。元画像バイトは変更しない。非公開化、グループ脱退、セッション参加解除、欠損ファイル・レコード、空ファイル、不明形式、正規化パス、serializerとHTMLのURLを新規11テストで確認した。先に旧実装で失敗することを確認した証跡は `tmp/scenario-image-red.log`。
- 固定9b1c9043イメージに既存セッション画像修正と今回の変更ファイルを読み取り専用適用した。最終SQLiteは新規シナリオ画像・既存シナリオ画像・セッション画像・ハンドアウト添付の69件と18 subtests成功（72.34秒）。PostgreSQL 16.15も同じ69件と18 subtests成功（48.79秒）。双方警告9件、終了コード0。`tmp/scenario-image-{sqlite,postgres}.log`、`tmp/formal-release-9b1c9043-output/scenario-image-{sqlite,postgres}.xml` と同接頭辞のcoverage.json。配信viewは38/38行、専用serializerフィールドとcontent_urlも実行対象行100%。全分岐・全アプリ100%という意味ではない。
- PostgreSQL初回は66件成功・3件失敗。直前の不明形式テストがresponse.close()を直接呼び、Djangoのrequest_finished経由でTestCaseのDB接続を閉じていた。Django test.clientのclosing_iterator_wrapperはclose_old_connectionsを切り離して終了するため、両画像テストをstreaming_contentの全バイト検証へ変更した。取得の判定は弱めず、後続テストの接続終了も解消した。初回失敗は `tmp/scenario-image-postgres-before-stream-fix.log` と同名XMLで保持した。
- OpenAPIは通常・セッション経由の両パス、整数ID、画像のバイナリ応答を生成し、spectacular --validateが成功。`tmp/scenario-image-schema.log` / `tmp/formal-release-9b1c9043-output/scenario-image-schema.yml`。Black/isort/flake8、差分、HTMLの既存日本語文言を確認した。表示URLの変更で、画面配置の変更はない。
- 専用PostgreSQL・ネットワークは試験終了後に停止・削除した。実データ・AWS変更なし。既存のTerraformと応急ポリシーはhandouts/だけを対象にするため、両画像の保存先を含めて拡張・検証する必要がある。配備準備資料に、古い候補を最終digest扱いしないことと、画像を含む配信保護の実行要件を追記した。実環境の迂回防止は未適用であり、Q04/正式公開No-Goは維持する。

## 継続監査: 画像を含むCloudFront経由の配信拒否案（2026-09-05）

- AWS profile tableno-preでバケットポリシー、Public Access Block、CloudFront distribution設定を再読した。ポリシーは対象CloudFrontから全keyへのAllowだけで、保護用Denyはまだない。Public Access Blockは4項目true、distributionはS3 OACを使用し、追加behavior・署名制限・エッジ関数なし、TTLはmin/default/maxとも0。オブジェクト内容・Secretsは取得していない。
- `infrastructure/terraform/main.tf` のassets bucket policyにsession_images/とscenario_images/の直下・任意location下を追加した。既存handouts/と合わせ6 resourceパターンを対象CloudFront principal/SourceArnのGetObjectに限定して拒否する。アプリのtask role、静的ファイルのAllow、DBやECS構成は変更していない。
- 再取得したポリシーからAllowを保持する具体案を `tmp/private-media-containment-34846799/proposed-policy.json` へ作成した。before-policy.jsonのSHA256は04b660fe783b9966262cfba2a9373cf6c3dd2ede5f2b349d3f0d7b2d589453ab、案は2ba55b16611afe7654da2f831dd65bde1eaaeb9247d8863a4bcc1ab63bb53db0。AWS Access AnalyzerのS3 resource policy検査はfindings=[]。Terraform 1.15.6のfmt -check / validateも終了コード0。validation-summary.jsonに観測・検査結果を記録した。
- plan/apply、バケットポリシー変更、invalidation、配備、試験画像の作成は未実施。静的検査は実際の拒否やキャッシュ失効の証拠ではない。旧アプリが直URLを返すため、拒否先行時の表示停止を含む適用順序と切り戻し制限を配備準備資料へ追記した。最新候補digest・実効storage location・実行直前の状態・試験データ・費用を揃えて承認を得る必要がある。正式公開No-Goを維持する。

## 継続監査: セッションの権限拒否画面（2026-09-05）

- セッション詳細・日程調整のHTML権限拒否は、APIView内でPermissionDeniedを送出するとDRFの開発者向け画面になっていた。先に両画面のテンプレート、日本語案内、非公開の題名/説明が出ないこと、JSON応答の契約を回帰テストにし、旧実装ではHTMLの2 subtestsが失敗した。`tmp/permission-page-red.log`。
- HTMLの拒否は共通403.htmlをstatus=403でrenderするよう変更した。既存のJSON 403 / {error: Permission denied}と閲覧許可条件は変更していない。回帰テストと既存のセッション可視性は10件・4 subtests成功（25.68秒、警告9件）。`tmp/permission-page-green.log`。
- 固定9b1c9043の専用コンテナへ変更viewを読み取り専用適用し、ブラウザから通常の登録・非公開グループ作成・セッション作成・完了への更新を実行した。独立した通常ユーザーはグループ/セッションAPIが404、詳細/日程調整HTMLが403となり、アプリの案内とホームへの導線を表示し、非公開題名を表示しない。API作成や強制認証で画面操作を置き換えていない。
- 初回の3ブラウザ成功後、WebKitの390px画像で共通403画面の戻るボタンだけが右へずれていることを確認し、ms-2をms-sm-2へ変更した。テンプレート差し替えだけでは古い表示が保持されたため専用サーバーを再起動し、ボタンの左右位置/幅の差が1px未満であることもE2Eで確認した。最終Chromium/Firefox/WebKitは3件成功（40.6秒、終了コード0）。`tmp/permission-page-browser.log`、`tmp/formal-release-permission-page.json` と同名resultsディレクトリのPC/モバイル画像。実機の検証ではない。
- ローカル専用DBに各ブラウザの試験利用者が計18人、staff/superuserはともに0人であることを確認した。コンソールメール設定を使用し、実通知・共有DB変更なし。専用コンテナは終了後に停止・削除した。Black/isort/flake8、日本語画面の実表示、差分を確認した。有料契約・外部連携・配信設定の実環境検証等は別の未完了条件として維持する。

## 継続監査: 6608de6dの配備イメージ固定と起動（2026-09-05）

- 画像保護・403画面を含む6608de6dのgit archiveから配備用Dockerfileでビルドした。ローカルイメージIDはsha256:6a7ec1bd4450cf9bd736d49a86ef4905aecee2b7a74c4252c344196ad376e77d、revisionラベルは6608de6d6e6d0dd3dbf854bd27a3dc07047a3d02。ECR未送信、RepoDigestsは空。詳細・証跡の場所は配備準備資料の同候補節に記録した。
- 外部通信・公開ポートなしの専用PostgreSQL/Redisと、aws-pre/stagingの本番系設定で通常entrypointを起動。migrate、179ファイルのcollectstatic、Daphne起動、UID 10001を確認した。pip check、check --deploy、migration差分/未適用確認はすべて成功。HTTPSプロキシヘッダーを模擬したreadyは200、DB/cacheともok。
- S3は無効、課金は無効、Stripeキー・事業者表示は隔離試験専用の値。実TLS、実AWS Secrets、実S3、販売条件、課金・外部連携の正常性は証明していない。専用コンテナとネットワークは検証後に削除した。同SHAの全体CIや実配備検証等は残るため、正式公開No-Goを維持する。

## 継続監査: 最終候補の全体再検証開始・ソーシャル連携の確認フラグ（2026-09-05）

- 6608de6dのgit archiveで固定依存のブラウザ付きテストイメージを作成し、SQLite/PostgreSQLの全体pytestを開始した。出力は `tmp/formal-release-6608de6d-full-output/`、実行handle・専用コンテナ名はexecution-context.json。実行中のhandleを確認しており、完了結果はまだない。このファイルだけを生存証拠にはしない。今回の後続アダプター修正は6608de6dの全体実行に含まれない。
- Stripe接続を再確認したが、UNAUTHORIZED / oauth_token_invalid_grantで再認証要求が続いている。アカウント一覧も取得できず、実Stripeイベントや課金操作は行っていない。
- `CustomSocialAccountAdapter.pre_social_login` はGoogleなら確認フラグに関係なく同じemailの既存利用者へconnectしていた。またDiscordの文字列falseを真扱いし、既存socialloginにも再連携を実行できた。先に新規テストで、Googleの未確認/欠落/非boolean、Discordの非boolean、既存連携のケースが旧実装で失敗することを確認した。`tmp/social-link-red.log`。
- 既存socialloginは早期returnとし、新規Googleはemail_verified（なければverified_email）、DiscordはverifiedがbooleanのTrueの場合だけ自動連携するよう変更した。確認済みの正常系、該当利用者なし、未対応providerも確認した。新規5件と既存Google/Discord API・認証テストを合わせ50件・15 subtests成功（39.72秒、警告9件）。`tmp/social-link-green.log`。connectはモックで呼出条件を検証しており、実OAuthの成功や実際のアカウント連携全体を証明するものではない。
- [allauthの設定説明](https://docs.allauth.org/en/latest/socialaccount/configuration.html)は、信頼するproviderの確認済みメールによる認証/自動連携を扱う。ローカルのGoogle provider実装もemail_verified/verified_emailを抽出している。一方、[Googleの説明](https://developers.google.com/identity/sign-in/android/backend-auth?hl=en)では、Gmail以外かつhdなしの場合はemail_verified=Trueでも現在の第三者メール所有権を保証できないとしている。今回の確認フラグ修正だけではこの条件を解消しない。ブラウザ/API両経路のメール自動連携に追加の所有権確認をどう適用するか、既存provider UIDとの紐付け維持も含めて次の監査・修正対象とする。
- Black/isort/flake8と差分を確認した。アプリの既存画面文言は変更していない。実認可・外部通知・共有データ変更なし。公開条件I01/I03/Q04は未達として維持する。

## 継続監査: Google APIの固定ID無視とメールによる誤認証（2026-09-05）

- google_authのIDトークン・認証コード・userinfo処理を読んだところ、Googleのsub/idをユーザー選択へ渡さず、email一致だけでローカル利用者とDRFトークンを返していた。既存SocialAccountのGoogle UIDも照合しない。
- 専用SQLite、外部通信なし、Google検証関数だけを模擬した2試験で再現した。未連携の別Google ID/第三者メールの一致は期待する拒否ではなく200。同じGoogle UIDのメール変更ケースは元利用者ID=1でなく別利用者ID=2を返した。`tmp/test_google_identity_probe.py` / `tmp/google-identity-probe.log`。2件失敗、18.27秒。実トークンや実利用者への試験ではない。
- [修正条件](GOOGLE_IDENTITY_REMEDIATION.md)に、固定ID優先、第三者メールの追加確認と利用者導線、3 API方式とブラウザの一貫性、競合・無効利用者・機密保護の条件をまとめた。今回のターンではこの問題の実装修正はまだない。確認フラグ修正や全体テストの成功で解消扱いにせず、I01/Q04を公開阻害事項として維持する。

## 継続監査: 6608de6d全体結果とGoogle固定ID修正

- 6608de6dの全体実行が両DBで終了した。SQLiteは1,565 passed / 3 skipped / 359 subtests、86.54%、1,172.44秒。PostgreSQLは1,568 passed / skipなし / 359 subtests、86.75%、1,199.86秒。JUnitは双方1,927件、failures/errorsとも0。tmp/formal-release-6608de6d-full-output/ のログ・JUnit・coverageを確認した。この後のGoogle認証変更は含まれない。
- Google APIの固定ID保持と優先照合、第三者メールの追加確認、認証後の明示的連携、原子的な作成と競合再試行、対象クライアントとuserinfoの照合を実装。ブラウザの一律確認済み指定と連携ボタンも修正した。詳細・検証限界・復旧の注意は [Google修正記録](GOOGLE_IDENTITY_REMEDIATION.md) に記録した。
- 認証関連の最終実行はSQLite83件成功+1skip、PostgreSQL84件成功、双方28 subtests。Googleの新規resolverは76/76実行行をカバー。実OAuthや実通知は行わず、共有環境・実データ・Secrets・費用への変更なし。I01/Q04と正式公開No-Goは継続する。

## 継続監査: ブラウザ登録途中の競合による部分保存

- 前回はGoogle固定ID修正・pushと実行結果があり、進捗あり。現在のca90f687と差分なしを確認して追加監査を開始した。
- ブラウザ登録でSocialAccount保存失敗後に利用者だけ残ることを隔離テストで再現。アダプターの登録保存を原子的にし、IntegrityError時は全体を取り消して再ログインを案内する修正を実施した。
- PostgreSQLの実2接続による同時初回登録・再試行を含む認証関連86件と28 subtestsが成功。範囲と証跡は[Google修正記録](GOOGLE_IDENTITY_REMEDIATION.md)を参照。実サービスの検証と全体候補の確認は未完了、正式公開No-Goを維持する。

## 継続監査: 認証エラーのログと応答への情報露出

- b56a3198で作業差分がないことを確認し、全体SQLite/PostgreSQLの既存handle 46678/10387を再確認した。両実行は稼働中で、今回のログ修正はその対象外。全体実行を再起動していない。
- CustomSocialAccountAdapterのエラー記録は、state、未知のGETパラメーター、Cookie/セッションキーの末尾、例外本文/tracebackを含んでいた。模擬の認証情報を入れた2テストが旧実装で失敗した（tmp/auth-error-logging-red.log）。連携先をgoogle/discord/twitter_oauth2、エラー分類をunknown/cancelled/deniedに制限し、例外型だけを記録するよう修正した。要求ヘッダー・パラメーター・Cookie・例外本文は読んでログに渡さない。
- X/Discord APIも外部エラー応答の本文と内部例外本文をログに出し、500応答のdetailに例外本文を含めていた。両providerのトークン交換・利用者取得・内部例外の6 subtestsで再現（tmp/provider-error-logging-red.log）。HTTPステータス/例外型に記録を限定し、利用者には既存の日本語errorのみを返すよう修正した。
- b56a3198の固定テストイメージへ変更ファイルを読み取り専用で載せた隔離SQLiteで、認証ログ・ブラウザGoogle・Google/X/Discord API・連携判定の46件、24 subtests成功、9件の既存警告。tmp/provider-error-logging-green.log / tmp/auth-error-logging-coverage.json。新しいon_authentication_errorの実行行はすべてカバーした。DB変更を含まないためこの変更のPostgreSQL再実行は行っていない。
- 実OAuth、実ログの内容調査、過去ログの削除、実ユーザー/共有環境への変更は行っていない。過去の実ログに認証情報が記録されていたかは未確認。今回の対象はアプリの認証エラー処理であり、基盤のアクセスログやサービス全体の秘匿情報監査の完了を示すものではない。Q04は引き続き未達。

## 継続監査: X・Discord APIの停止済み利用者の拒否

- 2fca981dと差分なしを確認して開始。全体テストの既存handle 46678/10387を再確認し、稼働継続を確認した。今回の修正はb56a3198の全体実行には含まれない。
- X/Discord APIは既存SocialAccountの利用者がis_active=Falseでもトークンを発行/返却していた。Discordは確認済みメール照合で見つかった停止済み利用者へも新規連携を作成した。認証済み利用者の連携経路にも同じチェックがなかった。
- 隔離fixtureの初回実行ではXのredirect_uri指定不足で400となったため、設定を補ったうえで旧版イメージへ再実行した。最終の再現では、両providerの既存ID・認証済み連携・既存トークンとDiscordメール照合の7ケースがすべて期待403に対して200となった（tmp/oauth-inactive-confirmed-red.log）。実OAuth・実利用者への試験ではない。
- 各経路で既存利用者を選択した直後、連携情報更新・メール確認・トークン発行より前にis_activeを確認する共通処理を追加。停止済みなら日本語のPermissionDeniedをDRFへ渡して403にする。一般エラーとして500に変換しない。
- 新規トークンなし、既存トークンを応答に含めない、既存連携のextra_dataを変更しない、メール確認/新規連携を作成しないことを検証。Google/X/Discordの既存APIテストを含むSQLite30件と12 subtests成功（38.98秒、既存警告9件）。新規拒否処理の実行行に未カバーなし。tmp/oauth-inactive-final.log / tmp/oauth-inactive-coverage.json。
- Black/isort/flake8、差分、UTF-8/LF、日本語エラーを確認。DBスキーマ、共有/本番データ、外部設定・権限・費用に変更なし。既存トークンの削除は行わず、停止状態では取得を拒否する。復旧はこのコード変更のrevertが可能だが、旧版の拒否漏れを再導入する。I02/I03と正式公開判定は実サービス検証が未完了のため未達を維持する。

## 継続監査: Discordメール確認フラグと変更後のメール

- 793c3063と差分なしから開始。Discord APIのbool(verified)は文字列false/trueや数値1も確認済みと扱っていた。また既存Discord UIDの現在メールがローカル登録メールと異なる場合も新しいメールをprimary=Trueで追加し、既存primaryとの制約違反で500となった。隔離再現は4失敗（1テスト+3 subtests）、tmp/discord-email-safety-red.log。
- 判定をverified is Trueに限定した。既存UIDのメールがローカル利用者と異なる場合はメール確認状態を変更せず、同じ利用者で認証を続ける。同じメールの大小文字だけが変わった場合も重複追加で失敗することを追加再現（tmp/discord-email-case-red.log）し、比較はcasefold、保存時の照合にはローカルの表記を使うよう修正した。
- SQLiteでGoogle/X/Discord APIと停止済み利用者の回帰テスト33件・17 subtests成功（37.34秒、既存警告9件）。tmp/discord-email-safety-final.log / tmp/discord-email-safety-coverage.json。未確認Discord IDの新規登録時にローカルメールを空として扱う既存動作は維持し、他人の既存メールへ連携・確認・トークン発行を行わないことを検証した。
- 実provider応答・実利用者・共有DB・OAuth設定への操作は行っていない。DBスキーマ/費用への変更なし。コードrevertは可能だが、メール誤照合とログイン失敗を再導入するため公開判断を伴う。実Discord認可・取消・失効は未確認で、I02/Q04は未達を維持する。

追加で専用PostgreSQL 16のDiscord API・停止済み利用者14件と11 subtestsも成功（19.93秒、警告9件、tmp/discord-email-safety-postgres.log）。この専用DB/ネットワークは終了・削除した。

b56a3198全体実行はSQLite1,596成功・5skip・2失敗、PostgreSQL1,601成功・2失敗、双方384 subtests成功で終了した。両失敗はGoogleUserInfoResilienceTestsで、必須クライアント設定なしのため通信試験に入らず503となる。テスト前提と、新しく追加したtokeninfo→userinfoの両通信を検証するfixtureの更新が必要。全体成功や最終候補合格とは扱わない。


全体実行で失敗したGoogle通信耐性テストを更新した。テスト専用クライアントIDを設定し、実際のtokeninfo→userinfoの2段階を模擬して各呼出の10秒timeoutを確認する。両段階それぞれのTimeoutで503と機密情報を含まない日本語応答・ログを検証する。YouTube既存2件も含む4件・2 subtests成功、0.70秒（tmp/google-http-resilience-final.log）。認証の設定チェックを緩めてテストを通したものではなく、設定済み環境の通信障害を検証する前提と範囲を修正した。修正後の候補全体テストは未実施であり、b56a3198の2失敗を後から全体成功に書き換えない。

## 継続検証: 58a27172の配備用イメージと通常起動

- 58a2717282bc9e5a21894097ad883dde89bf1e49のgit archiveを使用し、リポジトリのDockerfile/requirements.lock.txtでビルド成功。イメージtableno-formal-release:58a27172、ID sha256:8993fb43f519f89f7d9aad564480eeb6ea3a31d32383cc65e34396d9011861aa。revisionラベルは上記SHA。テスト依存を追加した全体テスト用イメージとは別物であり、ECRへpushしていない。
- 実データ・外部通信から隔離したinternal Dockerネットワーク、専用PostgreSQL 16/Redis 7、ホスト公開ポートなしで実行した。通常entrypointのRUN_MIGRATIONS/RUN_COLLECTSTATICを有効にし、migrate完了、179 static files収集、Daphne起動を確認。非root UID 10001、DEBUG=False、django.db.backends.postgresql。作成したアプリ/DB/Redisコンテナとネットワークは検証終了後に削除した。全体テストの別コンテナは稼働継続。
- pip check成功、check --deployは指摘0、makemigrations --check --dry-runは変更なし、migrate --check成功。コンテナ内curlで/health/ready/が200、database/cacheともok。X-Frame-Options DENY、nosniff、HSTSも確認。リバースプロキシのHTTPSヘッダーを模擬したHTTP通信であり、実TLS/ALBの実証ではない。
- 設定はテストコード内の架空の事業者表示等を元に新規生成した。APP_ENV=aws-pre/ENVIRONMENT=staging、S3無効、決済無効、実OAuth/実Stripe鍵なし。実利用者向け料金・規約の承認や、実サービスの稼働を示さない。tmp/candidate-58a27172.envはこの隔離実行専用で、配備へ流用しない。
- 証跡: tmp/formal-release-58a27172-production-build.log、tmp/candidate-58a27172-startup.log、tmp/candidate-58a27172-deploy-check.log、tmp/candidate-58a27172-migration-diff.log、tmp/candidate-58a27172-ready.log。候補全体のBlack/isort/flake8は別途成功。SQLite/PostgreSQL全体実行handle 4850/92058は稼働中で、完了結果は未取得。正式公開判定は未達を維持する。

## 継続監査: X・Discord APIの登録保存と競合

- 7bd33193と差分なしを確認し、58a27172の既存全体実行handle 4850/92058を確認した。稼働中の同じ実行を継続し、今回の変更はその対象に含めていない。
- X/Discord APIのトークン保存にIntegrityErrorを模擬すると、利用者・連携・メール確認や既存プロフィールの変更が途中まで残ることを検証した。旧実装で4 subtests失敗（tmp/oauth-atomicity-red.log）。
- 各APIの外部通信が完了した後のDB処理をtransaction.atomicにまとめた。一般エラー・停止済み利用者の拒否・保存競合で処理が例外終了した場合はDB変更を取り消す。IntegrityErrorには機密情報を含まない日本語の再ログイン案内と503を返す。正常応答のtoken/user/created/linkedは維持する。
- SQLiteの認証関連22件・15 subtests成功（20.85秒）。PostgreSQL 16ではAPIClientと独立した2接続による同時X登録・同時Discord登録を追加し24件・15 subtests成功（39.49秒）。競合側503・成功側200となり、利用者/連携/トークン各1件、再試行では同じ利用者とトークンが返ることを確認した。Discordの確認済みメールは1件、メールを提供しないXは0件という既存動作を確認。
- 証跡: tmp/oauth-atomicity-green.log、tmp/oauth-atomicity-postgres.log、tmp/oauth-atomicity-postgres-coverage.json。Google等の実サービス通信は行っていない。DBスキーマ・実利用者・共有環境・権限・費用への変更なし。Black/isort/flake8と差分・日本語エラーを確認した。復旧はアプリ変更のrevertで可能だが、部分保存の問題を再導入する。候補全体・実認可・取消/失効の検証は未完了で、正式公開判定は未達を維持する。

## 継続監査: 外部接続と静的指摘の分類

- 494abd0dと差分なしを確認。Stripeアカウント一覧を再取得したがUNAUTHORIZED/oauth_token_invalid_grantで再認証が必要だった。GitHub CLIは未ログイン。実課金・認可・公開操作は行っていない。未回答の料金・有料範囲を承認と扱っていない。
- 現在の6アプリにBanditを再適用。エラー0、HIGH/MEDIUM 0、LOW557、終了コード1。テスト475件、ローカル開発用コマンド71件、その他11件に分類し、[詳細と残作業](SECURITY_STATIC_TRIAGE_494ABD0D.md)を作成した。実行コード側の定数名等4件とゲーム乱数2件は用途から分類、例外処理5件は追加監査が必要。
- 開発コマンド7個×共有/不正設定8種類の境界テスト56 subtests成功。DB操作前に拒否することをSimpleTestCaseで確認した。過去の指摘件数とは走査範囲/対象コミットが異なるため、単純な増減を安全性の指標にしない。全体テストは既存handleを追跡中で、Q04と正式公開No-Goを維持する。

## 継続監査: 技能一括保存の部分失敗と58a27172全体結果

- 6a08e963と差分なしから開始。CharacterSkillViewSet.bulk_updateは、新規技能の作成例外と存在しない技能IDを無視し、先行する更新/作成だけを保存して200を返していた。6版/7版とも、後続の負値技能と不明IDで4 subtestsの失敗を再現した（tmp/skill-bulk-red.log）。
- 一括保存をtransaction.atomicで囲み、対象キャラクターを所有者で照合してロックする。入力は非空の配列と各技能オブジェクトを要求し、不正値・不明/他人の技能ID・空の新規技能名は400、他人/不明キャラクターは404。既存モデルの技能検証を維持する。400応答は日本語errorと1始まりのitemを含み、変更を保存しない。正常時は従来どおり更新技能+作成技能の配列を返す。
- DB競合/接続障害は503、予期しない例外は500とし、例外本文をログや応答へ含めない。いずれも先行する保存を取り消す。SQLiteは22件・20 subtests成功（38.72秒）、PostgreSQLは親ID未指定の直接呼出テスト追加前の21件・20 subtests成功（24.00秒）。6版/7版の正常作成/更新・部分失敗・外部ID拒否・障害時の巻戻しを確認。bulk_updateに未実行行なし。分岐網羅や同時編集の証明ではない。
- 証跡: tmp/skill-bulk-verified.log、tmp/skill-bulk-postgres.log、tmp/skill-bulk-final-coverage.json。既存の技能ポイント検証は変更せず、複数技能間のポイント再配分順序・他の更新経路との同時編集は追加検証として残す。DBスキーマ・実データ・共有環境・費用変更なし。専用DB/ネットワークは削除済み。コードrevertは可能だが旧版の部分成功を再導入する。
- 並行して追跡していた58a27172全体実行が終了した。SQLite1,611成功・5skip・403 subtests、カバレッジ86.81%、1,254.57秒。PostgreSQL1,616成功・skipなし・403 subtests、87.17%、1,289.01秒。JUnitは双方2,019件、failures/errors 0。実行対象は固定58a27172であり、後続のX/Discord保存処理・今回の技能修正を含まない。全体用の専用DB/ネットワークも終了・削除済み。最終候補の再検証とリモートCI・実サービス検証は残り、正式公開No-Goは維持する。

## 継続検証: 技能ポイント再配分の順序依存

- 03c53fc5から開始。最初の再配分テストは能力値未設定による0ポイントの交換だったため成功しており、再配分の証拠にならなかった。EDU/INTを明示し、上限が正であることも検査すると6版/7版の双方で400応答となり2 subtests失敗を再現した（tmp/skill-budget-nonzero-red.log）。前段の0ポイント成功を不具合なしの根拠として扱わない。
- 所有者確認・親ロック・全件トランザクションを維持し、入力と対象IDを先に検査する。対象技能の職業/趣味ポイントだけをトランザクション内で0にしてから、元の値を保持したモデルへPATCHを適用して保存する。これにより後続技能が解放するポイントを先行する更新/新規技能へ配分できる。省略フィールドは保持し、通常のモデル検証で未編集技能を含む上限超過を拒否する。失敗時は一時的な0への更新も含めて巻き戻す。
- SQLite関連45件・28 subtests成功（32.17秒、tmp/skill-budget-related.log）。PostgreSQL 16も関連45件・28 subtests成功（22.19秒、tmp/skill-budget-postgres-accounts.log）。再配分・新規作成先行・職業/趣味の最終合計超過・省略フィールド・重複IDの逐次PATCH・従来の部分失敗巻戻しを検証。最後に重複した新規技能名検査を整理した変更はPostgreSQLの最終実行に含む。
- 特定ビューだけを--cov対象にしたPostgreSQL実行はDB接続が閉じるエラーで失敗（tmp/skill-budget-postgres.log、tmp/skill-budget-postgres-final.log）。計測なしでは成功し、既存の全体検証と同じ--cov=accountsでは成功した。計測範囲に伴う失敗の根本原因は未確定で、失敗結果は保持する。最終計測tmp/skill-budget-accounts-coverage.jsonでbulk_updateに未実行行なし。分岐網羅・他の更新経路との同時編集の証明ではない。
- Black/isort/flake8成功、差分と日本語応答を確認。共有環境・実データ・DBスキーマ・権限・費用の変更なし。専用PostgreSQLとinternalネットワークは削除済み。復旧は当該アプリ変更のrevertで可能だが再配分の不具合が戻る。最終候補全体/CI/実連携/公開運用の検証は未完了で、正式公開No-Goを維持する。

## 継続監査: パスワードログインのDB照合障害

- 824857b4と差分なしから開始。CustomLoginFormはEmailAddress照合の例外を無視してCustomUser照合へ進んでいた。またCustomUser照合・必須メール確認のDB障害はフォームで処理されていなかった。OperationalErrorを各箇所に注入した回帰テスト3件で修正前の失敗を確認（tmp/login-lookup-red.log）。
- DB障害はDatabaseErrorに限定して捕捉し、日本語の再試行案内とlogin_unavailableコードでフォームを拒否する。EmailAddress障害時にCustomUser照合へ進まない。ログには例外型だけを記録する。元からモジュール先頭で必須importされているEmailAddressの重複importと広い例外処理を除去した。通常の未確認メール拒否も日本語へ変更し、既存の画面テストを更新した。
- 実データ・外部通信から隔離したSQLiteで既存認証を含む33件・3 subtests成功（52.64秒、tmp/login-lookup-green.log）。後から追加したHTTP画面テスト・ログ本文非露出の検査を含む障害テスト4件も成功（34.94秒、tmp/login-lookup-final.log）。実際のログイン画面が再試行案内を返し、認証セッションを作らないことを確認。DB障害は注入テストであり、共有DBの停止実験や実メール送信は行っていない。
- tmp/login-lookup-coverage.jsonで新規の例外ハンドラーと再試行案内に未実行行なし。Black/isort/flake8・差分・日本語文言を確認。DBスキーマ・実利用者・共有環境・権限・費用の変更なし。復旧はアプリ変更のrevertで可能だが障害時フォールバックが戻る。残る画像処理の例外監査・最終候補全体/CI/実サービス検証は未完了。正式公開No-Goを維持する。

## 継続監査: 画像容量検証後の読み取り位置

- 15c02fa0と差分なしから開始。容量検証後のseek(0)失敗を無視して入力を受理する問題を、OSError注入で再現した。修正前1失敗・1成功（tmp/image-stream-red.log）。
- OSError/ValueErrorで先頭へ戻せない場合は日本語の選び直し案内で入力を拒否する。正常PNGが検証後も先頭から全内容を読めることと、失敗時に画像DBレコードが増えないことを検証。容量推定の既存フォールバックや料金・枚数上限の仕様は変更していない。
- 隔離SQLiteの画像関連42件成功、14警告、48.28秒（tmp/image-stream-green.log）。警告はDjango非推奨9件と既存テストの戻り値に関する非推奨5件。Black/isort/flake8と差分・日本語案内を確認。共有ストレージ障害や実サービスの保存を再現した結果ではない。
- DBスキーマ・実利用者・共有環境・権限・費用変更なし。復旧はアプリ変更のrevertで可能だが読み取り位置の失敗が無視される動作が戻る。画像代替表示の例外監査、最終候補全体/CI/実サービス検証は未完了。正式公開No-Goを維持する。

## 継続監査: 一覧のメイン画像未指定時の表示

- d74b1dfdと差分なしから開始。CharacterSheetListSerializerはメイン画像が未指定の場合に版別画像モデルに存在しないcreated_atで並べ替え、例外を無視していた。6版/7版で一覧に代替画像が返らない2 subtests失敗を再現（tmp/list-image-red.log）。
- メイン指定を優先し、表示順・uploaded_at・主キーで選ぶ単一クエリへ変更。広い例外の無視を廃止した。リクエストがないシリアライズや画像なしの場合は元の表現を維持する。
- 隔離SQLiteで関連41件・2 subtests成功（49.88秒、tmp/list-image-green.log）。メイン未指定時の表示順・同順ならアップロード日時、指定時の優先を6版/7版で確認。14警告はDjangoと既存テスト戻り値の非推奨。Black/isort/flake8・差分を確認。実ストレージの可用性やブラウザ描画の検証ではない。
- DBスキーマ・実利用者・共有環境・権限・費用変更なし。復旧はアプリ変更のrevertで可能だが代替画像が返らない動作が戻る。既存移行の削除失敗の扱い、最終候補全体/CI/実課金・外部連携検証は未完了。正式公開No-Goを維持する。

## 継続検証: d572a618の全体実行開始

- d572a618841389151b5391d6a54568d79ae1b156と差分なしから開始。稼働中のDocker検証コンテナがないことを確認し、git archiveから固定ソースのテストイメージを構築した。tableno-formal-release-test:d572a618-browser、ID sha256:aa0e8edcab3cd56a7ddbf897febac39502682dd9998202b51047b1aa5f48e0ac、revisionラベルは上記完全SHA。配備用イメージではない。
- SQLite全体handle90338、PostgreSQL全体handle35984を開始。accounts/api/scenarios/schedules/support/tableno/tests/unit/tests/integrationとアプリ単位カバレッジを対象とし、出力先はtmp/formal-release-d572a618-full-output。PostgreSQL16は専用tmpfs DBとinternalネットワーク。SQLiteは開始後にbridgeを切断した。架空の検証設定であり、共有DB・実連携・外部通知は使用していない。途中出力の進捗を確認したが、完了結果は未取得。停止や失敗と推定して同じ実行を再開始しない。
- Blackは409ファイル変更不要、flake8は指摘なし。isortは既存test_character_image_apis.pyのローカル改行混在で失敗し、LFへ正規化後に全アプリのチェック成功。空白差分を除くソース変更はなし。全体テストはgit archiveの固定候補を維持しており、成功判定は終了結果取得後に行う。正式公開No-Goを維持する。

## 継続検証: d572a618配備用イメージの構築

- 既存の全体テスト用コンテナ2個が稼働し、途中進捗が増えていることを確認。同じhandle90338/35984を継続し、再開始していない。
- d572a618841389151b5391d6a54568d79ae1b156のgit archiveから通常Dockerfile/requirements.lock.txtでビルド成功。tableno-formal-release:d572a618、ID sha256:d47649829157729c72170347ab21348edc06567abf10e0d797d50132516024da。revisionラベルは対象完全SHA、実行ユーザーtableno。テスト依存入りイメージとは別。
- network noneでpip check成功。以前作成した架空設定tmp/candidate-58a27172.envを用い、network noneでmanage.py check --deployは指摘0。実料金・OAuth・Stripe設定やTLS/ALBの検証ではなく、DBへの疎通・通常起動・移行はこの実行では確認していない。ECRへpushせず、共有環境・実データ・権限・費用変更なし。
- 証跡: tmp/formal-release-d572a618-production-build.log、tmp/candidate-d572a618-deploy-check.log。全体テストの完了結果、候補の通常起動/移行、リモートCIと実サービス検証は引き続き未完了。正式公開No-Goを維持する。

## 継続検証: d572a618の通常起動と移行

- 固定配備用イメージtableno-formal-release:d572a618を、専用internalネットワーク、tmpfs PostgreSQL16、Redis7で起動した。共有環境・実データなし、ホスト公開ポートなし。以前の架空設定を使用し、DB/Redis接続先を今回の専用コンテナへ明示的に置換した。
- 通常entrypointでRUN_MIGRATIONS/RUN_COLLECTSTATIC=true、収集失敗許容false。全移行が完了し、179 static filesを収集、Daphne起動を確認。makemigrations --check --dry-runは変更なし、migrate --check成功。
- コンテナ内部の/health/ready/が200、database/cacheともok。DENY/nosniff/HSTSを確認。X-Forwarded-Proto=httpsを付けた内部HTTP検証であり、実TLS/ALB/OAuth/Stripe/S3の証明ではない。空の検証DBからの移行であり、実利用者データを含むアップグレード・ロールバックの代用ではない。
- 証跡: tmp/candidate-d572a618-startup.log、tmp/candidate-d572a618-migration-diff.log、tmp/candidate-d572a618-ready.log。アプリ/DB/Redisコンテナと専用ネットワークは終了・削除済み。別のSQLite/PostgreSQL全体テストは同じhandle90338/35984で継続中。正式公開No-Goを維持する。

## 全体検証終了とBootstrapのCDN依存是正

- d572a618全体実行handle90338/35984は双方終了コード1。SQLiteは1失敗・1630成功・7skip・437 subtests、86.93%、1233.81秒。PostgreSQLは1失敗・1637成功・skipなし・437 subtests、87.38%、1261.28秒。両方ともtests/integration/test_custom_skill_e2e_final.pyの技能追加ボタン待機が失敗。全体成功とは扱わない。専用PostgreSQL/ネットワークは削除済み。
- 共通base.htmlはBootstrapを外部CDNに依存し、隔離ネットワークではタブ操作が成立していなかった。従来と同じBootstrap5.3.0のCSS/JSをnpm配布物から改変せず同梱し、Django static経由の参照へ変更。MITライセンスと取得元・SHA-256をstatic/vendor/bootstrap/5.3.0/README.mdに記録。版更新や全依存の安全性評価はこの変更では行っていない。
- network noneの固定テストイメージへ修正したbase.htmlとvendorだけをマウントし、失敗した実Chrome E2Eが1件成功（32.99秒、9警告、tmp/bootstrap-offline-green.log）。node --checkと差分・文字コード・変更した参照を確認。Font Awesome/Axios等の外部参照は残るため、サイト全体のオフライン対応とは言わない。
- DBスキーマ・実データ・共有環境・権限・費用の変更なし。反映時はcollectstaticが必要。復旧はテンプレート変更のrevertで可能だがCDN依存が戻る。修正後の候補全体/CI/実サービス検証は未完了で、正式公開No-Goを維持する。

## 継続検証: Bootstrap同梱後の8f855617全体実行

- 8f85561755e67bc65ffef2fe9df0ef1c53f77156と差分なし、稼働中検証コンテナなしを確認。git archiveからテストイメージtableno-formal-release-test:8f855617-browserを構築した。ID sha256:8bb48a0f80079169dffc9441d73baee131f56dbbe92f61aed5f699ede6edad69、revisionラベルは対象完全SHA。
- SQLite handle18576、PostgreSQL handle60772で全体実行を開始。対象はaccounts/api/scenarios/schedules/support/tableno/tests/unit/tests/integration、アプリ単位カバレッジとJUnitを出力。SQLiteは開始時からnetwork none、PostgreSQL16は専用tmpfs DBとinternalネットワーク。共有DB・実連携・実通知は使用しない。
- 証跡先はtmp/formal-release-8f855617-full-output、実行スクリプトtmp/run-full-8f855617.ps1。両コンテナの稼働を確認したが終了結果は未取得。前回d572a618の両DB1失敗は履歴として維持し、今回の開始や該当E2E単独成功を全体合格と扱わない。正式公開No-Goを維持する。

## 継続検証: Bootstrap同梱の配備用イメージ

- 8f85561755e67bc65ffef2fe9df0ef1c53f77156のgit archiveから通常Dockerfileで配備用イメージを再構築。tableno-formal-release:8f855617、ID sha256:b9e97b30ba4ef2aa875e5f77339d8cad81d7c6fcb1fa1d5879b767fe1d3f87bc、実行ユーザーtableno。
- network none、以前の架空設定、S3無効でcollectstatic成功（183件）。配置済みBootstrap CSS/JSのSHA-256が配布物と一致し、Django staticが/static/vendor/bootstrap/5.3.0/以下の対応URLを生成することを確認。check --deploy指摘0。実CloudFront/S3配信やTLS確認は含まない。
- 証跡: tmp/formal-release-8f855617-production-build.log、tmp/candidate-8f855617-static-check.log。検証コンテナは終了時に削除。ECRへ送信せず、共有環境・実データ・権限・費用変更なし。全体テストは既存handle18576/60772の同じ実行を継続中。正式公開No-Goを維持する。

## 8f855617全体結果と一覧性能の基準測定

- 全体実行handle18576/60772は双方終了コード0。SQLite1631成功・7skip・437 subtests、86.94%、1239.78秒。PostgreSQL1638成功・skipなし・437 subtests、87.38%、1269.93秒。JUnitは双方2075件、failures/errors 0。前回失敗した技能E2Eが双方成功、SQLiteでskipの行ロック7件もPostgreSQLでは成功を個別照合した。
- 固定対象は8f855617。以降の性能ツール/文書はこの全体実行に含まれない。性能ツールの単体5件・3 subtestsは別途成功。リモートCI・実連携・公開判断は未完了。全体用の専用DB/ネットワークは削除済み。
- 全体終了後、準備済みの隔離性能環境でウォームアップ各10要求、その後同時要求1と10で各一覧30要求を順番に測定した。各測定は合計90要求すべて200。最初のウォームアップはポート8000指定漏れで接続失敗し、warmup.jsonに残す。修正後のwarmup-corrected.json以降だけを応答時間の資料とする。
- 同時要求1→10のp95は、キャラクター一覧361.4→4245.1ms、シナリオ一覧246.3→3184.0ms、セッション全期間183.8→678.5ms。1 CPU/1 GiBのローカルアプリ、専用PostgreSQL/Redis、利用者10人、キャラクター1000件/セッション100件/シナリオ100件という限定条件。合意した性能基準はなく、Q02の合格を意味しない。CPU/メモリのsampleは測定終了後でありピーク利用率ではない。
- 同じ利用者・データでAPIClientとDB execute_wrapperを用いてクエリを計数。キャラクター100件の一覧206クエリ（同形最大50回）、シナリオ30件152クエリ（同形最大30回）、セッション20件7クエリ。ネットワーク測定とは別の診断であり、一覧の繰り返しクエリを次の改善対象にする。
- 証跡: tmp/formal-release-8f855617-full-outputとtmp/performance-8f855617のconcurrency-1.json、concurrency-10.json、query-counts.log。性能用アプリ/DB/Redisとネットワーク、使い捨てトークンファイルは削除済み。共有環境・実データ・権限・費用変更なし。正式公開No-Goを維持する。

## シナリオ一覧の繰り返しクエリ削減

- 一覧だけ作成者・推奨技能・HOの関連データをまとめて読み、プレイ回数と時間を相関サブクエリで取得する。複数の共通グループがあっても集計を重複させず、従来の実時間優先・未関連履歴の扱いを維持する。
- 5シナリオと履歴・秘匿HOを使う回帰テストは修正前31クエリで失敗、修正後6クエリ以内で成功。所有者にはGMメモと秘匿HO内の技能を返し、共通グループの非所有者にはGMメモ・秘匿HOを返さず、無関係な所有者のシナリオを除外することも検証。
- SQLiteシナリオ関連62件・12 subtests成功。非所有者ケース追加後の最終回帰テストもSQLiteで1件成功（16.99秒）、PostgreSQL16では関連62件・12 subtests成功（72.00秒）。既存非推奨警告9件。証跡: tmp/scenario-query-green.log、tmp/scenario-query-sqlite-final.log、tmp/scenario-query-postgres.log。使い捨てPostgreSQLと専用ネットワークは削除済み。
- 応答時間の再測定と修正後候補全体のテストは未実施。8f855617の全体成功を本修正の全体成功として扱わない。正式公開No-Goを維持する。
- ソースレビューで追加の指摘なし。UI表示文言・DBスキーマ・実データ・共有環境・権限・費用の変更なし。復旧は本修正のrevertで可能。

## キャラクター一覧の画像取得を一括化

- 6版・7版の一覧用画像をそれぞれ表示優先順でprefetchし、シリアライザーがその結果を利用する。単独シリアライズ時の取得と既存のメイン画像優先・表示順・日時・IDによる選択順を維持する。
- 回帰テストは6版・7版計8キャラクターの画像問い合わせ8回で修正前に失敗し、修正後は2回以内で成功。画像なし・通常画像・メイン画像の選択、他ユーザーのキャラクター除外を検証した。従来の同順序でのアップロード時刻テストも成功。
- 隔離SQLiteで画像選択・複数画像・画像API・6版バージョン管理の56件・2 subtests成功（57.58秒、既存警告14件）。証跡はtmp/character-image-query-red.logとtmp/character-image-query-green.log。8f855617のテストイメージに変更3ファイルを読み取り専用マウントした。修正後のPostgreSQL・全体テスト・応答時間再測定は未実施。
- Black/isort/flake8、差分、文字コードを確認。ソースレビューで追加指摘なし。UI文言変更なし。DBスキーマ・実データ・共有環境・権限・費用への変更なし。復旧は本変更のrevert。一覧の最新バージョン取得にも繰り返し問い合わせが残るため、性能ゲート合格とは扱わず正式公開No-Goを維持する。

## キャラクター一覧の最新版取得を一括化

- 従来は各キャラクターについて親をたどり、根と直下の子だけから最大版を求めていた。利用者・6版/7版ごとにID・親ID・版番号だけを取得し、シリアライザー内で系列ごとの最新版を計算する。孫以降の版も含め、利用者間で集計を混ぜない。ページ外の版も対象にする。
- 修正前は10キャラクターの一覧で25クエリとなり上限10の回帰テストに失敗。修正後は10以内で成功し、両版の根・子・孫・分岐・独立系列・別所有者の高い版番号を区別できることを確認した。
- SQLite関連17件・2 subtests成功（23.70秒、9警告）。ページ外の最新版を明示確認するよう受け入れテストを補強し、最終テスト単独1件も成功（18.56秒）。証跡: tmp/character-version-list-red.log、tmp/character-version-list-green.log、tmp/character-version-list-pagination.log。
- PostgreSQL16では画像選択・画像API・複数画像・6版バージョン管理・シナリオ全体を含め119件・14 subtests成功（112.83秒、既存警告14件、tmp/list-query-postgres-final.log）。この実行はページ確認の補強前に開始した。8f855617の隔離イメージに最新の変更ファイルをマウント。専用tmpfs DBとinternalネットワークは検証後削除済み。
- Black/isort/flake8と差分を確認、ソースレビューの追加指摘なし。UI文言・DBスキーマ・実データ・共有環境・権限・費用変更なし。復旧は本修正のrevert。応答時間の同条件再測定と修正後候補全体のテスト/CIは未完了で、正式公開No-Goを維持する。

## b6e58ebd一覧性能の再測定

- 対象b6e58ebd2af17469a1b2d2fc0de1e9b355fa1129のgit archiveから通常Dockerfileで配備用イメージを構築。tableno-formal-release:b6e58ebd、sha256:8cd6229e7779e5abd5d2383379eae685909481f1a48ca27046e0b1b2de72408e、実行ユーザーtableno。collectstatic183件成功。ECR送信なし。
- 前回同様、1 CPU/1 GiBのアプリ、PostgreSQL16（1 CPU/512 MiB、tmpfs）、Redis7（128 MiB）、internalネットワーク、ホスト公開ポートなし。利用者10人、キャラクター1000件、セッション100件、シナリオ100件。同じseedと架空設定を使用し、名前に旧SHAが残るDB/アプリ名はseedの接続先ガードと比較条件を維持するため再利用した。実行イメージは上記の最新候補。
- 最初のseedはマイグレーション完了前に実行してデッドロックで失敗した（seed.log）。トランザクションがロールバックされ、初期化とASGI起動の完了後に空DBガードを満たして再実行成功（seed-retry.log）。API返却件数はキャラクター100件、シナリオ30件、セッション全期間20件で前回と一致。
- DB問い合わせはキャラクター206→10、シナリオ152→4、セッション7→7。同形SQLの最大反復は全て1回。APIClientによる別計測でありHTTP負荷測定とは区別する。
- ウォームアップ各10要求後、各一覧30要求を同時要求1、10の順で実行。ウォームアップ30件と測定180件は全てHTTP200。同時要求1のp95はキャラクター147.94ms、シナリオ48.05ms、セッション186.51ms。同時要求10のp95は1587.77ms、907.53ms、804.03ms。前回はそれぞれ4245.09ms、3184.02ms、678.48ms。セッションのp95は増えており、全画面一律の改善とはしない。
- 各条件1回、ローカル共有ホスト上、10利用者での限定測定で統計的有意差や本番性能の保証ではない。TLS/外部連携/アップロード負荷/実AWS/合意済み性能閾値は未検証。隔離HTTPのためSECURE_SSL_REDIRECT=falseを明示した環境でcheck --deployは想定したW008を1件報告。配備設定の合格証拠として使わない。
- 証跡はtmp/performance-b6e58ebdのfixture-counts.log、query-counts.log、warmup.json、concurrency-1.json、concurrency-10.json、deploy-check.log。ビルドはtmp/formal-release-b6e58ebd-production-build.log。専用アプリ/DB/Redis/ネットワークと使い捨てトークンファイルは削除済み。共有環境・実データ・権限・費用変更なし。正式公開No-Goを維持する。

## 77b10ded候補全体の検証開始

- 作業ツリーがクリーンで実行中の検証コンテナがないことを確認し、77b10ded69f467dea8f7a924dfc3f65faaa0da44のgit archiveからテストイメージを作成。tableno-formal-release-test:77b10ded-browser、sha256:b2a5063de868e7b2b21144b0e58e80b0040e77c82b91a48c2d9825df35f9e4d7。revisionラベル一致。
- SQLite handle79521とPostgreSQL handle97010でaccounts/api/scenarios/schedules/support/tableno/tests/unit/tests/integrationを実行中。SQLiteはnetwork none、PostgreSQL16は専用tmpfs DBとinternalネットワーク。前回8f855617からのアプリ差分は一覧取得・最新版集計と性能ツール等で、12ファイル差分。終了結果・カバレッジ・JUnitはまだ未取得。
- 実行スクリプトtmp/run-full-77b10ded.ps1、出力tmp/formal-release-77b10ded-full-output、ビルドログtmp/formal-release-77b10ded-test-build.log。コンテナとログ進捗を確認した。終了前に同じ実行を再起動せず、既存handleを継続して確認する。
- 配備準備資料とDraft PR文案を現候補に更新。記録済みAWS稼働ソース8cf3c7f7から188ファイル差分で、移行変更は従来どおりaccounts0058とschedules0055。現在のAWS状態を再取得した結果ではない。PR作成・CI・共有環境反映は未実施。
- 文書の差分・対象SHA・イメージIDを照合。共有環境・実データ・権限・費用の変更なし。正式公開No-Goを維持し、今回の全体実行開始を成功扱いしない。

## 77b10ded静的セキュリティ再解析

- 全体テストの既存handle79521/97010は双方実行中と確認。再起動せず継続。並行してBandit1.9.4で6アプリを再解析し、解析エラー0、HIGH/MEDIUM 0、LOW556、終了コード1。
- 前回d572a618のファイル/指摘ID/本文の多重集合と一致。テスト478、開発コマンド71、その他7。CCFOLIA出力テストのNode起動に関する9件を読み、固定リポジトリ資産・固定テスト入力・引数配列・shell未使用を確認した。PATH信頼とタイムアウトの制約を含め静的分類資料に記録。
- 証跡tmp/bandit-77b10ded-apps.jsonとtmp/bandit-77b10ded-run.log。コード変更なし。文書の差分・指摘場所・件数を照合。全体テスト終了結果、残る個別指摘、実サービス検証は未完了。正式公開No-Goを維持する。

## 既存データ入りPostgreSQL移行で新規阻害要因を再現

- 現行accounts/test_character_registry_migration.pyは独立SQLite DatabaseWrapperを明示しており、PostgreSQL全体テスト内でもSQLiteでの移行試験になる。この限界を確認し、専用PostgreSQL16/tmpfs/internalネットワークで追加検証した。
- 77b10dedの固定テストイメージでaccounts0054まで移行した旧構造に6版/7版の根と子、計4キャラクター、日本語メモ・秘匿情報・HP/SAN・版番号を作成し、現候補のleaf migrationsへ移行するスクリプトを実行。接続先名とDB名を固定し、空DB以外では開始しないガード付き。最初は検証データの必須能力値不足で失敗したため、使い捨てDBを作り直して必須値を補った。
- 再実行はaccounts0055の終了時のインデックス作成でOperationalError: cannot CREATE INDEX accounts_charactersheet6th because it has pending trigger events。django_migrationsのaccounts最新行は0054のままで、0055は適用完了していない。現候補へのデータ入りPostgreSQL移行は不合格であり、空DB移行成功や全体テストでは代替できない。
- accounts0055はCreateModelとRunPythonによる既存データコピーを同じ移行内で行う。Django公式文書にもPostgreSQLでスキーマ変更とRunPythonを同じ移行に混在させる際のpending trigger eventsへの注意がある: https://docs.djangoproject.com/en/5.2/ref/migration-operations/#runpython 。是正方法と既に適用済みの環境への影響は次の作業で検討し、無条件の逆移行・再実行やatomic無効化で回避しない。
- 証跡: tmp/prove-postgres-registry-upgrade.py、tmp/postgres-registry-upgrade-77b10ded.log（初回fixture不備）、tmp/postgres-registry-upgrade-77b10ded-retry.log（移行不備）。検証用DB/ネットワークは削除済み。共有環境・実データは未操作。修正・移行後のデータ一致・復旧検証は未完了で、正式公開No-Goを維持する。

## PostgreSQLのデータ入り0055移行失敗を是正

- accounts0055のデータコピー末尾でPostgreSQLに限りSET CONSTRAINTS ALL IMMEDIATEを実行し、同一トランザクション内の未実行FK検査を、schema editorのインデックス作成前に完了させる。atomicの無効化、制約の無効化、データ削除は行わない。制約違反は例外として伝播する。挙動の根拠: https://www.postgresql.org/docs/16/sql-set-constraints.html 。
- 0055は既存マイグレーションだが、未適用の旧構造から現候補へ到達できない問題を直すため局所修正した。既に0055適用済みのDBで再実行する変更ではない。共有環境では移行履歴を確認し、巻戻し/fake/適用済み処理の再実行を独断で行わない。配備前に確認する移行ファイル差分にはaccounts0055も追加される。
- 既存のレジストリ移行テストを、SQLiteでは独立ファイル、PostgreSQLではテストDB内のUUID名の専用スキーマで実行するよう拡張。移行を逆戻しせず旧状態から開始し、接続とスキーマ/ファイルをcleanupする。修正前のPostgreSQLで同じpending trigger eventsを回帰テストとして再現（24.63秒）。修正後はPostgreSQL1件成功（9.05秒）、SQLite1件成功（29.57秒）、各既存警告9件。6版/7版の移行、版の親子関係、技能/装備の引き継ぎ、旧列・旧関連テーブルの除去を確認。
- 初回の再現スクリプトも修正した0055を読み取り専用マウントして再実行成功。専用PostgreSQL16で旧構造から全leaf migrationsまで移行し、6版/7版計4件、日本語メモ・秘匿情報・HP/SAN・版・所有者・親子関係の一致、旧列不在、未適用移行0を確認。
- 証跡: tmp/registry-migration-pg-red.log、tmp/registry-migration-pg-green.log、tmp/registry-migration-sqlite-green.log、tmp/postgres-registry-upgrade-fixed.log。使用した基底イメージは77b10ded固定で、変更ファイルのみマウント。専用DB2台とネットワークは削除済み。
- Black/isort/flake8とソース差分を確認し追加指摘なし。UI文言変更なし。共有環境・実データ・権限・費用は未変更。復旧はアプリ変更のrevertと事前バックアップ方針に従い、既存の一方向移行を逆に実行しない。77b10dedの全体テストはこの修正を含まず、修正後全体・実環境移行・ロールバックは未検証。正式公開No-Goを維持する。

## 77b10ded全体結果とf692b994全体検証開始

- 77b10dedの既存handle79521/97010は双方終了コード0。SQLite1639成功・7skip・440 subtests、86.99%、1248.97秒。PostgreSQL1646成功・skipなし・440 subtests、87.43%、1274.06秒。JUnitは双方2086件、failures/errors 0。SQLiteでskipの行ロック7件がPostgreSQLでは全て成功したことと、技能E2E成功を個別照合。
- 8f855617以降の一覧コードの追加実行可能行をgit diffとPostgreSQL coverage JSONで照合。accounts/serializers25行、accounts/views/character_views3行、scenarios/serializers4行、scenarios/views6行に未通過行なし。行カバレッジであり分岐網羅や全セキュリティ条件の証明ではない。性能ツールや今回の移行修正の範囲を含めた100%主張はしない。
- 出力tmp/formal-release-77b10ded-full-output。旧実行用PostgreSQL/tmpfsとinternalネットワークは削除済み。この全体成功にはf692b994のデータ入りPostgreSQL移行修正が含まれない。
- 作業ツリーがクリーンなf692b994eb66d01b9c617577c3b7b6453664db95のgit archiveからテストイメージを作成。tableno-formal-release-test:f692b994-browser、sha256:020f2cda8cf566d6a6ade624eeeafbd55d586fae3df8a93d3d17e71a5f37c642、revisionラベル一致。SQLite handle26676、PostgreSQL handle51390で従来と同じ全体対象を開始。SQLite network none、PG16専用tmpfs/internalネットワーク、既存プロセスの再起動ではない。
- 実行スクリプトtmp/run-full-f692b994.ps1、出力tmp/formal-release-f692b994-full-output、ビルドログtmp/formal-release-f692b994-test-build.log。開始と稼働を確認し終了結果は未取得。共有環境・実データ・権限・費用の変更なし。正式公開No-Goを維持する。

## f692b994の配備用イメージ検証

- git archiveで固定したf692b994eb66d01b9c617577c3b7b6453664db95を通常Dockerfile/requirements.lock.txtで構築。tableno-formal-release:f692b994、sha256:1dd64113d7d6cec628aeda3220210e90c95e38c04bb275240012ad05daaada29、実行ユーザーtableno、revision一致。ECR送信なし。
- network none、既存の架空設定で、USE_S3_STORAGE=false・SECURE_SSL_REDIRECT=trueを明示。settings_production、DEBUG=false、session/CSRF secure cookie有効をassert。pip check成功、collectstatic183件、Bootstrap CSS/JSの収集先とソースのSHA-256一致、check --deploy（fail_level=WARNING）指摘0で完了。
- 証跡: tmp/formal-release-f692b994-production-build.log、tmp/check-f692b994-production.py、tmp/candidate-f692b994-production-check.log。コンテナは終了時削除。静的設定・ローカル収集を確認したもので、実TLS・S3/CloudFront・外部連携・実データ更新・バックアップ復旧の証明ではない。
- 全体テストは既存SQLite handle26676、PostgreSQL handle51390の双方が実行中。結果未取得。配備準備資料をf692b994とaccounts0055の追加差分へ更新。共有環境・実データ・権限・費用変更なし。正式公開No-Goを維持する。

## 配備用f692b994でデータ入り移行から通常起動まで確認

- 通常Dockerfileで構築済みのtableno-formal-release:f692b994（sha256:1dd64113d7d6cec628aeda3220210e90c95e38c04bb275240012ad05daaada29）を使用。専用PostgreSQL16/tmpfsとRedis7、internalネットワークを新規作成し、ホストポートを公開せず、既存の架空本番設定とS3無効化で実行。
- tmp/prove-postgres-registry-upgrade.pyを使用し、空DBガード確認後に旧accounts0054構造と6版/7版の根・子計4件を作成。全leaf migrationsまで成功。日本語メモ・秘匿情報・HP/SAN・版番号・所有者・親子関係一致、旧列不在、未適用移行0を確認。テストイメージへの修正ファイルマウントではなく、配備用イメージ内のソースで実行した。
- 同じデータ入りDBに通常entrypointで起動。RUN_MIGRATIONS=true、RUN_COLLECTSTATIC=true、COLLECTSTATIC_ALLOW_FAILURE=false。静的183件収集・Daphne起動成功。readiness HTTP200、database/cache ok。使い捨てユーザーのTokenを隔離DB内で生成して一覧APIを実HTTPで取得し、200・4件・両版・最新版2・メモ/秘匿HO非表示・未適用移行0を確認。
- SECURE_SSL_REDIRECT=trueを維持し、内部HTTPにX-Forwarded-Proto:httpsを付けたプロキシ模擬の確認。実TLS、信頼できるプロキシ設定、S3/CloudFront、実ユーザー/OAuth、外部配送、実環境ロールバックは未検証で、これらの合格とは扱わない。
- 証跡tmp/production-registry-upgrade-f692b994.log、tmp/production-upgrade-runtime-f692b994.log、tmp/production-upgrade-startup-f692b994.log。検証用アプリ/DB/Redis/internalネットワークを削除済み。トークンは出力しておらず、DB削除で破棄された。共有環境・実データ・権限・費用の変更なし。正式公開No-Goを維持する。

## 移行前PostgreSQLバックアップの別DB復元

- f692b994の通常配備用イメージ、専用PG16/tmpfs/internalネットワークで旧accounts0054構造と6版/7版計4件を作成。空DB・接続先ガードを維持したseedはtmp/rollback-f692b994/seed.py。移行前に全publicテーブルの行ハッシュ・列定義・制約・インデックスを取得し、pg_dump -Fcで保存。その後、同じDBへ現候補の全マイグレーションを適用して成功した。
- 別の空DB isolated_registry_restoredを作成してpg_restore --exit-on-errorで復元。39テーブル・78行の全行ハッシュ、列名/型/null可否/default、制約定義、インデックス定義が移行前と完全一致。移行履歴テーブルも比較対象に含む。一方向マイグレーションの逆実行はしていない。
- fingerprint.pyのinformation_schema.sequencesはidentity sequenceを列挙しないため、出力のsequences:0を採番状態の完全一致と解釈しない。別途、復元DBでpg_get_serial_sequence/nextvalを実行し、キャラクター4件の次値5、ユーザー1件の次値2を確認した。他のidentity sequenceの完全比較は未実施。
- 証跡tmp/rollback-f692b994のseed.log、before-summary.log、upgrade.log、restore.log、restored-summary.log、comparison.log、identity-next-values.log。比較元と先はisolated_registry_upgrade.jsonとisolated_registry_restored.json。DB内の実値はハッシュ化し、報告へ秘匿メモやトークンを出していない。
- ダンプは専用コンテナの/tmpのみで使用し、終了後にDBコンテナ・ネットワークを削除した。これは小規模な模擬データのDB復元証拠であり、稼働中環境の全データ/画像復元、旧アプリ起動、負荷中の書込み整合性、実RDS/S3、RPO/RTOの合格ではない。共有環境・実データ・権限・費用への変更なし。正式公開No-Goを維持する。
- f692b994の全体テストは既存handle26676/51390の実行中を再確認し、再起動していない。

## 移行前バックアップのidentity採番を含む再比較

- 以前の画像込み復元試験（tmp/restore-drill-20260905/probe.py）はpg_sequencesで87採番状態を比較していたことをソース確認。information_schema.sequencesによる見落としは直近の小規模移行復元スクリプトに限定される。
- 比較処理をpg_sequencesによる列挙へ修正し、元の証跡を上書きせずtmp/rollback-f692b994-v2で独立再実行。f692b994の通常配備イメージ、PG16/tmpfs/internalネットワークで旧accounts0054構造と6版/7版計4件を作成、移行前fingerprintとpg_dumpを取得、現候補まで全移行、その後別DBへpg_restore --exit-on-errorで復元。
- 全39テーブル・78行のハッシュ、列定義・制約・インデックスに加え、全39 sequenceのlast_value/is_calledが移行前と完全一致。列挙件数39をassertし、空の採番一覧同士の一致ではないことを確認した。今回の比較前にはnextvalで状態を進めていない。
- 初回のseed起動は/proofに配置したスクリプトのPython import経路不足でDB操作前に失敗。PYTHONPATH=/appを明示して空DBガードを維持したまま再実行した。seed.logに初回失敗、seed-retry.logに修正後実行を保存。
- 証跡tmp/rollback-f692b994-v2のbefore-summary.log、upgrade.log、restore.log、restored-summary.log、comparison.logと比較JSON。専用コンテナ/ダンプ/ネットワークは終了後削除済み。旧アプリ起動、画像、実RDS/S3、RPO/RTO、実ユーザーデータはこの試験の対象外。共有環境・実データ・権限・費用への変更なし。正式公開No-Goを維持する。

## f692b994全体結果とコメント順序テストの明確化

- 既存handle26676/51390は終了。SQLiteは終了コード0、1639成功・7skip・440 subtests、86.97%、1268.42秒。PostgreSQLは終了コード1、1645成功・1失敗・440 subtests、87.41%、1297.10秒。JUnitは双方2086件で、SQLite failures/errors 0、PostgreSQL failures1/errors0。SQLiteの行ロック7skipはPGで全て成功、今回拡張したデータ入りPGレジストリ移行テストも成功を個別照合。
- 失敗はschedules/test_advanced_scheduling.pyのtest_date_poll_comments_create_and_list。投稿した2コメントの取得順が期待と逆だった。一覧処理は既にcreated_at/idで降順取得後に反転する時刻順で、同時刻のID順も指定されている。失敗時の保存時刻はJUnitに記録されておらず、ホスト時計の変化など特定原因を断定しない。
- テストの「投稿順とホスト時計の時刻順が常に一致する」という暗黙の前提を除き、POSTでの作成確認後に使い捨てテストDB内のcreated_atを明示した。通常時刻順、IDと逆になる時刻順、同時刻のID順、limit=1の最新選択を検証する。アプリ処理は変更せず、単に期待順を実装の返却結果へ合わせる変更ではない。既存の投稿・入力拒否・非参加者拒否のassertも維持。
- 変更ファイルだけをf692b994固定テストイメージへマウントして日程調整関連を実行。PostgreSQL20件成功（24.72秒）、SQLite20件成功（39.78秒）、各既存警告9件。証跡tmp/date-poll-order-postgres.log、tmp/date-poll-order-sqlite.log。全体結果はtmp/formal-release-f692b994-full-output。過去のPG全体失敗を上書きせず、テスト修正後の全体再実行/CIとは区別する。
- Black/isort/flake8、ソース差分、既存日本語の保持を確認し追加指摘なし。UI表示・アプリコード・DBスキーマ変更なし。全体用の専用PG/tmpfsとネットワークは削除済み。共有環境・実データ・権限・費用変更なし。正式公開No-Goを維持する。

## 切り戻し検証用の実稼働イメージを固定

- 旧8cf3c7f7のDockerfileはrequirements.txtの範囲指定から依存を解決するため、現在の再ビルドを当時の稼働イメージと同一とみなせない。既存tableno-preプロファイルを用いてECS/ECRを読み取り確認した。最初のプロファイル未指定呼出はNoCredentialsで終了し、構成済みプロファイルを確認して読み取りを実施した。
- ECS tableno-aws-preはtask definition40、desired1/running1/pending0。RUNNINGタスクのwebコンテナはaws-pre-8cf3c7f7、imageDigest sha256:551535a7219a599891d592346480803966abfb54f856656201ca08eec1d42b66。ECR describe-imagesの同タグdigestと一致し、登録日は2026-08-15T10:00:05.723+09:00。
- 既存資格情報でECR認証後、タグではなく上記digest指定でローカルへpull。ローカルイメージID sha256:58a0a768937f40c7e5c03852cd16e8437a6f7e5cff5bc13195efde80dd9eb578、RepoDigests一致。取得ログtmp/rollback-running-image-pull.log。ECR資格情報はpassword-stdinで渡し、値を出力していない。
- network noneの一時コンテナで配布メタデータのみ確認。Django5.2.17、DRF3.18.0、allauth65.19.1、psycopg3.3.4、Stripe15.5.0。Config.Userは空で旧Dockerfileのデフォルト実行設定。アプリを共有DBへ接続していない。
- 今回は切り戻し検証対象の取得・同一性確認まで。旧アプリに適合する移行前DB/画像の用意、現候補への更新、復元後の旧アプリ起動と主要フローの一致は次の作業。AWSのサービス/タスク/DB/IAM/Secrets設定・実データ・継続費用は変更していない。公開No-Goを維持する。

## 実旧イメージから現候補へ更新し、復元した旧アプリを確認

- 取得済み実稼働イメージdigest sha256:551535a7219a599891d592346480803966abfb54f856656201ca08eec1d42b66を、専用PG16/tmpfs・Redis7・internalネットワークで通常起動。架空設定、ENV_FILE空、S3無効、ホストポート非公開。共有AWSへの接続はない。旧イメージで全移行・静的179件収集・Daphne起動後に空ユーザーDBガード付きseedを実行した。
- GM/PL2人、非公開グループ、セッション1件、参加者role1件、秘匿HO1件、6版/7版各1キャラクター、PNG1件を作成。各ユーザーの使い捨てTokenでヘルスと一覧をHTTP取得。GMはキャラクター2件・セッション1件、PLはキャラクター0件・セッション1件、HP8/SAN47・版の一致と一覧にsecret_ho_infoが含まれないことを確認。秘匿HO本文のAPI表示範囲や全UI操作を検証した主張ではない。
- 全91テーブル・614行、全87 sequenceのlast_value/is_called、列定義・制約・インデックス、画像1件のSHA-256を記録。pg_dump -Fcと画像ファイルのコピーを保存し、旧アプリを停止。f692b994の通常配備イメージへ切り替え、通常entrypointで移行・静的183件収集・起動成功。schedules0055適用を確認し、同じHTTP参照結果が成立した。
- 現候補アプリを停止し、別の空DBへpg_restore --exit-on-error、画像バックアップも別フォルダへ復元。旧digestのアプリを復元DB/画像で起動した。RUN_MIGRATIONS=false、静的179件再収集、Redisは未使用のDB1を使いキャッシュで復元不備を隠さない。旧アプリのヘルス200/DB・cache okとGM/PL参照結果が移行前・更新後と一致した。
- 復元後fingerprintは元の91テーブル・614行・87採番状態・画像1件・列/制約/インデックスと完全一致。旧アプリが復元DBで起動・参照できることを確認した。DB移行の逆実行、稼働AWSの切り戻し、本番データのコピーはしていない。
- 証跡はtmp/image-rollback-919dc0deのseed.py/check-http.py/fingerprint.py、各*-startup.log、before/upgraded/restored-http.log、before/restored-snapshot.log、upgraded-migration.log、restore.log、comparison.logと比較JSON。専用アプリ/DB/Redis/internalネットワーク・コンテナ内ダンプとtokens.jsonは削除済み。PNGとハッシュ記録は架空データの証跡としてローカルに保持。
- 本検証は少量の模擬データを用いたローカルの更新・復元・旧API確認。TLSは内部HTTPの転送ヘッダー模擬、S3/CloudFront・実ユーザー・同時書込み・実RDS復元・合意RPO/RTO・旧版の全画面は未検証。バックアップ時点以降の書込みを保持する復旧方法の証明でもない。共有環境・実データ・権限・継続費用への変更なし。正式公開No-Goを維持する。

## AWS開発環境のバックアップ・監視設定の読み取り確認

- 2026-09-05、AWS CLIのtableno-preプロファイル、ap-northeast-1でRDS/CloudWatch/Logs/SNSのdescribe/listのみ実行。設定変更・試験通知は実行していない。
- RDS tableno-aws-preはavailable、PostgreSQL、バックアップ保持7日、暗号化と削除保護が有効、Multi-AZは無効。取得時のLatestRestorableTimeは2026-09-05T09:23:56Z。実際の復元成功や合意RPO/RTOの達成は未検証。
- メトリクスアラームはALBターゲット5xx、ECS CPU、ECS memoryの3件、取得時すべてOK・actionsEnabled=true。同じSNSトピックへの通知設定がある。email購読1件のSubscriptionArnはPendingConfirmationではなく確定ARN。宛先は記録・表示しない。実配送・担当者の受信や対応は未検証。
- ALB 5xxは300秒Sum・閾値5・評価2回、CPU/memoryは300秒Average・閾値80・評価3回。欠測時は3件ともnotBreaching。リージョン内の取得結果にRDS専用メトリクスアラームはなく、対象prefixのCompositeAlarmもない。DB障害・無応答・ジョブ停止を網羅するとは判断しない。
- /ecs/tableno-aws-preのログ保持は3日。Terraformではaws-prod向けRDS保持14日・ログ保持90日・アラーム欠測missingを定義しているが、本番への適用を確認したものではない。
- 公開前には環境別の監視対象と通知担当、保存期間、復元目標を確定し、専用宛先への通知と実RDS/S3復元を承認済み範囲で検証する。O01/O02は未完了、正式公開No-Goを維持する。

## コメント順序テスト修正後のPostgreSQL全体検証

- ソース919dc0de6c3424b4d8aa4862c814aa4bcb46dcbcの隔離PostgreSQL16全体テストが終了コード0。1646 passed、440 subtests passed、159 warnings、1181.75秒、カバレッジ87.42%。JUnitは2086件・failure/error/skipped各0。
- コメント順序テスト、既存キャラクターデータの移行テスト、f692b994 SQLite全体でskipされた行ロック関連7件の成功をJUnitで照合。ログ・JUnit・coverageはtmp/formal-release-919dc0de-full-output。
- SQLite全体はf692b994の1639成功/7skipを維持し、919dc0deのテスト変更は両DBで関連20件成功。SQLite全体を919dc0deで実行したとは扱わない。アプリコードはf692b994と同一で、以降はテスト・文書変更。以前のPostgreSQL失敗記録は保持する。
- 全体テスト終了後に専用DBコンテナとinternalネットワークを削除。リモートCI・実環境・課金と外部連携の実証は未完了で正式公開No-Goを維持。

## 旧テンプレート画像の残存確認とTerraform案の補完

- クリーンな42219b05から、旧移行0041の広い削除例外と保存prefixを調査。AWS開発用S3を読み取り集計し、media/session_template_images/に119件・21264バイトの残存を確認。内容・所有者・削除失敗との因果関係は未確認で、実ファイル本文のダウンロードや削除は行っていない。
- 最新の実バケットポリシーは対象CloudFrontからのAllowのみ。既存の未適用Terraform拒否案に旧テンプレートprefixの直下/任意location配下2パターンを追加。既存6パターンと合わせ8パターン。Terraform fmt -check / validate成功、具体JSON案のAWS Access Analyzer findings=[]。
- 詳細はSECURITY_STATIC_TRIAGE_494ABD0D.mdとAWS_PRE_FORMAL_RELEASE_VALIDATION_PLAN.md。変更は配信拒否の準備案のみ。アプリコード・DB・AWS設定・Secrets・継続費用は変更なし。アプリ全体テストの追加実行は不要と判断。実保護とデータ保持/削除の判断は残り、正式公開No-Goを維持する。

## S3画像バックアップ設定と世代の読み取り確認

- 2026-09-05、3ce88bdeのクリーンな作業ツリーから、tableno-pre/ap-northeast-1の対象S3バケットを読み取り確認。VersioningはEnabled、デフォルト暗号化はAES256。ライフサイクルは全prefixにNoncurrentDays=30/NewerNoncurrentVersions=3、期限切れ削除マーカー除去、未完了multipartの7日後中断。Terraform定義とも一致。
- media/のListObjectVersionsをページ制限なしのAWS CLI JSON出力で集計。オブジェクト版2678件（最新の実体2647件）、全版合計301031157バイト、削除マーカー31件（最新27件）。全版のサイズであり現在使用量や請求額ではない。ファイル名・本文は表示せず、復元用manifestとして取得したものでもない。リスト取得中の並行書き込みまで固定したスナップショットではない。
- GetBucketReplicationはReplicationConfigurationNotFoundError。同リージョンのAWS Backup ListProtectedResourcesで当該バケットARNに一致する結果は0件。別リージョン・別アカウント・手動コピー・外部方式のバックアップ不存在を証明するものではない。現時点で独立した画像バックアップとその復元実績は確認できていない。
- 現ライフサイクルの旧版削除は非現行日数と新しい非現行版数の両条件を超えたときの対象であり、30日後に必ず全旧版が消える設定ではない。永久削除された旧版はバージョニングだけでは戻せない。[AWS Lifecycle公式資料](https://docs.aws.amazon.com/AmazonS3/latest/userguide/intro-lifecycle-rules.html)
- backup.mdに、書き込み停止とDB参照の完全キー、VersionId固定取得、manifestとSHA-256照合、専用復元先への配置、削除済み版での停止、元オブジェクト非破壊の手順を追加。一括取得の実装や実S3復元の成功とは扱わない。実データ取得・復元先作成・ポリシー/保持期間変更・費用増加は未実施。O02と正式公開No-Goを維持。

## グループ招待URLの同時参加を冪等にする修正

- 77c50e50を起点に、同一利用者の同時POSTが両方ともロック前に未参加を観測するケースを専用PostgreSQL16で再現。使用上限1では201/410、上限2では201/500（重複会員制約）となる。既存の順次参加テストでは検出できなかった。
- GroupInviteLinkJoinViewで既存の招待行ロック取得後に参加済み状態を再確認。先行要求が登録済みなら200を返し、招待の使用回数を追加消費しない。未参加者の有効期限・失効・使用上限検査と通常登録は維持する。招待の所持だけで新たな管理者権限を与える変更ではない。
- 新しいTransactionTestCaseは実DB接続2本のAPIClientを使い、事前の会員exists結果をBarrierで揃える。ロックそのものは模擬しない。同一利用者/残り1回、同一利用者/余裕あり、別利用者/残り1回の3ケース。修正前2失敗/1成功、修正後は同一利用者が200/201・会員1件・use_count=1、別利用者が201/410・会員1件・use_count=1。
- PostgreSQLで招待リンク・グループ機能・競合の計54件成功（60.53秒、9 warnings）。最終整形後の競合3件も成功（3.00秒）。coverage JSONで追加実行行812/813の両方を通過。ファイル全体100%や全体テスト成功の主張ではない。
- 証跡はtmp/invite-concurrency-red-valid.log、tmp/invite-concurrency-green.log、tmp/invite-concurrency-coverage.log/json。初回のテスト起動パス誤りと期限未指定のfixture失敗は有効なRED証拠に含めず、修正したfixtureで再現したログを採用する。
- アプリイメージ919dc0deのコードに対象viewと新テストだけを読取マウントして検証。共有DB・実招待・通知・AWS権限は変更していない。招待失効と参加の同時操作、他の参加経路との競合、ブラウザ上の再送、所有権引継ぎの公開要件は別途未完了。正式公開No-Goを維持。

- SQLiteの関連51件成功・行ロックを必要とする新規3件skip（75.49秒、9 warnings）。tmp/invite-concurrency-sqlite.log。Black/isort/flake8、UTF-8/LFと差分を確認。新たなUI文言はなく、DBスキーマ・課金・費用への変更なし。検証終了後、専用DBとinternalネットワークを削除。

## 招待トークンを含む応答のキャッシュ・参照元保護

- e2952520のクリーンな作業ツリーで、グループ招待のトークン発行・ランディング・参加・失効応答に明示的な保存禁止がないことを確認。回帰テスト2件はno-store欠落で失敗（tmp/invite-headers-red.log、20.08秒）。
- 招待4ビューに共通dispatchを追加し、Django add_never_cache_headersによるprivate/no-store等とReferrer-Policy: no-referrerを設定。発行/一覧、ランディング、参加、失効が対象。URL・画面・権限・失効判定は変更せず、APIの認証エラー等にも処理後にヘッダーを付ける。
- 隔離SQLite・外部ネットワークなしで既存招待テストと新規ヘッダーテスト計12件・2 subtests成功（45.36秒、9 warnings）。成功、失効204、失効後410、未ログイン拒否、不明なランディング404のヘッダーを確認。coverage JSONで追加dispatch本体4行すべて通過。Black/isort/flake8とUTF-8/LF・差分確認成功。新しいUI文言なし。
- 証跡tmp/invite-headers-green.log、tmp/invite-headers-coverage.json。既存919dc0deテストイメージへe2952520以降の対象view/テストを読取マウント。DB操作を変更していないため、この変更ではPostgreSQLや全体スイートを再実行していない。以前のPostgreSQL競合成功をこの最新変更込みの成功とは扱わない。
- 応答ヘッダーはアクセスログのパス・login/signupのnextパラメータ、ブラウザ履歴、既存キャッシュ、外部監視へ記録済みのトークンを消さない。ミドルウェア等でビューに到達せず生成された応答や未処理例外の500も、このdispatchの保護を確認した範囲に含めない。実ブラウザ/CDN/ログ設定・記録の調査は残り、正式公開No-Goを維持する。共有DB・Secrets・AWS・費用に変更なし。

## Daphneアクセスログの招待トークン・クエリ除去

- 29de99d9のクリーンな作業ツリーから調査。標準docker/entrypoint.shはDaphneの通常CLIを起動し、その既定verbosityのAccessLogGeneratorがpathをストリームへ書く。応答のno-store/no-referrerだけではこのアクセス記録を抑制しない。
- AWS読み取りでは、対象ALBのaccess/connection/health_check logs.s3.enabledはfalse。CloudFront E3RQ829D1NVY28のDistributionConfig.Logging.Enabledはfalse、既定behaviorのRealtimeLogConfigArnはnull。CloudFrontの別方式のログ配送、WAF、外部監視、過去ログの不存在までは確認していない。実利用者のログ本文は取得していない。
- tableno.serverでDaphne CLIのserver_classを差し替え、action_loggerへ渡すdetailsのコピーだけを加工。招待ランディング/参加パスのトークンを[redacted]へ置換し、全アクセスパスのクエリ/fragmentと改行等の非表示文字を除去。メソッド・ステータス・サイズ・通常パスを維持。元details、ASGI scope、実リクエストのrouting/auth入力は変更しない。docker/entrypoint.shの標準コマンドをpython -m tableno.serverへ変更し、明示された別コマンドのexecは維持。
- 固定Linuxテストイメージでアクセス記録とentrypoint関連28件・4 subtests成功（1.15秒、4 warnings）。新moduleのunit coverageは95.65%、未通過は__main__からCLIを起動する36行だけ。実配備用f692b994イメージへ最終module/entrypointと架空ASGI probeを読取マウントして通常起動し、そのCLI経路を別途実行確認。公開ポートなし・network none・DB/静的更新なし。
- probeへ架空トークン付きURLを送り、HTTP200と元パスのbody一致、実Daphneログの[redacted]、クエリ値の不在とステータス保持を確認。最終コードで再起動して再確認し、専用コンテナを削除。アプリ本体の全起動・WebSocket通信・最新全体CIの検証ではない。単一coverage計測で100%を達成したとは扱わない。
- 証跡tmp/server-access-red.log、server-access-green.log（旧コマンドを要求する既存テスト1失敗）、server-access-final.log、server-access-coverage.json、server-access-runtime-final.log。ローカルWindowsのDaphne importは既存Twisted循環importで失敗したため合格扱いせず、固定Linux依存関係で検証。Black/isort/flake8、sh -n、差分・UTF-8/LF確認成功。新UI文言なし。
- Djangoの例外メール/例外ログ、クエリ以外の他種類のURLトークン、明示コマンドで直接起動するDaphne、外部監視や既存ログの保護は残る。新しい起動処理は未配備で、AWS設定・Secrets・実データ・継続費用への変更はない。正式公開No-Goを維持する。

## 共有・購読・アカウント確認URLのアクセスログ保護

- 04d817e1のクリーンな作業ツリーから、tableno.urlsとallauth account URLsを照合。前回のDaphneログ対策はグループ招待のみだったため、共有URL、ICS購読、ゲスト招待、募集リンク、メール確認、パスワード再設定を追加対象とした。
- 回帰テストはDjango reverseで19種類の実登録ルートを生成し、AccessLogGeneratorの出力で架空トークン不在とステータス保持、入力detailsが元パスのままであることを確認。修正前は19 subtestsすべてトークン残存で失敗（tmp/shared-token-log-red.log）。固定共有UUID、画像一覧/ZIP/preview/CCFOLIA出力等も含む。
- TOKEN_PATHSへ対象prefixを追加。URL自体・認証/認可・受信パスは変更しない。修正後は起動関連と合わせ29件・23 subtests成功（1.20秒、4 warnings）。Black/isort/flake8・差分・UTF-8/LF確認成功。新規UI文言なし。
- 配備用f692b994イメージへ最終server/entrypointと架空ASGI probeを読取マウントし、network none、公開ポート・DB更新なしで通常起動。ICS、キャラクター共有ZIP、パスワード再設定の3 URLにHTTP要求を送り、元パスのbody一致と実Daphneログの伏せ字を確認。専用コンテナ削除済み。証跡tmp/shared-token-log-green.log、tmp/shared-token-log-runtime.log。
- この3要求は実Daphneの記録検証であり、アプリ本体の閲覧/再設定フローやメール配送の成功ではない。未配備。Djangoの例外メール・例外ログ、外部監視、既存ログ、今回列挙した以外の新規URL形式は未確認。正式公開No-Goを維持する。

## 管理者向け例外メールからリクエスト情報を除去

- dc261c31のクリーンな作業ツリーで本番mail_adminsの標準AdminEmailHandlerを調査。架空の招待URL・query・POST本文・Authorization/Cookieと例外メッセージを含む記録で、通知内容からfixture値が除去されないことをメモリ内メールで再現。修正前2失敗/1成功（tmp/error-report-red.log）。実メールや実資格情報は使っていない。
- SafeAdminEmailHandlerを追加し、本番設定のmail_adminsのみ接続。UTC発生時刻、logger、level、静的ルート名、既知HTTP method、妥当なstatus、例外クラス名、スタックのファイル名/行番号/関数名を通知。recordの自由文・URL/リクエスト値・例外メッセージ・ソース行/ローカル変数・HTML詳細報告を出力しない。元request/recordは変更せず、他handlerへの暗黙の改変はしない。
- 既存のERROR閾値とrequire_debug_falseを維持。ADMINS空の場合の送信なし、例外なし/リクエストなしの通知、HTML指定時にも機密値不在、本番設定のclass接続を検証。トラブル調査に必要な発生箇所は残す一方、入力値・例外メッセージによるメール上の詳細調査はできなくなる。必要な再現は専用データで行う。
- 固定Linuxイメージに対象module/settings/testsを読取マウントし、network none、locmem backendで23件成功（12.27秒、4 warnings）。新handler全実行行のcoverage成功。Black/isort/flake8・差分・UTF-8/LF確認成功。証跡tmp/error-report-final.log、tmp/error-report-coverage.json。新UI文言なし。
- 変更は未配備で実SMTP配送は未検証。Djangoのconsole/file例外出力や他の明示的メール送信、外部監視、保存済みメールは対象外。実データ・DBスキーマ・Secrets・配送先・AWS設定・継続費用は変更していない。最新全体CI・実サービス検証は残り、正式公開No-Goを維持する。
