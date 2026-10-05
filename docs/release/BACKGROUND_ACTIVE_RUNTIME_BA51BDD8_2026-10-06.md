# ba51bdd8有効アカウント確認の通常配布物・実HTTP検証

## 固定対象・通常配布物

[有効アカウント再確認修正](BACKGROUND_ACTIVE_GATE_2026-10-06.md)の候補 `ba51bdd8b7b74e39ae9e8104ab064956dd55262c` をgit archiveから構築した。証跡専用ブランチは `codex/background-active-runtime-20261006`。アプリ・依存lock・Dockerfile/entrypointは変更しない。元checkoutのハンドアウト13差分を混入させない。

| 項目 | 結果 |
| --- | --- |
| 通常イメージ | tableno:background-active-runtime-ba51bdd8 |
| image ID | sha256:1e5d3114e2c23473fc1bcce06273aeca65d71811a89fea878b07294e98f49e11 |
| revision label | 上記full commit SHAと一致 |
| 選定ファイル | 680個、集合差異0・SHA-256差異0 |
| 依存 | 111パッケージ、先行通常1a738d2aと名前/版一致 |
| 依存層 | 先行通常1a738d2aの最初の10層と一致 |
| Python生成キャッシュ/entrypoint | 0・実entrypoint bytes一致 |
| 正しい回帰対象 | 153件成功・省略0、49.306秒、終了0 |

選定範囲はaccounts/api/schedules/scenarios/support/tableno・static/templates・tests/unit/integrationのPython/HTML/CSS/JavaScript/画像/font/JSONとlock/entrypoint/manage.py。全イメージ全ファイルの一致とは扱わない。通常 `/app` のアプリsource・SDK・coverageは差替えず、読み取り専用の外部harness/probeだけ追加した。mediaは専用合成保存先または試験中だけ/tmpへ設定する。

回帰対象は背景透過premium/finalization/dispatch/uncertain/retention、通常背景透過、有料機能ライフサイクル、画像API/複数画像の9モジュール。今回の10テストと実PG競合2件を含む。AGENTS.md等を配布しない既存Dockerignoreに従い、通常imageの153件へ文書テストは含めない。

初回の回帰指定には不存在のモジュール名が3つあり、120件/3 import error・46.064秒・終了1だった。正しい対象は `test_background_dispatch_uncertain` / `test_background_result_retention_integrity` / `tests.integration.test_paid_feature_lifecycle`。アプリ修正や条件緩和ではなく、指定を訂正して上記153件へ再実行した。初回ログを保持し、初回全成功とは報告しない。

配布物照合の初回summaryもPowerShellのProperties.Countの列挙によりFiles値を1の配列として出した。集合/ハッシュ照合は元から差異0だったが、件数表現を明示的な配列Countへ訂正し、680件と再確認した。初回summaryは別名で保持する。

## 隔離構成・実HTTP25確認

PG18.3はnetwork none・公開portなし・256MiB・512MiB tmpfs。Web・合成ECS・probeはPGのnetwork namespace内loopbackだけで通信する。Webは未改変entrypoint・APP_ENV=aws-pre・DEBUG=False・read-only root・0.25 CPU/512MiBで起動し、隔離DBのmigrateと静的収集 `232 copied/624 post-processed`、ASGI listenを確認した。

S3/Redis/Stripe購入/課金メールは無効。資格情報・user/Token・画像は合成値で、共有AWS・実IAM・実ユーザー・実課金・メール配送には接続しない。実SDKのECS endpointだけloopback fixtureへ向け、RunTask target・署名header形式・cluster/taskDefinition/UUID clientToken/command/subnet/security group/public IP DISABLEDを検査する。実IAM署名検証・実ECS task/worker起動・推論成功とは区別する。

未改変ASGI/DRFへの実HTTPと本物のToken認証で25確認が成功、probe終了0。APIClient/force_authenticate/アプリ関数patchは使わない。

- Readiness200・DB/cache ok、匿名POST401、非premiumの通常user/staff/superuserは日本語403・job/画像/dispatch 0。
- premium失効・user削除・アカウント無効化を各別接続の未commit user行lock中に開始。Webの `SELECT ... FOR UPDATE` がこの接続へblockされ、queryにis_active/is_premium/user IDが含まれることをpg_blocking_pids/pg_stat_activityで観測した。保持中のjob/画像/dispatchは0。commit後、失効/削除は先行日本語403、無効化は「アカウントが無効のため、背景透過を開始できません。」のdetail完全一致/JSON403で、同じ0を維持した。
- 認証前から無効のpremium Tokenと、無効のpremium staff/superuser Tokenは既存認証により401。管理者例外を追加しない。
- 復帰後の作成202/pending/所有者status URL/元画像byte/task ARN/clientToken一致、重複409・dispatch不増を確認。作成後にpremiumだけ失効しても既存jobの所有者statusは202、他人404・匿名401、no-storeとVary Cookie/Authorizationを維持した。
- 既存jobを合成的に期限超過させ、通常cleanupでtimeout1件・failed・元画像削除、status503。その後は別UUIDで新規202・合計2 SDK要求を確認した。
- この作成済みjobの所有者を無効化すると、新しいstatus/POSTは401。jobの状態/元画像参照/updated_at/task ARNと実保存元画像は保持され、SDK要求も2のまま。再有効化後は所有者status202・重複409で、独断キャンセルや再dispatchはしない。
- 未commitの無効化を持つ別ownerで実Web待機を再度観測し、無効化をrollback。202/pending・第3 job/SDK要求・UUID/task ARN一致と所有者status202を確認した。待機中に既存2job/2要求が増えないことも検査した。

