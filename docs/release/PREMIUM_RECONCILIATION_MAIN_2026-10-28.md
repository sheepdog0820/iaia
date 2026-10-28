# 有料権限の再照合・管理画面再同期の競合対策（2026-10-28）

## 対象

正式公開はNo-Goを維持する。[Draft PR #10](https://github.com/sheepdog0820/iaia/pull/10)の運営コード修正 `81fa5a7d9acac855f89f7837ca16d72054a27447` の後続として、`reconcile_premium_access` と管理画面の再同期処理を修正する。元の製品修正は `cea7e76b847727c5244cc03a4d1454d7949cae20`。既存の巨大候補の履歴を一括投入せず、製品2ファイル・PG用CI一覧・回帰テストを分離した。

## 問題と変更

候補の取得時点で購読状態とUserのフラグを読み込んでいたため、購入や解約の確定後に古い状態から権限を書き戻していた。監査保存に失敗しても、権限だけが変更済みになる場合もあった。

- 候補IDだけを列挙し、Checkout/Webhookと共有するPremiumSubscription行をロックしてから状態を再取得する。Userは古いjoin結果を使わず、ロック後に読み込む。
- 削除済み候補を飛ばし、現在値と期待値が一致している場合は書き込み・監査を行わない。
- Userの変更と監査作成を同じtransactionに入れ、監査失敗時はrollbackする。コマンドの変更明細は成功したtransactionを抜けてから出す。
- `--dry-run` は行ロックもレコード変更・監査作成も行わず、差分だけを表示する。料金、手動付与や課金状態から権限を計算するルール自体は変更しない。

本修正を実データへ実行していない。実ユーザーに対する再照合コマンドや管理者操作は、対象・件数・差分・復旧案を揃えて別途承認を求める。

## 検証

現在の固定依存Python 3.11.18 / Django 5.2.17と、このgoal用の隔離PostgreSQL 18.3を使用した。外部公開ポートなしのinternal network、tmpfs DB、合成利用者だけを使用し、Stripeの参照だけをmockにした。

1. 修正前: **10失敗・2成功・3 subtests成功**。候補列挙後の状態変更、監査失敗、削除された候補、購入処理との順序、二重監査を再現した。
2. 修正後の新規ファイル: **12成功・4 subtests成功、省略なし**。PGの別connectionと実行順序を制御し、コマンド・管理画面の両方で購入後の新しい権限を維持、並行再照合の変更・監査が一度だけになることを確認した。
3. 運営コード、既存の課金・同時処理・退会・有料機能を含む7ファイル: **253成功・32 subtests成功、省略なし**。
4. SQLiteでは **9成功・4 subtests成功、3省略**。省略は行ロック用の同時処理3件で、PGでは全て実行した。
5. この単位の変更実行文はadmin 13行・command 19行の **32/32**が通過。PR #10全体ではbilling 24・admin 25・command 19の **68/68**が通過した。commandの37実行文・12分岐は100%。大きなadmin/billing全体や製品全体の100%網羅ではない。
6. 変更Python 3ファイルのBlack/isort/Flake8/Bandit（medium以上）、日本語通知・監査用の既存技術文字列とソースをレビューした。PGのCI jobへ本テストを明示追加した。

ログはGit管理外 `tmp/reconciliation-pg-red.log`、`tmp/reconciliation-pg-green.log`、`tmp/reconciliation-pg-broad-coverage.log`、`tmp/reconciliation-sqlite-regression.log`、`tmp/reconciliation-pg-coverage/coverage.json`、`tmp/reconciliation-changed-coverage.json` に保持する。

## 残る条件

最終headのCIと通常配布物での検証、先行PRを含むmainマージ、実AWS/実Stripeでの有料受け入れは別途必要。管理者の別の付与・失効/編集経路、削除との競合、StripeClient/SDK/API移行、課金メール・配送基盤、正式ゲートB03/B04/B05やOS監査等は継続する。今回の成功をもって課金の正式公開を合格にしない。

DBスキーマ/移行、Secrets・IAM・OAuth、実課金・実データ、外部メール、常設構成・費用への変更はない。mainへのマージは最終headとCIを固定した別の承認対象であり、先行PRの承認を流用しない。取り消しはrevert PRで可能だが、古い状態の上書きと監査の部分保存が再発するため、それだけで公開可とはしない。
