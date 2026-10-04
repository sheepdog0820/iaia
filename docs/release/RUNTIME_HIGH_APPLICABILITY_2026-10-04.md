# 稼働配布物のOS再監査とHIGH指摘の適用条件

## 固定対象・結論

正式公開は **No-Go** を維持する。対象はmain `8567f49f8d411bad7f732afaeebad85357eeca09`、[アイコン反映後](TABLENO_FAVICON_DEPLOYMENT_2026-10-04.md)の開発AWS定義54と同じ配布物である。

- ローカルimage ID: `sha256:9c829979f8a69e075b61f7769c3b26d7a4fa003316c47d07e1982f7d7b94f4ad`。
- registry/runtime digest: `sha256:adafc0705ded3dabf2a9d2223a5c460b48ff00b2c949f221a4edef3eedee695e`。
- Docker Scout 1.24.0で全268パッケージを再indexし、39指摘（HIGH **2** / MEDIUM **2** / LOW **35**、Python 0）を取得。終了コード1でゲートは未合格。
- 10月2日の39指摘とCVE IDの追加・削除は0。`CVE-2026-85091`だけがHIGH→LOWとなった。これはスキャナーの評価変更であり、アプリ修正・指摘解消ではない。直前の報告で旧内訳HIGH3/MEDIUM2/LOW34を使ったが、機械集計後に訂正した。
- C++のaligned newは実バイナリが`posix_memalign`経路を使うことを確認し、境界40例と正常10例に成功。zlibは対象のDebianソースに問題関数・非ブロッキング制御がないことを確認した。いずれも限定した適用条件の証拠であり、39件の抑制・リスク受容・全体合格にはしない。

レポート: `C:/tmp/runtime-os-favicon-8567f49f-20261004.sarif.json`、SHA-256 `4924d757f193ce8edc27492ad5006bea0a41b61bb61c0d57c7221fb5b1f48f39`。専用キャッシュと`DOCKER_SCOUT_NO_CACHE=true`で実施した。archive削除のfile-in-use警告は残ったが、index・全指摘・SARIF生成は完了。キャッシュは強制削除していない。

## パッケージ・実依存の確認

使い捨てコンテナで`apt-get update`/`apt-cache policy`を実行し、libstdc++6/libgcc-s1/libgomp1はinstalled/candidateとも`14.2.0-19`、zlib1gはともに`1:1.3.dfsg+really1.3.1-1+b1`。現行のtrixie・updates・securityでは今回の対象に新しい候補版がない。sid等の別ディストリビューション混入や独自ランタイム置換はしていない。

通信禁止・read-onlyコンテナでPython site-packages内の267 ELF共有オブジェクトを`ldd`照合。Pillow/AVIF、protobuf、NumPy、SciPy、ONNX Runtime、llvmlite、numba、scikit-image、ujson等がlibstdc++.so.6を参照している。PythonアプリだからC++が未使用とは言えず、ランタイムの単純削除は不可。zlibは画像・DBドライバー・数値処理等で実参照がある。

直接`ldd`した一部の同梱従属ライブラリには未解決名があり、主モジュールのRUNPATH等によるロードとは区別する。numbaの任意TBBバックエンドにもlibtbb.so.12不在がある。この一覧だけで全モジュールのロード成功/失敗や背景透過の全体成功を宣言しない。

通常の書込可能な使い捨てコンテナ（通信禁止・2 GiB上限）でNumPy/SciPy/PIL.Image/PIL._avif/protobuf/ONNX/llvmlite/numba/skimage/ujson/psycopg/rembgの12モジュールを実importし、すべて成功・終了0。モデル生成・取得・推論は未実行。先行の全面read-only・/tmpだけtmpfs条件ではrembgのnumba JITキャッシュlocatorが失敗し、ONNXのtelemetry保存警告も出た。通常条件の成功とこの制限条件の失敗を区別し、read-only本番の対応完了や実背景透過成功とは主張しない。

パッケージ内の実ライブラリはdpkgのMD5一覧と一致。`dpkg --verify`全体では削除済みchangelogが報告されるため、全ファイル検証成功とは扱わない。

| 実ライブラリ | SHA-256 |
| --- | --- |
| libstdc++.so.6.0.33 | `972bb2a18b71140dab0240f8a1f68ab3fb1d56bcd4c4f824a91b70888faf5a00` |
| libz.so.1.3.1 | `85590dd58edf5445e18bc7193e5ebc01ac5841f1ae187e97705a662e90c6421e` |

## 指摘ごとの証拠・残条件

### CVE-2026-95619: aligned newの整数オーバーフロー

