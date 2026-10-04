# Stripe制限付きキー対応の検証記録（2026-10-04）

正式公開は **No-Go** を維持する。基点は検証記録 `847ad563c172af55a453e7a01af3dfd106ee2eb0`、先行アプリ候補は `2b70f1d55f2b735b1e317c7b853aa8bd8959a550`。専用ブランチ `codex/stripe-restricted-key-support-20261004` で、既存のサーバーキー判定がRAKを拒否する不整合を修正した。main/AWSへは未反映で、faviconや固定候補6b6c570cの承認へ追加しない。

## 変更と境界

- 共通の純粋関数で `sk_test_` / `rk_test_` / `sk_live_` / `rk_live_` のモードを判定する。非文字列、公開キー、organizationキー、不明形式、prefixだけの値、空白を含む値を拒否する。opaqueなsuffixの完全検証や認証・権限・アカウント一致を証明する関数ではない。本番設定では既存の環境値取得処理が周囲の空白を除去してから判定する。
- 本番設定はliveのみ、staging設定はtestのみ許可する。購入停止中でも境界を維持する。従来stagingで通ったlive/不明形式の設定は起動失敗になるため、共有環境へ反映する前に実設定の安全な照合が必要。
- `billing_preflight`、`billing_stripe_remote_check`、`billing_development_check`、`create_stripe_development_prices` に同じ判定を適用する。開発envのコメントも含む漏えいprefix検査へ `rk_live_` を追加。既存公開キーのチェック、productionでのPrice作成禁止、Product応答のtest確認は維持する。
- 既存 `sk_` と設定名 `STRIPE_SECRET_KEY` の互換性を維持する。SDK16.0.0/API2026-09-30.endive、Webhook署名、共有行ロック、購入intent/再試行キー、購入開始/メール停止設定は変更しない。`get_stripe()` 全体へ新しいローカル実行ガードを追加したものではない。
- 実キー発行/ローテーション、Secrets、権限、Price/Webhook、DB移行、共有AWS、課金・メール・継続費用を変更していない。テストの無効な合成キーはメモリーtransportまたは設定importだけに使用し、実StripeへのHTTPは0件。

