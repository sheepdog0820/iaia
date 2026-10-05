# 背景透過workerの通常配布物検証 c7390ee3（2026-10-05）

## 結論・対象

固定アプリ `c7390ee3c847e7621b64d62a9e500202ee75bb82` を通常Dockerfileから構築し、Linux/PostgreSQLで関連31テスト、実workerコマンド3ケース、実HTTP18確認が成功した。実worker試験ではモデルをmockに置き換えず、透過PNG生成・所有者だけの結果取得・元画像削除・完了ジョブの再実行・破損storageの失敗・保存期限後の結果削除を確認した。

ジョブ投入は隔離fixtureからの作成であり、実ECS起動を検証したものではない。背景透過の単発Fargateコマンド構成を維持し、Celeryへの置換は行っていない。S3も使わず、Web/workerの画像領域だけを共有するローカルfilesystemで検証した。正式公開、実AWS、モデルの一般的な画像品質、全体負荷、常設worker/beatの合格には拡張しない。

全OSの新しい監査は39指摘（HIGH3/MEDIUM1/LOW35、Python0）・終了2でゲート未合格。後続照合で候補CI全6項目successを確認したが、公開条件全体の合格とは区別する。main/AWS/ECR/共有DB/Secrets/権限/料金/メール/容量は変更していない。favicon承認と固定6b6c570cの承認案の対象は変更せず、正式公開No-Goを維持する。

## 配布物の同一性・隔離

- Git archive対象は上記の固定commit。tag `tableno:background-worker-c7390ee3`、image ID `sha256:7c27f0969c47edf1bd2f09d64aa1b67042721645b77f3b44578224d5a5d7adb8`、revision labelも固定commit一致。
- archiveと実配布物の675選定ソースファイルを照合し欠落/不一致0、Pythonキャッシュ0、`/entrypoint.sh`も追跡ソース一致。ソースoverlay/SDK差替えなし。先行6828f209イメージと先頭10層が同じで、native/OS更新はしていない。
- 実PostgreSQL 18.3を新規tmpfs・`--network none`で起動。Web/workerは同じネットワークnamespaceを共有し、外部到達/公開portなし。実DBやSecretsを取得せず、synthetic用DB名・ユーザー・無効な課金値のみ使用。
- 通常Webは `APP_ENV=aws-pre` のproduction設定、非root実行。DB/cache readiness成功（cacheはLocMemでRedisではない）、通常entrypointで隔離DB migrate・静的収集232 copied/624 post-processed・Daphne起動、`migrate --check` と `check --deploy` 成功。
- workerは通常entrypointから小さな監査wrapperを実行し、その子プロセスで変更なしの `python manage.py process_background_removal_job <uuid>` を起動。wrapperは終了コードとfresh homeのtelemetryファイルを確認するだけで、service/model/DB処理をmockしない。
- workerは1 CPU/2 GiB、home/tmpをfresh tmpfs、既存U2NETモデル1ファイルをreadonly mount。モデルSHA256 `8d10d2f3bb75ae3b6d527c77944fc5e7dcd94b29809d47a739a7a728a912b491` を終了後も確認。ダウンロード/変更なし。CI抑制環境変数を指定していない。

## テスト・実コマンド・実HTTP

配布物内の `tests.unit.test_background_removal_model` と `accounts.test_character_background_removal` は隔離PostgreSQLテストDBで31件成功/省略0、12.775秒。既存API/ECS/S3異常のunit試験はmockの範囲であり、以下の実worker/HTTPとは区別する。全アプリテストの代替にはしない。

合成ユーザー2人と合成128×128 PNG/破損storageデータのみを作成。結果はRGBA、alpha 0〜255、SHA256 `97118d98655762cab2a06137caeeba448a79f62b8cb7eacbd42f7b066c356cde` で、先行直接推論の結果とも一致した。日本語の結果ダウンロード名も確認した。

| 実コマンド | 終了 | 永続状態・storage | fresh homeのtelemetryファイル |
|---|---|---|---|
| pendingジョブ | 0 | completed、結果保存、元画像/参照削除 | 0 |
| 同じcompletedジョブを再実行 | 0 | 結果名/hash/updated_at不変 | 0 |
| 保存画像を破損させた別fixture | 1（期待する失敗） | failed、元画像削除、結果なし | 0 |

正常workerの経過58.596秒はcontainer起動等を含む1回の隔離cold測定であり、AWS性能やp95、登録100人/同時10人の合格証拠ではない。

| 実HTTP確認群（各3件） | 確認結果 |
|---|---|
| pending | 所有者202/pending、他ユーザー404、未認証401 |
| completed | 所有者200/透過PNG、他ユーザー404、未認証401 |
| 再実行後 | 同じ結果200、他ユーザー404、未認証401 |
| guard | readiness200、無料ユーザーの処理開始403/ジョブ数不変、不明ジョブ404 |
| failed | 所有者503/汎用エラー、他ユーザー404、未認証401 |
| expired result | 所有者503/結果利用不可、他ユーザー404、未認証401 |

ジョブGETでは `no-store` と `Vary: Cookie, Authorization` をassert。課金や実決済は実行していない。失敗ケースは通常のアップロードvalidator通過を意味せず、保存後の破損に対するworker側の異常処理を検証したもの。

