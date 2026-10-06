# b3496898背景透過：通常配布物・実HTTP・資格情報更新の検証

## 固定配布物・回帰

[署名途中の入力保持修正](BACKGROUND_SIGNING_OUTCOME_2026-10-06.md)の候補 **b349689860426eb72f570cea0953faf60b2f0e39** をgit archiveから通常Dockerfileで構築した。証跡専用ブランチは `codex/background-signing-runtime-20261006`。アプリ・SDK・依存lock・Dockerfile/entrypointは変更せず、元checkoutのハンドアウト13差分を混入させない。

| 項目 | 結果 |
| --- | --- |
| image tag/ID | tableno:background-signing-runtime-b3496898 / sha256:babec53b6deefe4be6e2c524ee31a74f146d5944f5c18134af87b02a69bd1662 |
| revision label | 上記full SHAと一致 |
| 選定source/assets | 682個、集合差異0・SHA-256差異0、entrypoint bytes一致、Python cache0 |
| 依存 | 111パッケージの名前/版、最初の10依存層が通常ba51bdd8と一致 |
| 通常配布物PostgreSQL回帰 | 185件成功/省略0、49.559秒、終了0。新規14と既存実PG lock16件を含む |

選定範囲はaccounts/api/schedules/scenarios/support/tableno・static/templates・tests/unit/integrationのPython/HTML/CSS/JavaScript/画像/font/JSONとlock/entrypoint/manage.py。全イメージ全ファイル一致の主張ではない。通常 `/app` source・SDK・coverageを差し替えず、外部harness/probeだけをmountした。回帰は先行224件から、Dockerignoreで非配布の文書に依存する39件だけを除いた同じ13モジュール。pytestのSDK/inferenceモックは各既存テストの境界であり、後述の実HTTP/実U2NETとは区別する。

最初の `--network none` ビルドはapt工程の通信失敗・終了1だった。通常設定で再実行すると既存の依存工程をすべてcache利用し、新sourceの通常image構築が成功した。依存を更新/追加インストールしていない。初回ログを保持し、初回ビルド成功とは報告しない。

## 隔離・実HTTP44確認

PG18.3はnetwork none・公開portなし・256MiB/512MiB tmpfs。Web・合成ECS/資格情報サービス・probe/workerはそのnetwork namespace内loopbackだけで通信する。Webは未改変entrypoint・APP_ENV=aws-pre・DEBUG=False・read-only root・0.25 CPU/512MiB。隔離DB migrate、静的収集 `232 copied/624 post-processed`、ASGI起動・readinessのDB/cache okを確認した。共有DBやAWSの移行ではない。

S3/Redis/Stripe購入/課金メールを無効にし、user/Token/資格情報/画像は合成値だけを使う。ECS endpointとcontainer credentials URIをloopback fixtureへ指定し、SDKのserializer/signing/retry/parser/本物のcontainer credential refreshを実行する。短い8分期限の合成資格情報がmandatory refreshを起こし、初回RunTask500後に資格情報取得をHTTP400へ切り替える。アプリ関数・SDK・認証のpatch、APIClient/force_authenticateは使わない。実IAM認証・実AWS受理/Fargate起動の証明ではない。

成功したprobeの累積 **44 HTTP確認**（prepare38/completed3/finish3）、終了0。合成ECS wire9要求・資格情報16要求を記録し、各wireのtarget・署名形式・UUID clientToken・cluster/taskDefinition/command/network/public IP DISABLEDを検査した。

- 初回500→資格情報更新失敗：RunTask送信1回、資格情報更新の失敗3回、pending202・source bytes/参照/updated_at不変・error/task ARNなし。初回の資格情報失敗だけなら送信0回・failed503・source削除。
- 初回500→最終400、および初回500→HTTP200/tasksなし/明示failures：同じ全parameters/tokenでwire2回、pending202・元画像と時刻を保持。初回の400/明示failuresだけなら各wire1回・failed503・source削除。
- 初回500→成功task ARN：同じparameters/tokenでwire2回、pending202・ARN保存・source/時刻保持。
- 全4 pendingケースの重複POST409・SDK要求不増、所有者status202、他人404・匿名401、no-store/Vary Cookie/Authorizationを確認。非premiumの日本語403・job/画像/dispatch0、匿名POST401も確認した。
- retry_refusedのjobだけを合成的に16分前へ置き、通常cleanupでtimeout1件・failed/source削除、所有者503・他人404・匿名401を確認。

