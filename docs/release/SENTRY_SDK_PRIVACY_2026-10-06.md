# SentryのSDKログ：独立収集経路でも本文を送らない

## 問題と対象

基点 `0c38583c2281f1d84514d9c2cfa27f532016e012`、専用ブランチ `codex/sentry-sdk-privacy-20261006`。[先行の通常配布物検証](SDK_LOG_RUNTIME_DC0B053E_2026-10-06.md)はstream/file/rootを保護したが、Sentryは元のLogRecordを別に読み、formatterのコピーによる要約を利用しない。既存のsend_default_pii=FalseだけではSDK本文/引数/例外値/extraの保護を証明できなかった。

Windowsにインストール済みSentry2.63.0のLoggingIntegration、event/telemetry処理・LogBatcherを読んだ。実SDK・既存production settingsのinitを通すメモリ内transportで、合成markerがevent例外値/stack local/logentry/extra/context/user、SDK breadcrumb、Logs body/parametersへ入ることを再現した。実アカウントへの送信・実Secrets流出・過去のSentry監査の証明ではない。

## 修正と境界

- 既存Sentry initへbefore_send/before_breadcrumb/before_send_logを追加。boto3/botocore完全一致・ドット子loggerだけを対象にし、botocore_other等は変更しない。Sentry自体やSDK loggingを無効化せず、DSN・traces_sample_rate・send_default_pii・Logsの既定無効を変更しない。
- SDK eventはlogger/level/時刻/release/environment等とpayloadなし診断へ置換。自由文・引数・例外値/chain・stack local・context/user/extra・任意breadcrumbを送らない。loggerと例外種別のfingerprintで分類を維持する。LogRecordがないSDKイベントは自由文を通さずgeneric診断へ落とす。
- SDK breadcrumbはlevel/category/時刻・安全な診断だけにし、後続の非SDKイベントへ本文やextraが戻ることを防ぐ。
- SDK Logsはbody/引数/任意attributesを除去し、severity/時刻/trace IDsとlogger/コード関数・行を残す。SDKのLogs hookには元LogRecord hintが来ないため、例外class/stackをLogsへ再構成したとは主張しない。それらはSDK event・通常アプリログに残る。
- SDK要約を共通化し、SDK recordのrequest/status_code extraをコピーから除いてroute等の抜け道にしない。元record/event/breadcrumb/logを変更せず、Djangoの従来request診断は維持する。

対象はSDK loggerのevent/breadcrumb/Logsである。SDK loggerとして識別できないcapture_exception・Djangoイベント、transaction/span/profiling/attachment、任意の後付け収集経路、実Sentry受信・通知までの保護を証明しない。SDKの自由文や詳細contextは意図的に送らず、SDK以外の既存監視・通知設定は変更しない。

## TDD・検証

新規9件は実Sentry SDKのinit・LoggingIntegration・scope・serialize・batcherを通す。既存settingsのinitだけをwrapしてtransportをメモリ内へ変更し、Logsを**試験内だけ**有効化する。合成DSNはexample.test、transportのcapture_envelopeはlistへ保存するだけでHTTPを行わない。実Sentry/課金/Secrets/AWS接続はない。

event/log itemsとenvelope headersを検査する。4種類のSDK logger、合成ValueError/引数/extra、scope context/user/別breadcrumb、request extra、後続の通常イベント、非SDK監視不変、hintなし/不正hint、元データ不変、欠落metadata、未知fixture mode拒否を確認した。Ignored envelope typeの分岐はメモリ内だけのcheck-in fixtureで検証し、実monitorは作成していない。

