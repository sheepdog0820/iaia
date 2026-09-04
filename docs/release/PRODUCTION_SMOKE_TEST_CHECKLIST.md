# 本番スモークテスト手順

最終更新: 2026-09-05

この手順は `https://tableno.jp` にデプロイした後の最小確認です。実アカウント、実Secrets、実OAuth callback はリポジトリに記録しません。

## 事前条件

- DNS、ACM、ALB、ECS、RDS、ElastiCache、S3/CloudFront が本番値で構成済み。
- Google、Discord、Xの本番OAuth callback URLが登録済み。
- 管理者アカウントと初期運用権限が確定済み。
- 利用規約、プライバシーポリシー、特商法表示、問い合わせ先が本番実値で正式レビュー済み。
- 有料プランを含む正式公開では、Checkout有効と実Stripe test-mode event IDsを含む最終検証記録で `billing_release_gate --require-paid-checkout` が成功済み。

## 確認項目

| No | 確認 | 期待結果 | 結果 |
| --- | --- | --- | --- |
| 1 | `https://tableno.jp/health/live` | 200 | 未確認 |
| 2 | `https://tableno.jp/health/ready` | 200 | 未確認 |
| 3 | ホーム画面 | 表示できる | 未確認 |
| 4 | 通常ログイン | ログインできる | 未確認 |
| 5 | Google OAuth | callback成功、ログインまたは連携完了 | 未確認 |
| 6 | Discord OAuth | callback成功、ログインまたは連携完了 | 未確認 |
| 7 | X OAuth | callback成功、ログインまたは連携完了 | 未確認 |
| 8 | キャラクター作成 | 本番DBへ保存される | 未確認 |
| 9 | セッション作成 | 本番DBへ保存される | 未確認 |
| 10 | 外部連携設定 | Google/Discord設定画面が保存できる | 未確認 |
| 11 | CloudWatch Logs | web/worker/beatログが確認できる | 未確認 |
| 12 | CloudWatch Alarm | 通知先が実運用先になっている | 未確認 |
| 13 | 法務ページ | `/terms/`, `/privacy/`, `/contact/`, `/commercial-disclosure/` が本番実値で表示できる | 未確認 |
| 14 | 問い合わせ配送 | `/contact/` から実運用先へ通知またはメール配送される | 未確認 |
| 15 | Stripe Checkout公開ゲート | Checkout有効で `billing_release_gate --verification-record docs/runbooks/billing-verification-YYYYMMDD.md --require-paid-checkout` が成功 | 未確認 |
| 16 | Go/No-Go記録 | `docs/release/PRODUCTION_GO_NO_GO_RECORD_TEMPLATE.md` にOAuth/SNS/RDS/法務/Stripeの実確認結果を記録 | 未確認 |

## 記録欄

- 実施日時:
- 実施者:
- 対象revision / image:
- 問題:
- 判定:

有料正式公開ではCheckout無効を合格の代替条件にしない。ゲートは記録の形式検査であり、実イベントの真偽・料金の承認・本番設定の整合性を単独で証明しない。検証記録をStripeとアプリの実状態に照合し、人間の公開判断と併せて記録する。