ロック観測は主接続PID190、Webの失効PID192/削除193/無効化194/無効化rollback212。固定sleepだけを競合成立の証拠にしない。実HTTPは初回成功で、回帰の誤指定による先行失敗とは区別する。

WebのTraceback・実ERROR/CRITICAL・500は0。初回の大文字小文字を区別しないログ検索は、正常migrateの `error_message` を含む名前2行に誤一致した。実エラーレベルを区別して再検査し、アプリ障害と断定しない。期限後の503は想定確認で、全HTTPが200だったとは主張しない。

## 全OS監査

Docker Scout 1.26.0で上記の新しい固定イメージを全スキャンし、292パッケージをindex、16脆弱パッケージ・39指摘（HIGH3/MEDIUM1/LOW35、Python0）、終了2だった。先行通常1a738d2aとのCVE/package/severity差異0・SARIF hashも同一。依存層同一という推測だけでなく、今回imageへの監査が完了した結果である。

HIGHはCVE-2026-102010/CVE-2026-95619/CVE-2026-85091。未修正・未受容・未抑制で公開ゲートは未合格。新規D:配下のcache/tempだけを使い、古いcacheを削除・移動していない。[先行native再照合](RUNTIME_NATIVE_REVALIDATION_2026-10-06.md)のbytes/公開署名一致も、PBDS適用条件や全nativeビルド閉包の解消へ拡張しない。

## 後片付け・CI・影響

probeが自身のprefix付き合成ユーザー集合を完全一致で確認し、元画像・3job・user/Tokenを削除した。probeとPGの独立確認でuser/job/Token/画像0・test DB破棄済み。ID/用途label/OOMなし/公開portなしを照合した下記containerを停止・削除し、今回labelの残存container0を確認した。tmpfs内のDBは消えており、fixtureから再構築可能。archive・媒体フォルダー・harness/ログ・新規Scout cache/tempは保持し、旧キャッシュを削除・移動・別経路で掃除しない。

- Web: 21981418cfc094d0b6987f9faa6887c7906ef10c5760eacc97e47795dce197b0
- 合成ECS: 2b6b3a4d101e85681773df4330973d1a45604ff8f7243924871ec3285098d5b3
- PG: 3a68b9163a94bd7d3b6639f839363867b64cf269b444713ab0253949f2d88da9

候補ba51bdd8の[CI37386076213](https://github.com/sheepdog0820/iaia/actions/runs/37386076213)はfull SHA/branchを照合し、run completed/success・全6ジョブsuccessを確認した。Unit job112019557934は2248成功/85省略/159警告・705.70秒、全体coverage表示88%（41657文/未実行5180）。Playwright job112019557918は291成功・12.2分。全体coverage100%や全省略解消とは扱わず、今回文書コミットのCIとも区別する。

実AWS/ECS/S3/worker推論・実Stripe/外部連携/共有DB運用・正式性能/長時間負荷・RPO/RTO復旧・ブラウザー表示・本番公開は今回の対象外。main/AWS・共有DB/schema/実データ・Secrets/IAM・課金/継続費用/常設容量・通知は変更していない。既存の固定6b6c570c反映案やfavicon承認へ今回修正/証跡を追加せず、正式公開No-Goを維持する。文書の復旧は通常revertで、共有DBの逆移行や再デプロイは不要。

文書39テスト成功（0.035秒）、変更2文書の相対リンク200件/欠落0、下表の13hash一致を確認した。自己レビューで修正を要する指摘なし。ステージ対象は文書2ファイルのみで、差分空白/UTF-8/LF/BOMなしを確認した。アプリ/UI表示変更はなく、既存日本語拒否メッセージは実HTTP JSON完全一致で確認した。

## 保持証跡

保存先は `D:/tmp/codex-tableno-active-runtime-ba51bdd8-20261006/`。

| 証跡ファイル | SHA-256 |
| --- | --- |
| distribution-check.json | 20475a4c1e1c7a75ae794115cdcd94dc83ae4ce0d29b5fabfc9b5a7e40dd28c3 |
| inspection.json | d966f7bde1809d805bd1f66f7daa9bd1ea4212aeca3fd448d4084090b781a941 |
| regression-runtime.log | cd7eff654478d330c513d447c522ded917f77f73f7a0f0bf9d49c59869d68525 |
| regression-runtime-final.log | a7a16b60d86f9f71c6dcc8b5abba081841b869e17610378d3a8bacf74f3ffdf7 |
| http-gate.log | 697c568e9440b7bf40fc97da2a7b50896f8b8e472349c770d371bfcdca9707ca |
| runtime-containers-full.json | e55c38fc07cc9775b54be6604f52b3c7b98668a059d781c05d4a0d69005d5a0f |
| fake-ecs-state.json | fd8b7af3304b3c7ef69c6cb0485121deed0d7402870abedeb449b4bbf6fe99dc |
| web-final.log | 76215f0e7c0502f790ea47935c17639e3b051db994895e5726e07b24850d7b14 |
| postgres-cleanup.json | eb7d1f67716aaa0b56c7ec16fa84f8a791ccaaffd86e983c84469a7bc74290b4 |
| http_gate_probe.py | fd8bd851a8d9c13ddb15184bb226848998e8b27e03b4192c1ac12e749df98dd8 |
| scout-full.sarif.json | f7928c21ead7b05de6ea774993e0a92db59c0ceef768ff0b0559d573170957df |
| scout-full.log | 5c3ecf313d6367d7e39e594a0ae7aa872e7a398022b69b61cd4bd327a354527b |
| scan-summary.json | 4f4b87ceb2eaf05c119a166d9f0529cf704a9ee96d6236109fe1327c50a89b26 |
