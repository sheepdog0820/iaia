# 開発AWS用Stripeキーの権限案

対象ソースは `bb61b0e6`（課金処理は6ff9a1f9と同一）。現行AWSキーの認証エラーを解消する準備として、実際のSDK呼出しを確認した。キー作成・権限変更・AWS Secrets更新は未実施。この資料は設定案であり、制限付きキーで全フローが成功した証拠ではない。

Stripeの[制限付きAPIキー](https://docs.stripe.com/keys/restricted-api-keys)の案内に沿い、承認済みサンドボックス `acct_1UFA5iE2s31mT3or` のサービス専用テストキーを推奨する。CLI用の期限付きキーや本番キーを転用しない。公式CLIのdocsプラグインが未利用だったため、公式Web文書を参照した。

## アプリ実行時の操作

| リソース | ソースで確認した操作 | 権限案 | 用途 |
| --- | --- | --- | --- |
| Customers | create | Write | 購入者の作成 |
| Checkout Sessions | create / list / retrieve / expire | Write | 購入、再試行、古い購入画面の失効、退会保護 |
| Billing Portal Sessions | create | Write | 支払い方法変更・解約画面へ移動 |
| Subscriptions | list / retrieve | Read | 二重契約防止、現在状態確認、退会保護、Webhook処理 |
| Invoices | retrieve | Read | 請求通知の順序逆転を現在状態と照合 |
| Charges | retrieve | Read | 返金・異議と購読の関連確認 |
| Disputes | retrieve | Read | 異議通知の現在状態確認 |

確認箇所は `accounts/billing.py`、`accounts/billing_deletion.py`、`accounts/views/billing_views.py`。Webhook署名のconstruct_eventは受信データのローカル検証であり、Webhook Endpointの管理API権限とは別。署名鍵は登録先エンドポイント固有のものを使用する。

表はソースの操作から推定した開始案。Dashboardでの権限分類や依存する権限は、実際の制限付きキーで検証し、拒否されたAPIのエラーとリクエストログに基づいて必要な範囲だけ補う。WriteはReadを含む。アプリは直接の返金作成・送金・銀行口座変更を呼び出しておらず、それらの権限はこの案に含めない。

## 管理コマンドとの区別

`billing_stripe_remote_check` はPriceのretrieve、Portal Configurationのlist、Webhook Endpointのlistを使い、`--require-recent-events` 指定時はEventのlistも使う。この読み取り検査用の権限は通常のWeb処理とは別に扱う。実行時は既存のSTRIPE_SECRET_KEY設定をプロセス限定で検査用キーへ差し替える必要があり、専用設定変数が実装済みという意味ではない。権限不足で検査が失敗した場合、検査を省略して合格扱いにしない。

`create_stripe_development_prices` はProduct作成/更新とPrice作成を行う。既存の商品・月額/年額Priceを利用する通常運用キーへ、これらの書き込み権限を追加しない。商品作成は設定作業として別途扱う。

## 設定後に確認する項目

1. キーを作るDashboardが指定サンドボックスであることを確認する。テスト用キーと指定Price/Portal設定が同じアカウントに属することを照合する。
2. [Secrets管理の公式案内](https://docs.stripe.com/keys-best-practices)に従いAWSの既存Secrets保管先へ安全に登録する。会話、Git、コマンド引数、平文ログへ値を出さない。変更対象・参照キー・切戻し方法を承認案で明示してから実行する。
3. 購入を無効に保ったまま、読み取り検査、署名検証、アプリ設定を確認する。既存AWSキーが認証エラーなので、旧値へ戻すだけでは課金機能が復旧するとは扱わない。
4. 隔離した利用者で月額/年額Checkout、Portal、請求失敗/回復、解約、返金/異議通知、退会を制限付きキーで検証する。新規キーが以前のCLIキーと同じ権限を持つと仮定しない。
5. キー作成/Secrets設定と、購入・実メール・本番課金の有効化を区別する。旧キーの廃止は他の利用元を確認し、対象を明示して扱う。

APIバージョン・SDK方式の移行はキー権限設定とは別の変更として検証する。今回それらを変更していない。常設配送基盤の費用承認や、main/共有DB/AWSへの反映承認をこの資料で代替しない。
