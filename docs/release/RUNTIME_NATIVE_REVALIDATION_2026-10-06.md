# 後続候補のnative配布物・公開署名の再照合（2026-10-06）

## 結論・今回増えた証拠

[先行native照合](RUNTIME_NATIVE_PROVENANCE_2026-10-04.md)と[先行公開署名・ビルド調査](NATIVE_BUILD_ATTESTATION_2026-10-04.md)を、新しい候補の通常配布物へ再照合した。署名方式やビルドログの発見自体は先行確認済みで、今回の新規成果とは区別する。

対象はアプリ `1a738d2a00291520020662f39417b50dcd6e25fd` の[通常配布物](BACKGROUND_PREMIUM_RUNTIME_1A738D2A_2026-10-06.md)、image ID `sha256:9c4e660278d6e468971424a29eea25f9c8712eff43a1a8bdd0320d78513dfff7`。現在のソース候補 `ba51bdd8b7b74e39ae9e8104ab064956dd55262c` の通常imageを検証したという意味ではない。

- site-packages内の267 ELFは全件RECORD一致、所有者不明0・不一致0。
- main8567f49f時点の固定inventoryとのpath比較は欠落0・追加0、SHA-256変更1。266個は同一で、変わった1個はソースビルドのmysqlclient。全267個の再現可能ビルドとは主張しない。
- llvmlite 1個・ONNX Runtime 3個は、今回取得した固定公開wheelの実ファイルと一致。
- llvmliteのpublish attestationを実際に暗号検証し、正しい配布元/内容は成功、異なる配布元と1 byte改変はそれぞれ拒否。
- これは改変・公開元と候補配布物の対応の証拠で、PBDS非該当・CVE解消・完全なビルド閉包の証明ではない。正式公開 **No-Go** を維持する。

## 固定対象と比較境界

既存inventory工具 `C:/tmp/runtime-native-provenance-20261004.py`（SHA-256 `e0d64c44a97706819ff809a4d6a2aac8bf807e5c637a84838351bca3913c2efb`）を変更せず使用。通信禁止・read-only・512 MiB上限・--rmの専用コンテナで通常1a738d2aの実ファイルを読み、終了0。既存imageの更新・nativeコードの追加インストールはしない。

比較元は `C:/tmp/runtime-native-records-8567f49f-20261004.json`（SHA-256 `10b6f6cc7cb3c4c567d4e72eda34639e3aa30aeefbcb0827e2e5174caf0fe4ab`）。変更は `MySQLdb/_mysql.cpython-311-x86_64-linux-gnu.so` のみで、現在のSHA-256は `f811ba57579be76d48bc6e876c349dbff960e2d5256046f9c5b3b7c44a93db9c`。現在RECORDとの一致は確認したが、この差の原因の確定・同一ソースからの独立再現ビルドはしていない。先行の固定Cソース構成の証拠をバイナリ全依存の安全性へ拡張しない。

現在checkoutと通常1a738d2aの `requirements.lock.txt` はSHA-256 `e0bd61d0c1a3159a42a725af07299c05f1d4654a796c76b2f50ec64e1873ec65`。先行mainのlockとは異なる。今回新規に公開wheelを取得したのは下表の2パッケージだけで、21パッケージ全体を再取得したとは扱わない。残る同一ファイルは先行の固定公開wheel照合へ参照する。標準ライブラリ・OSライブラリ・モデル・全native実行ファイルの来歴はこの267個の対象外。

## 固定公開wheel・実ファイル

PyPI版別metadataからインストール済みWHEELタグに完全対応する候補を各1件に限定。archive SHA-256が既存lockに含まれ、TLS検証付き取得後のハッシュとも一致することを確認した。archiveはZIPとして読むだけで、展開・インストール・実行していない。

| 固定wheel | archive SHA-256 | 現在image内のELF一致 |
| --- | --- | ---: |
| llvmlite-0.49.0-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.whl | a8c0fc9d624bdc30a3d2db11eb2fb98f80fb209d20b37604eda516cd9b699cf4 | 1/1 |
| onnxruntime-1.29.0-cp311-cp311-manylinux_2_28_x86_64.whl | 85f8e8406c52658735fe5c7fbfd3ebaa1ed340768324f6252e4274e374580a23 | 3/3 |

4個のpathとSHA-256は保持した `wheel-comparison.json` にある。配布archiveの一致・インストール済みファイルの一致・公開署名の有無は別の検証項目として扱う。

## 署名の正負検証と公開/ビルドの区別

