# 実行用イメージからのOSビルド依存除去

## 試験結果と適用状態

OSパッケージの削減を試験用イメージで検証した後、正式Dockerfileにも反映してローカルで検証した。実環境には反映していない。初期試験は元の `tableno-runtime-tools:validation` に対してビルド用パッケージを除いたもので、`tableno-runtime-build-deps:probe` のイメージIDは `sha256:babe16b0aabebef286cade99ffb110655f13fb1a5cb09bc38d8ad1e0ac649019`。

単純なauto-removeではMySQLの実行用共有ライブラリも消えるため、`libmariadb3`、`libpq5`、`libgomp1` を保持対象にしたうえで、`build-essential`、`default-libmysqlclient-dev`、`libpq-dev`、`pkg-config` と不要になった依存を除いた。OSパッケージ数は175から114へ減少した。

元イメージは単一の最新Gitコミットそのものではなく、[Pythonビルドツール除去時の検証イメージ](RUNTIME_PACKAGING_TOOLS_2026-09-06.md)である。本試験はOS依存の比較であり、現在の全アプリ変更を含むリリース候補の検証ではない。

## 実行依存の確認

- pip/setuptools/wheel/pkg_resourcesが存在せず、Django、Daphne、Celery、channels_redis、psycopg、MySQLdb、Pillow、rembg、onnxruntime、Stripeのimportが成功。
- Python拡張と共有ライブラリ304ファイルをlddで比較。未解決の依存3件（Numbaのlibtbb、Tkinterのlibtk/libtcl）は削減前後で同じだった。「全共有ライブラリが解決」とはしない。
- MySQLdbが実際にlibmariadb.so.3等へリンクすることを確認した。

## 脆弱性スキャン

Scout 1.24.0の初回はキャッシュ初期化のロック競合で終了1。別の専用キャッシュでの再試行は292パッケージを検査し、17パッケージ・48指摘で終了2となった。指摘ありのため合格とはしない。一時アーカイブ削除の使用中警告も出たがSARIFは出力された。他プロセスの終了操作はしていない。

比較元の113指摘（HIGH 1 / MEDIUM 1 / LOW 105 / UNSPECIFIED 6）に対し、試験後は48指摘（HIGH 1 / MEDIUM 1 / LOW 40 / UNSPECIFIED 6）。LOWが65件減少し、HIGH・MEDIUM・未分類の指摘は残る。

証拠は `tmp/runtime-build-deps-probe/Dockerfile`、`tmp/runtime-build-deps-probe-build.log`、`tmp/runtime-build-deps-{before,after}-packages.txt`、`tmp/runtime-build-deps-{baseline,probe}-link-check.log`、`tmp/runtime-native-dependencies.log`、`tmp/runtime-build-deps-probe-scout{,-retry}.log`、`tmp/runtime-build-deps-probe-retry.sarif.json`。

## 正式Dockerfileでの検証

依存を導入してpip check・Pythonビルドツール除去を終えた後、保持する実行用ライブラリをmanual指定し、コンパイラー・開発ヘッダーをpurgeするRUNを追加した。依存導入のキャッシュは維持する。単一ステージの既存構成では下位レイヤーのビルド用ファイルは残るため、配布イメージ容量を同じ比率で削減したとはしない。最終ファイルシステムの不要パッケージ除去を目的とする。

ビルド用パッケージが存在しないことを要求するプローブは、元の通常イメージで `build-essential` が残っているため失敗。変更後の通常ビルドは成功し、同じプローブで4つのビルド用パッケージ不在と3つの実行ライブラリ保持を確認した。

現在の作業ツリーから作成したイメージは `tableno-runtime-build-deps:validation`、ID `sha256:8598e1d5bcd4d200016e90aa3125ab9e754f0da8b4ab50ff41feefac0cab2521`。`c9801e6c` に未コミットのDockerfile・共通CSS・テスト変更を含むため、単一のGit SHAだけで表さない。

- pip/setuptools/wheel/pkg_resourcesの不在と、Django・Daphne・Celery・channels_redis・psycopg・MySQLdb・Pillow・rembg・onnxruntime・Stripeのimportに成功。
- この通常イメージで課金・6版版管理・複数画像のDjangoテスト226件成功（91.361秒）。ネットワークなし・隔離SQLiteで実行。
- 専用internalネットワーク内の空PostgreSQL 16・Redis 7と本番設定で通常entrypointを起動。DB移行・collectstatic・ASGI起動が成功。外部公開ポートは設定せず、S3・Checkoutは無効。
- readinessと登録画面200、登録画面の静的ファイルとvendor9件のハッシュ付き配信・CSS/JS gzip内容照合に成功。
- `check --deploy` は指摘0、`migrate --check` と読み取り専用の `release_database_preflight` は終了0。
- 所有ラベルを確認して専用アプリ・DB・Redis・ネットワークを削除済み。共有環境・Secrets・実ユーザーデータは操作していない。

証拠は `tmp/runtime-build-deps-final-{build,tests,imports,http,startup,deploy-check}.log`、`tmp/runtime-build-deps-final-db.json`、`tmp/runtime-build-deps-check.py`。通常イメージの再スキャンを `tmp/runtime-build-deps-final.sarif.json` に記録する。キャッシュ先は[Docker公式設定](https://docs.docker.com/scout/how-tos/configure-cli/)の `DOCKER_SCOUT_CACHE_DIR` で分離する。

この通常ビルドではTerraformのローカル作業ファイル混入が見つかり、最初のスキャンは647パッケージ・134ルール（140検出）となった。ファイル内容を変更せずDockerの除外ルールを修正した経緯と検証は [ビルドコンテキスト分離](DOCKER_CONTEXT_ISOLATION_2026-09-06.md) を参照。

除外修正後の通常イメージ `tableno-runtime-build-deps:clean`（ID `sha256:ce8767d4e6dea73fc701a26098e3e4c4daa7626a91e698909d198d94778246ae`）は292パッケージ・48指摘（HIGH 1 / MEDIUM 1 / LOW 40 / UNSPECIFIED 6）、終了2。初期の削減試験と同じ件数であり、不要パッケージの削減とOS指摘の残存を区別する。OSパッケージ数は114。アプリの機能テストは上記の通常イメージで実施し、後続変更はTerraform作業ファイルの除外とそのCI検査である。

残る高重要度指摘の適用可否確認は引き続き必要。本番反映や共有DB操作の承認を代替する資料ではない。問題があればDockerfileのこの変更をrevertして再ビルドできるが、不要なビルド用パッケージも復帰するため監査指摘への影響を確認する。
