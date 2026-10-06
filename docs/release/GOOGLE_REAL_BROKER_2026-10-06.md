# Google連携の隔離Redis・実Celery配送検証

## 固定対象と隔離構成

製品対象は `29ef38a65553d2cd453af78671146fd75b18e82b`、証拠ブランチは `codex/google-real-broker-20261006`。[通常配布物検証](GOOGLE_RUNTIME_29EF38A6_2026-10-06.md)の固定image `sha256:8d0228736282a4d22f3377c7b97de97a2579f8ef31cf0436800568f3dc41357a` をそのまま使用する。製品ソース・依存・設定・schemaは変更せず、本書と受入表だけを更新する。前回の703選定source/assets一致や260回帰の記録と、今回の配送試験を区別する。

- PG 18.3はimage `sha256:fbaa243599038521bbda8f6fa286d2a8fc1236509606f22de81d0739b0610ba7`、network none、512 MiB/2 CPU、DB領域512 MiB tmpfs。公開port・volume mountなし。合成DB `google_broker_fixture` のみを作成・migrateする。
- Redisは既存image `sha256:2e1c703aab5fd50a33e1bccdff0ae62260fb34f2f6cb9d696275c82180619a35`、実観測7.4.11。PGのnetwork namespace内のloopback、128 MiB/1 CPU、/data 64 MiB tmpfs、save/AOF無効。合成認証付きbroker DB7/result backend DB8で、永続Redisではない。
- 独立した2 workerは通常entrypoint/read-only root/cap-drop ALL/no-new-privileges、各1 GiB/1 CPU。Celery 5.6.3、各solo/concurrency1、通常celery queue、gossip/mingle/heartbeat無効、beatなし。クライアントも同じimage・隔離構成を使い、eagerではなく実Redisで投入・受信する。
- /appを差し替えず、外部helperだけを/evidenceへread-only mountする。空ENV_FILE/local設定、自動起動処理無効、合成SECRET_KEY/資格情報を使用する。namespaceのnetwork noneにより実Google/AWSへ接続できない。
- worker helperは元のRequests transportを保持し、許可したCalendar/Sheets URLだけを `127.0.0.1:8015` の合成HTTP応答へ置換する。worker内の製品Task・claim・token処理・DB更新・Celery retryやbrokerをmockしない。ただし実GoogleのTLS/認可/ETag/公開OAuth審査は検証していない。期限内の合成tokenを使用し、refreshも今回対象外。

## 実配送10ケース

2 workerのping応答を確認後、実APIClientから各5ケースをCalendar/Sheetsに投入した。最終全10 jobがsucceeded/progress100/error空・開始終了時刻あり、Calendar同期5件synced。以下のHTTPは実Requestsで到達した合成providerであり、実Googleへの書き込みではない。

| ケース（各2件） | Calendar HTTP | Sheets HTTP | 結果 |
| --- | --- | --- | --- |
| 通常投入 | POST | PUT | queued=true、成功 |
| 同一job二重配送 | POST | PUT | 第1workerがRUNNING中、第2workerはinactive-job。各provider変更1回 |
| 投入後の呼出元例外 | POST | PUT | API queued=falseでもRUNNINGを維持し、その後成功 |
| 診断task ID保存失敗 | POST | PUT | API queued=trueを維持し、その後成功 |
| provider適用後の応答消失 | POST→POST(409)→GET→PUT | PUT→PUT | 実Celery retry後に成功。Calendarイベント1個、Sheetsの同じ固定範囲へ同一値2回 |

二重配送は第1workerをprovider gateで待機させたまま、元のTask.delayで別メッセージを実Redisへ投入し、第2workerの実AsyncResultがinactive-jobになることを確認する。新jobの重複やfailed状態からの重複再実行を証明しない。

投入後例外は元のdelayで実配送した後、別workerのRUNNING/provider到達を待って呼出元helperが例外を注入する。**実Redis/TCPの応答消失を発生させた試験ではない**。ID保存失敗もclient側QuerySet.updateへの限定的なDatabaseError注入で、実DB全体の停止ではない。workerプロセスの製品処理は差し替えない。[投入状態保全](GOOGLE_DISPATCH_STATE_2026-10-06.md)が実受信workerとの組合せでも働くことを確認した。

provider応答消失は合成serverが変更を保存してから実socketを閉じる。Calendarは決定的IDによる409後に私有metadata/ETagを読み、If-Match付きPUTへ進んだ。合成イベントは計5個で重複作成なし。SheetsはRAW/ヘッダー17セルを同じ固定範囲へ2回PUTし、最終値は一致した。今回はキャラクター行なしのヘッダー配送で、複数chunk/キャラクター値やexactly-once、同時ユーザー編集の保全を保証しない。全体の実HTTPは14回、合成provider検証エラー0、Sheets宛先5個。