[PyPI Integrity API](https://docs.pypi.org/api/integrity/)は対象llvmlite wheelへ200、bundle 1件/attestation 1件/transparency entry 1件を返した。subject filenameとdigestは固定wheelと一致。publisherはGitHub `numba/llvmlite`、workflow `upload_packages.yml`、environment `pypi`。predicateTypeはpublish/v1、predicateはnull。

[公式検証手順](https://docs.pypi.org/attestations/consuming-attestations/)に従い、アプリ環境と隔離した外部工具venvへpypi-attestations 0.0.30 / sigstore 4.5.0を導入した。期待repositoryはPyPIの公式Sourceリンクから独立に確認した。offline/staging/TLS・identity迂回なしで、通常の検証器に取得済みprovenanceと固定wheelを渡した。署名の作成・OAuth・認証情報の変更はしていない。

```text
pypi-attestations verify pypi --repository https://github.com/numba/llvmlite --provenance-file llvmlite-provenance.json <固定wheel>
```

| ケース | 検証CLI結果 |
| --- | --- |
| 正しいarchive・期待repository numba/llvmlite | OK、終了0 |
| 同じarchive/bundle・期待repository microsoft/onnxruntime | repository不一致、終了1 |
| 元archiveを保持し、別フォルダーの同名archiveを1 byte改変 | subject/digest不一致、終了1 |

負例のshell wrapperは期待どおりの拒否を確認して終了0としたが、検証CLI自体の終了1とは区別する。改変archiveはアプリや正しいreferenceへ使用しない。取得段階の `provenance-summary.json` にある `signatureVerified: false` は署名未検証のmetadata取得結果で、後続の実検証は専用ログに記録する。

検証済みbundleの証明書claimは公開SHA `5d881fd159581b97cd8221029ed3b1e50203e32e`、repository numba/llvmlite、refs/heads/main、[公開run31511294686/attempt1](https://github.com/numba/llvmlite/actions/runs/31511294686/attempts/1)。GitHub読み取りmetadataの成功・head SHA・workflow pathとも一致した。

[固定公開workflow](https://github.com/numba/llvmlite/blob/5d881fd159581b97cd8221029ed3b1e50203e32e/.github/workflows/upload_packages.yml)は既存wheel artifactsを取得して公開する。公開SHAをwheelコンパイル時のSHAとは扱わない。今回再取得したFind Workflow Runsログもtag v0.49.0・Linux-64 run31462634019を選択し、[ビルドrun](https://github.com/numba/llvmlite/actions/runs/31462634019)はhead b5a0ba74ae0601806c0ac3964d746f6be5f6d7b4・成功。cp311 job93689064415のGNU 10.2.1/devtoolset-10・llvmdev-22.1.0-manylinux_1は先行記録と一致する。ログ連鎖を完全な署名付きビルド閉包・コンパイル時全ヘッダーの証明へ拡張しない。

ONNX Runtimeの対象wheelへのIntegrity APIは404・No provenance available。このAPIで公開署名情報が得られないことだけを確認し、暗号検証の成功/失敗や危険な配布物との断定にはしない。[公式security model](https://docs.pypi.org/attestations/security-model/)に従い、publish attestationの成功を脆弱性不存在の証明にしない。

## OSゲート・CI・影響

今回、全OSスキャン・apt更新・新しい通常imageビルドは行っていない。最新の通常1a738d2a監査は先行記録の39指摘（HIGH3/MEDIUM1/LOW35、Python0）、終了2。一次情報の[PBDS](https://security-tracker.debian.org/tracker/CVE-2026-102010)、[aligned new](https://security-tracker.debian.org/tracker/CVE-2026-95619)、[zlib](https://security-tracker.debian.org/tracker/CVE-2026-85091)も再読時点で対象Debian版をvulnerable/unfixedとする。署名/bytes一致・文字列不在だけでは抑制・受容・修正済みにしない。

先行文書52acfba2の[CI37384706089](https://github.com/sheepdog0820/iaia/actions/runs/37384706089)は全6ジョブcompleted/successを確認。現在ソースba51bdd8の[CI37386076213](https://github.com/sheepdog0820/iaia/actions/runs/37386076213)は照合時点で4成功・Unit/IntegrationとPlaywright実行中。今回証跡コミットのCIや通常ba51配布物・実HTTP/AWSを合格扱いしない。

変更は証跡文書のみ。main/AWS・アプリ・依存lock・image・共有DB/実データ・Secrets/IAM・課金/継続費用/常設容量・通知を変更していない。調査コンテナは--rm終了済み、元checkoutの無関係な13差分は保持。外部工具venv・archive・ログは再調査用に保持し、Gitやimageへ含めない。文書の復旧は証跡コミットのrevertで行える。

文書関連39テスト成功（0.314秒）、変更2文書の相対参照201件/欠落0、下表9証跡ハッシュ一致、差分とステージ済みUTF-8/LF/BOMなしを確認した。自己レビューで修正を要する指摘なし。アプリ/UI表示変更はなく、全体テストやブラウザー確認は今回実行していない。

## 保持証跡

保存先は `D:/tmp/codex-tableno-native-provenance-20261006`。主要証跡のSHA-256は以下。先行工具/証跡も変更・削除していない。

| ファイル | SHA-256 |
| --- | --- |
| native-records-1a738d2a.json | eced44ffb6c9cbf9e08e451d78754659bc33aa634ead26c6e9dea79081f980ee |
| wheel-comparison.json | e94d944a44ee92bf1871161e908c5fb1e2a66b259c220e0c12a8df5964bdeec8 |
| llvmlite-provenance.json | fee721898f0c8c80005389478b87e5129f771528cb3862966917d28596ff0bc5 |
| llvmlite-verification.log | 6709a90789650025395de4fab82c08465cc2db80e5fd80fda503ab3b60e8511c |
| wrong-repository-rejection.log | cb955b0d9bb74688f5e3e34061cab977aefce4ec1ae397f79582f50256c48118 |
| tampered-wheel-rejection.log | 0b27317f4668e6b21e4808a7ef411ea342e7cb3051ded95112a67afebe0fe689 |
| llvmlite-certificate-fields.json | edc0512ac512aad3b7103ca3565ad45b968661299dcdb34e644cf2cb140fd333 |
| upload_packages-5d881fd1.yml | e841ddc4918845fd501ea8787ef46874d504f211a5f413df2a03bd3d116bcb51 |
| verifier-freeze.txt | 620a6d539b89e7c6e78ec8317f4732f3885cae6b10fe2a7d1f7df70d14b4dc5e |

PBDS/全nativeビルド閉包、実課金/共有DB/worker運用/外部連携、AWS性能/復旧/事業者運用等の不足は[受入条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)に維持する。既存6b6c570c反映案・favicon承認へ後続変更を追加しない。
