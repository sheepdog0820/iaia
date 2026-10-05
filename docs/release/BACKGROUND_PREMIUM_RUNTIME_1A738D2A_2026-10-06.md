# 1a738d2a背景透過権限確認の通常配布物・実HTTP検証

## 対象と配布物

[背景透過job作成時のプレミアム再確認](BACKGROUND_PREMIUM_GATE_2026-10-06.md)の固定候補 `1a738d2a00291520020662f39417b50dcd6e25fd` を `git archive` から構築した。検証記録専用ブランチは `codex/background-premium-runtime-20261006`。このブランチではアプリ・依存lock・Dockerfile・entrypointを変更しない。元worktreeのハンドアウト作業を混入させない。

| 項目 | 確認結果 |
| --- | --- |
| 通常配布イメージ | `tableno:background-premium-runtime-1a738d2a` |
| 固定image ID | `sha256:9c4e660278d6e468971424a29eea25f9c8712eff43a1a8bdd0320d78513dfff7` |
| revision label | 上記full SHAと一致 |
| 収録対象 | 680ファイル、双方の集合一致・SHA-256不一致/欠落/余分0 |
| Python依存 | 111パッケージ、先行3e5d46eeと名前/バージョン一致 |
| 依存層 | 先行3e5d46eeの最初の10層と同一 |
| Python生成キャッシュ | 0、entrypoint本体と収録sourceのbyte一致 |
| 回帰テスト | 143件成功・省略0、50.353秒、終了0 |

選定対象はaccounts/api/schedules/scenarios/support/tableno、static/templates、tests/unit/integrationのPython・HTML・CSS・JavaScript・画像/font/JSONと、lock/entrypoint/manage.py。ファイル選定範囲外まで全ファイル一致と主張しない。回帰対象は先行記録と同じ背景透過6モジュール・有料機能ライフサイクル・画像API/複数画像で、今回の11件と実PGロック2件を含む。

通常イメージの `/app` をそのまま使い、アプリsource・SDK・coverageのoverlayはしない。読み取り専用の外部harness/probeを追加し、回帰テスト内でmediaを使い捨て/tmpへ設定する。AGENTS.md等は既存Dockerignoreで配布しないため、文書テスト39件を通常イメージの143件に含めていない。

## 隔離構成と実HTTP

PG18.3はnetwork none・公開portなし・256MiB・512MiB tmpfs。Web・合成ECS endpoint・probeは同じnetwork namespace内のloopbackだけで通信する。Webは未改変entrypoint、APP_ENV=aws-pre、DEBUG=False、read-only root、0.25 CPU/512MiB、専用合成media、/tmpとstaticfilesのtmpfsで起動した。既存entrypointによる隔離DBのmigrateとcollectstaticが成功し、`232 static files copied, 624 post-processed`、ASGI listenを確認してからprobeを開始した。

S3/Redis/Stripe購入/課金メールは無効、資格情報・ユーザー・画像はすべて専用合成値。DB/schema操作は今回の使い捨てPGに限り、共有AWS・実ユーザー・実課金・メール配送は使わない。SDKのECS endpointだけ `127.0.0.1:8766` のfixtureへ向ける。合成endpointが署名header形式・RunTask target・cluster/taskDefinition/command/clientToken・subnet/security group・public IP DISABLEDを確認するが、実IAM署名検証・実ECS起動の成功ではない。

未改変Webへ本物のToken認証を伴うHTTPを送り、次の16確認すべて成功、probe終了0。APIClient/force_authenticate/アプリ関数のpatchは使わない。

- Readiness 200でDB/cache ok、匿名POSTは401。
- 権限失効：別接続でuser行をlockし、is_premium=Falseを未commitで保持。その間にHTTP POSTを開始し、Webが最新flagの `SELECT ... FOR UPDATE` でこの接続にblockされることを `pg_blocking_pids` / `pg_stat_activity` から観測した。保持中はjob/画像/起動要求0、commit後は日本語403で同じ0を維持する。
- ユーザー削除：合成user/Tokenの削除を未commitで保持し、同じ実Web user行ロック待機を観測。commit後は500ではなく日本語403、job/画像/起動要求0。観測は主接続PID147、失効時Web PID149・削除時PID150。queryのuser ID/is_premium/FOR UPDATEとwait種別Lockも照合し、固定sleepだけを競合成立の根拠にしない。
- 非premiumのstaff/superuserと通常userは、初期の日本語403・起動要求0。失効待機と初期拒否のJSONは共通の `detail` / 「背景透過はプレミアムプランの機能です。」で、application/jsonを確認。
- 権限復帰後は202・pending・所有者status URL・保存元画像byte一致・保存task ARNを確認。実SDK wireは1回で、clientToken=job UUID。実workerの起動・推論ではなく合成ECS応答である。
- 同じuserの重複POSTは409で起動要求を増やさない。作成後に権限を失っても既存jobはpending・元画像/時刻/ARN不変で、所有者status 202。他人404・匿名401、job GETのno-storeとVary Cookie/Authorizationを確認する。復帰しても進行中jobの重複は409のまま。
- 合成jobを期限超過にし、通常cleanupコマンドでtimeout 1件・failed・元画像削除を確認。所有者statusは503。その後の許可済み新規POSTは別UUIDで202、SDK wire総計2回・2job。再度失効してもこの作成済みjobのstatusは202である。