この結果、queued=falseは「未配送」を意味しないことも実受信付きで観測した。現UIの「開始できませんでした」という表示、再投入による別job重複、outbox/外側transactionの未commit、ACK/worker crash/lease/永続Redis・failover、prefork/time limit、同sync別job版競合、期限/部分出力/キャンセル後の外部副作用、永続接続先IDと再認可時の方針は未解決または未検証。今回これらの運用保証やUI変更を追加しない。

## 初回失敗と後片付け

初回clientはstandalone APIClientの既定HTTP_HOST=testserverが許可されずDisallowedHostとなり、そのエラー表示helperがresponse.dataを参照してAttributeError、終了1。投入前のjob0を確認した。製品ALLOWED_HOSTSは変更せず、helperだけでHTTP_HOST=127.0.0.1と固有PROBE_TAGを指定し、新しいclientで再実行した。初回clientの終端1を確認後に再試験し、同じPG/Redis/2 workerを使用した。初回ログ・metadataを保持し、初回から全成功とは扱わない。保存helperは訂正後の版で、初回版の完全source snapshotはない。

再試験clientは終了0/OOMなし。StartedAt 08:28:39.603487983Z、FinishedAt 08:28:47.040284051Zでcontainer全体約7.437秒（初期化/handshakeを含み、単独テスト時間ではない）。後片付け前のSQLはsucceeded10/synced5、Redis queue length0/unacked0/result keys12（元10・重複2）。

17:33:20 JSTに専用6 containerの完全ID/name/label/image/mount/namespaceを照合した。両workerを正常停止・終了0/OOMなしで確認し、初回/再試験clientを削除、専用PG/Redisを停止・自動削除して合成tmpfsを破棄した。対象label container/volume残数0。通常image・証拠・元worktreeの別作業13項目を保持する。実ユーザーデータは変更しない。

## CI・承認境界・公開判断

17:37 JST確認で製品29ef38a6の[CI 37433985459](https://github.com/sheepdog0820/iaia/actions/runs/37433985459)は全6ジョブsuccess。先行証拠be6d3b76の[CI 37435420661](https://github.com/sheepdog0820/iaia/actions/runs/37435420661)は5成功/Playwright実行中で、今回文書のCI成功を代用しない。生きたrunを中断・再実行しない。

今回OS再スキャン・APT候補/native閉包の再調査はしていない。通常29ef38a6の直前記録39指摘（HIGH3/MEDIUM1/LOW35、Python0）・終了2は未合格のまま。実Google/Discord/X/ICS/CCFOLIA、実課金/共有DB/常設worker/SMTP、実AWS性能・復旧・事業者運用等は未達で、[正式公開受入条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)はNo-Goを維持する。

main/AWS/ECR/ECS/S3/CloudFront、共有DB/schema、Secrets/IAM、課金/常設容量/継続費用、外部通知を変更しない。完了済みアイコン8567f49fの承認や固定6b6c570c反映案に追加しない。文書変更の復旧は通常revertで、製品image/共有環境/外部データに影響しない。関連Issue作成の先行403を権限変更で回避しない。

## 保存証拠

文書回帰39件成功（0.038秒・終了0）、下表9 SHA-256と相対文書リンク3件を照合した。日本語・実測/注入/未確認の区別を自己レビューし、追加の指摘なし。製品Python/JavaScript・UI文言を変更しないためformatter/ブラウザー検証の追加対象はない。

`D:/tmp/codex-google-real-broker-20261006/` にhelper/初回起動command、初回・再試験ログ、provider結果、全container inspect、SQL/Redis、正常停止ログ/cleanupを保持する。start_probe.ps1は初回commandの記録で、修正済みclientの自動再実行scriptとは扱わない。生成物はGitへ混入しない。

| ファイル | SHA-256 |
| --- | --- |
| probe.py | 5cc7f661ca417f995c759518bf4e43fec2bb4b37a1de3ea557afb484c1371301 |
| worker.py | 7be2ca5557236f241bf2ef8e9098b2cba971f81424b83debf97cb7a416350776 |
| probe-initial.log | e93ffaeb95ea42406caf10ced8e37ebe165d67f1071d068859ee87d4c2ad82ce |
| probe-recheck.log | 230a502bd8f921d8b21e0b2c5fd87f349272b813666963db7b723ac0f811283b |
| probe-results.json | 84cee86f40840210c8ef35e762811591bcbd29bb9c82adf06d5ce5d2ec47532b |
| client-recheck-inspect.json | 3d56d4e4d2a9bda910bbd7ed697a81da28ddb52d84be90be26679e3fc7eae977 |
| sql-redis-state.json | 5db35587828de6097cb60edcc1569bab7d073f9d9b1908d9a51e4aa4b7e0e903 |
| workers-stopped.json | 0bfa8630d91d72f297106c644c4bee77f2060f3dae9bb12d955833afb2014359 |
| cleanup.json | b3c11212b7381803170762225a858e9121995996376695946610f1d061da4abf |
