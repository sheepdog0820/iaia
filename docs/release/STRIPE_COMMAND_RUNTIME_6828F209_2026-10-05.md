# Stripeコマンド保護候補の通常配布物検証（2026-10-05）

## 対象と承認境界

対象は `6828f2095332c02c8fe0a965b5978ba736515f56`。[コマンド例外・SDKログ保護](STRIPE_COMMAND_ERROR_REDACTION_2026-10-04.md)と[本番設定fixtureの環境独立化](PRODUCTION_PROBE_ISOLATION_2026-10-04.md)を含む通常配布物を検証した。記録ブランチは `codex/stripe-command-runtime-evidence-20261005`。アプリやテストコードを追加変更せず、元checkoutのハンドアウト差分を保持した。

mainは先行読み取り照合で8567f49f。今回AWSは再照合・変更していない。mainマージ/ECR push/ECS/共有DB/CloudFront、実Stripeのキー/権限/Price/Webhook/API版/課金、Secrets/IAM、実メール、常設容量/継続費用は変更しない。既存favicon承認・固定6b6c570cの承認案へ追加しない。正式公開 **No-Go** を維持する。

## 通常イメージの同一性

固定SHAのgit archiveを通常Dockerfileで構築。タグ `tableno:stripe-runtime-6828f209`、image ID `sha256:eff050ac186039d19a0ecdd33e583d88f1c29b3c044a46327af37d13d67cc5e7`。revision labelは対象SHA、ユーザーtableno、entrypoint `/entrypoint.sh`。レジストリpush・署名検証は行っていない。

accounts/api/schedules/scenarios/support/tableno/static/templates、tests/unit/integrationの選定py/html/css/js/png/ico/svg/woff/woff2/ttf/jsonと、runtime lock/entrypoint/manage.pyの **675ファイル、欠落0・SHA-256不一致0・Python caches0**。imageの `/entrypoint.sh` も配布元とbytes一致。全filesystem/nativeビルド閉包の証明にはしない。

Pythonパッケージ111、Stripe16.0.0、API2026-09-30.endive。先行[529c30c7通常配布物](STRIPE_RAK_RUNTIME_529C30C7_2026-10-04.md)とPythonパッケージ名/版に差0、Docker先頭10層同一。依存層はキャッシュ使用で、新しいOS修正を取得したビルドではない。今回の全OS監査は別途実行した。

## 配布物内試験と通常起動

| 検証 | 結果・範囲 |
| --- | --- |
| 隔離PostgreSQL 18.3回帰 | **609件成功、省略0、116.355秒、終了0**。34既存モジュールに新規コマンド試験12件と本番設定試験36件を追加した36モジュール。後者36件は609件に含まれ、別途加算しない |
| 外部工具 | 読み取り専用の専用PG設定とNode20.20.2のみmount。アプリ・テスト・SDKのoverlayなし。Node SHA-256は6295488653f0d93b0a157841746fef7e72cc4328cfb60c4bbe0ca2668a836ffdと一致 |
| 本番設定fixture | 親ENVIRONMENT=developmentを明示した配布物内試験で成功。アプリ本体の本番モード判定は変更していない |
| 通常entrypoint | 新しい合成DBへ移行、静的232件/624 post-process、Daphne起動成功 |
| 初期fixture guard | DB名billing_runtime_fixture・ユーザー0・staging/test RAK・SDK/API・購入開始/課金メール/S3無効をassertし成功 |
| Django check --deploy / migrate --check | 問題0/終了0、未適用移行なし |
| 静的manifest | 232 mapping。先行529c30c7とraw manifest bytesのSHA-256も一致し、変更0 |

回帰は認証/退会/課金契約ガード、Checkout/Portal再試行・所有者・実行競合、Webhook順序/返金/Dispute、課金メール、コード/手動権限/再同期/管理のロックと監査、実SDKメモリーtransport、ICS/Calendar、6版API/CCFOLIA版保持を含む。コマンドSDKログ試験も通常lockのSDKで成功。mock・合成transport/HMACを使う試験を含み、実RAKの権限や実決済・メール成功ではない。意図したHTTP失敗・例外を含む回帰ログを、全ログ異常0とは扱わない。

## 実HTTP27件

PGは固定image `sha256:fbaa243599038521bbda8f6fa286d2a8fc1236509606f22de81d0739b0610ba7`、network none・公開portなし・512 MiB・データtmpfs。Redis7.4.11の固定image `sha256:5509c0097c6064aa8a3b1df58f1d950e67090fffa6678ae8f3f1dc2385f12deb` とWebはPGのnetwork namespaceを共有。Web0.25 vCPU/512 MiB、Redis128 MiB。到達不能SMTP loopback、S3無効、利用不能な合成RAK test。外部通信不能の隔離環境であり、共有AWSに接続しない。

通常Webの19 HTTPは期待結果一致。DB/cache readiness、ログイン、favicon等4 URLの元bytes、manifest内CCFOLIA helper bytes、ICS停止GET/HEAD拒否・再有効化・参加資格喪失・旧token失効・エスケープ/UTC、日本語長文、無料通常ユーザーの6版/7版JSON往復と能力値/幸運保持を確認した。

そのWebを停止して、同一imageの別Webを購入開始のみtrue・移行/静的収集falseで起動。未認証Checkout/Portal各401、保存intentのcustomer/metadata/reference/subscription metadata不一致各400、実PG行ロック待ち中の所有者変更後のCheckout/Portal各400、計8 HTTP成功・実ロック待ち2件。日本語拒否とレコード/intent/監査/権限の不変を確認。両Web保存ログのTraceback/HTTP5xxは0。

