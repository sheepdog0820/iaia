# Google共有実行権: COMMIT確定応答を失った通常worker

## 対象と判定

2026-10-08夜〜10-09未明の隔離検証。作業ブランチは `codex/google-commit-loss-20261008`、基準HEADは `64dabd842cdd8b35708fd71f082fb0c2408c4ba8`。製品コード・schema・依存・画面は変更せず、[PG停止・復帰](GOOGLE_DB_RESTART_RUNTIME_2026-10-08.md)に残っていたCOMMIT応答喪失の二境界を検査した。**正式公開はNo-Go**。

製品候補7eの[CI37790973338](https://github.com/sheepdog0820/iaia/actions/runs/37790973338)はhead一致・run/全6ジョブsuccessを確認した。PG復帰の記録は64dabd84としてcommit/通常push済みだが、その[CI37796166163](https://github.com/sheepdog0820/iaia/actions/runs/37796166163)はinfrastructureのみsuccess、他5ジョブcancelled、run cancelled。キャンセル原因は未確認で、全CI合格や単なる実行待ちとしない。今回の文書commitのCIは別に確認する。

## 固定配布物と隔離

通常imageは `sha256:8f2856941ba6763d7884e43e7b4794efe52d0ee0f68f8f0e0e07bdfe814e6c0b`、revision labelは製品候補 `7e70368b75ff17eb2ad0361291f95ca52b904d37`。64dは記録だけの後続版。今回独立に読んだ選定733 source/assetsの現在tree/image SHA-256不一致0、111 Python packages、通常entrypoint byte一致・pyc 0。ソースを `/app`や `/workspace`へoverlayせず、read-only `/evidence`に診断scriptを置く。通常entrypoint・非root・read-only・cap drop/no-new-privileges、1 GiB/1 CPUを維持した。

専用Redisのnetwork noneをanchorに、PG18.3・worker・模擬Google・診断proxyがlocalhostだけで通信する。ホストport・外部経路はない。PG/Redisのデータはtmpfsのみ、Docker volumeは作らず、全利用者/token/予定/キャラクターは合成。developer env/Secrets/S3/実メール/起動時migration・collectstaticは無効。migrateはこの専用合成DBへ明示的に実行した。ECRへpushしていない。

PGは512 MiB/2 CPU、Redisは128 MiB/1 CPU・永続化なし。実PG/Redis/Celery/Requests/API受付を使用し、Google URLだけを許可済みCalendar/Sheets経路のloopback模擬providerへ置換した。実Googleへの適用や実RDS障害の証拠ではない。

## 本当に確定したCOMMITの応答を切る

診断proxyはworkerのPG接続だけを127.0.0.1:5433からPGの5432へ転送する。observer/API/providerは5432へ直接接続し、proxyを通さず確定行を検査する。TLS/GSSはこの隔離経路でのみ無効。実Secrets/TLSセッションを扱わない。

[公式message formats](https://www.postgresql.org/docs/18/protocol-message-formats.html)と[message flow](https://www.postgresql.org/docs/18/protocol-flow.html)を参照し、BackendKeyDataのPID、frontend Query(COMMIT)、backend CommandComplete(COMMIT)を照合した。SQL本文・行データ・パスワード・cancel keyは記録しない。正確なworker backend PIDに一度だけarmし、実COMMITを転送した後、PGからCOMMIT完了messageを受け取った時点で、そのmessageと後続ReadyForQueryをworkerへ転送せずTCPを閉じる。ORM/driverのcommitや例外をmockしていない。未対応のCOMMIT形式はarmが残って監査に失敗するため、障害を起こしていないのに成功としない。

予備検査では専用診断tableに一行INSERTし、proxy経由のcommitが実psycopg OperationalError/closed connectionとなった一方、別の直接PG接続でその行の確定を確認した。proxyの完了観測だけで成功扱いせず、独立読み取りで確定を裏付けた。tableは検査後にDROPし、最終監査でも不存在を確認した。

workerは対象atomic関数の外側でPIDをarmするだけで、通常の `_begin_request` / `_receive_request` とcommitを実行する。HTTP中にDB transaction/lockを保持させない。診断instrumentationと無改変の製品ソースを区別する。

## solo/prefork × Calendar/Sheets × 二境界

| COMMITを失う境界 | 独立接続で確認した確定行 | 模擬HTTP/適用 | 最終実行権 |
| --- | --- | --- | --- |
| 送信INTENT保存 | INTENT一行・responseなし | 0/0 | UNKNOWN、全対象保持 |
| HTTP200後のreceipt保存 | KNOWN一行・status200・received_atあり | 1/1 | UNKNOWN、全対象保持 |

計8ケースで実workerタスクがRedis結果FAILURE/OperationalErrorとなり、proxyのPIDとworkerログのarm PIDが一致した。各caseのCOMMIT完了をPG socketで観測しACK転送falseを確認。今回はDB自体が生存しているため、finallyによる未解決状態のUNKNOWN保存が確定した。PG停止試験のACTIVEをUNKNOWNへ読み替えない。

実行期限・保存期限は未来、時計/期限注入なし。障害試験中にworker・PG・Redis・proxyをkill/restartして結果を作り直していない。終了したタスクの元workerを通常停止0とした後、別Celery workerへ元jobを再配送しinactive-job・製品状態保持・追加HTTP0。同じCalendar対象、または同じSheetの別rangeを新API受付してtarget-waiting・QUEUED/未開始/tokenなし/配送cipher保持・Calendar PENDING・追加HTTP0を確認した。

合成の元jobを削除してadmission/outboxが消えても、独立execution/request/targetは保持され、後続を再配送しても追加HTTP0。最終UNKNOWN8/INTENT4/KNOWN receipt4/保持target12、未開始後続8。receiptが既知でも、job成功の確定まで到達していない処理を全体成功や安全な自動回復としない。

正常対照として同じproxyを通る別のCalendar/Sheets job二件をarmなしで実行し、synced/exported・SUCCEEDED・KNOWN200・FINISHED/closed_at・対象解除を確認した。障害8件のprovider HTTP4/模擬適用4、正常対照2件を含む総HTTP6/適用6/エラー0。proxyは予備1＋製品8の計9 ACK切断、異なる9 PID、未消費arm0/内部エラー0。正常対照で「proxyが全COMMITを失敗させているだけ」ではないことを確認した。

別process/直接PG接続の `final_audit.py` が全8組の網羅、wireイベント/PID・正常worker停止、元行不存在、UNKNOWN/request証拠/全sequence・token保持、後続待機/cipher/PENDING、追加HTTP0と正常対照を再検査して成功した。

## 品質と未確認範囲

同じ固定imageの先行回帰449件・文書69件成功は[PG復帰記録](GOOGLE_DB_RESTART_RUNTIME_2026-10-08.md)の証拠で、今回の再実行として数えない。今回の品質は実wire予備検査1、障害8、正常対照2、独立監査と今回文書/CI69件成功・UTF-8/LF/差分/リンク確認を区別して残す。自己レビューで候補/image/診断instrumentation、予備確定行と製品確定行、模擬Google、INTENT/KNOWN/UNKNOWNと安全な回復の区別、CIキャンセル・片付け137・未検証範囲を確認し、追加修正を要する指摘は残っていない。製品変更がないため新製品coverage・UI/ブラウザー合格を追加主張しない。

同じimageの先行Scout1.26.0は37指摘（HIGH1/MEDIUM1/LOW35）・native終了2で未合格。今回新たにscanしたとは扱わず、依存や配布物不変を脆弱性の修正・受容に代用しない。

この検査はINTENT/receiptの「server確定・client未受信」であり、SQL保存途中の切断、COMMITが未確定の側、実行権獲得/job成功/解除の各COMMIT応答喪失、物理ストレージ/host/RDS failover、TLS経路、実Google、常設beat、自動・限定回復を証明していない。全cleanup/退会/再連携・鍵変更、全lock順・認可/資源濫用、legacy-drain/移行、保持/privacy、日本語待機UI、照合/限定回復も[残条件](GOOGLE_TARGET_FENCE_DESIGN_2026-10-06.md)として維持する。

## 証拠・片付け・承認境界

証拠は `D:/tmp/codex-google-commit-loss-20261008`。proxy/calibration/worker/probe/controller/audit/cleanup、全case結果・PID/events/inspection/log、733-file manifest、正常対照とSHA-256 manifestを保存する。再作成可能だが削除した合成DB自体は残していない。

10月9日00:04:07 JSTに完全ID/name/label/image/entrypoint/network/mount/port/終了状態と所有inventoryを照合し、24 container/tmpfsを撤去、残所有container0。worker17件とPG/Redisの通常終了0、test DB/他fixture connection/診断table0を確認した。proxy/providerの片付け停止137二件は、障害試験の9 ACK切断やworker障害とは別分類。Redis DB11/12のFLUSHDB/残存0は診断後の明示cleanupであり製品の自動queue cleanupの証拠ではない。volumeなし、固定image/全証拠/元checkoutの別作業13項目は保持し、実データや他のDocker資源は変更しない。

mainは読み取り8567f49f、AWSは再照合/変更していない。main/AWS/ECR/ECS/S3/CloudFront/共有DB/実Google/実ユーザーデータ/Secrets/IAM/課金/外部通知/容量・継続費用変更なし。faviconの反映承認を拡張しない。今回は未配備の記録のみなので実環境切戻しは不要、文書は通常revertで取り消せる。共有反映/DB移行は固定対象・現稼働版・停止/drain・証拠/保持・復旧案と必要承認を揃える。[正式公開条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)全体やIssueは完了扱いにしない。
