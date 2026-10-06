# Google Calendar同期中の対象削除ガード

## 対象・変更

親は `c0c248560069cca6dba1f0d84dc0b1e71cec4ea7`、作業ブランチは `codex/google-calendar-deleted-target-20261006`。[配送中ジョブ有効性](GOOGLE_JOB_ACTIVE_GUARD_2026-10-06.md)ではjob行を保護したが、処理中に同期行だけが削除されると既存の `save(update_fields=...)` がDatabaseErrorとなった。同じPKに別の作成日時で再作成した合成同期行は、古い処理に上書きされた。実ユーザーでの発生や別所有者への実Google書き込みを観測した主張ではない。

- 元の同期行のPK/user/session/created_atを照合し、開始取得後の認可/token前と各HTTP直前に再確認する。認可/資格情報確認中の削除も最終確認で停止する。
- 認可/token/未設定日時/通信・応答失敗と成功の5保存経路を、同じ識別条件付きUPDATEへ変更した。削除済み行を再作成せず、同じPKの新しい同期を上書きしない。updated_atの更新と通常の予定ID/状態/同期日時を維持する。モデル固有save override・当該senderのpost_save処理はない。
- 元jobが有効なら固定日本語でFAILED/finished_atを保存して停止し、APIでも案内する。先に失敗を保存済みなら元の失敗理由を保持して停止し、不要retryをしない。jobが既に無効なら既存ガードに従い、別の完了/削除行を上書きしない。
- 最後の遠隔変更が受理済みでも巻き戻さず、同期行が消えていれば確認案内で停止する。既存の「jobだけが無効化された場合は受理済み結果を残存syncへ記録する」動作を維持する。Googleイベントを自動削除したり、取消とHTTPを原子的にしたりする変更ではない。

## TDD・検証

| 段階 | 結果 |
| --- | --- |
| 修正前SQLite・新規7試験 | 2 failure（同PK置換）/21 error（削除後保存）、0.627秒、終了1 |
| 初期PG・新規＋配送/有効性回帰 | 29成功、6.672秒、終了0 |
| 追加PG削除競合＋開始競合 | 15成功、3.118秒、終了0 |
| 最終PG・Google22 modules＋文書 | 220成功・省略0、119.182秒、終了0 |
| 最終SQLite・同じ集合 | 214成功・PG専用6省略、83.010秒、終了0 |

新規は7通常試験＋1PG専用試験。取得後削除3経路、token/最終資格情報確認中6ケース、GET/409間4経路、最終受理後3経路、認可/token/通信/応答/未設定日時の5失敗、同PK置換の開始/受理後2ケースと通常3経路を検証する。PG専用は別接続のworkerをtoken/HTTPで有限待機させ、主接続の同期削除commit後に再開する2 subtest。HTTPはfixtureであり、実Googleの並列削除試験とは区別する。

親[通常配布物記録](GOOGLE_RUNTIME_337C7CC9_2026-10-06.md)の21 Google modulesへ新規moduleを加え、文書39件を別計数で合算した。最終Google部分181件と文書39件で220種類。既存のCalendar loopback8ケースとPG専用試験を含む。host Python 3.11.1、専用PG18.3/512 MiB/2 CPU・127.0.0.1:55444、合成DB google_deleted_fixtureのみを使い、SQLiteはメモリーDB。空ENV_FILE/隔離MEDIA_ROOT、AWS Secrets/Sentryなし、unmocked HTTP拒否（既存wire試験のstrict loopbackだけ元transport）で実ユーザー/外部データへ接続しない。通常image/実broker/常設worker/ブラウザー/実AWSの検証ではない。

変更本体21文・4分岐は両DB100%。新規試験204文・44分岐はPG100%、SQLiteの未通過27文/4分岐は省略したPG専用部分。2 PythonのBlack/isort/flake8・workflow YAML/PG対象追加確認・差分検査は合格。初回Banditは辞書キーtokenと合成エラー文をcredentialとしてLOW1誤検知した。限定nosec注釈で警告が出たため撤去し、fixtureの区分名をrefreshへ明確化した。検証条件/製品コードを変えず、最終Banditは指摘/エラー/警告0、最終広域回帰を再実行した。初期ログは保持し、最終runnerはPython出力UTF-8を明示する。表示エラーの日本語とAPI応答を確認し、画面/JS構造変更はない。

SQLでtest DB0/fixture public tables0を確認し、専用container b8dd939aa859の完全ID/name/label/imageとvolumeのname/label/mountを照合した。containerと専用volume（合成PGデータ）を削除、対象container/volume/55444 listenerは0。実データ・ソース・ログ/coverageは保持する。文書追加後の文書回帰は39成功・0.036秒・終了0。UTF-8/LF・日本語説明/表示エラー・最終staged差分を自己レビューし、追加の要修正事項なし。

## CI・残条件・承認境界

先行337c7cc9の[CI37427440562](https://github.com/sheepdog0820/iaia/actions/runs/37427440562)と親c0c24856の[CI37428864881](https://github.com/sheepdog0820/iaia/actions/runs/37428864881)は全6成功を確認した。今回の新候補のCI/通常配布物/実Google成功に拡張しない。GitHubの未完Issue一覧は1件（別の画面課題）で、今回のIssue作成は403 Resource not accessible by integrationで未完了。権限を変更せず本書/受入表へ結果を保存する。

開始前に同期行がなくなる場合のjob終了、enqueue時点の同期行世代固定、同じ現行syncの別job競合/編集の版管理、publisherの配送後エラー/結果不明、試行lease・failed後duplicate・原子的取消/絶対期限、既存外部予定方針などは残る。実課金/連携/worker/SMTP、AWS性能/復旧・法務/運用等も未達。[正式公開](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)No-Goを維持する。今回OS再監査はせず、直近通常imageのHIGH3未解消を保持する。

main/AWS/ECR/ECS/S3/CloudFront、共有DB/schema/migration/実ユーザーデータ、Secrets/IAM、課金/常設容量/継続費用・外部通知は変更していない。完了済みアイコン承認や固定反映案へ追加せず、元checkoutの無関係13変更を保持する。復旧は未反映ブランチの当該修正を通常revertし、親c0c24856へ戻す。共有環境の復旧操作は不要。

## 保存証拠

`D:/tmp/codex-google-calendar-deleted-target-20261006/` にRED/初期/最終ログ、runner、coverage、Bandit各段階、SQL/cleanup/container/volume metadataとevidence-sha256.jsonを保存し、Gitへ混入しない。

| ファイル | SHA-256 |
| --- | --- |
| regression-pg-final.log | cfe0a8aa743b64295cd74849b48817faa843cde8d5ff79003dc905357efcc366 |
| regression-sqlite-final.log | fc4de3a2e2fc99561fa222a0ea987c36f490f2d600ba8ecb72f6eb71ae9f5a9e |
| coverage-pg-final.json | 04e6871051d7c5a0099e5bc11698736530b504de530948352cbe62ccf27c2065 |
| coverage-sqlite-final.json | 8b4a1aa63a87c269d565426d4149008709c1346f9e0fe431ebf12c954309f16d |
| coverage-final-summary.json | be636429734ab873ab05c3c86c83e3a1629d069a80959ed02d3ec691b5edca1f |
| cleanup.json | a55f6538af8b31e618be8628e6c4f1847875095170d76c98911173bc68e0fe5a |
