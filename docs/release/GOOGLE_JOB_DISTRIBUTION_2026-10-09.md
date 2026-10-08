# Google履歴の通常配布物検証・API仕様の型修正

## 現在の判定

正式公開 **No-Go**。main/AWS/共有DB/Secrets/IAM/課金/容量は未変更。
今回の作業は固定ソースを通常Dockerfileでビルドしたローカル配布物の検査であり、
実Googleや常設worker/共有運用の成功を意味しない。

## 初回c3f41d35配布物

`c3f41d35cb9b171d0eac0f2931adec732605f839` のclean checkoutからgit archiveを取得し、
通常Dockerfileと通常entrypointでビルドした。固定imageは
`sha256:016fee2d66ce9f18a233390f1a306c27992dd9e1cf52ff26a61217f636ace8ee`。
選定736 source/assetsはarchiveと不一致0、111 packages/依存10層は先行7e配布物と一致、
entrypoint一致、pyc0。変更された選定7ファイルは履歴helper/view/templateと関連テストであり、
先行のworker fault試験を今回再実行した証拠とはしない。

証拠は `D:/tmp/codex-google-presentation-runtime-20261009`。
PG18.3はnetwork none、portなし、永続volumeなしのtmpfs。通常imageのテストはPGの
loopback namespaceだけを共有し、read-only・非root・cap-drop ALL・no-new-privileges、
source/test/設定のbind mountなし。実Google・AWSへの外部接続はできない。
追加ハーネスは `python -c` で試験の隔離だけを設定し、/appを書き換えない。

- Google/API/日本語UI静的回帰378件、終了0・省略0。
- 本番/ローカル設定・logging/SDK privacy70件は **1失敗、終了1**。
- `.github` が正常に配布対象外なのでCIの選定ファイル検査1件はimageには含めない。
  同検査は先行ソース試験で成功済みであり、製品試験を省略して合格にしたものではない。
- 配布物検査・回帰・設定・PGの専用4container/tmpfsを正確なID/labelで撤去。
  test DB消去とbase DB public表0を確認し、固定image/証拠/別作業を保持した。

## 不合格の原因と修正

`check --deploy` のAPI仕様生成で、追加した3つのSerializerMethodFieldに型情報がなく、
`drf_spectacular.W001` が3件出た。`can_retry` が実際にはboolなのにOpenAPIではstringとなる。
警告抑止・testの期待値変更ではなく、get_display_state/get_status_messageへstr、
get_can_retryへboolの戻り値注釈を追加する。返却値・所有者/認可・再試行条件は変えない。

Schemaの3項目の型とreadOnly、および警告0をassertする追加REDは、bool不一致と警告で
2失敗（`red-schema.log`）。修正後、実API/history/static・本番deploy checkの局所43試験が
失敗0、PG専用2省略（`green-schema.log`）。新schema試験を含むstatic module36文/4分岐先は
全実行・除外なし。Black/isort/Flake8/Banditと差分検査を確認した。

### 修正版の固定配布物

修正は `6791357f468c9aa7debecd68c817629f38329459` としてcommit/pushした。
同じ通常Dockerfileで新image
`sha256:6de91d2a3c3fb4d2d4254c656b893352098a40d3dbd1bb3a75b7707c7e238874` を作成。
証拠は `D:/tmp/codex-google-presentation-schema-runtime-20261009`。
再照合した736選定source/assets不一致0・111 packages/依存10層/entrypoint一致・pyc0。
c3配布物との差分は `job_views.py` とschema testの2ファイルだけで、画面資産は一致する。
同じ隔離条件で新schema testを含むGoogle回帰379件/196.049秒と設定・privacy70件/85.374秒が
成功。計449件は非重複の選定、全て省略0・終了0・OOM false。
deploy checkの3警告は解消し、OpenAPIのbool/string/readOnlyと警告0も実配布物で確認した。
初回の設定不合格やスキャンを、修正版の合格証拠に読み替えない。
専用4container/tmpfsを正確なID/label/nameで撤去し、test DB消去・base DB public表0を監査した。
固定image・archive・script/log/SARIF・元の別作業は保持した。

## 各固定imageの新しいスキャン

Docker Scout 1.26.0、フィルターなし・native終了2。SARIFは38指摘
（HIGH2/MEDIUM1/LOW35）で **未合格**。
HIGHはcyrus-sasl2のCVE-2026-107161、zlibのCVE-2026-85091で、当該レポートのfixed_versionは
両方 `not fixed`。先行の37指摘/HIGH1を今回imageの最新結果として流用しない。
依存bytesは同じであり、スキャン結果の変化を製品更新による改善/悪化と断定しない。
実際の影響と対策・残リスク判定は未完了で、公開判断を合格へ変えない。

修正版6deの新スキャンも、1.26.0/フィルターなし/native終了2、38指摘
（HIGH2/MEDIUM1/LOW35）で未合格。実際の38 resultsをrule IDへ照合して分類し、
HIGHは同じ2件・当該fixed_versionはnot fixedと確認した（`scan-reviewed.json`）。
通常回帰449成功をOSスキャンや正式公開の合格へ読み替えない。

後続の[HIGH利用条件調査](RUNTIME_HIGH_IMPACT_2026-10-09.md)でOSとpsycopg同梱のSASLを
別々に確認した。両方のDIGEST-MD5選択拒否は固定imageの限定証拠で、指摘は除外しない。
zlibの影響版判定の相違も未解消であり、38指摘/HIGH2の未合格を維持する。

## CIと残る条件

c3の[CI 37852932860](https://github.com/sheepdog0820/iaia/actions/runs/37852932860)はcancelledで終了。
修正版の[CI 37854284616](https://github.com/sheepdog0820/iaia/actions/runs/37854284616)は
後続の文書pushによる最新run優先でcancelled終了（3成功/3cancelled）。
その後続f271の[CI 37854944947](https://github.com/sheepdog0820/iaia/actions/runs/37854944947)は
10月9日の追加調査時点で実行中。全6成功の確認とは区別する。
親b710の全6成功とは区別し、cancelledや待機中を今回候補の成功にしない。
この記録は型修正候補679の配布物であり、後続の文書commitのCI成功を証明しない。
全cleanup/再連携/保持/認可・全lock順・legacy停止/drain/移行・限定回復・
実Google/共有運用、課金・実AWS性能・DB/S3復旧・運営条件は残る。
