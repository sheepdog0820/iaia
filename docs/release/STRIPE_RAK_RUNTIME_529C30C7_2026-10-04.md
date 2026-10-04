# Stripe制限付きキー候補の通常配布物検証（2026-10-04）

## 固定対象と承認境界

対象は `529c30c7770b775f59c9b939f042809058fcd033`。[RAK対応](STRIPE_RESTRICTED_KEYS_2026-10-04.md)の通常Docker配布物を検証した。記録は専用ブランチ `codex/stripe-rak-runtime-evidence-20261004` へ保存し、今回アプリコードは変更しない。元checkoutのハンドアウト未コミット変更は保持する。

mainの読み取り照合は `8567f49f8d411bad7f732afaeebad85357eeca09`。AWSは今回再照合・変更していない。main/AWS/ECR/ECS/共有DB/CloudFront、実Stripeアカウント/キー/権限/Price/Webhook、Secrets/IAM、実メール・課金・常設容量/継続費用は変更していない。faviconの完了済み承認や固定6b6c570cの反映案へ今回候補を追加しない。正式公開 **No-Go** を維持する。

## 配布物の同一性

固定SHAの `git archive` を通常Dockerfileへ渡し、タグ `tableno:stripe-runtime-529c30c7` を構築。image IDは `sha256:0013941872077af98a6a6be4d2e2dfdb544d57db137b51dfbb89ca8ff0a9da4c`、revision labelは対象SHA、実行ユーザーtableno、entrypoint `/entrypoint.sh`。レジストリpush・署名検証はしていない。

accounts/api/schedules/scenarios/support/tableno/static/templates、tests/unit/integrationの選定拡張子とruntime lock/entrypoint/manage.pyについて、archiveで選定した673ファイルとimage内の673ファイルの欠落0・SHA-256不一致0・Python caches0を確認。対象拡張子はpy/html/css/js/png/ico/svg/woff/woff2/ttf/json。`/entrypoint.sh` と配布元もbytes一致。全filesystem/nativeビルド閉包の証明にはしない。

Pythonパッケージ111、Stripe16.0.0/Django5.2.17、API2026-09-30.endive。先行2b70f1d5 imageと先頭10層が同じで、OS/apt/Python依存層はキャッシュ使用。今回ビルドを新しいOS修正取得とは扱わない。

## 配布物内テストと通常起動

| 検証 | 結果と範囲 |
| --- | --- |
| 隔離PostgreSQL 18.3回帰 | **561件成功、省略0、102.719秒、終了0**。保存した34モジュールは `regression-targets.json` |
| production/staging設定 | **33件成功、29.407秒、終了0**。別のnetwork noneコンテナ内の設定import subprocess |
| 実CLIのキー境界 | 7ケース成功。stagingのsk/rk testとproductionのsk/rk liveを許可、staging rk live/publicとproduction rk testは終了1、完全な合成キー値の非表示も確認 |
| 通常entrypoint | 専用空DBへの移行、静的232件/624 post-process、Daphne起動成功 |
| runtime fixture guard | DB名・ユーザー0・stagingのRAK test・SDK/API版・購入開始/メール/S3無効を初期化前にassert |
| `check --deploy` / `migrate --check` | 問題0/終了0、未適用移行なし |
| 静的manifest | 前2b70f1d5から232 mappingの追加/削除/変更0、元bytesのSHA-256一致 |

回帰は課金/認証/退会保護/競合、Stripe再試行・順序・返金/Dispute・メール、コード/手動付与/再同期・管理/所有者照合、6版API/CCFOLIA版保持、ICS/calendar APIを含む。今回のRAK単体16件、Endive更新20件、先行transport14件も含む。SDK試験はメモリーtransportと合成HMACを使用し、その他の既存mockもある。実RAKの認証・権限・アカウント一致や実決済の成功ではない。

アプリ/テスト/SDKをoverlayせず、通常runtime lockの配布物を使用。外部工具としてテスト設定とNode v20.20.2だけread-only mountした。Node binaryのSHA-256は `6295488653f0d93b0a157841746fef7e72cc4328cfb60c4bbe0ca2668a836ffd` と再照合。DockerがMarkdownを除外するため文書試験は561件に含めない。先行ローカル598件や設定33件と直接合算しない。回帰の意図した400/401/403/404/500/503・tracebackを、全ログ異常0や性能合格と誤解しない。

