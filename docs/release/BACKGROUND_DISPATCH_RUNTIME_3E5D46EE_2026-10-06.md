# 背景透過起動結果不明時の修正・通常配布物検証

## 固定対象と判断

アプリ対象は `3e5d46eed883ad42161a3d83c8643350a114a342`。[起動結果不明時の入力保持](BACKGROUND_DISPATCH_UNCERTAIN_2026-10-06.md)を、source/SDK overlayなしの通常配布物で検証した。今回のリポジトリ変更は証拠文書のみ、ブランチは `codex/background-dispatch-runtime-20261006`。正式公開は **No-Go** を維持する。

合成ECS endpointと通常Webの実SDK通信、受理を模した後の応答障害、実U2NET worker、非公開HTTP結果取得までを確認した。ただし合成endpointへの受理記録は実AWS/ECSでの起動・課金・IAMの証拠ではない。全OS監査のHIGH3は未解消/未受容で、共有運用・外部連携・性能/復旧等も未達。

## 配布物・隔離境界

| 項目 | 証拠 |
| --- | --- |
| image | `tableno:background-dispatch-runtime-3e5d46ee` |
| image ID | `sha256:395d5c051ed93596f47decd7e2ca6c7c8271d085228f9d6e6886ef0c7e1280f2` |
| revision label | 上記固定SHAと一致。`git archive`のclean sourceからbuild、ECR未push |
| 選定ファイル | アプリ/画面/静的資産/単体・統合テスト等679ファイル。archiveとimageの両方向setとSHA-256一致、欠落/余剰/不一致0、Python cache0 |
| entrypoint/依存 | 通常 `/entrypoint.sh` と配布内scriptが同一。先行7106f6fbとPython111 package/version・先頭10依存layer同一 |
| 通常image回帰 | PG97テスト成功/省略0、14.429秒、終了0。文書39件はDockerignoreがAGENTS等を除くためこのimageで実行せず、checkoutで別検証する |
| Web | APP_ENV aws-pre・DEBUG false、read-only root、512MiB/0.25 CPU。tmpfs静的/tmp、合成mediaの専用bind、通常Daphne |
| 初期化 | 初回通常entrypointで隔離DB migrate/collectstatic成功。232 copied/624 post-processed。地域設定補正後のWebも同じimageでcollectstatic成功、既存の同じDBを保持 |
| DB/network | PostgreSQL18.3、固有fixture DB/user、256MiB、network none/tmpfs。Web/worker/probe/合成endpointは同じnamespaceのみ、公開portなし |
| 外部サービス | S3/Redis/Stripe checkout/課金mail無効、合成資格情報のみ。SDK ECS endpointは127.0.0.1:8766、検証設定のstandard retry/最大2試行。SDK/HTTPのsleepやsend関数を置換しない |

archive/source/SDKをアプリへ重ねていない。外部probeコードは`/evidence`に配置し、アプリのmodule/関数を差し替えない。合成endpointは独立HTTP serverとread-onlyのDB観測で、requestの署名形式・target・固定task/command・job tokenを検査し、1 tokenにつき受理記録1件と最初のpending/source/timeを保存する。記録7要求のsubnet/security group/public-IP設定も事後照合した。署名・資格情報そのものをログへ出さない。追加した環境設定は隔離fixtureだけで、実環境や配布sourceを変更していない。

## 実SDK通信・HTTP・worker

成功したHTTPは **35件**（補正後pre-worker23、worker完了後6、再実行/期限後worker確認後6）。各job GETにno-storeとCookie/Authorization Vary、他所有者404・匿名401を検査した。初回の失敗probeや未観測running HTTPは35に含めない。

