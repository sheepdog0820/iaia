# 背景透過の保持競合修正を含む通常配布物7106f6fb（2026-10-06）

## 結論と範囲

固定アプリ `7106f6fb6dfc57e61b19d9838031a3d1db5aa687` の通常Dockerfileから配布物を構築し、ソースoverlayなしの隔離PostgreSQL回帰83件成功、実HTTPの明示確認27件を得た。[結果取得・保持削除の競合防止](BACKGROUND_RESULT_RETENTION_2026-10-05.md)を含む通常配布物の検証である。実HTTPの初回工程はロック観測で失敗し、後述の再開で残工程を検証した。初回全成功とは扱わない。

候補CIは全6項目success、pytest2218成功/80省略/全体coverage88%、Playwright291成功/flakyなし。一方、新しい全OS監査は39指摘（HIGH3/MEDIUM1/LOW35、Python0）・終了2で未合格。実ECS/S3/AWS性能・課金実運用・外部連携等は未達で、正式公開No-Goを維持する。main/AWS/ECR/共有DB/Secrets/権限/課金/実通知/常設容量は変更していない。

## 配布物と隔離

- 固定commitのgit archiveから通常構築。tag `tableno:background-retention-7106f6fb`、image ID `sha256:86f4a3a7b76c2e657e8b5eab43242b11f4dec1362513bc1a7ae120be46e3d68a`、revision labelも上記SHA一致。
- archive側・配布物側で選定した678ソース/画面/静的資産/テスト等の集合を両方向照合し、欠落/追加/ハッシュ不一致0、Python cache0。`/entrypoint.sh`も追跡ソースと同一。先行[7b75105e](BACKGROUND_RUNTIME_7B75105E_2026-10-05.md)とPython依存111件の変更0、先頭10層同一。OS/nativeを修正したbuildではない。
- 自前PostgreSQL18.3をnetwork none・256MiB上限・tmpfsで起動し、Web/回帰/HTTP probeのみ同じnetwork namespaceを共有。公開portなし・外部通信なし。Webはread-only root・512MiB/0.25 CPU上限・一時staticfiles/tmp、合成専用mediaだけを書き込む。実DB/Secrets/ユーザー情報は使わない。
- 通常WebはAPP_ENV=aws-preのproduction設定と通常entrypointで、隔離DB migrate・collectstaticを実施し、232 copied/624 post-processed・Daphne起動。DB/cache readiness、`check --deploy`・`migrate --check`も成功。S3不使用・LocMem cacheでRedisではない。Checkout/課金メール/開発ログイン自動作成は無効。
- イメージ内の関連83テストは20.905秒・全成功/省略0。保持20件、dispatch13件、finalization15件、既存API25件、model6件、infrastructure4件を含む。SDK/native・製品ソースを差し替えず、通常配布物内のテストを実行した。unit部分のECS/推論/storage障害mockと、次の実HTTP/ファイル検証は区別する。
- `.dockerignore`で配布しないAGENTS.mdを読む文書試験はcheckoutで別検証する。先行の既知の配布文書欠落を、overlayや合格条件緩和で回避していない。

## 実HTTP・保持コマンド

HTTPでは通常ASGIサーバー・認証Token・実PostgreSQL・実filesystemを使用し、view/ORM/storageをmockしていない。透過PNGは合成4×4/RGBA・alpha0〜255、SHA256 `26f1b360b2254c02918258ea3e603372cd67368374fb977df31bc9cc3264d941`、日本語attachment名を確認した。今回実モデル/workerは再実行しておらず、先行の実U2NET証拠とは範囲が異なる。

- 初回の観測失敗前に13 HTTP確認が成功：readiness1件、pending/正常PNG/参照を残して実ファイルだけ削除/同じ参照へ実ファイル復元の各3件。各組で所有者202/200/日本語503/200、他ユーザー404、未認証401。参照・completed・updated_atが欠損時/復元後とも不変であることをDBでもassertした。
- 最終再開の14 HTTP確認が成功：readiness、cleanup前のPNG、cleanup transactionを待つ所有者GET、削除後の他ユーザー/未認証、結果なし3件、終端ジョブ削除後3件、残った正常PNG3件。全job GETでno-store/Vary Cookie・Authorizationをassertした。途中の診断工程のHTTPは27件に加算していない。
- 実cleanupのdry-runで対象結果1件・ファイル不変を確認。25時間前の完了fixtureをロックしたtransaction内で、別の実Web GETが待機することをpg_locksの未許可ロックとpg_blocking_pidsで観測し、その後cleanupコマンドを実行。結果画像1件削除・失敗0、commit後のGETは日本語503、completed行は保持。8日前の別fixtureは実コマンドでジョブ/画像を削除し、実GETで404。別の正常画像は引き続き200だった。

