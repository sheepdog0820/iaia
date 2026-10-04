# Stripe Endive候補の通常配布物検証（2026-10-04）

## 固定対象・承認境界

対象は `2b70f1d55f2b735b1e317c7b853aa8bd8959a550`。[SDK/API更新](STRIPE_SDK_API_UPGRADE_2026-10-04.md)の通常Docker配布物を検証した。今回のリポジトリ変更は検証記録のみで、専用ブランチ `codex/stripe-endive-runtime-evidence-20261004` を使用する。元checkoutのハンドアウト未コミット差分は触っていない。

main/AWS/ECR/ECS/共有DB/CloudFront、Stripeアカウント/endpoint/Price/キー、Secrets/IAM、実メール、常設容量・継続費用は変更していない。完了済みfavicon8567f49fの承認や、固定6b6c570c反映案へ今回候補を追加しない。正式公開 **No-Go** を維持する。

## 配布物の同一性

固定SHAの `git archive` を通常Dockerfileへ渡し、タグ `tableno:stripe-runtime-2b70f1d5` を構築した。image IDは `sha256:b44e8700a017800964a603c9c48395af3a3aba906e846743ab45e9be7824b9da`。revision labelは対象SHA、実行ユーザーtableno、entrypoint `/entrypoint.sh`。レジストリへのpush・署名検証はしていない。

accounts/api/schedules/scenarios/support/tableno/static/templates、tests/unit/integrationの選定拡張子とruntime lock/entrypoint/manage.pyについて、追跡671ファイルのarchive対image SHA-256を照合し、欠落0・不一致0・Python caches0を確認した。対象拡張子はpy/html/css/js/png/ico/svg/woff/woff2/ttf/json。全filesystemやnativeビルド閉包の証明ではない。

Pythonパッケージ111、Stripe **16.0.0** / Django **5.2.17**。通常Webの設定でもAPI **2026-09-30.endive** を確認した。SDKやアプリソースをoverlayせず、runtime lockからインストールした配布物を使用する。前2ff6a4c8 imageと先頭7層は同じで、OS/apt層はキャッシュ利用。依存層を再構築したが、新しいOS修正の取得とは扱わない。

## 配布物内テストと通常起動

| 検証 | 結果・範囲 |
| --- | --- |
| 隔離PostgreSQL 18.3 | **545件成功、省略0、101.451秒、終了0**。保存した33モジュールの一覧は `regression-targets.json` |
| production設定 | **28件成功、25.508秒、終了0**。別のnetwork noneコンテナで実行 |
| 通常entrypoint | 空の専用DBへの移行、静的232件/624 post-process、Daphne起動成功 |
| 通常設定 | fixture初期化前に専用DB名・ユーザー表空・SDK/API版・購入開始/メール無効をassert |
| `check --deploy` | 問題0、終了0 |
| `migrate --check` | 終了0 |
| 静的manifest | 前2ff6a4c8から232 mappingの追加/削除/変更0、manifest bytes同一 |
| ローカル文書検査 | `tests.unit.test_release_documentation` 39件成功、0.035秒。配布物の545件とは別。差分・日本語記述・相対リンクも確認 |

PG回帰は課金/認証/退会ガード/競合、Stripe再試行/順序/返金・Dispute、メール配送/監視、コード/手動付与/再同期、管理/所有者照合、6版API/CCFOLIA版保持、ICS/calendar APIを含む。実SDK+メモリーtransportによるEndive更新20件と先行transport14件も配布物内で成功した。これらでは外部I/Oできないtransportと合成HMACを使用し、他の回帰には既存mockもある。実Stripeへの接続や実決済の成功ではない。

テスト用設定と既存Node工具だけread-only mountした。Node v20.20.2のbinary SHA-256は `6295488653f0d93b0a157841746fef7e72cc4328cfb60c4bbe0ca2668a836ffd` と再照合。アプリ/テスト/SDKの差し替えや、imageへのNode追加はしていない。DockerではMarkdownを除外するため、リリース文書テストはこの545件へ含めない。選択対象が異なる先行ローカル588件の証拠と区別し、直接合算しない。

fixtureは使い捨てPG・locmemメール/cache・一時メディア。意図した400/401/403/404/500/503やtracebackはログに残る。全ログの警告0や性能基準達成を主張しない。

## 27件の実HTTP

PG imageは `sha256:fbaa243599038521bbda8f6fa286d2a8fc1236509606f22de81d0739b0610ba7`、network none・公開ポートなし・512 MiB・DB tmpfs。Redis 7.4.11 `sha256:5509c0097c6064aa8a3b1df58f1d950e67090fffa6678ae8f3f1dc2385f12deb` とWebはPGのnetwork namespaceを共有した。Webは0.25 vCPU/512 MiB、Redisは128 MiB。S3無効、SMTPは到達不能loopback、実Stripeキーなしで外部通信不能。

通常Webの19 HTTPは全期待結果一致、終了0。readinessのHTTP200/DB・cache正常、ログインページ、favicon等4 URLの元bytes一致、manifest内CCFOLIA helper bytes、ICS停止GET/HEAD拒否/再有効化/参加資格喪失/旧token失効/文字・UTC、無料通常ユーザーのCCFOLIA 6版/7版API往復を確認した。静的manifestのAWS/CloudFront全bytesとの一致は未確認。

