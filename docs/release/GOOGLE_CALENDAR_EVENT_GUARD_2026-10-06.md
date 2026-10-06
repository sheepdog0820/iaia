# Google Calendar予定の照合・条件付き書き込み（2026-10-06）

## 対象と根拠

- 親は `0aa24d6425509f06b6d762c23c7342791f8b5ea5`、ブランチは `codex/google-calendar-event-guard-20261006`。変更はCalendar worker・関連fixture・新規試験・PG CI対象・検証記録に限定する。
- 保存済み外部予定IDの更新/取消には、新規作成の409回復経路と異なり、遠隔予定の識別情報を読む工程がなかった。接続先を固定する先行修正だけでは、現在のprimaryにある同じIDの無関係な予定を更新/削除しないことを証明できない。
- [Google events.get](https://developers.google.com/workspace/calendar/api/v3/reference/events/get) は現在の認可先のprimaryから予定を取得する。[events.update](https://developers.google.com/workspace/calendar/api/v3/reference/events/update) は全リソース更新である。[版指定の公式ガイド](https://developers.google.com/workspace/calendar/api/guides/version-resources)に従い、取得したETagをIf-Matchに指定して更新/削除する。版不一致は412となる。insertにはこの条件を適用しない。

## 実装と利用者への影響

- 保存済みIDの更新/取消でもGETを先に行い、予定IDと既存privateメタデータ（session ID・生成済みsync key）を完全一致で確認する。無関係なID・欠落/不一致・不正応答は固定日本語エラーで終了し、PUT/DELETEを送らない。既存外部IDは消さず、古い記録の識別情報を独断で後付けしない。
- 実際に変更する4経路（保存済み更新、保存済み取消、409回復更新、保存前の取消）は、単一の強いETagをIf-Matchへ渡す。欠落・非文字列・weak/wildcard/list・不正引用符・改行入り値を拒否する。GETのheadersは変更せず、資格情報は先行ガードで各HTTP直前に再確認する。
- 412では「Google Calendarの予定が確認後に変更されました。予定を確認して再実行してください。」を保存し、自動再取得/再試行で新しい版へ上書きしない。利用者が予定を確認して明示的に再実行する必要がある。他の通信障害の固定日本語エラー/既存retryは維持する。
- 取消のGET 404/410は追加DELETEなしで完了する。ID一致のcancelled応答も同様に完了する。[Google Events仕様](https://developers.google.com/workspace/calendar/api/v3/reference/events)では削除済み予定はID以外を保証しないため、この場合はprivate情報・ETagがないことを理由に再削除しない。ID不一致のcancelled応答は拒否する。
- 保存済み更新のPUT応答も予定IDを確認してから成功を記録する。不正な成功本文は失敗として記録するが、既に遠隔で受理された書き込みを自動で巻き戻すことはできない。
- 保存済みIDをURLの1要素としてエンコードし、Requestsが親パスへ正規化する「.」「..」はHTTP前に拒否する。記号入り試験値のURL維持はGoogleがその値を有効な予定IDとして受理する証拠ではない。
- 保存済み更新/取消では通常GETが1回増える。以前は無条件に書けた、識別情報のない古い予定は停止する。対象確認/安全な移行方法は別条件で、自動再作成や遠隔データ削除で回避しない。

## TDD・検証記録

- 修正前の8件は初回59 failure/8 error。期待される旧retryと欠落headerを明示的な失敗として観測するfixtureへ整え、67 failure/0 errorを確認した。実装後8件成功（0.852秒）、先行関連52件も成功（6.739秒）。
- 広い先行145件は2 error/PG専用3 skip。追加GETをmockしていない既存認可fixtureの2ケースが、合成資格情報で実GoogleへGETを送り401になった。遠隔書き込みは行っていない。fixtureへ実際に期待するメタデータ/ETag/GET mockを追加し、以後の最終隔離実行は未mockの外部HTTPを遮断する。
- URLレビューでdot segmentの4 failureを再現して拒否処理を追加。公式の削除済み応答を踏まえた4 subtest中2 failureも再現し、書き込みなしの完了へ修正した。
- loopback fixtureの初回は既にmockされたSessionへのautospec指定で8 error。元のtransportを保持し、宛先を当該127.0.0.1の動的portだけに限定、環境proxyを使わず、開始直後から後片付けを登録する形へ訂正した。新規13件（117 subtest）は成功（1.791秒）。
- 最終新規試験は、不一致10、不正GET8、不正ETag48、条件付き成功4、GET中の失効/資格情報変更16、URL境界2/dot4、412競合4、GET欠落2、削除済み応答4、GET通信失敗2、更新応答5、実loopback HTTP8を確認する。Requestsの生成後URL/headersに加え、HTTPサーバーで受けたIf-Matchを照合し、確認後に版が変わった4ケースは書き込み0、未変更の4ケースは書き込み1を確認する。
- 先行147件はPG147成功/省略0（42.403秒）、SQLite143成功/PG専用4省略（38.091秒）。削除済み対応とloopback追加後の149件もPG149成功/省略0（42.860秒）、SQLite145成功/4省略（27.550秒）。以下の最終整形・fixture整理後の記録とは区別する。
- 最終版はPostgreSQL149件成功/省略0（46.527秒）、SQLite145件成功/PG専用4件省略（31.250秒）。各実行には文書試験39件を含む。本体追加差分40実行文/16分岐、新規試験293文/66分岐は100%。worker全体の行・分岐合算は75%であり、全機能・実Googleを100%確認したという意味ではない。
- 対象6 PythonのBlack/isort/Flake8/Banditを確認。合成資格情報のB105/B106に限定した例外の「no failed test」警告は残るが指摘項目0。loopback宛先の検証は最適化で消えるassertを使わずTestCaseの照合にした。表示エラーを完全一致確認し、応答本文/資格情報を保存しない。
- この試験は実Googleの認可・書き込み・ETag運用の確認ではない。Celery/brokerはmock、HTTPの実証先はloopbackだけで、実ブラウザー・AWS・共有DB・本番の操作は実施していない。先行2件の実401を連携成功の証拠にしない。

最終証拠:

- `D:/tmp/codex-google-calendar-event-guard-20261006-final-formatted-pg-coverage.json`。SHA-256: `7306c968d79055f593e2c2a464b24d38db580dbbf0ce57aec678f074223c4875`。
- `D:/tmp/codex-google-calendar-event-guard-20261006-final-formatted-sqlite-coverage.json`。SHA-256: `1f69903cf82a1edb3f805ce2ceaed6b98198ad6bf57ff54a1f699ebed92ab05e`。
- 専用PG container `6018742321ab` はID/name/label/匿名volumeを照合し、Django試験DB0の後に停止・自動削除。volume `757d25af1b8f` と55437待受なしを確認。loopback各サーバーもshutdown/close/thread終了を確認し、記録は保持する。実ユーザーデータは変更/削除しない。
- 6 Pythonの整形・lint/security、日本語表示・実差分の自己レビューで追加の要修正事項なし。対象9ファイルのUTF-8/LFと空白検査を最終ステージで確認した。文書追加後の39件も成功（0.035秒）。CI YAML/PG対象追加を確認し、通常pushでAWSデプロイが起動しないDjango CIのみであることを維持する。全CIはpush後に別途確認する。

## 未確認事項・復旧

- メタデータは秘密の認証証明ではなく、同じID/メタデータを持つ別接続先のコピーや履歴を区別する永続スキーマは未実装。接続先別の外部予定ID管理、実Googleでの取消/復帰、古い記録の安全な移行は残る。
- 取得前に済んだ遠隔編集は、片方向同期の現在のアプリ値で更新され得る。保護するのは取得した版からの競合であり、利用者の手動編集をすべて保持する機能ではない。ETagのGoogle側運用は実連携承認後に検証する。
- DBで認可/接続状態を確認した直後の競合、開始済みHTTP取消、遠隔資格情報の所有者/有効性、旧worker混在等は先行記録どおり未証明。新しいガードだけで原子的な取消を保証しない。
- DB schema/共有データ、Secrets/IAM、課金/容量、外部通知、main/AWS反映の変更なし。以前のfavicon反映承認をこの候補へ拡張しない。元worktreeのハンドアウト別作業は保持する。
- 復旧は今回コミットのrevert。schema逆移行は不要。既にGoogleが受理した予定をrevertで復元せず、取得/If-Match保護がなくなることに注意する。
- [正式公開の受け入れ条件](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)はNo-Go。HIGH3・実課金/連携・運用/性能/復旧等の残条件を維持する。
