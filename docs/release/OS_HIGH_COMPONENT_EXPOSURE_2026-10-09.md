# OS HIGH 2件の実コンポーネント照合

## 対象と判断

2026-10-09、[home通知候補の通常配布物](HOME_FEEDBACK_RUNTIME_2026-10-09.md)を再利用し、
同じ固定imageを変更せずに調査した。製品候補は `0a6876310b9c76b06d15d6db88d82a58a168abc6`、
imageは `sha256:9d9f48b3e4ac3596b6cdac45efbe56f2a7a113206e4e5eb21d7355584e912627`。

| 指摘 | 今回の証拠と次の対応 |
| --- | --- |
| Cyrus SASL / CVE-2026-107161 | 通常imageには対象DIGEST-MD5 pluginがなく、実libraryの方式一覧にもない。plugin単独追加の対照で列挙できることを確認。固定imageに限定した非到達の証拠として保持し、全SASLの安全性やAWSの判定へ拡張しない |
| zlib / CVE-2026-85091 | 1.3.1でも書き込み失敗→エラー解除→再書き込みで、渡した入力範囲外の検査領域7 bytesが変更された。関数不在・版名だけによる非該当判断は不可。上流修正の同版backport対照では変更0だが、製品への組み込みは未完了 |

通常imageは修正していない。先行全スキャンの38指摘（HIGH2/MEDIUM1/LOW35、Python0/native終了2）
をそのまま保持し、VEX・severity/package除外・リスク受容は適用していない。
OSゲート未合格・[正式公開No-Go](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を維持する。
今回はネットワークからの攻撃、アプリの利用者入力からの到達、任意コード実行を実証したものではない。

## Debian配布物との照合

通常imageのDebian archive keyringを使用した一時helperで、HTTPSのtrixie/trixie-updates/
trixie-securityを `apt-get update` した。認証無効化・allow-unauthenticated/trusted設定は使っていない。
そのindexから正確なsource版の `apt-get source --download-only` とbinary版の `apt-get download` を実行。
source/binary取得helperではパッケージをインストールせず、アプリentrypointも動かさなかった。

| binary package | 実導入版 | source版 |
| --- | --- | --- |
| libsasl2-2 / libsasl2-modules-db | 2.1.28+dfsg1-9 | 2.1.28+dfsg1-9 |
| libsasl2-modules | not-installed | 対照用に同版を取得しただけ |
| zlib1g | 1:1.3.dfsg+really1.3.1-1+b1 | 1:1.3.dfsg+really1.3.1-1 |

以下は通常imageの実fileと、認証済み同版debの展開fileでSHA-256が一致した。

| file | SHA-256 |
| --- | --- |
| libz.so.1.3.1 | 85590dd58edf5445e18bc7193e5ebc01ac5841f1ae187e97705a662e90c6421e |
| libsasl2.so.2.0.25 | 3f93968591811eb3972c3467c69c2968dd9cb2b51f7b7bb48de22ba8e17d13fd |
| sasl2/libsasldb.so.2.0.25 | 2cb155db2279fbc84ca8536b80be8e06f34ef9854c1b223e182279cea773b503 |

zlibのorig/packaging archive hashはそれぞれ
`60dd315c07f616887caa029408308a018ace66e3d142726a97db164b3b8f69fb` /
`9ed525955ce9fb0c1b39be8ff98f73450dbfc6305a9a27e6149c8972d38a0a9e`。
Cyrusはそれぞれ `e796a5d85d1a85e1b433d43504e467f9075c7ebc0b45730a3996cf11b1deada4` /
`8215afa01ee2907da0a650bfa6b9cf0fae12f2611a098eedd853b5e71adf6623`。
APT indexからの認証とhash検査であり、個別.dsc署名者の独立した鍵検証までは主張しない。

## Cyrus SASLのplugin境界

[CVEレコード](https://www.cve.org/CVERecord?id=CVE-2026-107161)と
[上流報告](https://github.com/cyrusimap/cyrus-sasl/issues/889)の当該HIGHは
DIGEST-MD5 pluginの `add_to_challenge()` に関するもの。
[Debianのfile一覧](https://packages.debian.org/trixie/amd64/libsasl2-modules/filelist)と
取得した `debian/libsasl2-modules.install` では、`libdigestmd5.so*` は別binary packageに属する。

- 通常imageのplugin directoryにはlibsasldbだけ。`/usr`・`/opt`・`/app` のdigestmd5名fileも0。
- `sasl_client_init` 成功後の実 `sasl_global_listmech()` はEXTERNALだけ。
  DIGEST-MD5指定の `sasl_client_start` はSASL_NOMECH(-4)、選択方式なし。
- 対照では認証済みdebの `libdigestmd5.so.2.0.25` だけをplugin directoryへ読み取り専用mountし、
  一覧がEXTERNAL/DIGEST-MD5になることを確認。core/DB library hashは通常条件と同じ。
  資格情報callbackを供給していないため対照のstartも-4であり、認証交換成功とは扱わない。
- 両probeはnetwork none/read-only/非root/cap-drop ALL/no-new-privileges。
  SASL_PATH/LD_PRELOAD/LD_LIBRARY_PATHは未設定、実資格情報と外部serverは未使用。

libpq→libldap→libsasl2の依存を `ldd` で確認した。core packageを無理に削除してPG互換性を変えていない。
Debian CVEページはweb toolでは取得できなかったが、HTTPS GETで原文を保存し、trixie/source版の
vulnerable/unfixedを再確認した。これはsource-package単位の判定であり、plugin欠落の局所証拠と区別する。

## zlibの反証と通常binaryでの再現

取得sourceのDebian patch seriesは空。`gz_vacate` や非ブロッキング再開状態は当該sourceにない。
しかし[Debian bug #1146895のmessage 36](https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=1146895#36)は
旧版のdirect writerでも同種の問題が起きると報告している。
この反証を受け、単に「1.3.1.2未満だから非該当」とする方針は採らない。

通常imageの実libzとPythonのcompile/runtime versionは1.3.1。
最初の限定probeではnonblocking pipeを65536 bytesまで満たし、gzbuffer256/input1200の
gzwriteが0/Z_ERRNO、エラーを解除しない後続gzprintfがZ_STREAM_ERROR(-2)になることを確認した。
この結果は未解除のerrorがある1経路だけで、非該当証拠として不十分だった。

後続はnetwork noneで、書けない `/dev/null` のread-only fdを `gzdopen(..., "wbT")` に渡す。
caller storageは入力1200 + canary1024 + 終端の2225 bytesを確保し、渡す入力長は1200だけ。
gzbuffer256→gzwrite失敗(0/Z_ERRNO)→gzclearerr→gzprintf("probe")の順で実行した。
検査領域のoffset0〜5と255の7 bytesが変化、入力prefixは保持された。
余裕を持った確保領域の内側で検査しており、実ヒープ破壊やクラッシュは起こしていない。
「論理上渡していないcaller領域へ書いた」という局所的な観測であって、ASan全経路検査ではない。

## 修正対照と残る実装

[上流修正df84af25](https://github.com/madler/zlib/commit/df84af25dc1942490e1d1c899a07619152a46148)の
入力状態を戻す処理を、取得済み1.3.1 sourceのdirect-write失敗分岐へ移した。
認証済みoriginal sourceは保持し、別directoryの `gzwrite.c` 1箇所だけを変更した。
これはローカル試作で、Debian公式修正版や通常imageへの適用ではない。

一時build helperだけにgcc/make/libc6-devをインストールし、共有libraryをcompile。
同梱のstatic/shared/64-bit `make test` は成功、helper終了0/OOMなし。
Windows bind mountの時刻差によるmake warningは生ログに保持し、再現可能な製品buildの証明にはしない。
対照library hashは `27ec58df686ab3e3299191216f6fb3507681a23ebac697ca49babaaa73ac71d3`。
同じcanary probeを通常imageの別library pathで実行し、範囲外変更0、gzprintf結果5を確認した。
通常imageのlibzを上書きしたり、LD_PRELOADで製品の検証を通したりしていない。

次は保守可能な修正済み配布方法を選び、exact source/patch/binaryを固定した通常buildと、
全CVE関連経路・Python/Pillow/DB・通常起動の回帰、全OS再スキャンを行う。
この対照だけでCVE解消・OS合格・反映可能とは判定しない。MEDIUM/LOWの判定も残る。

## CI・失敗記録・後片付け

[製品候補0a687631のCI](https://github.com/sheepdog0820/iaia/actions/runs/37874963631)は
全6ジョブ成功。Playwrightのdecoded logは228件成功/14.9分、終了は11:48 JST。
先行文書commit62d18a1dのCIも、その後全6ジョブ成功を確認した。
その実行中の記録pushによるキャンセルを避けるため、別の
`codex/os-high-exposure-evidence-20261009` を62d18a1dから作成した。製品codeは変えない。

初回APT/build helperはcap-dropによる権限不足で終了100、成功扱いしていない。
source取得はAPT sandbox userを一時helper内だけrootにして再実行、署名検証は維持。
build helperは必要なlocal capabilitiesだけ追加した別実行で完了した。
初回controlでdirectory全体をmountしてDB pluginを隠した検査、gzprintf戻り値の誤期待、
変更0の対照にmax(empty)を呼んだrunnerも訂正し、最後の同一probeの通常/修正対照は両方終了0。
製品不具合と試験runnerの誤りを混同しない。

12:02:13 JST、完全ID/name/label/image/終了0を照合し、所有source/build helper2件を削除、label残0。
前の失敗helperも同様に照合後削除した。helper内のcompiler/一時APT層は破棄され復旧対象外。
通常image、取得source/deb・修正試作source/library・probe/JSON・生ログ/inspectは
`D:/tmp/codex-os-applicability-0a687631-20261009` に保持した。
main/ECR/AWS/共有DB/実利用者/Secrets/IAM/OAuth/課金・容量/外部通知の変更はない。

記録3ファイルの関連文書テスト39件成功、省略0。相対file link target163件が存在し、
差分の空白検査も成功。製品codeの変更がないため、今回の文書commitに全アプリ再実行を要求しない。