## 実HTTP27件

PG imageは `sha256:fbaa243599038521bbda8f6fa286d2a8fc1236509606f22de81d0739b0610ba7`、network none・公開portなし・512 MiB・DB tmpfs。Redis7.4.11 `sha256:5509c0097c6064aa8a3b1df58f1d950e67090fffa6678ae8f3f1dc2385f12deb` とWebはPGのnetwork namespaceを共有。Web0.25 vCPU/512 MiB、Redis128 MiB、S3無効、SMTPは到達不能loopback。無効な合成RAK testを使用し、外部通信不能。

通常Webの19 HTTPはすべて期待結果一致。readinessのHTTP200/DB・cache正常、ログインページ、favicon等4 URLの元bytes、manifest内CCFOLIA helper bytes、ICS停止GET/HEAD拒否/再有効化/参加資格喪失/旧token失効/文字・UTC、無料通常ユーザーのCCFOLIA6版/7版API往復を確認した。

通常Web停止後、同一imageの別Webを隔離fixtureの購入開始のみtrue、移行/静的収集falseで起動。未認証Checkout/Portal各401、保存intentのcustomer/metadata/client_reference/subscription_data.metadata不一致各400、実PGロック待ち中の所有者変更後のCheckout/Portal各400を確認。日本語拒否・レコード/intent/監査/権限の不変と実ロック待ち2件を確認し、追加8 HTTP・終了0。Webログの401×2/400×6と一致し、両Web保存ログのTraceback/HTTP5xxは0。

HTTP probeにStripe mockはないが、購入成功試験ではない。fixtureのDRF Token、loopback HTTPとproxy-HTTPSヘッダーを使用し、実ログイン/OAuth/TLS/ALB/ブラウザー/外部受信アプリの証明にはしない。共有AWSの購入開始設定は変更していない。先行管理HTTPは再実行せず加算しない。

## 検証手段の訂正・片付け

- PG起動の初回はローカルimage IDをregistry digestとして指定して失敗。既存ローカルIDを照合してID指定に訂正し起動した。別imageへの差し替えではない。Redisのtag照合もtag未登録だったため、固定image IDと実バイナリ7.4.11を照合した。
- fixture guardの初回は補助スクリプトのimportパス不足で失敗し、`PYTHONPATH=/app` を付けて成功。`fixture-guard-initial.log` を保持し、アプリコードやassertを変更していない。
- tmpfs内静的資産の`docker cp`取得は失敗し、初回比較はmanifest不存在のため無効。生存中コンテナから読み取りPythonでmanifest JSONと元bytesのハッシュをexportして比較を完了した。保存JSONは正規化exportであり、元bytesそのものとして扱わない。
- 回帰・設定33件・キーCLI7ケース・HTTP27件自体の失敗/再実行はない。試験手段の失敗を隠して全工程初回成功とはしない。

全検証後、4専用コンテナの完全ID・image・network・公開portなし・永続書込みmountなし・PG tmpfsを照合して停止/削除。再作成可能な合成DB/一時静的データのみ破棄し、他のコンテナ・実データを変更していない。image/archive/工具/ログ/manifest exportは保存した。

## 監査・CIと残作業

Scout1.26.0・専用cache・NO_CACHE=true・無抑制の全監査は292 indexed/16 vulnerable packages/39指摘（**HIGH3/MEDIUM2/LOW34、Python0**）、終了2、SARIF生成完了。先行2b70f1d5からCVE ID追加/削除0・重大度変化0。HIGHはGCC14のCVE-2026-102010/CVE-2026-95619とzlibのCVE-2026-85091、fixed versionはreport上not fixed。指摘抑制・ベース除外・リスク受容・OSゲート合格はしていない。

