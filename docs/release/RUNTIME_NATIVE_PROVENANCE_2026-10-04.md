# 稼働native依存の配布物照合とPBDS確認の境界

## 固定対象・結論

[OS監査](RUNTIME_HIGH_APPLICABILITY_2026-10-04.md)の後続調査。main `8567f49f8d411bad7f732afaeebad85357eeca09`、開発AWS定義54と同じ未変更イメージを対象とする。

- image ID: `sha256:9c829979f8a69e075b61f7769c3b26d7a4fa003316c47d07e1982f7d7b94f4ad`。
- registry/runtime digest: `sha256:adafc0705ded3dabf2a9d2223a5c460b48ff00b2c949f221a4edef3eedee695e`。
- Python site-packages内の267 ELF共有オブジェクトは22パッケージに属し、全件がインストール済みRECORDのハッシュに一致。所有者不明・不一致とも0。
- うち21パッケージ・266ファイルは、既存ロックに固定された公開wheelの内容ともバイト単位で一致。残り1ファイルはmysqlclientのソースビルド。
- 配布物の同一性は確認したが、C++テンプレートの全ビルド由来・使用条件を証明したわけではない。PBDS指摘を抑制せず、39指摘（HIGH2/MEDIUM2/LOW35、Python0）と正式公開 **No-Go** を維持する。今回スキャンは再実行していない。

## 照合手順・範囲

通信禁止・read-only・512 MiB上限の使い捨てコンテナで、`/usr/local/lib/python3.11/site-packages`配下の`.so*`を列挙しELF magicを検査した。各実ファイルのRECORD所有者、RECORDハッシュ、SHA-256、WHEELタグを取得。Python標準ライブラリ、OSライブラリ、native実行ファイル、モデル等を含む全イメージの来歴監査とは区別する。

