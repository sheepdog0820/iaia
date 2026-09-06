# aws-pre監視・バックアップ・非同期処理の確認

2026-09-06、profile tableno-pre、ap-northeast-1、対象アカウントをSTSで確認して読み取りのみ実施した。これは共有開発環境の観測であり、本番環境の運用実証ではない。

| 対象 | 確認結果 | 残る条件 |
| --- | --- | --- |
| ECSアプリ | tableno-aws-preはACTIVE、desired/running=1、pending=0 | 最新候補は未配備 |
| worker/beat | 手順書のtableno-aws-pre-worker、tableno-aws-pre-beatはdescribe-servicesでMISSING。タスク定義40のコンテナはwebのみ | 他の実行基盤の有無、ジョブ配送・定期実行を確認。必要な構成と費用を具体化してから承認対象を提示 |
| Redis | タスク定義40のUSE_REDIS_CACHE=false。REDIS_SSL_CERT_REQSの環境変数はなし | この観測だけでキューへの接続や別基盤の稼働を断定しない |
| CloudWatch Logs | /ecs/tableno-aws-pre、保持3日 | 本番で必要な調査期間・費用との合意 |
| CloudWatch Alarm | ALB target 5xx、ECS CPU、ECS memoryの3件、いずれもOK、ActionsEnabled=true、各通知action1件 | 異常発生時の検知と実通知到達は未実証。OKは配送成功の証拠ではない |
| SNS | 上記アラーム通知先の購読はemail1件、confirmed | 配送試験は未実施。宛先アドレスは記録しない |
| RDS | tableno-aws-pre、postgres、available、暗号化あり、削除保護あり、MultiAZ=false、自動バックアップ保持7日 | 合意RPO/RTO、障害時の復旧・独立バックアップの実証 |
| RDS復元点 | LatestRestorableTime=2026-09-06T02:30:26Z。取得時の自動snapshot11件はいずれもavailable・暗号化あり、最新は2026-09-05T16:06:18.053Z | 一覧の存在は復元成功や整合性の証拠ではない。実RDS復元は未実施 |

アプリのCELERY_BEAT_SCHEDULEには予約HO公開、ジョブ失効、有料期限更新、背景透過結果の清掃、祝日同期がある。Google Calendar/SheetsとDiscord配送もCeleryへの投入経路がある。専用サービスが見つからないため、これらの運用完了をアプリのreadinessだけで判定しない。

確認に使ったのはecs describe-services/describe-task-definition、logs describe-log-groups、cloudwatch describe-alarms、sns list-subscriptions-by-topic、rds describe-db-instances/describe-db-snapshots。Secrets取得、通知送信、リソース作成・更新・削除、DB変更は行っていない。

## Redisの証明書検証設定の修正

共有のTerraform main.tfに、Celery URLのssl_cert_reqs=CERT_NONEとDjango cacheのREDIS_SSL_CERT_REQS=noneが残っていた。2026-06-19の記録でも本番前の確認事項となっており、ElastiCacheを有効にした構成で検証が無効になるため、両方をrequiredへ修正した。Web・worker・beatの共通環境設定に適用される。実AWSへは適用していない。

[Celery公式設定資料](https://docs.celeryq.dev/en/stable/userguide/configuration.html#std-setting-broker_use_ssl)を参照し、Terraformに書かれた値を読み取って実際のKombu broker・Celery result backend・redis-py SSLConnectionへ渡す回帰テストを追加した。変更前はCERT_NONEとして2件失敗、変更後は双方CERT_REQUIREDを確認した。テストは外部へ接続しない。Celeryのcurrent appを変更せず他テストへ影響しないようにした。

初回の検証起動はENV_FILE未指定で停止し、隔離環境設定を明示して再実行した。最終の関連検証は27成功・4警告、17.42秒、終了0。Black/isort/flake8、terraform fmt -check main.tf、terraform validateは成功。証跡はtmp/redis-tls-red-final.log、tmp/redis-tls-final.log。差分・日本語文言・文字コード・自己レビューを確認した。変更はTerraform設定2箇所・回帰テスト・本資料で、DBスキーマ・実データ・Secrets・課金の変更はない。

本修正は証明書を信頼できない接続を拒否するため、適用前に実ElastiCacheでCAチェーン・名前照合を含むTLS接続を検証する。実TLS通信、実環境の上書き設定、Terraform plan/applyは未実施。既存環境へ自動反映しない。コードrevertは可能だが、証明書検証を無効へ戻す運用を復旧の標準にはせず、失敗時は適用を止め信頼設定を是正する。