- 接続断: 合成受理後、2 SDK要求とも接続を閉じる。Webは202/pending、同じsourceと時刻を保持、ARNは未保存。後の16分期限fixture変更→通常cleanupで1件timeout、元画像削除、所有者503を確認。
- 回復: 最初の合成受理後500、2回目は同じtoken/parametersで200。同じ受理記録のARNを保存、pending/source/time保持。
- 確定拒否: 400 InvalidParameterException、SDK要求1回・受理0。503/failed、元画像削除、backend詳細はresponseに露出しない。
- 500継続: 合成受理後、2 SDK要求ともServerException。Webは202/pending、同じsource/timeを保持、ARN空のまま。独立した正常image workerを手動起動すると実U2NETでcompletedへ進み、元画像が消え、所有者がRGBA透過PNGを取得できた。

各active jobへ再POSTすると409、job/合成RunTask要求の追加0。合成要求は計7回・受理記録3件。失敗後も取得した入力bytesが元のPNGと一致し、最初の合成受理時のDB snapshotとstatus/source/timeを比較した。実ECSによる自動起動や永続outbox/reconcileは今回検証していない。

workerは通常の `process_background_removal_job` command、同じimage・namespace/media/DB、1 CPU/2GiB、read-only root・一時home/cacheで起動。既存model `u2net.onnx`（175,997,641 bytes、SHA-256 `8d10d2f3bb75ae3b6d527c77944fc5e7dcd94b29809d47a739a7a728a912b491`）のみread-only mountした。終了0/OOMなし、hostから見た単発cold run約47.300秒で、AWS/p95の性能保証には使わない。通常imageのtelemetry opt-outを維持し、新しいnative安全性全体の証明とはしない。

出力は128×128 RGBA、alpha extrema0/255、日本語attachment filename、stored bytesとHTTP bytes一致。SHA-256は `97118d98655762cab2a06137caeeba448a79f62b8cb7eacbd42f7b066c356cde`。同じcompleted jobへの通常command再実行はmodel mountなしでも終了0、PNG・完了時刻不変。期限切れjobへのcommandはmodel mountなしで既存timeoutのCommandError/期待終了1、status/ref/result不変。これらをHTTP所有者制限と併せて確認した。

## 初回失敗・観測限界を保持

1. 合成endpoint補助コードが配布物にないpsycopg2をimportして終了1。配布物には固定psycopg3があり、補助importを修正し、終了済みの同じ補助containerを再起動した。アプリ/SDK/依存を追加・overlayしていない。
2. 初回pre-worker probeは通常Webの初期migrate途中に`migrate --check`で終了1。Webは同じ起動を継続し、DBのuser/job各0を確認した。初期Webを観測timeoutだけで再起動しない。
3. 起動完了後のprobeは最初のPOSTがNoRegionErrorにより503で終了1。USE_S3_STORAGE=falseのfixtureではAWS_S3_REGION_NAMEがsettingsで定義されず、SDKのdefault regionが必要だった。隔離envにAWS_DEFAULT_REGIONを補足してWebを同じimageで置き換え、同じDBの2 users/1 failed jobを保持。resume guardがそのfixtureとsourceなしを明示検査し、別の合成prefixで後続を実行した。DB reset/失敗行削除で隠していない。
4. running専用HTTP probeはworker終了後に起動し、running assertionで終了1、HTTP要求は未実行。途中のDB readでrunning/sourceありは観測したが、「実HTTPでrunningを確認」とは扱わない。workerを再起動して合格を作らず、同じcompleted jobの結果・再実行を検証した。

失敗ログを残し、初回全成功とは扱わない。最終probeの後にguard付きの同じ隔離DBで合成job/fileだけを片付け、media files0を確認した。自作5 containersはidentity/network/tmpfsを照合して停止・削除し、tmpfsDBを破棄した。元checkoutの13ハンドアウト関連変更は保持した。fresh D Scout cache/tempは証拠として残し、先行の削除拒否されたcacheへの別経路削除も試していない。

## OS監査・CI

Docker Scout1.26の新しい全image監査は292 packages・16 vulnerable packages・39 findings（HIGH3/MEDIUM1/LOW35、Python0）、終了2。先行7106f6fbとのCVE/package/severity差分0。HIGH `CVE-2026-102010`/`CVE-2026-95619`/`CVE-2026-85091`は解消・抑制・受容済みではない。今回はC容量障害なし、process-onlyのfresh D TEMP/TMP/cacheで完走した。

