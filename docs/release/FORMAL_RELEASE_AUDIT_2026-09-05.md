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
