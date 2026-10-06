# 背景透過：再試行途中の署名失敗でも入力を誤削除しない

## 問題・対象

基点は `30bc083091df51038f80599def78a5d46a9c67fe`、専用ブランチは `codex/background-signing-outcome-20261006`。[先行の再試行後ClientError対応](BACKGROUND_RETRY_OUTCOME_2026-10-06.md)は最終ResponseMetadataのRetryAttemptsを使ったが、初回timeout/500の後、次の署名用資格情報取得が失敗すると最終ECS応答自体がなく、Webがpending jobをfailedにして元画像を削除していた。

インストール済みboto3/botocore **1.43.34** のendpoint/signers/hooksを読み、各再試行で署名を作り直す順序と `needs-retry.ecs.RunTask` の引数・登録解除を確認した。[AWSの冪等性説明](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_Idempotency.html)は、timeout/server障害が資源変更後に起き得ると説明する。この情報から、後続のローカル署名失敗だけでは先行受理を否定できないと判断した。実AWSでその障害順序が起きた証拠ではない。

## 修正・受け入れ条件

- RunTask一呼び出し内のSDKイベントを先頭で観測し、通信例外、5xx、ServerException/ConflictExceptionのいずれかを受けたら「先行の結果不明」を保持する。callbackはNoneを返し、SDKの再試行判断・回数・backoffを変更しない。必ずfinallyで同じhandlerを解除する。
- 先行結果不明の後の署名/資格情報取得例外は、既存のBackgroundRemovalDispatchUncertainへ分類する。資格情報更新先のClientErrorにRetryAttempts=0があっても、先行ECS結果を確定失敗へ変えない。
- 結果不明の先行試行後にHTTP200・tasksなし・明示failuresを受けた場合も、最終応答だけで入力を削除しない。初回の明示failuresは既存の確定失敗503を維持する。
- 初回署名/資格情報取得失敗、明示的スロットリング後の署名失敗には、この先行結果不明がないため既存503・入力削除を維持する。成功task ARN保存、通常400/403、最終RetryAttemptsによる先行の保護も維持する。
- Webの最新job行ロック処理・既存202/job ID・source/status/error/updated_at保持へ戻す。202は起動確認済みではない。重複POSTは409、遅いworkerは入力を処理可能、未確認jobは既存timeoutで終端化する。
- 新しいアプリ再送、別token、timeout延長、quota/料金/権限変更、DB schema/モデル変更を加えない。実際には受理されていなくても保守的にtimeoutまでpendingとなる場合がある。

## TDD・回帰

新規14件は実SDKのserializer/signing/retry/parserを通し、最下位送信だけを合成応答へ置換する。資格情報取得の2回目にNoCredentialsError/RuntimeError/更新先ClientErrorを注入し、実署名イベント1/2回・wire送信0/1回・最終after-call未発生を観測する。Conflict後の署名ケースだけは試験専用retry callbackで再試行を起こすため、SDKの標準Conflict再試行を証明しない。HTTP200の明示failuresは初回/timeout後の両方を確認する。

同一job UUIDのclientTokenと全parameters、handler登録一覧の前後一致、backend詳細ログ非露出、重複409・遅い合成PNG worker完了/非公開結果、既存timeout/遅い推論抑止を確認する。APIClientの既存認証fixtureであり、実HTTP/実Token・実IAM/資格情報更新・実AWS/S3・実U2NETの追加証明ではない。

| 検証 | 結果 |
| --- | --- |
| 初回RED | 17件中6 failure。importした既存TestCase8件も重複発見されたためmodule aliasへ訂正し、以下の9件で再確認 |
| 訂正後RED・新規9件 | 6 failure/3成功、0.681秒・終了1 |
| 最小GREEN・新規9件 | 全9成功、0.605秒・終了0 |
| 明示failures追加RED・12件 | 1 failure/11成功、0.786秒・終了1。timeout後503を再現 |
| 初回GREEN回帰・12件含む | Windows SQLite206成功/PG専用16省略（83.741秒）、隔離PG222成功/省略0（64.336秒） |
| 資格情報更新先ClientError追加RED・14件 | 1 failure/13成功、0.967秒・終了1。先行timeoutを見落とす503を再現 |
| 最終Windows SQLite回帰 | 新規14を含む224件中208成功/PG専用16省略、66.008秒・終了0、in-memory TEST DB |
| 最終隔離PostgreSQL回帰 | 同じ224件すべて成功/省略0、64.194秒・終了0、既存実PG lock16件を含む |
| 変更起動関数＋observer coverage | 45文/12分岐＋5文/4分岐、すべて100%、除外0 |
| 新規test module coverage | 147文/14分岐100%、除外0 |
| tasks module全体coverage | 200/204文・63/64分岐。旧cleanupの未通過4文を含み、全モジュール100%とは扱わない |
| 品質 | Black/isort/Flake8・差分検査成功。最終Bandit指摘0、合成署名値だけのB106限定注釈1件 |

