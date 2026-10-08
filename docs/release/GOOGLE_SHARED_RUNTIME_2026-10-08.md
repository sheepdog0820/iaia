# Google共有実行権: 通常配布物の強制停止・再配送検証

## 対象と公開判断

2026-10-08。[共有実行権・独立送信記録](GOOGLE_SHARED_EXECUTION_2026-10-08.md)の製品コミットは `9a16fa89f9653e06ffbe9a995d0e1f560097e7c6`。作業ブランチは `codex/google-shared-runtime-20261008`。

9a16fa89の[CI37779822628](https://github.com/sheepdog0820/iaia/actions/runs/37779822628)はhead SHA一致、6ジョブ全てcompleted/successを読み取り確認した。後述のテスト修正・この記録のcommitのCIとは区別する。**正式公開はNo-Go**。共有DB、AWS、実Googleへの反映・検証は行っていない。

今回の製品コード変更はない。回帰試験で見つかった、作成時刻だけで別ジョブを選んでしまうテストの不安定性を修正した。実際に受け付けたジョブIDを使い、自動同期では新規行を一意に特定する。commit前のqueued/task ID未保存/broker未呼び出し、rollback、独立接続の不可視性などのassertionは維持する。

## 固定配布物と隔離条件

| 用途 | 固定した対象 | 確認範囲 |
| --- | --- | --- |
| 強制停止20ケース・永続relay・設定70試験 | 通常Dockerfileの9a16fa89 image `sha256:1e036af6f9b24d89b0fa4d54c3890c2c31ad517952f9b0a67e1bc9789b9be5c6` | 選定733 source/assetsのarchiveとの不一致0、111 Python packages、先行配布物の依存10層一致、entrypoint一致、pyc 0 |
| テスト修正後の通常回帰378試験 | 固定staged Git tree `a40241eda06aa89897f9cb9c03b86f35e23e53ee`から構築した通常image `sha256:9be20cc3a4ac1bee2974f2e150a2ecc26689ebfabcad22bc1a70608c2bb1ab3b` | 選定733 source/assetsの不一致0。9aとの変更は `schedules/test_google_dispatch_commit.py` だけ。製品ソース・111 packages・依存10層・entrypointは同一 |

後者はcommit SHAを偽装せず、image revisionに `tree:` を付けて未commit時の固定treeを記録した。最終commitと照合する対象は実測したsource/assetsであり、文書の追加はDockerの既存除外規則に従う。ECRへのpushは行わない。

PG18.3とRedisは専用container/tmpfs、PGのnetwork noneを共有するlocalhostだけを使う。ホストport・永続volume・外部経路はない。アプリは通常entrypoint/非root/read-only、`/app`へのsource overlayなし。developer env/Secrets/S3/メール・起動時migration/collectstaticは無効で、資格情報とデータは全て合成。配布物内のAPIを専用利用者として呼び、実Redis/Celery/Requestsで配送する。ログと検証scriptだけをread-only `/evidence`へmountする。

停止点のdiagnostic wrapperは、送信前intent・HTTP呼び出し前・receipt保存前に待機を挿入する。Google URLはホワイトリストでloopback模擬providerへ変更する。このinstrumentationを無改変の実Google通信と扱わない。追加カバレッジのsource検査は別の `/workspace`/coverage tool mountを使い、通常配布物の検証とは区別した。

## 送信境界のSIGKILL

Calendar新規作成とSheets PUTを、solo/preforkそれぞれで次の5点で停止した。計20ケース。実行期限は停止時点で未来、時刻・期限の注入なし。Dockerは所有完全ID/name/label/image/network/mount/live stateを照合してKILLし、exit 137・OOM falseを確認した。

| 停止点 | 確定したrequest記録 | 停止時HTTP / 模擬適用 | 確認した意味 |
| --- | --- | --- | --- |
| intent保存前 | 0 | 0 / 0 | 開始済み実行権だけでも、別worker/新jobが迂回できない |
| intent保存後・HTTP前 | INTENT 1 | 0 / 0 | HTTP未到達を外部から断定して自動解除しない |
| provider到達後・適用前 | INTENT 1 | 1 / 0 | worker停止後に遅い適用を許した模擬providerでも後続送信なし |
| provider適用後・応答前 | INTENT 1 | 1 / 1 | 書き込みは済んでもreceipt未保存の禁止を維持 |
| HTTP 200応答後・DB receipt前 | INTENT 1 | 1 / 1 | 応答だけでDBの送信境界を閉じたことにしない |

各ケースで独立した回復workerへ元jobを再配送し、`inactive-job`、製品状態保持、追加HTTP 0を確認した。新しいAPI受付は同じCalendar対象、または同じspreadsheetの別rangeを使い、`target-waiting`、QUEUED・未開始・tokenなし・配送cipher保持だった。遅い旧適用/応答を解放した後も、後続の再配送で追加HTTP 0。

次に合成の元jobだけを削除した。元admission/outboxは消えるが独立journal/request/targetは残り、後続再配送は引き続き待機・追加HTTP 0。これは実7日待機、退会、owner/session/sync全削除や再連携の完了証拠ではない。

SIGKILLでfinallyが動かないため、最終journalは **ACTIVE 20件**。UNKNOWNへ自動分類されたとは報告しない。未解決禁止として機能し、requestはINTENT 16件、Calendarの2対象とSheetsの1対象で合計30 target。providerはHTTP 12・模擬適用12・エラー0。重複・後続配送からの追加HTTPは全て0だった。模擬適用は実Googleでの適用証拠でもexactly-once保証でもない。

全元job削除後、実際の未開始配送期限を待ち、別Celery processで `dispatch_google_jobs` を実行した。attempted 20 / published 20、全て `target-waiting`、outbox attempt 2・cipher保持・新しいholder 0・追加HTTP 0。時計を進めたりnext_attempt_atを書き換えたりしていない。常設beat/自動運用や、失われたbroker ACKの自然復元まで証明したものではない。

`final_audit.py` は20通りの組合せ/元と後続UUID/137/独立journal/全対象sequence/receipt未保存/元行不存在/公開job APIの非露出/後続Calendar PENDINGを、別processの実DB読取で再確認した。部分的なケース成功だけから全受入条件を閉じていない。

## 回帰・修正・失敗記録

失敗ログを削除・成功へ上書きしない。

- 最初のprepareはAPI応答の `queued=false` を誤って失敗扱いした。実jobはcommit callback後にworkerへ到着し、同じ生存worker/同じjobを再確認して継続した。Celeryが付けるログprefixの観測timeoutも、同じhandleを再確認しただけでworkerを再起動していない。Calendar allocationを1件と仮定した診断assertionは、設計どおり論理/物理2対象の検査へ修正した。
- 初回の431試験は、Docker除外対象のAGENTS/Dockerfile/CI/文書を読む検査を混ぜて21エラーになった。除外規則は変更せず、リポジトリ文書検査を別に実行した。
- 通常配布物の377試験は、outer commitのテストで3失敗。`AsyncJob.objects.first()` が同時刻の元FAILED/既に配送済み別jobを選んでいた。時刻が同じ場合の新RED試験は5失敗で再現し、受付ID/新規行による参照へ修正した。製品の状態判定、delivery/認可/拒否assertionは緩めていない。
- 修正後の最初の通常回帰は、追加source PG測定と同じテストDB名を使ったため、終了時のDB削除で衝突した。この測定は合格記録にしない。用途別の専用test DBへ分離して再実行した。tmpfsのcoverageをcontainer停止後に取り出せない診断の失敗も保持し、生存中exportで再測定した。coverage configの未認識option警告も除去して記録を区別する。

最終通常配布物のGoogle/async job/PG credential等 **378件成功・省略0、166.452秒、container終了0**。設定/ログ秘匿70件は9a通常imageで90.104秒・省略0・終了0。module集合は非重複だが異なるimageでの測定なので、単一imageの448件検証と省略しない。

修正したsourceのPG13件は独立test DBで11.034秒・省略0、SQLiteと文書/CIの82件は81成功・PG専用1省略/4.844秒。両backendのcoverageを照合し、変更18実行文・2分岐先を100%/変更行除外0で確認。新helper6文/2分岐先、新しい同時刻試験5文も100%。配布物と検査sourceのSHA-256一致を確認した。

Black/isort/Flake8/Banditは変更したPython1ファイルで終了0。自己レビューでは新機能・認可・model/schema・依存・利用者向け文言を変更していないこと、既存assertionとPG独立接続検査の維持を確認した。新しい表示文言・画面変更はなく、ブラウザー合格をこの単位で追加主張しない。

## 新規OSスキャン

固定9a imageとテスト修正imageの双方を、Docker Scout **1.26.0・filterなし**で新規scanした。両方とも292 packages、脆弱package 15、37指摘（HIGH 1 / MEDIUM 1 / LOW 35）、終了2で**未合格**。Python package指摘0。HIGHはzlibのCVE-2026-85091でfixed versionはnot fixed。

先行39指摘からCVE-2026-102010/CVE-2026-95619が今回結果に出なくなったが、依存10層・package版は同一で、今回コード修正でOS脆弱性を解消したとは扱わない。advisory側の変化の理由・残リスク判定は未確定。古い同梱Scout1.5の試行も終了2だったが、最新版の記録で代替せず別に保持する。

## 証拠・片付け

証拠は `D:/tmp/codex-google-shared-runtime-20261008` に保持。fixed archive/build/733-file manifests、20 cases、全container inspection/log、独立最終audit、relay、失敗/最終回帰、coverage、Scout SARIF、cleanup、SHA-256 manifestを含む。実Secretsや実ユーザーデータは含めない。

片付けは全manifestの完全IDと実label inventoryを照合して行う。テストDB0・他のfixture connection0・journal20/request16を確認し、合成RedisのDB11〜14を明示的に消去して残存0とする。これは製品のbroker自動cleanupの成功証拠ではない。所有container/tmpfsだけを停止/削除し、失敗ログ・image・証拠と元checkoutのハンドアウト関連13項目を残す。送信境界の終了137の20ケースと、providerの片付け停止137を区別する。providerのPID1は通常TERMで終了せずdocker stopの終了137となったため、初回の143という診断期待は不成立。実状態を確認して同じ停止済みIDの片付けを継続し、providerを再起動しない。port bindingの空objectを誤判定した初回診断も削除前に修正した。PG/Redisの停止0、既知の試験失敗も別分類し、最終実施結果はcleanup.jsonへ保存する。

22:48:39 JSTに所有189 container/tmpfsを撤去完了。残container/volume0、合成Redis残存0、test DB/他fixture connection0、PG/Redis停止0・OOM false。実行中測定を削除していない。合成データはtmpfsとともに消え、必要なら保存したfixture/scriptから再作成する。配布image・archive・証拠・元checkoutの別作業は保持した。文書更新後のリポジトリ文書/CI69試験も成功した。

## 残る受入条件・承認境界

[設計T01〜T15](GOOGLE_TARGET_FENCE_DESIGN_2026-10-06.md)全体は未完了。今回T07の通常配布物/solo/prefork/送信境界SIGKILL/独立relay、T08の元job削除後禁止の限定部分を確認したが、次は残る。

- 実DB保存障害/DB再起動、実行・保存期限経過、全削除/再連携/署名鍵変更、部分Sheets・別owner/接続の実process競合、全経路/両順序のlock実測。
- 旧worker/producer/relayの停止・drain、未開始legacy移行、RUNNING/UNCERTAINの保留、新旧版互換。journalをDROPして旧workerを再開するrollbackは禁止。
- 保持・退会・再連携方針、共有Sheetの認可/資源上限/濫用防止、ログ/SQL/バックアップprivacy。
- 対象待ち/確認必要の日本語UI・3ブラウザー、照合と限定回復・独立競合・外部の人間編集。ACTIVE禁止を時間で自動解除して代用しない。
- 実Google/OAuth公開審査、常設基盤、Stripe/AWS購入・実メール、OS残リスク、実AWS性能、RDS+S3全体復旧、法務/税務/運用等の[正式公開条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)。

mainは読み取り8567f49f。AWSは今回再照合/変更していない。main/ECR/ECS/S3/CloudFront/共有DB/実データ/Secrets/IAM/実課金/外部通知/容量・継続費用は変更しない。favicon反映承認を拡張しない。GitHub open Issueは別UIの#1のみ、本課題の新Issueは先行403/CLI未認証に従い[下書き](GOOGLE_DURABLE_DELIVERY_ISSUE_DRAFT_2026-10-06.md)へ追記する。

未配備なので実環境の切戻しは不要。本単位はテスト・記録の通常revertで取り消せる。共有反映する場合は対象SHA・稼働版・drain/保持/送信停止・証拠保持・具体的復旧案を揃え、必要承認を別途確認する。
