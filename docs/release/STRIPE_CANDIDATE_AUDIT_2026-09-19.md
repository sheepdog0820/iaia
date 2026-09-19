# Stripe候補の公開条件照合（2026-09-19）

対象は `codex/stripe-completion-20260913` の `69cfa8767b02dab8bd0a0dc9016132dcbe139f22`。9月19日にローカルHEAD・差分なしとGitHub Actionsの対象SHAを照合した。前回の実装・サンドボックス検証は進捗ありと判定する。前回のCI待ちは解消した。

## CIの確定結果

[run 34753811909](https://github.com/sheepdog0820/iaia/actions/runs/34753811909) は9月13日11:26:56 UTCにcompleted/success。jobs APIでも以下6ジョブすべてsuccessを確認した。

| ジョブ | 結果 |
| --- | --- |
| system | success |
| infrastructure | success |
| playwright | success |
| Unit / Integration | success |
| lint-security | success |
| production-database | success |

今回確認したのは対象コミットのCI結果。各テスト件数・カバレッジ率の再集計、9月19日のStripe/AWS実環境試験ではない。9月13日のサンドボックス試験は当日の証拠として扱い、現在も同じ外部設定であると推定しない。

## 課金条件の照合

| 条件 | 証拠 | 未完了・限界 |
| --- | --- | --- |
| B01 料金・機能差 | [実Price照合](STRIPE_SANDBOX_VERIFICATION_2026-09-13.md)：テスト用JPY480/月・4,800/年、同一商品。無料範囲・背景透過のみ有料は既存の承認仕様 | 本番Price・公開画面・AWS設定との最終一致は未証明 |
| B02 月額・年額購入 | [月額実画面・実Webhook](STRIPE_SANDBOX_VERIFICATION_2026-09-13.md)、[年額・3D Secure](STRIPE_ADDITIONAL_VERIFICATION_2026-09-13.md) | localhostの隔離DB。AWSのログイン済み購入・戻り画面は未確認 |
| B03 課金ライフサイクル | 月額・年額更新、失敗/回復、返金、異議申し立て、カード変更、期間末解約を実テスト。解約後の勝訴による権限復活も修正・実証 | 退会との組合せ、複数返金/異議申し立て、AWS上の全フローは未完了 |
| B04 重複・再送・順序 | 実署名付き通知の重複・失敗再送・購読通知の逆順を確認。[同時購入・応答喪失](STRIPE_CHECKOUT_RETRY_2026-09-13.md)も実APIと隔離PostgreSQLで検証 | 請求成功/失敗の順序、異種Webhook間の並行更新・一時DB障害の全組合せは未証明 |
| B05 有料必須ゲート | ゲートのローカル動作確認と個別の実サンドボックス証跡あり | 実AWSの有料有効状態の記録を独立照合し、必須ゲートを通過した証拠はない |

## 次の実行対象と承認境界

1. 請求成功/失敗の通知順序と、複数返金/異議申し立てが競合する場合の状態更新を実装・追加検証する。ローカルの隔離DBで着手できる。
2. その候補のCI・レビューを完了する。9月13日のDraft PR作成は連携の403で失敗しており、この監査ではPR権限を再試行していない。
3. mainマージと開発AWSへの反映に際しては、対象SHA・現在の稼働版・復旧手順を照合する。追加テーブル `accounts/0065_stripe_billing_requests` の共有DB適用、テストSecrets/Webhookの設定は承認対象。
4. 実画面・メール・開示運用と、Google等の外部連携、性能・復旧・監視の残条件を完了する。課金候補のCI成功を正式公開全体の合格へ拡張しない。

正式公開はNo-Goを維持。今回の変更は監査資料と判定表のみで、mainマージ、AWS反映、共有DB・Secrets・料金・契約・通知送信の変更は行っていない。
