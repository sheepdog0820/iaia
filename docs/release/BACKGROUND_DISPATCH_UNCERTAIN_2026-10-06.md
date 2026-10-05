# 背景透過の起動結果が不明な場合の入力保持

## 対象・修正理由

基点は証拠コミット `a97f07b0ed6007b4d93118408c8cc654c69170ef`、作業ブランチは `codex/background-dispatch-uncertain-20261006`。[先行起動競合修正](BACKGROUND_DISPATCH_INTEGRITY_2026-10-05.md)はworkerがrunning/completedへ進んだ場合を保護したが、ECSが受理した可能性のある通信障害の後もpendingだった場合は、Webがfailedへ変更して元画像を削除していた。これでは応答だけ失われ、遅れて起動したworkerが正常に処理できない。

[AWSの冪等性仕様](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_Idempotency.html)は、変更後にtimeout/server例外を返す可能性、同一token・同一parametersでの再試行、SDKの自動token生成、tokenの有効期限を説明している。インストール済みbotocoreのRunTask modelは `idempotencyToken: true`、handlersの生成処理も確認した。従来のSDK内再試行にtokenがなかったとは扱わない。[RunTask仕様](https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_RunTask.html)のConflictExceptionは既存tokenと異なるparametersの競合で、既存taskが存在し得る。新tokenで再起動する修正は行わない。

## 変更範囲

- job UUIDをRunTaskのclientTokenに明示する。同じjob/parametersの呼び出しは同じtoken、別jobは別token。API呼び出し・アプリ再試行の追加やSDK retry設定の変更はない。
- RunTask中のHTTP/接続/response parse例外、5xx・ServerException・ConflictException、不完全な成功応答、受理後のtask ARN保存におけるDB例外を専用の「結果不明」例外として扱う。SDKの最後の接続障害だけでは、それ以前の試行で受理されていないと断定しない。
- 結果不明の場合は所有者付き行ロックで最新状態を取得する。pendingのstatus/source/error/timeを保持し、既存のjob ID/status URL付き202を返す。running/completed/failedと削除済み行も最新状態を優先する。task応答にfailuresが含まれていても実際に受理されたtaskがあればARNを保存する。
- 明確な設定不足・資格情報不足・parameter/権限エラー・taskなしの明示failureは従来どおり503/failedと元画像削除。既存のactive job拒否・日次上限・timeout/retention・所有者制限は変更しない。
- dispatchログはjob UUID・例外型のみで、raw exception、endpoint、応答本文、tracebackを出さない。新しい利用者向け英語文言は追加していない。既存の未翻訳error文言は今回の翻訳完了とは扱わない。

tokenの有効期限後・別cluster・parameters変更を含む永続的なexactly-onceを保証しない。設定変更をまたぐ再送のためのparameters永続化/outbox/自動reconcileは未実装。今回の202は「起動確認済み」ではなく、結果不明のjobが既存pollingで確認可能という意味である。受理されていなければ既存timeoutで失敗する。通常の既定値は900秒、テストfixtureは60秒で、期限を延長していない。

## TDD・隔離検証

| 検証 | 結果・範囲 |
| --- | --- |
| 初回RED | 新規10 test、7 failure/10 error/PG専用1 skip。subTest後の清掃が失敗assertで実行されず、次ケースへ行が残る補助テスト問題も含む |
| ケース隔離後RED | 同じ10 test、15 failure/1 error/PG専用1 skip。画像削除・503とtoken欠如を再現。errorは未実装clientToken参照で、成功扱いしない |
| 最初のSQLite GREEN | 関連132 test、120成功/PG専用12 skip、14.621秒 |
| 最終SQLite | SDK実行経路等を追加後の136 test、124成功/PG専用12 skip、15.623秒、終了0 |
| 隔離PostgreSQL | 同じ136 test全成功/skip0、19.272秒、終了0 |
| 変更関数coverage | `start_background_removal_task` 35文/10分岐、`CharacterImageBackgroundRemovalView.post` 44文/18分岐、合計79文/28分岐100%、除外0 |
| 新規テストcoverage | 新規14 test（SDK3、実PG lock1を含む）、267文/22分岐100%、除外0 |
| 品質 | Black/isort/Flake8、差分空白検査成功。変更source2ファイルのBandit指摘0・終了0 |