固定3e5d46eeの[CI 37377623775](https://github.com/sheepdog0820/iaia/actions/runs/37377623775)はSHA/専用sourceブランチ・terminal successと全6ジョブ成功を照合した。Unit job111990845774は2231 passed/81 skipped/159 warnings、585.35秒、全体表示88%（87.56%）。Playwright job111990845662は291 passed/12.8分、flaky/retry記録なし。親a97f07b0の[CI 37375521876](https://github.com/sheepdog0820/iaia/actions/runs/37375521876)はterminal failure（Unit runner shutdown、中断以外の5ジョブsuccess）、勝手な再開始なし。今回のdocsコミットのCIはpush後に別SHAで確認する。checkoutの文書39件は0.045秒で成功、記録13 SHA-256一致・相対リンク195件欠落0を確認した。

## 証拠・未確認・復旧

証拠は `D:\tmp\codex-tableno-dispatch-runtime-3e5d46ee-20261006`。以下SHA-256のほか、build.log、runtime-containers.json、fake-ecs-state.json、worker-reentry/after-timeout.log、probe source、source archive、synthetic-only envも保存した。

| ファイル | SHA-256 |
| --- | --- |
| inspection.json | `6d967ef436c39f82ae3e1f0f432d1e5dd93894d31ecf63988fa2eab9c0e9019c` |
| regression-runtime.log | `a1d79131e68e265d4555aff97a958b7f1feaf5b353fcdf6c2731e24a20fc2722` |
| fake-startup-failed.log | `4ab6badb4ee20701021d87441c35de6583eaf618dd4d07d08d1aa3c6d4a9d937` |
| http-pre-worker.log | `f87ceb15410bde28ff826ce26228e0576558258fa64d145847921a593a61ee63` |
| http-pre-worker-final.log | `fbe47b79759cde7487ec073adc0005f8713b16c488d3fdaf0f82532a698e8977` |
| web-before-region-fix.log | `e1b7a780499ef87f52ad3b5cf37b3587c26239157ac184120ce5dc8973e6e9a9` |
| http-pre-worker-resume.log | `78103ea3add15604c531e493b8672147ace471dfdb91521e5695c05573f35be2` |
| http-worker-running.log | `966eda72c0631a32d5ce677c393ae1362653b4802d44d6fb44265e07343c5f2f` |
| http-worker-completed.log | `0604cb0a3a94781551f1cdfe0c7845cfceb813c2d9d4fb878c412607da122f96` |
| http-worker-after-reentry.log | `c25665ca6fcc89db446f91423f7daa1244e9a2128321012e978974f57aa5a917` |
| worker-success.log | `8b69e725237d4b1c9e6840e4be9f9eae753dcdc1fac4297b61da7ad8fee71217` |
| scout-full.sarif.json | `f7928c21ead7b05de6ea774993e0a92db59c0ceef768ff0b0559d573170957df` |
| web-final.log | `b19cc885cbcf82789f67caae37335b4e1eacd2950749a437f815be5dcf3e2058` |

実ECS dispatch/通信障害・IAM・実S3・DB/storage分散原子性・孤立task/file回収・SDK設定変更をまたぐ再送、AWS性能/常設worker、課金/外部連携/監視/復旧/事業者条件は未証明。[正式公開条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を狭い検証で解除しない。

完了済みアイコン8567f49fの承認と固定6b6c570cの反映案を転用しない。今回main/AWSを再照合・変更しておらず、ECR/ECS/S3/CloudFront・共有DB/実データ・Secrets/IAM・実課金/通知・常設容量/継続費用も変更なし。未反映なので実環境切戻し不要。この証拠文書のrevertは配布アプリを変更せず、ソース不具合を再導入する旧アプリへの切戻しは優先しない。
