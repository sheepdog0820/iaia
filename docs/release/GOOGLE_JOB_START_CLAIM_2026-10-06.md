# Googleジョブの開始取得と再入抑止

## 根拠・変更・利用者への影響

親は `cf8eba2935fd21742584486f79ad3ea34c2b2919`、専用ブランチは `codex/google-job-start-claim-20261006`。[Sheets所有権確認](GOOGLE_SHEETS_OWNERSHIP_2026-10-06.md)後も、Google workerは成功済み・実行中・期限超過のジョブを再び処理できた。実PGで2つのworkerが同じqueued jobを読むと、Calendar/Sheetsとも両方が配送することを合成応答で確認した。実brokerでの重複受信や実Googleの二重配送を観測した主張ではない。

- owner/type・対象存在の既存照合後、成功済み/実行中/不明状態/期限超過は内部結果`inactive-job`で終了する。payloadが不正でも保存結果・エラー・時刻・Calendar同期行を上書きせず、認可/token/HTTP/retryを呼ばない。
- 期限内のqueued/failedだけを、同じjob UUID/owner/type/現在status/現在期限を条件とする単一DB UPDATEでRUNNINGへ取得する。更新0件のworkerは追加処理をせず終了する。先の読み取りで開始可能だった場合も、開始UPDATEの現在条件で判定し直す。長いHTTP中にDBロックを保持しない。
- 取得は認可/対象検査のエラー保存より前に行い、取得できたworkerだけが既存の検査とジョブ状態変更へ進む。開始進捗は0、既存の認可確認後は10を維持する。DBのCoalesceで最初の開始時刻を保持し、再開始中に古いfinished_at/エラーを残さない。
- 既存の通信失敗後の同じjobの自動retryと、利用者の明示再試行で新jobを作る仕様は維持する。failedを開始可能として扱うため、任意の遅延duplicateと正規のretryを識別する仕組みではない。成功済みを繰り返し送らなくなるが、遠隔writeのexactly-onceを保証しない。
- 期限や保持期間を変更せず、期限切れ記録をここで削除・再保存しない。既存retention cleanupとGoogle接続/資格情報/対象/内容/現在所有権/ETag・RAW/100行分割/日本語失敗は維持する。新しい利用者向け文言は0件で、内部結果の英語tokenを画面に追加しない。

## TDD・検証と証拠の範囲

- 修正前SQLiteは7メソッド中21 failure/0 error/PG専用1省略（0.704秒）。期限超過、完了・実行中・不明状態、逐次再配送、実行中再入、過去finish残留を再現した。実PGの同時開始1メソッドはCalendar/Sheetsの2 subtest failure/0 error（0.514秒）で両worker成功を確認した。
- 初期PG GREENは新規7成功/省略0（1.417秒）。レビューで取得を認可/対象検査より前へ移し、競合fixtureは両workerがqueued状態を実際に読んだ直後のBarrierへ整理した。DBの開始UPDATE・Task本体を置換しない。新規7件のAPI生成/worker直接実行と、実PGの別接続2スレッドを使う。
- 最終PG199成功/省略0（105.833秒）、SQLite194成功/PG専用5省略（74.821秒）。文書39、Calendar実Requests＋loopback8ケース、既存PG認可/refresh競合4と今回開始競合1を含む。今回provider HTTP/queue投入はmock、unmocked Sessionは遮断しており、実Google/broker/常設worker/配布物/AWSの証拠ではない。
- 本体追加23実行文/10分岐（新規lifecycle 12/2、tasks差分11/8）は両DBで100%。新規試験151文/26分岐はPGで100%、SQLiteはPG専用23文/2分岐を省略して128文/24分岐である。全アプリ100%の主張ではない。3 PythonのBlack/isort/Flake8/Bandit合格・検出指摘0。既存日本語失敗とAPI契約は広域回帰で確認し、PG CI選定へ新規moduleを追加する。
- 文書追加後も文書回帰39件を再実行し、39成功（0.037秒）を確認した。

最終coverageは `D:/tmp/codex-google-job-start-claim-20261006-postgres-coverage.json`（SHA-256 `1eb9f7bd1062770e0f0f5ed1cd530f16f1d3a972d531d55bbad86ac8db4f64e1`）と `D:/tmp/codex-google-job-start-claim-20261006-sqlite-coverage.json`（`e4da78239cf7ac787b04f1cdcbdf35ad41280e4ad743ae2ada136dc033e48d1a`）。RED/初期GREEN/最終ログ、専用外部HTTP遮断runner、PG metadata/cleanup JSONを同じD:/tmp固有prefixに保持する。

専用PG `cde655ebe3dd` の完全ID/name/label・127.0.0.1:55441・匿名volume `aa6ddb955663` を照合した。試験DB0・fixture public tables0の後に停止/自動削除し、container/volume/55441待受残数0。元checkoutの無関係13変更・実データ・検証記録は削除していない。

## CI・未確認事項・復旧

先行cc1e497cの[CI 37419358489](https://github.com/sheepdog0820/iaia/actions/runs/37419358489)は全6成功。直前cf8eba29の[CI 37420502638](https://github.com/sheepdog0820/iaia/actions/runs/37420502638)は確認時点で5成功/Playwright実行中。同じ生きているrunを確認し、観測待ちを理由に再起動していない。今回候補の全CI/通常配布物は別検証である。関連open Issueはなく、先行のIssue作成403を記録済みのため権限/資格情報を変更せず、この記録/受入表へ残す。

取得後のプロセス停止・未知例外からの回復、期限超過/cleanup削除/状態変化を処理中にも再確認する仕組み、failed後の遅延duplicateと正規retryの識別、別jobが同じCalendar同期を処理する競合、遠隔応答喪失後の整合性、queue全入力型、接続先別外部ID/既存予定方針、実Google/OAuth審査等は残る。既存RUNNING jobを独断で解放・再実行せず、永続lease/自動回復やretry権限の新方針を完了扱いしない。開始取得後の所有権確認とHTTPも原子的ではない。

main/AWS/ECR/ECS/S3/CloudFront、共有DB/実ユーザーデータ、schema/migration、Secrets/IAM、課金/常設容量/継続費用、外部通知は変更していない。favicon承認・固定6b6c570c反映案の候補を拡張しない。復旧は通常revertでschema逆移行不要だが、成功/期限超過の再配送と同時開始の不足を再導入するためfix-forwardを優先する。受理済みの遠隔writeをrevertで復元できない。HIGH3/native閉包、実課金/連携・性能/運用/復旧/事業者対応等の未達を保持し、[正式公開](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)はNo-Goである。
