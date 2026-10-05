# 背景透過の競合修正を含む通常配布物 7b75105e（2026-10-05）

## 結論と範囲

固定アプリ `7b75105ee6535b924ba2a500811816ea4945eac5` の通常Dockerfileから配布物を構築し、ソースoverlayなしのLinux/PostgreSQL回帰63件、実workerコマンド4ケース、実HTTP21確認に成功した。[終端状態保護](BACKGROUND_JOB_FINALIZATION_2026-10-05.md)と[起動応答の競合防止](BACKGROUND_DISPATCH_INTEGRITY_2026-10-05.md)を含む配布物の検証である。

実モデルを使うworkerのrunningを観測した後に、隔離fixtureの時刻を古くしてWebのタイムアウトを起動した。native初期化と推論の正確な開始時点は計測していないが、worker終了後も失敗理由・時刻を維持し、遅い結果画像を保存しないことを確認した。通常の成功・再実行・破損画像・期限後の結果削除・所有者制限も合格した。

候補CI全6項目successを固定SHA/branchで照合した。一方、新しい全OS監査は39指摘（HIGH3/MEDIUM1/LOW35、Python0）・終了2で未合格。実ECS/IAM/S3/AWS性能・外部連携・課金実運用等は未達で、正式公開No-Goを維持する。main/AWS/ECR/共有DB/Secrets/権限/課金/実通知/容量は変更していない。

## 配布物と隔離

- `git archive` の固定commitから通常構築。tag `tableno:background-runtime-7b75105e`、image ID `sha256:6ffcb1cc2f88deb352628306aec4b8944b184a27ec0c4fd264cc0be8e41b3f40`、revision labelも上記SHA一致。
- archive側とイメージ側の両方で選定した677ソース/画面/静的資産/テスト等をSHA256照合、欠落/不一致0、Python cache0。`/entrypoint.sh`も追跡ソースと同一。先行c7390ee3とPython依存111件の差分0、先頭10層も同一で、OS/nativeを修正したbuildではない。
- 自前のPostgreSQL18.3・tmpfs・network noneを起動し、Web/workerと今回の回帰/probeのみが同じnetwork namespaceを共有。公開port/外部通信なし。既存の合成専用設定を再利用し、実DB/Secrets/ユーザー情報を取得していない。Stripe Checkoutと課金メールは無効、S3不使用、cacheはLocMemでRedisではない。
- 通常WebはAPP_ENV=aws-preのproduction設定と通常entrypointで隔離DB migrate・collectstaticを実施し、232 copied/624 post-processed・Daphne起動、readinessのDB/cache正常、`check --deploy`・`migrate --check`成功。
- workerは通常entrypointから監査wrapperを起動し、その子プロセスが変更なしの`python manage.py process_background_removal_job <uuid>`を実行。推論/サービス/DB/ECSをmockするwrapperではなく、終了とfresh homeのtelemetryファイルを検査するだけ。1 CPU/2 GiB・home/tmpは新規tmpfs、既存モデルのみreadonly mount。CI抑制環境変数は未指定。
- U2NETモデル175,997,641 bytes、SHA256 `8d10d2f3bb75ae3b6d527c77944fc5e7dcd94b29809d47a739a7a728a912b491` を前後照合。ダウンロード/書換えなし。合成128×128画像のみで、実人物画像を使わない。

## 回帰・実コマンド・HTTP

配布物内のfinalization15件、dispatch13件、既存背景透過API25件、model6件、infrastructure4件が隔離PGで63成功/省略0、17.793秒。実行ロックの3ケースと観測診断も含む。ECS起動や推論のunit部分はmockであり、次の実worker/HTTPと区別する。

初回は文書試験39件も含めた102件を実行したが、`.dockerignore`で配布しないAGENTS.mdを読む文書試験1件がFileNotFoundErrorとなった。全102件成功とは扱わず、該当文書試験の削除/条件緩和/ドキュメントoverlayは行っていない。文書チェックはソースcheckoutで行い、通常配布物の関連63件を別実行して成功を確認した。初回ログも保持する。

| 実workerコマンド | 終了 | 状態/storage | fresh homeのtelemetryファイル |
|---|---|---|---|
| pendingの正常画像 | 0 | completed、結果保存、元画像/参照削除 | 0 |
| 同じcompletedの再実行 | 0 | 結果名/hash/updated_at不変 | 0 |
| 保存後に破損した別fixture | 1（期待失敗） | failed、汎用理由、元画像削除、結果なし | 0 |
| runningをWebでtimeoutした別fixture | 1（期待失敗） | timeout理由/updated_atを保持、遅い結果なし | 0 |

正常結果はPNG/RGBA・128×128・alpha0〜255、SHA256 `97118d98655762cab2a06137caeeba448a79f62b8cb7eacbd42f7b066c356cde`。日本語ダウンロード名と先行結果の同一性を確認した。正常workerの52.719秒は起動等を含む1回の隔離cold測定で、AWS性能・p95・同時利用基準の証明ではない。

実HTTPは7群×3確認：pendingの所有者202/他404/未認証401、completed200/404/401、再実行後200/404/401、guardのreadiness200/無料開始403・job数不変/不明job404、破損失敗503/404/401、期限後結果なし503/404/401、実worker進行中にtimeout503/404/401。job GETのno-storeとVary Cookie/Authorizationをassertした。

破損workerの最初のHTTP判定は、workerがまだ稼働中なのに終端状態を検査して失敗した。`failed-http-before-worker-exit.log`として保持し、同じworker handleの終了1を観測してからHTTPを再検証した。workerを新規起動/再試行して成功に見せたものではない。fixture経路もupload validatorの合格証拠にはしない。

