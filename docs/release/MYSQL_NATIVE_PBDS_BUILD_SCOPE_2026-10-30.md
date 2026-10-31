# MySQLdb拡張のビルド情報とPBDS調査範囲（2026-10-30）

正式公開は **No-Go**。統合候補PR #41のsource `a78d15bf` / 通常image `sha256:7d5dfc5a87b25d17cf0843864e35baeb1d95e7066bb4cb5dec5099f5e807018d`を調べた。OS監査の52指摘（C2/H9/M6/L35）・exit2は未除外のまま保持し、配布物全体のPBDS由来HIGHを解決済みとは扱わない。

## 調べた理由と結果

先行候補297a217dの通常image0fe931f7との照合で、native ELF267件のうちMySQLdbの1件だけはファイルのSHA256が異なっていた。その差分を未確認のまま同一バイナリと扱わず、固定した両imageからこのファイルだけを読み取りで取得した。アプリ・DB・AWSへ接続せず、既存imageをネットワークなし・root read-onlyで参照した。

対象は`/usr/local/lib/python3.11/site-packages/MySQLdb/_mysql.cpython-311-x86_64-linux-gnu.so`。候補内の配布metadataはmysqlclient2.2.8、wheel tagは`cp311-cp311-linux_x86_64`だった。

| 対象 | SHA256 |
| --- | --- |
| 先行image0fe931f7のMySQLdb拡張 | `13444a982d7ef858e2005a04990662447f0ba54f0b70a7031060032ef6006438` |
| 統合image7d5dfc5aのMySQLdb拡張 | `54a832ae51d6c9f6cebc47283fe42a19b1e330a05e862abb9e40a19ae5b5fe6e` |
| 公式sdist `mysqlclient-2.2.8.tar.gz`（92,287 bytes） | `8ed20c5615a915da451bb308c7d0306648a4fd9a2809ba95c992690006306199` |
| 同sdist内`src/MySQLdb/_mysql.c` | `2b58482bedf4553f2f688039bf453ad785cd81080010ccc35b7dcbce27d56f8c` |

ELF64/x86-64の全sectionを名前・type・flags・address・size・内容hashで比較した。異なるのは`.note.gnu.build-id`、`.debug_info`、`.debug_line`、`.debug_line_str`の4件だった。Build IDを除いたSHF_ALLOC付き23セクションは、これらの属性と内容がすべて一致した。`.text`等のロード対象コードの違いは見つからなかったが、ファイル全体のhashが一致したとは報告しない。

## ソース・コンパイル情報との対応

[PyPIの公式release metadata](https://pypi.org/pypi/mysqlclient/2.2.8/json)から同版の[公式sdist](https://files.pythonhosted.org/packages/eb/b0/9df076488cb2e536d40ce6dbd4273c1f20a386e31ffe6e7cb613902b3c2a/mysqlclient-2.2.8.tar.gz)を取得した。サイズとSHA256を照合し、そのhashが候補の`requirements.lock.txt`のmysqlclient2.2.8ブロックに含まれることも確認した。ダウンロードしたsetupコードは実行していない。

- 公式`setup.py`が指定する拡張sourceは`src/MySQLdb/_mysql.c`の1件。POSIXの通常構成はC99 flagを設定し、pkg-configでclient libraryへリンクする。
- 同じsetupには`--static`による別経路があり、その場合はC++を指定する。今回の判断をmysqlclientの全ビルド方式へ拡張しない。
- 実imageのDWARF compilation unitは両方とも1件、言語はANSI C99。producerはGNU C99 14.2.0で、`-std=c99`を含んでいた。line tableにも`_mysql.c`が記録されている。
- 両バイナリのDT_NEEDEDは`libmariadb.so.3`と`libc.so.6`。この実バイナリはclient shared libraryへリンクする経路に対応する。動的依存先にlibstdc++がないことだけを、他のnative部品の安全性の根拠にはしない。
- 取得したnative sourceとbuild定義にPBDSの参照はなく、sourceのincludeはPythonとMySQLのC API/headerだった。文字列検索の不在だけで判定せず、上記のC99のビルド構成・実compilation unit・動的依存先と合わせて評価した。

この固定MySQLdb拡張のビルド経路は、GNU C++ PBDSのbinary heapを直接instantiateする入力には該当しないと判断する。証拠はsource/build定義と実artifactの対応であり、第三者wheel全体のビルド由来の保証・再現ビルド・供給網全体の保証ではない。

## PBDS指摘と残る確認

[GCC公式修正](https://github.com/gcc-mirror/gcc/commit/aaa8351f4d2e636f9680a1f0a8ebc2f0a60611e6)は、`ext/pb_ds/detail/binary_heap_/erase_fn_imps.hpp`の`erase_if`で、再確保後のentry pointerを更新する。ヘッダーのコードはconsumerへ取り込まれるため、コンパイラー/headerの削除や、ELF内のPBDS名の検索だけで安全性を証明できない。[Debian tracker](https://security-tracker.debian.org/tracker/CVE-2026-102010)のtrixie/gcc14.2.0-19はvulnerableの表示を維持している。no-dsaという扱いを公開条件の免除にしない。

残りのnative ELF266件・21配布ownerについて、正確なconsumer source・vendor・build設定の確認は未完了。今回のC99の根拠を、C++/Rust/Fortranを含む別の部品や静的に含まれる実装へ流用しない。OS52指摘全体、Q04、[正式公開の全25条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を継続する。

## 検証・変更範囲・証拠

今回のGit変更はこの調査文書だけ。製品コード・依存lock・Dockerfile・移行・AWS/IAM/Secrets・費用・外部通知は変更していない。文書の差分・文字コード/改行・リンク・hashを確認し、アプリ全体テストはこの文書変更のためには再実行しない。文書の復旧はrevert PRで行える。PR #41のマージと、非公開コピーでの移行リハーサルはそれぞれ別の承認待ちである。

Git管理外の証拠は`tmp/mysql-native-provenance-20261030/`の`binary-comparison-proof.json`、`official-source-build-proof.json`、`candidate-distribution-metadata.json`、両版のdynamic/debug-info/raw-line出力と公式archiveに保持する。ネイティブバイナリ・公式sourceの複製・大きな調査出力はGitへ含めない。再現ビルドは未実施であり、Build IDの差を無条件に無視するscanner設定も追加していない。
