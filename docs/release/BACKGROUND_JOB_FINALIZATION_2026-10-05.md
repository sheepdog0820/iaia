# 背景透過の終端状態・タイムアウト競合防止（2026-10-05）

## 修正と利用者への影響

先行通常配布物の検証後、workerとタイムアウト処理の競合を隔離DBで追加確認し、次を再現・修正した。

- タイムアウト済みジョブが、遅いworkerの成功でcompletedへ戻り結果画像が公開される。
- 同じ遅いworkerの失敗が、既存のタイムアウト理由を汎用失敗へ上書きする。
- 古いpending/runningの取得結果が、既に完了したジョブや新しくclaimされたジョブを誤ってタイムアウトにする。
- 削除されたジョブに遅い結果画像を保存した後でDB更新が失敗し、参照のない画像が残る。
- PostgreSQLで行ロック待ちに入る前に、timeout側が元画像を削除、worker側が結果を保存してしまう。
- Windowsでは推論中まで元画像を開いたままにするため、並行削除がWinError32で失敗する。

`fail_stale_background_removal_job` は同じジョブの行ロック取得とrefresh後に現在状態・更新時刻を判定する。呼出し元のinstanceもrefreshするため、status APIの返却判断も最新になる。消えた行は再作成せずfalseを返す。

`process_background_removal_job` は元画像の読み出し後にfileを閉じ、推論とPNG確認をロック外で実施する。結果確定時には同じ行をロック/refreshし、まだrunningの場合にだけ結果保存・状態/元画像参照を更新する。他の終端状態になっていれば上書きせず、その最新状態を返す。削除済みなら遅い結果を作らず、保持していた元画像をcleanupしてDoesNotExistを返す（管理コマンドが終了1として扱う）。

PNG確認・storage保存失敗の汎用エラー、既存filename sanitization/fallback、単発Fargateコマンド、U2NET/CPU/telemetry opt-outを維持した。モデル/権限/プレミアム価格/日次上限/24時間と7日の保持設定を変更していない。DBスキーマ変更・マイグレーションはない。

## TDD・回帰・実行範囲

- ソース変更前に6再現テストを追加し、SQLiteで4 failure/2 errorを確認。PostgreSQLの行ロック2テストも先行追加し、8テストで6 failure/2 errorを確認した。推論中のfile handle試験もWindowsで先行失敗を確認してから修正した。
- 新規15テスト：競合/削除/ファイル閉鎖/不正出力/storage異常/filename/元画像なし、実PostgreSQL行ロック2ケースとロック観測がなければ失敗する診断1ケース。観測なしを成功にするfallbackや試験時間延長はしていない。
- 最終Windows/SQLiteは89件中86成功・PostgreSQL専用3省略、15.695秒。隔離PostgreSQL18.3では同じ89件全成功・省略0、14.128秒。関連背景透過API25件/model6件/infrastructure4件/release documentation39件を含む。
- PostgreSQLでは別connection/threadと `pg_blocking_pids` により、親transactionのジョブ行ロック待ちを直接assert。待機中の元画像保持と結果未作成、commit後の最新completed/failedの維持を確認した。sleepだけを競合証拠にはしていない。
- source read-only mountを使うLinuxソース検証であり、今回修正の通常配布物検証ではない。先行c7390ee3 runtime imageを実行環境に使ったが、新しいソースと区別する。coverage7.15.4のみreadonly mountしてpure Python tracerを使用し、SDK/native dependencyを差し替えていない。モデル推論/ECS/S3はこの回帰ではmockで、実クラウドの競合/性能を証明しない。
- CI Production Databaseの明示対象に新しいintegration testを追加した。SQLite側で省略される実行を、CIのPostgreSQLで実施する構成。今回候補のCI結果はpush後に確認する。

coverage JSONの関数別計測は、timeout判定17文/6分岐とworker44文/12分岐の合計61文/18分岐を全実行、未実行/除外0。新規テスト223文/4分岐も100%、除外0。未変更のdispatch/保持cleanup等や全アプリの100%とは扱わない。

Python3.11.1で変更Python2ファイルのBlack/isort/Flake8成功、Bandit指摘0/エラー0。実diffを状態遷移・削除・アクセス制御・ロック順序/異常系の観点で自己レビューし、当該修正に要修正指摘なし。新しい利用者向け文言/UIはなく、既存英語エラーの日本語化は今回変更していない。文書追加後の39テスト成功、代表証拠7hash一致、文書2件の相対リンク189件欠落0。stage5テキストのUTF-8/LF/BOM/置換文字検査と空白差分検査も成功。

## 未確認・残条件・復旧

新しい通常イメージ/Web/実モデル/全OS監査/全CI/AWSは今回未確認。先行c7390ee3の[通常配布物とCI成功](BACKGROUND_WORKER_RUNTIME_C7390EE3_2026-10-05.md)を今回候補の証拠へ転用しない。先行OS39指摘（HIGH3/MEDIUM1/LOW35）を修正/再監査した変更でもない。

storage I/Oは結果確定・timeoutの行ロック中に行うため、実S3遅延/長時間待機/障害時の影響は追加検証が必要。DBとS3の分散transactionを保証する変更ではなく、storage成功後のDB障害/commit失敗・孤立ファイル回収の全経路は未証明。ECS受理後の応答消失・dispatch失敗とworker進行の競合等も、この2関数の合格に含めない。

main/AWS/ECR/共有DB/実データ/Secrets/IAM/課金/メール/容量は変更していない。完了済みfavicon承認と固定6b6c570cの反映案の対象を変えず、今回候補の反映は別途固定対象・検証・承認を確認する。[正式公開条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)はNo-Goを維持する。復旧は作業ブランチで当該修正をrevert可能だが、競合を再導入するため安全な修正版を優先する。実環境へ未反映なので実環境の切戻しは不要。

## 隔離証拠

`C:/tmp/iaia-background-finalization-20261005/` にRED/回帰/coverage/Bandit・PG containerの記録を保持する。test DBと媒体はすべて隔離fixture。最後に事前記録と同じPG container ID/network noneを再照合して停止・自動削除を確認し、使い捨てtmpfs DBを破棄した。実ユーザーデータはなく、証拠ファイルは保持する。

| ファイル | SHA256 |
|---|---|
| red.log | 25bc9d6c31cb2afbb0272d558364f2f5e0e4aa373c4d510bf97c86c5ab16d139 |
| postgres-red.log | 7f4283e0a5dac1ce6cc80abc4536aaf674add7eebe1e31ced0c809bd3549d438 |
| source-handle-red.log | 8238ecb019ebb86dbf4ce345803e6ab901b7a4ef3551e859b04773b9bbbc078e |
| sqlite-final.log | 123091bf1369e35f8592d82ccbea2e2170db563dc47a7f734e28cd7b7d487b78 |
| postgres-final.log | c33c9a0ba34f6b4b1f65f5907566b76703c320dc4002a6982844e6f69c3f8948 |
| coverage-pg-final.json | b76c919012da60d145d9a0b26f1ccdc0c28a983a80b053c262d1c7111ad60c4f |
| bandit-final.json | 652d896d4d91691f27d83380286aed50c6d9b60bd2c2db163b97e0caae9f6800 |
