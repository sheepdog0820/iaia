# Stripe SDK / API更新のローカル検証

## 対象・承認境界

基準は `cd0cd9b429b2ad45cc24933c25fd8735036a98be`（アプリ本体 `2ff6a4c8`）。専用ブランチ `codex/stripe-sdk-api-upgrade-20261004` で、正式公開に必要なSDK/API更新・署名付きイベント対応と関連ゲートを修正した。元worktreeのハンドアウト変更は含めない。

今回はローカル実装・隔離テスト・通常commit/pushのみ。main/AWS反映、Stripe endpoint/アカウント/Price/キー設定、共有DB、課金、メール送信、IAM・Secrets・常設容量は変更していない。アイコン8567f49fの承認や、固定反映案6b6c570cの承認待ちを今回候補へ転用しない。正式公開 **No-Go** を維持する。

## 公式版と影響確認

- [公式API版管理](https://docs.stripe.com/api/versioning)をStripe CLI 1.53.0で取得し、currentが `2026-09-30.endive` と確認。スキル付属の版一覧は古いスナップショットなので採用しなかった。
- [SDK 16.0.0](https://github.com/stripe/stripe-python/releases/tag/v16.0.0)と[移行ガイド](https://github.com/stripe/stripe-python/wiki/Migration-guide-for-v16)を確認。Python 3.11で実SDKを使用し、3依存ロックを15.5.1から16.0.0へ更新した。pip-compileで3ロックを一時フォルダに解決し、他パッケージの固定版変更0。実ファイルはStripeブロックのみ更新し、無関係なハッシュ・整形・依存更新を混ぜない。
- SDKのReversal改名、StripeObject.request削除、path引数の位置指定、Dahlia/Endiveの変更を対象コードと照合。アプリには該当旧メソッドやbilling_cycle_anchor更新、payment_method_types送信がない。Hosted Checkout、Customer Portal、snapshot Webhookを維持し、Elements/Connect/preview/thin eventへ切り替えていない。Stripe ID列は既存の255文字のまま。
- [Checkout追跡ラベル](https://docs.stripe.com/changelog/dahlia/2026-03-25/adds-integration-identifier-parameter-to-checkout-sessions)は8ランダム英字を含め、新規intentへ一度だけ保存。再試行は本文/冪等キーを維持し、旧intentへ後付けしない。比較では追跡ラベルだけを除外し、顧客・所有者・Price・プラン・復帰URLは従来どおり照合する。明示的な旧API設定には未対応パラメーターを送らない。
- [Endiveの一時停止/再開](https://docs.stripe.com/changelog/endive/2026-09-30/pause-subscription)とinvoice.paidを処理・必須購読・実イベント証拠・確認記録へ追加。署名後に最新Subscription/Invoiceを取得し、遅延したsnapshotで権限や支払い失敗状態を巻き戻さない。手動付与・有効promo・返金等の自動停止の既存方針は維持する。

`STRIPE_API_VERSION` を設定に宣言し、既定をEndiveへ固定した。明示設定は尊重し、空欄ではSDK/アカウント既定へ黙ってフォールバックしない。4環境サンプルと運用手順を更新した。`billing_stripe_remote_check` はendpointのAPI版を照合し、アカウント既定/不明・旧版・preview・同URLにある有効な重複endpointの版不一致を拒否する。コマンドがStripe側を書き換えることはない。

## TDDと検証

| 検証 | 結果・限定範囲 |
| --- | --- |
| 初期RED | 新規13件中8 failure/2 error。既定版、追跡ラベル、pause/resume、invoice.paid、版ゲートの欠落を再現。SDK16そのもののimport失敗ではない |
| 重複endpoint RED | 7件中1 failure。最初のendpointだけ一致すると誤合格する問題を再現し、修正 |
| 新規テスト | 実SDK+メモリーtransport+HMAC署名20件、production設定の新規2件。資格情報は使用不能な合成値で、Stripeへ送信しない |
| 最終隔離PostgreSQL 18.3 | **588件成功、省略0、93.591秒**。課金/認証/退会/管理/行ロック、CCFOLIA版保持、ICS権限/文字、リリース文書を含む34モジュール |
| 最終SQLite・カバレッジ | 517件中478成功/39省略、63.500秒。PG専用競合ケースは省略し、上記PGで別途成功 |
| production設定 | 別プロセスの28件成功。隔離DB設定のassertを継承した初回は既存loggingテストが失敗したため、production設定用プロセスで再確認。アプリ修正やテスト除外で回避していない |
| 変更箇所の計測 | 比較対象5本体モジュールの変更20実行文に未実行0/変更起点の未実行分岐0。新規テストモジュール208文/4分岐100%。既存モジュール全体100%とは主張しない |
| 品質・自己レビュー | 変更PythonのBlack/isort/Flake8、diff検査成功。新しい運用確認文言は日本語、API/status/設定名は技術トークンとして保持。画面デザイン変更なし。依頼範囲の差分に追加修正を要する問題なし |
| セキュリティ | 本体/新規テストのBandit指摘0、CIと同じaccounts/api/schedules/scenarios/support/tableno全対象も指摘0。別途広くtests/unit/test_production_settings.pyを含めた試行は既存fixture/subprocessのLOW26件・終了1であり、その試行全体を合格としない |
| Python依存監査 | runtime lock111パッケージ、Stripe16.0.0を含め既知の脆弱性0、終了0。OS監査ではない |

PGはネットワークnone・公開ポートなし・tmpfs・合成DBのみ。テスト用アプリは先行2ff6a4c8イメージへ今回ソース/SDKをread-onlyでmountした。この結果を**今回コミットの通常配布イメージ検証とは呼ばない**。独立する既存DB・AWS・Stripeへ接続せず、テスト終了後に一時PGを停止・除去済み。ログの503/500/403等は異常系テストの期待応答で、最終集計は上表に従う。

## 証拠ファイル

ローカル保存先: `C:/tmp/iaia-stripe-sdk-upgrade-20261004/`。SDK wheelのSHA-256は `6a401baf2fc19c59ccb59005e674f8da8fa256e8db319ad8c50292f4cddf8c26`（ロック/PyPI一致）。専用CLIはGitHub releaseのdigestとchecksum manifestを照合して取得し、既存CLI/ログイン設定は更新していない。

| ファイル | SHA-256 |
| --- | --- |
| red.log | 363be7a56aea280f7760aafbb324a48ecd38def72b14dc3f297bf31519a479a7 |
| duplicate-endpoint-red.log | e172bc32ca4378e6560a5aed49f88050cda0b3e94d5ccffdd155165d6a0e9f1b |
| pg-final.log | 44d2d7f4a31ee2c536da9e585122a02e4db6c6029bb20fa60c0281c5596cc9f3 |
| sqlite-final.log | 4f836fffc1f6be536944298c6b6e776228491fd9ae832489669fc0033405ac5d |
| coverage-final.json | c8ffa50183a9fc45f380b2ca9253b834e152e4d5eef7a3b1f0cc708c5e9eb942 |
| production-settings.log | f1715cb5f0a9e25ef7dc0b5c1b7258f033992475656177692ca46ca5292d7023 |
| runtime-audit.json | c3ae765fd209f2c63400730e188021ff592f31f9c87da4937cff65dc940f2372 |
| bandit-ci.json | 0769a9b8233b4349bdc246be2aeb341c9d7cc4bf85e2344bfab713ec33abf803 |

## 残作業・復旧

先行2ff6a4c8の[CI](https://github.com/sheepdog0820/iaia/actions/runs/37200546871)と文書cd0cd9b4の[CI](https://github.com/sheepdog0820/iaia/actions/runs/37201501893)はSHA/branch一致・全体successを後続確認した。今回候補のCI、通常配布物/OS監査、隔離Sandboxの実API/購入/Portal/署名付きイベントは別途必要で、先行合格を今回へ拡張しない。

[公式アップグレード手順](https://docs.stripe.com/upgrades)に従い、Webhook版/署名Secretsを含む切替と復旧計画を別途準備する。SDKのリクエスト版変更だけではWebhook/account版は変更されない。切替には対象環境と必要な承認を確認する。RAKの権限・remote-checkのキーprefix対応、共有DB0065〜0067、worker/メール・監視・税務/運営体制なども未完了。Stripe Taxのautomatic_taxや税登録は有効化していない。

ローカル変更は作業ブランチで通常revert可能で、モデル/DB移行はない。ただし将来の実環境ロールバックではEndiveで作成された未解決intentを旧APIへ無確認で再送しない。購入開始を止め、本文・キーを保持したままStripeの実状態を照合する。版を戻すために追跡ラベルや冪等キーを書き換えない。共有環境への復旧操作は別途承認対象。

管理削除/所有者変更方針、外部連携、性能/復旧、既存OS指摘等の受入条件は未達のまま。本記録は正式公開の合格や、本番/開発AWSへの反映完了ではない。
