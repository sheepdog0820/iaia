# workerの同時実行数を構成で明示

TerraformのCelery worker起動コマンドが同時実行数を省略しており、コンテナが認識するホストCPU数から子プロセス数を決める状態だった。固定の通常配布image `sha256:fbb579ed5d7ced7523a6414308354b23c70e2ec252c6a152245c2bad1c1dc6a5`を0.5 CPU・1 GiB・UID10001・root read-only・通信なしで初期化すると、OS認識16 CPU・worker concurrency16となった。

この初回検査ではworkerを起動せず、設定初期化だけを確認した。実FargateでOOMや処理失敗を観測した記録ではない。Celeryの[公式workerガイド](https://docs.celeryq.dev/en/stable/userguide/workers.html#concurrency)にある同時実行数指定を使い、環境ごとに意図した値へ固定する。

## 変更

- `worker_concurrency`を追加し、既定2、1以上の整数を要求する。0による自動CPU数への復帰、負数・小数を拒否する。
- workerの起動コマンドへ`--concurrency=<値>`を渡す。aws-preの設定例にも2を記載する。
- CPU・メモリ・サービス台数、キュー、worker poolの方式、beat、夜間スケジュール、Redis/Webセッション、権限・Secretsを変更しない。

これは同時実行数の既定を意図的に変える修正である。実際に適用する場合、以前の自動値より同時実行数が少なくなり、待ち時間や処理量が変わり得る。2を全業務・全容量の最適値や性能合格として扱わず、確定した容量・タスク内容で測定して必要なら構成値を選ぶ。

## TDD・隔離検証

Terraform mock providerで、変更前のコンテナ定義に同時実行数がないことによるテスト失敗を確認した。最初の検査ではmockのDB/配信先等が未確定で条件を評価できなかったため、fixture endpointだけをplan時に固定し、製品のコマンドによるREDを別に確認した。

変更後は既定2・指定3、0/負数/小数の拒否、既存のネットワーク・broker/Web保存分離・夜間停止を含む15試験が成功。標準・offline-plan例・aws-pre例の3入力で各15件、計45件成功・失敗0。実資源は作らず、providerは全mock、`offline_plan=true`を使う。fmt/validateと、設定例の書式確認も成功した。

上記の固定配布物から実Celery CLIを`--concurrency=2`で起動し、0.5 CPU・1 GiB・通信なし・root read-only・UID10001でprefork2、親を含む3プロセスを確認した。broker/DBは起動せず、業務タスクを投入していない。同じ所有済みコンテナを停止・削除し、不在を確認した。これは新しいTerraform branchの配布imageをビルドした証拠や、実broker配送・処理量/メモリ余裕の合格ではない。

## 適用・復旧・残る条件

mainマージ・Terraform apply・AWS資源作成/更新は未実施。worker task definitionの新revision登録を含む実反映と、継続基盤の費用は具体的な計画で別途承認を確認する。起動中workerの変更は既存処理の終了・未処理ジョブ・再配送も確認してから行う。

ソースはrevertで戻せるが、戻すとホストCPU数による自動設定へ戻る。実反映後の復旧は承認済みのtask definition・サービス構成に対して用意し、稼働workerを無断で停止しない。

共有DB、実データ、既存承認待ちPR56/57/58、固定3deによる5移行コピーリハーサルの対象は変更しない。OS52指摘、[全25受け入れ条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)、有料プラン・外部連携を含む正式公開No-Goを維持する。