| 検証 | 結果 |
| --- | --- |
| 初回RED | 4 test/subtest failure6、9.571秒・終了1。Sentry独立経路への本文露出を再現 |
| 最小GREEN | 4成功、9.464秒・終了0 |
| 分類追加RED | 8 test/subtest error4、9.426秒・終了1。fingerprint欠落を確認して追加 |
| Windows settings回帰 | 初期8件含む68成功、53.177秒・終了0 |
| Linux settings/アクセスログ | 初期75成功、最終9件含む76成功・50.789秒・終了0 |
| 最終header検証/coverage | Windows22成功・44.899秒、Linux9成功・9.450秒、いずれも終了0 |
| Windows背景透過・画像・有料権限・文書 | 新規9件含む239件中223成功/PG専用16省略、79.366秒・終了0。使い捨てtest_db.sqlite3は終了後不存在 |
| 保護module coverage | error_reporting全体78文/16分岐100%、除外0 |
| 新規test coverage | 146文/22分岐100%、除外0。子プロセスの実SDKコードも測定・合算 |
| 品質 | Black/isort/Flake8・差分検査成功、変更Pythonの最終Bandit指摘0、追加抑制なし |
| 最終文書・ステージ検査 | 文書39件成功、相対リンク欠落0、証拠8件のSHA一致、5ファイルのUTF-8/LF検査成功 |

Linuxはdc0b053e通常イメージ（Sentry2.68.1）の依存に現在sourceをread-only mountしたnetwork none試験。新候補の通常配布物・実HTTP試験とは扱わない。76件後にenvelope headersの負例確認を追加したため、Linuxの新9件を再実行して最終header確認も成功した。今回PG試験・新OS監査は行わない。

初回BanditはfixtureのPython assertだけをB101として検出し、無効化せずTestCase.assertへ置換して再検査した。初回coverageの新testはignored envelope typeの1分岐が未通過で、上記offline check-inを追加して100%へ解消した。coverageの親プロセスにはproduction settings未importの警告があるが、子プロセスで実import/initを計測・合算しており、settings module全体やリポジトリ全体100%とは扱わない。コード位置・安定分類・元データ非変更・SDK以外不変を自己レビューし、追加指摘なし。新利用者向け文言/画面変更は0件、内部診断文は運用向け英語のためUI日本語化対象ではない。

## 証拠と公開境界

保存先 `D:/tmp/codex-tableno-sentry-sdk-privacy-20261006/`。失敗ログも保持する。

| ファイル | SHA-256 |
| --- | --- |
| red.log | ace37d73c4317fd294972c253dc4194378bba2ea064664f91778ca8d9fbb4fc8 |
| green.log | 8912b8bca9d165ae8d7a01bd09c8e426ce911aad5bca4352d268f74691e8e92c |
| fingerprint-red.log | acace8900afe88b9398a1ba01b01eab5b3b8b77207355a569b044121e095f7d1 |
| settings-regression.log | 9e47eed979047264922daaf423f747deac81ecc25a9f6f9dab7e3b8c9942871d |
| linux-settings-regression-final.log | 4afb19dbc585ada33b42867b3fd244f1a46b0b54bd49dd0fb022a3e96d0251be |
| linux-headers-final.log | d69a57f82ee967cd1409ec141f7274e6650bfcca40e70c545d1e90728d174da3 |
| sqlite-background-regression.log | 679a7fcbe64bdab2e21aef4606db5a08e6b954d08bd9cfe1ce1b4df3d21a4bdc |
| coverage-headers-final.json | 84e91b61e391258964b5e72efd9c72d432c0c5f916a7ef2d94da816210a66cf9 |

先行dc0b053eの[CI37397258941](https://github.com/sheepdog0820/iaia/actions/runs/37397258941)はhead SHA一致・全6項目successを後続照合した。今回の修正には引き継がず、新候補CI/通常配布物/実HTTP・PG・実Sentry受信は未確認。最新OS監査HIGH3は未解消で正式公開No-Goを維持する。

変更はerror_reporting.py・settings_production.py・新規test・本記録・受入表の5ファイルだけ。main読み取り照合8567f49f、main/AWS/共有DB/Secrets/IAM/容量/契約/外部通知は操作せず、既存アイコン承認へ追加しない。元checkoutの無関係13項目は保持する。復旧する場合は対象修正の通常revertを使い、共有反映するなら対象・稼働版・復旧定義を別途承認範囲で確認する。