WebログのTraceback・ERROR/CRITICAL・500は0。期限超過後の503は想定ケースであり、全HTTPが200だったとは扱わない。今回の回帰・HTTP probeは初回実行で成功した。先行修正時のRED/途中失敗を今回の再成功で削除・上書きしていない。

## 新規全OSスキャン

Docker Scout 1.26.0でこの固定イメージを新規に全スキャンした。292パッケージをindex、脆弱な16パッケージに39指摘、HIGH3/MEDIUM1/LOW35、Pythonパッケージ指摘0、終了コード2。先行3e5d46eeのCVE/package/severity比較は差分0、SARIF自体のhashも一致した。新イメージを実際に指定して完了した結果であり、同じ依存層という推測だけの結果ではない。

HIGHは `CVE-2026-102010` / `CVE-2026-95619` / `CVE-2026-85091`。未修正・未受容・未抑制で、正式公開ゲートは未合格のまま。Scannerの検出を全適用条件の証明に拡張せず、OS/native閉包等の評価・解消を別途必要とする。

キャッシュとTEMP/TMPはこの検証用の新しいD:配下へ限定した。`DOCKER_SCOUT_CACHE_DIR` の動作は[Docker公式の環境変数説明](https://docs.docker.com/scout/how-tos/configure-cli/)を確認した。既存キャッシュの削除・移動・別経路での掃除は行わず、今回のcache/tempも証拠とともに保持する。

## 後片付け・証拠・未確認

probeが自身の作成したprefix付き合成ユーザー集合を照合し、元画像・2job・user/Tokenを削除して、ユーザー/job/Token/画像0を確認した。PGで別途 `0|0|0` とtest DB破棄済みを確認。以下の3containerはID・用途label・network/OOMを確認後、停止・削除した。回帰/probeの一時containerも終了0で自動削除済み。残存container・公開port0、tmpfsの合成DBは消えており、fixtureから再構築できる。

- PG：`7e55ffab29a84e243beb1539fa66608151672d06c02a951a738294dcd555447e`
- 合成ECS wire：`cac5ae35fa2f6b923694b91b81071009a5cfa61eeaad3622a02260103fdfd7d3`
- Web：`6cfcf96951d0e8f287b6eb81ee4791f068415dda1f1c944f7641763ed40afc42`

証拠は `D:/tmp/codex-tableno-premium-runtime-1a738d2a-20261006/` にarchive/build/inspection、正常回帰・HTTPログ、合成wire要求、container設定、Scout全結果とharnessを保存した。

| 証拠ファイル | SHA-256 |
| --- | --- |
| `distribution-check.json` | `f2d121a2af760738c7f32ac4575fd8821c5fbb32cbd552004297e862086730bb` |
| `inspection.json` | `e69f3694deee51b537cd13267a1b115026b4b7bde7db98fd727dfe6fae64938a` |
| `regression-runtime.log` | `c69be7b5e2063a08a59da461b322ab8f7ad3b63644d0d85fbb04f1f65c509a51` |
| `http-gate.log` | `d6b72229da7226d62bd4414e95f85263aee699661a407e9db3beff0c1cdc097e` |
| `runtime-containers.json` | `c804ef9c289d77c8b7adb0798a50d1ae2551faae756627c33c84eeb57e117beb` |
| `fake-ecs-state.json` | `7a90e6355d9b8549ccda0a90bdf51054b388ca26ab24def0401f69b0470136a4` |
| `web-final.log` | `7667de2ecf1e862ed7d27cc91b42d74f005bc146730787a864869a66d9cfe086` |
| `fake-ecs-final.log` | `9d53bb06faea8eac1ac61da6152d3d9e2caf857ae476a4b9085adde9d0bd86d2` |
| `scout-full.sarif.json` | `f7928c21ead7b05de6ea774993e0a92db59c0ceef768ff0b0559d573170957df` |
| `scout-full.log` | `5fb59346a86ca593361316cf50e1d103ea7dd42e03f6c8c326a32702ff0e2c81` |
| `scan-summary.json` | `455a470a5f7ed78d444fea1b5a1ce4cdf15945a9e8da0d2a3b9b3346194b633e` |

候補1a738d2aの[CI run 37382212283](https://github.com/sheepdog0820/iaia/actions/runs/37382212283)は固定full SHA・ブランチを照合し、全6ジョブsuccess・run completed/successを確認した。Unit job112006746922は `2240 passed, 83 skipped, 159 warnings in 615.69s`、全体coverage表示88%（41653文中未実行5180）。Playwright job112006746874は `291 passed (16.9m)`。初期の実行中ログ取得404は観測失敗で、テスト失敗や成功の根拠にせず、完了後のjob/runとログで確認し直した。pip cache保存の競合警告があるが、jobは成功している。今回文書コミットのCI成功とは区別する。

文書39件成功、変更2文書の相対リンク196件・欠落0、上表の証拠11hash一致を確認。ステージ対象2ファイルはUTF-8/LF・BOMなし・差分空白チェック合格。自己レビューで追加修正が必要な指摘はなく、アプリ/SDK/UI表示の変更は含めない。元worktreeの未コミット13項目はそのまま保持した。

実AWS/ECS/S3、Stripe・外部連携・共有DB採用、workerの実起動/推論、ブラウザー、正式性能/SLO・長時間負荷・RPO/RTO復旧・本番公開は今回の検証範囲外。今回の修正/記録を既存の固定候補反映承認へ追加せず、main/AWSは変更しない。正式公開No-Goを維持する。復旧は記録のみの通常revertで、共有DBの逆移行・アプリ再デプロイは不要。
