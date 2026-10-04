# native配布物の公開署名とビルド由来の追加調査（2026-10-04）

## 結論・固定対象

[native配布物照合](RUNTIME_NATIVE_PROVENANCE_2026-10-04.md)の後続。現在のアプリ候補 `3492d3d381d7ccdd0744eee774b479f7f9b831cf` の通常image `sha256:9f5a3c0bb4ee0d7c6f9922fc7e619d7b1285af717b798048a40a00e0291df275` を対象に、llvmliteの公開署名とnative bytesの一致を検証した。

固定wheelの署名・公開元・ハッシュを確認し、LLVM/GCCの公開ビルドログへ辿れた。ただし公開署名は完全なビルド来歴やPBDS非該当を証明しない。ONNX Runtimeの同じ仕組みによる証明は提供されておらず、他のnative依存のビルド閉包も未完了。39指摘（HIGH2/MEDIUM2/LOW35、Python0）と正式公開 **No-Go** を維持し、抑制・リスク受容・独自ランタイム置換をしない。

## 修正版の有無

同じ固定imageの使い捨てrootコンテナで、既存のDebian配布元へ署名検証付きapt-get updateを行った。libstdc++6/libgcc-s1/libgomp1はinstalled/candidateとも `14.2.0-19` で、新しい候補はない。配布imageやAWSへパッケージを追加・更新していない。

