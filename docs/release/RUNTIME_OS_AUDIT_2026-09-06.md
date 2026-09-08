# 配備候補のOSパッケージ監査

2026-09-06、通常Dockerfileで作成した候補0b0cea6fec716ed7dfda15546b471c9e90cc0d34を監査した。Pythonとnpmの監査成功だけではOSパッケージの確認にならないため追加した検査である。指摘の修正完了・例外承認・本番公開可とは判定しない。

## 対象と再現

- イメージ: `tableno-formal-release:0b0cea6f`
- イメージID: `sha256:5d2c113a6488c0c772f798b250ef45d59878ac110c9cef851e0a677a29cfedd1`
- 初回のDocker Scout CLIは1.5.0。下記のとおり1.24.0でも再評価した。
- コマンド: `docker scout cves --only-package-type deb --format sarif --exit-code --output tmp/runtime-os-0b0cea6f.sarif.json local://tableno-formal-release:0b0cea6f`
- 終了コード: 2。SBOMの索引366パッケージのうち、指摘されたソースパッケージ20、脆弱性ルール113件。
- 重大度: High 1、Medium 1、Low 105、Unspecified 6。全ルールのfixed_versionはnot fixed。これは取得した監査情報の表示であり、すべての実行経路が脆弱という意味でも、リスクを受容できるという意味でもない。
- SARIFのSHA-256: `4ec9ea24bc5c2e63d77e03991b704c591d16b07d7443890aabe4a72fdb1f58aa`
- ローカル証跡: `tmp/runtime-os-0b0cea6f.sarif.json`、`tmp/runtime-os-0b0cea6f-scout.log`、`tmp/runtime-os-0b0cea6f-packages.txt`。これらはGit管理外のため、配備承認時には候補を再監査し、正式な証跡保管先へ保存する。

## 優先指摘の調査

### High: CVE-2026-85091 / zlib

