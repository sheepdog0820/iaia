# Google連携worker強制停止・回復不足の隔離検証

## 結論と固定対象

Calendar/Sheetsの外部書き込み前・適用後応答前にworkerを物理的に停止すると、実行中jobが回復せず残ることを実測した。solo/preforkの8ケースすべてでAPI履歴はrunning、再試行は400。元の未ACKメッセージを復元してもinactive-jobになり、期限処理は履歴を削除するだけでCalendar同期pendingが残る。**再現検証の成立であり、障害復旧の合格や修正完了ではない。正式公開No-Goを維持する。**

対象は[通常29ef38a6配布物](GOOGLE_RUNTIME_29EF38A6_2026-10-06.md)の固定image `sha256:8d0228736282a4d22f3377c7b97de97a2579f8ef31cf0436800568f3dc41357a`。作業親はUI修正 `e6ebcc5f755fb3d771be0325fe885ce869855cc4`、証拠ブランチは `codex/google-worker-crash-20261006`。関連tasks/lifecycle/job views/models/connection/Sheets/Celery/settings/lockの29ef→親差分なしを確認した。ただし[後続UI](GOOGLE_DISPATCH_UI_2026-10-06.md)を含む親全体の通常配布物を今回検証したとは扱わない。製品source・schema・依存は変更せず、本書と受入表だけを更新する。

## 隔離構成と停止方法

- PG 18.3の固定image `sha256:fbaa243599038521bbda8f6fa286d2a8fc1236509606f22de81d0739b0610ba7`、network none、512 MiB/2 CPU、DB512 MiB tmpfs、公開port/mountなし。合成DB google_crash_fixtureだけをmigrateする。
- Redis 7.4.11の固定image `sha256:2e1c703aab5fd50a33e1bccdff0ae62260fb34f2f6cb9d696275c82180619a35`、PG namespaceのloopback、128 MiB/1 CPU、/data64 MiB tmpfs、save/AOF無効。合成認証、broker DB7/result DB8、永続Redisではない。
- appは通常entrypoint/read-only root/cap-drop ALL/no-new-privileges、各1 GiB/1 CPU、合成local設定・空ENV_FILE・自動起動処理無効。/appの差替え・pip追加なし、外部helperだけを/evidenceへread-only mount。network noneにより実Google/AWSへ接続できない。
- 実Celery 5.6.3・Redis配送・製品claim/token/DB処理を使用し、workerは各soloまたはprefork/concurrency1。gossip/mingle/heartbeat/beatは無効。helperは許可Google URLのRequests transportだけをloopback合成HTTPへ変更する。書き込み前は受信後未適用、適用後は合成状態を保存して応答を保留する。SheetsはRAW/ヘッダー17セルのみで、キャラクター行・複数chunkは今回対象外。
- API202/queued=true、job running、合成HTTP到達と実Redis ACK状態を確認してready markerを出す。hostで完全ID/name/label/image/read-only mount/namespaceを照合し、対象worker container全体に `docker kill --signal KILL`。8件すべて終了137/OOMなしを確認し、別名のreplacement workerを起動する。preforkの親子を含むcontainer全体の停止であり、子だけの異常終了/soft-hard limit/ECS停止猶予試験ではない。

## 8ケースの実測

| worker方式・各4ケース | 停止前の元メッセージ | replacement起動後 | 手動同一job配送 | API・同期 |
| --- | --- | --- | --- | --- |
| solo（Calendar/Sheets×適用前/後） | queue0、元taskがunackedに存在 | 5秒観測中running/HTTP追加0、元unackedを保持 | inactive-job、runningを維持 | 詳細200/running、再試行400 |
| prefork（同上） | queue0、元taskがunackedに不在 | 5秒観測中running/HTTP追加0、元結果STARTED | inactive-job、runningを維持 | 同上 |

8 taskのacks_lateはfalse、task.reject_on_worker_lostはnull。**設定が同じでもsoloの同期実行とpreforkでACK観測が異なった**ため、既定値だけで「配送済み/喪失」を断言しない。preforkはこの観測時点で復元可能な元メッセージがbrokerに残っていない。soloの自然なvisibility期限後の配送は5秒観測の範囲外であり、「永久に再配信されない」とは言わない。

実HTTP計8回、合成provider検証エラー0、適用前4件の外部変更0・適用後4件は変更1回ずつ（Calendar2イベント/Sheets2宛先）。全jobはrunning/progress10/error空/result空・startedあり/finishedなし。Calendar4同期はpending/external_event_id空で、適用後でもDBに外部完了が残らない。元taskの結果backendはSTARTED。各replacement後の約5.062～5.077秒、計160 snapshotで状態・HTTP数・元unacked有無を確認した。長時間の自然回復や常設監視の保証ではない。

各jobの期限を合成DBで過去へ変更しても、詳細200/running・再試行400のまま。返る日本語は「失敗したジョブだけ再試行できます。」。現在のUIが履歴確認へ誘導しても、この停止状態の回復操作はまだ提供されない。

## 元メッセージ復元・期限処理

8ケース完了後、soloの元delivery tag/task IDがRedis unackedに4件残ることを照合した。これらの合成jobだけを期限内へ戻し、Redisの該当unacked_index時刻を0へ変更して、実Kombu channel.qos.restore_visible(interval=1)を呼び出した。実channelのvisibility_timeoutは3600。**1時間待った試験ではなく、隔離Redisへの時刻経過注入**であり、製品設定を変更しない。

