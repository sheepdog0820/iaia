# OS再監査52指摘とCritical/Highの適用範囲（2026-10-30）

## 判定と対象

既知のCritical 2件・High 7件について、下記の固定した通常配布物には該当する問題の実装が含まれないと技術判定する。MariaDBの8件はサーバー/ダンプCLI等の実装、zlibの1件はこの版に未導入のnon-blocking処理である。これは当該image内のコードの適用範囲の判定であり、修正版への更新やリスク受容ではない。スキャナーの元の50指摘・exit2という結果は変更せず、除外設定も追加しない。正式公開は **No-Go** を維持する。

同じ候補をScout1.29.0で新しく監査したところ、未除外の結果は**52指摘（Critical2/High9/Medium6/Low35）、exit2**だった。新たなgcc-14由来のHigh2件のうち、aligned newは後述の実binary/分岐確認に基づき、このOS libraryでは問題の経路を通らないと判定した。priority queueの問題は未判定である。High/Criticalがすべて解決したという結論にはしない。

| 項目 | 対象 |
| --- | --- |
| source | `297a217da2d3445697c56171da212524d9433537`（PR #38の候補、未配備） |
| 通常image | `sha256:0fe931f78d4280275d151381601589bf36d7edf4c0fe81171d2e7cade2b93e15` |
| OS | Debian trixie、amd64 |
| 対象binary package | `libmariadb3:amd64`、`mariadb-common`、いずれも`1:11.8.6-0+deb13u1` |
| 対象zlib binary package | `zlib1g:amd64` `1:1.3.dfsg+really1.3.1-1+b1`、sourceは末尾`+b1`のない版 |
| 元のOS監査 | source873552d9/image6c3afa3dのScout1.28、50指摘（Critical2/High7/Medium6/Low35）、exit2 |

候補imageのPython111/OS101パッケージが先行配布物と同一である記録を保持する。ただし、この同一性確認と今回の9件の調査を、全パッケージスキャンの合格と扱わない。稼働中のWeb定義55のimageや外部MariaDBサーバーへ判定を拡張しない。

## 固定候補の新しい全パッケージ監査

10月30日に同じlocal imageを`local://sha256:0fe931...`で監査した。severity/package/EPSS等のフィルター、ignore/VEXは付けていない。実行中のジョブを観測タイムアウトで再作成せず、それぞれの終了を確認した。

| toolと完了時刻（JST） | package識別数 | 未除外の結果 |
| --- | --- | --- |
| Scout1.28.0、09:57:43 | 292 | 50指摘、C2/H7/M6/L35、exit2 |
| Scout1.29.0、10:00:48 | 298 | 52指摘、C2/H9/M6/L35、exit2 |

