# Google手動再試行の元ジョブ停止と二重受付防止

## 対象と公開判断

親は `508ec5f0ff2e4a3637a0b885655221ace98c8d4f`、作業ブランチは `codex/google-retry-supersession-20261006`。[永続配送の残課題](GOOGLE_DURABLE_DELIVERY_ISSUE_DRAFT_2026-10-06.md)のうち、手動再試行を受け付けた後の元FAILEDジョブ再開と、同じ元ジョブから複数の後続ジョブを作る競合を修正する。**同期対象全体の世代管理が完成したという意味ではない。正式公開No-Goを維持する。**

main/AWS/ECR/ECS/S3/CloudFront、共有DB/実データ、実Google/Stripe/OAuth、Secrets/IAM、実課金/通知、常設容量/継続費用は変更しない。新しい依存・設定・マイグレーションは追加しない。既存favicon反映承認をこの候補へ拡張しない。

## 変更仕様

- 再試行APIとworkerの開始取得が、同じ元AsyncJob行を `select_for_update` でロックする。再試行が先なら元ジョブは再開不可、workerが先なら元ジョブはRUNNINGとなりAPIは400で拒否する。実PostgreSQLで両順序と並列二重POSTを検証する。SQLiteの単独動作は確認するが、SQLiteの行ロック保証は主張しない。
- 後続ジョブ作成と同じtransactionで、元ジョブの非公開payloadに `google_retry_successor` と後続UUIDを保存する。元の失敗状態・理由・結果・開始/終了時刻などは変更しない。新ジョブの `retry_of`、接続先・Sheets内容binding、選択スナップショットは維持する。記録は後続ジョブの削除後も残り、rollback時には元ジョブ・新ジョブ・配送意図と一緒に戻る。payloadやUUIDをAPIへ新たに公開しない。
- markerはキーの存在を停止条件とし、null/空/不正形でも自動的に解除・再構築しない。古いmarkerなしデータでは同所有者・同種別・同元UUIDの `retry_of` を参照する。再試行POSTが既存の後続行を発見した場合は、元行へ記録を補って409で拒否する。全旧データを一括移行したわけではなく、補完前の旧行は後続行の保持に依存する。
- 同じ元ジョブをもう一度再試行すると409と固定日本語案内を返し、新ジョブ/配送を追加しない。後続がFAILEDでも元を復活させず、その最新の失敗ジョブを対象とする再試行は別途受け付けられる。UNCERTAINの自動・手動再試行拒否、所有者/接続先/権限チェックを維持する。
- workerは初期判定、ロック取得後の開始、送信前の実行確認、進捗・成功・失敗・結果不明のUPDATEで元ジョブ停止を確認する。relayも古い配送意図を破棄して暗号文を消去する。元payloadへの追記により元の配送digestが一致しなくなる場合も、安全な破棄として扱う。
- Calendarの失敗保存と同期情報更新の隙間で新しい手動再試行を受け付けた場合、古い同期情報更新とCelery再試行を停止し、新しいPENDING状態を保つ。同期情報の更新は元行ロック中に行い、同期対象削除後の失敗分類は例外によるrollbackを避けるためそのtransaction外で確定する。
- 実HTTPをすでにGoogleが受理した後で元ジョブが削除された場合は、同一の現存同期情報に受理済みID等を残す既存仕様を維持する。この挙動は別ジョブ・同一予定の完全な世代fenceではない。
- CIのPostgreSQLジョブに新しい競合moduleを追加し、静的テストで取りこぼしを検出する。workflowはテストのみで、この作業ブランチpushによるAWSデプロイは追加しない。

## 検証と失敗記録

証拠は `D:/tmp/codex-google-retry-supersession-20261006/`。host Python3.11.1、使い捨てSQLiteメモリーDB、固定PostgreSQL18.3のtmpfs/512MiB/2CPUを使用する。PGはlocalhost限定55445、通常Docker bridgeでありnetwork noneではない。全未mockのHTTPを拒否し、実Google/資格情報は使わない。worker入口の `.run` と独立DB接続を検証するが、この候補の通常image・Redis/Celery別プロセス・AWS・ブラウザ表示検証ではない。

