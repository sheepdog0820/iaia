# 検証済みStripe候補のmain・開発AWSアプリ反映 承認案

対象コミット: `99acd8ca4d319c2579f74e4c1a102815ccd4a668`。
対象環境: AWSアカウント083773015316、ap-northeast-1、ECS tableno-aws-pre、stg.tableno.jp。
現在のmain: d875d028ede0b3172780d54d4baacdb226a1d3b3。稼働ECS定義49、aws-pre-d875d028。

## 検証済みの根拠

- CI run 35431750178の6ジョブすべて成功: Unit / Integration、PostgreSQL、Playwright、infrastructure、lint/security、system。
- 同一SHAのコンテナをビルドし、起動とHTTP readiness成功。
- PostgreSQL 18.3で旧版→0065/0066/0067→新版、旧版での読出し、新版への復帰を確認。既存データと未配送記録を保持。
- pg_dump/pg_restoreで既存データと追加3テーブルが一致。実AWSはPostgreSQL 18.3、バックアップ保持7日、確認時の最新復元可能時刻は2026-09-19 17:28:41 JST。
- 詳細: STRIPE_CANDIDATE_CONTAINER_2026-09-19.md、STRIPE_CANDIDATE_CONTAINER_RESULT_2026-09-19.json、STRIPE_CANDIDATE_CI_2026-09-19.json。

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
