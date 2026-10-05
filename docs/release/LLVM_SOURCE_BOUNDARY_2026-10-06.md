# LLVM native依存の同梱レシピ・ソース調査（2026-10-06）

## 結論と確認範囲

[先行ビルド調査](NATIVE_BUILD_ATTESTATION_2026-10-04.md)でllvmlite wheelのビルドログに記録された `numba/label/llvm_wheel::llvmdev-22.1.0-manylinux_1` の公開archiveを取得し、全体SHA-256と同梱レシピを確認した。同梱レシピが指定するLLVM 22.1.0公式source archiveも全体ハッシュ一致を確認し、通常ファイル168,946個の内容を走査した。PBDS関連の4文字列の一致は0件。検出器の正例・ハッシュ不一致の負例も確認した。

これは外部LLVMソースの確認範囲を増やした証拠であり、コンパイル時の全ヘッダー・生成物・他native依存・完全なビルド閉包を証明しない。指摘抑制・リスク受容・HIGH解消は行わず、正式公開 **No-Go** を維持する。最新の[通常ba51bdd8配布物監査](BACKGROUND_ACTIVE_RUNTIME_BA51BDD8_2026-10-06.md)は39指摘（HIGH3/MEDIUM1/LOW35、Python0）・終了2のまま。今回OS再スキャンはしていない。

## 固定conda archiveと歴史的同一性の限界

