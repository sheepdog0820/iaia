# mainを基点にしたAWS SDK診断の情報保護（2026-10-28）

## 対象と公開判断

正式公開はNo-Goを維持する。[PR #7](https://github.com/sheepdog0820/iaia/pull/7)の承認・通常マージ後のmain `e914b325c2d79eb96c96cd05e418f15b5bd7fc0a` を基点に、既知のSDKログ問題を分離して修正する。作業ブランチは `codex/formal-release-followups-20261028`。元の作業フォルダーの未コミット変更は保持する。

元の修正は `dc0b053e356e2e9d1426f60760d07257c3e198e0` と `39b432869372aa6c6c4619b8c5bc5bf23ebba6a4`。この2件の製品ファイルと回帰テストだけを現在のmainに適用し、以前の大きな候補群、課金・Googleの変更、依存ロック、古い検証資料を一括で取り込んでいない。過去の正常配布物の試験結果は今回の配布物の成功へ流用しない。

追加レビューで、従来の依存宣言 `sentry-sdk>=1.38.0` では新しいhookを持たない版も許可されると分かった。[Sentryの公式2.35.0記録](https://github.com/getsentry/sentry-python/releases/tag/2.35.0)を確認し、入力側を `>=2.35.0,<3` へ整合した。3ロックの固定版2.68.1は変更せず、今回の実行検証もこの固定版を使う。

## 問題と修正

botocoreの実資格情報更新処理に合成の失敗を与えると、連鎖例外の本文が通常のログ出力へ残った。SentryでもSDKのイベント、後続イベントに付くbreadcrumb、Logsの収集対象に合成の非公開マーカーが残った。実Secretsや実ユーザー情報を使った検証ではなく、既存の運用ログに実際の漏えいがあったことを示す調査でもない。

- `botocore` / `boto3` とその子loggerだけを安全なformatterへ送り、rootへの伝播を止める。既存rootのログレベルによる選択は維持し、SDK用の管理者メール送信は追加しない。
- 本文、引数、例外メッセージ、cached traceback、stack_info、request/statusの追加値を出さず、logger、レベル、時刻、例外の種類と発生ファイル・行・関数を残す。元のLogRecordは変更しない。
- Sentryの実初期化に `before_send` / `before_breadcrumb` / `before_send_log` を設定し、SDKのイベント・breadcrumb・Logsを許可した診断項目だけにする。`send_default_pii=False` は維持する。
- `botocore_other` 等の別logger、通常のエラー通知と診断を維持する。アプリ独自loggerに書かれた任意のSDK例外まで全て保護するという主張ではなく、対象外の経路は後続監査を続ける。

本文を省くため、AWS診断の詳細は従来より少なくなる。例外の種類と発生位置は残すが、これだけで全てのAWS障害を特定できるとは扱わない。Sentryの送信先、Secrets、IAM、OAuth scope、保持期間や通知宛先を変更していない。

## 隔離検証

Python 3.11.18 / Django 5.2.17、botocore/boto3 1.43.80、sentry-sdk 2.68.1、coverage 7.15.4。現在の固定依存を使う補助Dockerイメージで、ソースを読み取り専用に配置し、外部通信なし・使い捨てストレージで試験した。通常配布物とは区別する。

1. 修正前の通常ログ: pytestで16失敗・4成功・4 subtests成功（失敗数にはsubtest失敗を含む）。資格情報更新のmandatory/advisory両方、開発/本番、標準出力/ファイル/rootで本文の残存を確認した。
2. 修正前のSentry: 10失敗・3成功（subtest失敗を含む）。実SDKのoffline Transportでイベント・breadcrumb・Logsの内容を捕捉した。未実装hookのImportErrorも失敗数に含む。
3. 修正後の初回追加試験: 56成功・55 subtests成功・1失敗。検証runnerの `USE_REDIS_CACHE=False` が本番設定試験へ継承され、TLS cacheの期待を変えていた。製品側の条件を弱めずrunnerからその値を除き、失敗ログを保持した。
4. 修正後の再試験: SDK/Sentry、既存エラー通知、本番設定、HTTP/WebSocketアクセスログの5ファイルで **57成功・55 subtests成功、省略なし**。botocoreは実更新ロジック、Sentryは実初期化と実envelopeを使い、外部送信はoffline Transportとネットワーク遮断で防いだ。
5. coverageのsubprocess追跡を有効にして `tableno/error_reporting.py` は **78実行文・16分岐とも未通過0、100%**。HTML/JavaScriptや製品全体の網羅率ではない。
6. 変更したPython 5ファイルのBlack・isort・Flake8・Bandit（medium以上）は成功。日本語UI文言の変更はなく、英語の追加文字列は技術者向けの診断ログである。差分レビューで対象外loggerの挙動、元recordの不変、送信先追加なしを確認した。
7. 設定モジュールもsubprocess追跡へ加え、SDK/Sentryと既存リリース文書の54テスト・38 subtestsが成功。追加実行文はerror_reportingの41行とproduction設定の7行が全て通過した。通常設定の追加は辞書リテラル内で新規実行文として計上されないため、LOGGING代入の実行と実handlerの動作試験で確認した。設定モジュール全体の100%網羅という主張にはしない。

生ログは専用worktreeのGit管理外 `tmp/sdk-logging-red.log`、`tmp/sentry-logging-red.log`、`tmp/sdk-sentry-green.log`、`tmp/sdk-sentry-coverage-green.log`、`tmp/sdk-settings-coverage.log` と、両coverage JSONに保持する。

## 未完了と承認境界

### 通常配布物の追加検証

製品修正のコミット `d523f964ed8c035e59d6113b50c9dfc227999605` の `git archive` を通常Dockerfileで構築した。イメージIDは `sha256:8c6552c795714beb9d1d996bf1c379729d6d1e8d317c3ef849dcc2449f4c4ac7`、ローカルタグは `tableno:release-candidate-d523f964`。ECRへのpushはしていない。

アプリの製品コード、テスト、3ロックと依存入力、entrypointの計10ファイルがGit blobと一致。ソースのbind mount・pip/pytestの追加なし、UID10001・読み取り専用ファイルシステム・外部通信なしで、通常イメージ内のSDK/Sentry・既存エラー通知・本番設定の **50テストが成功**した。50件はDjango runnerの件数で、pytestの57件・subtestsとの合算はしない。Webの起動や実Sentry宛先への送信をこの結果で実証したとは扱わない。

初回は診断用manifestに、Dockerの除外対象であるDockerfileまで含めてしまい、試験前にファイル不在で終了した。検証側の対象を実配布する10ファイルへ直し、失敗ログ `tmp/sdk-normal-runtime-tests.log` を保持して再実行した。成功ログは `tmp/sdk-normal-runtime-tests-verified.log`、構築記録は `tmp/sdk-normal-image-build.log`、ソースmanifestは `tmp/sdk-normal-source-manifest.json`。

### 残る条件

最終headのCIは[PR #8のChecks](https://github.com/sheepdog0820/iaia/pull/8/checks)で確認する。後続の検証資料だけのコミットと製品修正SHAは区別する。実AWS反映・実Sentry宛先は未確認。OS残指摘50件とTwisted RC2、Google/Stripe等の未統合修正、実サービス検証、性能・運用・復旧の必須条件も残る。

DB/移行ファイル、実データ、リソース、費用、購入有効化への変更はない。mainへの追加マージはこのPRの最終headと全必須CIを固定して承認を求める。AWS反映・共有DB0068・公開の承認を含めない。取り消しは通常のrevert PRで可能だが、この保護を戻すと元のログ問題が再発するため、復旧時にも診断の本文を残してよいとは扱わない。