最初のprobeは `/app` import path未指定でModuleNotFoundError・終了1だった。harnessのsys.pathを訂正した後に上記prepareへ進んだ。不存在の補助ファイル名2回/Windows rg glob指定の読み取り診断も訂正した。アプリの条件・SDK retry・待機上限を緩めていない。

## 実worker・再実行

保持されたrefresh_fail入力を、通常imageの未改変 `process_background_removal_job` コマンドと実U2NET/CPUで処理し、completed・終了0を確認。既存モデルをread-onlyでmountし、外部downloadなし、1 CPU/2GiB・read-only root・一時/tmpで実行した。モデルSHA-256は `8d10d2f3bb75ae3b6d527c77944fc5e7dcd94b29809d47a739a7a728a912b491`。

実HTTP200の128×128 RGBA PNG、alpha extrema0/255、元画像削除、所有者限定/他人404/匿名401を確認。結果SHA-256は `97118d98655762cab2a06137caeeba448a79f62b8cb7eacbd42f7b066c356cde`。worker再実行後もstatus/updated_at/結果参照/hashが不変でSDK要求9のままだった。

期限切れjobのworker再実行は既存コマンド仕様どおり `CommandError: Background removal timed out.`・終了1。status/updated_at/画像なしを保持した。最初のshell checkerは全再実行に終了0を期待して停止したため、コマンドの実仕様と状態不変を確認した。初回finish比較もJSONでtupleがlistになる差異で失敗した。harnessをlistへ統一し、次のfinishで不変性/cleanupに成功した。失敗finishで既に行った3 HTTPは44件へ合算せず、その失敗ログも保持する。最初から全probe成功とは扱わない。

## 未解決のSDKログ露出・全OS監査

入力保持は成功したが、通常WebログにSDKのmandatory refresh警告2回、Traceback見出し4件、合成資格情報エラー本文marker4件が残った。アプリ側のdispatch詳細marker/ERROR/CRITICAL/HTTP500は0、HTTPの応答本文には両markerがない。SDK警告は想定して注入した障害だが、**エラー本文のログ露出は未解決**。先行unitのaccounts loggerだけの検証を全SDKログ保護の証明へ拡張しない。今回、実Secretsの漏えいや過去のCloudWatch露出は検証していない。次の安全な作業は本番形式のroot/SDKログについて再現テストと保護修正を行うこと。

初回のdefault Docker Scoutは1.5.0で259 packages/39指摘・終了2だった。CLIの版と範囲を区別し、既存の固定 **Scout1.26.0** で今回imageを再監査した結果は292 packages・16脆弱packages・39指摘（HIGH3/MEDIUM1/LOW35、Python0）、終了2。先行ba51とのCVE/package/severity差異0、SARIF hashも一致した。依存層同一という推測だけで「新規監査済み」とはしていない。

HIGHはCVE-2026-102010/CVE-2026-95619/CVE-2026-85091。未修正・未受容・未抑制で公開ゲートは未合格。[先行native再照合](RUNTIME_NATIVE_REVALIDATION_2026-10-06.md)のbytes/公開署名一致をビルド閉包やPBDS非該当の証明へ拡張しない。新しいD:配下cache/tempと両版の報告を保持し、旧cacheを削除/移動していない。

## 後片付け・CI・影響

probeがprefix付き合成ユーザー8名/job UUID7件の集合を完全一致で確認し、その画像/job/user/Tokenだけを削除した。独立PG確認でもuser/job/Token=0、test DBなし、保存先media file0。名前/ID/用途label/公開portなし/network/OOMなしを照合し、Web `3fba2d4a7073f2120b1954f6b01f5904bb12864c02d39185f344f9e52e04a26d`、fixture `21a35b3d8ad60c8f8ab8892c1f25fae33015b598a76dbf934d77f97febbdb2da`、PG `619896a7e31ed4a270c7e1aaea9da9f6d48d493373d5d54c868fdfe07e9e60ad` を停止・削除した。今回labelの残存container0を確認済み。途中の停止出力がyieldした後もcontainer一覧で終了を再照合し、停止を重複実行しない。tmpfs DBは破棄済みでfixtureから再構築可能。archive/harness/model/ログ/cache/mediaフォルダーは保持する。

