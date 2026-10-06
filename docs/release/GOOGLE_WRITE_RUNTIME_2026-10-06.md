# Google書き込み結果不明・通常配布物の実worker検証（2026-10-06）

## 対象と結論

対象アプリは `28ac2bc7d63dfeb49092f2643e975da56953bd0e`、記録ブランチは `codex/google-write-runtime-20261006`。[応答喪失・結果不明修正](GOOGLE_WRITE_UNCERTAINTY_2026-10-06.md)を通常Dockerfileでbuildし、実PostgreSQL/Redis/Celery/Requestsのloopback HTTPで、実行期限内の曖昧な書き込みを再適用しないことを検証した。通常配布物のGoogle214・設定70テストは合計 **284成功/省略0**。

solo/prefork各14、合計 **28ケース** は結果不明22・成功6。元のjob/同期行保持、再試行API 400、追加28重複メッセージの `inactive-job`、追加HTTP 0を確認した。42 HTTP・合成provider適用28・providerエラー0。時計/期限経過注入、worker強制停止、Task/queue/token取得mockは今回の実worker試験に使用していない。

ただし新規Scoutは **終了2、HIGH 3を含む39指摘**。durable outbox・同期対象をまたぐ世代fence・結果照合/限定回復・実Google/AWS・運用/性能/復旧等は未達で、正式公開 **No-Goを維持**。main/AWS/共有DBの反映・追加承認は行っていない。

## 通常配布物の照合

- 完全なGit archiveを新規 `source/` に展開。通常Dockerfile/.dockerignore/entrypoint・runtime lockを使い、コードoverlay・追加pip・テスト専用イメージ・依存更新なし。
- 固定imageは `sha256:027a10cea68d254b0f6443cb9178929e8c3fb46134a91882c14762b3adc7f157`、tagは `tableno:google-write-runtime-28ac2bc7`、サイズ1,286,351,729 bytes、ユーザーtableno、通常 `/entrypoint.sh`、OCI revisionは上記アプリSHA。
- 選定 **707 source/assets** の欠落/余分/bytes hash不一致0、source Python cache0、entrypoint bytes一致。選定範囲はaccounts/api/schedules/scenarios/support/tableno/static/templates/tests(unit/integration)の既存inspect helper対象拡張子＋lock/manage.py/entrypoint。全trackedファイル・Markdown・TypeScript E2E・tests/utils等の全照合とは区別する。
- 先行固定f1 image `sha256:9735d7a06d7772336d7be323ff4746cf05f4f71918153f0b7e48a9323bacd70a` とinstalled packages **111**・先行依存10層の差分0。APT署名付き最新候補やnative ABI closureを今回調査/改善したという意味ではない。

## 回帰・実workerの検証

通常イメージはroot RO、cap drop ALL/no-new-privileges、既存entrypoint、helper/evidenceのみRO mountで実行し、アプリimportは `/app` を優先した。PG18.3とRedis7.4.11は固定image、PG network noneのnamespaceを共有し、ポート公開なし。DBは `google_write_runtime_fixture`、broker 11/result backend 12の合成Redisで、AWS/Secrets/Sentry/S3は無効。migrateは隔離DBだけに適用し、schemaファイルは変更していない。

通常回帰:

- Google関連25モジュール **214成功、59.435秒**、実PGテストDB作成/削除、2 GiB/2 CPU。既存unitテストにはmockがあり、別worker試験と区別する。
- 設定/サーバー/SDKログ/プライバシー/Sentry関連6モジュール **70成功、53.795秒**、network none・SQLite tmpfs、1 GiB/1 CPU。
- 両コンテナ終了0/OOM false/省略0。全課金/Web/背景透過/ブラウザー/負荷の全体回帰ではない。
- 記録変更後の文書39テストも成功（0.036秒、実DB setupなし）。文書2ファイルの差分/日本語/相対リンク/証拠hashをレビューし、staged UTF-8/LF/BOM/文字化け検査とwhitespace検査は成功、対応が必要な指摘なし。文書のみのためPython/JavaScript formatter・画面変更は対象外。

実workerはsoloまたはprefork/concurrency1、1 GiB/1 CPU、beat/gossip/mingle/heartbeatなし。各poolの正常配送14＋手動の重複配送14＋読み取りの実Celery retry1をworkerログで確認した（各29受信、合計58）。Google HTTPSのRequestsだけを `127.0.0.1:8016` へrouteし、実際のHTTP本文/Authorization/If-Match/RAWとDB状態を合成providerで検査する。producerとjob APIはDjango APIClientであり、ASGI HTTPではない。

| 各poolのケース | 数 | 検証結果 |
|---|---:|---|
| Calendar作成/更新/取消/409照合後PUT・Sheets PUTの適用後socket切断 | 5 | 結果不明、実行期限は未来、再試行/重複送信なし |
| Calendar/Sheetsの不正な200 ACK | 2 | 結果不明、providerは適用記録済み、成功へ推測更新なし |
| Calendar/Sheetsの適用後503、Sheetsの408 | 3 | 結果不明、機械的backoff/reapplyなし |
| Sheets 201行の最初100行適用後、次chunkを403拒否 | 1 | 結果不明/進捗49、残りchunkなし、先行100行再送なし |
| Calendar/Sheetsの正常ACK | 2 | 同期/出力成功、重複配送はinactive-job |
| Calendar GETの切断→実Celery retry→GET/条件付きPUT | 1 | 成功、書き込みは1回、GET/GET/PUTを実測 |

