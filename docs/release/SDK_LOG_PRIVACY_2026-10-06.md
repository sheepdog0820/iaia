# AWS SDKログ：資格情報応答本文を出力しない

## 問題と変更範囲

基点は `2f6558675e6fff7d68f2b45aafb78b28cb5f7f5c`、専用ブランチは `codex/sdk-log-privacy-20261006`。[先行の通常配布物検証](BACKGROUND_SIGNING_RUNTIME_B3496898_2026-10-06.md)で、botocoreの資格情報更新警告が合成応答本文をrootログへ出すことを観測した。実Secretsの流出・過去のCloudWatchログ監査を意味しない。

- `SafeRequestFormatter`の既存のpayloadなし要約を、完全一致のboto3/botocoreとそのドット区切り子loggerにも適用する。任意のmessage/args、例外本文・chain、cached traceback、stack_infoを出さず、時刻・logger・level・例外class・コード位置を残す。元のLogRecordは変更しない。`botocore_other`等の無関係loggerは対象外。
- 開発/本番settingsにSDK専用の安全なhandler経路を追加し、SDKからrootへの生の伝播を止める。loggerはNOTSET・disabled=falseで、サーバーのroot verbosityを継承する。WARNINGをERRORへ引き上げたりSDK loggingを無効化したりしない。
- 本番は既存のstream/file選択に従う。両方無効の場合だけ、従来rootへの出力に代わる安全なStreamHandlerを使う。既存fileのINFO閾値・場所・rotationは変更しない。DEBUGはstream有効時に確認した。
- SDKにmail_adminsを割り当てず、新しいメール通知を追加しない。既存Django/request/allauth/tablenoのhandler・レベル・メール、アクセスログ処理、SDK再試行・認可・課金・DB schemaは変更しない。

任意に後付けされたhandler、SDK以外のlogger、Sentry等の独立した収集経路までの保護を証明する変更ではない。SDKの自由文診断は意図的に要約へ置き換えるため、資格情報更新のmandatory/advisoryという元の文面自体はログに残さない。

## TDD・検証

新規6件は、実botocore 1.43.34のRefreshableCredentialsを通す。合成callbackがMetadataRetrievalErrorをchained ValueErrorから発生させ、mandatory時は例外継続、advisory時は旧資格情報維持というSDKの挙動を変えず、どちらのWARNINGも安全に出力する。AWS/ネットワークには接続しない。

子プロセスでサーバー相当のroot handlerを先に作り、Djangoのconfigure_loggingと実settingsを適用する。設定前に存在する子logger・設定後の子logger、stream/fileの4組合せ、WARNING/INFO/DEBUGのverbosity、boto3 ERROR、DEBUGのAuthorization引数、メール呼び出し0、通常root logger不変を確認した。

| 検証 | 結果 |
| --- | --- |
| 訂正後RED | 新規6件、subtest failure 16、16.577秒・終了1。SDK本文露出を確認 |
| GREEN | 新規6件全成功、13.568秒・終了0 |
| Windows settings回帰 | 60成功、41.817秒・終了0。DB不使用 |
| Linux settings/アクセスログ回帰 | 67成功、41.612秒・終了0。network none、read-only、DB不使用 |
| Windows背景透過・画像・有料権限・文書回帰 | 230件中214成功/PG専用16省略、67.815秒・終了0。専用checkoutの使い捨てtest_db.sqlite3は終了後不存在 |
| 最終SDK/文書確認 | 45成功、13.576秒・終了0。合成metadataへの限定注釈後 |
| formatter coverage | error_reporting全体39文/10分岐100%、除外0 |
| 追加本番経路coverage | 6実行文/4分岐すべて実行、未通過0 |
| 新規test coverage | 93文/12分岐100%、除外0。子プロセスの実SDK callbackも合算 |
| 品質 | Black/isort/Flake8・差分検査成功、変更Pythonの最終Bandit指摘0。offline合成metadataの2箇所だけB105注釈 |

初回は既定ENV_FILE不在、次はSECRET_KEY不在で起動前に失敗した。合成環境に訂正した最初のREDでは、productionに非対応sqliteを指定した検証側失敗も混じったためpostgres設定importへ訂正し、上記REDで再確認した。接続・DB作成は行っていない。

初回Windowsの広いsettings回帰は60成功と既存Daphne/Twistedのimport error 1。既存依存を変更せず、同じ試験をLinuxでも実行してアクセスログ7件を含む67成功を確認した。Linuxは既存b3496898イメージ `sha256:babec53b6deefe4be6e2c524ee31a74f146d5944f5c18134af87b02a69bd1662` の依存に現在のsourceをread-only mountした試験であり、新候補の通常配布物試験ではない。Windows背景回帰の既存print出力には端末エンコーディング由来の文字化けがあるが、ソースは変更していない。初回全成功とは報告しない。

coverageは外部harnessでPython settings probeも計測・合算した。settings全体の過去未通過コードは残り、リポジトリ全体100%とは扱わない。追加のtest Banditはoffline合成metadataのsecret/token文字列2件を検出したため、その2行だけ理由付きB105注釈を付けて再検査した。実キーではなくネットワークclientも作らない。自己レビューでrootへの二重出力、logger名の境界、cached例外本文、メールfallback、元recordの変更、既存handlerの回帰を確認し、追加指摘なし。利用者向け文言変更0件、ブラウザー検証なし。

## 証拠と反映境界

証拠は `D:/tmp/codex-tableno-sdk-log-privacy-20261006/`。失敗ログも保持する。

| ファイル | SHA-256 |
| --- | --- |
| red-corrected.log | 13c37bdb23b99a9397f6aa8dfa1a0fdffea6c924e04b185c14f4071e0ac29901 |
| green.log | 669d2bd38f9e118049f51407f571d1ea2aeaa0621fa1b7e6749921eaee33bfe8 |
| windows-settings-regression-corrected.log | 8623638d29985dc9d7b69a963b772b291cee8e47124aac5d91a22bf723d4f637 |
| linux-settings-regression.log | 92126c189ed011b10db52afad62c55b61df5e45811e28ee45088f5992fda554a |
| sqlite-background-regression.log | 1f621a685f42d41c86b7c84067356531ad0db8c27fc7af16406a0adfdb6cbbab |
| coverage.json | 250306e5b95b0b9f5f579521bc16b8c7eac9051f1b352fb283ceb56ce1c24030 |

対象はerror_reporting.py・settings.py・settings_production.py・新規unit test・本記録・受入表の6ファイルだけ。通常配布物の再構築、実HTTPでのSDK警告再現、今回のPG/CI全項目は未確認。次に固定コミットの通常イメージで先行の資格情報HTTP障害を再検証する。

mainは読み取り照合で8567f49fのまま。今回main/AWS/共有DB/Secrets/IAM/容量/契約/外部通知は操作せず、既存のアイコン承認へ追加しない。元checkoutの無関係13項目は保持。OS再監査なし、最新HIGH3は未解消で正式公開No-Goを維持する。復旧が必要な場合は作業ブランチの対象修正を通常revertし、共有反映するなら別途対象承認・稼働定義確認を行う。
