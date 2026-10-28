# 課金レコード編集の古い保存を防ぐ（2026-10-28）

## 対象と再現

正式公開はNo-Goを維持する。[ユーザー編集・手動付与のPR #13](https://github.com/sheepdog0820/iaia/pull/13)のhead `891b56fa964d0b8b605d4713f518c0d17898c492` を基点に、別ブランチ `codex/subscription-admin-followups-20261028` で既知 `ae4d12ef` の製品差分・回帰だけを分離した。対象は `PremiumSubscriptionAdmin` の編集フォーム・保存処理であり、保留中の後続全体やStripe SDK/APIの更新は含めない。

従来は、フォームを開いた後のWebhook変更を保存時に検出せず、購読状態・支払失敗・検知・Stripe識別子等を古い値で上書きできた。変更なしの保存でも更新日時を変え、直接の保存経路で削除済みレコードを再作成した。新form未実装によるimport失敗とは区別し、既存の実HTTP保存・直接保存の4ケースを先に実行して全て失敗することを確認した（残る18ケースはこの初回では選択していない）。

## 修正と操作の変化

- 画面表示時点の全ての課金列からSHA-256のdigestを作り、対象レコードIDと一緒に署名したhidden項目を渡す。Stripe IDや課金内容そのものを確認項目へ入れず、既存のDjango署名鍵を使う。新しいSecretsや権限は追加しない。
- 保存時は課金行をロックして署名と内容を確認する。`updated_at` を変えない書き込みや、読み取り専用日時の1マイクロ秒の差も検出する。変更・欠落・改ざん・別レコードの確認情報は日本語で再読み込みを求め、保存・監査の成功にしない。
- 正常な画面の編集は、実際に変えた具体的な列だけを保存する。確認用hidden項目だけで変更扱いにせず、変更なしでは更新日時も変えない。キャンセル予定のチェックを明示的に解除する通常操作は保持する。
- Django管理画面の外側のtransactionを使い、検証から保存・関連情報・管理ログまで課金行のロックを保持する。フォーム検証後に別の呼び出しで保存する場合も再確認し、ログ保存の失敗時は変更をrollbackする。
- 管理画面の変更権限、読み取り専用列、新規追加、課金レコード編集時にユーザー権限を暗黙同期しない既存方針は保持する。内部の `form=None` 呼び出しはロックを取る明示的な全列保存として互換性を保ち、画面の署名付き保存と区別する。

古い画面を開いたままWebhook等が進んだ場合、管理者は最新内容を再読み込みして編集し直す必要がある。課金状態の編集権限を広げず、実Stripeの返金・解約・実ユーザーの権限変更を追加するものではない。

## 検証

現在の固定依存、Python 3.11.18 / Django 5.2.17 / PostgreSQL 18.3を使用した。専用labelとinternal network、公開ポートなしのローカル使い捨てDBを確認し、外部通信・実データなしで検証した。

修正後の対象 **22テスト・2 subtests成功、省略なし**。実Django管理画面のGET/POST、署名の欠落・改ざん・別レコード/不正形式、読み取り専用列と時間精度、変更なし/新規追加・明示的編集・権限なしの403、検証後の変更・削除、ログ失敗のrollbackを含む。実PostgreSQLの3件の別接続試験で、Webhook側の更新を待って古い画面を拒否すること、管理ログ保存後のcommitまでロックが保持されること、指定列だけの直接保存が最新の未編集列を保持することを確認した。ブラウザーや実AWSの試験は別途必要である。

対象3ファイルだけのBlack/isort確認は変更なし、Flake8/Bandit成功。新しいhidden項目のラベルと再読み込み・保存失敗の表示は日本語で、実HTTP応答にも完全一致で確認する。PostgreSQLのCI対象へこの回帰ファイルを追加する。

証跡はGit管理外 `tmp/subscription-admin-existing-pg-red.log`、`tmp/subscription-admin-pg-green.log` 等に保持する。関連課金回帰、SQLite、変更行の網羅率、通常配布物・最終CIは後続の記録で照合する。

整形確認後、既存の課金・退会・運営コード・再照合・管理者操作・手動付与・有料機能を含む10ファイルの **320テスト・45 subtestsが実PostgreSQLで成功、省略なし**。追加/変更実行文は **67/67**（admin23・form44）を通過、新formは44実行文・6分岐100%。admin全体は約86%であり、全体100%とはしない。SQLiteも19テスト・2 subtests成功、ロック等が必要な3件のみ意図して省略し、同じ3件はPostgreSQLで成功した。証跡は `tmp/subscription-admin-pg-broad.log`、`tmp/subscription-admin-sqlite.log`、`tmp/subscription-admin-pg-coverage/coverage.json` に保持する。実Stripeや実ユーザーを操作した検証ではなく、通常配布物とCIは別途照合する。

### 通常配布物

製品修正 `9c7ed38d8ff721347448866b6a8ec2023a76a4bb` を通常push後、そのgit archiveから通常Dockerfileで構築した。タグ `tableno:release-candidate-9c7ed38d`、イメージID `sha256:bc88f62921d39d18dd77f8de063cfe93d478a5c6a46aba2c705db7739a387e97`。製品ソース・固定依存・試験・entrypoint等25ファイルと実entrypointのGit blob一致を確認した。

通常配布物内でも同じ10モジュールの **320 Djangoテストが実PostgreSQLで成功、省略なし**。合成設定ファイルだけを読み取り専用で渡し、製品ソースbind mountやpip/pytest追加なし、UID10001・読み取り専用・外部通信なしで実行した。実Stripeの参照は既存試験のmockだけである。証跡は `tmp/subscription-admin-normal-image-build.log`、`tmp/subscription-admin-normal-runtime.log`、`tmp/subscription-admin-normal-source-manifest.json` に保持する。OS再監査・ECR push・実AWS反映は行っていない。

[Draft PR #14](https://github.com/sheepdog0820/iaia/pull/14)はPR #13をbaseとし、製品修正と後続の資料コミットを区別する。最終CIはChecksで照合し、CI待ちの候補をマージ可能とは扱わない。

## 承認と復旧

実ユーザーの課金行や権限、実Stripe、実AWSは変更していない。DBスキーマ/移行、Secrets/IAM/OAuth、料金・保持期間、外部通知、常設資源・費用は変更しない。作業ブランチへの通常push・Draft PRまでを進め、先行PRのマージ後にbase・最終head・差分・CIを照合してmainへの追加マージを別途承認してもらう。

復旧は対象コミットのrevert PRで可能だが、古い課金情報の上書きや削除済み行の復活を再導入する。正式公開No-Goを維持し、有料必須ゲート・実AWSの受け入れ、外部連携・OS監査・性能・運用復旧等をこの局所修正だけで合格にしない。
