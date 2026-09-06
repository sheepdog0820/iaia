# 外部連携・定期処理のAWS構成レビュー

2026-09-06、9a756381時点のソースと既存aws-preの設定・stateを読み取りで照合した。非同期連携と清掃・予約公開等の実行基盤を確認するための調査であり、配備承認の最終資料ではない。Terraform apply、サービス作成、通知送信、費用が増える操作は行っていない。

## 現在の設定

ローカルaws-pre.tfvarsはenable_elasticache/enable_worker_service/enable_beat_serviceをすべてfalse、worker/beat desired_countを0としていた。worker/beatは各256 CPU units・512 MiB。enable_nat_gateway=false、enable_off_hours_schedule=true。AWSの専用worker/beatサービスがMISSINGなのは、この設定と一致する。過去の構成を無断で復元する理由にはしない。

backendのbucket/keyはaws-pre用、workspaceはdefaultであることを確認した。現在のstateを読む際もprofile tableno-preと東京リージョンを明示した。stateやplanの秘密値は本資料に掲載しない。

## 確認用plan

実際のtfvarsを変更せず、ElastiCache・worker・beatを有効、worker/beat各1という5つの上書き引数でplanを作成した。初回のPowerShell引数解釈による停止後、Pythonの引数配列で実行し終了0。ロックを無効にした読み取り計画であり、そのまま実行に使わない。適用時には最新stateと確定した入力で再planが必要。

| 操作 | リソース |
| --- | --- |
| 新規作成4件 | workerサービス、beatサービス、cache.t4g.microのRedis1ノード、ElastiCacheサブネットグループ |
| task definitionの置換4件 | web、worker、beat、背景透過。Terraform集計上は各create/delete |
| 更新4件 | webサービス、背景透過起動IAM policy、S3バケットpolicy、data security group |

合計は8 add / 4 change / 4 destroy。destroyの4件は登録済みtask definitionの置換で、RDSやS3バケット本体の削除ではない。ただし古いtask definitionの扱いと復旧対象は適用前に確認する。

このplanには次の未解決事項がある。

- container_image入力はaws-pre-2b2f02a3のまま。webサービスの現在のtask definitionは40であり、既に確認した稼働イメージaws-pre-8cf3c7f7や検証済みアプリ候補01a52f52とは異なる。入力を固定・照合せずに適用しない。
- S3 policyへのDenyPublicPrivateMediaDownloads追加が含まれる。既存の秘匿ファイル公開経路対策だが、非同期基盤だけの変更ではない。配信確認・キャッシュ失効・権限変更の承認範囲を別途具体化する。
- ElastiCache有効化はブローカー追加だけではなく、Webのセッション保存先をDBからRedisへ変更し、WebSocketも有効にする。既存ログインセッションへの影響と切替方法が必要。
- 現行の夜間停止設定はweb/RDSが中心で、worker/beatの停止・再開を含む整合確認が必要。RDS停止中に定期処理を動かす構成をそのまま採用しない。
- worker/beatを起動すると、待機中ジョブや予約HO公開、清掃、外部通知が実行され得る。テストキュー・テスト宛先・処理対象を確認し、既存ユーザーへの通知やデータ変更を無断で開始しない。
- Redisは1ノードであり、高可用性やキューの耐久性・復旧時間が実証された構成ではない。必要規模とRPO/RTOは未確定。

## 追加基本料金の試算

AWS Price List APIを2026-09-06に取得。東京、Linux/x86 Fargate、オンデマンド、730時間/月、worker/beat各0.25vCPU・0.5GiB・public IPv4各1、Redis OSS cache.t4g.microを1台の条件。現在のweb/RDS等の費用に加算される概算で、契約・利用開始・予算承認ではない。

| 項目 | 単価（USD/時） | 月額計算（USD） |
| --- | --- | --- |
| Fargate CPU | 0.05056/vCPU | 0.5 × 0.05056 × 730 = 18.4544 |
| Fargate memory | 0.00553/GiB | 1 × 0.00553 × 730 = 4.0369 |
| public IPv4 | 0.005/個 | 2 × 0.005 × 730 = 7.30 |
| Redis OSS cache.t4g.micro | 0.025/ノード | 0.025 × 730 = 18.25 |
| 合計 | | 約48.04/月 |

料金体系は[AWS Fargate](https://aws.amazon.com/fargate/pricing/)、[ElastiCache](https://aws.amazon.com/elasticache/pricing/)、[public IPv4](https://aws.amazon.com/vpc/pricing/)を参照。税、為替、通信、ログ、追加スナップショット、Redisの延長サポート、デプロイ中の重複タスク等は含めない。夜間停止を正しく設計すればFargate/IPの稼働時間は減るが、未実装の節約を計上しない。Redisの実エンジン版・保守条件も適用前に固定する。

## 次の実施条件

採用する稼働方式・費用上限・夜間運用を確定し、既存セッションとテストキューへの影響を抑える構成案を作る。候補イメージを固定し、S3/IAM/DBの変更範囲、実TLS接続、検証用データと宛先、失敗時の停止・復旧手順まで準備した後に、具体的な適用の承認を求める。現時点でこの確認用planの適用は推奨しない。

ローカル証跡: tmp/aws-pre-async-review-plan-final.log、tmp/aws-pre-async-review.tfplan、tmp/aws-pre-async-review-summary.json、tmp/aws-pre-async-review-effects.json、tmp/aws-pre-async-prices.json。planの生データは秘密値を含み得るためGitへ追加しない。
