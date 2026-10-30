# pyasn1のCPU枯渇脆弱性4件への対応（2026-10-31）

08:43 JST、文書PR #42のhead `ce18e45d`に対するPR/push両CIの依存監査が、`pyasn1==0.6.4`の4件で終了1となった。以前の候補のPython既知0件とCI成功は各実行時点の記録であり、現在の監査合格を意味しない。PR #41/#42/#43にもこの追加指摘を記録し、既存headは変更していない。

## 対象と変更

公式の[0.6.5リリース](https://github.com/pyasn1/pyasn1/releases/tag/v0.6.5)と次の修正情報を照合した。

| ID | 対象 | 公式修正情報 |
| --- | --- | --- |
| CVE-2026-119194 | schemaなしコンテナの型追跡 | [GHSA-fm9c-5rcf-2q5p](https://github.com/pyasn1/pyasn1/security/advisories/GHSA-fm9c-5rcf-2q5p) |
| CVE-2026-119195 | 構築文字列・不定長ANYの連結 | [GHSA-9m75-vc3g-4x39](https://github.com/pyasn1/pyasn1/security/advisories/GHSA-9m75-vc3g-4x39) |
| CVE-2026-119196 | 構築BIT STRINGの連結 | [GHSA-2qm8-x737-gmw5](https://github.com/pyasn1/pyasn1/security/advisories/GHSA-2qm8-x737-gmw5) |
| CVE-2026-119197 | binary REALの仮数デコード | [GHSA-mm57-4v3p-rchx](https://github.com/pyasn1/pyasn1/security/advisories/GHSA-mm57-4v3p-rchx) |

いずれも攻撃者のASN.1入力が該当デコーダーへ届く場合のCPU消費に関する指摘で、これだけでタブレノの特定の公開経路が悪用可能と確認したものではない。依存は実metadata上で `google-auth → pyasn1-modules → pyasn1`。`pyasn1-modules 0.4.2`の条件 `>=0.6.1,<0.7.0`と修正版0.6.5は整合し、要求Python>=3.8も既存Python3.11で満たす。

通常入力に`pyasn1>=0.6.5`を追加し、Python3.11の既存pip-compile方式で通常/開発/テストを再解決した。公式PyPIの未取り消し配布物2件のSHA256と一致したpyasn1ブロックだけを採用した。他の版・hash・ブロックはバイト単位で不変で、Linuxで省略される既存async-timeout/coloramaも保持した。Twisted正式版など既存のsecurity floorは維持する。

| 公式artifact | SHA256 |
| --- | --- |
| `pyasn1-0.6.5-py3-none-any.whl` | `4017b0fce125096b8573b39c989fdb1a4b19cf761e683398184550fea0e66587` |
| `pyasn1-0.6.5.tar.gz` | `6b11616a6bcf3a40e635f082bb232fa57b5e0dd7f517bd7ddd69ec3794508a47` |

## 検証

- ハッシュ付きtestロックの導入と`pip check`成功。通常111・開発167・テスト207パッケージのpip-auditはすべて既知0件・省略0件・終了0。除外やhash検証の無効化は行っていない。
- 公式sdistのサイズ/SHA256を照合し、そこに含まれる公式suiteを実インストール済みwheelに対して実行した。1,261件成功・失敗/省略0件。通信禁止・root read-only・UID10001のコンテナで実行し、import先がsite-packages内であることも確認した。
- Google認証/コールバック・OAuth原子性/無効利用者・Google job認可・JWTの既存回帰は、隔離SQLite58件成功・40 subtests/2件省略。省略は行ロック非対応によるもので、同じ対象を隔離PostgreSQL18.3で60件成功・40 subtests/省略0件と確認した。外部OAuthや実利用者のデータは使用していない。
- UTF-8/LF・差分、依存条件とlockの最小差分を自己レビューした。製品のPython/画面/API・DBモデル/移行は変更せず、新たな利用者向け文言もない。

固定source `a0d2e5527a8dff8de730d4ffa82b4c5650bc0c09`をgit archiveし、通常Dockerfileでimage `sha256:98d2931793417af89c2219b30151c553cba4a4c32c99d98b026fe7dba19caa7d`を構築した。Git由来562ファイル/entrypoint一致、UID10001/root read-only、pip/pytestなし、製品sourceの上書きなしを確認。実111 packageの監査は既知0件/省略0、配布物内の認証PG60件と公式suite1,261件も成功した。OS inventory101件は旧統合候補と一致し、Scout1.29の未除外監査は52指摘（C2/H9/M6/L35）・exit2で不合格のままである。専用PG/networkは08:54 JSTに削除し、endpoint残存0とabsenceを確認した。最新CIは確認中で、過去imageの成功を今回の成功として扱わない。

ローカルの検証用image作成の初回は、DockerfileのFROMへ短いimage IDを使って失敗したログを保持し、既存の固定IDと一致を確認したローカルtagへ修正して成功した。配布物照合の初回もWindows引数長制限で失敗し、manifestを標準入力で渡して同一imageで成功した。製品Dockerfileやhash条件は変更していない。

## 適用と復旧

比較baseはPR #41の固定head `a78d15bf`。この修正は同PRの承認対象を変更せず、独立したDraftとして扱う。main・AWS稼働版・共有DBへの反映は未実施で、PR #43のグループ修正も含めない。通常pushはCIだけを起動することをworkflowで確認した。

DB schema/実データ・AWSリソース・IAM/Secrets/OAuth設定・費用・外部通知に変更はない。復旧は入力と3ロックのrevert PRで、戻すと今回の4指摘が再発する。OS/nativeの52指摘などをこの更新で解決したとは扱わず、正式公開No-Goと全25受け入れ条件を維持する。

ローカル証拠：`tmp/pyasn1-security-lock-adoption-proof-20261031.json`、`tmp/pyasn1-security-lock-validation-20261031-attempt2.log`、`tmp/pyasn1-official-sources-20261031/source-proof.json`、`tmp/pyasn1-security-upstream-tests-20261031.log`、`tmp/pyasn1-security-google-regressions-20261031.log`、`tmp/pyasn1-security-google-pg-20261031.log`。これらはGitに含めない。
