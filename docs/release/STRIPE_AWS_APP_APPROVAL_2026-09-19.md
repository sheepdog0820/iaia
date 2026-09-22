# 検証済みStripe・Google統合候補のmain・開発AWSアプリ反映 承認案

対象コミット: `9889f4c8903658e6dfa0ddf4b25b8901e74b9bc9`。
旧候補bb61b0e6の案を置き換える。bb61b0e6の課金メール監視に加え、期限不明のGoogleアクセストークンをrefreshする修正・テスト・証跡を含む。監視の定期実行、Googleのscope/Secrets/公開設定変更、worker常設化は含まない。対象SHAのCI全6ジョブと通常配布物の隔離検証を確認済み。旧候補への承認を新候補への承認として扱わず、本案の操作について承認を得てから実行する。
対象環境: AWSアカウント083773015316、ap-northeast-1、ECS tableno-aws-pre、stg.tableno.jp。
現在のmain: d875d028ede0b3172780d54d4baacdb226a1d3b3。稼働ECS定義49、aws-pre-d875d028。

## 検証済みの根拠

- 候補の[CI run 35675930275](https://github.com/sheepdog0820/iaia/actions/runs/35675930275)はUnit / Integration、lint-security、production-database、infrastructure、playwright、systemの全6ジョブ成功。対象SHAとrun全体のsuccessを照合済み。[統合候補の検証記録](RUNTIME_CANDIDATE_9889F4C8_2026-09-22.md)を参照。
- 課金契約が残るアカウントの削除を、退会画面・通常API・管理者API・管理画面の単件/一括処理で拒否する。Webhookとの行ロック競合、通知未反映の契約、未確定のCheckout作成を含めて保護する。管理画面の一括削除は対象に削除不可の利用者がいれば全件をDB上でロールバックする。
- 関連252テストが隔離PostgreSQL 18.3で成功。実Stripeサンドボックスを使った4削除経路の23項目が成功し、試験用契約はすべて終了済み。[削除経路の検証](STRIPE_DELETION_PATHS_2026-09-19.md)、[実Stripe接続試験](STRIPE_DELETION_PATHS_API_2026-09-19.md)、[署名付き通知との競合試験](STRIPE_DELETION_RACE_2026-09-19.md)を参照。
- 9889f4c8から通常コンテナをビルドし、ネットワークなしのGoogle連携16テストとソースハッシュ、隔離PostgreSQL 18.3/Redis 7での全マイグレーション・collectstatic・通常起動・DB/cache readinessを確認。[統合候補の検証記録](RUNTIME_CANDIDATE_9889F4C8_2026-09-22.md)を参照。今回登録するローカルイメージIDは `sha256:af008fa03e3fa2f870ff40e596237750815cb2cfc3a45b221133e7032685819d`。
- bb61b0e6の隔離DBへのマイグレーション、実CLIの正常/異常終了とJSON・データ保持、コマンドのハッシュ照合の8項目も成功済み。[課金監視の配布イメージ検証](BILLING_EMAIL_HEALTH_2026-09-19.md)を参照。bb61b0e6から今回候補まで課金監視コマンド・DBマイグレーション・依存ロック・Dockerfile・entrypointに差分はない。
- 先行6ff9a1f9では隔離PostgreSQLへのマイグレーション、イメージ内9回帰テスト、5ソースファイルのハッシュ照合、通常起動とHTTP readinessが成功。[先行配布イメージ検証](STRIPE_CONTAINER_6FF9A1F9_2026-09-19.md)を参照。今回の追加コマンド以外の実行コード・DBマイグレーション・依存ロック・Dockerfile・entrypointに差分はなく、これらを今回再実施したと扱わない。
- 前候補0f6b81feではPostgreSQL 18.3で旧版→0065/0066/0067→新版、旧版での読出し、新版への復帰、pg_dump/pg_restoreによる既存データと追加3テーブルの保持を確認。0f6b81feから今回候補までDBマイグレーション・依存ロック・Dockerfile・entrypointの差分はない。今回同じ復元試験を再実施したとは扱わない。[前候補のDB検証](STRIPE_CONTAINER_0F6B81FE_2026-09-19.md)を参照。
- 実AWSの9月22日09:10 JST頃の読み取り確認ではPostgreSQL 18.3、バックアップ保持7日、ECS定義49、desired/runningとも1、CPU256/メモリ512、既存イメージdigest59542e45、readinessのdatabase/cacheともok。origin/main=d875d028が今回候補の祖先であることも確認した。
- 同日10:53 JSTのstg HTTP readinessはdatabase/cache正常。一方、AWS CLI資格情報が失効してECS/RDSの再取得はできなかった。前回値を最新状態へ読み替えず、反映前にAWS認証・稼働定義・バックアップ・復元可能時刻を再確認し、不一致なら停止する。

## 今回承認する操作

1. 他の変更を混ぜず、候補コミットをmainへ通常マージする。現在mainが祖先であることを再確認し、未知の変更・競合があれば停止する。force pushは使わない。
2. 検証したイメージをECRに登録し、現行ECS定義49のイメージのみを差し替えた新リビジョンを作る。CPU256・メモリ512・役割・環境変数・Secrets参照・ネットワークを維持する。
3. 新定義の単発タスクで共有DBのmigrate --planを確認する。想定はaccounts 0065 StripeBillingRequest、0066 StripeInvoiceState、0067 BillingEmailDeliveryの新規3テーブル。既に適用済みのものは再適用しない。これ以外の未適用変更や失敗があれば中止する。
4. 同じ新定義で共有DBへ上記マイグレーションを適用する。成功とmigrate --checkを確認後、Webサービスを新定義へ更新する。DB適用が失敗した場合は旧Webを維持する。
5. 稼働版・readiness・DB/cache・主要ログイン導線を確認し、反映記録を残す。課金設定の確認は読み取りに限定する。

追加3テーブルは既存テーブルの変更・削除やデータ書換えを含まない。実AWSの適用履歴の直接照会はECS Execが無効なため未実施であり、上記の単発タスクで確認してから適用する。Terraform stateはWeb定義36のため、全体terraform applyを使わず、現行定義49を基に限定操作する。

## 今回の対象外

Stripe Secret・Price・Webhook設定変更、購入有効化、メール配送有効化、常設Redis/worker/beat増設、IAM/SG変更、実メール送信、本番課金、本番環境への反映は行わない。これらは別の構成・費用承認が必要。追加したメールはDBの配送待ちとして保持されるが、worker未設置のため配送機能の完成確認にはならない。

常設Webの台数・CPU・メモリは増やさない。通常のECR保存・短時間の単発タスク・ログ等は発生する。今回は月約49米ドルの常設基盤増設を含まない。

## 切戻しと停止条件

新Webが健全化しない場合は既存定義49へ戻す。このアプリ反映に必要な切戻しも承認対象とする。追加3テーブルは残し、逆マイグレーションによるデータ消失を起こさない。既存データの復元・削除が必要なら、その影響を提示して再判断する。Secrets・権限・料金設定は変えない。

この反映だけでは有料正式公開条件は満たさない。AWSの既存Stripeキーは認証エラーで、常設worker/beatもない。これらの解決、実サービス検証と運用確認を続ける。正式公開はNo-Goのままとする。
