# LLVM native依存の同梱レシピ・ソース調査（2026-10-06）

## 結論と確認範囲

[先行ビルド調査](NATIVE_BUILD_ATTESTATION_2026-10-04.md)でllvmlite wheelのビルドログに記録された `numba/label/llvm_wheel::llvmdev-22.1.0-manylinux_1` の公開archiveを取得し、全体SHA-256と同梱レシピを確認した。同梱レシピが指定するLLVM 22.1.0公式source archiveも全体ハッシュ一致を確認し、通常ファイル168,946個の内容を走査した。PBDS関連の4文字列の一致は0件。検出器の正例・ハッシュ不一致の負例も確認した。

これは外部LLVMソースの確認範囲を増やした証拠であり、コンパイル時の全ヘッダー・生成物・他native依存・完全なビルド閉包を証明しない。指摘抑制・リスク受容・HIGH解消は行わず、正式公開 **No-Go** を維持する。最新の[通常ba51bdd8配布物監査](BACKGROUND_ACTIVE_RUNTIME_BA51BDD8_2026-10-06.md)は39指摘（HIGH3/MEDIUM1/LOW35、Python0）・終了2のまま。今回OS再スキャンはしていない。

## 固定conda archiveと歴史的同一性の限界

[公式Anaconda metadata](https://api.anaconda.org/package/numba/llvmdev)から、linux-64・22.1.0・manylinux_1・label llvm_wheelの候補1件を選定した。[公式取得経路](https://api.anaconda.org/download/numba/llvmdev/22.1.0/linux-64/llvmdev-22.1.0-manylinux_1.conda)はTLS検証を迂回せず使用した。

- archiveは893,725,486 bytes、SHA-256 `c8603c82c26fb6b65c7bace30eaef09ce7287770d8e187ca5c93ec58b53e8c2d`。全体サイズ・ハッシュが取得metadataと一致した。
- metadataのupload_timeは2026-05-27 19:41:48.329000+00:00。同梱indexもllvmdev 22.1.0、manylinux_1、build_number 1を示す。
- 先行wheelビルドログはname/version/buildを示すが、当時取得したconda archive全体のdigestは確認できていない。今回の公開metadataとの一致を、当時使われたbytesの暗号学的同一性や署名付きビルド証明とは扱わない。
- 過去workflow runの期間検索はconnectorがHTTP400/INVALID_ARGUMENTで拒否した。runが0件、ログが消失、元ビルドが存在しないという証拠ではない。LLVM conda buildの固定run・全コンパイルログは未確認。

## 同梱レシピと後のwheelソースを区別する

ZIP内のinfo tar.zstだけを読み、index・rendered recipe・template・build.sh・build config・about・hash inputを保持した。pkg payloadの展開・実行・インストールはしていない。metadata readerは重複名、絶対/親パス、サイズ超過を拒否し、compressed info 16 MiB・展開buffer 64 MiB・選定text member 4 MiBを上限とする。既存imageのlibzstdを使い、新しいnative工具を導入していない。

| 比較対象 | build | active patches |
| --- | --- | --- |
| 今回取得archiveの同梱rendered recipe/template | manylinux_1 / build_number 1 | rendered recipeはnull、templateはコメントのみ |
| [wheelビルド固定commit b5a0ba74のrecipe](https://github.com/numba/llvmlite/blob/b5a0ba74ae0601806c0ac3964d746f6be5f6d7b4/conda-recipes/llvmdev_for_wheel/meta.yaml) | manylinux_0 / build_number 0 | Windows AArch64 target detection patch参照あり |

同じLLVM versionでも、後のwheel側ソースrecipeを以前のnative archiveの完全な設定として代用しない。一方、同梱build.shと[固定commitのbuild.sh](https://github.com/numba/llvmlite/blob/b5a0ba74ae0601806c0ac3964d746f6be5f6d7b4/conda-recipes/llvmdev_for_wheel/build.sh)はbytes同一、SHA-256 `ad876fcf53a2ce5ade849e487510d364b29bc95a7bac96f9d4ca44be3d74d436`。

build.shはlld/compiler-rt、Linux64 Intel JIT events、FFI/assertionsを有効にし、ZSTD/LIBEDIT/LIBXML2/RTTI/TERMINFO等を無効にする。build前にAddLLVM.cmakeへ2回のsed変換も行うため、patches:nullを「ソース完全無変更」とは扱わない。ninja/installと一部testを指定するが、今回はビルドも上流testも実行していない。scriptのignore-fail/filter設定を全test合格の証拠にしない。

同梱recipeはconda-build 26.1.0、aboutはconda 26.5.0。build/host metadataにlibffi 3.4.4、libzlib/zlib 1.3.1、libgcc-ng/libstdcxx-ng 11.2.0がある。これらはビルド環境metadataで、アプリへ追加した依存ではない。libstdcxx-ngの版を実compiler版と取り違えず、先行wheel compileログのGNU 10.2.1/devtoolset-10とも区別する。LLVM conda buildの実compiler・全header入力は未証明。

## LLVM公式source archiveと検出器の正負確認

同梱recipe指定の[LLVM 22.1.0 source archive](https://github.com/llvm/llvm-project/releases/download/llvmorg-22.1.0/llvm-project-22.1.0.src.tar.xz)は167,040,408 bytes、SHA-256 `25d2e2adc4356d758405dd885fcfd6447bce82a90eb78b6b87ce0934bd077173`。全体ハッシュはrecipeと[公式release asset metadata](https://api.github.com/repos/llvm/llvm-project/releases/tags/llvmorg-22.1.0)のdigestに一致した。releaseの署名/attestation自体は取得・検証しておらず、checksum照合を署名付き来歴や再現可能ビルドと表現しない。

通信禁止・read-only・512 MiB/1 CPU・--rmの専用コンテナで、tar.xzを展開せずstreamingで読む。全archive member 184,760、通常ファイル168,946、通常内容2,023,461,242 bytesを走査。拡張子で限定せず、binary/textの両方を1 MiB chunk・64 bytes overlapで読み、`__gnu_pbds`・`ext/pb_ds`・`binary_heap_`・`erase_fn_imps.hpp` のliteral byte列を検索した。一致ファイル0、CLI終了0。19個のlinkは追跡せずpath/targetを証跡へ記録した。

| 制御ケース | 結果 |
| --- | --- |
| 合成通常ファイル2個、chunk境界を跨ぐ文字列・binary内文字列、外部向きlink1個 | 全4文字列を2ファイルで検出、linkを読まず、終了0 |
| 同じ合成archiveに不一致のexpected SHA-256を与える | Complete LLVM source digest mismatchで拒否、CLI終了1 |
| 固定公式source archive | 全体SHA再照合・全通常ファイル走査成功、文字列一致0、終了0 |

負例のshell全体も終了1を返した。期待する拒否を確認した結果であり、アプリの失敗やshell終了0として報告しない。literal不在はマクロ/生成code/forced include/実compiler headers/ビルド引数を解決する解析ではない。未追跡link・外部依存・他nativeパッケージにも結果を拡張せず、PBDS非該当は未確定とする。

## 影響・検証・復旧

今回repoへ変更するのはこの証跡文書と[受け入れ条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)のみ。アプリ・依存lock・image・main/AWS・共有DB/実データ・Secrets/IAM・課金/継続費用/常設容量・外部通知を変更しない。調査は既存の通常ba51bdd8 imageを使用し、専用--rmコンテナは終了済み。archive/sourceをアプリやGitへ含めず、旧監査cache・証跡を削除しない。元checkoutの無関係な差分は保持する。文書の復旧は証跡commitのrevertで可能。

文書関連39 test成功（0.063秒）、変更2文書の相対参照202件/欠落0、下表10ハッシュ一致、差分確認成功。自己レビューで修正を要する指摘なし。ステージ済み2文書もUTF-8/LF/BOMなしの検査に成功。アプリ/UI表示変更はなく、今回アプリ全体testやブラウザー確認は行わない。今回commitのCIを確認前に全成功とは扱わない。HIGH/全native閉包・実課金/共有運用/外部連携・AWS性能/復旧/事業者運用の不足は維持し、既存main/AWS承認の対象へこの後続変更を追加しない。

## 保持証跡

保存先は `D:/tmp/codex-tableno-llvm-source-20261006`。大容量archive・取得metadata・工具・ログはGit外に保持する。

| ファイル | SHA-256 |
| --- | --- |
| llvmdev-package-metadata.json | 758f266fbb50359b65e1fac21176adc50891b1757c8b75e3fc211818218f405c |
| llvmdev-22.1.0-manylinux_1.conda | c8603c82c26fb6b65c7bace30eaef09ce7287770d8e187ca5c93ec58b53e8c2d |
| conda-info-read.json | e96393f68a072a621f1fbd9cf4d87657bb8cac892a5b590b5e78a4af182d0595 |
| llvm-project-22.1.0.src.tar.xz | 25d2e2adc4356d758405dd885fcfd6447bce82a90eb78b6b87ce0934bd077173 |
| llvm-source-marker-scan.json | dff8295af26fe82223343e9ce12b2cb6ba4a5eef73ff0bff2b684cd3dc9fc740 |
| scanner-positive-control.json | cff27abb451a01a29c02a24312bf685c0e8911f38f03c8d67c7f276f48cc7f6f |
| scanner-negative-control.log | d26bc4e3bf88a1663b11de16dff4a27b7df28f6abf29041c7d7ce4355c99f7a1 |
| read_conda_info.py | bf0799ec1a44b6fc5acd980e02c00fa2419664fa6bcae54eb3c1d17d111d2232 |
| scan_llvm_source.py | ae5be2ff50348d927163627f4a26a16a51bcbc4d3a5e4d176278666eb51347b4 |
| llvmdev_for_wheel-meta-b5a0ba74.yaml | 94cb6f08a8b657a2d87be0397a372dd20f21e988f52b1007e1b0f069d964529e |
