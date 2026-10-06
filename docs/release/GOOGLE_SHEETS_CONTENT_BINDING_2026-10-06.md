# Google Sheetsのqueue出力内容とジョブの照合

## 根拠と利用者への影響

親は `4f97d179a7e4dce5d7c5ec88872890b757aa6d9f`、専用ブランチは `codex/google-sheets-content-binding-20261006`。[配送対象の照合](GOOGLE_DISPATCH_TARGETS_2026-10-06.md)後も、同じjob/owner/Google接続先/spreadsheet/rangeに別のvaluesを渡すと、その内容を送信できた。これはqueue引数の内容混線への不足で、一般利用者が公開APIから任意のCelery引数を送れる実証ではない。

- 初回APIと再試行APIの2生成経路で、確定したvaluesの用途別HMAC（SHA-256、64桁）を既存JSON payloadの`google_values`へ保存する。既存SECRET_KEYを使い、新しい鍵・schema・migrationは作らない。元の出力行/名前/資格情報をジョブへ追加保存しない。
- workerは既存のowner/type・現在認可・正規化対象・元Google接続先の照合後、token取得・Google HTTPより先にvaluesの一致を確認する。セル、ヘッダー、行追加/削除/順序、形状の差替え、digest欠落/不正/不一致を固定日本語失敗で終了する。queue側のvaluesから旧ジョブを自動補修しない。
- 表はlistのlist、セルはstr/int/有限float/bool/nullに限定する。非表・非scalar・NaN/Infinity・UTF-8化できない文字列は不一致として終了し、型例外でRUNNINGに残さない。新しいエラーに出力内容やprovider診断を含めない。
- 表示は「ジョブ作成時のGoogle Sheets出力内容を確認できません。連携設定から新しく出力してください。」。該当ジョブだけを終了し、Calendar同期行・元payload・token・HTTP・自動retryを変更しない。job詳細APIでも日本語全文を保持する。
- [現行再試行仕様](GOOGLE_SHEETS_RETRY_TARGETS_2026-09-10.md)は維持する。初回は作成時の内容を配送し、再試行は元の対象ID内で現在所有するキャラクターの現在値を作り直す。新しい再試行ジョブはその行を新しく確定し、旧digestをコピーせず、後から追加した対象へ範囲を広げない。古い接続/対象不明ジョブの拒否は維持する。
- 17列、RAW（数式風文字列を値として扱う）、日本語、0件、100行分割・部分進捗、通常token更新/失効・再接続チェック・broker失敗表示は維持する。

## TDD・検証と証拠の範囲

- 修正前の新規6メソッドは18 failure/1 error（0.846秒）。内容変更/旧digestを拒否せず配送し、Noneで型例外になること、2生成経路がdigestを保存しないことを確認した。HTTP4種はmock、unmocked Sessionは遮断し、実Googleに送信しない。
- 実装後、新規6＋既存AsyncJob API14は20成功（14.629秒）。非dict payloadのmatcher境界試験を加え、新規は7メソッドとなった。初回/再試行APIで実際にqueueへ渡された引数を本物のworkerへ渡す正例と、queue内容だけを改変した拒否例で契約を確認する。
- 既存の配送/refresh/URL/部分失敗試験では合成行をfixtureとして明示的に確定する共通補助を使う。この補助は試験用にdigestを保存して本物のworkerを呼ぶもので、製品workerがdigestを再構築する機能ではない。新規内容改変/旧ジョブ拒否試験と既存API/自動生成/再試行の契約試験はこの補助を使わない。補助の成功をproducerの正しさの証拠へ読み替えない。
- 最終PostgreSQLは183成功/省略0（60.663秒）、SQLiteは179成功/PG専用4省略（43.873秒）。文書39件、Calendar実Requests＋loopback HTTP8ケース、実PG認可/refreshロック競合も含む。Celery brokerとprovider HTTPはmockであり、実Google/常設worker/AWSの証拠ではない。
- 本体追加26実行文/10分岐、新規試験133文/26分岐・fixture補助8文は100%。google_job_connection全体36文/14分岐も100%だが、全アプリ100%の主張ではない。14 PythonのBlack/isort/Flake8/Bandit合格。既存合成fixture注記のunused警告9件・検出指摘0で、製品ガードや全体の警告基準を緩めていない。新しい日本語は保存値・job詳細APIで完全一致確認し、PG CI選定に新規moduleを追加する。文書追加後も文書39件成功（0.036秒）、17ファイルのUTF-8/LF・差分空白検査に合格した。

最終coverageは `D:/tmp/codex-google-sheets-content-20261006-postgres-coverage.json`（SHA-256 `e30f1c98663ae09f59846845e19f75bf24ce28785ea4e006a887a219082f0b99`）と `D:/tmp/codex-google-sheets-content-20261006-sqlite-coverage.json`（`4840a3b44454930dfed80d8ce06258bd140a51d2e30a4358dd328ddabf0e520c`）。RED/GREEN/最終ログ、外部Requestsを遮断する専用runnerを同じD:/tmp固有prefixで保持する。

専用PG `81c9327f8559` は完全ID/name/label、127.0.0.1:55439、匿名volume `bc3f14eba93d` の一致を確認した。試験DB0・fixture public tables0の後に停止/自動削除し、container/volume/55439待受残数0。metadata/cleanup JSONとログは保持する。実データや元checkoutの無関係13変更は削除していない。

## CI・未確認事項・復旧

先行9f46fa97の[CI 37416999744](https://github.com/sheepdog0820/iaia/actions/runs/37416999744)と直前4f97d179の[CI 37418050140](https://github.com/sheepdog0820/iaia/actions/runs/37418050140)は全6成功。同じ生きているrunの終了を確認し、観測待ちを理由に再起動していない。今回候補の全CI/通常配布物/実Google/AWSは別検証である。open Issuesに関連Issueはなく、先行で作成403を確認済みのため権限・別資格情報を変更せず、この文書/受入表へ記録する。

内容HMACは保存時に確定した表との一致であり、現在のキャラクター所有権の継続や遠隔Google token所有者を証明しない。初回queue待機/チャンク間のキャラクター所有権変更・削除、同一ジョブ並列配送、queue全入力型、チェック後競合/原子的取消、接続先別外部予定ID/再接続時の旧予定方針、実Google/OAuth公開審査等は残る。確認待ちの既存予定方針や共有DB変更を独断で決めない。

main/AWS/ECR/ECS/S3/CloudFront、共有DB/実ユーザーデータ、Secrets/IAM、課金/常設容量/継続費用、外部通知は変更していない。完了済みfavicon8567f49f承認・固定6b6c570c反映案へ候補を追加しない。復旧は通常revertでschema逆移行不要だが、内容混線の照合不足を再導入するためfix-forwardを優先する。受理済みの遠隔書き込みはrevertで復元しない。HIGH3/native閉包、実課金/連携・性能/運用/復旧/事業者対応等の未達条件を保持し、[正式公開](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)はNo-Goである。
