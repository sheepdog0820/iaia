# AWSの一時Redis・worker接続試験結果

2026-09-10、ユーザーが[一時試験案](GOOGLE_WORKER_CONNECTIVITY_APPROVAL_2026-09-10.md)を承認した後に実施。AWS上でRedisのTLS接続とCelery workerの応答確認が成功し、作成した一時リソースの削除まで完了した。Googleへの書き込み、Webへのブローカー設定、DB移行・業務データ変更は行っていない。

## 対象と結果

東京・アカウント083773015316、既存の開発VPCを使用。Redis7.1.0、cache.t4g.micro、1ノード、転送時/保存時暗号化有効。専用SGは既存ECS SGからTCP6379のみ許可し、既存DB用SGは変更しなかった。

workerは稼働Webと同じ20803480の通常イメージ（digest `sha256:64a901c0d3b8e4ac84f05ec8c706f735e2a257fa18564b5cab7a01e3e79282ee`）、0.25 CPU・512 MiB、concurrency=1。専用キューrelease-verificationを指定し、beatと業務タスクは起動していない。Webの定義45とサービス設定は変更していない。

| 確認 | 結果 |
| --- | --- |
| RedisのTLS証明書検証付きPING | 成功 |
| 対象worker指定のCelery ping | pong、成功 |
| DBセッション設定の維持 | 確認タスクで成功 |
| 上記の接続確認処理時間 | 約0.41秒（基盤起動時間を含まない） |
| workerと確認タスクの終了 | 両方STOPPED・終了0 |
| 起動/確認ログ | ERROR・Tracebackなし |

事前のローカル試験でも通常イメージとTLS専用Redisで起動・応答が成功し、信頼しない証明書の接続がCERTIFICATE_VERIFY_FAILEDで拒否された。AWS試験はAWSの通常CA信頼ストアで検証した。証明書検証を無効化して成功させたものではない。

試験タスク定義は `tableno-pre-worker-check-20260910:1`、workerは `da11f07dbdd948bfabd213be722318b2`、確認タスクは `19c7d66ce4bc400abd9ccdfd6d77eb19`。確認タスクは60秒の処理制限を設け、Redis接続と制御pingだけを実行した。Secretsの値やGoogleトークンは取得・記録していない。

## 削除・既存環境・費用

作成開始13:34:32 JST、最終確認13:50:35 JSTで、約16分。作成応答・専用タグ・IDを照合して後片付けした。最終確認で次を実証した。

- 試験replication groupと構成cache clusterが存在しない。
- 試験subnet group、専用SG `sg-022b1d8c94134782e`、そのSGを使うENIが存在しない。
- 両タスクは停止済み、専用定義はINACTIVE。
- 既存Webは定義45のまま稼働1/希望1、readinessは正常。試験後に継続稼働するRedis/workerはない。

承認案の最大4時間・概算$0.20に対し、約16分で削除確認まで終了。実請求額は未確定であり、稼働時間から確定請求額を断定しない。既存CloudWatchログには試験ログを保持する。新しい常設基盤やIAMポリシー変更はない。

## 残る公開条件

今回の成功は基盤の接続確認に限定する。常時workerと夜間停止の整合、監視、Webへのブローカー設定、Chromeログイン継続、Google Calendar/Sheetsへの限定データの実同期、取消・失効・再試行、beatの定期処理は未検証。これらとStripe・事業者情報等が残るため、正式公開はNo-Goを維持する。

証跡はGit管理外の `tmp/aws-worker-connectivity-20260910/` に作成応答、タスク定義、ログ、result.json、cleanup-verified.jsonを保存。生の設定JSONは公開資料へ転載しない。ローカル試験証跡は `tmp/worker-tls-20803480/`。