HTTP工具は[先行配布物](STRIPE_RAK_RUNTIME_529C30C7_2026-10-04.md)と同じguard・19件probe・8件probeをそのまま再利用。後者もStripe mockはないが、購入成功の検証ではない。DRF Token、loopback HTTP、proxy-HTTPSヘッダーによる確認であり、実TLS/ALB/ブラウザー/OAuth/CCFOLIA本体/ICS受信アプリや性能ゲートは未検証。購入開始trueはこの隔離fixtureだけで、実設定は変更しない。

## 試験手段の訂正と片付け

guardをdocker cpで/tmpへ届けた初回は、コンテナからファイルが見えず終了2。工具配置の失敗として保持し、同一工具をUTF-8のstdinから実行して成功した。アプリ・guard assert・HTTP期待値を緩めていない。初回のエラー出力をfixture-guard-initial.logへ保存したが、これはtool出力から保存した訂正記録で、生の全工程ログではない。回帰609件・HTTP27件自体の失敗/再実行はない。

全試験後、専用4コンテナの完全ID・image・network・公開portなし・mountはtmpfsのみ・PGデータtmpfsを照合して停止/削除。再作成可能な合成DB/キャッシュ/静的データだけを破棄した。--rmの回帰コンテナも終了し、最後のdocker ps -aは空。実データ・他の作業を削除しない。image/archive/工具/生成ログ/manifest/監査は保存した。

## OS監査・CI・未完了条件

Docker Scout **1.26.0**、専用cache・NO_CACHE=true・無抑制/全パッケージの新しい監査は292 indexed、16 vulnerable packages、**39指摘（HIGH3/MEDIUM1/LOW35、Python0）・終了2**。SARIF生成完了。先行529c30c7とCVE ID追加/削除0。dashのCVE-2026-102473だけMEDIUM→LOWとなったが、同じパッケージ版・not fixedで、修正解消ではない。HIGHはCVE-2026-102010/CVE-2026-95619/CVE-2026-85091でreport上not fixed。指摘を抑制・リスク受容せず、OSゲートは未合格。

対象[6828f209のCI全6項目success](https://github.com/sheepdog0820/iaia/actions/runs/37211219662)は[Firefox調査](FIREFOX_SIGNUP_DIAGNOSTICS_2026-10-05.md)でSHA一致と最終結果を照合済み。この記録を含む後続commitのCIは別途確認する。先行Firefox timeoutの原因は未確定で、後続成功を因果証明にしない。

最新コマンド修正を含む通常配布物未検証は上記範囲で解消した。実RAKの最小権限/認証/account一致・Sandbox Endive API/Checkout/Portal/署名イベント、共有DB0065〜0067/worker/SMTP/監視、管理削除/所有者方針、OS/native閉包、外部連携、AWS性能/整合復旧、事業者運用/税務等は未完了。共有API版/Secrets/Stripe Taxを変更しない。[公開No-Go](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を維持する。

記録のrevertは稼働版に影響しない。将来コマンド保護を戻す場合はAPI例外/SDKログの詳細露出が再導入されるため、保護を保持して復旧対象を選ぶ。実環境でのキー/権限変更、DB削除、反映は別途承認範囲を確認する。

## 保存証跡

保存先 `C:/tmp/iaia-stripe-runtime-6828f209/`。大量生成物・合成env・archiveをGitへ含めない。

| 証跡 | SHA-256 |
| --- | --- |
| source-manifest.json | 2eb9926d2e11a17cb7ba2f3a08572a5306446bfd44ad12fe151eb9cbb8988978 |
| inspection.json | 1bf9b69a37307cc41e0c0999a9d3a36eddad84f26df71baef55125c87d347c48 |
| image-inspection.json | 673573397fafa3ab94c54481b08ae4a976a98b9e07ef223d5c92e6d84dff65f7 |
| regression-targets.json | 6ea83b2e94ad4414770cded8f2a57cbe576165eaa6c1f8d888c5739be13bbf94 |
| regression.log | db81e81eb2e7e283f309b95beee1dc6f756a2e5afa56d38d473b777382f3e71a |
| fixture-guard.log | 0d419f42f4769ab8ea8c01e0a09681427b815030a0bab38dfb106fde347f6195 |
| fixture-guard-initial.log | 5adb8ca88dad2b7687db047b94ae0516d23d71c58f8e232b626b4781b73e9499 |
| web-startup.log | 6d4ab9011e0758d3328fc7791c5d024fdbfac40d9915b445fd1a62a84441c2f5 |
| base-http.log | ab1c9a9ec1236aa0c2c6499dadaf21c28caffbd37b596c9aaf4ef83cefdf7b3e |
| owner-http.log | bad9db744eb8971479054a87cd49d7ae500c577d573972e1850b470efcab0602 |
| owner-web.log | fe6bd466a621d4ef604bc7be4b06d63934d2bb87b5b57435ecc92566e380d59b |
| static-manifest-export.json | 3effe15f54dba813a5fe2e9814f721ad67caec72b2508df6fa4d968b76f9d73b |
| runtime-full.sarif.json | f7928c21ead7b05de6ea774993e0a92db59c0ceef768ff0b0559d573170957df |
| scan-summary.json | 3297f4197e644c67bbbeb7e1c5fb540f5ad277760aa02907f44555aa957d3ea8 |
| cleanup-targets.json | 7fc7b537dedc0858a7d6fc7e427585c8854f85b9bb887af6c88902cbf12e99d6 |
