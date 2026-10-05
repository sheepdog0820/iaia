# 背景透過job作成時の有効アカウント再確認

## 問題と対象

[先行のプレミアム再確認](BACKGROUND_PREMIUM_GATE_2026-10-06.md)はuser行ロック下で最新 `is_premium` を確認するが、認証後に `is_active=False` が確定した場合も、プレミアムが残れば新規jobを作成していた。実Token認証後の画像検証中と、実PostgreSQLのuser行ロック待機中の無効化で再現した。新規作成202、既存job期限処理への到達、日次制限429への到達を確認した。

開始点は検証記録 `52acfba22a7d00b7fb847cd035aa7c5f720c44eb`、専用ブランチ `codex/background-active-gate-20261006`。元worktreeのハンドアウト未コミット変更は対象外。

## 修正と仕様の境界

- 作成直前の既存 `transaction.atomic()` / user行 `SELECT ... FOR UPDATE` で `pk/is_active/is_premium` を同時に取得する。追加の状態確認用SELECTや課金API呼び出しは増やさない。
- 認証後にアカウント無効化が確定していれば、日本語403 / `detail` / 「アカウントが無効のため、背景透過を開始できません。」で拒否する。日次回数確認・古いjob期限処理・画像保存・job作成・dispatchより前に判定する。
- userが存在しなければ先行の日本語403、存在して有効なら先行のプレミアム再確認へ進む。初期のpremium高速判定・DRF認証・認証前から無効だったTokenの401は変更しない。無効化とpremium失効が両方確定した場合、ロック内では無効化の案内を優先する。
- 確認前に有効へ戻った場合や、待機原因となった無効化がrollbackした場合は、ほかの条件を満たせば202で作成する。staff/superuserの例外は設けない。
- 作成が確定した後の無効化で認可済みjobを独断で取り消さない。無効アカウントの新しいTokenアクセスは既存認証が401で拒否し、有効へ戻れば所有者は既存jobを再参照できる。

既存のアカウント無効化を尊重する限定修正であり、管理者の所有権・削除方針・有料契約・返金の判断は変更しない。workerの停止/推論/既存jobキャンセルも追加しない。DB/schema・Secrets/IAM・実ユーザー権限・容量・費用への操作はない。ロック順はuser→jobのまま。

## テストと途中結果

新規10件は実Token認証を使う8件と実PG競合2件。force_authenticateを設定した先行fixtureのclientは置き換え、実際のリクエストはToken headerを持つ別APIClientから送る。画像検証中の状態変更・dispatchは隔離テスト内のpatchであり、実HTTP/実ECSの成功とは区別する。

正常/拒否/競合に加え、初期無効Token401、無効化とpremium失効の優先順位、staff/superuserの拒否、古いjob/画像/時刻の保持、日次quota前の拒否、再有効化、作成後無効化時のjob保持/Token401/復帰後status202を確認する。PG2件は実Token認証のリクエストを別DB接続で実行し、主接続の未commit user行にblockされることを `pg_blocking_pids` で観測する。GREENでは `pg_stat_activity` のaccounts_customuser / FOR UPDATE / wait種別Lockも確認する。固定sleepだけを競合成立の根拠にしない。

- SQLite RED：10件中6 failure（staff/superuserの2 subtestを含む）・PG専用2 skip、終了1。認証前から無効の401、復帰後作成、作成後無効化の3件は既存挙動で成功した。
- PG RED：初回はharnessのcwdが `/app` のため旧testsが選択され、class不存在1 errorとcoverage NoDataError。cwdをread-only source rootへ合わせた再実行で、実ロック待機後の無効化確定ケースが202となる1 failure、rollbackケースは成功、終了1。アプリ修正前に再現した。
- SQLite GREEN初回：harnessの `DATABASES.TEST` 初期化不足によりKeyError/NoDataError、DB試験開始前に終了1。setdefaultとin-memory TEST DBで修正した。
- 整形前GREEN：Windows SQLite153件中137成功・PG専用16省略（62.996秒）、隔離PG153成功・省略0（64.273秒）、ともに終了0。
- 最終整形後Windows SQLite：153件中137成功・PG専用16省略、59.113秒、終了0。in-memory TEST DBを終了時に破棄した。
- 最終整形後隔離PostgreSQL：153件すべて成功・省略0、58.097秒、終了0。変更POST51文/24分岐、追加テスト149文/4分岐は100%・除外0。テストモジュール全体304文/6分岐も100%。画像ビュー全体は文277/297・分岐68/78であり、全モジュール100%とは扱わない。途中失敗・整形前結果を削除/上書きしない。

