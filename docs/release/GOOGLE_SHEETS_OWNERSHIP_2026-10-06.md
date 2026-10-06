# Sheets配送時のキャラクター所有権確認

## 根拠・変更・利用者への影響

親は `cc1e497cc51de09251fd58ffc79369ed78050df2`、専用ブランチは `codex/google-sheets-ownership-20261006`。[内容照合](GOOGLE_SHEETS_CONTENT_BINDING_2026-10-06.md)後も、ジョブ作成後に対象が削除・別所有者へ変更されると、初回のキャラクター情報をそのまま配送していた。公開APIから所有権を任意に移動できる実証ではなく、配送までに保存状態が変わる場合の不足である。

- 保存payloadの`selection_snapshot`が厳密なtrue、対象IDが正の符号付き64bit範囲内の整数list、重複なしであることを確認する。bool/文字列/float/巨大値・対象不明を全件へ読み替えない。
- 内容HMAC照合後に、表の先頭が既存17列のヘッダー、各行が17列、行IDが整数かつ保存対象IDと順序を含め一致することを確認する。不一致は「ジョブ作成時の出力対象を確認できません。連携設定から新しく出力してください。」で終了し、token/HTTPを呼ばない。旧ジョブを自動補修しない。
- token取得前と各100行chunkのHTTP送信直前に、確定対象すべてが現在も同じユーザーに所有されていることをDBで再確認する。削除/所有権変更を検知したら「出力対象のキャラクターが削除されたか、所有者が変更されました。連携設定から新しく出力してください。」で該当ジョブだけを終了し、自動retryしない。
- 初回送信後の検知では「途中まで出力されている可能性があります。出力先を確認してください。」を追加する。元payload/別Calendar同期行を変更せず、既に送信済みの行を自動削除・復元しない。
- 初回の確定内容は保つ。所有権が継続する対象の名前等が変わっても、初回配送を現在値に置き換えず、後から追加したキャラクターを含めない。[再試行仕様](GOOGLE_SHEETS_RETRY_TARGETS_2026-09-10.md)どおり、明示再試行では元対象内で現在も所有するものの現在値を新しいジョブとして確定する。0件はヘッダーだけとして保持する。

## TDD・検証・証拠

- 修正前の新規7メソッドは34 failure/0 error（4.948秒）。待機中・token取得中・chunk間の削除/所有権変更と不正対象が配送を止めないことを再現した。provider HTTP4種をmock、unmocked Sessionを遮断して実Googleへ送信しない。
- 初期GREENは新規7＋既存内容照合7の14成功（4.103秒）。境界parserとtransport fixture契約を追加し、新規は9メソッドとなった。所有権の拒否/正例/明示再試行は実APIがqueueへ渡した引数を本物のworkerへ渡し、対象確認をmockしない。
- 初回広域は190件（SQLite187成功/PG専用3省略、78.112秒・PG190成功/省略0、95.936秒）。先行検証のGoogle認可PG競合1件が選定から漏れていたため追加し、fixture契約追加後に全選定を再実行した。この初回結果を最終の4競合検証へ読み替えない。
- 最終PostgreSQL192成功/省略0（97.291秒）、SQLite188成功/PG専用4省略（80.757秒）。文書39、Calendar実Requests＋loopback8ケース、実PG認可/refresh競合を含む。実Google・broker・常設worker・通常配布物・AWSの検証ではない。
- 本体差分35実行文/20分岐（google_sheets 17/12、tasks 18/8）、新規試験180文/36分岐、fixture補助16文は100%。両DBのcoverageと実際の追加行の交差を確認した。全アプリ100%の主張ではない。6 PythonのBlack/isort/Flake8/Bandit合格、既存合成資格情報注記のunused警告3・検出指摘0。新しい日本語は保存値とjob詳細APIで全文一致確認し、PG CIへ新規moduleを追加した。
- 既存transport試験の補助は、元の合成入力と同じ総行数（最低ヘッダー1行）の所有キャラクター/7版詳細を隔離DBで作り、既存行生成処理で17列の表と対象を確定する。過去の任意行形式を製品へ許可する例外ではない。補助自体を0件/空合成名/RAW数式風日本語で検証するが、これを実API producerの証拠へ読み替えない。所有権の改変/拒否試験は補助を使わない。

coverageは `D:/tmp/codex-google-sheets-ownership-20261006-postgres-coverage.json`（SHA-256 `f196d9a44755de04590534b2f393ad7662892b60fb3749e3cc47dbaba5bd4d13`）と `D:/tmp/codex-google-sheets-ownership-20261006-sqlite-coverage.json`（`59dd7e6866bb1a938de7968c58147e07cee0286ae90eb34cec4ccb056e5b487d`）。RED/GREEN/初回/最終ログ、外部Requests遮断runner、PG metadata/cleanup JSONを同じD:/tmp固有prefixで保持する。

専用PG `2b3927ac1853` の完全ID/name/label・127.0.0.1:55440・匿名volume `03110decb302` を照合した。試験DB0・fixture public tables0の後に停止/自動削除し、container/volume/55440待受残数0。実データ・元checkoutの無関係13変更・検証記録は削除していない。

## CI・未確認事項・復旧

先行cc1e497cの[CI 37419358489](https://github.com/sheepdog0820/iaia/actions/runs/37419358489)は確認時点で4成功/Unit・Playwright実行中。同じ生きているrunを確認し、待ちを理由に再起動していない。今回候補の全CI・配布物は別検証である。関連open Issueはなく、先行でIssue作成403を確認済みのため権限・資格情報を変更せず、この記録/受入表へ残す。

所有権確認とHTTPは原子的ではない。チェック後や送信中の変更、同一ジョブ並列配送・完了/失効済みジョブの再配送、queue全入力型、接続先別Calendar外部ID/既存予定方針、実Google/OAuth審査、配送の最終的整合性等は未解決・未検証である。HTTP中のDBロック保持や共有データ一括修復をこの変更で導入しない。最終write後の削除をさかのぼって取り消す保証もない。

main/AWS/ECR/ECS/S3/CloudFront、共有DB/実ユーザーデータ、schema/migration、Secrets/IAM、課金/常設容量/継続費用、外部通知は変更していない。完了済みfavicon承認・固定6b6c570c反映案の候補を拡張しない。復旧は通常revertでschema逆移行不要だが、検知済みの所有権失効対象を送る不足を再導入するためfix-forwardを優先する。受理済みの遠隔書き込みはrevertで復元しない。HIGH3/native閉包、実課金/外部連携・性能/運用/復旧/事業者対応等の未達条件を保持し、[正式公開](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)はNo-Goを維持する。