候補[CI run37207744357](https://github.com/sheepdog0820/iaia/actions/runs/37207744357)は対象SHA/branch一致。先行照合では4項目success/2項目実行中だったが、最終は5項目success/Unit / Integration failure・全体failure。job111452382775のpytestは23 failed/2138 passed/69 skipped、終了1（896.06秒）。失敗23件はすべてproduction設定試験。親のENVIRONMENTを継承するsubprocess fixtureへCIのdevelopment値を渡すローカルpytestでも、同じ23 failed/10 passedを再現した（23.78秒）。単独設定33件の成功をCI失敗の解消や全体合格へ拡張しない。fixture修正と新しいCIは別の修正単位で対応し、今回記録のCIも別途確認する。

通常配布物のRAK形式対応/設定境界と回帰は上記範囲で確認した。実RAKの最小権限・認証・対象account、Sandbox Endive API/Checkout/Portal/署名付きイベント、共有Webhook/API版/Secrets切替、共有DB0065〜0067、worker/SMTP/監視、管理削除/所有者方針、OS/native閉包、外部連携・AWS性能/整合復旧・事業者運用は未完了。実キーはAWS Secrets Manager等へ保管し、通常アプリ・検査・商品作成のRAKを分ける。実権限変更は別途承認が必要。Stripe Tax/automatic_tax・税務登録は変更しない。[正式公開No-Go](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を維持する。

ローカル文書テスト39件成功、ステージ対象2ファイルのUTF-8/LF・BOM/文字化け・差分検査成功、相対リンク欠落0、証跡16件のハッシュ一致を確認。文書だけの変更で新しいUI表示やPython整形はない。記録レビューで追加修正を要する問題は残っていない。

記録のrevertは稼働版に影響しない。将来アプリを戻す場合はRAK拒否とstagingの従来の緩いキー判定が戻る影響、Endive未解決intent/API版の整合性を評価する。購入開始を停止して実状態を照合し、無承認のキー変更/権限拡大やDB削除で回避しない。実環境の復旧対象・操作は別途承認する。

## 保存証跡

保存先 `C:/tmp/iaia-stripe-runtime-529c30c7/`。合成env/archive/工具/大量生成物をGitへ含めない。

| 証跡 | SHA-256 |
| --- | --- |
| source-manifest.json | a8699b8482bff244d957859e5f5ab6d4e73257f9ab1741be96198ab87a9c7b80 |
| inspection.json | 3e1c82c242c53b660f61b371f7391d47fde4bdc29c141b0502534b271f7fa72c |
| image-inspection.json | 98b473ef4a2621aae2a35f6bd55cc8c12592619da9f661edcd09f677365cd863 |
| regression-targets.json | 7b05d494a9094b484e4a78020c35105bc8a428cab7fa55aa7d35a71b262ca339 |
| regression.log | fe376875f830a1274c04d17e1b34cf1d4ddfa92c8839c2286f8dfb72822b510f |
| production-settings.log | 04acd270cc600f7b0c2bef7bf5684899e92ee918c29a645de29bc29bbbeeeee0 |
| fixture-guard.log | 0d419f42f4769ab8ea8c01e0a09681427b815030a0bab38dfb106fde347f6195 |
| web-startup.log | d740182a7d442c0d5f59f90ed0ed3d685729cfe85be2c29dae995540d33487da |
| base-http.log | ab1c9a9ec1236aa0c2c6499dadaf21c28caffbd37b596c9aaf4ef83cefdf7b3e |
| owner-http.log | bad9db744eb8971479054a87cd49d7ae500c577d573972e1850b470efcab0602 |
| owner-web.log | 29b1e3e98e511fa859e71463e1faf42745a9257fc84e548983fc9c02e371135d |
| static-manifest-export.json | 3effe15f54dba813a5fe2e9814f721ad67caec72b2508df6fa4d968b76f9d73b |
| runtime-key-modes.json | c7b3acd209626c96a1d4171d0e31cb89d19c5a2ff7f99ff74a0dc6daf5b85ba2 |
| runtime-full.sarif.json | 1963b7babb9ba6979200a32b0baee8dd57e19ee9e1642c8778e0fbed440e2f16 |
| scan-summary.json | 50338acbf54d26c4e00a7272383423290fdc56566a1c2c47f61816c050d3a63e |
| cleanup-targets.json | bc09548466f49b581d08d36e09e517403558d5f8633a53985fefddc6e4184a7e |
