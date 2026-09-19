# 検証済みStripe候補のmain・開発AWSアプリ反映 承認案

対象コミット: `bb61b0e6244aa5c9726dca4b8b00c3dd29e9cf05`。
旧候補6ff9a1f9の案を置き換える。差分の実行コードは読み取り専用の課金メール監視コマンド1ファイルで、関連テストと文書を伴う。監視の定期実行や通知設定は含まない。対象SHAのCI全6ジョブ成功を確認済み。旧候補への承認を新候補への承認として扱わず、本案の操作について承認を得てから実行する。
対象環境: AWSアカウント083773015316、ap-northeast-1、ECS tableno-aws-pre、stg.tableno.jp。
現在のmain: d875d028ede0b3172780d54d4baacdb226a1d3b3。稼働ECS定義49、aws-pre-d875d028。

## 検証済みの根拠

- 候補の[CI run 35437997407](https://github.com/sheepdog0820/iaia/actions/runs/35437997407)はUnit / Integration、lint-security、production-database、infrastructure、playwright、systemの全6ジョブ成功。対象SHAとrun全体のsuccessを照合済み。[CI記録](STRIPE_CI_BB61B0E6_2026-09-19.json)を参照。
- 課金契約が残るアカウントの削除を、退会画面・通常API・管理者API・管理画面の単件/一括処理で拒否する。Webhookとの行ロック競合、通知未反映の契約、未確定のCheckout作成を含めて保護する。管理画面の一括削除は対象に削除不可の利用者がいれば全件をDB上でロールバックする。
- 関連252テストが隔離PostgreSQL 18.3で成功。実Stripeサンドボックスを使った4削除経路の23項目が成功し、試験用契約はすべて終了済み。[削除経路の検証](STRIPE_DELETION_PATHS_2026-09-19.md)、[実Stripe接続試験](STRIPE_DELETION_PATHS_API_2026-09-19.md)、[署名付き通知との競合試験](STRIPE_DELETION_RACE_2026-09-19.md)を参照。
- bb61b0e6から通常コンテナをビルドし、隔離DBへのマイグレーション、実CLIの正常/異常終了とJSON・データ保持、コマンドのハッシュ照合の8項目が成功。[配布イメージ検証](BILLING_EMAIL_HEALTH_2026-09-19.md)を参照。今回登録するローカルイメージIDは `sha256:e2d81b173fd6e7b632c0c2990e198559d6a669442bce85e6c7e4530961616fd3`。
- 先行6ff9a1f9では隔離PostgreSQLへのマイグレーション、イメージ内9回帰テスト、5ソースファイルのハッシュ照合、通常起動とHTTP readinessが成功。[先行配布イメージ検証](STRIPE_CONTAINER_6FF9A1F9_2026-09-19.md)を参照。今回の追加コマンド以外の実行コード・DBマイグレーション・依存ロック・Dockerfile・entrypointに差分はなく、これらを今回再実施したと扱わない。
- 前候補0f6b81feではPostgreSQL 18.3で旧版→0065/0066/0067→新版、旧版での読出し、新版への復帰、pg_dump/pg_restoreによる既存データと追加3テーブルの保持を確認。0f6b81feから今回候補までDBマイグレーション・依存ロック・Dockerfile・entrypointの差分はない。今回同じ復元試験を再実施したとは扱わない。[前候補のDB検証](STRIPE_CONTAINER_0F6B81FE_2026-09-19.md)を参照。
- 実AWSの読み取り確認時点（18:49 JST）ではPostgreSQL 18.3、バックアップ保持7日、最新復元可能時刻18:43:43 JST。ECS定義49、desired/runningとも1、readinessのdatabase/cacheともok。反映直前にmainと稼働定義を再確認し、変化があれば差分を再評価する。
- 19:58 JSTの再確認でもmain=d875d028、ECS定義49、desired/running=1、pending=0、rollout=COMPLETED、CPU256/メモリ512、既存イメージdigest59542e45、readinessのdatabase/cache正常。mainがbb61b0e6の祖先であることも確認した。RDSの復元時刻はこの再確認では取得していない。

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
