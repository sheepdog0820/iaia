# ONNX Runtimeの配布物・依存ソース照合と未確認範囲（2026-10-31）

正式公開は **No-Go**。PR #41のsource `a78d15bf20cf4ac0fe6e050e72484fb7ef69fb4e` / 通常image `sha256:7d5dfc5a87b25d17cf0843864e35baeb1d95e7066bb4cb5dec5099f5e807018d`について調べた。OS監査52指摘（C2/H9/M6/L35）・exit2と、PBDS由来HIGHの未解決状態を維持する。この調査はCVEの解消判定ではない。

## 実配布物と公式wheelの対応

実imageのONNX Runtimeは1.29.0。ネットワークなし・root read-onlyで取得したmetadataとnative ELFを、[PyPI公式metadata](https://pypi.org/pypi/onnxruntime/1.29.0/json)が指す`onnxruntime-1.29.0-cp311-cp311-manylinux_2_28_x86_64.whl`と照合した。wheelは23,113,193 bytes、SHA256は`85f8e8406c52658735fe5c7fbfd3ebaa1ed340768324f6252e4274e374580a23`で、候補のruntime lockにも含まれる。

| image内のnative ELF | SHA256（公式wheel内と一致） |
| --- | --- |
| `onnxruntime/capi/libonnxruntime.so.1.29.0` | `8902e52a04bf6bf26f1613746811d6194f9c97ce7a6a7a28452b48522d3bd8d0` |
| `onnxruntime/capi/libonnxruntime_providers_shared.so` | `086ec1d5388f64153d9c63470d126693db9a182c8ce236d3a1119068471b8a0d` |
| `onnxruntime/capi/onnxruntime_pybind11_state.cpython-311-x86_64-linux-gnu.so` | `a434baf53b7eba95c0c819eb67505099d9c8027e1fce4f3e25a0a368bc01045b` |

実artifactのbuild infoは`git-commit-id=2e2543fbe9`、Releaseを示す。対応する[公式commit](https://github.com/microsoft/onnxruntime/commit/2e2543fbe9fae542f921d47a72d21d5a4ef0b710)の完全SHAは`2e2543fbe9fae542f921d47a72d21d5a4ef0b710`で、VERSION_NUMBERも1.29.0だった。これは実wheelの全ビルド入力・引数や再現ビルドの証明ではない。

## 公開ソースと依存取得経路

同commitの公式core archive（277,684,829 bytes、SHA256 `00a7483d894037b23e5f2a7d9b18c4026e3585e2636b316cd2870b6e1bc660cb`）を取得し、代表3ファイルをGitHubのGit blobと照合した。全regular file10,863件・572,109,914 bytesを静的に読み、`pb_ds`、`__gnu_pbds`、`binary_heap_tag`、`extc++.h`のliteralは見つからなかった。archiveはGit submoduleの中身を含まないため、この件数を依存全体の件数とは扱わない。

[公開Linux packaging script](https://github.com/microsoft/onnxruntime/blob/2e2543fbe9fae542f921d47a72d21d5a4ef0b710/tools/ci_build/github/linux/build_linux_python_package.sh)は`--use_vcpkg --use_vcpkg_ms_internal_asset_cache`を渡す。`--x-asset-sources`の設定はsource assetのcacheを示し、コンパイル済みbinary cacheを使用した証拠ではない。非公開cacheへのアクセスは試みていない。

[vcpkg設定](https://github.com/microsoft/onnxruntime/blob/2e2543fbe9fae542f921d47a72d21d5a4ef0b710/cmake/vcpkg-configuration.json)のregistry baselineは`18a4723aeb7adbbae84bcff0edf510883800f32f`。11 overlay portとversion overrideを確認し、registryの選択版をversions表のGit tree・各blobのSHAと照合した。たとえばflatbuffersはbaselineの25.12.19ではなくoverrideの23.5.26、benchmarkは1.9.5ではなく1.9.4を調べた。`cmake/deps.txt`だけを全依存の一覧とは扱わない。

選択した公開レシピに対し、直接・任意feature・孫依存を含む計28 archiveのSHA512を検証した。対象はBoost config/mp11/cmake/headers、cxxopts、date、GSL、JSON、re2、SafeInt、flatbuffers、benchmark、abseil、telemetry、cpuinfo、dlpack、Eigen、ONNX、protobuf、pthreadpool、pybind11、XNNPACK、curl、gtest、mbedtls、sqlite3、fxdiv、zlib。全regular file38,527件・448,000,123 bytes、およびレシピ等134ファイル（patch36件を含む）に上記literalは見つからなかった。任意featureのsourceも含めた調査集合であり、28件すべてが実wheelへ組み込まれたという意味ではない。

Eigenの初回取得はローカル`PermissionError`で中断した。元の失敗記録を保持して同じGitLab公式URLを別のローカルファイルへ取得し、レシピのSHA512と一致した。checksum不一致やmirrorでの回避として記録しない。pybind11はレシピが指定するZIPを使い、別形式のarchiveのhashで代用していない。

## 残る確認と公開条件

- 実wheel製造runの全引数、compiler/sysroot/header、生成・注入される入力は未検証。公開標準レシピの確認だけで、実際のすべての入力を確定できない。
- submoduleの有効経路を確認する。coreのlibprotobuf-mutator/emsdk、telemetryの`lib/modules`やテスト依存、protobufのテスト依存、mbedtlsのframeworkなどは、宣言の存在と実際のcompile対象を分けて確認する。
- vcpkg以外のFetchContent・fallback経路、optional provider/featureを、実ビルドで使用したか除外したかは未確定。WebGPU向けDawnは未調査として残す。
- 文字列の不在だけでは、macroや生成コード、別の入力、取り込まれたheaderを否定できない。ONNX Runtimeの3 ELFについても、PBDSへの非該当を完了としない。他のnative ownerとOS側consumerも対象に残す。

[MySQLdbの限定的なC99ビルド経路の判断](MYSQL_NATIVE_PBDS_BUILD_SCOPE_2026-10-30.md)をONNX Runtimeへ流用しない。267 ELF/22 ownerの棚卸し、OS52指摘、Q04と[全25受け入れ条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を継続する。ignore/VEX/除外・severity変更や依存機能の削除は行っていない。

今回の変更は調査文書のみ。source/setup/CMakeの実行、製品コード・lock・imageの変更、DB・AWS・IAM/Secrets・費用・外部通知の変更はない。文書の数値/hash・リンク・UTF-8/LF・差分を確認した。文書変更のためのアプリ全体テストやimage再buildは実施しない。復旧は文書のrevert PRで可能。

Git管理外の証拠は`tmp/ort-native-provenance-20261030/`の`locked-wheel-core-source-proof.json`、`complete-core-byte-scan-proof.json`、`vendor-scope-proof-20261031.json`、version tree/blob、各archiveと取得/検証記録に保持する。大きなarchive・バイナリ・調査出力はGitへ含めない。