一次情報の[PBDS指摘](https://security-tracker.debian.org/tracker/CVE-2026-102010)と[aligned new指摘](https://security-tracker.debian.org/tracker/CVE-2026-95619)もgcc-14/trixieをvulnerable/unfixedとしている。修正できたという結論や、別distroへの移行を根拠なく採用しない。

## llvmlite公開署名の検証

対象は `llvmlite-0.49.0-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`。PyPI版別metadataのarchive SHA-256が既存requirements.lockに含まれ、TLS検証付きのfiles.pythonhosted.org取得後のSHA-256とも一致した。ダウンロードしたLinux wheelをWindowsやアプリへインストール・実行していない。

[PyPI Integrity API](https://docs.pypi.org/api/integrity/)は対象wheelにHTTP200、attestation bundle 1件を返した。publisherはGitHub `numba/llvmlite`、workflow `upload_packages.yml`、environment `pypi`。statementのsubjectは対象filenameと固定SHA-256、predicateTypeはpublish/v1・predicateはnull。

[公式の消費手順](https://docs.pypi.org/attestations/consuming-attestations/)に従い、アプリ用環境とは別の検証venvへpypi-attestations 0.0.30 / sigstore 4.5.0を導入した。pip checkは終了0。offline/stagingを使わず、通常の検証器で取得済みprovenance・固定wheel・期待repositoryを渡した。

```text
pypi-attestations verify pypi --repository https://github.com/numba/llvmlite --provenance-file llvmlite-provenance.json <固定wheel>
```

- 正しいwheelと期待repository: `OK`、終了0。
- 同じwheelで期待repositoryをmicrosoft/onnxruntimeへ変更: repository不一致で終了1。
- 元wheelを保持し、同じfilenameの別内容の合成ファイルを与える: subjectとdistribution digest不一致で終了1。このファイルは利用可能なwheelではない。

証明書のSANは `https://github.com/numba/llvmlite/.github/workflows/upload_packages.yml@refs/heads/main`。署名検証後の証明書claimに公開commit `5d881fd159581b97cd8221029ed3b1e50203e32e` と[公開run 31511294686](https://github.com/numba/llvmlite/actions/runs/31511294686)があり、runのhead SHA・workflow_dispatch・成功と一致した。

現在候補のllvmlite nativeファイルと署名検証済みwheel内の同ファイルを直接比較し、SHA-256一致を確認した。先行のRECORD/公開wheel照合のbytesとも一致する。実importの報告するLLVM versionは22.1.0。これらの確認だけを他パッケージや全ABIへ拡張しない。

## 公開ログと完全なビルド証明の区別

[公開commitのworkflow](https://github.com/numba/llvmlite/blob/5d881fd159581b97cd8221029ed3b1e50203e32e/.github/workflows/upload_packages.yml)は別runのartifactsを取得して公開する。公開commitをwheelコンパイル時のソースcommitと取り違えない。

公開runのFind Workflow Runsジョブログはtag `v0.49.0` のLinux-64ビルドrun `31462634019` を選択した。Download Artifactsログに対象cp311 wheel名がある。[そのビルドrun](https://github.com/numba/llvmlite/actions/runs/31462634019)はhead `b5a0ba74ae0601806c0ac3964d746f6be5f6d7b4`、tag v0.49.0、成功。cp311 build job `93689064415` から次を確認した。

- manylinux image取得digest `sha256:0a42cb7e5f4ba6bbfb8d0a86d1aab0c8876ba9c3be16bd99360ae42bf010ec77`。
- conda選択はnumba/label/llvm_wheelの `llvmdev-22.1.0-manylinux_1`。
- C/CXX compilerはGNU 10.2.1、devtoolset-10のcc/c++。
- 対象filenameのビルドとauditwheel処理。

固定commitの[ビルドworkflow](https://github.com/numba/llvmlite/blob/b5a0ba74ae0601806c0ac3964d746f6be5f6d7b4/.github/workflows/llvmlite_linux-64_wheel_builder.yml)と[build script](https://github.com/numba/llvmlite/blob/b5a0ba74ae0601806c0ac3964d746f6be5f6d7b4/buildscripts/manylinux/build_llvmlite.sh)も参照した。ビルドartifact一覧は現在0件で、元ビルドartifactのbytes/コンパイル全ログと公開wheelまでの独立再現照合はしていない。LLVM conda packageの完全なソース/ヘッダー・PBDS利用条件・全従属ライブラリの閉包は未確認。

[publish/v1の公式仕様](https://docs.pypi.org/attestations/publish/v1/)は公開元と配布物の対応を扱う。今回はSLSA build provenanceではなく、ソース全体・compiler headers・再現可能ビルド・脆弱性不存在の証明にしない。上記のログ連鎖は追加のビルド由来の証拠として保持し、完全な署名付きビルド閉包とは区別する。

ONNX Runtimeの対象 `onnxruntime-1.29.0-cp311-cp311-manylinux_2_28_x86_64.whl` へのIntegrity APIはHTTP404・No provenance available。通信切れや署名検証成功として扱わず、このAPIで証明が得られないことだけを記録した。先行のwheel bytes一致を否定するものでも、危険な配布物と断定するものでもない。

## 証跡・影響・残作業

証跡/工具は `C:/tmp/iaia-native-build-provenance-20261004` と専用venv `C:/tmp/iaia-attestations-venv-20261004`。wheel/JSON/工具はGit・配布imageへ含めない。

| 対象 | SHA-256 |
| --- | --- |
| 固定llvmlite wheel | a8c0fc9d624bdc30a3d2db11eb2fb98f80fb209d20b37604eda516cd9b699cf4 |
| llvmlite-provenance.json | fee721898f0c8c80005389478b87e5129f771528cb3862966917d28596ff0bc5 |
| llvmlite/binding/libllvmlite.so | 90829145327c8c37ee7a3494e3b20161343efc3357537d558cb006014a1b0f12 |

今回の変更は検証記録のみ。アプリ・image・main/AWS・共有DB/実データ・Secrets/IAM・課金/費用/常設容量を変更していない。調査コンテナは--rmで削除済み。元checkoutのハンドアウト差分は保持する。文書の復旧は証拠コミットのrevertで行える。

候補3492d3d3の[CI全6項目success](https://github.com/sheepdog0820/iaia/actions/runs/37185332518)を追加確認したが、39指摘、PBDS/他native閉包、実AWS/課金/外部連携、総合性能/復旧/運用の未達は残る。既存の6b6c570c反映案やfavicon承認へ後続変更を追加せず、[正式公開No-Go](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を維持する。