初回HTTP probeはpg_stat_activityを用いたロック観測が5秒以内に成立せず終了1。DB/Web/fixtureをリセットせず、同じ状態で調査した。統計がtransaction内で保持される仕様を[PostgreSQL公式資料](https://www.postgresql.org/docs/18/monitoring-stats.html#MONITORING-STATS-VIEWS)で確認し、snapshot更新も試したが、1回は実待機を観測しても「古い観測が必ずfalse」の診断assertが失敗、追加の同一配布物Webを使う診断でも観測assertが失敗した。初回失敗の単一原因は未確定であり、統計cacheが原因と断定しない。これら3失敗のsource/logを保存した。

最終probeは同じ元Web/DB/fixtureで再開し、[公式のロック情報](https://www.postgresql.org/docs/18/view-pg-locks.html)から未許可ロックと、そのpidを妨げる保持pidの実一致を要求した。5秒上限・実待機を要求する合格条件は維持し、sleep時間だけによる判定や観測なしの成功fallbackは追加していない。画像を取得して経路の稼働を確認してから検証した。取得が先行する方向は配布物内のPGテストが実readのbarrierと別cleanupの行ロック待機で確認し、実HTTPではcleanupが先行する方向を確認した。両者を全S3経路の保証へ拡張しない。

## CI・OSゲート

[CI 37326743931](https://github.com/sheepdog0820/iaia/actions/runs/37326743931)はcompleted/success、head SHA/専用branch一致、全6ジョブsuccessを照合した。ログもpytest2218成功/80省略/159 warning/887.21秒/全体coverage88%、Playwright291成功/12.2分/flakyなし。省略を実施済みに読み替えない。Production Databaseで追加の保持integration testも実行するworkflowである。

Docker Scout1.26.0で新しい配布物全体を新規監査し、292 package中16 package・39指摘、HIGH3/MEDIUM1/LOW35、Python0、終了2。先行7b75105eとCVE ID/重大度差分0。HIGHはCVE-2026-102010/95619/85091、scannerではnot fixed。指摘の抑制・リスク受容・native閉包の非該当証明・公開ゲート解除はしていない。今回はCドライブ空き約2.9GBを確認し、プロセス限定のTEMP/TMP/Scout cacheを空き約1.2TBのDの新規専用領域へ配置して監査を完了した。過去にポリシー拒否されたcacheの削除は再試行していない。

## 終了処理・残条件・承認境界

Web `1808a56ac1cb62ad58fe082ae93e940e97261e75ca085ee4754a5e88c26aa204`、診断用Web `eda9200442907cb4e1f453a93427e2366f81b7d37bcb1d4beaace28d56f2de56`、PG `f70b66529dfee484cc411b61d5fdfdc73d60b0b19827509e0f9fd751a7dbf39a` の保存ID/network modeを再照合して停止・自動削除。回帰/各HTTP probeも終了時自動削除、今回container残数0。使い捨てtmpfs DBは破棄した。残った合成媒体2件を最終probeで削除し、mediaファイル0を確認した。archive/image/ログ/probe/Scanner cache・tempはGit外に保持し、資格情報をコミットしない。

実S3のアクセス拒否/遅延/削除整合性、DB commit失敗後のstorage整合性、孤立ファイル回収、曖昧なpending dispatch、AWSの性能/長時間/worker運用、実Stripe/RAK/Endive/共有DB/メール、管理方針、外部連携、RDS/S3復旧、事業者/税務等は未達。[正式公開条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)はNo-Goを維持する。今回の限定配布物・実HTTPの検証を全API/全課金/公開可能へ拡張しない。

完了済みアイコン8567f49fの承認と固定6b6c570cの反映案をこの候補へ転用しない。main/AWSは今回再照合・変更していない。元checkoutのハンドアウト関連変更を保持する。未反映なので実環境の切戻しは不要。今回は証拠文書のみで配布アプリの追加変更はない。

## 証拠

証拠は `D:/tmp/codex-tableno-retention-7106f6fb-20261005/` に保持する。初回失敗probe・2診断probe・最終probeを別名で残し、成功ログで失敗ログを上書きしていない。

文書追加後の39テスト成功（0.043秒）、下記8hash一致、変更文書2件の相対リンク194件欠落0、staged2テキストのUTF-8/LF/BOM/置換文字と空白差分の検査も成功。記録と証拠の対応、失敗/省略/未確認の区別を自己レビューし、当該文書の追加要修正指摘なし。新しいUI文言や製品ソース変更はなく、Python formatterの新しい製品対象はない。

| ファイル | SHA256 |
|---|---|
| inspection.json | 7e067dc8dcf8f742417861ddae288085545f9bdedca1ac015a9fba293291768a |
| regression-runtime.log | bb4bc1e88d445031131007079158aa6ffc7a48f70c1da7ab6ddc4468c15838e0 |
| http-runtime.log | fe6b45cd8aa740b11501ecfa4b7803dc766d5f0940e05cad2562bb89c6c6f44c |
| http-runtime-resume.log | c3131a39074894347dfb3e2ab5bd223841c8e34ea52f7f3c35cb4a05927ba5a1 |
| http-runtime-fresh.log | 66367a4e6767f2216e592f3edc95227c73e90e2511300356b4486a709861f29b |
| http-runtime-locks.log | e2c71736c3ddf6d440e9f8f14eb49320f7b28278342a0b176871b4238680d4ef |
| scout-full.sarif.json | f7928c21ead7b05de6ea774993e0a92db59c0ceef768ff0b0559d573170957df |
| web-final.log | 852445277eec72b57e9ba6802eb126b075dcf49516619f3475373c1423d5af1f |
