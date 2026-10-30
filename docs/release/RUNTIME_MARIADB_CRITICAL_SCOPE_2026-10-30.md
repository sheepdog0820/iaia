# MariaDB Critical 2件の配布物内の適用範囲（2026-10-30）

## 判定と対象

既知のCVE-2026-85746とCVE-2026-92262について、下記の固定した通常配布物には問題のサーバー実装が含まれないと技術判定する。これは当該image内のコードの適用範囲の判定であり、MariaDBの修正版への更新やリスク受容ではない。スキャナーの元の50指摘・exit2という結果は変更せず、除外設定も追加しない。正式公開は **No-Go** を維持する。

| 項目 | 対象 |
| --- | --- |
| source | `297a217da2d3445697c56171da212524d9433537`（PR #38の候補、未配備） |
| 通常image | `sha256:0fe931f78d4280275d151381601589bf36d7edf4c0fe81171d2e7cade2b93e15` |
| OS | Debian trixie、amd64 |
| 対象binary package | `libmariadb3:amd64`、`mariadb-common`、いずれも`1:11.8.6-0+deb13u1` |
| 元のOS監査 | source873552d9/image6c3afa3dのScout1.28、50指摘（Critical2/High7/Medium6/Low35）、exit2 |

候補imageのPython111/OS101パッケージが先行配布物と同一である記録を保持する。ただし、この同一性確認と今回の2件の調査を、新しい全パッケージスキャンの合格と扱わない。稼働中のWeb定義55のimageや外部MariaDBサーバーへ判定を拡張しない。

## 公式修正が変更するコード

| 指摘 | 公式の修正箇所 | 配布物との対応 |
| --- | --- | --- |
| [CVE-2026-85746](https://security-tracker.debian.org/tracker/CVE-2026-85746) | [公式patch 5c04ca5](https://github.com/MariaDB/server/commit/5c04ca5524385356ff7cf84974a7d491974c1f85)の製品変更は`sql/spatial.cc`。GeometryCollectionのWKT変換で出力容量を扱うサーバー実装 | Connector/Cのソース・ビルド対象に当該実装がない |
| [CVE-2026-92262](https://security-tracker.debian.org/tracker/CVE-2026-92262) | [公式patch f277eef](https://github.com/MariaDB/server/commit/f277eefa424850a8cba5c2371406047f6395e8bb)は`sql/`の11ファイルと`storage/mroonga/`・`storage/myisammrg/`の2ファイル。サーバーの表名・ファイル名処理を変更。[後続574ba66](https://github.com/MariaDB/server/commit/574ba66b2d6c5d71db83d416677876e9b592858e)はテストのみ | Connector/Cのソース・ビルド対象に当該実装がない |

[MariaDB公式の85746の告知](https://github.com/MariaDB/server/security/advisories/GHSA-8fvj-c57c-pggx)と[92262の告知](https://github.com/MariaDB/server/security/advisories/GHSA-65jj-h265-3m7h)は、11.8系の修正版を11.8.9としている。Debian trackerはtrixieのsource package `1:11.8.6-0+deb13u1`をvulnerableと表示している。source package全体の表示と、実際に入っているclient binaryの内容を区別して調べた。

## 実施した照合

1. 固定image内のdpkg情報・ファイル一覧から、MariaDB関連は上記2パッケージであることを確認した。`mariadbd`/`mysqld`の実行ファイルと`/usr/lib`配下のembedded server library `libmariadbd*.so*`はなかった。`mariadb-common`の内容は設定と文書で、サーバー実装ではない。
2. Debian公式poolの同じ版の[libmariadb3 amd64 package](https://deb.debian.org/debian/pool/main/m/mariadb/libmariadb3_11.8.6-0+deb13u1_amd64.deb)を読み取りで取得した。配布物の`libmariadb.so.3`と認証plugin6件、計7個のELFファイルがすべて公式package内の同じファイルとSHA256一致した。
3. ELFのDT_NEEDEDを確認した。7個の直接依存先はlibz/libssl/libcrypto/libc/ローダーで、MariaDB server/embedded server libraryへの依存はなかった。サーバーの不在だけで結論を出さず、次のソースとビルド定義も照合した。
4. [Debianの正確な版のsource](https://sources.debian.org/src/mariadb/1%3A11.8.6-0%2Bdeb13u1/)を取得した。元source archiveとDebian追加archiveは、同版の[公式dsc](https://deb.debian.org/debian/pool/main/m/mariadb/mariadb_11.8.6-0+deb13u1.dsc)に記載されたサイズ・SHA256に一致した。ダウンロードしたコードは実行・インストールしていない。
5. rootのCMake→`cmake/mariadb_connector_c.cmake`→`libmariadb/`の構成を読んだ。Connector/Cは独立したsource directoryを設定し、`libmariadb/libmariadb/CMakeLists.txt`がclientのsourceからobject libraryと`libmariadb`を作る。該当する`sql/`・`storage/`の修正ファイルはこの構成に含まれない。
6. Connector/C配下のC/C++/header/CMake計269ファイルを照合し、当該WKT変換・旧表名処理の実装を含まないことを確認した。Debian patch seriesの11件はConnector/Cの変更を含まず、全diff headerも確認した。`debian/libmariadb3.install`の出荷先はclient shared libraryと上記6pluginで、実imageの内容と対応した。

主要なハッシュは次のとおり。sourceの再ビルドによる再現性検証と、dsc/元archiveのPGP署名検証は行っていない。公式HTTPS経由のartifactと明示したハッシュ・ビルド定義の照合であり、供給網全体の保証ではない。

| artifact | SHA256 |
| --- | --- |
| `libmariadb3_11.8.6-0+deb13u1_amd64.deb` | `b2a2d1cdf7493c75d43916a18947700740964513ff5ff603cf5cbbf61e9e6385` |
| image内`libmariadb.so.3`（公式packageと一致） | `d283268434adf3cc3ffcb0580b384f3e13c91bd24b58114022073694dbcc2928` |
| `mariadb_11.8.6.orig.tar.gz` | `b126581a8ca89376d2a3ce63fee97c114c3e15315345e769b9d00c51e1b7d619` |
| `mariadb_11.8.6-0+deb13u1.debian.tar.xz` | `84da78759f1de6452e19cbc24eaa3855ed352fc9306eb12fa9c8f30832d1613b` |

## 残る公開条件

この2件に対する固定image内の適用範囲の判断だけでは、Q04や正式公開条件は完了しない。ほかの指摘、zlib等のHigh、Twisted RC2、最新の全パッケージ監査、AWS実行経路・実データ/配送/権限の検証は引き続き必要である。指摘のseverityを変更したり、scannerへignoreを追加したり、修正のないパッケージをsid等から混入させたりはしていない。

image・依存package・native plugin・ビルド設定が変わった場合は、この判定を再使用せず再確認する。将来MariaDB serverやembedded serverを導入する場合にも再判定が必要である。最新main・共有DBの適用・Web/背景処理反映・課金/外部連携・復旧/性能・運用を含む[正式公開の受け入れ条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を維持する。

本変更は調査文書だけで、DB・AWS・IAM/Secrets・費用・外部通知を変更しない。文書の復旧はrevert PRで行える。ローカル証拠は`tmp/mariadb-debian-provenance-20261030/`のbuild-source-map.json/client-binary-scope-proof.jsonと、`tmp/mariadb-critical-official-patch-map-verified-20261030.json`に保持している。無視対象の調査artifactはGitへ含めない。