callback観測と最終例外分類の関係、初回の確定失敗、登録解除・期限・権限・最新行優先を自己レビューし、上記の追加2ケースを修正した。unusedなafter-call callbackをMockの未呼び出し検証へ整理し、テストの未通過1文を解消した。新規利用者向け文言は0件で、既存英語エラーの翻訳完了とは扱わない。画面/ブラウザー検証は今回行っていない。PG CIの明示対象へ新規moduleを追加し、待機上限・retry・合格条件は緩めていない。

## 隔離・証跡

Linuxは通常ba51bdd8 image `sha256:1e5d3114e2c23473fc1bcce06273aeca65d71811a89fea878b07294e98f49e11` に今回sourceとcoverage 7.15.4のみread-onlyで重ねたpytrace計測。root read-only、1 CPU/512 MiB、一時/tmp/media、PG namespace以外へ通信不可。SDK/アプリ依存の差替え・追加インストールはないが、今回commitの通常配布物同一性の検証ではない。

PG18.3 image `sha256:fbaa243599038521bbda8f6fa286d2a8fc1236509606f22de81d0739b0610ba7`、固有DB/user、network none・公開portなし、256 MiB/512 MiB tmpfs。終了後test DBなし・基点DB public table0を確認し、名前/ID/network/ports/tmpfsを照合した専用コンテナ `af74547699bb79f47753e20e2040c22ef0c8ae4fb41ed4d990cb7f406a29dc9d` を停止・削除した。検証アプリは--rm終了済み。Windows初回RED/GREENは専用test_db.sqlite3、最終回帰はメモリDBで、いずれも使い捨て合成データだけ。実データや共有DBへ接続していない。初回Windows回帰stdoutの文字コードを最終実行ではPYTHONIOENCODING=utf-8で明示した。ソースを文字化け回避目的で書き換えていない。

証跡は `D:/tmp/codex-tableno-signing-outcome-20261006`。初回・途中・最終のログを別名で保持し、過去の証跡/cache・他作業コンテナを削除していない。

| ファイル | SHA-256 |
| --- | --- |
| red.log | 480cfcee2f07bccbded4e2d868c4f5319377866767271fc707d71d4d2e2685af |
| red-nine.log | 0e1ced2a3471dd1be468c05bf5f74c605b0b4f81db7169823447f5672965b48f |
| red-explicit-failure.log | 9fbcb1bc5e81867972cf31662c53b62dc3183a8e57e05a932fd4ba31f75ba64e |
| red-credential-client.log | cb6dabf3ddd4ee4c9f4fdb2525fed69c3a554e5f3014e27f765253cabe9abb71 |
| sqlite-reviewed.log | 938ffa4ff01f8867525e51d739b029443f5a325edd9ac48b4c9628aab7d71810 |
| postgres-reviewed.log | 860db4ea9a91bee29e967f57fc3751e3323f49b4a85b08393d8224b96612ce1f |
| coverage-postgres-reviewed.json | 15a00c3733dd58a8bc0f21bcc1b3b75d5143cfd145c74e8d6b5882b13251cec6 |
| coverage-sqlite-reviewed.json | a6fa966a84d44e02abe66390348dc8d6a3249b717226c020930d997b381dda33 |
| bandit-reviewed.json | b4f56e5febbb1912aa14666d528dd03fd5de6014759b84719fdb14e9849976de |
| run_isolated_tests.py | eab32f16346a1dc62870676026a047ec54a9f397c5a991c797cd1288ec3b17f4 |

## 影響・未完了

文書追記後の関連39 test成功（0.036秒）、変更文書の相対参照203件/欠落0、上表10ハッシュ一致。ステージ対象5ファイルのUTF-8/LF/BOMなし・差分検査も成功した。実差分と日本語表示への影響をレビューし、追加修正を要する指摘なし。

今回候補の全CI・通常配布物・実HTTP/実AWS/S3・実課金/常設worker/外部連携・性能/復旧/事業者条件等は未証明。設定変更をまたぐ再送parameters永続化/outbox、token TTL超過のexactly-once、孤立task/画像回収・DB/storage分散原子性も今回の範囲外。新しいOSスキャン/依存更新はなく、最新通常ba51監査の39指摘（HIGH3/MEDIUM1/LOW35、Python0）・終了2を解消/受容済みにはしない。[正式公開条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)は **No-Go** を維持する。

main/AWS/ECR/ECS/S3/CloudFront、共有DB/実データ、Secrets/IAM・課金/メール・容量/継続費用は変更していない。既存main/AWS承認へこの後続修正を追加しない。元checkoutの無関係な13変更は保持した。復旧は作業ブランチのrevertで可能だが入力誤削除を再導入するためfix-forwardを優先する。