回帰範囲は背景透過premium/finalization/dispatch/uncertain/retention、通常背景透過、有料機能ライフサイクル、画像API・複数画像の9モジュール。CI production-databaseは既に `test_background_premium_gate` を実行対象としており、新規PG2件を含む。

Linux試験は固定正常イメージ `tableno:background-premium-runtime-1a738d2a`（ID `sha256:9c4e660278d6e468971424a29eea25f9c8712eff43a1a8bdd0320d78513dfff7`）へ今回sourceをread-only overlayし、coverage 7.15.4だけを外部からread-only mountしてpytraceで計測する。SDK/通常依存は変更しないが、今回commitの正常配布物検証とは主張しない。

PG18.3はnetwork none・公開portなし・256MiB・512MiB tmpfs。検証アプリはPGと同じnamespace内で通信し、rootはread-only・一時/tmp/mediaを使い、計測結果だけ外部 `/evidence` へ出力する。S3/Redis/Checkout/課金メールは無効、資格情報は合成値。Windowsの最終harnessもin-memory TEST DBと一時mediaに限定する。最初のSQLite REDでDjangoがこの検証checkoutの専用test_db.sqlite3を再作成し、終了時に破棄した。共有DB・実ユーザーDBは使わない。

## 証拠・品質確認・未確認

証拠は `D:/tmp/codex-tableno-background-active-gate-20261006/` にRED・途中失敗・GREEN・coverage JSON・harnessを保持する。最初のWindows RED出力の日本語はconsole encodingの影響を受けたため、後続はPYTHONUTF8=1を設定し、sourceのUTF-8日本語は変更していない。

PG container `61bd38b2acf3af56ead3e94b15564fdb205bec1aac409d55492b5b7802799f8e` のID・用途label・network none・OOMなしを確認し、test DBが破棄済みでbase/system DBだけ、baseのpublic table0を確認後に停止・削除した。検証アプリcontainerも終了0で自動削除済み、今回labelの残存container・公開portは0。tmpfs内の合成DBは消えており、必要ならfixtureから再構築できる。元worktreeの13項目は保持した。

| 証拠ファイル | SHA-256 |
| --- | --- |
| `red-sqlite.log` | `4cdea4e726b7bc1e4cee518b4a4ece75ac681ea52a440e2cfa32797470139274` |
| `red-postgres.log` | `cd977eec9a270180fa3d0e56a3cac8b91c202b5695d50a517c84a20f754e87b7` |
| `red-postgres-corrected.log` | `e130b2fad3dd07b74d42f4135263b30bb22a1bcd57d0f7d14863bfa3464dbd6a` |
| `green-sqlite.log` | `9bfd1d90eb438101f8ca9cff79d755004c4e383eb27c7af38e45f7dce6251cc8` |
| `green-sqlite-formatted.log` | `7c5229c3513a307cfc693a75885be2bcac8c0bba1873b3945b4ebe21bffd17a8` |
| `green-postgres-formatted.log` | `e78713a82b05468d8b9fdd8afa04d3d5d715f0dbafb4be11aa19fb44df4cf4dd` |
| `coverage-green-postgres-formatted.json` | `cb201e8471441c4a40132bbb1ad082008fac8243b422eb95484d3eee410174ab` |
| `run_isolated_tests.py` | `7b0f91a8d674c90f69ebac9d58274cb196a57c3f49464507c6ff3ec3820a6fe7` |
| `postgres-inspection.json` | `ab0a0253a700bf3ee43871a8805d75a1ca98e118a191cb7dde236cbd7cbdfd1c` |

Python3.11.1で変更2PythonファイルのBlack/isort/flake8/Banditと差分空白チェックが合格。日本語403はレスポンスJSONの完全一致で確認し、表示レイアウト/JavaScriptは変更しない。文書39件成功（0.036秒）、変更2文書の相対リンク197件・欠落0、上表の証拠9hash一致、ステージ4ファイルのUTF-8/LF・BOMなしを確認。自己レビューで追加修正が必要な指摘はない。

今回CI・通常配布物・実HTTP競合・AWS/ECS/S3・実worker・課金/外部連携/運用・性能/復旧は未確認。先行正常イメージのOS監査HIGH3を今回の修正で解消したとは扱わない。main/AWSへ反映せず、既存の固定候補反映承認へ追加しない。正式公開No-Goを維持する。復旧はこの限定修正の通常revertで、共有DB逆移行は不要。