- 最初の新規9テストはSQLiteで17 failure/PG専用2省略、PGで21 failureを確認した。いずれもsubTestのfailure数であり、テストケース件数へ加算しない。
- 最初のGREENにはCalendar GET mockの `side_effect` が `return_value` より優先するfixture誤りがあり、修正後に9件の単独動作を確認した。最初のrelay用REDはbroker停止に遮られて通ってしまったためRED証拠として使わない。broker稼働fixtureへ訂正し、旧配送が通る2 failureを確認してからrelayの拒否を追加した。
- 後続削除・不正marker・旧行記録補完のRED3テストでは14 failure。PowerShellの複数labelを配列にしなかった呼び出しはパラメータ検証で終了し、テスト未実行として区別する。CI追加前の静的テストは1 failure。
- 最初の335件全回帰はSQLite36 failure/2 error/PG専用14省略、PG37 failure/2 error。元payload不変の旧期待値を、追加markerだけを許す全フィールド比較へ更新した。所有権テストの二つの条件は独立した元FAILED行で検証し、旧行への二重受付を正常系として扱わない。
- 同回帰で、同期対象削除の失敗保存が新transactionでrollbackされる実装上の不具合も確認した。失敗分類をtransaction外へ移し、元job削除後の受理済み同期receipt保持も維持した。修正対象5modulesの実PG54件は全成功、scope確認用coverageの未import module警告は広範囲カバレッジ証拠にしない。
- 追加競合は実DB接続PID・ `pg_stat_activity` の行ロック待機を確認してからブロッカーを解除する。二重POSTは202/409各1、再試行先行では元worker拒否、worker先行ではAPI400/新job0。観測には有界timeoutを設け、timeout経路も検証する。
- 新しい409案内はAPIテストで日本語一致を検証する。既存画面の `reportGoogleDispatchError` は401/403/5xx以外のdetailを安全に表示することをソース確認した。画面の新規変更やブラウザ実表示確認を実施したとは扱わない。

## 確定したローカル検証結果

- 最終の30modules/336件は実PG **336成功/省略0・169.000秒**、SQLite **322成功/PG専用14省略・117.693秒**、双方終了0。Google関連28modules271件、文書39件、配布/CI静的26件の合計で、正式リリース全機能・実Googleの合格件数ではない。新module20件（PG専用4件を含む）とCI静的1件を追加した。実配送意図を保存する手動retryのrollbackも、既存元行・同期行の復元、新job/暗号化意図/commit callbackの破棄を両DBで確認した。
- 両DBの実行開始前・終了後に対象8Python filesのSHA-256を照合してソース変更0。製品差分 **35文・12分岐先100%/未実行0/除外0**、新規テストmoduleは実PG **376文・48分岐100%/除外0**。ソースバージョンが異なる初期ログをこの最終coverageへ混ぜていない。
- 対象8Python filesのBlack/isort/Flake8/Bandit成功・Bandit指摘0、Django checkと `makemigrations --check --dry-run` は問題/差分なし。新しい日本語API案内、変更した旧テストの全フィールド比較・所有権条件、差分自己レビューを確認し、依頼範囲の追加指摘なし。最終文書39件成功、staged12 textのUTF-8/LF・BOM/置換文字/文字化け検査と差分チェックに合格。今回CIは通常push後に別途確認する。
- 親508ec5f0の[CI](https://github.com/sheepdog0820/iaia/actions/runs/37468590555)はhead SHA一致・全6項目successを確認した。今回候補のCI成功を代用するものではない。
- 22:47:17 JSTに専用PGのfull ID/image/label/port/mountを照合し、public表0/test DB0/他のactive接続0を確認して停止・tmpfsを撤去した。終了0/OOMなし、自分のcontainer/volume残存0。合成データはテストfixtureから再作成可能、ログ・coverage・SHA-256証跡は保持する。元checkoutの別作業13 itemsは変更・stageしない。

## 残課題・反映・復旧

この修正が扱うのは、同じ元FAILEDジョブからの**明示的な手動再試行の系列**である。新規同期API/セッション変更が別のジョブを作る競合、同一予定/重なるSheets領域の共有世代排他、異なる利用者が同じSheetへ書く競合、開始済みHTTP・UNCERTAINの結果照合と限定回復、7日清掃後の恒久的結果保持、鍵ローテーション、常設relay/beat/worker/監視は未完了。Google再接続後の既存予定方針も回答待ちであり、独断で選択しない。

将来の反映では、旧workerが停止markerを理解しないため停止/排出・新旧混在回避を含む計画と、新しい対象のmain/AWS承認が必要。今回新migrationはないが、親候補までの0056〜0058は共有DBに未適用であり、必要な共有schema承認は別に扱う。現在は未反映なので稼働環境の復旧操作は不要。作業コードは通常revertできるが、受け付け済みmarkerを消去して元jobを復活させず、旧workerへ無条件に戻す手順とはしない。

GitHub open Issueは#1のキャラクターUI課題だけを確認した。Google課題の新規Issueは先行403/CLI未認証から未作成のまま、権限を変更せず下書きを維持する。OS HIGH3、実Stripe/通知、実外部OAuth/Google/AWS、正式性能・長時間負荷・RPO/RTOなどの[正式公開条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)は未達。
