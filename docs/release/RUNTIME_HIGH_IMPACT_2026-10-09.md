# 通常配布物のHIGH指摘・SASL利用条件の調査

## 判定と対象

正式公開 **No-Go**。指摘の抑制、例外承認、リスク受容は行っていない。
対象は[通常配布物検査](GOOGLE_JOB_DISTRIBUTION_2026-10-09.md)のアプリ6791357f、
固定image `sha256:6de91d2a3c3fb4d2d4254c656b893352098a40d3dbd1bb3a75b7707c7e238874`。
新Scoutの38指摘（HIGH2/MEDIUM1/LOW35、native終了2）は未合格のまま。
今回は新しいスキャンやAWS調査ではなく、同じ固定imageと公開一次情報の追加照合である。

10月9日07:47 JST取得のDebian記録は、当該cyrus-sasl2/zlibのtrixie版を両方
vulnerable、修正版をunfixedとしている。別ディストリビューションの判定や
上流の修正案を、このDebian配布版の修正済み証拠にしない。

## CVE-2026-107161: DIGEST-MD5の利用条件

[CNAの公開記録](https://raw.githubusercontent.com/CVEProject/cvelistV5/main/cves/2026/107xxx/CVE-2026-107161.json)は、
Cyrus SASLのDIGEST-MD5プラグインで、悪意あるサーバーの値を引用処理する際の
ヒープ書き込みを説明し、当該方式を使わないことを回避案に挙げている。
[Debian記録](https://security-tracker.debian.org/tracker/CVE-2026-107161)はsource package
`2.1.28+dfsg1-9`を脆弱とする。
[上流PR892](https://github.com/cyrusimap/cyrus-sasl/pull/892)はclosedだが、修正版配布の証拠とはしない。

通常imageの読み取りと、ネットワーク通信を伴わないライブラリAPI呼び出しで確認した。

| 対象 | 確認結果 |
| --- | --- |
| OS libsasl2-2 / modules-db | `2.1.28+dfsg1-9`、install ok installed |
| OS libsasl2-modules | unknown ok not-installed。DIGEST-MD5名のファイルも選定2ルートに0 |
| OS依存経路 | libpq5 → libldap2 → libsasl2-2 → modules-db。コアライブラリの単純削除はしない |
| Python配布物 | psycopg / psycopg-binary 3.3.4、実選択binary、libpq runtime 180000 |
| OS SASL API | version 2.1.28、init/done 0、列挙EXTERNALのみ、DIGEST-MD5選択-4（SASL_NOMECH） |
| psycopg同梱SASL API | version **2.1.26**、init/done 0、列挙EXTERNALのみ、DIGEST-MD5選択-4 |

Python import後の実ロードmapにも同梱libpq/LDAP/SASLを確認した。
OSパッケージだけの調査では、この別ライブラリの確認が欠落する。
同梱ライブラリ単体のlddには従属名のnot foundがあるが、通常psycopg import後のロードと
API呼び出しは成功しており、単体lddだけからDBドライバー故障とは判断しない。

推論として、この固定imageの通常探索条件では報告されたDIGEST-MD5経路の利用条件を
満たさない証拠が得られた。ただし、実認証・CVE入力・全native経路・AWSのmount/configや
長時間worker内のロード状況は検査していない。SASL_PATH変更、追加プラグイン、依存更新、
別imageでは再照合が必要。これをHIGHの解消や正式公開の安全性へ拡張しない。

## CVE-2026-85091: 既存証拠と判定相違

実system zlibはbuild/runtimeとも1.3.1、source `1:1.3.dfsg+really1.3.1-1`。
libz.so.1.3.1のSHA-256は
`85590dd58edf5445e18bc7193e5ebc01ac5841f1ae187e97705a662e90c6421e`で、
[先行の署名付きAPTソース調査](RUNTIME_HIGH_APPLICABILITY_2026-10-04.md)のバイナリと一致する。
先行のソース取得・問題関数の有無の調査は今回再実行していない。

[CNA記録](https://raw.githubusercontent.com/CVEProject/cvelistV5/main/cves/2026/85xxx/CVE-2026-85091.json)の
影響版表と[Debian記録](https://security-tracker.debian.org/tracker/CVE-2026-85091)の判定は
一致しない。[上流の修正commit](https://github.com/madler/zlib/commit/df84af25dc1942490e1d1c899a07619152a46148)は
存在するが、[影響版に関するDebianからの質問](https://github.com/madler/zlib/issues/1310#issuecomment-5979623265)も
残る。バージョンの大小や先行ソース調査だけで誤検知と確定しない。
上流commitの存在を、当該imageが修正を含む証拠にも読み替えない。

## 次の対応と境界

1. Debianの修正配布または正式な適用条件判定を確認し、固定imageを再ビルド・再スキャンする。
   独自patch/異なるOSの混入で単にスキャン件数を減らすことはしない。
2. SASLの証拠を非該当判定案へ使う場合も、配布版・プラグイン探索・実稼働設定を指定し、
   判断者の承認と再照合条件を記録する。今回は案の材料までで、除外を実施しない。
3. 修正版を導入した場合は、DB認証・Google/Stripe/OAuth・画像/背景透過・通常起動の回帰と
   新配布物の来歴を確認する。ローカル449成功を新しい依存変更へ流用しない。
4. Googleのcleanup/保持/認可/限定回復・移行/drain等、修正版の待機と独立した安全な作業は続ける。
   実AWS課金/外部連携・性能・DB/S3復旧・運営条件も[全体受入条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)に残る。

アプリ/schema/依存・main/AWS/共有DB/実データ/Secrets/IAM/課金/容量/通知は未変更。
作業ブランチの記録だけをコミットし、先行CIの完了後に通常pushする。
10月9日07:54 JSTの[先行f271 CI37854944947](https://github.com/sheepdog0820/iaia/actions/runs/37854944947)は
Infrastructure/Lint-Security/System/Production Databaseの4成功、Unit/IntegrationとPlaywrightは実行中。
検証途中のrunを文書pushで再度cancelしないため、pushを留保する。今回記録のCI成功は未確認。
文書の復旧は当該証拠commitのrevertで行える。

## 保持証拠・調査の失敗と修正

保存先は `D:/tmp/codex-high-impact-20261009`。
最終auditは非root10001、network none、read-only、cap-drop ALL、no-new-privileges、
512 MiB/1 CPU、mount0、image/source追加インストールなし。正常終了0、OOM false。
正確なID/label/nameを確認して専用container
`e773989c162e1a8367405501246a584c2929b6568918c38c4e65ad1d61a312fc`を削除した。
同ラベルのcontainer不在を確認し、固定image・生記録・原作業13差分は保持した。

初回auditはlibsasldbプラグインをコアと誤分類し、存在しないversion APIを呼んで終了1。
`libraries.json`の失敗を保持し、libsasl2コア2個へ選定を修正して再実行した。
最終成功はこの工具修正後の結果であり、製品ライブラリを置換した成果ではない。
公開情報の取得でも初回PowerShell構文エラーは失敗とし、修正後4 URLのHTTP200/取得時刻を保存した。

| ファイル | SHA-256 |
| --- | --- |
| audit.py | `10408e242559e8488f0aa3eaeb3961c8b055192bbc3a6e12fba48644e260b1bc` |
| libraries-final.json | `81b84bf129fdd79887cc05118f7b265548938c8385fc9c1fd6974a7d2a4b6011` |
| audit-inspect.json | `d7f10aa80ab3ef4b13a37a62a5f96ffdcdb71519e305926f49a47eacac060046` |
| audit-result.json | `7856d9265e3b16a2904002b8927ae29d12c40e1c5696ecfa57873ac86668874b` |
| source-fetch.json | `2987183ef6f941e11f16c3d90d696d04d2cf610f884a3a380af8f3f1481c8667` |

変更3文書の差分・UTF-8/LF/BOMなし、相対参照258件/欠落0を確認した。
文書・文字品質44試験が成功、DBのセットアップは不要で実DBには触れていない。
自己レビューで今回の記録に修正を要する指摘なし。アプリ/UI変更はなく、
新しいアプリ全体試験・ブラウザー・AWS反映を行ったとは報告しない。