28のjobには28の異なる最終実行UUIDがあり、全て未来の実行期限で終了。結果不明は固定日本語案内・進捗10（部分出力49）を保持し、Calendar同期はpending、正常Calendarはsynced。provider適用はfixture上の定義であり、Google実サービスの503/408が必ず適用済みという保証でも、全経路exactly-onceの保証でもない。新しい別job、外部編集、再連携、token失効、長時間/kill/lease回復は今回の対象外。

## 回帰テストの残留メッセージと撤去

最初の撤去監査は、queue 1/unacked 0/index 0を検出して停止した。残ったCalendar task `b540305c-b9cb-46ed-8893-17effe9d08f4` のjob `472f9001-b3e2-46e8-b8ac-c09726ecbdc5` は通常runtimeの28 jobに含まれず、SQLでも不在、テストDBも削除済み。回帰テスト由来の残留と判断したが、発行した個別テストは特定していない。テストの完全なbroker mock/isolationを証明するものではない。

追加の実prefork workerはprovider HTTPを全面禁止し、その元メッセージを実配送して `invalid-job` として拒否。HTTP禁止marker0、既存28 job/28同期行の全値不変を確認した。CeleryのSUCCESSはjobの成功/回復を意味せず、ここでは拒否という戻り値である。残留を黙ってpurgeしたり、未知のjobを復元/再送したりしていない。

20:17:48 JSTにfull ID/name/task label/image/network/mount/entrypoint/終了状態を検査して、専用 **11コンテナ** と合成tmpfsを撤去した。全終了0/OOM false、queue/unacked/index 0、test DB0、task labelのcontainer/volume残数0。最後のSQLはjob結果不明22/成功6、user28、character400、同期pending24/synced4。同期行には各Sheetsケース用の未使用合成行12が含まれ、実アプリのSheetsがCalendar同期行を作るという意味ではない。通常image/archive/helper/logは保存し、元checkoutの別ハンドアウト作業13項目は保持した。合成データはhelperから再作成できる。

## 新規スキャンと未完了ゲート

既存の固定Scout **1.26.0**（git `ee73e17cd5243bd85c30416b274c339ad5e2f284`）を明示し、新規cacheで `cves --format sarif --exit-code` を上記tagの固定imageへ実行した。20:14:43 JSTに完了、292 packages/16 vulnerable packages/39 rules/results、CRITICAL0/HIGH3/MEDIUM1/LOW35/Python0。severity/only-fixed/ignore-base/VEX抑止やリスク受容は使っていない。

HIGHはgcc-14 source package（14.2.0-19）のCVE-2026-102010/CVE-2026-95619と、zlib（1:1.3.dfsg+really1.3.1-1）のCVE-2026-85091。スキャン上のfixed versionはnot fixed、先行f1のCVE/severity/package signatureと差分0。今回の署名付きAPT policy確認やnative closureの解決、OSゲート成功ではない。

20:18頃のアプリ28ac CIは5成功/Playwright実行中。今回の記録コミットのCI成功とは区別する。main読取は `8567f49f8d411bad7f732afaeebad85357eeca09`、AWSは今回読取/変更なし。DB schema/共有DB/実ユーザー/Secrets/IAM/課金/容量/正式通知の変更なし。承認済みfavicon以外のmain/AWS反映や、先行accounts 0065–0067/schedules0056等の共有migration適用は別の具体案・承認境界を守る。

## 証拠

証拠は `D:/tmp/codex-google-write-runtime-20261006/`。初回比較で先行manifestのファイル名誤記を訂正した。初回 `outcome-summary.json` はPowerShellの空array集約でproviderエラーを1と誤計数し、全caseのraw errorsとassertionを照合した `outcome-summary-verified.json` で0へ訂正した。元summary・残留監査・ログを保持し、製品試験の失敗/成功とは混同しない。

| 主な証拠 | SHA-256 |
|---|---|
| `source.tar` | `a7f27aa4bf98c86f5492d92004c41a1d8428b900100d0eb836beb9c3f8f4ca85` |
| `distribution-check.json` | `76ebeb115266dfeaaa48a004285fe47ae99764c62e649a7294c288b4dd257686` |
| `regression-tests.log` | `cd2ff7e6039938e791020d43fb4a7aa4e59ed8c71cb678ed70a3323384be28d0` |
| `regression-settings.log` | `b3f6e3e7265a06853f59044929c6c34934ed59c353491830a323250bad7c2bc0` |
| `results.json` | `e526ff810fb494230cc0dbc7589cb11d65e6fd196c9fac8f8933dc25f08a82d1` |
| `orphan-client.log` | `4ccd35e2adc61e0f0061192a1e08382a2f412de840185b86800a74cebe2fa2fe` |
| `scout.sarif.json` | `1027ec99acf7f636d52ad912840d89c415a418d5169f99902866c6b6800b061d` |
| `cleanup.json` | `a0a91781141f1b4f46578f035ebb86de000f4e4cc5e238331eff9120f0ec20c4` |