関連対象は新規dispatch uncertain、先行dispatch/finalization/retention、`accounts.test_character_background_removal`、モデル/infrastructure単体、release文書テスト。同じ入力のworker後続完了・PNG取得、2回目POSTの409とRunTask追加なし、未起動jobのtimeoutと遅いworkerの推論抑止、latest terminal/deleted state、確定失敗のcleanup、backend詳細ログ非露出も検証した。

SDK3ケースは実際のbotocore client/serializer/signing/retry/parserを使い、最下位 `_send` だけを合成応答/timeoutへ置換した。2試行のtoken保持→成功ARN保存、2試行が尽きた後もpending/source保持とアプリ再起動なし、400の1試行だけで確定失敗を確認。retry backoffのsleepだけを置換し、実AWS通信・実受理・課金の証拠にはしない。

PG lockケースはWeb側を別DB connection/threadで動かし、最新completed行を保持するtransactionへの実際の待機を `pg_blocking_pids` で確認した後に解除する。5秒の観測上限や合格条件を緩めていない。返却completed・result参照・完了時刻を確認した。

PG18.3は固有の合成DB/user・network none・256MiB・tmpfs。検証コンテナはそのnetwork namespaceを共有し、sourceをread-onlyで重ねた先行通常image `tableno:background-retention-7106f6fb`（ID `sha256:86f4a3a7b76c2e657e8b5eab43242b11f4dec1362513bc1a7ae120be46e3d68a`）を利用した。coverage計測用moduleもread-only overlay、pytraceであり、この候補の通常配布物同一性/overlayなしruntimeの証明ではない。外部通信、共有DB、S3、実modelは使わず、source/testmediaは一時領域。自作PGコンテナ `2c7c0a9f859c5c44ef905f42064420ab15ad377b187938a43fc72c4111012574` は名前・network/tmpfsを照合して停止・削除、tmpfsDBを破棄済み。元checkoutのハンドアウト関連13変更は保持した。

## 証拠・CI・残課題

証拠ルートは `D:\tmp\codex-tableno-dispatch-uncertain-20261006`。以下はSHA-256、小文字表記。

| ファイル | SHA-256 |
| --- | --- |
| red.log | `9f17aed7907d461fcf6117dd72d5698268c88ae2e02d5b7fd86862edf4dd17fc` |
| red-isolated.log | `1dc2bf3e25129a1b8f3f28de12879f5deac19fe966326abe007936f1b1ec7bb3` |
| green-sqlite.log | `28517f7e98a969886c549d8bf1fe83c6397a7065c220663aa77da7830f336502` |
| sqlite-final.log | `8bd77f8ad3aa949f9b742eefc8a180385e7e67010894ab2eeee441639dc3cf52` |
| postgres-green.log | `1991ad9ab1804f267925f735c0fe25af61c5711200668c58d555ea75ecb9a430` |
| coverage.json | `fdfff597f7007d7eddba4fbd5301b6b45144bfaf98aceeb102ea560f8f87bb48` |
| bandit.json | `7205db8d7bbd7f7a559c4c54717f62512d9efe0831da450960a55ee8c763d951` |

親a97f07b0の[CI 37375521876](https://github.com/sheepdog0820/iaia/actions/runs/37375521876)は今回の読み取りでLint/Infrastructure/System/Production Database成功・Playwright実行中、Unit/Integrationはfailure。job111983127661のログはpytest59%付近でrunner shutdown signal/operation canceledを示し、完了した全pytest結果はない。source assertionの失敗と断定せず、全CI成功とも扱わない。同じrunを勝手に再開始していない。今回候補のCIはpush後に別の固定SHAで確認する。

通常配布物・実ECS受理/通信/S3・DB/storage間の分散原子性・孤立task/画像回収・AWS性能・常設worker運用は未証明。先行全OS監査のHIGH3を解消/受容済みとはしない。課金実運用・外部連携・性能/復旧・事業者条件等を含む[正式公開条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)は **No-Go** を維持する。

main/AWS/ECR/ECS/S3/CloudFront・共有DB/実データ・Secrets/IAM・実課金/メール・容量/継続費用は今回変更していない。完了済みアイコン8567f49fの承認や固定6b6c570cの反映案へ追加しない。DB schema変更なし。未反映のため実環境切戻しは不要で、作業ブランチの修正はrevert可能だが、元画像を誤削除する不具合を再導入するためfix-forwardを優先する。
