# Stripe年額・返金・異議申し立て・再送の検証

2026-09-13、`codex/stripe-completion-20260913` のローカルコードを使い、サンドボックス `acct_1UFA5iE2s31mT3or` で実施。使い捨てSQLite、localhostのみの待受、メモリメールを使用した。読込元の `accounts/billing.py` がこのworktreeであることをassertしている。

## 成功した実接続試験

- 年額Priceで購読を作成し、Test Clockで翌年へ進め、4,800円の更新請求成功を確認。
- CLIから届いた実イベントの本文と署名をメモリ内で保持し、同じものを再送。HTTP 200・duplicate応答・監査ログ増加なしを確認。
- 隔離環境の購読同期処理を一度だけ意図的に失敗させ、HTTP 500とfailed記録を確認。故障注入を解除して同じ実イベントを再送し、succeededへ回復することを確認。
- 4,800円のテスト決済を実APIで返金し、署名付きWebhookで権限停止を確認。後続active通知でも返金済み権限を再付与しない。
- 公式PaymentMethod `pm_card_createDispute` で異議申し立てを発生させ、権限停止を確認。
- 公式テスト証拠 `winning_evidence` と `losing_evidence` を別のテスト購読で送信。実Stripe側のwon/lostと、アプリの権限復旧・停止維持を確認。

これらは [Stripe公式テスト手順](https://docs.stripe.com/testing) と [Webhook再送手順](https://docs.stripe.com/webhooks) に基づく。実カード・実課金・実ユーザーへのメール送信はない。故障注入時の500は意図したもので、最終的な受信イベントはすべてsucceeded。

## 実装修正

異議申し立てイベントにはcustomerがなく、Charge照会で顧客を特定することがある。従来はこの照会が失敗すると例外を握りつぶし、Webhookを成功済みにしていた。その後にStripeが同じイベントを送っても重複扱いになり、権限停止が抜ける。

照会失敗を通常のWebhook失敗処理へ伝播するよう修正した。再送時に照会が成功すれば権限停止を行い、以後は重複処理を避ける。回帰テストは修正前に失敗（期待500に対し200）、修正後は課金・法務・設定の232テスト成功（22.448秒）。Black、isort、flake8、Bandit、差分検査も成功。新しいDBスキーマ・表示文言はない。

実イベントと判定は [追加の証跡](STRIPE_ADDITIONAL_EVENTS_2026-09-13.json) を参照。スクリプトはGit管理外の `tmp/stripe_advanced_probe.py` と `tmp/stripe_dispute_probe.py`。署名、秘密鍵、顧客メール、Portal URLは記録から除外した。

## 残る確認

Webhookの順序逆転・並行実行、二重契約防止、年額Checkout画面と3D Secure、支払い方法更新画面、開発AWSの設定・Webhook・戻り導線、実運用メール・法務・販売開始条件は残る。この記録は正式公開の最終合格証拠ではない。

今回の3件のテスト購読はすべて解約済み。テスト商品・料金・顧客・時計・イベントは検証証拠として保持し、HTTPサーバー・CLI転送は停止、使い捨てDBは破棄した。AWS、本番設定、Stripe Taxは変更していない。コードのrevertは可能だが、照会失敗を成功扱いする旧不具合が戻る。
