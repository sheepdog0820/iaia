# Google共有実行権: 通常配布物でのPostgreSQL停止・再起動

## 対象と公開判断

2026-10-08。固定候補は `7e70368b75ff17eb2ad0361291f95ca52b904d37`、記録用ブランチは `codex/google-db-restart-20261008`。[保存SQLの前後での実DBエラー](GOOGLE_DB_BOUNDARY_FAILURES_2026-10-08.md)に続き、DB接続が実際に失われた後も未解決の送信を再実行しないか検査した。**正式公開はNo-Go**。今回のリポジトリ変更は記録のみで、製品コード・schema・依存・画面・公開設定は変更しない。

先行 `b348b06a` の[CI37788447885](https://github.com/sheepdog0820/iaia/actions/runs/37788447885)はhead一致・全6ジョブsuccessを確認した。候補7eの[CI37790973338](https://github.com/sheepdog0820/iaia/actions/runs/37790973338)は23:39頃の5成功/Playwright実行中から、後続の読み取りでhead一致・runと全6ジョブsuccessを確認した。これは固定候補7eの成功であり、今回の文書commitのCIとは区別する。

## 固定配布物と隔離条件

通常Dockerfileを候補7eのGit archiveから構築したimageは `sha256:8f2856941ba6763d7884e43e7b4794efe52d0ee0f68f8f0e0e07bdfe814e6c0b`。revision labelは候補の完全SHA。選定733 source/assetsはarchiveとのSHA-256不一致0、111 Python packages、通常entrypointのbyte一致、pyc 0。先行の通常修正imageとの選定差分は `schedules/test_google_target_execution.py` だけで、製品ソース・依存10層・package版は同一だった。選定733件を全配布file数としない。ECRへpushしていない。

アプリは通常entrypoint・非root・read-only・cap drop/no-new-privileges。sourceを `/app`や `/workspace`へoverlayせず、診断script/logだけをread-only `/evidence`へmountする。developer env/Secrets/S3/実メール・起動時migration/collectstaticは無効で、利用者・token・データは全て合成。

Redisを専用network noneのanchorとし、PG/アプリ/providerはそのnetwork namespaceのlocalhostだけを使う。ホストportや外部経路はない。Redisは128 MiB/1 CPU・read-only・tmpfs・永続化なし。PG18.3は固定image `sha256:fbaa243599038521bbda8f6fa286d2a8fc1236509606f22de81d0739b0610ba7`、512 MiB/2 CPU・read-only rootで、**合成DBだけの専用Docker volume一個**を使う。tmpfsだけではcontainer停止後の保持を検査できないための一時volumeで、既存volumeや実ユーザーデータを再利用しない。通常アプリは1 GiB/1 CPU、回帰processは2 GiB/2 CPU。

実API受付、PostgreSQL、Redis、Celery、Requestsを使用する。Google URLは許可したCalendar/Sheets URLだけをloopback模擬providerへ置換する。送信前INTENT保存の外側、または実HTTP200の返却後・receipt保存の外側でdiagnostic gateを入れる。gateはDB transactionを保持せず、controllerの明示resumeを待つ。これは無改変の実Google通信ではない。外部適用は模擬providerの適用カウンターであって、実Googleの適用証拠やexactly-once保証ではない。

## 実PG停止と復帰の8ケース

solo/prefork × Calendar/Sheets × 以下2境界 = 8ケース。実行期限は停止時も復帰時も未来、時計・期限注入なし。

| 境界 | 停止前のrequest | 模擬HTTP / 適用 | PG復帰後の禁止 |
| --- | --- | --- | --- |
| INTENT保存前 | 行なし | 0 / 0 | 実行権だけでも後続送信を止める |
| HTTP200後・receipt保存前 | INTENT一件、status/received_atなし | 1 / 1 | 応答済みでも保存できなければ未解決を保持 |

caseごとにjob/journal/request/allocation/target/dispatchの全行を読んでfingerprintを保存する。PGの完全ID/name/label/image/network/専用volume/live stateを照合し、**PGだけ**をKILLする。exit137・OOM false・停止を確認してから同じworkerのgateをresumeした。workerのタスクは実DB接続のOperationalErrorでRedis結果FAILUREとなり、その間PGは停止したまま、worker containerは生存していた。workerを再起動して結果を作り直していない。タスク終了を確認した後にworkerを通常停止し、終了0を確認した。

同じPG container/volumeをstartし、readiness成功後の `pg_postmaster_start_time()` が変わったことを確認する。Redis/anchorのPIDは一度も変わっていない。停止前後の全行fingerprintは8ケース全て一致した。PGの復旧ログ・停止/復帰inspectionはcase別に保存する。観測timeoutを終了扱いした再起動や、測定途中の削除はない。

復帰後は別Celery workerへ元jobを再配送し、inactive-job・製品状態保持・追加HTTP0。同じCalendar対象、または同じSheetの別rangeを新API受付するとtarget-waiting・QUEUED/未開始/tokenなし・配送cipher保持・追加HTTP0だった。再配送後も同じ禁止を維持した。

続いて合成の元jobだけを削除した。元admission/outboxは消えるが独立journal/request/targetは残り、後続の再配送は引き続き待機・追加HTTP0。owner/session/sync全削除、退会・再連携、実7日経過の完了証拠ではない。

DB停止中はfinallyの記録更新もできないため、最終journalは **ACTIVE 8件**、requestは **INTENT 4件**、保持targetは **12件**。UNKNOWNへ自動分類されたとは扱わない。providerは合計HTTP4/模擬適用4/エラー0、元重複・後続・元削除後の追加HTTPは全て0。元worker/回復worker16 containerは全て通常停止0。

独立processの `final_audit.py` は8組の網羅、各PGの137/復帰/同一IDと起動時刻差、両workerの停止0、元行不存在、独立journal/全target sequence/token、receipt未保存、後続QUEUE/cipher/PENDING、各配送の追加HTTP0を実DB読取と保存inspectionから再確認した。

今回の停止は確定済みの記録を持つ外側の境界である。DB COMMIT応答喪失、SQL実行中/保存途中の接続切断、物理ストレージ障害、ホスト再起動、実RDS failover、実Google、常設beatの自動回復や限定回復は証明していない。送信を止められることと、利用者の処理を回復できることは別条件である。

## 回帰とOSスキャン

同じ固定通常imageでGoogle/async job/PG credential等379件成功・省略0、176.589秒、container終了0。候補7eの保存SQL障害20 subcaseもこの集合内で再実行した。設定・ログ秘匿の70件も70.642秒・省略0・終了0。module集合は非重複なので、この通常imageの回帰は計449件。PGを使う379件は8ケースの終了後に実行し、設定70件は独立network none/SQLiteで並行実行した。source mountを使った先行379件とは区別する。

Docker Scout1.26.0・filterなしで新規scanした。292 packages、脆弱package15、37指摘（HIGH1/MEDIUM1/LOW35）、Python package指摘0。HIGHはzlibのCVE-2026-85091・fixed versionはnot fixed。native scanner終了2、PowerShell呼出の外側終了1を両方記録し、いずれも**未合格**として扱う。依存層/package版は先行と同じで、指摘の隠蔽・抑制や修正済み扱いはない。

文書/CI69件成功。UTF-8/LF・差分・リンク確認の最終結果を証拠へ保存する。製品コード・新UI文言を変えていないため、この文書単位で新しい製品coverageやブラウザー合格を追加主張しない。自己レビューでは固定SHA/image、診断instrumentation、実停止と模擬provider、ACTIVE/UNKNOWN、停止と回復の区別、未検証範囲を確認し、設定70件は障害試験と独立に並行実行したことを明記した。追加の修正を要する指摘は残っていない。

## 証拠と片付け

証拠は `D:/tmp/codex-google-db-restart-20261008`。Git archive/build/733-file manifests、volume作成証拠、全8 case/checkpoint/result、PG停止/復帰inspection/log、worker/probe log、最終audit、通常回帰、Scout SARIF/終了記録、cleanupとSHA-256 manifestを保持する。実Secrets/実利用者データを含めない。

23:39:04 JSTに完全ID/name/label/image/network/mount/終了状態と全label inventoryを照合して、所有24 containerと合成DB用volume一個を撤去した。test DB/他fixture connection0、PG/Redis通常停止0・OOM false、残所有container/volume0。providerの片付け停止137はPG障害の8回とは別分類。合成RedisのDB11〜14は明示FLUSHDB/残存0を確認したもので、製品のbroker自動cleanup成功の証拠ではない。

合成DB・brokerデータは削除されたが、固定image/archive・log・audit・再作成用scriptは保持した。元checkoutのハンドアウト関連13項目は変更・破棄・コミットしていない。実ユーザーデータ、共有環境、他のDocker volumeには触れていない。

## 残条件・承認境界・復旧

[設計T01〜T15](GOOGLE_TARGET_FENCE_DESIGN_2026-10-06.md)全体は未完了。今回T07/T10のDB停止・復帰とT08の元job削除の限定部分を補ったが、保存途中/commit応答喪失・期限経過・全cleanup/再連携/署名鍵変更、共有Sheet認可/資源上限・実process競合/全lock順、legacy停止/drain/移行、保持/退会方針・privacy、日本語対象待機UI、照合と限定回復/独立競合/人間編集は残る。時間経過でACTIVEを解除して代用しない。

実Google/OAuth公開審査・他の外部連携、常設基盤、Stripe/AWS購入・実メール、OS残リスク、実AWS性能、RDS+S3全体復旧、事業/税務/運用等の[正式公開条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)も未完了。

mainは読み取り8567f49f、AWSは今回再照合/変更していない。main/ECR/ECS/S3/CloudFront/共有DB/実データ/Secrets/IAM/実課金/外部通知/容量・継続費用は変更せず、favicon承認を拡張しない。GitHub open Issueは別UIの#1のみで、本課題は先行403/CLI未認証に従い[下書き](GOOGLE_DURABLE_DELIVERY_ISSUE_DRAFT_2026-10-06.md)へ追記する。Issue全体を閉じない。

未配備なので実環境切戻しは不要。今回の文書は通常revertで取り消せる。共有反映する場合は対象SHA・稼働版・drain/保持/送信停止・証拠保持・具体的復旧案と必要承認を揃え、journalをDROPして旧workerを再開する方法は復旧案にしない。
