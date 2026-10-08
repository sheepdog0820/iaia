# GitHub Issue下書き: Googleジョブの永続配送と結果不明の安全な回復

2026-10-06の新Issue作成はintegrationの403（Resource not accessible by integration）で失敗、CLIは未認証。**Issueは未作成**。既存open #1のキャラクターUIとは別課題であり、認証/権限変更は行っていない。次回の書き込みは利用可能な正規の権限を確認してから行い、未確認のIssue番号を割り当てない。

## 目的

Google Calendar/Sheetsを正式公開できる品質にするため、DB確定とCelery投入の隙間、再配送、結果不明、同期対象の世代競合を解消する。部分修正・ローカル成功のみで完了にしない。

## 現在の部分実装と証拠

- 10月8日の[PostgreSQL保存SQL障害](GOOGLE_DB_BOUNDARY_FAILURES_2026-10-08.md): INTENT/receipt/job成功/journal完了/target解除の前後×Calendar/Sheets20ケースでDB側の実SQLSTATE22012/abort/rollbackを検査し、UNKNOWN・closed_atなし・全holderを保持、元再配送/後続の追加mock送信0を確認。局所20 subcase成功・変更60文16分岐先100%/除外0。製品コード/schema/依存変更なし、source mount・mock Google・task直接呼出の範囲であり、通常新配布物/実HTTP/別worker/DB再起動を証明しない。先行b348b06a commit/pushと今回commitを区別し、広域/最終品質/cleanupは当該記録を参照。T10全体/移行-drain/保持・認可/UI/限定回復/実Google・共有運用、OS37指摘・HIGH1とその他公開条件は残る。main/AWS/共有DB/Secrets/課金/容量変更・承認拡張なし、Issue全体未完了・No-Goを維持する。

- 10月8日の[通常配布物・共有実行権SIGKILL](GOOGLE_SHARED_RUNTIME_2026-10-08.md): 9a通常imageの選定733 source/assets・111 packages/先行依存10層を照合、送信境界5点×Calendar/Sheets×solo/preforkの20停止で独立worker/新job/元job削除後の追加HTTP0を確認。ACTIVE20/INTENT16/target30、provider HTTP12/適用12/エラー0、時計注入なし。独立Celery relay20再投入も待機/cipher保持/追加HTTP0。時刻だけで別jobを選ぶ回帰fixtureの3失敗を同時刻REDで再現し受付IDへ修正、DB名衝突等の失敗を保持して分離再試験、通常修正image378成功/省略0・9a設定70成功・差分18文2分岐先100%/除外0。9a CI37779822628全6成功と今回commitのCIを区別する。新Scout1.26は両image37指摘（HIGH1/MEDIUM1/LOW35）/終了2で未合格、依存変更なしで減った指摘を修正完了としない。実DB fault/全cleanup・再連携/認可濫用/全lock順/legacy-drain/保持・UI/限定回復/実Google・常設運用は残る。main/AWS/共有DB/Secrets/課金/容量変更・既存承認の拡張なし、Issue全体未完了・No-Goを維持する。

- 10月8日の[共有実行権・独立送信記録](GOOGLE_SHARED_EXECUTION_2026-10-08.md): 対象FIFO/待機cipher保持、送信前INTENTと既知/unknown receipt、job削除後の禁止、後続Calendar PENDING保全、allocation改変/偽token拒否、journalを残す逆移行ガードを追加。最終PG431成功/省略0・SQLite407成功/PG専用24省略、675 source照合不一致0、製品差分241文56分岐先・新規35テスト601文16分岐先/helper10文2分岐先100%・除外0。実PG独立接続のholder1/書き込み1・HTTP前INTENT確定を確認し、Python21品質/Bandit終了0/schema差分0、自分のPG/tmpfs撤去・証拠/別作業保持。無料KP579 CI全6成功を作業ブランチへ取り込んだが、新製品候補のCIとは区別する。全lock順、通常新配布物のSIGKILL、legacy/drain/移行、保持・再連携・認可/濫用防止・UI・限定回復・実Google/共有運用は残り、Issue全体は閉じない。main/AWS/共有DB/Secrets/課金/容量変更・既存承認の拡張なし、No-Goを維持する。以下の未コミット/CI未確認等は各先行記録時点の状態である。