候補の[CI37393905801](https://github.com/sheepdog0820/iaia/actions/runs/37393905801)はfull SHA/branch一致を照合した。先行照合では4成功/Unit・Playwright実行中だったが、証跡コミット直前の後続照合でrun completed/success・全6ジョブsuccessを確認した。この最新結果を追記し、アプリ候補のCIと今回文書commitのCIを区別する。CI成功だけでSDKログ露出やOS指摘を解消扱いしない。

実AWS/ECS/S3・実Stripe/外部連携/共有DB運用・正式性能/長時間負荷・RPO/RTO復旧・ブラウザー表示・本番公開は今回の対象外。main/AWS・共有DB/schema/実データ・Secrets/IAM・課金/継続費用/常設容量・通知は変更せず、既存の固定6b6c570c反映案やfavicon承認へ今回修正/証跡を追加しない。正式公開No-Goを維持する。文書の復旧は通常revertで、共有DBの逆移行や再デプロイは不要。

文書関連39テスト成功（0.037秒）、変更2文書の相対参照204件/欠落0、下表20ハッシュ一致。ステージ済み2ファイルのUTF-8/LF/BOMなし・差分検査に合格した。自己レビューで証跡文書の追加訂正を要する指摘なし。アプリ/UI表示の変更はなく、日本語premium拒否文言は実HTTP JSON完全一致で確認した。SDKログの未解決事項は文書合格で解消扱いしない。

## 保持証跡

保存先は `D:/tmp/codex-tableno-signing-runtime-b3496898-20261006/`。

| 証跡ファイル | SHA-256 |
| --- | --- |
| build.log | 42ae2dea07e73a887625d4d90fc52ef2b4b3ec45a982cbdee0518b24521e48d9 |
| build-normal.log | 1d3565efa561924ff9acabb137f561baaca2d7eb206fb1525d718aa108f384a7 |
| distribution-check.json | b6738a70d199d2344fc18e34fc1faee69cf9c1405879963b66505e6ca5eaaebe |
| inspection.json | bbd436702d8353e259982c866f0327882ccd1e7997e145df39c1e6714c7bc92c |
| regression-runtime.log | fe45b2627b0add6fc44aedbd512ad143398f78ac303f5224c0dd87f2c5d82b49 |
| http-prepare.log | c965c840e176872d78d704491ef62c46dedb37f3203d03f560d573139707c4db |
| http-prepare-corrected.log | 5978d903d4d3ec66baa2b60379acaaddb4afd28858660fb11af56644b2491965 |
| http-finish.log | 54c08b18275b5cca7b0e5d1d66a7b3b05039f9136ea626a755253f82b9983e92 |
| http-finish-corrected.log | af91ec552aa651f2399f52c466d4678076862e8a6cb9a624e878b47a56bf46dc |
| http-state.json | d466ff5fc81ea11119abb16e13f05b35613b9775d282f20766c909050bc5ce0f |
| fake-ecs-state.json | e2d0ce708bb593c0e22a15b612ba0b24e45b663973a1334a3f5c8e71b4e03962 |
| web-final.log | 76debd85f967362b97a6f1ae64a4ea82e89a87a939dfec1aaf7ba89203750ca9 |
| web-log-check.json | 683e2608482b48d333ea374051726f1bfc5199eb74aa2383f560b1394eef24dd |
| runtime-containers.json | 71856916fd6e7f597fe951c4cbfdeb49120fbce99160c913d2460eb805da2f91 |
| worker-success.log | 30581afbff22dfbbc3fd33865b4accbafa78d38258370f0417a3e57181b05fc7 |
| worker-reentry-retry_refused.log | e819a9dbcc615ef08722202a25cccd1adf439d8e4cade8c9f56b72b4a818b47d |
| scout-full.sarif.json | 0c11f662132e6f3fe67e726439aff4b8268d5b948a0680c921a541c5e8d338a7 |
| scout-1.26.sarif.json | f7928c21ead7b05de6ea774993e0a92db59c0ceef768ff0b0559d573170957df |
| scan-summary.json | dcff6b0dd624dbe040494be8afe166f186262fbc30f444b2345ef58294882d22 |
| http_probe.py | 95c9e03b4d0f2b9eedefabd9f5a432ab34f1727d2c5ad03241cd273d91550356 |