保存期限の試験では、完了fixtureのtimestampだけ25時間前へ移動し、既定24時間のresult保持/7日のjob保持をassertした。実 `cleanup_background_removal_jobs` が結果画像1件を削除し、completed/failedのジョブ2件を保持、削除失敗0。保存期間や利用者への約束を変更せず、beatの定期稼働・S3削除成功も証明していない。

## CI・OS監査

[候補CI run 37310973465](https://github.com/sheepdog0820/iaia/actions/runs/37310973465)のSHA/branchと完了後の全6ジョブsuccessを照合した。Lint/Security・Infrastructure・Unit/Integration・System・Production Database・Playwrightが成功。ログでもpytest2181成功/69省略/159 warning/681.32秒/全体coverage88%、Playwright291成功/16.6分/flakyなしを確認した。69省略を全試験実施とは扱わない。再起動や合格条件の変更はしていない。これはc7390ee3のCIであり、この後の文書コミットのCIとは区別する。

通常イメージの全OS監査を、既存Docker Scout 1.26.0で新規cacheを使って実施した。配布zip checksumも確認済み。292 package中16 packageに39指摘、HIGH3/MEDIUM1/LOW35、Python指摘0、終了2。先行6828f209とCVE ID/重大度の変化0、installed Python111件も変更0。HIGHのCVE-2026-102010/95619/85091はscanner上いずれもnot fixed。指摘抑制、リスク受容、CVE解消、PBDS/native閉包非該当の証明はしていない。

最初にPATH上の旧Scout 1.5.0でも監査が開始されたため、同じhandleを完了まで観測し、259 package/39指摘/終了2のログと別SARIFを保持した。旧版のpackage inventory数を新しい1.26.0の結果と混同しない。今回の正式な監査値は新しい292 packageの結果を使用し、両ツールの終了2を成功扱いしない。

## 後片付け・残条件・復旧

identityを事前保存した今回Web/PGのIDと再照合して停止し、自動削除を確認した。worker/回帰containerも終了時自動削除。使い捨てtmpfs DBは破棄済みで、実ユーザーデータはない。背景透過の入力2件と期限切れの合成結果1件は上記試験で削除済み。ログ、commit archive、通常イメージ、監査scriptと合成制御JSONをGit外で保持する。制御JSONのsynthetic tokenは公開・コミットせず、対応DBも破棄済み。

実ECS dispatch/IAM/network/S3、AWSモデル取得・性能・日常運用、常設worker/beat/Redis、実Stripe/RAK/Endive・共有DB/メール、管理者所有者/削除方針、外部連携、RDS/S3復旧、事業者/税務は未達。[背景透過telemetry修正](BACKGROUND_REMOVAL_TELEMETRY_2026-10-05.md)、[先行通常配布物](STRIPE_COMMAND_RUNTIME_6828F209_2026-10-05.md)、[正式公開条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を参照する。今回の背景透過限定検証を全API/課金PG回帰の成功へ読み替えない。

main/AWS反映には対象固定・現在稼働版/復旧定義の照合・必要な承認を別途行う。telemetry防止を戻す単純revertは優先せず、opt-outを維持した修正版を用意する。今回はアプリ追加変更/実環境反映なしなので実環境の切戻し操作は不要。

## 隔離証拠

文書追加後のrelease documentation39テスト成功。代表証拠10hashを照合し、変更文書2件の相対リンク189件欠落0、stageのUTF-8/LF・BOM/置換文字検査と空白差分検査も成功。実diffと検証範囲を自己レビューし、要修正指摘なし。新規UI文言/アプリ変更はなく、Python formatterの対象追加もない。

`C:/tmp/iaia-background-worker-c7390ee3/` にbuild/source archive、inspection、runtime/image/layer情報、回帰ログ、worker3ログ、HTTP6ログ、通常起動/設定チェック、cleanup記録、scannerログとSARIFを保存。代表証拠のSHA256は以下。

| ファイル | SHA256 |
|---|---|
| inspection.json | 3fe122154e8f5880e9b17a09e0d29b1e0ae6ad8760034501048f7941723a3c21 |
| regression.log | ba91cf066261f06e7ef3832199502eee0800531e0f309a66f2717ccf774b4fde |
| worker-success.log | 750ef6eb181b69c008f4725d5ad4f9440f24ea37bb04f909e1585bfdd60bd16f |
| worker-reentry.log | 750ef6eb181b69c008f4725d5ad4f9440f24ea37bb04f909e1585bfdd60bd16f |
| worker-failure.log | b215cd75af30914f6b0f326b6c4404d3d1a2f06ebd71ee6e17beef7fd46f4e00 |
| cleanup-jobs.log | 3ab8b73ed776c958c11a81e418f318fa482fbaf54fcdc6258d72e97461c2bc2f |
| expired-http.log | d2eb508709d7bf269a212bd40e17678a73c4a05e1f9a76a2123ff4404d2bee83 |
| runtime-full-1.26.sarif.json | f7928c21ead7b05de6ea774993e0a92db59c0ceef768ff0b0559d573170957df |
| worker_probe.py | 6a836debbcc679b8fda490569e57274be7ad405f6c91af13da36436cde719e2b |
| worker_runner.py | a3170f0ea52e49add3c91b1b09d3d5b6de4ea6fc19810bfb0b5f9c0b8256ad8a |