[1.29.0の公式リリース](https://github.com/docker/scout-cli/releases/tag/v1.29.0)はDebian packageの識別と古いSBOM cache等の修正を含む。そのため1.28の結果だけで止めず、release asset digestとchecksum一覧を検証した1.29をtask専用tmpへ展開して監査した。global installや製品imageは変更していない。version間の指摘差分は次の2件で、いずれもsource package gcc-14の14.2.0-19に対応する。

| 新しいHigh | 公式情報と現状 | 未完了 |
| --- | --- | --- |
| [CVE-2026-102010](https://security-tracker.debian.org/tracker/CVE-2026-102010) | libstdc++のbinary heap priority queue `erase_if`。trixieのgcc-14 sourceはvulnerable、forky/sidは14.4.0-3でfixed | headerからconsumerへ取り込まれるコードも含め、実native依存への適用範囲と修正を確認する |
| [CVE-2026-95619](https://security-tracker.debian.org/tracker/CVE-2026-95619) | libstdc++のaligned operator newのinteger overflow。trixieのgcc-14 sourceはvulnerable、forky/sidは14.4.0-3でfixed | 下記の固定OS libraryはPOSIX分岐を使うと確認。別library/versionやvendorが同梱する実装へ拡張しない |

imageにはgcc-14-base/libgcc-s1/libgomp1/**libstdc++6**の14.2.0-19が入っている。compilerの不在を理由にこの2件を適用外としない。修正版表示があるsidのpackageを独断で混入させず、priority queueの問題は未判定で残す。新しい監査の52件は全件OS由来で、Pythonの新しい指摘はなかったが、Twisted RC2や全経路の受け入れを解消する証拠にはしない。

### aligned newの実binary・実行分岐

[GCC14系の公式修正200183d](https://github.com/gcc-mirror/gcc/commit/200183d4ab5d57575f3dfebc6af3baf649910b9e)は、C11 aligned_alloc等へ渡す前のサイズ丸めのoverflowを修正する。同commitはPOSIX memalignの分岐ではその丸めを行わないことも説明している。source packageの版だけで判定せず、次を確認した。

- imageの`libstdc++.so.6.0.33`は、[公式Debian libstdc++6の同版amd64 binary](https://deb.debian.org/debian/pool/main/g/gcc-14/libstdc++6_14.2.0-19_amd64.deb)内のファイルとSHA256一致した。実libraryのSHA256は`972bb2a18b71140dab0240f8a1f68ab3fb1d56bcd4c4f824a91b70888faf5a00`。
- その実binaryの`_ZnwmSt11align_val_t`を逆アセンブルした。入力sizeを保持して`posix_memalign@plt`へ渡し、問題のsize+alignmentの丸め計算、C11 aligned_alloc、fallback mallocの分岐はなかった。関数名の文字列検索だけでなく、当該関数の命令列をレビューした。
- 検査専用C++ fixtureをWSLのg++11.4で作り、元の通常image内で動的リンクして実行した。巨大size9ケースはthrowing APIでbad_alloc、同じ9ケースはnothrow APIでnullとなり、通常のsize/alignment12ケースも成功した。計30ケースで想定外の小さい確保や通常入力の失敗は0だった。通信なし・root read-only・cap-drop・128 MiB・0.25 vCPUで、製品sourceは上書きしていない。

この根拠から、固定imageのこのOS libraryのaligned newはCVE-2026-95619の問題経路に該当しないと技術判定する。修正版の導入やscannerの指摘削除ではない。検査用のg++11.4はfixtureを作るためだけに使っており、製品native依存のビルド元やpriority queue headerの安全性を証明しない。native vendorの別実装・静的同梱・別imageはこの判断の対象外である。PGP署名・再現ビルドは未検証のままで、rawの52指摘を保持する。

## 公式修正が変更するコード

| 指摘 | 公式の修正箇所 | 配布物との対応 |
| --- | --- | --- |
| [CVE-2026-85746](https://security-tracker.debian.org/tracker/CVE-2026-85746) | [公式patch 5c04ca5](https://github.com/MariaDB/server/commit/5c04ca5524385356ff7cf84974a7d491974c1f85)の製品変更は`sql/spatial.cc`。GeometryCollectionのWKT変換で出力容量を扱うサーバー実装 | Connector/Cのソース・ビルド対象に当該実装がない |
| [CVE-2026-92262](https://security-tracker.debian.org/tracker/CVE-2026-92262) | [公式patch f277eef](https://github.com/MariaDB/server/commit/f277eefa424850a8cba5c2371406047f6395e8bb)は`sql/`の11ファイルと`storage/mroonga/`・`storage/myisammrg/`の2ファイル。サーバーの表名・ファイル名処理を変更。[後続574ba66](https://github.com/MariaDB/server/commit/574ba66b2d6c5d71db83d416677876e9b592858e)はテストのみ | Connector/Cのソース・ビルド対象に当該実装がない |
| [CVE-2026-107823](https://security-tracker.debian.org/tracker/CVE-2026-107823)（High） | [8a642bc](https://github.com/MariaDB/server/commit/8a642bc8103aadc6b2087d781ba8e1595616a2c4)、`sql/parse_file.h`・`sql/sql_view.cc`のview metadata処理 | Connector/Cの構成に含まれない |
| [CVE-2026-86047](https://security-tracker.debian.org/tracker/CVE-2026-86047)（High） | tracker掲載の公式5 patchすべてを確認。`client/mysqldump.c`、`sql/sql_acl.cc`・`sql/sql_show.cc`等と`storage/innobase/handler/ha_innodb.cc`のSQL生成 | サーバー実装とダンプCLIがなく、Connector/C libraryとは別のビルド対象 |
| [CVE-2026-107821](https://security-tracker.debian.org/tracker/CVE-2026-107821)（High） | [3b1c2e5](https://github.com/MariaDB/server/commit/3b1c2e58abab5571bec4ff52773ddc75b1738da9)、`sql/table.cc`のFRM処理 | Connector/Cの構成に含まれない |
| [CVE-2026-107818](https://security-tracker.debian.org/tracker/CVE-2026-107818)（High） | [e3d62d4](https://github.com/MariaDB/server/commit/e3d62d4e78fd4941cef3f5053e6a50d0b32d740e)、systemd service・Galera起動script・runtime directory設定 | そのservice/Galera script・サーバーがimageにない。socket設定の共通性を、serviceによる環境ファイル読み込みと混同しない |
| [CVE-2026-107815](https://security-tracker.debian.org/tracker/CVE-2026-107815)（High） | [b369925](https://github.com/MariaDB/server/commit/b369925f6855d3e1f0ebcf453492724b99fda6f8)、`storage/connect/value.cpp`のCONNECT engine | Connector/Cとは別のserver engineで、`ha_connect.so`もimageにない |
| [CVE-2026-97380](https://security-tracker.debian.org/tracker/CVE-2026-97380)（High） | [dbd60d0](https://github.com/MariaDB/server/commit/dbd60d0ad8daa2d01050346aa50b7b102490e456)、`sql/sql_yacc.yy`・`sql/structs.h`のGRANT PROXY処理 | Connector/Cの構成に含まれない |

[MariaDB公式の85746の告知](https://github.com/MariaDB/server/security/advisories/GHSA-8fvj-c57c-pggx)と[92262の告知](https://github.com/MariaDB/server/security/advisories/GHSA-65jj-h265-3m7h)は、11.8系の修正版を11.8.9としている。Debian trackerはtrixieのsource package `1:11.8.6-0+deb13u1`をvulnerableと表示している。source package全体の表示と、実際に入っているclient binaryの内容を区別して調べた。

## 実施した照合

1. 固定image内のdpkg情報・ファイル一覧から、MariaDB関連は上記2パッケージであることを確認した。`mariadbd`/`mysqld`の実行ファイルと`/usr/lib`配下のembedded server library `libmariadbd*.so*`はなかった。`mariadb-common`の内容は設定と文書で、サーバー実装ではない。
2. Debian公式poolの同じ版の[libmariadb3 amd64 package](https://deb.debian.org/debian/pool/main/m/mariadb/libmariadb3_11.8.6-0+deb13u1_amd64.deb)を読み取りで取得した。配布物の`libmariadb.so.3`と認証plugin6件、計7個のELFファイルがすべて公式package内の同じファイルとSHA256一致した。
3. ELFのDT_NEEDEDを確認した。7個の直接依存先はlibz/libssl/libcrypto/libc/ローダーで、MariaDB server/embedded server libraryへの依存はなかった。サーバーの不在だけで結論を出さず、次のソースとビルド定義も照合した。
4. [Debianの正確な版のsource](https://sources.debian.org/src/mariadb/1%3A11.8.6-0%2Bdeb13u1/)を取得した。元source archiveとDebian追加archiveは、同版の[公式dsc](https://deb.debian.org/debian/pool/main/m/mariadb/mariadb_11.8.6-0+deb13u1.dsc)に記載されたサイズ・SHA256に一致した。ダウンロードしたコードは実行・インストールしていない。
5. rootのCMake→`cmake/mariadb_connector_c.cmake`→`libmariadb/`の構成を読んだ。Connector/Cは独立したsource directoryを設定し、`libmariadb/libmariadb/CMakeLists.txt`がclientのsourceからobject libraryと`libmariadb`を作る。該当する`sql/`・`storage/`の修正ファイルはこの構成に含まれない。
6. Connector/C配下のC/C++/header/CMake計269ファイルを照合し、当該WKT変換・旧表名処理の実装を含まないことを確認した。Debian patch seriesの11件はConnector/Cの変更を含まず、全diff headerも確認した。`debian/libmariadb3.install`の出荷先はclient shared libraryと上記6pluginで、実imageの内容と対応した。
7. High 6件の公式10 commitもすべてConnector/Cのビルド対象とは別だった。実imageの`mariadb-dump`/`mysqldump`/`galera_new_cluster`のコマンド・該当するsystemd service・CONNECT engine pluginの不在も確認した。単にSQL接続先がPostgreSQLだから適用外としたのではない。

主要なハッシュは次のとおり。sourceの再ビルドによる再現性検証と、dsc/元archiveのPGP署名検証は行っていない。公式HTTPS経由のartifactと明示したハッシュ・ビルド定義の照合であり、供給網全体の保証ではない。

| artifact | SHA256 |
| --- | --- |
| `libmariadb3_11.8.6-0+deb13u1_amd64.deb` | `b2a2d1cdf7493c75d43916a18947700740964513ff5ff603cf5cbbf61e9e6385` |
| image内`libmariadb.so.3`（公式packageと一致） | `d283268434adf3cc3ffcb0580b384f3e13c91bd24b58114022073694dbcc2928` |
| `mariadb_11.8.6.orig.tar.gz` | `b126581a8ca89376d2a3ce63fee97c114c3e15315345e769b9d00c51e1b7d619` |
| `mariadb_11.8.6-0+deb13u1.debian.tar.xz` | `84da78759f1de6452e19cbc24eaa3855ed352fc9306eb12fa9c8f30832d1613b` |

## zlib Highの導入前コードとの照合

[CVE-2026-85091](https://security-tracker.debian.org/tracker/CVE-2026-85091)は、non-blocking write後のstale bufferと`gz_vacate()`に関する指摘である。[導入commit 81cc0be](https://github.com/madler/zlib/commit/81cc0bebedd935daeb81b0b6e475d8786b51af3d)が`gz_vacate()`と`state->again`を追加し、[修正df84af2](https://github.com/madler/zlib/commit/df84af25dc1942490e1d1c899a07619152a46148)はwrite停止時のinput pointerを扱う。Debian trackerには影響範囲の議論へのリンクがあり、trixieをvulnerableとする表示も残っている。その表示は削除・上書きせず、具体的なcodeの有無を調べた。

- imageのOSライブラリは`zlib1g:amd64` `1:1.3.dfsg+really1.3.1-1+b1`、実行時versionは1.3.1だった。[同じ版の公式binary](https://deb.debian.org/debian/pool/main/z/zlib/zlib1g_1.3.dfsg+really1.3.1-1+b1_amd64.deb)内の`libz.so.1.3.1`と実imageのSHA256が一致した。
- [正確なDebian source](https://sources.debian.org/src/zlib/1%3A1.3.dfsg%2Breally1.3.1-1/)の`gzwrite.c`に`gz_vacate()`と`state->again`はない。`zlib.h`も1.3.1で、Debian追加archiveにその機能をbackportするpatchはなかった。元archive/追加archiveは公式dscのサイズ・SHA256に一致した。
- この根拠から、固定imageのこのOS libzには当該導入コードがないと判定する。別のversion・vendorが静的に同梱するzlib・別imageの適用範囲は判定していない。PGP署名検証・再現ビルドはMariaDBと同様に未実施である。

| artifact | SHA256 |
| --- | --- |
| `zlib1g_1.3.dfsg+really1.3.1-1+b1_amd64.deb` | `015be740d6236ad114582dea500c1d907f29e16d6db00566ca32fb68d71ac90d` |
| image内`libz.so.1.3.1`（公式binaryと一致） | `85590dd58edf5445e18bc7193e5ebc01ac5841f1ae187e97705a662e90c6421e` |
| sourceの`gzwrite.c` | `469b1e58932ea11bdda2a153f6655f7b3c13254240fae157181b49ed1bc93b47` |

## 残る公開条件

従来の9件と追加のaligned newについて固定した対象の適用範囲を確認したが、Q04や正式公開条件は完了しない。gcc-14のpriority queue由来High・ほかのMedium/Low、Twisted RC2、AWS実行経路・実データ/配送/権限の検証は引き続き必要である。指摘のseverityを変更したり、scannerへignoreを追加したり、修正のないパッケージをsid等から混入させたりはしていない。

image・依存package・native plugin・ビルド設定が変わった場合は、この判定を再使用せず再確認する。将来MariaDB serverやembedded serverを導入する場合にも再判定が必要である。最新main・共有DBの適用・Web/背景処理反映・課金/外部連携・復旧/性能・運用を含む[正式公開の受け入れ条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を維持する。

本変更は調査文書だけで、DB・AWS・IAM/Secrets・費用・外部通知を変更しない。文書の復旧はrevert PRで行える。ローカル証拠は`tmp/mariadb-debian-provenance-20261030/`のbuild-source-map.json/client-binary-scope-proof.json/high-binary-scope-proof.json、`tmp/mariadb-critical-official-patch-map-verified-20261030.json`、`tmp/high-official-patch-map-20261030.json`、`tmp/zlib-gzwrite-provenance-20261030/zlib-gzwrite-scope-proof.json`、`tmp/gcc-native-scope-20261030/aligned-new-binary-scope-proof.json`と逆アセンブルに保持している。再監査は`tmp/current-release-297a217d-1.28.sarif`・`tmp/current-release-297a217d-1.29.sarif`と各scan-summary.jsonに未除外で保存した。無視対象の調査artifactはGitへ含めない。
