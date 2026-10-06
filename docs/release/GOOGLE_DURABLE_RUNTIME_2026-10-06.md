# Google永続配送の通常配布物・実プロセス回復検証

## 対象と公開判断

固定アプリは **`2261adf789b2b85ed04473d68557c125c0701583`**。[永続配送の部分実装](GOOGLE_DURABLE_DISPATCH_2026-10-06.md)を通常Dockerfile/entrypointから構築し、実PostgreSQL・Redis・別producer/relay・solo/prefork worker・Requestsで未開始ジョブの回復を確認した。[候補CI](https://github.com/sheepdog0820/iaia/actions/runs/37465093050)はhead SHAを照合して全6項目successを確認した。今回の追加commitは証拠文書のみで、アプリやimageは変更しない。

正式公開は **No-Go** を維持する。main/AWS/ECR/ECS/S3/CloudFront、共有DB/実データ、実Google/Stripe/OAuth、Secrets/IAM、実課金/メール・通知、常設容量/継続費用は変更していない。新migration0057/0058を適用したのは自分の使い捨てDBのみ。完了済みfavicon承認や固定6b6c570c反映案へこの候補・証拠を追加しない。

## 配布物と隔離範囲

- clean固定commitの`git archive`から構築。image IDは `sha256:0e70ed852659c95c6bd1e2abc1ce4f459aff325e2a5dff8cddc96ddcc270eadd`、revision labelは2261adf7と一致する。選定 **713 source/assets** の欠落・追加・SHA-256不一致0、Python cache0、imageのentrypointとarchive bytes一致。全リポジトリファイルを照合したという意味ではない。
- installed Python packages **111件** と先行28ac imageの依存先行10層が一致した。cryptography50.0.1の通常配布runtimeで暗号化配送を実行した。新規依存・lock変更なし。
- 固定PG18.3とRedisを使い、PGはnetwork none、他のapp/Redisはそのnetwork namespaceを共有。host port公開なし、外部接続不可。appは通常entrypoint、read-only、cap-drop ALL、no-new-privileges、一時/tmp。mountは外部helper `/evidence` のみで **/appのsource overlayはない**。
- providerはnamespace内の `127.0.0.1:8016`。Requestsの既知Google URLだけをloopbackへ変更し、それ以外を拒否する。実GoogleのTLS/API応答/トークン更新・失効を検証したとは扱わない。providerは合成token、Calendar body、Sheetsの正確な内容binding、worker開始/暗号文消去を照合する。記録にはbodyのSHA-256を残し、セル値を保存しない。
- 回帰テストはRedis DB9/10、fault試験はDB11/12に分離。共有データや本番資格情報は使わない。常設beatは起動せず、relayは別のproducerコンテナから実アプリ `dispatch_google_job` を呼び出した。自動常設回復・共有環境運用の証拠とは区別する。

## 回復・重複配送試験

各行をCalendar/Sheets×solo/preforkの4組で検証し、非重複 **16ケース**。途中の「12成功」はこの16件の部分集合であり加算しない。

| 障害位置 | fault注入と確認 | 回復結果 |
| --- | --- | --- |
| producer commit直後 | on_commit wrapperを外部helperで一時停止。DB確定・job QUEUED・意図PENDING/暗号文保持/attempt0を確認して実SIGKILL | 別relayが同じjobを投入、attempt1で成功 |
| relay claim確定後・publish前 | 5分claimをDB確定した位置で外部helperが一時停止、実SIGKILL。期限内の独立relay4回は投入拒否 | 時刻/期限を変更せず実時間で5分経過後、同じjobをattempt2で回復 |
| broker受理後・worker開始前 | worker停止中に実Celeryで2 messageを投入、Redis list=2を確認。自分の非永続Redisを実SIGKILL/同ID再起動、list=0 | 暗号化意図を保持。実60秒待機期限後、同じjobをattempt2で再投入して成功 |
| publish受理後の応答喪失 | 実senderを呼んだ後、外部helperが戻り値だけFalseへ置換。これはネットワークpacket喪失そのものではなく制御されたACK喪失fixture | workerの結果/receiptを保持し、attempt1・同じjobで成功 |

producer8件（claim用準備4件を含む）・relay4件の **12個のapp processを意図的にSIGKILL**。Redisの意図的137終了・再起動は2回。アプリ自体のtransaction/暗号文/claim状態に直接UPDATEする注入はしていない。期限変更・時計patch・Celery eager実行なし。

16件すべてjob SUCCEEDED/progress100・outbox DELIVERED/暗号文空で、利用者ごとのjobは1件のまま。合成provider **16 HTTP/適用16/検証エラー0**。全HTTPの直前にDBのworker開始receiptと暗号文消去、実行期限が未来であることを確認した。4つのclaimケースは元gateログのclaim期限と実DB started_atを比較し、実期限経過後の開始を追加の読み取りauditで検証した。例: solo Calendar期限12:57:07.829985 UTC→開始12:57:25.985267 UTC。

各完了jobを実workerへ1回ずつ重複配送、**16件すべて `inactive-job`、追加HTTP0・結果保持**。outbox経由の同job再投入もFalse。旧FAILEDメッセージと新しい別job・同一同期対象の世代競合を解消したという意味ではない。

## 回帰・監査・失敗記録

- 通常image内Google関連27 modules **251成功/省略0**（85.380秒）、設定/ログ保護6 modules **70成功/省略0**（68.299秒）。非重複総 **321成功**。hostの39文書テストは別集計。新0057/0058の実PG移行・逆移行・raw DELETEと25新規配送テストを含む。未mock外部HTTPは禁止する。
- 4つのworkerログに合成Bearer token/セル名が含まれないことを確認。worker4個の正常停止は終了0/OOMなし。ハーネスのproviderは `docker stop -t 5` 後に **137/OOMなし** で終了しており、正常終了0/143とは扱わない。
- 初回配布監査のPowerShell JSON単一オブジェクト扱いが誤り、`distribution-check.json` のimage/revisionがnullとなった。これは**無効な監査結果**。fail-closedのauditへ訂正し、`distribution-reviewed.json` で固定image・revision・全713 bytes・依存10層を再照合した。
- 初回cleanupはprovider終了を143と仮定して削除前に停止した。正確なID/label/image、terminal137/OOMなし、全provider結果、5秒stop履歴を確認して、その検証用providerだけの期待値を訂正した。app回復失敗としても、全process終了0としても記録しない。
- 新規Scout **1.26.0**・新しいcache・filterなしで全OSを監査。292 packages indexed/16 vulnerable packages、**39指摘（CRITICAL0/HIGH3/MEDIUM1/LOW35、Python0）・終了2、不合格**。先行28acのCVE/severity/package/fixed-version signatureとの差0。HIGHはgcc-14のCVE-2026-102010/95619、zlibのCVE-2026-85091でscannerはnot fixed。最新APT修正版やnative closureへの修正成功を主張しない。

## 終了・証拠・残課題

証拠は `D:/tmp/codex-google-durable-runtime-20261006/`。22:03 JSTのcleanupで、正確なfull ID/label/image/mount/network/期待終了状態を確認した **83コンテナ** を撤去し、tmpfsの合成データを削除した。SQLはjob succeeded16/outbox delivered16/暗号文保持0/users16/characters8/test DB0。RedisのDB9/11ともcelery/unacked/unacked_index=0。自分のcontainer/volume残存0、OOMなし。ログ・archive・runtime manifest・SHA-256一覧は保持する。元checkoutのハンドアウト関連13 itemsは変更・stageしていない。

復旧はこの証拠文書commitの通常revertで、配布アプリを変更しない。共有DBの逆移行・AWS切戻しは今回不要。現在のコードの未開始配送回復はローカル実プロセスまで証明したが、管理コマンド/beatの常設運用・監視、鍵ローテーション/バックアップ上のprivacy、旧FAILED/新job・同期対象世代fence、開始済み停止/結果不明の照合と限定回復、実Google・AWS・OAuth公開審査は残る。

OS HIGH3、Stripe/実通知、正式性能・長時間負荷、RPO/RTOを含めた[正式公開条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)は未達。GitHub Issueは権限403の先行状況から新規作成しておらず、[下書き](GOOGLE_DURABLE_DELIVERY_ISSUE_DRAFT_2026-10-06.md)で部分達成と残課題を維持する。