正常完了fixtureのみを25時間前へ移動し、既定24時間/7日をassertして実cleanupコマンドを実行。結果1画像削除・job2行保持・削除失敗0を確認した。その後3つ目の正常画像fixtureで、実workerのrunningを観測し、時刻だけ20分前へ変更して所有者の実GETによるtimeoutを起動した。worker終了後のDB/媒体でfailed・timeout理由・時刻同一・結果参照なし・output画像0・job3行をassert。推論失敗のTracebackはlate workerログになく、遅い推論の結果を公開しない経路を確認した。S3やbeatの定期運用の証明ではない。

## CI・OSゲート

[7b75105e CI 37319485017](https://github.com/sheepdog0820/iaia/actions/runs/37319485017)はcompleted/success、SHA/専用branch一致、全6ジョブsuccess。ログでもpytest2205成功/73省略/159 warning/689.13秒/全体coverage88%、Playwright291成功/12.9分/flakyなしを照合した。省略を実施済みへ読み替えない。親c0b5380bの[CI 37317470226](https://github.com/sheepdog0820/iaia/actions/runs/37317470226)も全6success、pytest2193成功/72省略/全体88%・Playwright291成功/flakyなしを確認。これは各固定アプリのCIであり、後続の文書commitのCIとは別である。

Docker Scout1.26.0の全OS新規監査は292 package中16 package・39指摘、HIGH3/MEDIUM1/LOW35、Python0、終了2。先行c7390ee3とCVE ID/重大度差分0、SARIF hashも同一。HIGH3件はCVE-2026-102010/95619/85091で、scannerではnot fixed。指摘抑制/リスク受容/native閉包非該当の証明/ゲート解除はしていない。

初回監査はWindows一時ディスク容量不足で終了1、報告未完成。終了を確認してから、空き容量を確認したローカル固定Dドライブの今回専用temp/cacheへ、そのプロセスだけの環境変数で切り替えて再試行し、上記終了2とSARIFを取得した。初回失敗ログも保存し、監査成功とは扱わない。OS監査は通常配布物の合格を阻む残条件である。

## 後片付け・残条件・復旧

Web/PGの保存済みID/image/network modeを終了前に照合し、停止・自動削除を確認。worker/回帰/HTTP probeのcontainerも終了時自動削除され、該当container残数0。使い捨てtmpfs DBは破棄済み、合成入力3件と期限切れ結果1件は検証中に削除。モデルは未変更。archive/image/ログ/probe/合成制御JSONはGit外に保持し、制御tokenは公開・コミットせず、対応DBは存在しない。

scannerの今回専用cache/temp削除コマンドは実行ポリシーに拒否され、代替経路で削除していない。`C:/tmp/iaia-background-runtime-7b75105e/scout-cache` と `D:/tmp/codex-tableno-runtime-7b75105e-20261005/cache`・`temp` は残る。再生成可能なscanner一時データだが削除完了とは報告しない。監査SARIF/証拠はC側に別途保持している。

実ECS dispatch/IAM/network/S3、まだpendingの曖昧な起動応答の解決、DB/S3分散原子性/孤立ファイル回収/結果取得と保持cleanupの競合、AWS性能・運用、実Stripe/RAK/Endive/共有DB/メール、管理者所有者/削除方針、外部連携、RDS/S3復旧、事業者/税務等は未達。[正式公開条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を維持する。今回の限定配布物検証を全API/全課金回帰/公開可能へ拡張しない。

完了済みfavicon反映承認と固定6b6c570cの反映案をこの候補へ転用しない。main/AWS未反映で、実環境の切戻し不要。必要な検証・対象固定・現在稼働版/復旧版確認・個別承認を得てから反映する。今回は文書のみで、配布アプリへ追加変更していない。

## 代表証拠

`C:/tmp/iaia-background-runtime-7b75105e/`に証拠を保持する。文書追加後の39テスト成功、下記10hash一致、変更文書2件の相対リンク192件欠落0、stage2テキストのUTF-8/LF/BOM/置換文字検査と空白差分検査も成功。実diff・証拠・失敗/省略/未確認の区別を自己レビューし、当該文書の追加要修正指摘なし。新しいUI文言/アプリ変更はなく、Python formatterの新しい製品ソース対象はない。

| ファイル | SHA256 |
|---|---|
| inspection.json | aa322272baa94a75c068d120861ccbe9bd54d1d2f528c50e2f7807b93e103f1c |
| regression-runtime.log | 61bc6ae2fdcb4df2b8ed7bb81b1b9e88116455a6ed075c974d0a8f968078fec4 |
| worker-success.log | 398036cdf3ae8d215ec29ec98ad7b8b001c74fb122f319e75b190d889bf1d2ce |
| worker-reentry.log | 398036cdf3ae8d215ec29ec98ad7b8b001c74fb122f319e75b190d889bf1d2ce |
| worker-failure.log | 19c4edc9d1b6659eaa6fa52db9423ada7e5c64ee82c2daf39a65e3bf1b5e6314 |
| worker-late.log | 37b7cc9a44d6019649f18ee0095535c5b7ef1b7d4a259053160ba6443a4005a3 |
| timeout-http.log | 5969ed82f7c43ef7d5ac784915d544b25d0d30e19ec63ebba6f203819f9dade2 |
| late-verified.log | 62ab701b11147223eff08e25d8f91320fb8d6de5ace6ca66bf6b0162e684de9d |
| runtime-full-retry.sarif.json | f7928c21ead7b05de6ea774993e0a92db59c0ceef768ff0b0559d573170957df |
| late_worker_probe.py | f021e58def665f55274cfd4810cd069d6d7148b9761dee20e834b10b88935569 |
