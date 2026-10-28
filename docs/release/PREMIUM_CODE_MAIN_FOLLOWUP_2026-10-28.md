# 運営コードの付与・失効の競合と監査原子性（2026-10-28）

## 対象と位置付け

正式公開はNo-Goを維持する。main e914b325から分離したSDK/ICSの後続、`9a12260a8f6e0238fcd66608bc30043df4d38de5` を基点に、`codex/premium-access-followups-20261028` で運営コードの既知不具合を再検証する。先行の[PR #8](https://github.com/sheepdog0820/iaia/pull/8)・[PR #9](https://github.com/sheepdog0820/iaia/pull/9)は、この作業開始時点ではDraft。これらの未承認変更を先取りしてmainへ入れない。

元の製品修正は `a0f94a403cbbcf9c3f2bdf2699c89b7afe3ac43f` と `3492d3d381d7ccdd0744eee774b479f7f9b831cf`。製品ファイル・回帰テスト・PGのCI対象だけを分離し、以前の巨大候補や過去の実Stripe検証結果を一括で取り込まない。StripeClient/SDK/API版の移行、管理者の他の権限操作や再照合処理は後続の別単位である。

## 問題と修正

- 同じ利用者が異なるコードを同時に使うと、コードごとのロックだけでは両方を消費する。有料権限取得済みの古いUserオブジェクトでも、最新状態を見ずにコード由来の権限へ上書きできた。
- Checkout/Webhookと同じPremiumSubscription行をロックし、利用者の現在のpremium/staff/superuser状態とコードの有効期限を再確認してから付与する。待機中に有料権限が付いた場合やコードが失効した場合は消費しない。
- 失効候補の列挙後に新しい有料権限や有効期限へ変わっても、古い結果を使って失効していた。候補IDを列挙後、共有行ロック中に対象条件を再確認する。
- 管理画面で古いコードを選ぶと、その後のコードで付与した権限まで失効していた。現在の最新redemptionを日時・主キーで一意に照合し、そのコードに対応する権限だけを操作する。
- 失効と監査記録を同一transactionに置き、監査保存失敗時は権限変更もrollbackする。複数の失効workerが同じ対象を選んでも失効と監査は一度だけ。手動の付与がある場合はその権限を維持する。

料金、無料/有料の範囲、コード利用条件や上限自体は変更しない。新しいStripe API呼び出し、実決済・返金・契約・コード使用、外部メール送信は行っていない。署名検証や外部Webhookの正式受け入れ全体を、このローカル状態競合の試験で代替しない。

## 検証

Python 3.11.18 / Django 5.2.17と、使い捨てPostgreSQL 18.3を使用。Dockerのinternal networkだけに接続し、ポートを公開せず、DBデータはtmpfs上に置いた。接続先はこのgoal用ラベルとIDで検査したfixtureのみ、DBは `goal_scratch` / `test_goal_scratch`。実AWS・実ユーザーDB・実Stripeに接続していない。

1. 修正前のPG: **21失敗・7成功**（失敗数にはsubtest失敗を含む）。古い権限、別コード同時使用、失効待機中の購入、二重失効、監査失敗時の部分保存を再現した。
2. 修正後の新規2ファイル: **26成功・2 subtests成功、省略なし**。PostgreSQLの実ロック・別connectionで、同じ利用者の別コード、初回の課金行作成、共有コードの上限、購入handlerとの順序、複数workerを検証した。Stripeの現在値取得だけをmockに置き換え、通信は行っていない。
3. 既存の課金・課金同時処理・退会・有料機能の一連の利用を含む6ファイル: **241成功・28 subtests成功、省略なし**。
4. SQLiteの互換性: **19成功・2 subtests成功、7省略**。省略は行ロック機能を必要とする7件であり、PGでは全て実行して成功した。SQLiteの結果だけで同時処理の正しさを判断しない。
5. PG coverageで変更実行文はbilling 24行・admin 12行の **36/36**を通過。モジュール全体の網羅率は83%で、全製品100%という主張ではない。
6. Python 4ファイルのBlack/isort/Flake8/Bandit（medium以上）と差分レビューを完了。既存の日本語通知と技術用の監査理由を維持し、新たな英語UIは追加していない。CIのPG jobに新規2ファイルを明示追加した。

ログはGit管理外 `tmp/promo-pg-red.log`、`tmp/promo-pg-green.log`、`tmp/promo-pg-broad-coverage.log`、`tmp/promo-sqlite-regression.log`、`tmp/promo-pg-coverage/coverage.json`、`tmp/promo-changed-coverage.json`。DB接続情報はGit管理外のfixture用ファイルだけに保存し、公開資料へ記録しない。

## 未完了・承認・復旧

この修正の最終CI・通常配布物での検証、SDK/ICSの先行PRとこのPRのmainマージ、実AWSでの課金・監査・退会との照合は別途必要。管理者の他の付与/失効・再照合・削除の競合、Stripe SDK/APIの移行と実サービスでの異常系も後続で継続する。B03/B04/B05、性能・運用・OS監査等の正式公開条件を合格にはしない。

DBスキーマ/移行ファイル、Secrets/IAM/OAuth、常設資源・費用、実データへの変更はない。共有DBへの適用や実ユーザーへの失効コマンドは未実施。mainマージには最終headとCIを固定した承認、AWS/共有DB/公開にはそれぞれ別の承認が必要。取り消しはrevert PRで可能だが、古いコードの権限上書き・二重失効の問題が再発するため、それだけで公開可としない。
