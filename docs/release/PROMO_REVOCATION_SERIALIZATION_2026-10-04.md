# プレミアムコード由来権限の失効・監査の競合防止（2026-10-04）

## 発見・修正

[コード利用時の直列化](PREMIUM_CODE_SERIALIZATION_2026-10-04.md)に続き、期限失効と管理者のコード一括失効を確認した。取得済みの古い課金行で新しいStripe権限や延長済みの期限を上書きでき、古いコードを選択すると後から別コードで付与された権限まで失効した。また、監査ログの保存に失敗しても利用者・課金行の更新だけが残った。

専用ブランチ `codex/promo-revocation-serialization-20261004` で次を修正した。

- 期限失効・管理者失効が同じpromo対象条件を使い、Checkout/購入完了ハンドラーと共有するPremiumSubscription行をロックして対象条件を再確認する。JOIN先のuserまでロックせず、既存のsubscription→user更新順を維持する。
- 各対象の権限更新と監査ログを一つのtransactionにする。ログ保存失敗時はその対象の変更を戻す。複数対象の処理全体を一括rollbackする仕様ではない。
- 管理者失効ではロック取得後の最新コード利用履歴と選択対象を照合する。履歴時刻が同じ場合はpkで順序を確定し、古いコード・消失した履歴による失効を防ぐ。
- dry-runは件数取得のみ。既存の手動付与の保持、期限・価格・コードquota、監査metadata、日本語の件数メッセージは維持する。
- CIのPostgreSQLジョブへ、先行コード利用と今回の失効の両テストファイルを追加する。SQLiteで省略される行ロック試験をPGで実行するための変更で、AWSにアクセスするジョブではない。

DBスキーマ、Stripe SDK/API、Secrets/IAM、決済・税設定、実ユーザーデータは変更していない。Stripe監査スキルの方針に従い、Webhookによる権限反映を維持し、購入の戻り画面での付与へ置き換えていない。

## RED/GREENと回帰結果

修正前のSQLite試験は、最初の8件で4成功/4失敗、監査保存失敗等を追加した11件で4成功/7失敗（終了1）。古い取得結果によるStripe/延長期限の上書き、旧コード選択、時刻同値、履歴消失、監査保存失敗を再現した。最終版では履歴消失ケースを課金行取得後の削除に変更し、最新履歴がない場合のガードも実行した。

修正前のPG競合3件はすべて失敗（20.587秒、終了1）。期限処理2ワーカーが両方1件を失効した。購入完了ハンドラーとの2ケースは失効側がFOR UPDATEへ到達せず、ハンドラーの待機確認が10秒で失敗した。これはロック機構の不備の証拠であり、実Stripeとの通信試験ではない。

修正後の通常11件はSQLiteで全成功。PG専用3件を含む14件は全成功し、coverage付きの最終実行も14件成功（1.491秒、省略0）。実PG行ロックの待機をSQLで観測し、購入完了後のStripe source/status/購読IDを保持してpromo失効0件・失効監査0件となることを確認した。2期限ワーカーの結果は1/0・監査1件。実Stripe APIはmockで、外部署名付きWebhook配信や実課金は行っていない。

| 回帰環境 | 結果 | 実行時間 |
| --- | --- | --- |
| Windows Python3.11.1 / Django5.2.17 / SQLiteメモリDB | 300件成功・省略0・終了0 | 45.899秒 |
| Linux / 隔離PostgreSQL 18.3 | 315件成功・省略0・終了0 | 42.101秒 |

範囲はbilling、削除ガード、paid_feature_lifecycle、コード利用/失効、課金メール配送/監視、Stripeの請求順序・複数停止理由・Checkout再試行/順序・Dispute回復/順序/再試行・Portal解約。PGでは既存課金競合を加えた。HTTP警告・外部障害の例外ログは異常系の期待結果で、予期しないテストエラーはない。

## 検証環境・品質・証跡

PGは固定image `sha256:fbaa243599038521bbda8f6fa286d2a8fc1236509606f22de81d0739b0610ba7`、network none・公開ポートなし・512 MiB・DBデータtmpfs。アプリは先行通常image `sha256:cdaa475f53dc0f24c6f612d756a61f6047aed4f138a99cc94166194458da3391` に現在のbilling/adminと新規テストをread-onlyで重ねたもの。合成設定と使い捨てDBのみを使い、新修正の通常image構築・配布物全体の証明とは区別する。DjangoがテストDBを破棄し、今回専用のPG/coverageコンテナも停止・削除した。他のコンテナや実DBは操作していない。

既存coverage 7.15.4を検証ツールとしてread-only mountし、pytrace/thread tracingで計測した。新規テスト206文/12分岐、active_promo_subscriptionsの1文、expire_promo_subscriptionsの15文/6分岐、管理者失効の14文/6分岐はcoverageの計測対象で100%。billing/admin全体や全権限更新経路の100%を意味しない。

Black/isort/Flake8、差分空白検査が成功。Python3対象のBanditは0指摘・0エラー。workflow YAMLの構文とPG対象2ファイルを確認した。日本語の管理者件数表示を新規テストでassertし、新しい表示文言や画面レイアウト変更はない。行ロック順・再確認・履歴帰属・監査原子性・既存metadataを差分レビューし、この修正単位に追加の要修正指摘は残らない。

ローカル証跡は `C:/tmp/iaia-promo-revocation-20261004`。coverage出力前の初回コピーはファイル未作成で失敗し、同じ実行の正常終了後にコピーを完了した。試験の再起動や成功扱いへの置換は行っていない。

| 証跡 | SHA-256 |
| --- | --- |
| coverage-pg.json | feb2babafb5913ea227d9920ef8df9b8078efa9df9650ce5683af8f4977a307c |
| bandit.json | 1a3993d198ffb21b59af7eb4c3a2048c5adcca7350116df7c9cecb76be29422a |

## 未完了・反映境界

先行 `a0f94a40` の[CI全6項目success](https://github.com/sheepdog0820/iaia/actions/runs/37184128999)を確認した。GitHub CLIは未認証だったため、接続済みGitHubの読み取りで各ジョブを確認した。今回の新候補CI、通常配布物、AWS、実署名Webhookとの同時処理は別途必要。手動管理者付与等の全経路の競合、外部連携、正式公開B03/B04/Q04の全条件を合格にしない。

main・開発AWS・共有DB・実ユーザーデータ・Secrets/権限・課金有効化・容量/継続費用は変更していない。元checkoutのハンドアウト差分は保持した。[6b6c570c反映案](AWS_APP_APPROVAL_6B6C570C_2026-10-04.md)はその固定対象のままで、先行/今回の後続修正を無断で追加しない。既に完了したfavicon承認も拡張しない。

修正前へ戻すと誤失効・監査欠落を再導入するため、復旧は修正を保持したfix-forwardを優先する。今回は本番/共有環境への反映をしておらず、実データの復元は不要。[正式公開No-Go](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を維持する。