[Debianの追跡情報](https://security-tracker.debian.org/tracker/CVE-2026-85091)の説明は1.3.1.2から1.3.2のgz_vacate関数を対象としている。一方、同じページのパッケージ表はtrixieの1.3.1もvulnerableとしている。[上流の未定義動作への対処](https://github.com/madler/zlib/commit/e3dc0a85b7032e98380dec011bc8f2c2ee0d8fca)はgzwrite.cでNULLポインターの判定を追加しているが、これを当該CVEの正式な修正とする確認は取れていない。

2026-09-08の再確認では、Debianの注記に[上流への照会Issue #1310](https://github.com/madler/zlib/issues/1310)が追加されていた。IssueはOpenで、取得した本文は報告の有無を尋ねるものであり、修正完了や非該当の回答ではない。Debianバグ1146895の本文は今回取得できず、内容を確認した扱いにはしない。

同日、curl削除後の通常イメージ `158c7301a238` でPythonの実行時zlibは1.3.1、実体は `/usr/lib/x86_64-linux-gnu/libz.so.1.3.1`、SHA-256は `85590dd58edf5445e18bc7193e5ebc01ac5841f1ae187e97705a662e90c6421e`。`dpkg -V zlib1g` は終了0だがchangelogファイル3件の欠落を表示した。libz本体の不一致は表示されなかったものの、終了値だけでパッケージ全体が完全一致と解釈しない。最新版候補でもHIGH指摘の正式な解消判断は保留する。

候補内のzlib1g/zlib1g-devは `1:1.3.dfsg+really1.3.1-1+b1`。PythonのZLIB_VERSIONとZLIB_RUNTIME_VERSIONはいずれも1.3.1。[Debian公開ソースのgzwrite.c](https://sources.debian.org/src/zlib/1%3A1.3.dfsg%2Breally1.3.1-1/gzwrite.c/)を取得したところ、gz_vacateは存在せずgzvprintfは存在した。取得ファイルは19,237バイト、SHA-256は `469b1e58932ea11bdda2a153f6655f7b3c13254240fae157181b49ed1bc93b47`、ローカル保存先は `tmp/debian-zlib-1.3.1-gzwrite.c`。

以上は適用範囲に食い違いがある証拠であり、誤検知の確定ではない。初回に取得できなかったパッチ一覧は、後続で[Debianのseries](https://sources.debian.org/data/main/z/zlib/1%3A1.3.dfsg%2Breally1.3.1-1/debian/patches/series)を直接取得し、空ファイルと確認した。[debian/rules](https://sources.debian.org/data/main/z/zlib/1%3A1.3.dfsg%2Breally1.3.1-1/debian/rules)も取得し、build-stampはconfigure後にmakeを行い、パッチ適用処理の記述は見当たらなかった。rulesのSHA-256は `de5f6bf1daba3309b7ac352c2fc35330b02a703ae1b61d2d45973725783b06fc`。

2026-09-08の補足: 上記の上流コミットe3dc0a8は、説明と差分からNULLへの加算による未定義動作を避ける変更と確認できる。このCVEが説明する書き込み停止後の古い外部バッファポインターによるオーバーフロー全体を修正したという上流の確認は得られていない。「上流の修正」をCVE解決の証拠として読み替えない。

同日、固定候補10d21e42（イメージID `sha256:dec00ade1cc08142732ee124b9082d2c19e88003cac4a40339d3efc302e69cf2`）をネットワークなし・読み取り専用・終了時削除で検査した。Pythonのコンパイル時/実行時zlibはともに1.3.1、zlib1gは `1:1.3.dfsg+really1.3.1-1+b1`。`/usr/lib/x86_64-linux-gnu/libz.so.1.3.1` のSHA-256は `85590dd58edf5445e18bc7193e5ebc01ac5841f1ae187e97705a662e90c6421e`。dpkg --verifyは終了0で欠落したchangelog 3件のみを表示し、ライブラリの変更は報告しなかった。これで旧候補に限られていたパッケージ検証を最新の固定候補でも確認したが、再現ビルドや非該当の確定ではない。

主要アプリaccounts/schedules/scenarios/tablenoのPython（test*除外）でgzprintf/gzvprintf/gzwrite/gzip/zlibの記述は一致なし。依存内部の圧縮処理の不在を証明しない。公式追跡ページは対象バージョンの食い違いを維持し、以前あったcheck detailsという注記は今回の表示にはなく、Debian Bug #1146895への参照が追加されている。注記の削除だけで調査完了と推定しない。Bug本文は閲覧ツールのエラーで取得できず、その内容は未確認。上流Issue #1310にも解決を示す応答は確認できなかった。HIGHは未解決を維持し、根拠のないパッチ適用や指摘抑制は行わない。

候補内の `dpkg --verify zlib1g` は終了0で、欠落したchangelog文書3件だけを表示し、ライブラリの変更は報告しなかった。ただしこれはバイナリの再現ビルド検証ではない。対象関数が含まれない可能性を裏付ける追加証拠として扱い、指摘は抑制しない。パッケージ提供元の判定更新と最終候補の再監査を公開前の残条件とする。

### Medium: CVE-2025-45582 / tar

候補にはtar `1.35+dfsg-3.1` がある。[Debianの追跡情報](https://security-tracker.debian.org/tracker/CVE-2025-45582)は、同じディレクトリへ連続して展開する不正なアーカイブとシンボリックリンクを説明し、上流の仕様どおりとして争われている指摘と記載する。

accounts/api/schedules/scenarios/support/tableno/scriptsのPython・シェルを対象にtarfile、extractall、unpack_archive、gzprintf、gzvprintf、gzwriteを検索し一致なし。ただし依存ライブラリや全運用経路の到達不能を証明する検索ではない。利用者提供アーカイブの取り扱いと運用スクリプトの展開先分離を最終候補で確認する。現時点では例外承認していない。

### UnspecifiedとLow

Unspecified 6件はMariaDBソースパッケージに対応するCVE-2026-47023、60184、60331、60585、60747、61081。dpkg一覧にはクライアントライブラリ・開発パッケージ・commonがあり、MariaDBサーバーパッケージは見当たらない。これだけでクライアントへの非該当とは判定せず、各CVEの対象コンポーネントとの照合を残す。

Low 105件は個別の適用範囲・緩和策を未評価。Dockerfileではbuild-essentialなどのビルド依存も最終イメージに残る。ランタイムからの除去は改善候補だが、必要な共有ライブラリを壊さないビルド・起動・機能検証を伴う別の修正単位で扱う。件数を減らす目的だけでパッケージを削除しない。

## 影響と残条件

### 2026-09-08: 現候補の対象コンポーネント照合

OSビルド用パッケージ除去後の対象は `tableno-runtime-build-deps:clean`、イメージID `sha256:ce8767d4e6dea73fc701a26098e3e4c4daa7626a91e698909d198d94778246ae`。上記の旧候補113件とは区別する。最新の保存済み監査は48件（HIGH 1 / MEDIUM 1 / LOW 40 / UNSPECIFIED 6）であり、この照合だけで件数やスキャナーの終了コードを変更しない。[ビルド・検証記録](RUNTIME_BUILD_DEPENDENCIES_PROBE_2026-09-06.md)を参照。

Debianの各CVEページを再取得して対象を照合した。

| CVE | 公式説明の対象コンポーネント |
| --- | --- |
| [CVE-2026-47023](https://security-tracker.debian.org/tracker/CVE-2026-47023) | Server: Replication |
| [CVE-2026-60184](https://security-tracker.debian.org/tracker/CVE-2026-60184) | Server: Replication |
| [CVE-2026-60331](https://security-tracker.debian.org/tracker/CVE-2026-60331) | Server: Replication |
| [CVE-2026-60585](https://security-tracker.debian.org/tracker/CVE-2026-60585) | Server: Replication |
| [CVE-2026-60747](https://security-tracker.debian.org/tracker/CVE-2026-60747) | Server: Replication |
| [CVE-2026-61081](https://security-tracker.debian.org/tracker/CVE-2026-61081) | Server: Performance Schema |

6ページともソースパッケージmariadbのtrixie `1:11.8.6-0+deb13u1` はvulnerable、sidの修正版は `1:11.8.9+ds-1` と記載されていた。sidの修正情報だけで現行安定版イメージを更新済みとは扱わず、配布系列も変更しない。

固定イメージを `docker run --rm -i --network none --read-only --entrypoint python` で検査。`dpkg-query -W` の全パッケージからmysql/mariadbを抽出すると、インストール済みは `libmariadb3:amd64` と `mariadb-common`（ともに `1:11.8.6-0+deb13u1`）、`mysql-common`（`5.8+1.1.1`）のみだった。PATH内のmariadbd/mysqld/mysql/mariadb、`/usr/sbin/mariadbd`、`/usr/sbin/mysqld`、`/usr/lib/mysql/plugin` は存在せず、`/usr/lib/x86_64-linux-gnu/libmariadb.so.3` は存在した。

この結果は説明対象のサーバーがアプリイメージにインストールされていないことを裏付ける。クライアントライブラリは残っており、ソースパッケージ単位の指摘とバイナリの適用範囲を区別する必要がある。修正差分のクライアントへの影響までは未確認のため、6件を一括で誤検知・例外承認済みとはしない。外部DBサーバーの安全性を証明する検査でもない。

HIGHのzlibは再取得時もtrixieがvulnerableで、説明の対象バージョンとの不一致が残る。注記が参照する[上流Issue #1310](https://github.com/madler/zlib/issues/1310)はopenでコメント0件だった。問い合わせの存在は上流による修正・非該当の確認ではない。tarのページも上流が仕様として争っている旨の記載を維持していた。新たな安全宣言や指摘の抑制は行わない。

### 現行スキャナーによる再評価

[Docker公式の1.24.0リリース](https://github.com/docker/scout-cli/releases/tag/v1.24.0)からWindows amd64 ZIPを一時ディレクトリへ取得し、GitHub release APIのSHA-256 `1b7afb489e9224411fafe848eb5002cdc5c59a5cf2b77d6ccffcb44ffdf4f350` と一致を確認した。既存のDockerプラグインは置換せず、一時EXEを直接実行した。

同じイメージ・同じdeb限定条件で再検査し、終了2、20ソースパッケージ・113件だった。新旧SARIFのCVE ID集合は一致した。追加の証跡は `tmp/runtime-os-0b0cea6f-scout124.sarif.json`（SHA-256 `8d945c1d870ea204099db2586bdb16518ddf7fcefeb7001be98ebace2de012d8`）と `tmp/runtime-os-0b0cea6f-scout124.log`。旧CLIだけに由来する指摘として除外する根拠は得られなかった。

今回は読み取り監査と文書化のみ。アプリ、DB、Secrets、AWS、課金設定、配備候補の内容は変更していない。既存の読み取り専用AWS検査の承認依頼も未実行のまま。この監査で新たな未解決事項が判明したため、同候補の公開承認には本記録を含める。

公開前には、最新のスキャナー・脆弱性情報と固定した最終イメージで再検査し、Highの適用範囲の不一致、MariaDB各項目、残るLowを評価する。修正可能なものは修正・再検証し、残るリスクは根拠と緩和策を示して公開責任者の判断対象にする。自動スキャンの終了2を成功へ読み替えない。