[Debian記録](https://security-tracker.debian.org/tracker/CVE-2026-95619)はgcc-14をvulnerable/unfixedとする。[上流修正](https://github.com/gcc-mirror/gcc/commit/59d235ffa5a69231eb42e5290d52dc8c90d28b7a)はaligned_alloc・Windows・fallbackの加算を修正し、posix_memalign経路はその加算を行わない。[GCC 14.2ソース](https://raw.githubusercontent.com/gcc-mirror/gcc/releases/gcc-14.2.0/libstdc%2B%2B-v3/libsupc%2B%2B/new_opa.cc)もこの条件分岐を持つ。

実ライブラリの`_ZnwmSt11align_val_t`をobjdumpで確認し、サイズを丸める危険な加算ではなく`posix_memalign@plt`を呼ぶことを確認した。binutils導入は使い捨て調査コンテナだけで、配布イメージには追加しない。

同じ未変更イメージでscalar/arrayのnothrow aligned newへSIZE_MAXから0/1/63/4095を引いたサイズを渡し、alignment 8/16/32/64/4096の40組すべてNULLで拒否。65 bytesの正常10組は要求alignmentを満たし、対応するdeleteで解放した。書き込み・巨大バッファの使用はせず、64 MiB・通信禁止・read-only・pids 32の隔離コンテナで終了0。

このLinuxバイナリと当該関数の条件不一致を裏づけるが、全サイズ・全ABI・別の同梱C++実装を網羅した安全性証明ではない。スキャナーのHIGH指摘は残す。

### CVE-2026-102010: PBDS binary heapのerase_if

[上流修正](https://github.com/gcc-mirror/gcc/commit/aaa8351f4d2e636f9680a1f0a8ebc2f0a60611e6)はC++ヘッダー内の再確保後ポインター更新である。共有ライブラリがロードされるかだけでは、wheel内にコンパイルされた当該テンプレートの使用を判定できない。ヘッダー削除済み・文字列検索不一致を非該当証拠にしない。native wheelのビルド由来・対象テンプレートの使用/修正版取り込みの確認が残る。[Debian](https://security-tracker.debian.org/tracker/CVE-2026-102010)もunfixedのまま。

後続の[native配布物照合](RUNTIME_NATIVE_PROVENANCE_2026-10-04.md)で267 ELFのRECORD一致、うち21パッケージ266ファイルの固定公開wheel一致を確認。残るmysqlclientは固定Cソースの構成を確認した。配布物の同一性とPBDS非該当証明は区別し、外部LLVM/ONNX等のビルド閉包・使用条件は未確認としてHIGH指摘を維持する。

### CVE-2026-85091: zlibの非ブロッキングgzwrite経路

[Debian記録](https://security-tracker.debian.org/tracker/CVE-2026-85091)の説明は上流1.3.1.2〜1.3.2の`gz_vacate`経路を対象とし、trixieのパッケージ表はvulnerableと表示する。[導入コミット](https://github.com/madler/zlib/commit/81cc0bebedd935daeb81b0b6e475d8786b51af3d)は非ブロッキング状態管理等を追加している。

対象のsource packageは`1:1.3.dfsg+really1.3.1-1`。既存Debian署名鍵を使ったAPTのdeb-src読み取りで正確な版を取得し、gzwrite.c/gzlib.c/gzguts.hに`gz_vacate`も`again`状態制御もないことを確認。[公開ソース](https://sources.debian.org/src/zlib/1%3A1.3.dfsg%2Breally1.3.1-1/gzwrite.c)の表示とも一致する。Debian patches/seriesは0 bytesで、該当コードのバックポート追加もない。Pythonのbuild/runtime・ctypesで呼んだsystem zlibはいずれも1.3.1。

- orig archive SHA-256: `60dd315c07f616887caa029408308a018ace66e3d142726a97db164b3b8f69fb`。
- Debian archive SHA-256: `9ed525955ce9fb0c1b39be8ff98f73450dbfc6305a9a27e6149c8972d38a0a9e`。
- gzwrite.c SHA-256: `469b1e58932ea11bdda2a153f6655f7b3c13254240fae157181b49ed1bc93b47`。

説明された発生条件と対象ソースの不一致という技術証拠は得たが、Debian/scannerとの判定相違は未解消。今回のLOW化を修正版導入・例外承認とみなさない。別のzlib指摘や同梱別実装へ判定を広げない。

## 証跡・影響・次の作業

再実行用のローカル調査スクリプトを保持した。

| パス | SHA-256 |
| --- | --- |
| `C:/tmp/runtime-native-inventory-20261004.py` | `35985b25122d9af49751d4542b1d29c7bb3d6ba93982b90da865dc1024fc7f42` |
| `C:/tmp/runtime-aligned-new-probe-20261004.py` | `5134c92c5b4ae77ef4e16312f383b5400f5f98b193cdc7828c0670f7d02198c5` |
| `C:/tmp/runtime-zlib-source-probe-20261004.py` | `f716ec7b1fac0e3791ce0f2659029baeed2b1a0f04a8da4c121de7dd0ef655c8` |

初回のshell引用・Signed-By拡張子不一致を調査コマンド内で修正し、成功実行と区別した。Debian Sourcesの生取得は証明書期限エラーで失敗したため、TLS検証を無効化せず、署名検証される既存APT配布元を利用した。生URLの取得/ハッシュ成功とは主張しない。

アプリソース・配布イメージ・AWS・DB・Secrets・IAM・料金・通知・常設容量を変更していない。調査コンテナは`--rm`で終了時削除され、実ユーザーデータを使っていない。文書だけを戻す場合は当該証拠コミットをrevertできる。

13:48 JSTにmain=8567f49f・AWS定義54・1/1/0・HEALTHY・指定digest一致・DB/cache readiness正常を読み取り再確認。`docker ps`で調査コンテナ不在も確認した。過去のセキュリティ更新記録は証拠ブランチ7ca069dcから内容をそのまま取り込み、現在の反映済み情報と旧時点の記述を区別する。

次はPBDSのnative依存由来の確認、残るMEDIUM/LOWの条件照合または修正版導入・回帰検証。共有DB0065〜0067の実状態、AWSの課金/worker/メール、実外部連携、総合性能・復旧・事業者運用は別の未達条件として維持する。