ホスト側では[PyPI JSON API](https://docs.pypi.org/api/json/)の版別メタデータから、インストール済みタグに対応するwheelを選択。候補を1件に限定し、archive SHA-256が`requirements.lock.txt`に存在すること、TLS検証付き取得後のarchiveハッシュ、wheel内部WHEELタグ、全対象ELFファイルのSHA-256を確認した。ダウンロードしたコードの実行・インストールはしていない。

rcssmin/rjsminはwheel名のタグ集合と内部WHEELタグ集合が異なるため、ファイル名タグの共通部分から唯一の候補を選択した。その後の内部タグ完全一致・固定archiveハッシュ・実バイナリ一致も必須とし、タグだけで配布物を同一と判定しない。初回の厳格なファイル名タグ選択でこの2件が未選択だった状態と、後続の成功を区別する。

RECORDだけでは配布元の証明にならないため、公開wheelとの独立比較を追加した。ただし公開wheelとの一致もビルド安全性の証明とは異なる。[PyPI Integrity API](https://docs.pypi.org/api/integrity/)のattestation取得・署名検証は今回未実施で、署名検証済みとは主張しない。

| 所有パッケージ | 版 | ELF数 | 公開wheel内の全対象ファイル一致 |
| --- | --- | ---: | --- |
| scipy | 1.17.1 | 114 | 成功 |
| charset-normalizer | 3.5.1 | 2 | 成功 |
| zope.interface | 8.6 | 1 | 成功 |
| PyYAML | 6.0.3 | 1 | 成功 |
| rcssmin | 1.2.2 | 1 | 成功 |
| autobahn | 26.7.1 | 2 | 成功 |
| numba | 0.67.0 | 14 | 成功 |
| llvmlite | 0.49.0 | 1 | 成功 |
| psycopg-binary | 3.3.4 | 17 | 成功 |
| msgpack | 1.2.1 | 1 | 成功 |
| cffi | 2.1.1 | 1 | 成功 |
| pillow | 12.3.0 | 26 | 成功 |
| cryptography | 50.0.1 | 1 | 成功 |
| numpy | 2.4.6 | 22 | 成功 |
| scikit-image | 0.26.0 | 54 | 成功 |
| protobuf | 7.36.0 | 1 | 成功 |
| ujson | 5.13.0 | 1 | 成功 |
| rpds-py | 2026.6.3 | 1 | 成功 |
| cbor2 | 6.1.4 | 1 | 成功 |
| onnxruntime | 1.29.0 | 3 | 成功 |
| rjsmin | 1.2.5 | 1 | 成功 |
| mysqlclient | 2.2.8 | 1 | 対応する公開Linux wheelなし。RECORD照合のみ |

## ソース確認・未解消条件

267ファイルに`__gnu_pbds`/`ext/pb_ds`/`binary_heap_`/`erase_fn_imps.hpp`文字列は見つからなかった。strip・inlineされたテンプレートは残らない可能性があるため、文字列不在をPBDS非該当の根拠にしない。

mysqlclientの固定sdist `mysqlclient-2.2.8.tar.gz`（SHA-256 `8ed20c5615a915da451bb308c7d0306648a4fd9a2809ba95c992690006306199`）は既存ロック・取得archiveとも一致。C/C++拡張子のソースは`src/MySQLdb/_mysql.c`の1件で、setup.pyも同じC拡張を指定し、当該文字列は不在。これはソース構成の証拠で、インストール済みバイナリの再現ビルド照合・すべての従属ライブラリの安全性証明ではない。

llvmliteの固定sdist `llvmlite-0.49.0.tar.gz`（SHA-256 `00f16db782f4a13c78c5804aedc434e46794a77e89999a168f9401106270e50a`）もロック・取得archiveと一致。C/C++ソース内に上記文字列は不在だが、`ffi/CMakeLists.txt`は外部LLVMのCONFIGを必須とし、既定の対応majorは22、LLVMは既定で静的リンクする構成。版チェックを迂回するオプションもあり、この設定だけから実wheelのLLVMリビジョン・ビルド環境を確定しない。外部LLVM側までのソース照合が残る。

onnxruntime 1.29.0のPyPI版別メタデータにはsdistがなく、GitHubのtagsへの案内がある。公開wheel一致は確認済みだが、同wheelに対応するソースコミット・ビルド時の従属ライブラリとGCCヘッダーまでの照合は未完了。GitHubソースが存在しないという意味ではない。他のwheelも全第三者ソースの閉包・実ビルドログを確認していない。

[上流PBDS修正](https://github.com/gcc-mirror/gcc/commit/aaa8351f4d2e636f9680a1f0a8ebc2f0a60611e6)が対象とするテンプレートの使用、コンパイル時ヘッダー、修正版取り込みまで確認する必要がある。[Debian記録](https://security-tracker.debian.org/tracker/CVE-2026-102010)のunfixed判定は変更されていない。今回の来歴照合をCVE解消・例外承認・公開条件の緩和にしない。

## 証跡・影響・検証

| 保持ファイル | SHA-256 |
| --- | --- |
| `C:/tmp/runtime-native-provenance-20261004.py` | `e0d64c44a97706819ff809a4d6a2aac8bf807e5c637a84838351bca3913c2efb` |
| `C:/tmp/runtime-native-records-8567f49f-20261004.json` | `10b6f6cc7cb3c4c567d4e72eda34639e3aa30aeefbcb0827e2e5174caf0fe4ab` |
| `C:/tmp/runtime-wheel-reference-probe-20261004.py` | `ebc6cc6c7cd900f3e36759f256d0678d53ee863250193e0f2c3a654b0daaeb78` |
| `C:/tmp/runtime-native-source-boundary-20261004.py` | `6c0c5f8bc2d73fb97d5eb4ffc751aa739a3107527e7b2c8dfc69c3abe1aa305f` |
| 対象checkoutの`requirements.lock.txt` | `81b0a269e11bc3b5dfdca3fab79bf46b347eb9607f3d5b23a0b6717ffd1a5b1a` |

RECORD調査・最終wheel比較・ソース境界調査はいずれも終了0。wheel比較は欠落0・不一致0。ローカル一時スクリプト/JSONは再調査用に保持し、アプリ配布物やリポジトリには追加しない。文書だけの更新に対して差分・参照先・UTF-8/LFを検証し、アプリ全体テストと後続CIの成功は未確認として区別する。

アプリ・イメージ・AWS・DB・Secrets/IAM・課金・常設容量・通知を変更していない。実ユーザーデータは使わず、調査コンテナは終了時削除した。復旧対象は証拠文書だけで、当該コミットをrevertできる。未達の共有DB・課金実運用・実外部連携・総合性能・復旧・事業者運用は[受入条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)に維持する。