[公式Anaconda metadata](https://api.anaconda.org/package/numba/llvmdev)から、linux-64・22.1.0・manylinux_1・label llvm_wheelの候補1件を選定した。[公式取得経路](https://api.anaconda.org/download/numba/llvmdev/22.1.0/linux-64/llvmdev-22.1.0-manylinux_1.conda)はTLS検証を迂回せず使用した。

- archiveは893,725,486 bytes、SHA-256 `c8603c82c26fb6b65c7bace30eaef09ce7287770d8e187ca5c93ec58b53e8c2d`。全体サイズ・ハッシュが取得metadataと一致した。
- metadataのupload_timeは2026-05-27 19:41:48.329000+00:00。同梱indexもllvmdev 22.1.0、manylinux_1、build_number 1を示す。
- 先行wheelビルドログはname/version/buildを示すが、当時取得したconda archive全体のdigestは確認できていない。今回の公開metadataとの一致を、当時使われたbytesの暗号学的同一性や署名付きビルド証明とは扱わない。
- 初回のworkflow別期間検索はconnectorがHTTP400/INVALID_ARGUMENTで拒否した。runが0件、ログが消失、元ビルドが存在しないという証拠ではない。後続のリポジトリ全体run検索と同梱git metadataの確認結果は次節に区別して記録する。

## 後続調査：5月の固定run・レシピ一致・証明できない入力

[リポジトリ全体run検索](https://api.github.com/repos/numba/llvmlite/actions/runs?created=2026-05-26..2026-05-28&per_page=100)は21件を返し、5月26日の[run26481208591](https://github.com/numba/llvmlite/actions/runs/26481208591)を確認した。workflow_dispatch、head `f3dbf3bbd5e7e14d4b1f0ba1b50a217171fbe3ec`、completed/successで、`llvmdev_for_wheel-linux-64` job77978671184のbuild/test・artifact uploadもsuccess。ただし実test内容やコンパイル引数はログを読めていない。翌日のrun26544685751も候補として区別し、同linux-64 job78193975426を確認した。成功statusだけを全test・安全性の証明にしない。

| 記録 | UTC時刻 | 示す範囲 |
| --- | --- | --- |
| 固定run26481208591開始 | 2026-05-26 23:31:21 | GitHub run metadata |
| 同梱rendered recipeのtemplate更新時刻 | 2026-05-26 23:31:36 | archive内の記述、独立した時計保証ではない |
| 同梱indexのtimestamp | 2026-05-27 01:28:18.606 | archive内timestampの変換 |
| 同runのupdated_at | 2026-05-27 02:58:34 | GitHub metadataの更新時刻、厳密なbuild終了時刻とは扱わない |
| Anaconda upload_time | 2026-05-27 19:41:48.329 | 公開metadata、runのartifact bytesとの一致は未確認 |

[固定f3dbf3bbのmeta.yaml](https://github.com/numba/llvmlite/blob/f3dbf3bbd5e7e14d4b1f0ba1b50a217171fbe3ec/conda-recipes/llvmdev_for_wheel/meta.yaml)は同梱templateと完全bytes一致、内容SHA-256 `7afeee4c8af5995ee1ca8d1ffada1bed980670e910c4ee1dcfbb7cfc9aa5e2f9`。[同build.sh](https://github.com/numba/llvmlite/blob/f3dbf3bbd5e7e14d4b1f0ba1b50a217171fbe3ec/conda-recipes/llvmdev_for_wheel/build.sh)も同梱scriptと完全bytes一致（ad876fcf…）。これで後のb5a0ba74と異なるレシピの固定ソースを特定したが、同じレシピを使う他runや再ビルドの可能性を排除しない。上の時刻対応だけで、今回archiveがこのrunから公開されたと断定しない。

対象2ジョブの実ログ取得はGitHub API HTTP410。run26481208591の現在artifact一覧は0件。元artifactのbytes/digest、manylinux imageの当時digest、実compiler/header/全コマンドは取得できず、取得失敗を成功や脆弱性不存在へ読み替えない。

[固定workflow](https://github.com/numba/llvmlite/blob/f3dbf3bbd5e7e14d4b1f0ba1b50a217171fbe3ec/.github/workflows/llvmdev_build.yml)はlinux-64でquay.io/pypa/manylinux2014_x86_64のtagを使い、digest固定がない。Minicondaのversion付きfilenameを指定するが、[準備script](https://github.com/numba/llvmlite/blob/f3dbf3bbd5e7e14d4b1f0ba1b50a217171fbe3ec/buildscripts/manylinux/prepare_miniconda.sh)にinstallerのハッシュ検証はない。[LLVM生成script](https://github.com/numba/llvmlite/blob/f3dbf3bbd5e7e14d4b1f0ba1b50a217171fbe3ec/buildscripts/manylinux/build_llvmdev.sh)のconda/conda-buildもversion指定なし。workflowの「Upload conda package」はGitHub artifactへのuploadで、Anacondaへの公開そのものではない。これらの可変入力を現在tagや現在solverで再実行して当時の閉包とすることはできない。外部workflowのdispatch・publish・再ビルドは行っていない。

追加のread-only/通信禁止/256 MiB・1 CPU/--rmコンテナで、既に固定した全archiveとinfo tarのハッシュを再照合し、`info/git` と `info/test/run_test.sh` だけを読んだ。info/gitは空文字列（0 bytes、空SHA-256 e3b0c442…）で、ソースcommitやcompiler識別子は得られない。test scriptはllvm-config/llc・3ファイル存在・ld.lld確認で、今回は実行していない。pkg payload・sourceの展開/実行・インストールはしておらず、調査コンテナ終了を確認した。前回reader/証跡は変更せず、新reader/結果を別ファイルへ保持する。

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

前回の文書関連39 test成功（0.063秒）、変更2文書の相対参照202件/欠落0、当時の10ハッシュ一致、差分確認成功。自己レビューで修正を要する指摘なし、ステージ済み2文書もUTF-8/LF/BOMなしの検査に成功した。今回の後続追記も文書関連39 test成功（0.036秒）、相対参照202件/欠落0、21ハッシュ一致、差分確認成功。時刻/recipe一致を来歴の断定へ拡張しない観点で自己レビューし、修正を要する指摘なし。ステージ済み2文書のUTF-8/LF/BOMなし・差分検査も成功した。アプリ/UI表示変更はなく、今回アプリ全体testやブラウザー確認は行わない。今回commitのCIを確認前に全成功とは扱わない。HIGH/全native閉包・実課金/共有運用/外部連携・AWS性能/復旧/事業者運用の不足は維持し、既存main/AWS承認の対象へこの後続変更を追加しない。

## 保持証跡

保存先は `D:/tmp/codex-tableno-llvm-source-20261006`。大容量archive・取得metadata・工具・ログはGit外に保持する。

| ファイル（GitHub file取得responseはcontent/encoding/SHA等を含むJSON wrapper） | 保存ファイルのSHA-256 |
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
| llvm-history-runs.json | bc1e3b12fed90150a8c3cfaca74a4e8d71c08ce5a35151f17e15bb77456b6e72 |
| llvm-run-26481208591.json | c89bea0b5acb51845ca73fb2d255d2fde9b8f9711f4d31eac88e694fc1bea794 |
| llvm-run-26481208591-jobs.json | 6d93a837ed290433d6c7c29ed064d66a301723bd1223057116c1c873fd44ed89 |
| llvm-job-77978671184-log-response.json | 904a0a642399a924721227f01103ed8ac2d2978780b4110e0e24918775f6fcd7 |
| llvm-artifacts-26481208591.json | fb09a9699b26ad536855bb4263ff01baa31a107d9af48b348e96cb4a9eb2b8d9 |
| llvm-workflow-f3dbf3bb.json | 6346643f7665158abd715ed44bb255ef40f58465e970b36e9b9572e148b4fd6a |
| meta-f3dbf3bb.yaml | 9a54c3153d5b6e9abe1f27674b79646b0fb97972030d245741af44d068a09659 |
| build-f3dbf3bb.sh | b57099e37a246e9297aec9992991a2323dc76a7b2023080c24c8268a1a5345c1 |
| prepare-miniconda-f3dbf3bb.json | 58cbc7394695c1adfc0f0e5e715998c71a4f3dd7e62c24734a83d423789e85c1 |
| read_conda_git.py | f9d6bf9cd794925f4e560f6f11a84505012115016f8ee8945906a339d8dc8cdb |
| conda-git-read.json | 662e2c74a3eaddd0d480f198bcc85e9828971f9cbe9e45e6dd0e7eeadec1f5a6 |
