# プレミアムコードと課金権限の競合防止（2026-10-04）

## 発見・修正範囲

正式公開B03/B04/Q04の監査で、`redeem_premium_access_code` が取得済みの利用者objectだけで権限を判断していることを確認した。別リクエストの付与後も古いfalseが残ると、同じ利用者が異なるコードを2個消費し、新しいStripeのactive/source/期限をpromo権限で上書きできる。古いtrueでは失効後も新コード利用を拒否し、再利用時の返却権限も古いままになる。

専用ブランチ `codex/premium-code-serialization-20261004` で、コード取得後にpremium/staff/superuserをDBから再取得する。新規利用時は既存Checkout/購入完了ハンドラーと同じPremiumSubscription行をロックし、権限とコード期限を使用直前に再確認する。コード行の既存ロックは保持し、異なる利用者の同一コード上限も維持する。既に権限がある場合や不正コードでは、新しい課金行を作らない。

コードの価格・使用回数上限・期限・一度使った同じコードを再消費しない仕様は変更しない。既存の付与・監査ログを一つのtransactionに保ち、subscription→user更新の順序はCheckoutと揃える。Stripe API/SDK/税設定/Secrets/実データへの変更はない。Stripe監査スキルのWebhookを権限更新の根拠とする方針を維持し、戻り画面での付与へ置き換えていない。

## REDとGREEN

- SQLiteの初期6ケースでは、既存premium/役割の再確認・失効後の利用・再利用の返却状態・別コード消費で失敗を確認。staff/superuserは最終fixtureで別利用者/別コードへ分け、失敗によるデータの混入を除いた。
- 修正前imageに最終段階の10テストだけをread-onlyで追加したPostgreSQL試験は、9 failure（8ケースが失敗し、役割の2サブケースを別failureとして計上）・終了1。異なるコードの同時利用は既存課金行あり/なしの双方で2つともTrueとなり、2個消費した。同一コード1回限りの2利用者試験は成功した。
- 購入完了ハンドラーが実PG行ロックを保持する試験も修正前は失敗。コード側が課金行のFOR UPDATEへ到達しないため、ハンドラー内の待機確認が10秒で失敗した。実Stripeはmockで、署名付き外部Webhook配信の試験ではない。
- ロック待ち中の期限切れは模擬時計で追加再現し、初期の直列化修正だけでは期限切れコードを消費した。期限再確認を追加して解消した。
- 最終版の新規12テスト（通常8・PG同時実行4）は隔離PostgreSQLで全成功（1.901秒、省略0）。同一利用者/異なるコード、初回課金行の同時作成、別利用者/同一コード、購入完了ハンドラーのロック待機を確認。後者ではDB SQLのFOR UPDATE到達を観測し、handlerの付与後にコード利用がFalse・use_count=0、source=stripe/status=active/購読ID保持となった。
- Windows Python3.11.1/Django5.2.17・SQLiteメモリDBの関連289テストは全成功（47.957秒、終了0、省略0）。Linux/隔離PostgreSQL 18.3では同じ範囲に既存課金競合と新規PGケースを加え、301テスト全成功（38.321秒、終了0、省略0）。予期された拒否/外部障害のHTTP警告は異常系テストのもので、予期しないテストエラーはない。

回帰対象はaccountsのbilling・billing_deletion_guard（PGではbilling_concurrencyも追加）、paid_feature_lifecycle、新規serialization、課金メール配送/監視、Stripeの請求順序・複数停止理由・Checkout再試行/順序・Dispute回復/順序/再試行・Portal解約。外部Stripe/SMTPはmockまたはlocmemであり、実送信・実決済・AWS購入の成功証拠ではない。

## 検証環境・品質

PGは固定image `sha256:fbaa243599038521bbda8f6fa286d2a8fc1236509606f22de81d0739b0610ba7`、network none・公開ポートなし・512 MiB・DBデータtmpfs。アプリは先行の通常image `sha256:cdaa475f53dc0f24c6f612d756a61f6047aed4f138a99cc94166194458da3391` の `/app/accounts/billing.py` と新規テストだけをread-onlyで重ねたもの。新修正の通常image再構築/全配布物監査ではない。検証用設定/認証情報/DBは合成。DjangoがテストDBを破棄し、専用PG/coverage/reportコンテナも停止・削除済み。他のコンテナや実DBは操作していない。

Linux coverageは検証用に既存coverage 7.15.4のPython packageをread-only mountし、pytrace/thread tracingを使った。配布imageの依存へ追加していない。新規テスト193文・4分岐が100%、追加したアプリ実行行8行もすべて実行した。redeem関数全体は既存の空コード拒否1文/1分岐が今回の選択範囲では未実行（36/37文・13/14分岐）で、billing全体100%の意味ではない。

Black/isort/Flake8・差分空白検査は成功。対象Python2ファイルのBanditは0指摘・0エラー。新しい表示文言は追加せず、期限切れには既存の日本語エラーを使う。コード/課金のロック順・原子性・quota・監査重複と実差分を自己レビューし、この変更に追加の要修正指摘は残らない。

証跡は `C:/tmp/iaia-premium-code-serialization-20261004`。SHA-256:

| 証跡 | SHA-256 |
| --- | --- |
| coverage-sqlite.json | c7940475370b52b91d8ec42664ab414538ee4d4132ab7621e6d3140bb9e95dff |
| coverage-pg.json | 985d9644462386290742637ff48e604a161a4f1eb3e1086610bd3beb0b61c6ff |
| bandit.json | bc5bc263c7608d5efc8f11e434fee1d1f8db64fb923e72c51b0fa0e3513241f6 |

## 未完了・反映境界

今回の修正は作業ブランチのみ。新候補のCI/通常配布物/AWSでの認証済み操作、実署名Webhookとの同時処理は未確認。手動管理者付与やpromo期限処理/管理者失効の全経路の同時実行まで証明したものではない。復旧のため修正前へ戻すと余分なコード消費・課金権限上書きを再導入するため、修正を保持したfix-forwardを優先する。

main・開発AWS・共有DB移行・実利用者データ・Secrets/IAM/OAuth・税/課金設定・容量/継続費用は変更していない。元checkoutのハンドアウト差分を保持した。先行の[6b6c570c反映案](AWS_APP_APPROVAL_6B6C570C_2026-10-04.md)はその固定対象のままで、この後続修正を無断で追加しない。先行の文書コミットaf4cf683の[CI全6項目success](https://github.com/sheepdog0820/iaia/actions/runs/37182930598)は確認済みだが、今回の新修正へ拡張しない。[正式公開No-Go](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)は維持する。