別の実prefork workerが元task ID4件を受信し、Celery結果はSUCCESS/inactive-job、製品jobはrunning/progress10/終了なしのまま。provider呼出しを拒否するhelperでも禁止マーカー0で、外部処理へ進まない。queue/unacked/indexは0。この試験は新しいtask.delayによる重複だけでなく、元brokerメッセージの復元も回復しないことを示す。Celery SUCCESSだけでは利用者の連携完了を判定できない。

最後に全合成job8件を期限切れにして、実expire_async_jobsを呼んだ。job削除8件・残数0、Calendar同期pending4件は残る。beatは起動していないため定期実行の運用検証ではない。実時間7日を待ったわけでもない。期限削除は障害回復や外部変更の取り消しではない。

## 初回の失敗・片付け

初回helperは「HTTP待機中のunacked0」を前提にsoloで待ち、early ACK確認45秒がtimeout、client終了1。その後のmarker待機もtimeoutし、SIGKILL前に試験が止まった。helper終了で合成HTTPが閉じ、workerの通常retryは最終failedになった。初回source snapshot・4 container inspect/log・cleanupを保持する。この失敗を製品の強制停止結果に混ぜない。

初回専用4 containerを確認・停止削除後、helperを観測型に直して新しいPG/Redisで8ケースを実施。全8 client終了0、意図的停止8 worker終了137/OOMなし、8 replacement正常終了0。追加の元配送復元client終了0、workerも正常停止0を確認した。18:26:49 JSTに完全ID/name/label/image/mount/namespaceを照合して再試験28 containerを削除、合成PG/Redis/tmpfsを破棄した。SQL最終job0/pending同期4/合成user8、Redis queue/unacked0、対象label container/volume残数0。元worktreeの別作業13項目とimage/source/証拠は保持し、実データは変更しない。

## 修正に向けた受入条件（未実装）

1. 永続dispatch情報とtransaction境界を持ち、投入結果不明でもjob ID/入力/接続先を保持する。ACK変更だけを回復策にしない。
2. 実行lease・claim世代で停止を検出し、遅い旧workerによる上書きを拒否する。heartbeatの一時不通を確定失敗と誤認せず、外部結果不明として保存・可視化する。
3. 元job/接続/所有者/期限/入力・Calendar ID/ETag等を再検証した限定回復にする。Sheets適用後や同時ユーザー編集は自動上書きせず、結果確認を先にする。再認可時の旧イベントの扱いは未回答の人間方針を決めつけない。
4. 停止前後・ACK前後・部分出力・復元配送・旧worker遅延・再失効・期限削除を実PG/Redis/HTTPで再検証し、利用者の結果不明履歴と監視を失わない。共有運用/常設構築/容量・費用変更は別承認を維持する。

## CI・承認境界・証拠

18:27 JST確認で親e6ebcc5fの[CI 37441294494](https://github.com/sheepdog0820/iaia/actions/runs/37441294494)は5成功/Playwright実行中。今回文書のCI成功とは区別し、生きたrunを中断しない。mainは同時点で8567f49f。AWSの再照合・変更、OS再スキャン/APT調査は今回実施しない。直前のOS HIGH3/MEDIUM1/LOW35・終了2を未合格として維持する。

文書回帰39件成功（初回0.037秒・文書追加後0.036秒）、下表9 SHA-256と相対文書リンク3件を照合。差分/日本語/実測と時刻注入・未実装の区別を自己レビューし、文書への追加指摘なし。製品Python/JS/UI変更なしのため追加formatter/画面試験対象はない。main/AWS/共有DB/schema/Secrets/IAM/課金/常設容量/継続費用/外部通知は変更せず、完了済みアイコン承認や固定6b6c570c反映案へ追加しない。文書だけの復旧は通常revert。障害復旧・実外部連携/課金/性能/復旧/事業者運用などは[受入表](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)でNo-Goを維持する。

証拠は `D:/tmp/codex-google-worker-crash-20261006/`。初回/再試験helper・完全inspect/log・8ケース160 snapshot・元配送復元・SQL/Redis/cleanupを保持し、Gitに混入しない。

| ファイル | SHA-256 |
| --- | --- |
| probe.py | c31516985c29284b9b3a3f8361952b304d14afd46e2ed6d88448338e7bc34e25 |
| worker.py | 15fd16a07de72d91e09263f749ff70c83f0a101b2073016537326619d6cc2154 |
| results.json | fd24ecf7a1f398b6a74edbff0adff38912cf0d6601a81456233518b799bc6d02 |
| restore_probe.py | 108038521128edde78c6f667405533e9b5197f79c1d3db3be3e556f930f167c1 |
| restore-results.json | 32106a0029689047c8ae4549317c718893ffeb3da5d1352ff8d4c62403784baa |
| restore-worker.log | 8a317b8bc33c57cd8b88e4f71d9373bb1d8bfe7f7b0f4594e547eafc89308c76 |
| containers-before-cleanup.json | 789ad939093a4a9f65fe8bfda7f748520d678000b0717adf60cfbacdf1afe420 |
| sql-redis-final.json | ae8a551e2874f97c53facf1e6026c4e65f1129b5764710bfb1ec8f0a4550a44a |
| cleanup.json | 297c14e4f6691d619548ff3ae2bb9442d477fc985adabbcff6b6247aa9387628 |