通常Web停止後、同じimageの別Webを合成 `STRIPE_CHECKOUT_ENABLED=true` / `RUN_MIGRATIONS=false` / `RUN_COLLECTSTATIC=false` で起動。未認証Checkout/Portal各401、保存intentのcustomer/metadata/client_reference/subscription_data.metadata不一致各400、実PGロック待ち中の所有者変更後にCheckout/Portal各400を確認した。日本語エラー・レコード/intent/監査/権限の不変も照合し、追加8 HTTP・終了0、実ロック待ち観測2件。Webログの401×2/400×6と一致した。共有AWSの購入開始設定は変えていない。

HTTP probeにはStripe mockがないが、購入成功を確認したものでもない。DRF Tokenはfixtureで注入し、loopback HTTPにproxy-HTTPSヘッダーを付けた。実ログイン/OAuth/TLS/ALB/ブラウザー/外部受信アプリの検証ではない。先行管理41操作は再実行せず加算しない。今回の回帰/HTTP検証に初回失敗・再実行はない。

全検証後、Web2/Redis/PGの完全ID・image・network・公開ポートなし・PG tmpfsを再照合して停止/削除した。合成データのみ破棄し、fixtureで再作成可能。image/archive/静的生成物/ログ/工具は保存し、他のコンテナや実データは変更していない。

## 監査・CI・残作業

Scout1.26.0、専用cache、NO_CACHE=true、無抑制全監査は292 indexed/16 vulnerable packages/39指摘（**HIGH3/MEDIUM2/LOW34、Python0**）、終了2。SARIF生成完了。前2ff6a4c8からCVE IDの追加/削除0・重大度変化0だが、未修正は未修正のまま扱う。HIGHはGCC14のCVE-2026-102010/CVE-2026-95619とzlibのCVE-2026-85091で、report上のfixed versionはnot fixed。抑制・ベース除外・リスク受容・OSゲート合格はしていない。

候補[CI run37204401824](https://github.com/sheepdog0820/iaia/actions/runs/37204401824)は対象SHA/branchと一致。22:17 JSTの確認時点ではproduction-database/infrastructure/system/lint-securityがsuccess、Unit / Integrationとplaywrightは実行中。完了前にCI全6項目成功やマージ可能とは扱わない。今回記録のCIも候補CIとは別に確認する。

SDK/API更新の通常配布物未検証は上記範囲で解消した。RAKの権限・prefix対応、実SandboxでのEndive API/Checkout/Portal/署名付きイベント、Webhook版/Secrets切替・復旧、共有DB0065〜0067、worker/SMTP/監視、管理削除/所有者方針、OS/native閉包、外部連携、AWS性能・復旧、事業者/税務は未完了。Stripe Taxの登録・automatic_tax設定は変更していない。[正式公開No-Go](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を維持する。

記録のrevertはアプリ/稼働版を変えない。将来の実環境ロールバックでは、Endiveで作成された未解決intentを旧APIへ無確認で再送せず、購入開始を止め、本文・冪等キーを保持して実状態を照合する。復旧対象と操作の承認を別途確認する。

## 保存証跡

保存先 `C:/tmp/iaia-stripe-runtime-2b70f1d5/`。合成env、archive、工具、大量生成物はGitに含めない。ソース照合とHTTP probeは先行候補で読了した検証スクリプトを再利用した。

| 証跡 | SHA-256 |
| --- | --- |
| source-manifest.json | 1de069f85cce4c36f0845a622500d56c8a30676b15aadd3bda1a37f598be7d25 |
| inspection.json | 348b74dee56c4e180c72f3ed54b1ce70e660ac893a2d6e6c3af4f5e57a1b829f |
| image-inspection.json | 15f8f09f2dfc7d4de72108daee4c552aa819f7f1c07f6d204b1305ad203daa10 |
| regression-targets.json | 11fd14fb9ea45a9e7a70e88d40384e1e9e8bf4d2b461e0bb529f9d5f10cd5d5c |
| regression.log | ed4667553c6dc8c7cffb567cdd01b5124ec8dcc95c002ce63d8445a4643d8b08 |
| production-settings.log | 242ef3fff01127615adf97cd53009960d740dd23644ee86af30fb2fd6b9ec0cb |
| fixture-guard.log | 555a6798f0ded909b8513b855ce873240268c38621875245a17cd7437f1f87c6 |
| web-startup.log | 962a7502a1b5822c12b5e81e99eb0ba5badc04f876b503086f50437ed9b2ada5 |
| base-http.log | ab1c9a9ec1236aa0c2c6499dadaf21c28caffbd37b596c9aaf4ef83cefdf7b3e |
| owner-http.log | bad9db744eb8971479054a87cd49d7ae500c577d573972e1850b470efcab0602 |
| owner-web.log | f31c5c473cd328ee2cf5f63417cb6cba710c2f2f0514cbb33fd93f71a512f629 |
| staticfiles/staticfiles.json | 20af8bfd892374b30973bd097c015e79a355d09b3273868a8bf7806d709c11f0 |
| runtime-full.sarif.json | 1963b7babb9ba6979200a32b0baee8dd57e19ee9e1642c8778e0fbed440e2f16 |
| scan-summary.json | 968c12d2c609b01186023640dda6206b44f714244655fa397dcc2db39702ca07 |
| cleanup-targets.json | 2baf3bc36d778f9173e187379fadeadd4e3eeea4cdd9d739342cf938842f84f6 |