- 基準77192584のCIは[37540663348](https://github.com/sheepdog0820/iaia/actions/runs/37540663348)で5成功/Playwright失敗（428 passed/1 flaky）。Firefox無料KPのsignup goto(load) timeoutを[別の専用修正](FREE_KP_SIGNUP_READINESS_2026-10-07.md)で調査し、画像待ちの旧開始条件をRED再現、既存helperを利用して通常/画像待ちの一連操作と広域93件が3ブラウザーで成功（retry/skip/flaky0）した。ただし元CIの根本原因未確定で、Google実装の安全性合格や全CI成功に読み替えない。共有対象の実行排他6ファイルは未コミットの別worktreeへ保持し、このCI修正へ混ぜない。今回候補の全CIと排他側の広域回帰は未完了。

- 最新の[worker固定本文消費](GOOGLE_WORKER_SNAPSHOT_2026-10-07.md): Calendar/Sheets workerが受付の固定本文・操作・対象を使用し、構造/資格情報/同期行incarnation/暗号文/採番/対象keyを照合する。HTTP間の受付喪失・認証済み別本文への差し替えは続送を止め、部分Sheets適用後はUNCERTAINを保持。最終PG410成功/省略0・SQLite388成功/PG専用22省略、製品差分97文36分岐先100%/除外0、新規20試験346文82分岐先/合成Sheets helper22文2分岐先100%、Python17品質/Bandit0・schema差分0。先行fixture/受付後ID変更の失敗を保持して実受付方式に更新、専用PG/tmpfs撤去・証拠/別作業保持。共有holder/FIFO開始・HTTP intent/receipt・独立unknown journal・後続PENDING保全/全lock順/移行/drain/回復は未完了。親d84 CI全6成功と今回候補CIを区別し、main/AWS/共有DB/Secrets/課金/容量変更・承認拡張なし、No-Goを維持する。

### 先行の受付実装（検証時点）

- 最新の[全5経路の固定受付](GOOGLE_WRITE_INTAKE_2026-10-07.md): Calendar/Sheets/両retry/自動同期のjob・固定本文/接続/incarnation・admission/sequence・outboxを原子的に保存。認可再検査、日本語400、失効owner単位のrollback、セッション編集の500防止、期限処理のjob削除件数を修正した。最終PG389成功/省略0・SQLite367成功/PG専用22省略、製品差分92文16分岐先100%/除外0・新規PG348文72分岐先100%、Python7品質/Bandit0・schema差分0。実PGのproducer lock順と別owner/接続/rangeの共有Sheet採番を確認し、先行driver3エラー/coverage不足等を保持して再検証、専用PG/tmpfs撤去・証拠/別作業保持。worker snapshot消費・共有holder・HTTP intent/receipt・独立unknown journal・全lock順/移行/回復は未完了。親75b CI全6成功と今回候補CIを区別。main/AWS/共有DB/Secrets/課金/容量変更・承認拡張なし、No-Goを維持する。

### 先行単位（各記録時点）

- [受付台帳・固定snapshot基盤](GOOGLE_WRITE_ADMISSION_2026-10-06.md): 内部3テーブル・確定FIFO採番・暗号化snapshot・rollback/同job冪等/旧raw DELETE互換を追加。最終PG368成功/省略0・SQLite349成功/PG専用19省略、製品差分178文48分岐先100%/除外0・新規PG452文44分岐先100%、Python8品質/Bandit0・schema差分0。実PG独立接続のsource/対象lock待機と固定snapshotを観測し、先行RED/旧migration復元不足による4エラーを保持して修正。専用PG/tmpfs撤去・証拠/別作業保持。全5producer/worker/HTTP/receipt/対象待機は未接続で、共有対象の排他・unknown保持の完成ではない。新migration0059/0060は隔離DBのみ、通常新配布物/実Google/保持方針等は残る。共有DB/main/AWS/Secrets/課金/容量変更・承認拡張なし、No-Goを維持する。

- [対象単位の世代・排他設計](GOOGLE_TARGET_FENCE_DESIGN_2026-10-06.md): a91be6b8で別Calendar jobの二重RUNNING/HTTP許可、古いreceiptによる新PENDING上書き、Sheets UNCERTAIN後の別job書き込みをSQLite/PG各3ケースで再現。mock HTTP・同一接続の順序制御であり、安全性合格や実worker競合の証拠ではない。対象FIFO・immutable snapshot・job削除で消えない未解決holder・共有spreadsheet排他・legacy/drain・限定回復の不変条件と15受入項目を整理。文書のみで実装/配備未完了、No-Goを維持。

- [手動再試行の元ジョブ停止](GOOGLE_RETRY_SUPERSESSION_2026-10-06.md): 同じ元FAILED行の再試行受付とworker開始を行ロックで直列化し、元payloadの非公開停止markerを後続作成と同時保存する。二重受付409・後続削除後の元再開拒否・旧relay/worker/Calendar保存の拒否を実装。通常の新規同期・同一予定/重なるSheets領域の共有世代排他、結果照合/限定回復は残り、全体完了とはしない。

- 最新の[2261adf7通常配布物・実プロセス回復](GOOGLE_DURABLE_RUNTIME_2026-10-06.md): 選定713 source/assets・111 packages/先行依存10層一致、通常回帰Google251/設定70の非重複321成功。実PG/Redis/Requests・solo/prefork×Calendar/Sheetsの16ケースでproducer commit後停止、relay停止の実5分期限、未消費message消失、制御されたACK喪失から同じjobを回復。期限内relay4回拒否・重複16配送の追加HTTP0・暗号文消去を確認した。候補CI全6成功。新規Scout HIGH3含む39/終了2は未合格。自分の83 container/tmpfsを撤去・証拠保持、main/AWS/共有DB/Secrets/課金/容量変更なし。自動常設回復/世代fence/結果照合/限定回復/実Google等は残る。

- アプリ28ac2bc7は応答喪失/408/5xx/不正ACK/部分Sheets後続拒否を結果不明へ分類し、自動再適用を抑止。親CI全6成功。
- [通常28ac実worker](GOOGLE_WRITE_RUNTIME_2026-10-06.md): 回帰284成功、実PG/Redis/Celery/Requestsの28ケース（結果不明22/成功6）、追加28重複配送のHTTP0を確認。実Google/AWSではない。
- [先行DB確定後投入](GOOGLE_DISPATCH_COMMIT_2026-10-06.md): commit待機/rollback破棄、PG265成功/省略0、SQLite256成功/PG専用9省略、製品差分34文20経路100%。その時点のcallbackはメモリ内でありoutboxなし。親62573a06のCI全6成功を後続で確認した。
- [未開始ジョブの永続配送](GOOGLE_DURABLE_DISPATCH_2026-10-06.md): jobとAES-GCM暗号化配送意図の原子的保存、5分claim/上限付きrelay、投入ACK後も開始まで保持、開始receiptと暗号文消去の同時確定を実装。最終PG290成功/省略0、SQLite280成功/PG専用10省略、read-onlyソースbindのLinux設定70成功。新migration0057/0058は隔離DBのみ。通常新配布物・実Redis/独立workerのproducer停止/再起動は未検証、旧FAILEDと新job/同期対象世代fence・結果照合・限定回復は未実装。共有運用・Issue全体完了とは扱わない。

## 完成の受け入れ条件

- [ ] jobと配送意図を同じDB transactionで永続化し、commit直後のproducer停止でも回復可能にする。暗号化・内容binding・同時保存・callback喪失・通常配布物の実producer停止/独立relay回復はローカル検証済み。鍵ローテーション・共有運用時消去・バックアップprivacyの証拠は残る。
- [ ] 独立relayのclaim/期限/再試行/失われたpublish応答を検証する。PG独立connection・実5分期限、実別relay/Redis/worker・メッセージ消失・制御されたACK喪失・実worker重複受信は新候補で確認済み。取消競合・常設監視/beat・実共有運用は残る。
- [ ] 旧メッセージ・旧FAILED job・新しい別job/同期対象世代をfenceし、同一予定/Sheets領域の競合を安全に扱う。明示的な手動再試行系列の元停止は部分実装したが、新規同期同士・共有対象の世代排他は残る。
- [ ] Google側結果照合と限定回復を設計・実装・検証する。結果不明を成功/失敗と推測せず、保存期限処理だけで痕跡を消さない。
- [ ] 通常配布物・実Redis/別worker/独立producer/プロセス停止/再起動のfault試験で上記を証明する。
- [ ] 承認済み範囲で実Google OAuth更新/失効/連携設定変更を検証し、常設worker/監視の運用証拠を揃える。

## 承認境界と公開判断

main/AWS/共有DB/migration適用/Secrets/IAM/費用/実ユーザー変更・通知は別の具体案と承認が必要。この下書きは実行承認を拡張しない。OS HIGH3、実外部連携、課金、性能、復旧等の不足も残るため正式公開No-Goを維持する。
