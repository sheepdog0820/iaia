# SentryのHTTP診断・性能トレースの情報保護（2026-10-28）

## 問題と対象

正式公開はNo-Goを維持する。[SDK保護のPR #8](https://github.com/sheepdog0820/iaia/pull/8)のhead `35e259855792d7358ebaccc26716030de99072ee` を基点に、別ブランチ `codex/sentry-request-privacy-20261028` で追加の問題を調査した。承認を確認中のPR #8のコミットは変更していない。ICS・運営コードの後続とはコード依存がなく、当初のPR baseはSDKの作業ブランチとする。

通常のDjango HTTP 500では、SDK loggerを通らずDjangoIntegrationから直接イベントを送る経路がある。この経路とsecurity loggerでは、HTTP本文・URL・例外メッセージ・フレームの変数・追加contextがSentryのenvelopeに残ることを、実SDKで再現した。`send_default_pii=False` や標準出力のsafe formatterだけでは、この送信経路を保護できなかった。

全て合成データの検証で、実Sentryへの送信をoffline Transportと外部通信遮断で止めた。実ユーザー情報や実Secretsを読み取った調査ではなく、既存の実ログに漏えいがあったことを確認した記録でもない。

## 修正

- HTTP requestの文脈、Django例外mechanism、`django.request` / `django.security*`、request付きLogRecordを識別する。DjangoIntegrationがloggerを経由しない場合も保護する。
- 本文・引数・例外値・ソースcontext/変数・request/user/extra/context/breadcrumb等を残さず、識別用metadataと例外型、発生ファイル・行・関数を記録する。requestがある場合の既存の安全なroute/method/statusの扱いも維持する。
- 実Python例外のhintがある場合は型だけを再構築し、既知のDjango/logging mechanismの処理済みboolを保つ。未知の機構はlogging扱いへfallbackし、元の任意dataを残さない。例外本文を省き型だけを持つ形式は[公式Relay schemaとroundtripテスト](https://raw.githubusercontent.com/getsentry/relay/master/relay-event-schema/src/protocol/exception.rs)でも確認した。
- security/requestのbreadcrumbとLogsも本文や追加dataを省き、元のrecord・event・breadcrumb・logを破壊しない。
- SDKの既存保護と対象外の通常診断を維持する。送信先や `enable_logs` の製品設定、Secrets・権限・保持期間は変更しない。テストでのみLogs収集を明示的に有効にして境界を検証する。

診断の詳細は減る。例外値・変数やソース行をSentry UIへ出さず、例外型と位置は安全な要約として残す。Pythonのhintがない場合は例外型を元payloadから推測せず、省略した診断にする。

## 検証

Python 3.11.18 / Django 5.2.17 / sentry-sdk 2.68.1の固定依存。使い捨て設定のDockerでソースを読み取り専用に置き、外部通信なし、実SDKのTransportだけをofflineの捕捉先へ置き換えた。HTTP試験は実Django handlerで合成の本文/URL/例外を使う。DB・認証middlewareや実業務エンドポイントの全体試験とは区別する。

1. 最初の再現は3失敗・1成功。その後request付きアプリlogger・breadcrumb・hintなしを含む回帰は18失敗・3成功・5 subtests成功（失敗数にはsubtest失敗を含む）。空の送信内容で成功扱いにせず、実envelopeの存在・500応答・実例外型を確認した。
2. 本文だけを省く最小実装で、未処理/処理済みの区分まで失うことも回帰として検出した。型と安全なmechanismを残す修正後、関連6ファイルの **65テスト・79 subtestsが成功、省略なし**。
3. isort/Blackで対象2ファイルだけを整形し、同じ試験を再実行して65テスト・79 subtests成功。診断モジュールの **124実行文・34分岐とも未通過0、100%**。製品全体や全入力の100%網羅ではない。
4. SDK診断、管理者メール、標準出力・ファイル、本番設定、HTTP/WebSocketアクセスログの回帰を含む。新しいアプリUI文言はなく、追加の英語は運用診断用の技術文字列である。

ログはGit管理外 `tmp/sentry-request-red.log`、`tmp/sentry-request-current-red.log`、`tmp/sentry-request-mechanism-red.log`、`tmp/sentry-request-metadata-red.log`、`tmp/sentry-request-formatted-coverage.log`、`tmp/sentry-request-coverage/coverage.json` 等に保持する。

## 未完了と承認

### 通常配布物の追加検証

製品修正 `8302068ef276469c1ee15e33ea739d9f4e709806` の `git archive` から通常Dockerfileで構築した。ローカルタグは `tableno:release-candidate-8302068e`、イメージIDは `sha256:0744c6d3019d73a4d9130757e58cf2771eae3e169f0a1c1fdd3055cf7c6b06e6`。ECRへのpushは未実施。

製品コード・固定依存・テスト・entrypoint等15ファイルのGit blob一致と、実entrypointの一致を確認した。ソースのbind mountやpip/pytest追加なし、UID10001・読み取り専用・外部通信なしで、通常イメージ内のDjango runnerでも同じ6モジュールの **65テストが成功、省略なし**。pytestのsubtests件数との合算はしない。実SDKのenvelopeはofflineだけで捕捉しており、実Sentryの受信や実業務のHTTP操作を代替するものではない。

構築・実行・ソース照合の証跡はGit管理外 `tmp/request-privacy-normal-image-build.log`、`tmp/request-privacy-normal-runtime.log`、`tmp/request-privacy-normal-source-manifest.json`。後続の検証資料だけのコミットと、製品修正SHAは区別する。

### 性能トレースの追加調査

HTTPエラーの保護とは別に、既存の `traces_sample_rate` の対象となる性能トレースも調査した。Django TestClientだけではWSGIのtransaction計測を通らないため、実 `WSGIHandler.__call__` とSDKのoffline Transportで500要求を実行した。実transactionが1件存在することを確認した上で、本文・URL・追加contextに加え、子spanのSQL説明・任意dataにも合成文字列が残る回帰を検出した（`tmp/sentry-http-trace-red.log`）。この記録は外部送信や実ユーザーデータの調査ではない。

`before_send` はtransactionを処理せず、別の `before_send_transaction` を設定する必要があることを、固定版の[公式SDK実装](https://raw.githubusercontent.com/getsentry/sentry-python/2.68.1/sentry_sdk/client.py)でも確認した。HTTP requestまたは `http.server` のtraceを対象に、送信前の許可リストでrequest/user/extra、任意context・tags・measurements、spanの説明/data等を省く。処理時間、trace/span/親spanのID、操作種別・生成元・処理結果は残す。安全なroute/componentをtransaction名に使い、生URL由来や名前不明の場合は固定名にする。span自体を全て捨てて成功扱いにはしない。必須のspan ID・trace ID・開始/終了時刻は[公式Relay schema](https://raw.githubusercontent.com/getsentry/relay/master/relay-event-schema/src/protocol/span.rs)と照合した。

サンプリング率・送信先・Logsの製品設定を変更せず、HTTP以外のtransactionは維持する。SQL・外部通信先・任意タグ別の詳しい解析はできなくなるが、処理時間と操作ごとの内訳を保持する。profileや別のworker診断の保護をこの修正だけで合格にしない。追加の最終検証と通常配布物は以下の追記で区別する。

追加回帰の修正前は実transactionの情報残存を含む4テストが失敗した。修正後は関連6ファイルの70テスト・86 subtestsが成功、省略なし。診断モジュールは141実行文・38分岐とも未通過0、100%。実transactionが1件あり、開始/終了時刻が異なり、DBの子spanが存在し、合成本文が全捕捉内容から消えることを確認した。hook単体ではHTTP以外の維持、route/componentの保持、生URL・名前不明の固定名、元event不変、任意の追加フィールド除外も確認した。証跡は `tmp/sentry-http-trace-hook-red.log`、`tmp/sentry-http-trace-green.log`、整形後の `tmp/sentry-http-trace-formatted.log` と `tmp/sentry-request-coverage/coverage.json` に保持する。

### 残る条件

今回の最終CIは[Draft PR #11のChecks](https://github.com/sheepdog0820/iaia/pull/11/checks)で照合する。実Sentryの受信画面は未確認。profile、requestの文脈を持たない別のアプリ診断やworkerの経路も引き続き監査する。Q04全体や正式公開のGo条件をこの結果だけで合格にしない。

DB/移行、依存ロック、実データ、Secrets/IAM/OAuth、常設資源・費用、外部通知への変更はない。SDKの先行PRマージ後にbaseをmainへ変更し、最終head・差分・CIを固定して、この追加修正のマージを別途承認してもらう。共有DB・AWS反映・公開の承認に拡張しない。取り消しはrevert PRで可能だが、HTTP診断の本文・変数が再び残るため、それだけで公開可とはしない。
