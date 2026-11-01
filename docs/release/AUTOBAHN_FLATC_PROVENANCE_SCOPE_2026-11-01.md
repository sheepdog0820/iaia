# Autobahn同梱flatcの公式wheel・公開署名・ソース参照（2026-11-01）

正式公開は **No-Go**。main `72ad82999739747ba16cf6ad8fda84a0a8bee3fa` と同じ製品treeを持つ通常image `sha256:ddb493e310c75d7b93b1f9312b87e00d99d1801e12b1784c13ba640fbda9fb8f` の追加native調査である。OS監査53指摘（Critical2/High10/Medium6/Low35）・raw exit2を維持し、ignore/VEX/例外やseverity変更は追加しない。

拡張子による旧棚卸しから漏れていた `autobahn/_flatc/bin/flatc` を調べた。既存imageのファイルを読み、公式配布物・公開署名・公開レシピとの対応を確認した。新しいflatcの導入、依存更新、製品imageの変更ではない。

## 実imageと公式配布物の一致

既存imageをnetwork none・root read-only・UID10001・capability全drop・no-new-privilegesで参照した。Pythonはmetadataとファイルのhashだけを読み、アプリやflatcを起動していない。検査containerは終了0、応答で得た同じIDの削除・不在を確認した。

[PyPI公式release metadata](https://pypi.org/pypi/autobahn/26.10.1/json)が指す次の配布物を取得し、sizeとSHA256を照合した。wheelのSHAは製品の `requirements.lock.txt` に含まれる。

| 対象 | size / SHA256 |
|---|---|
| `autobahn-26.10.1-cp311-cp311-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl` | 2,267,084 bytes / `e1a0dab939eb8c55d45b2440e123ef8c2ef8107ea71621b29348d34a8c47f57c` |
| `autobahn-26.10.1.tar.gz` | 14,313,294 bytes / `0acc00895d4d3b06b55e4c945592d426033062c989ca2910749777a855faa27a` |
| image内flatcとwheel内同一path | 4,039,808 bytes / `9a21ccc58e1197c3fd3e797eef199f0a56d9970bad119e68a4a0d59d95e64637` |

wheelはHatchling 1.32.4生成、CPython3.11/Linux x86-64のtagを持つ。vendored runtimeの `_git_version.py` はv25.12.19、`_version.py` は25.12.19を示す。実binaryの先行 `--version` 観測も25.12.19だったが、版文字列だけで全ビルド入力を確定しない。

## PyPI publish署名の実検証

対象wheelの[PyPI Integrity API](https://pypi.org/integrity/autobahn/26.10.1/autobahn-26.10.1-cp311-cp311-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl/provenance)はHTTP200で、PyPI Publish v1のattestationを1件返した。SLSA Build Provenanceは含まれていない。

[PyPI公式の消費手順](https://docs.pypi.org/attestations/consuming-attestations/)に従い、専用の使い捨て用途venvに `pypi-attestations==0.0.30` とwheel形式の依存を導入した。通常環境・製品imageのPython依存は変更していない。取得済みwheelとprovenanceを使い、期待repositoryを `https://github.com/crossbario/autobahn-python` に固定してCLI検証し、exit0と対象ファイルのOKを確認した。

追加の否認確認2件も実施した。元wheelに合成byteを付加した別fixtureはsubject digest不一致、元wheelに別の期待publisherを指定した場合はrepository不一致で拒否された。単なるファイル名不備や通信失敗による非zeroを、署名改変の拒否として扱っていない。取得したAutobahnのPythonコード・setup・flatcは実行していない。

検証後の証明書のscopeは次のとおり。

| 項目 | 値 |
|---|---|
| publisher | crossbario/autobahn-python、environment pypi、release.yml |
| signer/config | `.github/workflows/release.yml@refs/heads/master` |
| signer/source digest | `b7c3646d213820254d5ce88df65b48ea58a1fb26` |
| trigger | workflow_run |
| invocation | [run39178235215 / attempt1](https://github.com/crossbario/autobahn-python/actions/runs/39178235215/attempts/1) |

GitHub APIでも同runのevent/head/pathとcompleted/successを照合した。ただし、これは署名されたwheelの公開元と公開処理の記録である。[PyPI Publish v1の意味](https://docs.pypi.org/attestations/publish/v1/)を、native binaryの全compiler/header/ビルド引数や再現ビルドの保証へ拡張しない。検証器とその依存33件はPyPI HTTPS取得とinstall reportのdigestを信頼する前提で、検証器自体の再現ビルド・全依存署名は検証していない。

## 公開レシピとFlatBuffers参照

[Autobahnのv26.10.1 tag](https://github.com/crossbario/autobahn-python/tree/v26.10.1)はcommit `2ac4f0e26b999cee3377ca51d549f2e5a7813515` を指す。**このtag commitと上記publisherのmaster commitは別である。** tagレシピを実wheelの完全なビルド由来と断定しない。両commitで `deps/flatbuffers` のgitlinkは同じ `7e163021e59cca4f8e1e35a7c828b5c6b7915953` だった。公開annotated tag2件のGitHub verificationはunsignedであり、署名済みGit tagとの報告はしない。

[tagのhatch_build.py](https://github.com/crossbario/autobahn-python/blob/2ac4f0e26b999cee3377ca51d549f2e5a7813515/hatch_build.py)は公式sdist内とbyte一致し、SHA256は `a2588931d9e3662ae0a90ef40459c394df611e1a7fdfedad4af86fa0e573f5c6`。その通常レシピはdeps/flatbuffersからReleaseのflatc targetを作り、tests/flatlib/flathash/grpctest/sharedlibをOFFにしてpackage内へコピーする。sdistは当該submodule本体を除外しているため、sdistだけを全sourceとして調べない。

[FlatBuffers公式v25.12.19](https://github.com/google/flatbuffers/tree/7e163021e59cca4f8e1e35a7c828b5c6b7915953)も同commitを指す。その公式archiveは2,359,249 bytes、SHA256 `4236c5d22309abeac2384d3800febcc8d60423e8cb2f573abfa8f798352c4536`。全regular file1,903件・13,181,428 bytesを静的に読み、PBDS関連のliteral4種（pb_ds、__gnu_pbds、binary_heap_tag、extc++.h）は見つからなかった。CMakeLists.txtはGitHub treeに記録されたGit blob `7bf48e6aeccc6564c70f3d6c91f1657daa928011` と一致した。

CMakeのflatc targetはC++のcompiler source集合を使用する。この文字列の不在は、実wheelビルドで別途使われたheader、生成・注入入力、compiler/sysroot、静的同梱部分、macro経由の利用を否定しない。実際の製造runからwheelまでのartifact対応と全build入力は未確認で、PBDSへの非該当は未確定のままである。

## 呼出し範囲と残作業

wheelのPython204ファイルでは、`_flatc` / run_flatc / get_flatc_pathのliteral参照はwrapper自身だけだった。ASTでは明示的なrun_flatcとconsole mainの2か所がsubprocess.callで同梱binaryを呼ぶ。製品と同じアプリコードを持つ検査元head `9bdba22e` のGit管理Python/JS/shell683ファイルにはflatc literal参照がなかった。このheadにはmainにないCOMMIT回帰テストがあるため、683という件数をmainそのものの件数とは呼ばない。

動的import・生成されたコマンド・他依存内部まで確認した結果ではなく、HTTP経由の到達不能を証明したものでもない。compilerの同梱を削除したり、対応機能を取り除いて指摘を減らしたりしていない。

残る確認は、実製造run・compiler/sysroot/header・全flagsとwheelの対応、PBDS/aligned newを含むnative適用範囲、他21 ownerを含む残りのnative部品とOS指摘への対応である。[既存のONNX Runtime調査](ONNXRUNTIME_NATIVE_SOURCE_SCOPE_2026-10-31.md)や[MySQLdbの限定的なC99判断](MYSQL_NATIVE_PBDS_BUILD_SCOPE_2026-10-30.md)とscopeを混同しない。全268 ELFの由来を検証済みとはしない。

## 変更・検証・証拠

Git変更はこの調査文書1件だけ。数字・hash・参照リンク・差分・UTF-8/LF/BOMなし・自己レビューを確認する。アプリ全体テストやimage rebuildはこの文書変更のためには再実行しない。文書はrevert PRで戻せ、DB逆移行は不要。DB/実データ・AWS資源/権限/Secrets・費用設定・実Stripe・外部通知を変更していない。PR #63、固定3de/image4617のコピー内5移行、専用S3設定の既存確認3件は別の対象として維持する。[元25受け入れ条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)と正式公開No-Goは不変。

Git管理外の根拠は調査worktree `restore-ownership-evidence-20261101/iaia/tmp/flatc-provenance-20261101/` に保持する。主要記録はcurrent-image-file-proof.json、official-artifacts.json、attestation-verification-result.json/log、negative-verification-results.jsonと2否認log、verified-publisher-certificate-scope.json、各GitHub tag/gitlink/run/workflow、flatbuffers-source-scan.json、flatc-caller-scope.json、verifier-install-report.json。wheel/source archive/証明書/venvはGitへ含めない。
