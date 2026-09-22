# 最新検証済み候補の開発AWS反映案

対象: `f8aa55a95b54892020576b6a9b57085aae1835ec`。本案は[旧9889f4c8反映案](STRIPE_AWS_APP_APPROVAL_2026-09-19.md)の対象と手順を更新する。承認待ちであり、マージ・共有DB移行・AWS反映は実行していない。

## 対象と検証

- 環境: AWSアカウント083773015316、ap-northeast-1、ECS `tableno-aws-pre`、stg.tableno.jp。
- イメージ: `tableno:display-security-f8aa55a9`、ID `sha256:a3dee0c7341a22304da025e343e1cd239de81a9d664b785d3b41132afc0f019f`。
- 旧候補からの追加はOAuth障害処理、外部連携の失敗案内・再試行、Sheets分割出力・進捗、統計と技能名のHTML保護。
- アプリ・テスト候補1b051dbaの[CI全6ジョブ](https://github.com/sheepdog0820/iaia/actions/runs/35695689750)は成功。f8aa55a9との差分は文書のみであり、f8aa55a9自身のCI成功とは区別する。
- f8aa55a9の[配布物検証](CHARACTER_CUSTOM_SKILL_SECURITY_2026-09-22.md)で関連62テスト、修正JSのハッシュ一致、隔離PostgreSQL 18.3/Redisで全移行・静的収集・通常起動・readinessが成功。
- OS監査は36指摘（HIGH 2 / MEDIUM 1 / LOW 33）が残る。正式公開可能とはしない。
- mainからのDB差分はaccounts/0065・0066・0067の追加のみ。9889f4c8からDockerfile・entrypoint・依存ロック・課金監視コマンドに差分なし。先行DB復元・Stripe実試験の証拠と制約は旧反映案を継承する。

## 現在の稼働状態

2026-09-22 16:05 JST頃に読み取り確認した。

- origin/mainは`d875d028ede0b3172780d54d4baacdb226a1d3b3`で候補の祖先。
- STSのアカウントは083773015316。以前のAWS認証切れは今回確認時点で解消。
- ECS定義49、desired/running=1、pending=0、CPU256・メモリ512。
- 定義49のイメージdigestは`sha256:59542e45e5dc8e1e33cbf7202eb12911ffbb390156a778fe7eb11f0fe4c65f79`。
- RDSはPostgreSQL 18.3、available、バックアップ保持7日、最新復元可能時刻2026-09-22 06:59:04 UTC。
- HTTP readinessはdatabase/cacheとも`ok`。

適用直前に再確認する。共有DBの適用履歴は今回直接照会していない。

## 承認対象の操作

1. 候補f8aa55a9をmainへ通常マージする。mainの未知の更新や競合があれば停止する。
2. 検証済みイメージをECRの`aws-pre-f8aa55a9`へpushしdigestを記録する。現行定義49を基にイメージだけを差し替え、CPU・メモリ・台数・役割・環境変数・Secrets参照・ネットワークを維持する。
3. 新定義の単発タスクで`migrate --plan`を確認する。想定はaccounts 0065 StripeBillingRequest、0066 StripeInvoiceState、0067 BillingEmailDeliveryの新規3テーブル。想定外なら停止する。
4. 上記移行を共有DBへ適用し、終了0と`migrate --check`を確認する。失敗時は旧Webを維持する。逆マイグレーションは行わない。
5. 新定義で`collectstatic --noinput`を実行し終了0を確認する。旧版と共有する静的パスを更新するため、事前に変更対象JSの旧S3オブジェクトのVersionIdまたは復旧用コピーを確保する。復旧手段を確保できなければ更新前に停止する。
6. Webを新定義へ更新し安定化を待つ。静的CloudFront `E3RQ829D1NVY28`の`/static/*`を無効化し完了を確認する。
7. 稼働タスクの定義・digest、readiness、ログイン、連携設定、統計、6版/7版作成画面を確認する。修正JSのS3存在・CloudFront応答・配信ハッシュ・構文と実画面表示を確認する。

全体terraform applyは含めない。追加3テーブルは既存テーブルの削除や既存データ書換えを含まない。

## 費用・対象外・復旧

ECR保存、短時間の単発タスク、静的保存・配信・無効化、ログの従量費用は発生する。常設Web増量、Redis/worker/beat増設は含めない。

Stripeキー・Price・Webhook設定、購入・メール配送有効化、OAuth scope、Secrets、IAM/SG、本番環境、実メール送信は対象外とする。

新Webが健全化しなければ定義49へ戻す。静的障害では記録した旧オブジェクトを復元してCloudFrontを無効化する。旧JSには今回修正した表示上の脆弱性が戻るため、切戻しを安全性の回復とみなさず、影響画面の利用制限または修正版再配信を判断する。

追加3テーブルは残す。既存データの復元・削除が必要なら影響を提示して別途判断する。切戻し後もreadinessと主要導線を確認する。

開発環境への反映は正式公開承認ではない。OS指摘、AWS課金・実OAuth・通知、常設worker、実メール、性能・復旧・事業運用が残り、正式公開No-Goを維持する。