[公式キー仕様](https://docs.stripe.com/keys)と[公式保護手順](https://docs.stripe.com/keys-best-practices)をStripe CLI 1.53.0の公開docs経由で確認。RAKの最小権限を推奨し、通常アプリ・読み取り検査・テスト商品作成のキーを分ける手順を[運用文書](../runbooks/STRIPE_BILLING_OPERATIONS.md)へ追記した。権限不足の403を合格へ変換せず、検査を省略しない。漏えい検査の推奨は記載したが、コミットフックの導入やキー権限の変更は実施していない。

## TDD・回帰結果

新規テストは21メソッド（制限付きキー16、production設定5）。実装前のREDは制限付きキー12件中failure4/error7、production新規4メソッドの7 subcase failure。修正中のPortal fixture形状誤りと、aws-preテストが継承していたlive合成キー2件はfixture側を訂正し、実装のモード境界は緩めていない。prefixだけの値の拒否と完全値の非表示を分け、誤った非表示期待も訂正した。

| 検証 | 最終結果・範囲 |
|---|---|
| 隔離PostgreSQL 18.3広域回帰 | 35モジュール598件成功、省略0、83.879秒。最後の追加2テスト前の結果 |
| 隔離PostgreSQL最終新規単体 | 16件成功、0.217秒。上の598件と重複するため合算しない |
| SQLite最終関連回帰 | 279件成功、36.850秒。実SDK transport/API版/文書試験を含む |
| production/staging設定import | 最終33件成功、26.157秒。合成環境のsubprocessのみ |
| 新規helper・単体モジュール | 7文/6分岐、147文/18分岐、いずれも100% |
| 変更実行文監査 | 5既存モジュール32変更文、未実行0、変更分岐起点の不足0。設定importの7合成ケースを別計測し、新規helperも全実行 |
| Black/isort/Flake8 | 変更Python9ファイル成功。無関係な全体整形はしない |
| Bandit | CI対象フォルダ0、新規単体/変更本体0。変更9ファイル全体は既存productionテストのLOW26件、終了1で全体合格ではない |

新規合成資格情報のBandit誤検知3件のみ、用途を明記した限定 `nosec B105` を付与した。既存26件は抑制していない。残る26指摘の各行が基点のproductionテストに存在することも照合した。新しい利用者向け拒否文は日本語でキー実値を含まず、重要な日本語文言と非表示をテストで確認。差分レビューでは新たな要修正事項なし。文書変更後に39文書テスト成功、相対リンク欠落0、ステージ対象12ファイルのUTF-8/LF・BOM/文字化け・差分チェック成功を確認した。

PG試験は先行Endiveイメージへ今回ソースをread-only overlayした隔離検証であり、今回候補の通常配布物を検証したものではない。PGはnetworkなし・公開portなし・512MiB tmpfsの合成DBを使用。終了後、ID/イメージ/network/mountを照合して専用DBコンテナを停止・削除し、再作成可能な合成データだけを破棄した。イメージとログは保持し、他のコンテナ・実データを変更していない。

## CI・未確認事項と復旧

先行 `2b70f1d5` の[CI全体success](https://github.com/sheepdog0820/iaia/actions/runs/37204401824)と基点 `847ad563` の[CI全体success](https://github.com/sheepdog0820/iaia/actions/runs/37205459447)を、SHA/branch一致とともに後続確認した。今回候補のCIはpush後に別途確認する。先行CI成功を今回修正の成功へ拡張しない。

今回の通常配布物・OS再監査・実RAK/Sandboxの権限/アカウント/API版照合・共有環境切替は未実施。先行通常配布物のOS39指摘（HIGH3/MEDIUM2/LOW34、Python0）は解消扱いにしない。共有DB0065〜0067、常設worker/メール、管理削除・所有者付け替え方針、外部連携、実AWS性能、RDS/S3整合復旧、事業者運用は引き続き未完了。

復旧は作業ブランチで通常revertを用意し、検証・承認を経て反映する。revertするとRAK拒否とstagingの従来の緩いキー判定が戻るため、その影響を評価する。RAK対応失敗を理由に無承認でキーを変更したり広い権限を付与したりしない。DB移行/削除は不要。Stripe Tax/automatic_tax・税務登録は変更せず、販売対象と登録承認・実検証は別途必要。

## ローカル証拠

保存先 `C:/tmp/iaia-stripe-restricted-key-20261004`。生成物はリポジトリへ追加しない。

| ファイル | SHA-256 |
|---|---|
| red.log | 05687eb4b2433b869c7bb385fe018e4aa4a754a28e44252b6408f752a77f37e1 |
| production-red.log | f8c62fc1112d7647560c0619d0b453cb15f4dd1d68391c966af13bb3474d09f3 |
| pg-regression.log | 860fe95c3718f24c84cfbf1d12fcde4070681d108705e1dec1cd35166d3027f4 |
| pg-unit-final.log | 37091d8bed38d8ced9ad9d14213c4a2fef7b9fce6476c7d98f41282d1af9211b |
| sqlite-final.log | 2efc7a61af7106c571c805b30f1a1a37a3dd9105f96bbf2dd117f4f5016df634 |
| production-final-reviewed.log | 9f61cca701ca7b3cf46430acbf99a8747e0ee642b8ecd2a867ee8af542c206fc |
| coverage-final.json | 24ee8f1c80498e7ad2cdd0ac60f18cfc574d45e86d29dd07ec2e30ef7a55d467 |
| coverage-production.json | 3ea576980f8bceac79378466990d53c260f1e7012853ff873bdf14765af8bb56 |
| changed-coverage-audit.json | 59dddf9ca348516bdf38dc1e4bbbb9e23a3f607d82ecc84fd8fd2ab40ffaf637 |
| bandit-ci.json | d342ca28ca7c3cc7765011bc79a7ad4202303fa7ac4be1b8f20be186162e9c72 |
| bandit-all-changed-final.json | 073cb32dd1943e32ca020d95311adc264cfda2005b3c56058dfa337f0c90b50e |
| bandit-body-final.json | c3f6b7bb82a77d2f106de43846468ac2aae88a09ece12045bdb09a281183c3a8 |
| documentation-final.log | 43b715918f0f78383c0749471106349f54444a643a3bfe1861208bffa37b104d |
