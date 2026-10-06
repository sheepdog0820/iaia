# Googleジョブの配送引数と保存対象の照合

## 根拠と修正

親は `9f46fa97e92029e615ed12bd7cc876ed61fb17d8`、専用ブランチは `codex/google-dispatch-targets-20261006`。[先行ジョブ境界](GOOGLE_JOB_TARGET_GUARD_2026-10-06.md)でowner/typeを照合した後も、同じ利用者の別Calendar同期行や別Sheets出力先をworker引数へ渡すと、保存payloadの対象と比較せず配送できた。これはqueue引数混線に対する不足で、一般利用者が公開APIから任意のCelery引数を送れる実証ではない。

- Calendarはdispatchのsync IDを正のsigned bigint範囲のintに限る（bool/文字列/float等を暗黙変換しない）。存在しない/不正な同期対象は内部結果`invalid-job`で、ジョブ/同期行/token/HTTP/retryに手を付けず終了する。既存のowner/type照合を維持する。
- 保存payloadがdictで、保存sync IDがintかつdispatchの同期行と一致することを認可・token取得・状態更新・遠隔照合より先に確認する。不一致/欠落では該当ジョブだけを失敗にし、別の同期行やその遠隔予定を変更しない。
- Sheetsは既存の認可、ID/range正規化、接続ダイジェスト照合を維持し、正規化後のdispatch ID/rangeと保存された対象をtoken取得/HTTPより先に比較する。別のspreadsheet/開始cellや保存対象の欠落を拒否する。APIは既に正規化値を保存しており、同じ対象を表す空白や`$a$1:B5`等は受理できる。
- 対象不一致は固定日本語「ジョブの処理対象が一致しません。連携設定から新しく実行してください。」を該当ジョブへ保存する。個人情報、Google ID、provider応答、資格情報を新しいエラーへ含めない。job APIの既存serializerはこの日本語を保持する。
- 新規schema/永続項目/鍵/資格情報は追加しない。古い対象不明ジョブをdispatch引数から自動補修しない。既存fixtureは製品生成経路と同じsync ID/正規化ID/rangeを持つよう訂正し、製品の照合を緩めない。

## TDD・検証

- 最初のrunner準備2回は、local selectorが存在しない`.env.development`を自動指定して停止した。製品のREDとして数えず、専用runnerで空のENV_FILEを明示して環境ファイルを読まないよう訂正した。実データには接続しない。
- 修正前新規6メソッドは26 failure/7 error（0.677秒）。同じownerの別同期/取消、保存対象の欠落・型不正、sync不存在/不正引数、Sheetsの別対象/範囲への送信を再現した。provider HTTP4種をmockし、unmocked Sessionを拒否するため実Googleへの送信はない。
- 実装後の新規6件＋先行7件は13成功（1.551秒）。新規試験はCalendar全同期行の全フィールド不変、token/4 HTTP/retry未呼出、該当ジョブだけの固定日本語失敗を照合する。既存正規化と同一対象の成功も確認する。
- 広い176件はSQLite5 failure/PG専用4省略、PG5 failure。既存external integrationsの2fixtureが対象を持たず（1正例＋refresh例外の4 subcase）、新しい対象チェックに止められた。fixtureへ実生成形式の対象を加えて再実行した。失敗ログも保存し、初回を成功扱いしない。
- 最終SQLiteは172成功/PG専用4省略（46.939秒）、PostgreSQLは176成功/省略0（59.930秒）。文書39、Calendar実loopback HTTP8ケース、実PG認可/refreshロック競合、API/自動生成6ケース・再試行の実worker正例を同じ選定へ含める。Celery broker/provider HTTPはmockであり、実Google/常設worker/AWSの成功ではない。
- 本体追加12実行文/8分岐、新規77文/16分岐は100%。tasks全体は行・分岐合算76%で、全機能100%の意味ではない。11 PythonのBlack/isort/Flake8/Bandit合格、既存合成fixture注記のunused警告2件・検出指摘0。新しい日本語は完全一致で確認した。PG CI選定へ新規moduleを追加する。

SQLite最終coverageは `D:/tmp/codex-google-dispatch-targets-20261006-sqlite-coverage.json`、SHA-256 `6b244fa4c2f534c4bab87be077db1ac02485aa781b0a71d4840e6ab9503d9511`。PG最終は `D:/tmp/codex-google-dispatch-targets-20261006-postgres-coverage.json`、`cad2c423036c25ffb768c64e6cad904fb8aa92390e3be213c1401de1129db8d5`。RED/初期GREEN/失敗/最終ログと専用runnerは同じD:/tmpの固有prefixで保持する。

専用PG `04e93e398ac7` は完全ID/name/label、127.0.0.1:55438、匿名volume `d12b11716f23` の一致を確認した。試験DB0・fixture public tables0の後に停止/自動削除し、container/volume/55438待受残数0。metadata/cleanup JSONとログを保持し、実データは削除していない。

## CI・承認境界・残作業

先行9f46fa97の[CI run 37416999744](https://github.com/sheepdog0820/iaia/actions/runs/37416999744)は2026-10-06 14:18 JST時点で4成功/Playwright・Unit実行中。生きている同じrunを確認し、観測待ちを理由に再起動しない。この候補の全CI・通常配布物・実Google/AWSは別検証である。open Issuesに関連Issueはなく、先行でIssue新規作成403を確認済みのため権限や別資格情報を変更して再試行せず、この文書/受入表へ記録する。

今回の対象照合だけでqueue引数全体の真正性を証明しない。Sheetsのvalues内容と保存対象/所有権の結合、queue入力全体の型検証、不正job UUID時の安全な終了、同期対象と外部予定ID/Google接続先の永続対応、同一ジョブの並列配送/開始済みHTTPの原子的取消等は別条件として残る。再接続後の既存予定の停止/明示再紐付けか別予定作成かは確認待ちで、独断で旧記録を移行しない。

main/AWS/ECR/ECS/S3/CloudFront、共有DB/実ユーザーデータ、Secrets/IAM、課金/常設容量/継続費用、外部通知は変更しない。使い捨て合成DBのみ試験に使い、元checkoutの無関係13変更は保持する。完了済みfavicon8567f49fの承認や固定6b6c570cの反映案へ候補を追加しない。

復旧は今回commitの通常revertでschema逆移行不要。ただし対象混線への照合不足を再導入するためfix-forwardを優先する。遠隔受理済み予定/Sheet書き込みはrevertで復元しない。OS HIGH3/native閉包、実課金/連携・運用/性能/復旧/事業者対応等の未達条件を維持し、[正式公開](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)はNo-Goである。
