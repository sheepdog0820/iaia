# Googleジョブの所有者・種類照合と再試行接続先の引継ぎ

## 根拠と対象

親は `c8d22c11781a79c4b1ab27ffbcbb580bf1627242`、専用ブランチは `codex/google-job-target-guard-20261006`。先行[通常配布物検証](GOOGLE_RUNTIME_A266DD12_2026-10-06.md)に続き、ジョブ境界と再試行APIを確認した。

- Calendar workerは同期行の利用者とジョブ所有者を照合しておらず、Calendar/Sheetsの両workerはジョブ種類も確認していなかった。これはworkerへの引数混線に対する不足であり、一般利用者が公開APIから任意のCelery引数を送れる実証ではない。
- [待機ジョブの接続先固定](GOOGLE_QUEUED_CONNECTION_2026-10-06.md)後も、再試行APIの2生成経路は接続ダイジェストを保存していなかった。そのため同じ接続での再試行を受理しても、workerでは接続先不明として終了する。
- GitHubのopen Issuesを確認したが関連Issueはなく、新規作成は接続済みintegrationの権限不足（403 Resource not accessible by integration）で拒否された。権限・別資格情報を変更せず、この文書と受入表へ結果/不足を保存する。Issue作成成功・クローズ済みとは扱わない。

## 修正と利用者への影響

- workerはjob ID・owner ID・実際のjob type（`google_calendar_sync` / `google_sheets_export`）で検索し、不一致/不存在は内部結果`invalid-job`で終了する。token取得・HTTP・ジョブや同期行の状態変更を行わない。Sheetsの既存owner照合を維持し、Calendarにも同じ境界を加える。
- 再試行APIは連携の有効性/scopeに加え、元ジョブのダイジェストと現在のconnection/credential identityを確認してから、元の`google_connection`を新しいジョブへコピーする。現在の接続先へ勝手に再紐付けしない。元のダイジェストをそのまま使うため、通常のaccess token更新は受理する。
- 古い/不正payload・ダイジェスト欠落/不一致・再接続・token行削除/差替え・Google account/署名鍵変更は日本語400「ジョブ作成時のGoogle接続先を確認できません。連携設定から新しく実行してください。」。追加ジョブ/queue/同期状態変更なしで拒否する。raw token/UIDや応答本文を新しく保存しない。
- 正しい接続の再試行202、`retry_of`、Sheetsの初回対象snapshot（空の出力を含む）、セッション閲覧権限、broker失敗時の固定日本語案内は維持する。古いジョブを自動補修せず、利用者には新しい実行を案内する。
- 既存API fixtureには合成Google資格情報/正しい接続ダイジェストを追加し、認可fixtureのjob typeを実際の生成経路と同じ値へ直す。製品側の資格情報/種類ガードを緩めて試験を通していない。

## TDD・最終検証

- 新規7メソッドの初回は16 failure/15 error。queue mockの真偽値未設定によるJSON再帰エラーを訂正し、不正payloadの500はclientの応答として観測する形にした。修正前の再実行は31 failure/0 error（0.548秒）。所有者/種類の不一致、接続情報の不継承、変更済み接続の再利用を再現した。外部送信はHTTP mockとSession遮断で防いでいる。
- 実装後の新規7件＋既存AsyncJob API14件は21件成功（14.105秒）。再試行APIで実際にqueueへ渡した引数を本物のworker関数へ渡す正例と、access更新後の新しいAuthorizationでの配送正例へ強化した。Celery brokerとprovider HTTPはmockであり、実Google/常設workerの実証ではない。
- 広い170件はPG/SQLiteとも11 failure。既存認可fixtureが`google_calendar`/`google_sheets`という製品で生成しない種類を使っていたため、fixture1行を本来の種類へ訂正した。失敗を成功扱いせず、訂正後に以下を再実行した。
- 最終PostgreSQLは170成功/省略0（74.479秒）、SQLiteは166成功/PG専用4省略（54.660秒）。両実行には文書39件を含む。先行Calendar実loopback HTTP8ケースとPGの実ロック競合も対象に残す。
- 新規7メソッドは所有者/種類/不存在、他人からの再試行、未変更/通常access更新の2サービス正例、不正/変更済み接続の2サービス×10ケースを確認する。拒否ではtoken/HTTP/queue未呼出と、ジョブ/同期行の全フィールド不変を照合する。
- 本体追加差分10実行文/6分岐、新規試験165文/36分岐は100%。job_views全体の行・分岐合算88%、tasks全体75%で、全機能を100%確認したという意味ではない。5 PythonのBlack/isort/Flake8/Bandit合格。合成資格情報に限るB105/B106注記のunused警告はあるが指摘項目0。誤った位置の注記で一度残ったLOW1を正しいfixture行へ移し、再検査終了0。
- 新しい日本語400を完全一致で確認し、workerの内部技術結果以外に英語の新しい表示文言はない。DB schema/新規migrationは作らない。PG CI選定に新規moduleを追加する。

最終coverage証拠は `D:/tmp/codex-google-job-target-guard-20261006-postgres-coverage.json`（SHA-256 `13a551c2d4dcef53bcc1d975602ac39ef20d342d899c4fc81476f00eebc13a33`）と `D:/tmp/codex-google-job-target-guard-20261006-sqlite-coverage.json`（`7afef976e729e60226f8f58ea645a9ad82c8e1bcb1ae42aa9cc25288bd52c204`）。RED/初期GREEN/失敗/最終ログと専用runnerも同じD:/tmpの固有prefixで保持する。

専用PG `8faa505b789d` は完全ID/name/label、127.0.0.1:55437、匿名volume `eb60fdc92580` を確認し、Django試験DB0・fixture public tables0の後に停止/自動削除した。container/volume/55437待受残数0。使い捨ての合成DBを削除し、実データや元checkoutの無関係13変更は保持する。

## CI・未確認事項・復旧

先行a266dd12の[CI run 37414514659](https://github.com/sheepdog0820/iaia/actions/runs/37414514659)は最終5成功/Unit・Integration失敗。ログでSheets対象snapshot fixtureの資格情報欠落による2 subtest失敗、2,345成功/88省略を確認した。今回のfixture追加と再試行/worker修正を先行CIの成功へ読み替えない。新しい候補の全CI・通常配布物・ブラウザー/AWSはpush後の別検証である。

Google再接続後の既存Calendar外部予定IDと接続先の永続的な対応は未実装で、既存予定停止後の明示的再紐付けか、旧予定を保持して新接続先へ別予定を作るかを利用者へ確認中。今回の再試行拒否だけでこの問題を解決したとは扱わず、共有DB変更も実施しない。同一所有者の別同期行とqueue引数の完全結合、チェック後の競合/原子的取消、実Googleのrefresh/ETag・公開OAuth審査も別条件として残る。

main/AWS/ECR/ECS/S3/CloudFront、共有DB/実データ、Secrets/IAM、課金/常設容量/継続費用、外部通知は変更していない。完了済みfavicon8567f49fの承認や固定6b6c570c反映案へこの候補を追加しない。復旧は今回commitの通常revertでschema逆移行不要。ただしジョブ照合不足と再試行不備を再導入するので、fix-forwardを優先する。既に遠隔で受理された予定をrevertで復元しない。

OS HIGH3/native閉包、実課金/連携・運用/性能/復旧/事業者対応等の未達条件を維持し、[正式公開](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)はNo-Goである。
