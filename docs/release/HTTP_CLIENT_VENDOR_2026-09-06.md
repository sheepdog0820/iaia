# 共通HTTPクライアントの固定配信

共通テンプレートはバージョン指定なしの外部Axios CDNを同期読み込みしていた。公開候補と配信時のライブラリが一致するよう、上流のAxios 1.20.0配布物を同梱してDjango staticから読み込む。既存fetch代替処理は変更しない。取得元・配布物ハッシュ・MITライセンス・更新時の監査手順は[同梱README](../../static/vendor/axios/1.20.0/README.md)に記録した。

## 検証

- テストファーストで、共通テンプレートの固定パスとmanifestへのAxios収集を追加。変更前はテンプレートと未配置ファイルの2件で失敗。変更後は2テストと5 subtestが成功。sourceMappingURLが参照するmapも配布物のまま配置し、manifest収集は終了0。
- 一時ディレクトリでexact指定したaxios@1.20.0のlockfileを作成し、npm auditは指摘0・終了0。配布アーカイブのSHA-512とSHA-1をnpmメタデータと照合。
- Chromium/Firefox/WebKitで共通HTTPクライアント、ホーム読み込み中の操作、smokeの関連27件成功。2026-09-06T06:40:14Z開始、70.24秒、expected=27、skipped/unexpected/flaky=0、retries=0。
- HTTPクライアントのケースは外部HTTPSを遮断し、同梱版はVERSION=1.20.0、同梱配信も止めたケースはVERSIONなしの代替処理であることを確認。日本語・特殊文字・配列・日付・既存クエリーの保持を両方で検証。
- テスト用イメージtableno-browser:playwright-1.63へ今回のbase.html、同梱Axios、HTTPテスト、現行Playwright設定を読み取り専用マウント。専用空SQLiteと合成ユーザー3件を使用し、コンテナは終了後削除。
- Black/isort/flake8の対象Python検査、同梱JSの構文、差分・文字コード・日本語文書のレビューは成功。製品の表示文言や権限は変更していない。

ローカル証跡: tmp/axios-manifest-red.log、tmp/axios-manifest-green.log、tmp/axios-package-audit.json、tmp/axios-browser-probe.log、tmp/axios-browser-probe-output/results.json。全体のリモートCIはpush後に確認する。新たなブラウザケース6件により全体は180件となる。

## ホーム遷移の未解決事項との区別

先のCIで発生したFirefoxの遷移失敗については、この変更前のアプリを使い、該当操作を10回・再試行なしで実行して全件成功した（72.69秒、tmp/home-firefox-probe-output/results.json）。再現できなかったという結果であり、原因の特定・解消ではない。本変更をその不具合の修正とは扱わない。CIのfailOnFlakyTestsにより、再試行でだけ成功する場合も以後は失敗として追跡する。

## 影響と復旧

全画面のブラウザ依存と配布静的ファイルが変わる。DB・Secrets・課金・外部サービス設定・実環境への反映は行っていない。以前の配備候補0b0cea6fには今回のAxios同梱を含まない。最終配備時には新候補の通常イメージを作成し、ハッシュ付きURL・圧縮配信を含めて再検証する。

問題が出た場合はこの変更単位をrevertできるが、未固定CDN参照が戻る。原因に応じて同梱版を維持した修正を優先する。サイト全体のオフライン対応や、ほかの同梱ライブラリの安全性を保証する変更ではない。

## 通常配備イメージの隔離検証

7ffd1f9715395eb0574b67d5f54746576eafa53cのgit archiveから通常Dockerfileでビルドした。タグはtableno-formal-release:7ffd1f97、ローカルIDは `sha256:c490460ebb1844a32eb88fcf9d737ef7da83bb4ae1924b3960c2a15ca197ce3c`。revisionラベルは同SHA、実行ユーザーはtableno。ECR未送信であり、このIDはECR manifest digestではない。

空PostgreSQL 16/Redis 7を専用internalネットワークへ配置し、公開ポートなし・外向き通信なしでAPP_ENV=aws-prodの通常entrypointを起動した。設定は隔離検証用の仮値、S3/Checkout無効。pg_isready成功後にアプリを起動し、空DBへの移行・静的203件収集/583件後処理・Daphneのリスナー起動を確認した。

readiness/登録画面200、登録画面の静的参照6件200、Axiosを加えたvendor9件のハッシュ付きURL・配信内容の照合が成功。CSS/JSはgzipで配信され、展開後はcollectstatic生成ファイルと一致する。AxiosはsourceMappingURLのmanifest書換えがあるため、上流配布物そのものと生成後ファイルのハッシュは異なる。check --deployは指摘0、migrate --checkとpip checkは終了0。release_database_preflightも終了0、read_only=true、participant_id/roleの一意制約、複数ロール・重複組とも0を確認した。

証跡はtmp/release-axios-7ffd1f97-build.log、同http.log、同startup.log、同db.json。検証用アプリ・DB・Redisと専用ネットワークは削除済み。実ユーザーデータや共有DBの移行、実TLS/S3/Stripeの検証を示す結果ではない。

OS監査の初回はScoutキャッシュ競合で終了1となった。[Dockerの設定手順](https://docs.docker.com/scout/how-tos/configure-cli/)に従いDOCKER_SCOUT_CACHE_DIRを専用tmp/scout-cache-7ffd1f97へ変更し、他のプロセスや既存キャッシュを変更せず再実行した。1.24.0で392パッケージを索引し、deb限定では20ソースパッケージ・113件、終了2。新旧イメージのdpkg一覧175件は完全一致した。OSの未解決事項は維持する。

同じ候補をパッケージ種別の除外なしで監査すると25パッケージ・119ルール、終了2だった。High 6、Medium 2、Low 105、Unspecified 6。追加6ルールは以下のPythonパッケージに対するもので、独立した6種類の攻撃経路を実証したという意味ではない。

| 指摘 | 監査上の対象 | 修正版の表示 |
| --- | --- | --- |
| CVE-2026-59890 | setuptools 70.3.0 / 79.0.1 | 83.0.0 |
| CVE-2026-24049 | wheel 0.45.1 | 0.46.2 |
| CVE-2026-57585 / GHSA-6v7p-g79w-8964 | msgpack 1.1.2 | 1.2.1 |
| CVE-2025-47273 | setuptools 70.3.0 | 78.1.1 |
| CVE-2026-23949 | jaraco.context 5.3.0 | 6.1.0 |

実イメージのトップレベルはsetuptools 79.0.1、wheel 0.46.3、msgpack 1.2.1。一方、setuptools/_vendorのMETADATAはwheel 0.45.1とjaraco.context 5.3.0を示し、pip 26.2.1の_vendor/vendor.txtはmsgpack 1.1.2とsetuptools 70.3.0を示した。実アプリがimportするmsgpack 1.2.1だけを見て、同梱された古いコピーの指摘を解決済みにはしない。CI用requirements-test.lock.txtのsetuptools 84.0.0は、通常イメージ内のsetuptoolsを更新していなかった。ビルド関連ツールがランタイムに必要かを調査し、更新または最終イメージからの除去と起動・機能検証を次の修正単位で行う。

追加証跡: tmp/runtime-os-7ffd1f97-scout.log（初回失敗）、tmp/runtime-os-7ffd1f97-scout-isolated.log、tmp/runtime-os-7ffd1f97.sarif.json、tmp/runtime-os-7ffd1f97-packages.txt、tmp/runtime-all-7ffd1f97.sarif.json、tmp/runtime-all-7ffd1f97-scout.log。指摘を抑制せず、公開判定は引き続き未達とする。
